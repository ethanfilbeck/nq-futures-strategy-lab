"""Contract-roll discontinuities in unadjusted continuous futures series.

A Databento continuous symbol like `MNQ.v.0` splices quarterly contracts WITHOUT back-adjustment, so the
series jumps by the calendar spread on each roll. The gap is positive for equity index futures (positive
carry) and scales with interest rates: near zero in 2020-2021, about 1% a quarter at 2023-2025 rates.

Any strategy that HOLDS ACROSS A ROLL records that gap as profit it would never have received, because a
trader holding one contract experiences no jump. This inflates every long overnight strategy. It is what
the November 2026 audit found in H8 (docs/AUDIT_2026_11_ROLLS.md).

The reliable fix is the `symbol` column, which `data.fetch_databento` now keeps: roll dates are then exact.
`detect` below is the fallback for files downloaded before that, and it is a HEURISTIC - see its docstring.
"""
from __future__ import annotations

import pandas as pd

from .data import times

QUARTERLY = (3, 6, 9, 12)


def detect(bars: pd.DataFrame, quarterly_only: bool = True) -> dict[pd.Timestamp, float]:
    """Suspected roll minutes mapped to their fractional gap. HEURISTIC, for files without a symbol column.

    Per expiry month, the largest positive one-minute move in the overnight session (18:00-08:00 ET) whose
    volume is at or below the file's 75th percentile. Rolls are quiet level shifts, so volume screens out
    news. Known weakness: when carry is near zero the real gap is smaller than ordinary overnight noise, so
    low-rate periods give false positives of negligible size. Prefer `from_symbols` whenever the column exists.
    """
    t = times(bars)
    ret = bars["close"].pct_change()
    quiet = bars["volume"] <= bars["volume"].quantile(0.75)
    overnight = (t.hour >= 18) | (t.hour < 8)
    best: dict[tuple[int, int], tuple[pd.Timestamp, float]] = {}
    for ts, r in ret[overnight & (ret > 0) & quiet].dropna().items():
        if quarterly_only and ts.month not in QUARTERLY:
            continue
        key = (ts.year, ts.month)
        if key not in best or r > best[key][1]:
            best[key] = (ts, float(r))
    return {ts: gap for ts, gap in best.values()}


def from_symbols(bars: pd.DataFrame) -> dict[pd.Timestamp, float]:
    """Exact roll minutes from a `symbol` column: the first bar of each new contract, and its gap."""
    if "symbol" not in bars.columns:
        raise ValueError("no 'symbol' column - re-download with data.fetch_databento, or use detect()")
    sym = bars["symbol"]
    changed = sym != sym.shift(1)
    changed.iloc[0] = False
    out = {}
    prev_close = bars["close"].shift(1)
    for ts in bars.index[changed]:
        p = float(prev_close.loc[ts])
        if p:
            out[ts] = float(bars.loc[ts, "open"]) / p - 1.0
    return out


def spans(entry_ts, exit_ts, rolls: dict[pd.Timestamp, float]) -> list[float]:
    """Gaps of every roll strictly after entry_ts and at or before exit_ts. Empty means the hold is clean."""
    return [g for ts, g in rolls.items() if entry_ts < ts <= exit_ts]


def adjust_exit(exit_px: float, entry_ts, exit_ts, rolls: dict[pd.Timestamp, float]) -> float:
    """`exit_px` with any roll gaps inside the hold divided out: what one held contract actually did."""
    factor = 1.0
    for gap in spans(entry_ts, exit_ts, rolls):
        factor *= 1.0 + gap
    return exit_px / factor
