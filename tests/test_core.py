from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from nq_bot.backtest import run_backtest
from nq_bot.broker.base import BracketRequest
from nq_bot.broker.sim import SimBroker
from nq_bot.config import load_settings, override
from nq_bot.contracts import SPECS, front_month, third_friday
from nq_bot.data import synthetic_bars
from nq_bot.features import add_features
from nq_bot.risk import RiskManager

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cfg():
    c = load_settings(ROOT / "config/settings.yaml")
    c["events"]["file"] = str(ROOT / "config/events.csv")
    return c


def test_specs():
    assert SPECS["NQ"].tick_value == 5.0
    assert SPECS["MNQ"].tick_value == 0.5


def test_front_month_rolls():
    assert third_friday(2026, 12) == date(2026, 12, 18)
    assert front_month("NQ", date(2026, 11, 4)).local_symbol == "NQZ6"
    # 8 days before Dec 18 expiry -> already on March
    assert front_month("MNQ", date(2026, 12, 10)).local_symbol == "MNQH7"


def test_no_lookahead_in_opening_range(cfg):
    bars = synthetic_bars(days=3)
    f = add_features(bars, cfg)
    first_day = f[f["session_date"] == f["session_date"].iloc[0]]
    assert first_day.loc[first_day["minute_of_day"] < 9 * 60 + 45, "or_high"].isna().all()
    # truncating future data must not change past features
    f_short = add_features(bars.iloc[:500], cfg)
    pd.testing.assert_series_equal(f["vwap"].iloc[:500], f_short["vwap"], check_names=False)
    pd.testing.assert_series_equal(f["or_high"].iloc[:500], f_short["or_high"], check_names=False)


def test_sizing_caps(cfg):
    rm = RiskManager(cfg, 10_000)
    spec = SPECS["MNQ"]
    qty, _ = rm.size(20000, 19980, spec, 3000, 0.75, 1)   # 20pt = $42.50 all-in vs $50 budget (0.5%)
    assert qty == 1
    qty, _ = rm.size(20000, 19995, spec, 2000, 0.75, 1)   # 5pt = $12.50 -> 4 by risk, 2 by margin, cap 2
    assert qty == 2
    qty, why = rm.size(20000, 19900, spec, 3000, 0.75, 1)  # 100pt = $200 > $50 budget
    assert qty == 0 and "risk budget" in why
    qty, _ = rm.size(20000, 19990, SPECS["NQ"], 30000, 2.0, 1)  # NQ: $200+/contract > budget
    assert qty == 0


def test_daily_limits(cfg):
    rm = RiskManager(cfg, 10_000)
    rm.new_day(date(2026, 1, 5))
    now = pd.Timestamp("2026-01-05 10:00", tz="America/New_York")
    rm.record_trade(-60, now)
    ok, why = rm.can_enter(now + pd.Timedelta(minutes=5))
    assert not ok and "cooldown" in why
    rm.record_trade(-60, now)  # 2nd consecutive loss
    ok, why = rm.can_enter(now + pd.Timedelta(hours=3))
    assert not ok and "consecutive" in why
    rm.new_day(date(2026, 1, 6))
    assert rm.can_enter(now + pd.Timedelta(days=1))[0]


def test_drawdown_kill(cfg):
    rm = RiskManager(cfg, 1000)
    now = pd.Timestamp("2026-01-05 10:00", tz="America/New_York")
    rm.record_trade(-150, now)
    assert rm.killed_reason
    rm.new_day(date(2026, 1, 6))
    assert not rm.can_enter(now)[0]  # kill survives new day


def test_sim_broker_stop_first_and_no_duplicates():
    b = SimBroker(SPECS["MNQ"], slippage_ticks=1)
    ts = pd.Timestamp("2026-01-05 10:00", tz="America/New_York")
    b.submit_bracket(BracketRequest("a", 1, 1, stop=99.0, target=110.0), 100)
    b.submit_bracket(BracketRequest("b", 1, 1, stop=99.0, target=110.0), 100)  # duplicate
    _, ev = b.poll()
    assert [e.status for e in ev] == ["submitted", "rejected"]
    b.process_bar(ts, 100, 100.5, 99.75, 100.25)  # entry at 100.25 (slip)
    assert b.position() == 1
    b.process_bar(ts, 100, 111, 98, 105)          # both touched -> stop assumed first
    fills, _ = b.poll()
    assert fills[-1].kind == "stop" and b.position() == 0
    assert fills[-1].price == 98.75               # 99 - 1 tick slippage


def test_backtest_runs_and_obeys_limits(cfg):
    bars = synthetic_bars(days=40, seed=3)
    res = run_backtest(bars, cfg)
    t = res["trades"]
    if not t.empty:
        per_day = t.groupby(pd.to_datetime(t["entry_ts"]).map(lambda x: x.date())).size()
        assert per_day.max() <= cfg.risk.max_trades_per_day
        assert t["qty"].max() <= cfg.risk.max_contracts
        daily = t.groupby(pd.to_datetime(t["exit_ts"]).map(lambda x: x.date()))["net"].sum()
        # a single gap-through stop can exceed the limit by slippage; allow 1 trade's risk of slack
        assert daily.min() >= -(cfg.risk.max_daily_loss_usd + cfg.risk.max_risk_per_trade_usd)
        assert (pd.to_datetime(t["exit_ts"]).map(lambda x: x.hour * 60 + x.minute) <= 16 * 60).all()


def test_override(cfg):
    c2 = override(cfg, {"strategy.reward_risk": 1.5})
    assert c2.strategy.reward_risk == 1.5 and cfg.strategy.reward_risk == 2.0
