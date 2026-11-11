"""Intraday momentum (pre-registered in docs/PREREG_INTRADAY_MOMENTUM.md).

H1 'first_half_hour': sign(price@10:00 - prev 16:00 close) -> trade 15:30-16:00
H2 'rest_of_day':     sign(price@15:30 - prev 16:00 close) -> trade 15:30-16:00
Entry at the 15:29 bar's close (fills 15:30 open), exit after the 15:59 bar (fills ~16:00),
protective stop = entry -/+ max(10, 1.5 * median |15:30->16:00 move| over prior 20 sessions).
No parameters are tuned.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .strategy import Signal

M_1000, M_1529, M_1559 = 9 * 60 + 59, 15 * 60 + 29, 15 * 60 + 59
MOM_COLS = ["mom_prev_close", "mom_p1000", "mom_p1530", "mom_stop_pts"]


def add_momentum_features(feats: pd.DataFrame, cfg) -> pd.DataFrame:
    """Adds per-session reference prices. Every value is only placed on bars at/after the
    time it becomes known, so nothing looks ahead."""
    out = feats
    m = out["minute_of_day"]
    sd = out["session_date"]
    c = out["close"]

    def at(minute):  # close of that bar per session (NaN if missing)
        s = c[m == minute]
        return pd.Series(s.values, index=sd[m == minute].values)

    c1559, c1529, c0959 = at(M_1559), at(M_1529), at(M_1000)
    sessions = pd.Index(sorted(set(sd)))
    daily = pd.DataFrame(index=sessions)
    daily["c1559"] = c1559.groupby(level=0).last()
    daily["c1529"] = c1529.groupby(level=0).last()
    daily["c0959"] = c0959.groupby(level=0).last()
    daily = daily[daily["c1559"].notna() | daily["c1529"].notna() | daily["c0959"].notna()]
    rth_days = daily.index[daily["c1529"].notna()]  # sessions that have an RTH close area
    d = daily.loc[rth_days]
    d["prev_close"] = d["c1559"].shift(1)                     # previous RTH session's 16:00 close
    lh = (d["c1559"] - d["c1529"]).abs()
    s = cfg.momentum
    d["stop_pts"] = np.maximum(s.min_stop_points,
                               s.stop_mult * lh.shift(1).rolling(s.stop_lookback_days,
                                                                 min_periods=s.min_history_days).median())

    def get(col: str) -> pd.Series:
        """Map each bar's session date onto that day's value of `col`."""
        return sd.map(d[col]).astype(float)

    out["mom_prev_close"] = get("prev_close")
    out["mom_p1000"] = get("c0959").where(m >= M_1000)
    out["mom_p1530"] = get("c1529").where(m >= M_1529)
    out["mom_stop_pts"] = get("stop_pts")
    return out


class IntradayMomentum:
    def __init__(self, cfg, spec):
        self.cfg, self.spec = cfg, spec
        self.variant = cfg.momentum.variant
        self._traded = set()

    def mark_traded(self, session_date, side):
        self._traded.add(session_date)

    def evaluate(self, row, regime: str) -> Signal | None:
        if row["minute_of_day"] != M_1529 or not row["rth"] or row["session_date"] in self._traded:
            return None
        prev, stop_pts = row["mom_prev_close"], row["mom_stop_pts"]
        ref = row["mom_p1000"] if self.variant == "first_half_hour" else row["mom_p1530"]
        if any(x is None or (isinstance(x, float) and math.isnan(x)) for x in (prev, stop_pts, ref)):
            return None
        pred = ref - prev
        if pred == 0:
            return None
        side = 1 if pred > 0 else -1
        close = row["close"]
        stop = self.spec.round_to_tick(close - side * stop_pts)
        far = self.spec.round_to_tick(close + side * 100 * stop_pts)  # no profit target: time exit only
        return Signal(side, close, stop, far, None, regime,
                      f"{self.variant}: predictor {pred:+.2f} pts, stop {stop_pts:.1f} pts")
