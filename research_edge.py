"""Edge study: does the signal make money per trade, independent of account size?

Runs the strategy at a fixed 1 MNQ contract with risk caps loosened so sizing never
filters a signal, while keeping the strategy's own rules (2 trades/day, stop after
2 losses, cooldown, flat by 15:55). Reports results in dollars per contract and in R.
Usage:  python research_edge.py data/mnq_train.csv runs/edge
"""
import json
import sys
from pathlib import Path

import pandas as pd

from nq_bot.backtest import run_backtest
from nq_bot.config import load_settings, override
from nq_bot.data import load_csv
from nq_bot.features import add_features
from nq_bot.metrics import breakdown

RESEARCH = {
    "risk.starting_equity": 100_000.0, "risk.max_risk_per_trade_pct": 2.0,
    "risk.max_risk_per_trade_usd": 5_000.0, "risk.max_contracts": 1,
    "risk.max_daily_loss_usd": 5_000.0, "risk.max_drawdown_pct": 90.0,
    "risk.profit_lock_trigger_usd": 1e9,
}


def main(csv, out, extra=None):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    cfg = override(load_settings("config/settings.yaml"), {**RESEARCH, **(extra or {})})
    bars = load_csv(csv)
    res = run_backtest(bars, cfg, featured=add_features(bars, cfg))
    t = res["trades"]
    t.to_csv(out / "trades.csv", index=False)
    t["year"] = pd.to_datetime(t["exit_ts"]).map(lambda x: x.year)
    report = {"summary": res["summary"], "monte_carlo": res.get("monte_carlo"),
              "avg_r": float(t["r_multiple"].mean()), "median_risk_pts": float((t["gross"].abs()).median())}
    print(json.dumps(report, indent=2, default=str))
    for k in ("year", "regime", "side", "entry_hour", "exit_kind"):
        print(f"\n== by {k} ==\n{breakdown(t, k).to_string()}")
    (out / "summary.json").write_text(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    extra = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    main(sys.argv[1], sys.argv[2], extra)
