"""Runs strategy family 2 exactly as pre-registered in docs/PREREG_FAMILY2.md and reports every
criterion, pass or fail. Usage: python run_family2_prereg.py data/mnq_train.csv runs/family2"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from nq_bot.backtest import run_backtest
from nq_bot.config import load_settings, override
from nq_bot.data import load_csv
from nq_bot.family2 import add_family2_features, overnight_drift_trades
from nq_bot.features import add_features
from nq_bot.metrics import breakdown, monte_carlo, summarize
from research_edge import RESEARCH

POST = pd.Timestamp("2021-01-01").date()
T_BAR = 3.0


def t_stat(x):
    x = np.asarray(x, float)
    return float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")


def judge(name, t, t2, equity=100_000.0):
    t = t.copy()
    t["d"] = pd.to_datetime(t["entry_ts"]).map(lambda x: x.date())
    t["year"] = pd.to_datetime(t["entry_ts"]).map(lambda x: x.year)
    s = summarize(t, equity)
    by_year = breakdown(t, "year")
    full = by_year.loc[[y for y in by_year.index if 2019 <= y <= 2024], "net"]
    post = float(t.loc[t["d"] >= POST, "net"].sum())
    pre = float(t.loc[t["d"] < POST, "net"].sum())
    net2 = float(t2["net"].sum()) if len(t2) else float("nan")
    checks = {
        "1_profit_factor_ge_1.20": s["profit_factor"] >= 1.20,
        "2_t_stat_ge_3.0": t_stat(t["net"]) >= T_BAR,
        "3a_positive_years_ge_4_of_6": int((full > 0).sum()) >= 4,
        "3b_net_positive_since_2021": post > 0,
        "4_positive_at_2_ticks": net2 > 0,
        "5_at_least_200_trades": len(t) >= 200,
    }
    rep = {"hypothesis": name, "summary_1tick": s, "gross_before_commissions": round(float(t["gross"].sum()), 2),
           "t_stat_net": round(t_stat(t["net"]), 2), "net_before_2021": round(pre, 2),
           "net_since_2021": round(post, 2), "net_at_2_ticks": round(net2, 2),
           "positive_full_years": f"{int((full > 0).sum())} of {len(full)}",
           "exit_kinds": t["exit_kind"].value_counts().to_dict(),
           "monte_carlo": monte_carlo(t["net"].to_numpy(float), equity),
           "checks": checks, "PASS": all(checks.values())}
    return rep, by_year, t


def main(csv, outdir):
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    bars = load_csv(csv)
    reports = {}

    # H3 overnight drift (fixed-time, outside RTH)
    h3 = overnight_drift_trades(bars, 1)
    h3_2 = overnight_drift_trades(bars, 2)
    rep, by_year, t = judge("H3 overnight drift", h3, h3_2)
    pts = t.assign(y=t["year"]).groupby("y")["move_open_to_open"].mean().round(2).to_dict()
    rep["mean_02_to_03_move_pts_by_year"] = pts
    rep["mean_move_pts_before_2021"] = round(float(t.loc[t["d"] < POST, "move_open_to_open"].mean()), 2)
    rep["mean_move_pts_since_2021"] = round(float(t.loc[t["d"] >= POST, "move_open_to_open"].mean()), 2)
    reports["H3"] = (rep, by_year, t)

    # H4 / H5 through the bot's engine
    base = load_settings("config/settings.yaml")
    feats = add_family2_features(add_features(bars, base), base)
    del bars
    for key, name in (("H4", "sweep"), ("H5", "vwap_pullback")):
        cfg = override(base, {**RESEARCH, "strategy.name": name, "events.file": "none.csv"})
        r1 = run_backtest(None, cfg, featured=feats)
        r2 = run_backtest(None, override(cfg, {"instrument.slippage_ticks": 2}), featured=feats)
        rep, by_year, t = judge(f"{key} {name}", r1["trades"], r2["trades"])
        rep["by_side"] = breakdown(t, "side").to_dict()
        reports[key] = (rep, by_year, t)

    for key, (rep, by_year, t) in reports.items():
        print(f"\n================ {rep['hypothesis']} ================")
        print(json.dumps(rep, indent=2, default=str))
        print(by_year.to_string())
        (out / f"report_{key}.json").write_text(json.dumps(rep, indent=2, default=str))
        by_year.to_csv(out / f"by_year_{key}.csv")
        t.to_csv(out / f"trades_{key}.csv", index=False)


if __name__ == "__main__":
    main(*sys.argv[1:3])
