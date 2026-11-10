"""TradingView webhook receiver -> PaperRunner (SIMULATED orders only).

TradingView -> (HTTPS tunnel, e.g. cloudflared) -> this server on 127.0.0.1 -> ExternalSignals -> risk engine.

Security controls (a public URL that can trigger orders is an attack surface, even for paper):
- Listens on 127.0.0.1 only; exposure is via a tunnel you start deliberately.
- Shared secret ('passphrase' in the JSON body, since TradingView cannot set headers), >= 24 chars,
  compared in constant time. Never logged.
- Optional source-IP allowlist: TradingView's four documented webhook IPs, checked via the tunnel's
  CF-Connecting-IP / X-Forwarded-For header (only trusted when the request comes from 127.0.0.1).
- Body <= 4 KB, JSON only, strict schema; symbol must be MNQ/NQ; prices must be finite and positive.
- Freshness: the alert's 'time' must be within 2 minutes of the latest market bar (replay protection).
- Duplicate suppression (same body within 10 minutes) and rate limit (10 requests / minute).
- Responds immediately (TradingView cancels after 3 s); processing happens on the next bar.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pandas as pd

log = logging.getLogger("nq_bot.webhook")
TRADINGVIEW_IPS = frozenset({"52.89.214.238", "34.212.75.30", "54.218.53.128", "52.32.178.7"})
MAX_BODY = 4096
RATE_LIMIT = 10          # requests per 60 s
DEDUP_SECONDS = 600
MIN_SECRET_LEN = 24


class WebhookGate:
    """Validation logic, separate from HTTP so it can be unit-tested directly."""

    def __init__(self, runner, secret: str, allow_ips: frozenset | None = TRADINGVIEW_IPS, clock=time.time):
        if not secret or len(secret) < MIN_SECRET_LEN:
            raise ValueError(f"WEBHOOK_SECRET must be at least {MIN_SECRET_LEN} characters")
        self.runner, self.secret, self.allow_ips, self.clock = runner, secret.encode(), allow_ips, clock
        self.recent: deque[float] = deque()
        self.seen: dict[str, float] = {}
        self.lock = threading.Lock()

    def handle(self, body: bytes, peer_ip: str, fwd_ip: str | None) -> tuple[int, str]:
        now = self.clock()
        # IP allowlist first, so traffic from outside it can't use up the rate limit and lock out real alerts
        if self.allow_ips is not None:
            src = fwd_ip if (peer_ip == "127.0.0.1" and fwd_ip) else peer_ip
            if src not in self.allow_ips:
                self._audit("rejected", f"source ip {src} not allowed")
                return 403, "forbidden"
        with self.lock:
            while self.recent and now - self.recent[0] > 60:
                self.recent.popleft()
            if len(self.recent) >= RATE_LIMIT:
                return 429, "rate limited"
            self.recent.append(now)
        if len(body) > MAX_BODY:
            return 413, "body too large"
        try:
            msg = json.loads(body.decode("utf-8"))
            if not isinstance(msg, dict):   # not an assert: asserts vanish under `python -O`
                raise ValueError("not a JSON object")
        except Exception:
            return 400, "invalid JSON"
        given = str(msg.pop("passphrase", "")).encode()
        if not hmac.compare_digest(given, self.secret):
            self._audit("rejected", "bad passphrase")
            return 401, "unauthorized"
        digest = hashlib.sha256(body).hexdigest()
        with self.lock:
            for k in [k for k, t in self.seen.items() if now - t > DEDUP_SECONDS]:
                del self.seen[k]
            if digest in self.seen:
                return 200, "duplicate ignored"
            self.seen[digest] = now
        if msg.get("event") in ("closed", "partial", "halted"):
            return 200, "ignored (informational)"   # the bot tracks its own trades
        ok, why, sig = self._validate(msg)
        if not ok:
            self._audit("rejected", why)
            return 400, why
        if sig["event"] == "flatten":
            self.runner.external_flatten(f"TradingView: {msg.get('reason', 'flatten')}")
            self._audit("accepted", "flatten")
            return 200, "flatten queued"
        self.runner.external.submit(sig)
        self._audit("accepted", f"{'long' if sig['side'] > 0 else 'short'} stop {sig['stop']} target {sig['target']}")
        return 200, "signal queued"

    def _validate(self, m: dict):
        ev = m.get("event")
        if ev not in ("entry", "flatten"):
            return False, "event must be entry or flatten", None
        sym = str(m.get("symbol", "")).upper()
        if not (sym.startswith("MNQ") or sym.startswith("NQ")):
            return False, "symbol must be MNQ or NQ", None
        try:
            t = pd.Timestamp(int(m["time"]), unit="ms", tz="UTC")
        except Exception:
            return False, "missing or invalid time (ms since epoch)", None
        last = self.runner.last_ts
        if last is None or abs(t - last.tz_convert("UTC")) > pd.Timedelta(minutes=2):
            return False, "stale: alert time not within 2 minutes of the latest market bar", None
        if ev == "flatten":
            return True, "", {"event": "flatten"}
        side = {"long": 1, "short": -1}.get(str(m.get("side", "")).lower())
        if side is None:
            return False, "side must be long or short", None
        try:
            stop, target = float(m["stop"]), float(m["target"])
        except Exception:
            return False, "stop and target must be numbers", None
        if not all(math.isfinite(x) and x > 0 for x in (stop, target)):
            return False, "stop/target must be finite and positive", None
        if (side > 0 and not stop < target) or (side < 0 and not target < stop):
            return False, "stop/target on the wrong sides", None
        return True, "", {"event": "entry", "side": side, "stop": stop, "target": target,
                          "time": t.tz_convert(self.runner.cfg.session.timezone),
                          "id": hashlib.sha256(json.dumps(m, sort_keys=True).encode()).hexdigest()[:10]}

    def _audit(self, status: str, detail: str) -> None:
        self.runner.journal.write(pd.Timestamp.now(tz="UTC"), "webhook", status=status, detail=detail)
        if status == "rejected":
            log.warning("webhook rejected: %s", detail)


def serve(gate: WebhookGate, host: str = "127.0.0.1", port: int = 8787, path: str = "/tv") -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        server_version = "nqbot"
        sys_version = ""

        def do_POST(self):
            if self.path != path:
                return self._reply(404, "not found")
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return self._reply(400, "bad Content-Length")
            if n < 0 or n > MAX_BODY:   # a negative length would make read() wait for EOF with no size limit
                return self._reply(413 if n > 0 else 400, "bad Content-Length")
            body = self.rfile.read(n)
            fwd = self.headers.get("CF-Connecting-IP") or (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip() or None
            code, msg = gate.handle(body, self.client_address[0], fwd)
            self._reply(code, msg)

        def do_GET(self):
            self._reply(404, "not found")

        def _reply(self, code, msg):
            data = json.dumps({"status": msg}).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt, *args):  # no request bodies or secrets in logs
            log.info("%s %s", self.address_string(), fmt % args)

    httpd = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd
