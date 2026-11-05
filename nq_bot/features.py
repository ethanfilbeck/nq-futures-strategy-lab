"""Causal (no look-ahead) indicators on 1-minute bars.

Input: DataFrame indexed by tz-aware bar-OPEN timestamps (America/New_York) with
open, high, low, close, volume. Every column at row t uses only bars <= t.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _hm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def add_features(df: pd.DataFrame, cfg) -> pd.DataFrame:
    f = cfg.features
    out = df.copy()
    idx = out.index
    minutes = pd.Series(idx.hour * 60 + idx.minute, index=idx)
    out["minute_of_day"] = minutes
    out["session_date"] = idx.date

    rth_start, rth_end = _hm(cfg.session.rth_start), _hm(cfg.session.rth_end)
    out["rth"] = (minutes >= rth_start) & (minutes < rth_end)

    # True range / ATR
    prev_close = out["close"].shift(1)
    tr = pd.concat(
        [out["high"] - out["low"], (out["high"] - prev_close).abs(), (out["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    out["atr"] = tr.rolling(f.atr_period, min_periods=f.atr_period).mean()
    # Volatility baseline = median ATR at the SAME minute of the session over the last N days.
    # (A plain rolling median mixes in quiet overnight bars and makes every open look "extreme".)
    days = f.vol_baseline_days
    rth_mask = (minutes >= _hm(cfg.session.rth_start)) & (minutes < _hm(cfg.session.rth_end))
    atr_rth = out.loc[rth_mask, "atr"]
    base = atr_rth.groupby(minutes[rth_mask]).transform(
        lambda s: s.rolling(days, min_periods=max(5, days // 4)).median())
    out["atr_ratio"] = (out["atr"] / base.reindex(out.index)).where(rth_mask)

    # Trend
    out["ema_fast"] = out["close"].ewm(span=f.ema_fast, adjust=False).mean()
    out["ema_slow"] = out["close"].ewm(span=f.ema_slow, adjust=False).mean()
    out["ema_slow_slope"] = out["ema_slow"] - out["ema_slow"].shift(f.slope_lookback)

    # Session VWAP (RTH bars only; NaN outside RTH)
    tp = (out["high"] + out["low"] + out["close"]) / 3.0
    vol = out["volume"].where(out["rth"], 0.0).astype(float)
    pv = (tp * vol).groupby(out["session_date"]).cumsum()
    cv = vol.groupby(out["session_date"]).cumsum()
    out["vwap"] = (pv / cv.replace(0, np.nan)).where(out["rth"])

    # Opening range: known only once the window has fully closed
    or_end = rth_start + cfg.strategy.opening_range_minutes
    in_or = (minutes >= rth_start) & (minutes < or_end)
    hi = out["high"].where(in_or).groupby(out["session_date"]).transform("max")
    lo = out["low"].where(in_or).groupby(out["session_date"]).transform("min")
    n_or = in_or.groupby(out["session_date"]).transform("sum")
    complete = n_or >= max(1, int(cfg.strategy.opening_range_minutes * 0.8))
    available = (minutes >= or_end) & out["rth"] & complete
    out["or_high"] = hi.where(available)
    out["or_low"] = lo.where(available)
    out["or_mid"] = (out["or_high"] + out["or_low"]) / 2.0
    out["bar_range"] = out["high"] - out["low"]
    return out
