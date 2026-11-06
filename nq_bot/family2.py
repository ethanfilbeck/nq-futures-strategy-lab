"""Strategy family 2 (pre-registered in docs/PREREG_FAMILY2.md). Rules are frozen; do not tune.

H4 'sweep'          — liquidity sweep of the prior day's RTH high/low, then reclaim -> fade it.
H5 'vwap_pullback'  — in a trending regime, buy/sell the pullback to session VWAP.
H3 (overnight drift) is a fixed-time trade outside RTH and lives in run_family2_prereg.py.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .strategy import Signal

F2_COLS = ["pdh", "pdl"]
SWEEP_MIN_PTS = 2.0
RECLAIM_BARS = 5          # the sweep bar and the next 4
STOP_BUFFER = 2.0
MIN_STOP = 8.0
RR = 2.0
H4_START, H4_END = 9 * 60 + 45, 15 * 60
H5_START, H5_END = 10 * 60, 14 * 60
H5_ATR_MULT = 0.5


def add_family2_features(feats: pd.DataFrame, cfg) -> pd.DataFrame:
    """Previous regular session's high/low, attached to every bar of the next session (causal)."""
    out = feats
    rth = out["rth"]
    sd = out["session_date"]
    hi = out["high"].where(rth).groupby(sd).max()
    lo = out["low"].where(rth).groupby(sd).min()
    daily = pd.DataFrame({"hi": hi, "lo": lo}).dropna()
    daily["pdh"] = daily["hi"].shift(1)
    daily["pdl"] = daily["lo"].shift(1)
    out["pdh"] = sd.map(daily["pdh"]).astype(float)
    out["pdl"] = sd.map(daily["pdl"]).astype(float)
    return out


def _nan(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


class LiquiditySweep:
    """H4. `observe` sees every bar (also while in a trade); `evaluate` only returns a signal created on this bar."""

    def __init__(self, cfg, spec):
        self.cfg, self.spec = cfg, spec
        self.day = None
        self._ready: Signal | None = None

    def _reset(self, d):
        self.day = d
        self.state = {s: {"active": False, "done": False, "n": 0, "ext": None} for s in (1, -1)}

    def mark_traded(self, session_date, side):
        pass  # one sweep per side per day is enforced by 'done'

    def observe(self, row) -> None:
        self._ready = None
        if row["session_date"] != self.day:
            self._reset(row["session_date"])
        if not row["rth"] or _nan(row["pdh"]) or _nan(row["pdl"]):
            return
        m = row["minute_of_day"]
        for side, level in ((-1, row["pdh"]), (1, row["pdl"])):
            st = self.state[side]
            if st["done"]:
                continue
            swept = row["high"] >= level + SWEEP_MIN_PTS if side == -1 else row["low"] <= level - SWEEP_MIN_PTS
            if not st["active"]:
                if not swept:
                    continue
                st.update(active=True, n=0, ext=row["high"] if side == -1 else row["low"])
            else:
                st["ext"] = max(st["ext"], row["high"]) if side == -1 else min(st["ext"], row["low"])
            st["n"] += 1
            reclaimed = row["close"] < level if side == -1 else row["close"] > level
            if reclaimed:
                st["done"] = True
                if H4_START <= m < H4_END and self._ready is None:
                    self._ready = self._signal(side, row["close"], st["ext"], level)
            elif st["n"] >= RECLAIM_BARS:
                st["done"] = True  # first sweep failed to reclaim: no more for this side today

    def _signal(self, side, close, ext, level) -> Signal:
        stop = ext + STOP_BUFFER if side == -1 else ext - STOP_BUFFER
        if side * (close - stop) < MIN_STOP:
            stop = close - side * MIN_STOP
        stop = self.spec.round_to_tick(stop)
        risk = abs(close - stop)
        target = self.spec.round_to_tick(close + side * RR * risk)
        return Signal(side, close, stop, target, None, "n/a",
                      f"sweep {'PDH' if side == -1 else 'PDL'} {level} ext {ext}, reclaim close {close}")

    def evaluate(self, row, regime: str) -> Signal | None:
        return self._ready


class VwapPullback:
    """H5."""

    def __init__(self, cfg, spec):
        self.cfg, self.spec = cfg, spec
        self._traded = {}

    def mark_traded(self, session_date, side):
        self._traded.setdefault(session_date, set()).add(side)

    def evaluate(self, row, regime: str) -> Signal | None:
        m = row["minute_of_day"]
        if not row["rth"] or not (H5_START <= m < H5_END):
            return None
        vwap, atr = row["vwap"], row["atr"]
        if _nan(vwap) or _nan(atr):
            return None
        taken = self._traded.get(row["session_date"], set())
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]
        side = 0
        if regime == "bullish" and l <= vwap and c > vwap and c > o and 1 not in taken:
            side = 1
            stop = min(l, vwap) - H5_ATR_MULT * atr
        elif regime == "bearish" and h >= vwap and c < vwap and c < o and -1 not in taken:
            side = -1
            stop = max(h, vwap) + H5_ATR_MULT * atr
        if side == 0:
            return None
        if side * (c - stop) < MIN_STOP:
            stop = c - side * MIN_STOP
        stop = self.spec.round_to_tick(stop)
        risk = abs(c - stop)
        target = self.spec.round_to_tick(c + side * RR * risk)
        return Signal(side, c, stop, target, None, regime, f"VWAP pullback {regime}: close {c} vs VWAP {vwap:.2f}")


def overnight_drift_trades(bars: pd.DataFrame, slippage_ticks: int = 1, commission: float = 0.62,
                           point_value: float = 2.0, tick: float = 0.25) -> pd.DataFrame:
    """H3: long at the 02:00 ET bar open, out at the 03:00 ET bar open, with a protective stop.
    `bars` index = bar OPEN times in America/New_York."""
    idx = bars.index
    mins = idx.hour * 60 + idx.minute
    dates = pd.Index(idx.date)
    slip = slippage_ticks * tick
    o, l = bars["open"].to_numpy(), bars["low"].to_numpy()
    pos = {}
    for i, (d, m) in enumerate(zip(dates, mins)):
        if m in (120, 180):
            pos.setdefault(d, {})[m] = i
    days = sorted(d for d, v in pos.items() if 120 in v and 180 in v and pd.Timestamp(d).weekday() < 5)
    moves = pd.Series({d: o[pos[d][180]] - o[pos[d][120]] for d in days})
    hist = moves.abs().shift(1).rolling(20, min_periods=10).median()
    rows = []
    for d in days:
        if np.isnan(hist[d]):
            continue
        i0, i1 = pos[d][120], pos[d][180]
        entry = o[i0] + slip
        stop = round((entry - max(10.0, 1.5 * hist[d])) / tick) * tick
        exit_px, kind = o[i1] - slip, "time"
        for j in range(i0, i1):
            if l[j] <= stop:
                exit_px, kind = min(stop, o[j]) - slip, "stop"
                break
        gross = (exit_px - entry) * point_value
        rows.append({"entry_ts": idx[i0], "exit_ts": idx[i1], "side": 1, "qty": 1, "entry_price": entry,
                     "exit_price": exit_px, "exit_kind": kind, "gross": round(gross, 2),
                     "commission": 2 * commission, "net": round(gross - 2 * commission, 2),
                     "r_multiple": round((gross - 2 * commission) / ((entry - stop) * point_value), 3),
                     "regime": "overnight", "entry_hour": 2,
                     "move_open_to_open": o[i1] - o[i0]})
    return pd.DataFrame(rows)
