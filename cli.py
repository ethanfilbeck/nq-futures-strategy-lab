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
    pr = sub.add_parser("paper-live", help="unattended PAPER trading on Databento live 1-minute bars (simulated orders)")
    pr.add_argument("--strategy", default=None, help="override strategy.name (orb_vwap, sweep, vwap_pullback, intraday_momentum, none)")
    pr.add_argument("--out", default="logs/paper")
    pr.add_argument("--webhook", action="store_true", help="also accept TradingView webhook signals (strategy 'tradingview')")
    pr.add_argument("--webhook-port", type=int, default=8787)
    pr.add_argument("--allow-any-ip", action="store_true", help="skip the TradingView IP allowlist (local testing only)")
    rp = sub.add_parser("paper-replay", help="replay real historical sessions through the paper runner")
    rp.add_argument("--csv", required=True)
    rp.add_argument("--days", type=int, default=5)
    rp.add_argument("--strategy", default=None)
    rp.add_argument("--out", default="logs/paper_replay")
    sub.add_parser("kill", help="emergency stop for a running paper-live session (creates logs/paper/KILL)")
    sub.add_parser("reset-kill", help="clear the drawdown kill switch after you've reviewed why it fired")
    dp = sub.add_parser("drill", help="IB PAPER drills for the execution mechanics (see docs/PAPER_DRILLS.md)")
    dp.add_argument("action", choices=["status", "bracket", "duplicate", "reconcile", "flatten"])
    dp.add_argument("--side", choices=["buy", "sell"], default="buy")
    dp.add_argument("--stop", type=float, help="stop level to use when replacing a missing stop")
    dp.add_argument("--delayed", action="store_true",
                    help="use IB's free delayed quotes (no CME real-time subscription); wide buffers, paper only")
    dp.add_argument("--ref", type=float, help="with --delayed: reference price you read off a chart, if IB sends none")
    fp = sub.add_parser("fomc-paper", help="forward PAPER tracking of H8 (pre-FOMC drift) on the IB paper account")
    fp.add_argument("--test-now", action="store_true", help="plumbing check: buy 1, place GTC stop, sell ~20 s later")
    fp.add_argument("--if-due", action="store_true",
                    help="for the scheduled task: run only if a trade is open or today is an entry day, else exit")
    sub.add_parser("alert-test", help="send one test message to ALERT_WEBHOOK_URL (Discord) from .env")
    lp = sub.add_parser("paper")
    lp.add_argument("--live", action="store_true", help="ALSO needs mode: live, env flag and typed confirmation")

    args = p.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose or args.cmd in ("paper", "drill", "fomc-paper") else logging.WARNING,
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
    elif args.cmd in ("paper-live", "paper-replay"):
        from nq_bot.config import override
        from nq_bot.paper import PaperRunner, replay
        if args.strategy:
            cfg = override(cfg, {"strategy.name": args.strategy})
        if cfg.mode != "paper":
            raise SystemExit("paper commands only run with mode: paper")
        print(f"SIMULATED ORDERS ONLY. Strategy: {cfg.strategy.name}. Output: {args.out}")
        if args.cmd == "paper-replay":
            import pandas as pd

            from nq_bot.data import load_csv, times
            bars = load_csv(args.csv)
            sessions = sorted(set(times(bars.between_time("09:30", "15:59")).date))[-args.days:]
            start = pd.Timestamp(f"{sessions[0]} 00:00", tz=cfg.session.timezone)
            hist = bars[(bars.index < start) & (bars.index >= start - pd.Timedelta(days=35))]
            runner = PaperRunner(cfg, hist, args.out)
            replay(runner, bars[bars.index >= start])
        else:
            import os

            import pandas as pd

            from nq_bot.contracts import front_month
            from nq_bot.data import times
            from nq_bot.paper import databento_history, run_databento_live
            key = os.environ.get("DATABENTO_API_KEY")
            if not key:
                raise SystemExit("Set DATABENTO_API_KEY in .env")
            fm = front_month(cfg.instrument.root, date.today(), cfg.instrument.roll_days_before_expiry)
            print(f"Contract: {fm.local_symbol} (roll on/after {fm.roll_date}). Loading warm-up history...")
            hist = databento_history(key, fm.local_symbol)
            last_bar = times(hist)[-1]
            gap = pd.Timestamp.now(tz="UTC") - last_bar.tz_convert("UTC")
            live_from = ((last_bar + pd.Timedelta(minutes=1)).tz_convert("UTC").isoformat()
                         if gap < pd.Timedelta(hours=23) else None)
            print(f"History: {len(hist):,} bars to {last_bar}. Live replay from: {live_from or 'now'}")
            runner = PaperRunner(cfg, hist, args.out)
            if runner.engine.risk.killed_reason:
                raise SystemExit(f"Kill switch is set ({runner.engine.risk.killed_reason}). Run reset-kill first.")
            if args.webhook:
                from nq_bot.webhook import TRADINGVIEW_IPS, WebhookGate, serve
                if cfg.strategy.name != "tradingview":
                    raise SystemExit("--webhook needs --strategy tradingview")
                gate = WebhookGate(runner, os.environ.get("WEBHOOK_SECRET", ""),
                                   None if args.allow_any_ip else TRADINGVIEW_IPS)
                serve(gate, port=args.webhook_port)
                print(f"Webhook receiver on http://127.0.0.1:{args.webhook_port}/tv (expose with a tunnel; see docs/AUTOMATION.md)")
            try:
                run_databento_live(runner, key, fm.local_symbol, start=live_from)
            except KeyboardInterrupt:
                runner.kill("stopped by user (Ctrl+C)")
    elif args.cmd == "kill":
        Path("logs/paper").mkdir(parents=True, exist_ok=True)
        Path("logs/paper/KILL").write_text("emergency stop requested\n")
        print("KILL file written. The running paper session will flatten and stop within ~5 seconds.")
    elif args.cmd == "reset-kill":
        import json as _json

        from nq_bot.live import reset_kill
        files = {"logs/risk_state.json": "IB runner (py cli.py paper)",
                 "logs/paper/risk_state.json": "Databento runner (py cli.py paper-live)"}
        killed = []
        for state_file, what in files.items():
            try:
                reason = _json.loads(Path(state_file).read_text()).get("killed_reason")
            except (OSError, ValueError):
                reason = None
            print(f"  {state_file:28s} {what}: " + (f"KILLED ({reason})" if reason else "not killed"))
            if reason:
                killed.append(state_file)
        default = killed[0] if len(killed) == 1 else "logs/paper/risk_state.json"
        path = Path(input(f"Which state file? [{default}] ").strip() or default)
        Path("logs/paper/KILL").unlink(missing_ok=True)
        if input("Type RESET to clear the kill switch: ").strip() == "RESET" and reset_kill(path):
            print("Kill switch cleared. The drawdown limit now measures from your equity at the next start.")
        else:
            print("Nothing cleared.")
    elif args.cmd == "drill":
        from nq_bot.drill import run as drill
        drill(cfg, args.action, side=args.side, stop=args.stop, delayed=args.delayed, ref=args.ref)
    elif args.cmd == "fomc-paper":
        from nq_bot import fomc_paper as fp_mod
        if args.if_due:
            import pandas as pd
            st = fp_mod.load_state(fp_mod.OUT / "state.json")
            now = pd.Timestamp.now(tz=fp_mod.TZ)
            if not fp_mod.due_today(now, fp_mod.fomc_events(), bool(st.get("in_trade"))):
                print(f"{now:%Y-%m-%d %H:%M} ET: no FOMC paper trade due today.")
                return
        fp_mod.run(cfg, test_now=args.test_now)
    elif args.cmd == "alert-test":
        from nq_bot.journal import Alerts
        al = Alerts()
        if not al.url:
            print("ALERT_WEBHOOK_URL is not set. Add it to the .env file in this folder (see docs/FOMC_PAPER.md).")
        elif al.send("info", "Test alert - phone alerts are working. (PAPER bot, no real money.)"):
            print("Sent. Check Discord on your phone.")
        else:
            print("The webhook post failed - check the URL in .env (copy it again from Discord).")
    elif args.cmd == "paper":
        from nq_bot.live import run
        run(cfg, live_flag=args.live)


if __name__ == "__main__":
    main()
