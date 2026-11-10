"""Mechanics of the Family 4 simulators on synthetic sessions."""
import pandas as pd

from nq_bot import family4 as f4
from tests.test_family3 import make_days


def test_pre_holiday_days_come_from_the_session_calendar():
    days = [d for d in pd.bdate_range("2024-07-01", "2024-07-12").date if str(d) != "2024-07-04"]
    s = f4.Session4(make_days(days, lambda di, m: (100, 100.25, 99.75, 100)))
    assert [str(d) for d in f4.pre_holidays(s)] == ["2024-07-03"]
    (t,), _ = f4.run_h10(s)
    assert str(t.entry_ts.date()) == "2024-07-02" and str(t.exit_ts.date()) == "2024-07-03"


def test_h11_trades_opening_hour_direction_after_high_range_day_only():
    days = pd.bdate_range("2024-01-01", periods=24).date

    def px(di, m):
        if di == 22:                                   # one very wide day
            return 1000, 1100, 900, 1000
        if di == 23:                                   # next day: opening hour rises, then keeps rising
            p = 1000 + m * 0.5
            return p, p + 0.25, p - 0.25, p
        return 1000, 1002, 998, 1000                   # quiet days
    s = f4.Session4(make_days(days, px))
    trades = f4.run_h11(s)
    assert len(trades) == 1
    t = trades[0]
    assert t.side == 1 and t.kind == "time" and str(t.entry_ts.time()) == "10:30:00"
    assert t.exit > t.entry
