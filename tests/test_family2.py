"""Mechanics of the pre-registered family-2 strategies (no performance claims)."""
from pathlib import Path

import numpy as np
import pandas as pd

from nq_bot.config import load_settings
from nq_bot.contracts import SPECS
from nq_bot.family2 import LiquiditySweep, VwapPullback, overnight_drift_trades

ROOT = Path(__file__).resolve().parents[1]
TZ = "America/New_York"


def cfg():
    return load_settings(ROOT / "config/settings.yaml")


def row(t, o, h, l, c, pdh=100.0, pdl=50.0, **kw):
    r = dict(open=o, high=h, low=l, close=c, minute_of_day=t.hour * 60 + t.minute, session_date=t.date(),
             rth=True, pdh=pdh, pdl=pdl, vwap=kw.get("vwap", 75.0), atr=kw.get("atr", 4.0))
    return r


def ts(hm):
    return pd.Timestamp(f"2025-03-04 {hm}", tz=TZ)


def test_sweep_short_signal_and_stop():
    s = LiquiditySweep(cfg(), SPECS["MNQ"])
    s.observe(row(ts("10:00"), 99, 103, 98, 101))      # sweeps PDH by 3, closes above
    assert s.evaluate(None, "") is None
    s.observe(row(ts("10:01"), 101, 104, 99, 99.5))    # new extreme 104, closes back below PDH
    sig = s.evaluate(None, "")
    assert sig and sig.side == -1
    assert sig.stop == 107.5                           # 104 + 2 = 106 is only 6.5 pts away -> widened to the 8-pt minimum
    assert sig.target == round(99.5 - 2 * (sig.stop - 99.5), 2)


def test_sweep_min_stop_and_first_sweep_only():
    s = LiquiditySweep(cfg(), SPECS["MNQ"])
    for i, hm in enumerate(["10:00", "10:01", "10:02", "10:03", "10:04"]):
        s.observe(row(ts(hm), 101, 103, 100.5, 101.5))  # sweeps, never reclaims within 5 bars
        assert s.evaluate(None, "") is None
    s.observe(row(ts("10:05"), 101, 104, 98, 98))      # reclaim after the window: first sweep already used
    assert s.evaluate(None, "") is None


def test_sweep_needs_two_points_and_window():
    s = LiquiditySweep(cfg(), SPECS["MNQ"])
    s.observe(row(ts("10:00"), 99, 101.5, 98, 99))     # only 1.5 pts through: not a sweep
    assert s.evaluate(None, "") is None
    s2 = LiquiditySweep(cfg(), SPECS["MNQ"])
    s2.observe(row(ts("15:01"), 99, 103, 98, 99))      # sweep + reclaim after 15:00: no signal
    assert s2.evaluate(None, "") is None


def test_vwap_pullback_long_and_once_per_day():
    v = VwapPullback(cfg(), SPECS["MNQ"])
    r = row(ts("10:30"), 74, 80, 74.5, 79, vwap=75.0, atr=4.0)   # touches VWAP, closes above & up
    sig = v.evaluate(r, "bullish")
    assert sig and sig.side == 1
    assert sig.stop == 71.0                            # min(74.5, 75) - 2 = 72.5 -> widened to close-8 = 71
    v.mark_traded(r["session_date"], 1)
    assert v.evaluate(r, "bullish") is None
    assert v.evaluate(row(ts("09:50"), 74, 80, 74.5, 79), "bullish") is None   # before 10:00
    assert v.evaluate(r, "sideways") is None


def test_overnight_drift_fills_and_stop():
    frames = []
    for i, d in enumerate(pd.bdate_range("2025-01-06", periods=14)):
        idx = pd.date_range(f"{d.date()} 01:50", periods=80, freq="1min", tz=TZ)
        px = 100.0 + np.arange(80) * 0.25
        frames.append(pd.DataFrame({"open": px, "high": px + 0.25, "low": px - 0.25, "close": px, "volume": 1.0}, index=idx))
    bars = pd.concat(frames)
    t = overnight_drift_trades(bars)
    assert len(t) == 14 - 10                            # needs 10 prior sessions for the stop
    first = t.iloc[0]
    assert first["exit_kind"] == "time"
    # entry 02:00 open = 100+10*0.25 = 102.5 (+1 tick), exit 03:00 open = 117.5 (-1 tick)
    assert first["entry_price"] == 102.75 and first["exit_price"] == 117.25
    assert first["net"] == round((117.25 - 102.75) * 2 - 1.24, 2)
