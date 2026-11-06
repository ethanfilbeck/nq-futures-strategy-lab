"""Signals that arrive from outside the bot (TradingView webhooks).

An external signal is only a *request*: it still goes through the same risk engine (limits, cooldowns,
event blackouts, sizing from equity and stop distance, order sanity checks) and the same simulated broker
with a bracket stop/target. The sender's quantity is ignored; the bot sizes every trade itself.
"""
from __future__ import annotations

import threading
from collections import deque

import pandas as pd

from .strategy import Signal

MAX_SIGNAL_AGE = pd.Timedelta(minutes=2)


class ExternalSignals:
    def __init__(self, cfg, spec):
        self.cfg, self.spec = cfg, spec
        self._q: deque[dict] = deque(maxlen=50)
        self._lock = threading.Lock()
        self.rejected: list[tuple[str, dict]] = []

    def submit(self, sig: dict) -> None:
        """sig: {'side': 1|-1, 'stop': float, 'target': float, 'time': pd.Timestamp, 'id': str}"""
        with self._lock:
            self._q.append(sig)

    def mark_traded(self, session_date, side):
        pass

    def evaluate(self, row, regime: str) -> Signal | None:
        """Take the newest signal that is not older than 2 minutes relative to this bar; drop the rest."""
        now = row.get("_ts")
        with self._lock:
            items = list(self._q)
            self._q.clear()
        best = None
        for s in items:
            if now is not None and (now - s["time"] > MAX_SIGNAL_AGE or s["time"] > now + pd.Timedelta(minutes=1)):
                self.rejected.append(("stale or future-dated", s))
                continue
            best = s
        if best is None or not row["rth"]:
            return None
        c = row["close"]
        stop, target = self.spec.round_to_tick(best["stop"]), self.spec.round_to_tick(best["target"])
        return Signal(best["side"], c, stop, target, None, "external",
                      f"TradingView webhook {best.get('id', '')}: stop {stop} target {target}")
