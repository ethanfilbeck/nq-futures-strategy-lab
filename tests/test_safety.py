"""Tests for the five safety questions: daily-loss interaction, partial+breakeven, rollover,
drawdown kill behaviour, and restart/disconnect recovery."""
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from nq_bot.broker.sim import SimBroker
from nq_bot.config import load_settings, override
from nq_bot.contracts import SPECS, front_month
from nq_bot.engine import Engine
from nq_bot.events import EventCalendar
from nq_bot.journal import Alerts, Journal
from nq_bot.risk import RiskManager

ROOT = Path(__file__).resolve().parents[1]
TZ = "America/New_York"


@pytest.fixture
def cfg():
    c = load_settings(ROOT / "config/settings.yaml")
    c["events"]["file"] = str(ROOT / "config/events.csv")
    return c


def ts(hm, d="2026-11-05"):
    return pd.Timestamp(f"{d} {hm}", tz=TZ)


def row(t, o, h, l, c):
    """A bar that is bullish by every regime/strategy rule, with OR 19979-19999 and ATR 5."""
    return dict(open=o, high=h, low=l, close=c, minute_of_day=t.hour * 60 + t.minute, session_date=t.date(),
                rth=True, atr=5.0, atr_ratio=1.0, ema_fast=19995.0, ema_slow=19990.0, ema_slow_slope=5.0,
                vwap=19990.0, or_high=19999.0, or_low=19979.0, or_mid=19989.0, bar_range=h - l)


def make_engine(cfg):
    spec = SPECS["MNQ"]
    broker = SimBroker(spec, cfg.instrument.slippage_ticks)
    ev = EventCalendar(cfg.events.file, TZ, 15, 15)
    return Engine(cfg, broker, spec, Journal(None, enabled=False), Alerts(enabled=False), ev), broker


def step(eng, broker, t, o, h, l, c):
    broker.process_bar(t, o, h, l, c)
    eng.on_bar(t, row(t, o, h, l, c))


# 1 ---------------------------------------------------------------- daily loss vs per-trade risk
def test_trade_risk_shrinks_to_remaining_daily_allowance(cfg):
    rm = RiskManager(cfg, 100_000)          # 0.5% = $500, but the $100 hard cap wins
    rm.new_day(date(2026, 11, 5))
    spec = SPECS["MNQ"]
    # 8-pt stop -> $16 + $1.50 commission + $1.00 slippage = $18.50 per contract
    assert rm.size(20000, 19992, spec, 2000, 0.75, 1)[0] == 2         # capped by max_contracts
    rm.day.realized = -230.0                                           # $20 left today
    assert rm.size(20000, 19992, spec, 2000, 0.75, 1)[0] == 1
    rm.day.realized = -240.0                                           # $10 left -> no trade
    assert rm.size(20000, 19992, spec, 2000, 0.75, 1)[0] == 0


def test_open_pnl_counts_toward_daily_limit(cfg):
    rm = RiskManager(cfg, 10_000)
    rm.new_day(date(2026, 11, 5))
    rm.day.realized = -200.0
    assert rm.check_open_loss(-49.0) is False
    assert rm.check_open_loss(-50.0) is True and rm.day.halted_reason


# 2 ---------------------------------------------------------------- partial + breakeven
def test_partial_then_breakeven_stop(cfg):
    cfg = override(cfg, {"instrument.margin_per_contract": 2000.0})
    eng, broker = make_engine(cfg)
    step(eng, broker, ts("10:00"), 19999, 20001, 19998, 20000)    # signal -> bracket for 2
    step(eng, broker, ts("10:01"), 20000.25, 20009, 20000, 20007)  # filled 20000.50; high hits 1R partial
    assert broker.position() == 2 and eng.trade["partial_done"]
    assert broker.stop == 20000.5 and broker.prot_qty == 1          # stop moved to breakeven, resized
    step(eng, broker, ts("10:02"), 20006, 20007, 20000, 20001)      # reduce fills at open, then BE stop hit
    assert broker.position() == 0 and eng.trade is None
    t = eng.trades[-1]
    assert t["exit_kind"] == "stop" and t["qty"] == 2
    # reduce: (20005.75-20000.50)*2 = 10.50 ; stop: (20000.25-20000.50)*2 = -0.50 ; minus 4 sides of commission
    assert t["gross"] == pytest.approx(10.0)
    assert t["net"] == pytest.approx(10.0 - 4 * cfg.instrument.commission_per_side)


def test_no_partial_with_one_contract(cfg):
    eng, broker = make_engine(cfg)                                   # margin 3000 -> 1 contract
    step(eng, broker, ts("10:00"), 19999, 20001, 19998, 20000)
    step(eng, broker, ts("10:01"), 20000.25, 20009, 20000, 20007)
    assert broker.position() == 1 and not eng.trade["partial_done"] and broker.stop == 19992


# 3 ---------------------------------------------------------------- rollover
def test_roll_dates():
    assert front_month("MNQ", date(2026, 12, 9)).local_symbol == "MNQZ6"
    assert front_month("MNQ", date(2026, 12, 10)).local_symbol == "MNQH7"
    assert front_month("MNQ", date(2027, 3, 11)).local_symbol == "MNQM7"   # Mar 19 2027 expiry - 8


def test_never_holds_overnight(cfg):
    eng, broker = make_engine(cfg)
    step(eng, broker, ts("10:00"), 19999, 20001, 19998, 20000)
    step(eng, broker, ts("10:01"), 20000.25, 20003, 20000, 20002)
    assert broker.position() == 1
    step(eng, broker, ts("15:55"), 20002, 20003, 20001, 20002)     # flatten time -> market out
    step(eng, broker, ts("15:56"), 20002, 20003, 20001, 20002)
    assert broker.position() == 0 and eng.trades[-1]["exit_kind"] == "flatten"


