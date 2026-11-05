"""Runs the pre-registered intraday momentum test exactly as written in
docs/PREREG_INTRADAY_MOMENTUM.md and reports every metric in its section 5, pass or fail.

Usage: python test_momentum_prereg.py data/mnq_train.csv runs/momentum <variant>
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from nq_bot.backtest import run_backtest
from nq_bot.config import load_settings, override
from nq_bot.data import load_csv
from nq_bot.features import add_features
from nq_bot.metrics import breakdown
from nq_bot.momentum import M_1000, M_1529, M_1559, add_momentum_features
from research_edge import RESEARCH

POST_PUB = pd.Timestamp("2020-06-01").date()  # Baltussen et al. sample ends May 2020


def t_stat(x):
    x = np.asarray(x, float)
    return float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")


def plain_stats(feats, variant):
    """Correlation / OLS slope of last-half-hour return on the predictor, before any costs."""
    m, sd, c = feats["minute_of_day"], feats["session_date"], feats["close"]
    day = pd.DataFrame({k: c[m == mm].groupby(sd[m == mm]).last()
                        for k, mm in (("c0959", M_1000), ("c1529", M_1529), ("c1559", M_1559))}).dropna()
    day["prev"] = day["c1559"].shift(1)
    day = day.dropna()
    ref = day["c0959"] if variant == "first_half_hour" else day["c1529"]
    x = ref / day["prev"] - 1
    y = day["c1559"] / day["c1529"] - 1
    slope = float(np.polyfit(x, y, 1)[0])
    return {"days": int(len(day)), "corr": round(float(np.corrcoef(x, y)[0, 1]), 4),
            "ols_slope": round(slope, 5), "sign_hit_rate_pct": round(float((np.sign(x) == np.sign(y)).mean() * 100), 2),
            "first_half_hour_abs_ret": (day["c0959"] / day["prev"] - 1).abs()}


def run(cfg, feats, extra):
    return run_backtest(None, override(cfg, extra), featured=feats)


def main(csv, outdir, variant):
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    base = override(load_settings("config/settings.yaml"),
                    {"strategy.name": "intraday_momentum", "momentum.variant": variant,
                     "session.flatten_time": "15:59", "events.file": "none.csv"})
    bars = load_csv(csv)
    feats = add_momentum_features(add_features(bars, base), base)

    edge = run(base, feats, RESEARCH)
    slip2 = run(base, feats, {**RESEARCH, "instrument.slippage_ticks": 2})
    acct = run(base, feats, {})

    t = edge["trades"].copy()
    t["entry_date"] = pd.to_datetime(t["entry_ts"]).map(lambda x: x.date())
    t["year"] = pd.to_datetime(t["entry_ts"]).map(lambda x: x.year)
    ps = plain_stats(feats, variant)
    fh = ps.pop("first_half_hour_abs_ret")
    t["vol_day"] = np.where(t["entry_date"].map(fh) > fh.median(), "high", "low")

    by_year = breakdown(t, "year")
    full_years = by_year.loc[[y for y in by_year.index if 2019 <= y <= 2024], "net"]
    post = t[t["entry_date"] >= POST_PUB]["net"].sum()
    s = edge["summary"]
    checks = {
        "1_profit_factor_ge_1.20": s["profit_factor"] >= 1.20,
        "2_t_stat_ge_2.5": t_stat(t["net"]) >= 2.5,
        "3a_positive_years_ge_4_of_6": int((full_years > 0).sum()) >= 4,
        "3b_post_publication_net_positive": post > 0,
        "4_positive_at_2_ticks": slip2["summary"].get("net_profit", -1) > 0,
    }
    report = {
        "variant": variant,
        "edge_1tick": s, "gross_before_commissions": round(float(t["gross"].sum()), 2),
        "t_stat_net": round(t_stat(t["net"]), 2),
        "post_publication_net": round(float(post), 2),
        "positive_full_years": f"{int((full_years > 0).sum())} of {len(full_years)}",
        "edge_2tick": slip2["summary"], "account_10k_default": acct["summary"],
        "plain_stats_before_costs": ps, "monte_carlo": edge.get("monte_carlo"),
        "exit_kinds": t["exit_kind"].value_counts().to_dict(),
        "pass_checks": checks, "PASS": all(checks.values()),
    }
    print(json.dumps(report, indent=2, default=str))
    for k in ("year", "side", "vol_day"):
        print(f"\n== by {k} ==\n{breakdown(t, k).to_string()}")
    t.to_csv(out / f"trades_{variant}.csv", index=False)
    (out / f"report_{variant}.json").write_text(json.dumps(report, indent=2, default=str))
    by_year.to_csv(out / f"by_year_{variant}.csv")


if __name__ == "__main__":
    main(*sys.argv[1:4])
