"""Opening-range breakout with VWAP + trend-regime filter.

Long:  after the opening range completes and before entry_cutoff, a bar CLOSES above
       the OR high, above session VWAP, and the regime is bullish.
Short: mirror image.
Stop:  the tighter of the OR midpoint or entry -/+ max_stop_atr * ATR (min min_stop_points).
Exits: partial at partial_r, final at reward_risk, stop to breakeven after partial,
       flatten at flatten_time. One trade per direction per day.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .features import _hm


@dataclass
class Signal:
    side: int            # +1 long, -1 short
    entry_ref: float     # close of the signal bar (actual fill comes from the broker)
    stop: float
    target: float
    partial_target: float | None   # None = no partial exit (the whole position runs to stop or target)
    regime: str
    reason: str

    @property
    def risk_points(self) -> float:
        return abs(self.entry_ref - self.stop)


class OpeningRangeBreakout:
    def __init__(self, cfg, spec):
        self.cfg = cfg
        self.s = cfg.strategy
        self.spec = spec
        self.or_end = _hm(cfg.session.rth_start) + self.s.opening_range_minutes
        self.cutoff = _hm(self.s.entry_cutoff)
        self._traded = {}  # session_date -> set of sides taken

    def mark_traded(self, session_date, side: int) -> None:
        self._traded.setdefault(session_date, set()).add(side)

    def evaluate(self, row, regime: str) -> Signal | None:
        s = self.s
        m = row["minute_of_day"]
        if not row["rth"] or m < self.or_end or m >= self.cutoff:
            return None
        hi, lo, atr, vwap, close = row["or_high"], row["or_low"], row["atr"], row["vwap"], row["close"]
        if any(isinstance(x, float) and math.isnan(x) for x in (hi, lo, atr, vwap)):
            return None
        width = hi - lo
        if width < s.min_or_points or width > s.max_or_points:
            return None
        if regime not in s.allowed_regimes:
            return None
        taken = self._traded.get(row["session_date"], set())

        side = 0
        if s.allow_long and regime == "bullish" and close > hi and close > vwap and 1 not in taken:
            side = 1
        elif s.allow_short and regime == "bearish" and close < lo and close < vwap and -1 not in taken:
            side = -1
        if side == 0:
            return None

        mid = (hi + lo) / 2.0
        atr_stop = close - side * s.max_stop_atr * atr
        # tighter = closer to entry
        stop = max(mid, atr_stop) if side == 1 else min(mid, atr_stop)
        if side * (close - stop) < s.min_stop_points:
            stop = close - side * s.min_stop_points
        stop = self.spec.round_to_tick(stop)
        risk = abs(close - stop)
        target = self.spec.round_to_tick(close + side * s.reward_risk * risk)
        partial = self.spec.round_to_tick(close + side * s.partial_r * risk)
        return Signal(side, close, stop, target, partial, regime,
                      f"ORB {'long' if side == 1 else 'short'}: close {close} vs OR {lo}-{hi}, VWAP {vwap:.2f}")
