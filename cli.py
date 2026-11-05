"""Command line entry point.

  python cli.py contract                          # which quarterly contract to trade today
  python cli.py backtest --csv data/mnq_1m.csv    # backtest on real data you downloaded
  python cli.py backtest --synthetic              # plumbing test on RANDOM data
  python cli.py walkforward --csv data/mnq_1m.csv
  python cli.py fetch --symbol MNQ.v.0 --start 2021-01-01 --end 2026-10-31 --out data/mnq_1m.csv
  python cli.py paper                             # IBKR paper account, real-time
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path

from nq_bot.config import load_settings


def _env():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def _bars(args, cfg):
    from nq_bot.data import load_csv, synthetic_bars
    if args.synthetic:
        print("!! SYNTHETIC RANDOM DATA - results test the code only and say NOTHING about the strategy !!")
        return synthetic_bars(days=args.days)
    if not args.csv:
        raise SystemExit("give --csv PATH or --synthetic")
    return load_csv(args.csv, tz_of_file=args.csv_tz)


def _print(res):
    print("\n== Summary ==")
    print(json.dumps(res["summary"], indent=2, default=str))
    if res.get("killed"):
        print(f"\nKILL SWITCH TRIGGERED: {res['killed']}")
    for key in ("by_regime", "by_side", "by_hour"):
        if key in res:
            print(f"\n== {key} ==\n{res[key].to_string()}")
    if "monte_carlo" in res:
        print("\n== Monte Carlo (bootstrap of trade P&L) ==")
        print(json.dumps(res["monte_carlo"], indent=2))


def main():
    p = argparse.ArgumentParser(description="NQ/MNQ paper-first trading bot")
    p.add_argument("--config", default="config/settings.yaml")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("contract")
    for name in ("backtest", "walkforward"):
        sp = sub.add_parser(name)
        sp.add_argument("--csv")
        sp.add_argument("--csv-tz", default="UTC", help="timezone of naive timestamps in the CSV")
        sp.add_argument("--synthetic", action="store_true")
        sp.add_argument("--days", type=int, default=120)
        sp.add_argument("--out", default="logs")
        if name == "walkforward":
            sp.add_argument("--folds", type=int, default=4)
    f = sub.add_parser("fetch")
    f.add_argument("--symbol", default="MNQ.v.0")
    f.add_argument("--start", required=True)
    f.add_argument("--end", required=True)
    f.add_argument("--out", required=True)
    sub.add_parser("reset-kill", help="clear the drawdown kill switch after you've reviewed why it fired")
    dp = sub.add_parser("drill", help="IB PAPER drills for the execution mechanics (see docs/PAPER_DRILLS.md)")
    dp.add_argument("action", choices=["status", "bracket", "duplicate", "reconcile", "flatten"])
    dp.add_argument("--side", choices=["buy", "sell"], default="buy")
    dp.add_argument("--stop", type=float, help="stop level to use when replacing a missing stop")
    lp = sub.add_parser("paper")
    lp.add_argument("--live", action="store_true", help="ALSO needs mode: live, env flag and typed confirmation")

    args = p.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose or args.cmd in ("paper", "drill") else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    _env()
    cfg = load_settings(args.config)

    if args.cmd == "contract":
        from nq_bot.contracts import SPECS, front_month
        fm = front_month(cfg.instrument.root, date.today(), cfg.instrument.roll_days_before_expiry)
        s = SPECS[cfg.instrument.root]
        print(f"{fm.local_symbol} (TradingView {fm.tv_symbol}) expires {fm.expiry}, roll on/after {fm.roll_date}")
        print(f"tick {s.tick_size} = ${s.tick_value:.2f}, ${s.point_value:.0f}/point")
    elif args.cmd == "backtest":
        from nq_bot.backtest import run_backtest
        bars = _bars(args, cfg)
        res = run_backtest(bars, cfg, journal_dir=args.out)
        _print(res)
        Path(args.out).mkdir(exist_ok=True)
        if not res["trades"].empty:
            res["trades"].to_csv(Path(args.out) / "trades.csv", index=False)
            print(f"\ntrades -> {Path(args.out) / 'trades.csv'}")
    elif args.cmd == "walkforward":
        from nq_bot.backtest import walk_forward
        bars = _bars(args, cfg)
        grid = {"strategy.opening_range_minutes": [15, 30], "strategy.reward_risk": [1.5, 2.0],
                "strategy.max_stop_atr": [1.0, 1.5]}
        res = walk_forward(bars, cfg, grid, n_folds=args.folds)
        for fold in res["folds"]:
            print(json.dumps(fold, indent=2, default=str))
        print("\n== Out-of-sample only ==")
        print(json.dumps(res["oos_summary"], indent=2, default=str))
    elif args.cmd == "fetch":
        from nq_bot.data import fetch_databento
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        df = fetch_databento(args.symbol, args.start, args.end, out_csv=args.out)
        print(f"saved {len(df):,} bars to {args.out}")
    elif args.cmd == "reset-kill":
        from nq_bot.live import reset_kill
        path = Path(cfg.journal.dir) / "risk_state.json"
        if input("Type RESET to clear the kill switch: ").strip() == "RESET" and reset_kill(path):
            print("Kill switch cleared. The drawdown limit now measures from your equity at the next start.")
        else:
            print("Nothing cleared.")
    elif args.cmd == "drill":
        from nq_bot.drill import run as drill
        drill(cfg, args.action, side=args.side, stop=args.stop)
    elif args.cmd == "paper":
        from nq_bot.live import run
        run(cfg, live_flag=args.live)


if __name__ == "__main__":
    main()
