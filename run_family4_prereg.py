"""Run the pre-registered Family 4 tests (docs/PREREG_FAMILY4.md) once, on training data only."""
import json
import sys
from pathlib import Path

from nq_bot import family3 as f3
from nq_bot import family4 as f4
from nq_bot.data import load_csv

TRAIN_END = "2025-06-30 23:59"
T_BAR = 3.5


def verdict(name, trades, pool=None, min_trades=None):
    base, slip2 = f3.stats(trades), f3.stats(trades, extra_ticks=1)
    years = f3.by_year(trades)
    pos_years = sum(1 for y, v in years.items() if 2019 <= y <= 2024 and v > 0)
    s21 = f3.since_2021(trades)
    checks = {"pf>=1.20": base.get("pf", 0) >= 1.20, f"t>={T_BAR}": base.get("t", 0) >= T_BAR,
              ">=4 of 6 years positive and 2021+ positive": pos_years >= 4 and s21 > 0,
              "positive at 2-tick slippage": slip2.get("net", 0) > 0}
    extra = {}
    if pool is not None:
        p95, pm = f3.bootstrap_p95(pool, base["n"])
        extra = {"benchmark_pool_size": len(pool), "benchmark_mean_per_trade": pm, "benchmark_p95_of_means": p95}
        checks["beats random 1-day long holds (> 95th pct)"] = base["mean"] > p95
    if min_trades:
        checks[f">={min_trades} trades"] = base["n"] >= min_trades
    kinds = {}
    for t in trades:
        kinds[t.kind] = kinds.get(t.kind, 0) + 1
    return {"name": name, "stats_1tick": base, "stats_2tick": slip2, "by_year": years, "exits": kinds,
            "positive_years_2019_2024": pos_years, "net_since_2021": s21, **extra,
            "checks": checks, "PASS": all(checks.values())}


def main(csv):
    bars = load_csv(csv)
    bars = bars[bars.index <= TRAIN_END]
    s = f4.Session4(bars)
    out = {"data": [str(bars.index[0]), str(bars.index[-1])], "trading_days": len(s.days)}
    h9, sk9 = f4.run_h9(s)
    out["H9"] = verdict("H9 macro announcement days", h9, f4.one_day_pool(s, set(f4.macro_days(s)))) | {"skipped": sk9}
    h10, sk10 = f4.run_h10(s)
    ph = f4.pre_holidays(s)
    out["H10"] = verdict("H10 pre-holiday", h10, f4.one_day_pool(s, set(ph))) | {"skipped": sk10,
                                                                               "pre_holiday_days": [str(d) for d in ph]}
    h11 = f4.run_h11(s)
    out["H11"] = verdict("H11 opening-hour trend after high-range day", h11, min_trades=150)
    Path("runs").mkdir(exist_ok=True)
    Path("runs/family4_results.json").write_text(json.dumps(out, indent=2, default=str))
    for k in ("H9", "H10", "H11"):
        r, b = out[k], out[k]["stats_1tick"]
        print(f"{r['name']}: n={b['n']} net=${b['net']:,.0f} mean=${b['mean']:.2f} PF={b['pf']:.2f} "
              f"t={b['t']:.2f}  -> {'PASS' if r['PASS'] else 'FAIL'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/mnq_train.csv")