def _fake_ib(positions=(), open_trades=()):
    return SimpleNamespace(positions=lambda: list(positions), openTrades=lambda: list(open_trades),
                           reqAllOpenOrders=lambda: None, sleep=lambda s: None)


def test_startup_refuses_leftover_old_month_position(cfg):
    pytest.importorskip("ib_async")
    from nq_bot.broker.ibkr import IBKRBroker
    b = IBKRBroker(cfg, SPECS["MNQ"])
    old = SimpleNamespace(contract=SimpleNamespace(symbol="MNQ", localSymbol="MNQZ6"), position=1)
    b.ib = _fake_ib(positions=[old])
    with pytest.raises(RuntimeError, match="MNQZ6"):
        b._startup_checks()
    stray = SimpleNamespace(contract=SimpleNamespace(symbol="NQ", localSymbol="NQH7"),
                            order=SimpleNamespace(action="SELL", totalQuantity=1, orderType="STP"))
    b.ib = _fake_ib(open_trades=[stray])
    with pytest.raises(RuntimeError, match="orders"):
        b._startup_checks()
    b.ib = _fake_ib()
    b._startup_checks()  # clean account passes


def test_roll_due(cfg):
    pytest.importorskip("ib_async")
    from nq_bot.broker.ibkr import IBKRBroker
    b = IBKRBroker(cfg, SPECS["MNQ"])
    b.front = front_month("MNQ", date(2026, 12, 9))
    assert not b.roll_due(date(2026, 12, 9))
    assert b.roll_due(date(2026, 12, 10))


# 4 ---------------------------------------------------------------- drawdown kill switch
def test_drawdown_kill_flattens_open_position(cfg):
    cfg = override(cfg, {"risk.max_drawdown_pct": 0.1})              # $10 on $10k, for the test
    eng, broker = make_engine(cfg)
    step(eng, broker, ts("10:00"), 19999, 20001, 19998, 20000)
    step(eng, broker, ts("10:01"), 20000.25, 20001, 19994, 19994)    # -$13 open, stop 19992 not hit
    assert eng.risk.killed_reason and "open P&L" in eng.risk.killed_reason
    step(eng, broker, ts("10:02"), 19994, 19995, 19993, 19994)
    assert broker.position() == 0 and eng.trades[-1]["exit_kind"] == "flatten"
    eng.risk.new_day(date(2026, 11, 6))
    assert not eng.risk.can_enter(ts("10:00", "2026-11-06"))[0]       # stays killed next day


# 5 ---------------------------------------------------------------- restart / disconnect
def test_restart_cannot_reset_daily_limits_or_kill(cfg, tmp_path):
    from nq_bot.live import reset_kill, restore_risk_state, save_risk_state
    f = tmp_path / "risk_state.json"
    rm = RiskManager(cfg, 10_000)
    rm.new_day(date(2026, 11, 5))
    rm.record_trade(-60, ts("10:00"))
    rm.record_trade(-60, ts("10:45"))                                 # 2 losses -> halted for the day
    save_risk_state(rm, f)

    same_day = RiskManager(cfg, 9_880)
    restore_risk_state(same_day, f, date(2026, 11, 5))
    assert same_day.day.trades == 2 and same_day.day.realized == -120
    assert not same_day.can_enter(ts("13:00"))[0]

    next_day = RiskManager(cfg, 9_880)
    restore_risk_state(next_day, f, date(2026, 11, 6))
    assert next_day.day.trades == 0 and next_day.peak_equity == 10_000  # counters reset, peak kept

    rm.kill("test")
    save_risk_state(rm, f)
    again = RiskManager(cfg, 9_880)
    restore_risk_state(again, f, date(2026, 11, 9))
    assert again.killed_reason == "test"
    assert reset_kill(f) and json.loads(f.read_text())["killed_reason"] is None


def test_disconnect_blocks_entries(cfg):
    eng, broker = make_engine(cfg)
    broker.connected = False
    step(eng, broker, ts("10:00"), 19999, 20001, 19998, 20000)
    assert eng.pending is None and eng.risk.day.halted_reason == "broker disconnected"


def test_protection_always_matches_position():
    pytest.importorskip("ib_async")
    from nq_bot.broker.ibkr import protection_fix
    assert protection_fix(0, True, True, 2, False) == "none"            # entry still working - leave bracket
    assert protection_fix(0, False, True, 2, False) == "cancel_children"  # orphan stop after exit
    assert protection_fix(2, False, False, 0, False) == "replace_stop"  # stop missing - never allowed
    assert protection_fix(1, False, True, 2, False) == "resize"         # partial entry fill / reduce done
    assert protection_fix(2, False, True, 1, True) == "none"            # reduce in flight - wait
    assert protection_fix(-1, False, True, 1, False) == "none"


def test_restart_adopts_existing_stop_instead_of_stacking_a_second(cfg):
    pytest.importorskip("ib_async")
    from nq_bot.broker.ibkr import IBKRBroker, protection_fix
    b = IBKRBroker(cfg, SPECS["MNQ"])
    b.contract = SimpleNamespace(conId=1, localSymbol="MNQZ6")
    pos = SimpleNamespace(contract=b.contract, position=1)
    stop = SimpleNamespace(contract=b.contract, isDone=lambda: False,
                           order=SimpleNamespace(orderId=7, action="SELL", orderType="STP", auxPrice=20980.0,
                                                 totalQuantity=1, orderRef="old"))
    b.ib = _fake_ib(positions=[pos], open_trades=[stop])
    b.adopt_existing_orders()
    assert b.sl is stop and b.stop_px == 20980.0
    # with the stop adopted, reconciliation has nothing to replace
    assert protection_fix(1, False, True, 1, False) == "none"
