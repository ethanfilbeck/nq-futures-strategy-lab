"""Pre-week readiness check on REAL historical MNQ bars (no live connection needed).

1. Replays N real sessions bar-by-bar through the paper runner (exactly as live bars would arrive).
2. Runs the backtester over the same bars and checks the two produce IDENTICAL trades.
3. Checks every trade had a stop, every exit is a stop / target / 15:55 flatten, and nothing is held overnight.
4. Fires the kill switch mid-session and checks it flattens, persists across a restart, and blocks entries.
5. Confirms a daily report was written for every replayed session.

Usage: python scripts/readiness_check.py data/mnq_train.csv [--strategy orb_vwap] [--days 5] [--end 2025-06-27]
"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nq_bot.backtest import run_backtest  # noqa: E402
from nq_bot.config import load_settings, override  # noqa: E402
from nq_bot.data import load_csv, times  # noqa: E402
from nq_bot.journal import Alerts  # noqa: E402
from nq_bot.paper import PaperRunner, replay  # noqa: E402

SIZE = {"risk.starting_equity": 100_000.0, "risk.max_risk_per_trade_pct": 2.0, "risk.max_risk_per_trade_usd": 5_000.0,
        "risk.max_contracts": 1, "risk.max_daily_loss_usd": 5_000.0, "risk.max_drawdown_pct": 90.0,
        "risk.profit_lock_trigger_usd": 1e9}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--strategy", default="orb_vwap")
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--end", default=None, help="last session to replay (YYYY-MM-DD); default = last in file")
    a = ap.parse_args()

    cfg = override(load_settings("config/settings.yaml"), {**SIZE, "strategy.name": a.strategy, "events.file": "none.csv"})
    bars = load_csv(a.csv)
    sessions = sorted(set(times(bars.between_time("09:30", "15:59")).date))
    end = pd.Timestamp(a.end).date() if a.end else sessions[-1]
    replay_days = [d for d in sessions if d <= end][-a.days:]
    start_ts = pd.Timestamp(f"{replay_days[0]} 00:00", tz="America/New_York")
    end_ts = pd.Timestamp(f"{replay_days[-1]} 23:59", tz="America/New_York")
    hist = bars[(bars.index < start_ts) & (bars.index >= start_ts - pd.Timedelta(days=35))]
    live = bars[(bars.index >= start_ts) & (bars.index <= end_ts)]
    results: dict[str, object] = {}
    ok = True

    tmp = Path(tempfile.mkdtemp(prefix="nqbot_ready_"))
    try:
        # 1-2: paper replay vs backtest
        r = PaperRunner(cfg, hist, tmp / "paper", alerts=Alerts(enabled=False), persist=False)
        replay(r, live)
        paper = pd.DataFrame(r.engine.trades)
        bt = run_backtest(pd.concat([hist, live]), cfg, trade_from=start_ts)["trades"]
        cols = ["side", "qty", "entry_ts", "entry_price", "exit_ts", "exit_price", "exit_kind", "net"]
        same = (len(paper) == len(bt)) and (len(paper) == 0 or
                paper[cols].astype(str).reset_index(drop=True).equals(bt[cols].astype(str).reset_index(drop=True)))
        results["replayed_sessions"] = [str(d) for d in replay_days]
        results["paper_trades"] = len(paper)
        results["backtest_trades"] = len(bt)
        results["paper_matches_backtest"] = bool(same)
        ok = ok and bool(same)
        # 3: protection and session rules
        if len(paper):
            exits_ok = paper["exit_kind"].isin(["stop", "target", "flatten"]).all()
            same_day = (pd.to_datetime(paper["entry_ts"]).map(lambda x: x.date())
                        == pd.to_datetime(paper["exit_ts"]).map(lambda x: x.date())).all()
            journal_lines = r.journal.path.read_text().splitlines() if r.journal.path else []
            stops = [json.loads(line) for line in journal_lines if '"event": "order"' in line]
            all_had_stops = all(o["signal"]["stop"] is not None for o in stops)
        else:
            exits_ok, same_day, all_had_stops = True, True, True
        results["every_order_had_a_stop"] = bool(all_had_stops)
        results["exits_are_stop_target_or_flatten"] = bool(exits_ok)
        results["no_overnight_positions"] = bool(same_day)
        ok &= bool(exits_ok and same_day and all_had_stops)
        # 5: reports
        reps = sorted(p.name for p in (tmp / "paper").glob("report_*.md"))
        results["daily_reports"] = reps
        ok &= len(reps) >= len(replay_days)

        # 4: kill switch mid-session, then restart
        k = PaperRunner(cfg, hist, tmp / "kill", alerts=Alerts(enabled=False), persist=True)
        first_day = live[times(live).date == replay_days[0]]
        fd_t = times(first_day)
        half = first_day[fd_t.hour * 60 + fd_t.minute < 11 * 60]
        for ts, b in half.iterrows():
            k.on_bar(ts, b["open"], b["high"], b["low"], b["close"], b["volume"])
        k.kill("readiness drill")
        flat_after_kill = k.broker.position() == 0
        k2 = PaperRunner(cfg, hist, tmp / "kill", alerts=Alerts(enabled=False), persist=True)
        rest = live[live.index > half.index[-1]]
        for ts, b in rest.iterrows():
            k2.on_bar(ts, b["open"], b["high"], b["low"], b["close"], b["volume"])
        kill_flattens = bool(flat_after_kill)
        kill_survives = k2.engine.risk.killed_reason == "readiness drill"
        no_entries = len(k2.engine.trades) == 0
        results["kill_flattens"], results["kill_survives_restart"] = kill_flattens, kill_survives
        results["no_entries_after_kill"] = no_entries
        ok = ok and kill_flattens and kill_survives and no_entries
        sample = (tmp / "paper" / reps[-1]).read_text() if reps else ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    results["READY"] = bool(ok)
    print(json.dumps(results, indent=2, default=str))
    if sample:
        print("\n--- sample daily report ---\n" + sample)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
