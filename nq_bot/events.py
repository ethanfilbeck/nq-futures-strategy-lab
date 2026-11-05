"""Economic-event blackout windows (CPI, PPI, NFP, FOMC...).

The CSV is yours to maintain from official sources (BLS release calendar, Federal Reserve
FOMC calendar). The bot never invents event dates; an empty file means no blackouts.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pandas as pd


class EventCalendar:
    def __init__(self, path, tz: str, before_min: int, after_min: int):
        self.before = timedelta(minutes=before_min)
        self.after = timedelta(minutes=after_min)
        self.events = pd.DataFrame(columns=["datetime_et", "event", "impact"])
        p = Path(path)
        if p.exists():
            df = pd.read_csv(p, comment="#")
            if len(df):
                df["datetime_et"] = pd.to_datetime(df["datetime_et"]).dt.tz_localize(tz)
                df["impact"] = df.get("impact", "high").fillna("high").str.lower()
                self.events = df.sort_values("datetime_et").reset_index(drop=True)

    def blackout(self, ts) -> str | None:
        for _, e in self.events.iterrows():
            if e["datetime_et"] - self.before <= ts <= e["datetime_et"] + self.after:
                return str(e["event"])
        return None

    def high_impact_soon(self, ts) -> str | None:
        for _, e in self.events.iterrows():
            if e["impact"] == "high" and e["datetime_et"] - self.before <= ts < e["datetime_et"]:
                return str(e["event"])
        return None
