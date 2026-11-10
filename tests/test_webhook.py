"""TradingView webhook receiver: security checks, HTTP round trip, and end-to-end on real replayed bars."""
import json
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from nq_bot.config import load_settings, override
from nq_bot.journal import Alerts
from nq_bot.webhook import TRADINGVIEW_IPS, WebhookGate, serve

ROOT = Path(__file__).resolve().parents[1]
SECRET = "s" * 32
TZ = "America/New_York"
BAR = pd.Timestamp("2025-06-30 10:00", tz=TZ)


class FakeRunner:
    def __init__(self):
        self.cfg = SimpleNamespace(session=SimpleNamespace(timezone=TZ))
        self.last_ts = BAR
        self.signals, self.flattens, self.log = [], [], []
        self.journal = SimpleNamespace(write=lambda *a, **k: self.log.append(k))
        self.external = SimpleNamespace(submit=self.signals.append)

    def external_flatten(self, reason):
        self.flattens.append(reason)


def body(**over):
    m = {"passphrase": SECRET, "event": "entry", "symbol": "MNQ1!", "side": "long",
         "stop": 22000.0, "target": 22100.0, "time": int(BAR.tz_convert("UTC").timestamp() * 1000)}
    m.update(over)
    return json.dumps(m).encode()


def gate(allow=None, clock=None):
    r = FakeRunner()
    return WebhookGate(r, SECRET, allow, **({"clock": clock} if clock else {})), r


def test_rejects_short_secret():
    with pytest.raises(ValueError):
        WebhookGate(FakeRunner(), "short")


def test_valid_entry_queued_without_leaking_secret():
    g, r = gate()
    assert g.handle(body(), "127.0.0.1", None) == (200, "signal queued")
    assert r.signals[0]["side"] == 1 and r.signals[0]["stop"] == 22000.0
    assert SECRET not in json.dumps(r.log, default=str)


@pytest.mark.parametrize("payload,code", [
    (body(passphrase="x" * 32), 401),
    (b"not json", 400),
    (b"[1, 2]", 400),                                            # valid JSON but not an object
    (b"x" * 5000, 413),
    (body(event="buy_everything"), 400),
    (body(symbol="ES1!"), 400),
    (body(side="up"), 400),
    (body(stop=22200.0), 400),                                   # stop above target on a long
    (body(stop="nan"), 400),
    (body(time=int((BAR - pd.Timedelta(minutes=10)).timestamp() * 1000)), 400),   # replayed old alert
])
def test_rejections(payload, code):
    g, r = gate()
    assert g.handle(payload, "127.0.0.1", None)[0] == code
    assert not r.signals


def test_duplicate_ignored_and_rate_limited():
    t = {"now": 0.0}
    g, r = gate(clock=lambda: t["now"])
    assert g.handle(body(), "127.0.0.1", None)[1] == "signal queued"
    assert g.handle(body(), "127.0.0.1", None)[1] == "duplicate ignored"
    for i in range(8):
        g.handle(body(stop=21990.0 - i), "127.0.0.1", None)
    assert g.handle(body(stop=21900.0), "127.0.0.1", None)[0] == 429
    t["now"] += 61
    assert g.handle(body(stop=21901.0), "127.0.0.1", None)[0] == 200


def test_ip_allowlist_through_tunnel():
    g, r = gate(allow=TRADINGVIEW_IPS)
    assert g.handle(body(), "127.0.0.1", "8.8.8.8")[0] == 403
    assert g.handle(body(), "127.0.0.1", "52.89.214.238")[0] == 200
    assert g.handle(body(stop=21999.0), "203.0.113.5", "52.89.214.238")[0] == 403   # header from non-tunnel peer ignored


def test_flatten_event():
    g, r = gate()
    assert g.handle(body(event="flatten", reason="end of session"), "127.0.0.1", None)[0] == 200
    assert r.flattens == ["TradingView: end of session"]


