"""Paper runner safeguards: data problems, stale feed, missing stop, kill switch, daily report."""
import json
from pathlib import Path

import pandas as pd
import pytest

from nq_bot.config import load_settings, override
from nq_bot.data import synthetic_bars
from nq_bot.journal import Alerts
from nq_bot.paper import PaperRunner, replay

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cfg():
    c = load_settings(ROOT / "config/settings.yaml")
    return override(c, {"events.file": str(ROOT / "config/events.csv")})


def runner(cfg, tmp_path, history=None, clock=None):
    kw = {"clock": clock} if clock else {}
    return PaperRunner(cfg, history, tmp_path, alerts=Alerts(enabled=False), persist=True, **kw)


def test_rejects_duplicate_out_of_order_and_malformed_bars(cfg, tmp_path):
    r = runner(cfg, tmp_path)
    t = pd.Timestamp("2025-03-04 10:00", tz="America/New_York")
    r.on_bar(t, 100, 101, 99, 100.5, 10)
    r.on_bar(t, 100, 101, 99, 100.5, 10)                          # duplicate
    r.on_bar(t - pd.Timedelta(minutes=1), 100, 101, 99, 100, 10)   # out of order
    r.on_bar(t + pd.Timedelta(minutes=1), 100, 99, 101, 100, 10)   # high < low
    assert len(r.hist) == 1
    issues = [json.loads(l)["issue"] for l in r.journal.path.read_text().splitlines() if '"data_issue"' in l]
    assert len(issues) == 3


def test_stale_feed_flattens_and_halts(cfg, tmp_path, monkeypatch):
    now = {"t": 1000.0}
    r = runner(cfg, tmp_path, clock=lambda: now["t"])
    t = pd.Timestamp("2025-03-04 10:00", tz="America/New_York")
    r.on_bar(t, 100, 101, 99, 100, 10)
    r.broker.pos, r.broker.stop = 1, 95.0                          # pretend we hold 1 contract
    r.engine.trade = {"id": "x", "side": 1, "qty": 1, "open_qty": 1, "entry_price": 100.0, "entry_ts": t,
                      "stop": 95.0, "target": 110.0, "partial": None, "partial_done": False, "regime": "test",
                      "exits": [], "commission": 0.62}
    fake_now = pd.Timestamp("2025-03-04 10:05", tz="America/New_York")
    monkeypatch.setattr(pd.Timestamp, "now", classmethod(lambda cls, tz=None: fake_now))
    now["t"] += 30
    r.heartbeat()
    assert r.broker.position() == 1                                 # 30 s silence is fine
    now["t"] += 200
    r.heartbeat()
    assert r.broker.position() == 0
    assert "no market data" in r.engine.risk.day.halted_reason
    assert r.engine.trades and r.engine.trades[-1]["exit_kind"] == "flatten"


def test_missing_stop_triggers_emergency(cfg, tmp_path):
    r = runner(cfg, tmp_path)
    t = pd.Timestamp("2025-03-04 10:00", tz="America/New_York")
    r.on_bar(t, 100, 101, 99, 100, 10)
    r.broker.pos, r.broker.stop = 1, None
    r.engine.trade = {"id": "x", "side": 1, "qty": 1, "open_qty": 1, "entry_price": 100.0, "entry_ts": t,
                      "stop": 95.0, "target": 110.0, "partial": None, "partial_done": False, "regime": "test",
                      "exits": [], "commission": 0.62}
    r.on_bar(t + pd.Timedelta(minutes=1), 100, 101, 99, 100, 10)
    assert r.broker.position() == 0
    assert "without a protective stop" in r.engine.risk.day.halted_reason


def test_kill_persists_across_restart(cfg, tmp_path):
    r = runner(cfg, tmp_path)
    r.kill("drill")
    r2 = runner(cfg, tmp_path)
    assert r2.engine.risk.killed_reason == "drill"


def test_replay_writes_daily_reports(cfg, tmp_path):
    bars = synthetic_bars(days=3, seed=5)
    r = runner(cfg, tmp_path, history=bars.iloc[:390 * 2])
    replay(r, bars.iloc[390 * 2: 390 * 2 + 60])                     # first hour of day 3
    reports = list(Path(tmp_path).glob("report_*.md"))
    assert reports and "SIMULATED" in reports[0].read_text()


def test_no_report_without_regular_session_and_rth_gaps_only(cfg, tmp_path):
    r = runner(cfg, tmp_path)
    sun = pd.Timestamp("2025-03-02 18:00", tz="America/New_York")       # Sunday evening open
    for i in range(3):
        r.on_bar(sun + pd.Timedelta(minutes=i), 100, 101, 99, 100, 1)
    assert r.end_of_day(sun.date()) is None
    mon = pd.Timestamp("2025-03-03 10:00", tz="America/New_York")
    r.on_bar(mon, 100, 101, 99, 100, 1)
    r.on_bar(mon + pd.Timedelta(minutes=3), 100, 101, 99, 100, 1)      # 2 missing minutes in RTH
    assert r.gaps_today == 1
