"""Schedule logic of the H8 forward paper tracker (no IB needed)."""
from datetime import date

import pandas as pd

from nq_bot.fomc_paper import decide, due_today, fomc_events, next_window, prev_weekday, window_for

TZ = "America/New_York"


def ts(s):
    return pd.Timestamp(s, tz=TZ)


def test_events_come_from_calendar():
    ev = fomc_events("config/events.csv")
    assert date(2026, 12, 9) in ev and ev == sorted(ev)


def test_window_is_2pm_day_before_to_1355_statement_day():
    w = window_for(date(2026, 12, 9))
    assert w.entry == ts("2026-12-08 14:00") and w.exit == ts("2026-12-09 13:55")
    assert prev_weekday(date(2027, 3, 1)) == date(2027, 2, 26)            # Monday event -> Friday entry


def test_decisions():
    w = window_for(date(2026, 12, 9))
    assert decide(ts("2026-12-08 10:00"), w, False, 0) == "wait"
    assert decide(ts("2026-12-08 14:00:20"), w, False, 0) == "enter"
    assert decide(ts("2026-12-08 14:06"), w, False, 0) == "skip"            # never enter late
    assert decide(ts("2026-12-08 22:00"), w, True, 1) == "hold"
    assert decide(ts("2026-12-09 13:55"), w, True, 1) == "exit"
    assert decide(ts("2026-12-09 16:00"), w, True, 1) == "exit"             # late exit if the PC was off
    assert decide(ts("2026-12-08 22:00"), w, True, 0) == "stopped"
    assert decide(ts("2026-12-08 14:00"), w, False, 1) == "refuse"          # someone else's position
    assert decide(ts("2026-12-08 14:00"), None, False, 0) == "done"


def test_next_window_moves_on_after_exit():
    ev = [date(2026, 12, 9), date(2027, 1, 27)]
    assert next_window(ts("2026-12-09 13:54"), ev).event == date(2026, 12, 9)
    assert next_window(ts("2026-12-09 13:55"), ev).event == date(2027, 1, 27)


def test_daily_task_only_starts_on_entry_day_or_open_trade():
    ev = [date(2026, 12, 9)]
    assert due_today(ts("2026-12-08 13:40"), ev, False)            # entry day, before 14:00 ET
    assert not due_today(ts("2026-12-08 14:10"), ev, False)        # too late to enter
    assert not due_today(ts("2026-12-07 13:40"), ev, False)        # day before entry day
    assert not due_today(ts("2026-11-20 13:40"), ev, False)        # ordinary day
    assert due_today(ts("2026-12-09 09:00"), ev, True)             # trade open (e.g. after a reboot): resume
