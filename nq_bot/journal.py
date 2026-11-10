"""Decision journal (JSON lines) and alerts. Credentials are never written here."""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime
from pathlib import Path

log = logging.getLogger("nq_bot")


class Journal:
    def __init__(self, directory: str | Path | None, enabled: bool = True):
        self.enabled = enabled and directory is not None
        self.path: Path | None = None
        if self.enabled and directory is not None:
            Path(directory).mkdir(parents=True, exist_ok=True)
            self.path = Path(directory) / f"decisions_{datetime.now():%Y%m%d_%H%M%S}.jsonl"  # noqa: DTZ005 (local file name)

    def write(self, _ts: object, _event: str, /, **data: object) -> None:
        if not self.enabled or self.path is None:
            return
        rec = {"at": str(_ts), "event": _event, **data}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")


class Alerts:
    """Logs every alert; also POSTs to ALERT_WEBHOOK_URL (Discord/Slack-style) if set."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        url = os.environ.get("ALERT_WEBHOOK_URL") or None
        if url and not url.lower().startswith("https://"):
            # urllib would also open file:// or plain http:// - never send alerts anywhere but an HTTPS webhook
            log.warning("ALERT_WEBHOOK_URL ignored: it must start with https://")
            url = None
        self.url = url

    def send(self, level: str, text: str) -> bool:
        """Log the alert and, if a webhook URL is set, post it. Returns True only if the post succeeded."""
        if not self.enabled:
            return False
        getattr(log, level if level in ("info", "warning", "error") else "info")(text)
        if not self.url:
            return False
        try:
            body = json.dumps({"content": f"[NQ bot {level.upper()}] {text}"}).encode()
            # Discord rejects Python's default user agent, so name ours.
            req = urllib.request.Request(self.url, data=body, method="POST",  # noqa: S310 (https enforced in __init__)
                                         headers={"Content-Type": "application/json", "User-Agent": "nq-bot-alerts/1.0"})
            urllib.request.urlopen(req, timeout=5).read()  # noqa: S310
            return True
        except Exception as e:  # alerts must never crash the bot; never log the URL (it is a secret)
            log.warning("alert webhook failed: %s", type(e).__name__)
            return False
