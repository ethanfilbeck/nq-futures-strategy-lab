"""Mechanics of the Family 3 simulators on small synthetic sessions (no market data needed)."""
import numpy as np
import pandas as pd

from nq_bot import family3 as f3

TZ = "America/New_York"


def make_days(days, price_fn):
    """One-minute RTH bars 09:30-15:59 for each day; price_fn(day_i, minute_i) -> (open, high, low, close)."""
    rows = []
    for di, d in enumerate(days):
        for m in range(390):
            ts = pd.Timestamp(d, tz=TZ) + pd.Timedelta(minutes=570 + m)
            o, h, l, c = price_fn(di, m)
            rows.append((ts, o, h, l, c, 10.0))
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"]).set_index("ts")
    return df


def flat(px):
    return lambda di, m: (px, px + 0.25, px - 0.25, px)


def test_tom_windows_pick_day_minus2_and_plus3():
    days = pd.bdate_range("2024-01-24", "2024-02-08").date
    s = f3.Session(make_days(days, flat(100.0)))
    (start, end), = f3.tom_windows(s)
    assert str(start) == "2024-01-30" and str(end) == "2024-02-05"   # Jan 31 is day -1; Feb 5 is day +3


def test_h7_gap_up_short_hits_gap_fill_target():
    days = pd.bdate_range("2024-03-01", periods=25).date

    def px(di, m):
        if di < 24:                                    # quiet history, small alternating gaps
            base = 1000 + (2 if di % 2 else -2)
            return base, base + 1, base - 1, base
        if m == 0:                                     # big gap up on the last day
            return 1060, 1061, 1059, 1060
        p = max(1060 - m, 990)                         # drifts back down through the prior close
        return p, p + 0.5, p - 0.5, p
    s = f3.Session(make_days(days, px))
    trades, _ = f3.run_h7(s)
    t = trades[-1]
    assert t.side == -1 and t.kind == "target" and t.exit == 1002.0   # previous 15:59 close (day 23) = 1002
    assert t.entry == 1059 - 0.25                                     # 09:31 open, 1 tick worse


def test_stop_counts_first_when_both_touched_in_one_bar():
    days = pd.bdate_range("2024-03-01", periods=25).date

    def px(di, m):
        if di < 24:
            base = 1000 + (2 if di % 2 else -2)
            return base, base + 1, base - 1, base
        if m == 0:
            return 1060, 1061, 1059, 1060
        if m == 5:                                     # one wild bar hits both stop and target
            return 1050, 1200, 900, 1050
        return 1050, 1050.5, 1049.5, 1050
    s = f3.Session(make_days(days, px))
    t = f3.run_h7(s)[0][-1]
    assert t.kind == "stop" and t.exit > t.entry


def test_net_and_slippage_accounting():
    t = f3.Trade(None, None, 1, 100.0, 110.0, "time")
    assert t.net() == 10 * 2 - 1.24
    assert t.net(extra_ticks=1) == 10 * 2 - 1.24 - 2 * 0.25 * 2      # two market sides
    assert f3.Trade(None, None, -1, 110.0, 100.0, "target").net(1) == 20 - 1.24 - 0.5   # one market side
