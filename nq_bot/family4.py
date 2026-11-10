"""Strategy Family 4 (pre-registered in docs/PREREG_FAMILY4.md): macro announcement days (H9), pre-holiday (H10),
opening-hour trend after a high-range day (H11). Research code only; reuses the Family 3 fill/cost machinery."""
from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from . import family3 as f3
from .family3 import TICK, Trade

# BLS release days (08:30 ET), from bls.gov/bls/news-release/cpi.htm and empsit.htm, read 2026-11-09.
CPI_DAYS = """2019-05-10 2019-06-12 2019-07-11 2019-08-13 2019-09-12 2019-10-10 2019-11-13 2019-12-11
2020-01-14 2020-02-13 2020-03-11 2020-04-10 2020-05-12 2020-06-10 2020-07-14 2020-08-12 2020-09-11 2020-10-13
2020-11-12 2020-12-10 2021-01-13 2021-02-10 2021-03-10 2021-04-13 2021-05-12 2021-06-10 2021-07-13 2021-08-11
2021-09-14 2021-10-13 2021-11-10 2021-12-10 2022-01-12 2022-02-10 2022-03-10 2022-04-12 2022-05-11 2022-06-10
2022-07-13 2022-08-10 2022-09-13 2022-10-13 2022-11-10 2022-12-13 2023-01-12 2023-02-14 2023-03-14 2023-04-12
2023-05-10 2023-06-13 2023-07-12 2023-08-10 2023-09-13 2023-10-12 2023-11-14 2023-12-12 2024-01-11 2024-02-13
2024-03-12 2024-04-10 2024-05-15 2024-06-12 2024-07-11 2024-08-14 2024-09-11 2024-10-10 2024-11-13 2024-12-11
2025-01-15 2025-02-12 2025-03-12 2025-04-10 2025-05-13 2025-06-11""".split()
NFP_DAYS = """2019-05-03 2019-06-07 2019-07-05 2019-08-02 2019-09-06 2019-10-04 2019-11-01 2019-12-06
2020-01-10 2020-02-07 2020-03-06 2020-04-03 2020-05-08 2020-06-05 2020-07-02 2020-08-07 2020-09-04 2020-10-02
2020-11-06 2020-12-04 2021-01-08 2021-02-05 2021-03-05 2021-04-02 2021-05-07 2021-06-04 2021-07-02 2021-08-06
2021-09-03 2021-10-08 2021-11-05 2021-12-03 2022-01-07 2022-02-04 2022-03-04 2022-04-01 2022-05-06 2022-06-03
2022-07-08 2022-08-05 2022-09-02 2022-10-07 2022-11-04 2022-12-02 2023-01-06 2023-02-03 2023-03-10 2023-04-07
2023-05-05 2023-06-02 2023-07-07 2023-08-04 2023-09-01 2023-10-06 2023-11-03 2023-12-08 2024-01-05 2024-02-02
2024-03-08 2024-04-05 2024-05-03 2024-06-07 2024-07-05 2024-08-02 2024-09-06 2024-10-04 2024-11-01 2024-12-06
2025-01-10 2025-02-07 2025-03-07 2025-04-04 2025-05-02 2025-06-06""".split()

STOP_FRAC = 0.03


class Session4(f3.Session):
    def __init__(self, bars: pd.DataFrame):
        super().__init__(bars)
        t = bars.index
        for hm in ("10:29", "10:30"):
            h, m = map(int, hm.split(":"))
            sel = bars[(t.hour == h) & (t.minute == m)]
            self._minute[hm] = {ts.date(): (ts, row) for ts, row in zip(sel.index, sel.itertuples(index=False))}
        mins = t.hour * 60 + t.minute
        rth = bars[(mins >= 570) & (mins < 960)]
        g = rth.groupby(rth.index.date)
        self.rth_range = (g["high"].max() - g["low"].min()).to_dict()
        open_hr = rth[(rth.index.hour * 60 + rth.index.minute) < 630]
        go = open_hr.groupby(open_hr.index.date)
        self.oh_high, self.oh_low = go["high"].max().to_dict(), go["low"].min().to_dict()


def _close_to_close(s, d_prev, d):
    a, b = s.bar(d_prev, "15:59"), s.bar(d, "15:59")
    if not a or not b:
        return None
    return f3._hold(s, a[0], a[1].close + TICK, b[0], b[1].close, STOP_FRAC)


def macro_days(s):
    fomc = {pd.Timestamp(x).date() for x in f3.FOMC_DAYS}
    return sorted({pd.Timestamp(x).date() for x in CPI_DAYS + NFP_DAYS} - fomc)


def run_h9(s):
    trades, skipped = [], 0
    for d in macro_days(s):
        i = s.day_index.get(d)
        if i is None or i == 0:
            skipped += 1
            continue
        t = _close_to_close(s, s.days[i - 1], d)
        if t is None:
            skipped += 1
            continue
        trades.append(t)
    return trades, skipped


def pre_holidays(s):
    out = []
    trading = set(s.days)
    for d in s.days:
        nxt = d + timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += timedelta(days=1)
        if nxt <= s.days[-1] and nxt not in trading:
            out.append(d)
    return out


def run_h10(s):
    trades, skipped = [], 0
    for d in pre_holidays(s):
        i = s.day_index[d]
        if i == 0:
            skipped += 1
            continue
        t = _close_to_close(s, s.days[i - 1], d)
        if t is None:
            skipped += 1
            continue
        trades.append(t)
    return trades, skipped


def one_day_pool(s, exclude):
    """1-session close-to-close long holds on trading days not in `exclude`."""
    pool = []
    for i in range(1, len(s.days)):
        d = s.days[i]
        if d in exclude:
            continue
        t = _close_to_close(s, s.days[i - 1], d)
        if t is not None:
            pool.append(t.net())
    return np.array(pool)


def run_h11(s):
    trades = []
    for i in range(21, len(s.days)):
        d, p = s.days[i], s.days[i - 1]
        hist = [s.rth_range[x] for x in s.days[max(0, i - 21): i - 1] if x in s.rth_range]
        if len(hist) < 10 or p not in s.rth_range:
            continue
        if s.rth_range[p] <= 1.5 * float(np.median(hist)):
            continue
        o, c, e, x = s.bar(d, "09:30"), s.bar(d, "10:29"), s.bar(d, "10:30"), s.bar(d, "15:55")
        if not all((o, c, e, x)) or d not in s.oh_high:
            continue
        move = c[1].close - o[1].open
        if move == 0:
            continue
        side = 1 if move > 0 else -1
        entry = e[1].open + side * TICK
        raw = s.oh_low[d] - 1 if side > 0 else s.oh_high[d] + 1
        stop = min(raw, entry - 10) if side > 0 else max(raw, entry + 10)
        path = s.bars[(s.bars.index >= e[0]) & (s.bars.index < x[0])]
        tr = None
        for ts, r in zip(path.index, path.itertuples(index=False)):
            first = ts == e[0]
            if side > 0 and r.low <= stop:
                tr = Trade(e[0], ts, side, entry, (stop if first else min(stop, r.open)) - TICK, "stop")
            elif side < 0 and r.high >= stop:
                tr = Trade(e[0], ts, side, entry, (stop if first else max(stop, r.open)) + TICK, "stop")
            if tr:
                break
        trades.append(tr or Trade(e[0], x[0], side, entry, x[1].open - side * TICK, "time"))
    return trades
