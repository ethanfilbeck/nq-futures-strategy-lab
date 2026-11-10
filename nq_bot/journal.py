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
        self.path = None
        if self.enabled:
            Path(directory).mkdir(parents=True, exist_ok=True)
            self.path = Path(directory) / f"decisions_{datetime.now():%Y%m%d_%H%M%S}.jsonl"

    def write(self, _ts, _event: str, /, **data) -> None:
        if not self.enabled:
            return
        rec = {"at": str(_ts), "event": _event, **data}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")


class Alerts:
    """Logs every alert; also POSTs to ALERT_WEBHOOK_URL (Discord/Slack-style) if set."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.url = os.environ.get("ALERT_WEBHOOK_URL")

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
            req = urllib.request.Request(self.url, data=body, method="POST",
                                         headers={"Content-Type": "application/json", "User-Agent": "nq-bot-alerts/1.0"})
            urllib.request.urlopen(req, timeout=5).read()
            return True
        except Exception as e:  # alerts must never crash the bot; never log the URL (it is a secret)
            log.warning("alert webhook failed: %s", type(e).__name__)
            return False
