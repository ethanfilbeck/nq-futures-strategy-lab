"""Rule-based market-regime classifier.

Measurable criteria only: EMA alignment, EMA slope, price vs VWAP, ATR vs its baseline.
An ML classifier can replace this later ONLY if it beats it out-of-sample.
"""
from __future__ import annotations

import math

BULLISH, BEARISH, SIDEWAYS = "bullish", "bearish", "sideways"
HIGH_VOL, LOW_VOL, NO_TRADE = "high_volatility", "low_volatility", "no_trade"


def _bad(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def classify(row, cfg) -> str:
    r = cfg.regime
    needed = ("atr", "atr_ratio", "ema_fast", "ema_slow", "ema_slow_slope", "vwap")
    if any(_bad(row[k]) for k in needed) or not row["rth"]:
        return NO_TRADE
    ratio = row["atr_ratio"]
    if ratio >= r.extreme_vol_ratio:
        return NO_TRADE
    if ratio <= r.low_vol_ratio:
        return LOW_VOL

    up = row["ema_fast"] > row["ema_slow"] and row["ema_slow_slope"] >= r.min_slope_points and row["close"] > row["vwap"]
    down = row["ema_fast"] < row["ema_slow"] and row["ema_slow_slope"] <= -r.min_slope_points and row["close"] < row["vwap"]
    trend = BULLISH if up else BEARISH if down else SIDEWAYS
    if ratio >= r.high_vol_ratio and trend == SIDEWAYS:
        return HIGH_VOL
    return trend