def post(port, data, headers=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/tv", data=data, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_http_round_trip():
    g, r = gate()
    httpd = serve(g, port=0)
    port = httpd.server_address[1]
    try:
        assert post(port, body()) == (200, {"status": "signal queued"})
        assert post(port, body(passphrase="y" * 32))[0] == 401
    finally:
        httpd.shutdown()


DATA = ROOT / "data" / "mnq_train.csv"


@pytest.mark.skipif(not DATA.exists(), reason="needs data/mnq_train.csv (not in the repo)")
@pytest.mark.parametrize("stop_pts,expect_trade", [(10, True), (60, False)])
def test_end_to_end_on_real_replayed_session(tmp_path, stop_pts, expect_trade):
    """A webhook signal during a replayed real session becomes a bracketed simulated trade -
    unless its stop is too wide for the $10k account's $50 per-trade risk limit."""
    from nq_bot.data import load_csv
    from nq_bot.paper import PaperRunner
    cfg = override(load_settings(ROOT / "config/settings.yaml"),
                   {"strategy.name": "tradingview", "events.file": "none.csv"})
    bars = load_csv(str(DATA))
    day = pd.Timestamp("2025-06-30", tz=TZ)
    hist = bars[(bars.index < day) & (bars.index >= day - pd.Timedelta(days=35))]
    live = bars[(bars.index >= day + pd.Timedelta(hours=9, minutes=30)) & (bars.index < day + pd.Timedelta(hours=10, minutes=30))]
    runner = PaperRunner(cfg, hist, tmp_path, alerts=Alerts(enabled=False), persist=False)
    g = WebhookGate(runner, SECRET, None)
    httpd = serve(g, port=0)
    port = httpd.server_address[1]
    sent_at = None
    try:
        for ts, b in live.iterrows():
            runner.on_bar(ts, b["open"], b["high"], b["low"], b["close"], b["volume"])
            if sent_at is None and ts.hour == 10 and ts.minute == 0:
                c = b["close"]
                code, _ = post(port, body(stop=c - stop_pts, target=c + 2 * stop_pts,
                                          time=int(ts.tz_convert("UTC").timestamp() * 1000)))
                assert code == 200
                sent_at = ts
    finally:
        httpd.shutdown()
    eng = runner.engine
    journal = runner.journal.path.read_text()
    if not expect_trade:
        assert eng.trade is None and not eng.trades
        assert "risk budget" in journal
        return
    fills = live[live.index > sent_at]
    nxt = fills.iloc[1]                         # signal is picked up on the next bar, fills on the one after
    trade = eng.trades[0] if eng.trades else eng.trade
    assert trade is not None, "webhook signal did not produce a simulated trade"
    assert trade["entry_price"] == nxt["open"] + 0.25          # next-bar open + 1 tick slippage
    orders = [json.loads(l) for l in journal.splitlines() if '"event": "order"' in l]
    assert len(orders) == 1 and orders[0]["signal"]["stop"] < orders[0]["signal"]["entry_ref"] < orders[0]["signal"]["target"]
    assert orders[0]["qty"] == 1                                # bot sized it; sender's qty is ignored
    if eng.trades:
        assert eng.trades[0]["exit_kind"] in ("stop", "target", "flatten")
    else:
        assert runner.broker.stop is not None                   # still open: protective stop is working


def test_informational_alerts_ignored_after_auth():
    g, r = gate()
    assert g.handle(body(event="closed"), "127.0.0.1", None) == (200, "ignored (informational)")
    assert g.handle(body(event="closed", passphrase="z" * 32), "127.0.0.1", None)[0] == 401


def test_pine_alert_json_is_accepted():
    """The exact JSON shape the Pine script sends must pass the receiver's validation."""
    pine = Path(ROOT / "tradingview/holdout_orb.pine").read_text()
    assert '"passphrase":"\' + iPass' in pine and '"time":\' + str.tostring(time)' in pine
    ms = int(BAR.tz_convert("UTC").timestamp() * 1000)
    sample = ('{"bot":"holdout","passphrase":"' + SECRET + '","event":"entry","symbol":"MNQ1!","side":"short",'
              '"qty":1,"ref":22050.25,"stop":22070.5,"target":22009.75,"time":' + str(ms) + '}').encode()
    g, r = gate()
    assert g.handle(sample, "127.0.0.1", None) == (200, "signal queued")
    assert r.signals[0]["side"] == -1


def test_outside_ips_cannot_exhaust_rate_limit():
    """Found in security review: rate limit used to run before the IP allowlist, so anyone could lock out alerts."""
    g, r = gate(allow=TRADINGVIEW_IPS)
    for _ in range(50):
        assert g.handle(body(), "127.0.0.1", "203.0.113.9")[0] == 403
    assert g.handle(body(), "127.0.0.1", "52.89.214.238")[0] == 200


def test_negative_or_bad_content_length_rejected():
    """Found in security review: Content-Length -1 made the server read until EOF with no size cap."""
    import http.client
    g, r = gate()
    httpd = serve(g, port=0)
    port = httpd.server_address[1]
    try:
        for bad in ("-1", "abc"):
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            c.putrequest("POST", "/tv")
            c.putheader("Content-Length", bad)
            c.endheaders()
            assert c.getresponse().status == 400
            c.close()
    finally:
        httpd.shutdown()
    assert not r.signals


def test_alert_webhook_must_be_https(monkeypatch):
    from nq_bot import journal
    for bad in ("http://example.invalid/hook", "file:///etc/passwd", "ftp://example.invalid/x"):
        monkeypatch.setenv("ALERT_WEBHOOK_URL", bad)
        assert journal.Alerts().url is None
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://example.invalid/hook")
    assert journal.Alerts().url == "https://example.invalid/hook"
