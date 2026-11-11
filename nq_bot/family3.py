"""Strategy Family 3 (pre-registered in docs/PREREG_FAMILY3.md): turn of the month (H6), overnight-gap
reversal (H7), pre-FOMC drift (H8). Research code: simulates 1-MNQ trades on 1-minute bars with the
pre-registered fills and costs. Nothing here is wired into the live/paper bot."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from .data import times

TICK = 0.25
PT_VALUE = 2.0          # MNQ $/point
COMMISSION_RT = 1.24    # $0.62 per side

# Scheduled FOMC statement days (14:00 ET) inside the training data, from federalreserve.gov
# fomccalendars.htm and fomchistorical2019/2020.htm (read 2026-11-09). Unscheduled 2020 actions excluded.
FOMC_DAYS = [
    "2019-06-19", "2019-07-31", "2019-09-18", "2019-10-30", "2019-12-11",
    "2020-01-29", "2020-04-29", "2020-06-10", "2020-07-29", "2020-09-16", "2020-11-05", "2020-12-16",
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16", "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
    "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15", "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14", "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
]


@dataclass
class Trade:
    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp
    side: int
    entry: float
    exit: float
    kind: str

    def net(self, extra_ticks: int = 0) -> float:
        """Net $ for 1 MNQ. Base fills already include 1 tick per market side; extra_ticks adds more per side."""
        gross = (self.exit - self.entry) * self.side * PT_VALUE
        return gross - COMMISSION_RT - extra_ticks * TICK * PT_VALUE * self._market_sides()

    def _market_sides(self) -> float:
        return 1.0 if self.kind == "target" else 2.0   # limit target exit has no slippage


class Session:
    """Per-trading-day lookups on ET-indexed 1-minute bars."""

    def __init__(self, bars: pd.DataFrame):
        self.bars = bars
        t = times(bars)
        mins = t.hour * 60 + t.minute
        rth = (mins >= 570) & (mins < 960) & (t.weekday < 5)
        counts = pd.Series(1, index=t[rth]).groupby(t[rth].date).sum()
        self.days = [d for d, n in counts.items() if n >= 300]
        self.day_index = {d: i for i, d in enumerate(self.days)}
        self._minute: dict[str, dict] = {}
        for hm in ("09:30", "09:31", "13:55", "14:00", "15:55", "15:59"):
            h, m = map(int, hm.split(":"))
            sel = bars[(t.hour == h) & (t.minute == m)]
            self._minute[hm] = {ts.date(): (ts, row) for ts, row in zip(sel.index, sel.itertuples(index=False))}

    def bar(self, day, hm):
        return self._minute[hm].get(day)

    def path(self, start_ts, end_ts):
        """Bars strictly after start_ts up to and including end_ts."""
        b = self.bars
        return b[(b.index > start_ts) & (b.index <= end_ts)]


def _stop_scan(path: pd.DataFrame, side: int, stop: float):
    """First bar that touches the stop (long: low <= stop). Returns (ts, fill) or None."""
    if side > 0:
        hit = path[path["low"] <= stop]
        if hit.empty:
            return None
        ts, r = hit.index[0], hit.iloc[0]
        return ts, min(stop, r["open"]) - TICK
    hit = path[path["high"] >= stop]
    if hit.empty:
        return None
    ts, r = hit.index[0], hit.iloc[0]
    return ts, max(stop, r["open"]) + TICK


def _hold(s: Session, entry_ts, entry_px, exit_ts, exit_px_raw, stop_frac):
    """Long hold with a disaster stop. entry_px already includes the entry tick."""
    stop = entry_px * (1 - stop_frac)
    hit = _stop_scan(s.path(entry_ts, exit_ts), 1, stop)
    if hit:
        return Trade(entry_ts, hit[0], 1, entry_px, hit[1], "stop")
    return Trade(entry_ts, exit_ts, 1, entry_px, exit_px_raw - TICK, "time")


# ---------------------------------------------------------------- H6 turn of the month
def tom_windows(s: Session):
    """(day -2, day +3) pairs for every month boundary in the data."""
    out: list[tuple[date, date]] = []
    d = s.days
    for i in range(1, len(d) - 3):
        if d[i].month != d[i + 1].month:            # d[i] is day -1, d[i+1] is day +1
            out.append((d[i - 1], d[i + 3]))
    return out


def run_h6(s: Session):
    trades, skipped = [], 0
    for start, end in tom_windows(s):
        a, b = s.bar(start, "15:59"), s.bar(end, "15:59")
        if not a or not b:
            skipped += 1
            continue
        trades.append(_hold(s, a[0], a[1].close + TICK, b[0], b[1].close, 0.05))
    return trades, skipped


def h6_benchmark_pool(s: Session):
    """Same 5-session close-to-close long holds started on days whose window avoids every ToM day -1..+3."""
    tom_days = set()
    for start, end in tom_windows(s):
        i, j = s.day_index[start], s.day_index[end]
        tom_days.update(s.days[i + 1: j + 1])
    pool = []
    for i in range(len(s.days) - 5):
        if s.days[i] in tom_days or any(x in tom_days for x in s.days[i + 1: i + 6]):
            continue
        a, b = s.bar(s.days[i], "15:59"), s.bar(s.days[i + 5], "15:59")
        if a and b:
            pool.append(_hold(s, a[0], a[1].close + TICK, b[0], b[1].close, 0.05).net())
    return np.array(pool)


# ---------------------------------------------------------------- H7 overnight-gap reversal
def run_h7(s: Session):
    trades: list = []
    gaps: list = []
    skipped_filled = 0
    for i in range(1, len(s.days)):
        d, p = s.days[i], s.days[i - 1]
        o, c = s.bar(d, "09:30"), s.bar(p, "15:59")
        if not o or not c:
            continue
        gap = o[1].open - c[1].close
        hist = gaps[-20:]
        gaps.append(gap)
        if len(hist) < 10:
            continue
        sd = float(np.std(hist, ddof=1))
        if sd <= 0 or abs(gap) / sd < 1.0 or abs(gap) < 10:
            continue
        e, x = s.bar(d, "09:31"), s.bar(d, "15:55")
        if not e or not x:
            continue
        side = -1 if gap > 0 else 1
        entry = e[1].open + side * TICK
        target = c[1].close
        if (target - entry) * side <= 0:            # gap already filled at entry: no trade
            skipped_filled += 1
            continue
        stop = entry - side * max(10.0, 0.5 * abs(gap))
        path = s.bars[(s.bars.index >= e[0]) & (s.bars.index < x[0])]
        tr = None
        for ts, r in zip(path.index, path.itertuples(index=False)):
            first = ts == e[0]
            if side > 0 and r.low <= stop:
                tr = Trade(e[0], ts, side, entry, (stop if first else min(stop, r.open)) - TICK, "stop")
            elif side < 0 and r.high >= stop:
                tr = Trade(e[0], ts, side, entry, (stop if first else max(stop, r.open)) + TICK, "stop")
            elif side > 0 and r.high >= target + TICK:
                tr = Trade(e[0], ts, side, entry, target, "target")
            elif side < 0 and r.low <= target - TICK:
                tr = Trade(e[0], ts, side, entry, target, "target")
            if tr:
                break
        if tr is None:
            tr = Trade(e[0], x[0], side, entry, x[1].open - side * TICK, "time")
        trades.append(tr)
    return trades, skipped_filled


# ---------------------------------------------------------------- H8 pre-FOMC drift
HOLDOUT_FOMC_DAYS = ["2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10", "2026-01-28", "2026-03-18",
                     "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28"]


def run_h8(s: Session, events=None):
    trades, skipped = [], 0
    for ds in (events or FOMC_DAYS):
        e = pd.Timestamp(ds).date()
        if e not in s.day_index or s.day_index[e] == 0:
            skipped += 1
            continue
        p = s.days[s.day_index[e] - 1]
        a, b = s.bar(p, "14:00"), s.bar(e, "13:55")
        if not a or not b:
            skipped += 1
            continue
        trades.append(_hold(s, a[0], a[1].open + TICK, b[0], b[1].close, 0.03))
    return trades, skipped


def h8_benchmark_pool(s: Session):
    fomc = {pd.Timestamp(x).date() for x in FOMC_DAYS}
    pool = []
    for i in range(len(s.days) - 1):
        p, e = s.days[i], s.days[i + 1]
        if p in fomc or e in fomc:
            continue
        a, b = s.bar(p, "14:00"), s.bar(e, "13:55")
        if a and b:
            pool.append(_hold(s, a[0], a[1].open + TICK, b[0], b[1].close, 0.03).net())
    return np.array(pool)


# ---------------------------------------------------------------- statistics
def stats(trades, extra_ticks=0):
    pnl = np.array([t.net(extra_ticks) for t in trades])
    if len(pnl) == 0:
        return {"n": 0}
    wins, losses = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    sd = pnl.std(ddof=1) if len(pnl) > 1 else float("nan")
    return {"n": len(pnl), "net": float(pnl.sum()), "mean": float(pnl.mean()),
            "pf": float(wins / losses) if losses > 0 else float("inf"),
            "t": float(pnl.mean() / (sd / np.sqrt(len(pnl)))) if sd and sd > 0 else float("nan"),
            "win_rate": float((pnl > 0).mean())}


def by_year(trades):
    out: dict = {}
    for t in trades:
        out[t.entry_ts.year] = out.get(t.entry_ts.year, 0.0) + t.net()
    return dict(sorted(out.items()))


def since_2021(trades):
    return float(sum(t.net() for t in trades if t.entry_ts.year >= 2021))


def bootstrap_p95(pool, n, draws=2000, seed=7):
    rng = np.random.default_rng(seed)
    means = rng.choice(pool, size=(draws, n), replace=True).mean(axis=1)
    return float(np.percentile(means, 95)), float(means.mean())
