"""Sanity-check a 1-minute bar CSV before trusting any backtest built on it. Offline; reads only.

    py scripts\\validate_data.py data\\mnq_train.csv [--tick 0.25]

Hard errors (exit 1): unsorted or duplicate timestamps, missing/non-positive prices, high/low inconsistent
with open/close, negative volume. Warnings: prices off the tick grid, very large one-bar moves, long gaps
inside regular trading hours. A continuous-contract file (e.g. MNQ.v.0) is a research series, not a
tradable contract: roll days can show jumps, which is why big moves are warnings and not errors.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def validate(bars: pd.DataFrame, tick: float = 0.25, max_move_pct: float = 3.0) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a DataFrame indexed by bar-open time with open/high/low/close/volume."""
    errors, warnings = [], []
    need = ["open", "high", "low", "close", "volume"]
    missing = [c for c in need if c not in bars.columns]
    if missing:
        return [f"missing columns: {missing}"], warnings
    if len(bars) == 0:
        return ["no rows"], warnings
    idx = bars.index
    if not idx.is_monotonic_increasing:
        errors.append("timestamps are not sorted ascending")
    dup = int(idx.duplicated().sum())
    if dup:
        errors.append(f"{dup} duplicate timestamps")
    px = bars[["open", "high", "low", "close"]]
    n_nan = int(px.isna().any(axis=1).sum())
    if n_nan:
        errors.append(f"{n_nan} rows with a missing price")
    n_nonpos = int((px <= 0).any(axis=1).sum())
    if n_nonpos:
        errors.append(f"{n_nonpos} rows with a zero or negative price")
    bad_hl = int(((bars["high"] < px[["open", "close"]].max(axis=1)) | (bars["low"] > px[["open", "close"]].min(axis=1))
                  | (bars["high"] < bars["low"])).sum())
    if bad_hl:
        errors.append(f"{bad_hl} rows where high/low do not contain open/close")
    n_negvol = int((bars["volume"] < 0).sum())
    if n_negvol:
        errors.append(f"{n_negvol} rows with negative volume")

    off = np.abs(px / tick - (px / tick).round()) > 1e-6
    n_off = int(off.any(axis=1).sum())
    if n_off:
        warnings.append(f"{n_off} rows with a price off the {tick} tick grid")
    move = (bars["close"].pct_change().abs() * 100).dropna()
    big = move[move > max_move_pct]
    if len(big):
        warnings.append(f"{len(big)} one-bar moves over {max_move_pct}% (first: {big.index[0]}, {big.iloc[0]:.1f}%) "
                        "- check for roll jumps or bad prints")
    if getattr(idx, "tz", None) is not None and idx.is_monotonic_increasing:
        et = idx.tz_convert("America/New_York")
        rth = (et.hour * 60 + et.minute >= 570) & (et.hour * 60 + et.minute < 960) & (et.dayofweek < 5)
        t = et[rth]
        gaps = pd.Series(t[1:] - t[:-1], index=t[1:])
        same_day = pd.Series(t[1:].date == t[:-1].date, index=t[1:])
        long = gaps[(gaps > pd.Timedelta(minutes=15)) & same_day]
        if len(long):
            warnings.append(f"{len(long)} gaps over 15 min inside regular hours (first ends {long.index[0]})")
    return errors, warnings


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv")
    ap.add_argument("--tick", type=float, default=0.25)
    args = ap.parse_args()
    from nq_bot.data import load_csv
    bars = load_csv(args.csv)
    errors, warnings = validate(bars, tick=args.tick)
    print(f"{args.csv}: {len(bars):,} bars, {bars.index[0]} -> {bars.index[-1]}")
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    if errors:
        sys.exit(1)
    print("OK: no hard errors." + (f" {len(warnings)} warning(s) to review." if warnings else ""))


if __name__ == "__main__":
    main()
