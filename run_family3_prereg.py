"""Run the pre-registered Family 3 tests (docs/PREREG_FAMILY3.md) once, on training data only."""
import json
import sys
from pathlib import Path

from nq_bot.data import load_csv
from nq_bot import family3 as f3

TRAIN_END = "2025-06-30 23:59"


def verdict(name, trades, pool=None):
    base, slip2 = f3.stats(trades), f3.stats(trades, extra_ticks=1)
    years = f3.by_year(trades)
    pos_years = sum(1 for y, v in years.items() if 2019 <= y <= 2024 and v > 0)
    s21 = f3.since_2021(trades)
    checks = {
        "pf>=1.20": base.get("pf", 0) >= 1.20,
        "t>=3.0": base.get("t", 0) >= 3.0,
        ">=4 of 6 years 2019-2024 positive and 2021+ positive": pos_years >= 4 and s21 > 0,
        "positive at 2-tick slippage": slip2.get("net", 0) > 0,
    }
    extra = {}
    if pool is None:
        checks[">=200 trades"] = base["n"] >= 200
    else:
        p95, pool_mean = f3.bootstrap_p95(pool, base["n"])
        extra = {"benchmark_pool_size": len(pool), "benchmark_mean_per_trade": pool_mean,
                 "benchmark_p95_of_means": p95}
        checks["beats random long holds (> 95th pct)"] = base["mean"] > p95
    kinds = {}
    for t in trades:
        kinds[t.kind] = kinds.get(t.kind, 0) + 1
    return {"name": name, "stats_1tick": base, "stats_2tick": slip2, "by_year": years,
            "positive_years_2019_2024": pos_years, "net_since_2021": s21, "exits": kinds,
            **extra, "checks": checks, "PASS": all(checks.values())}


def main(csv):
    bars = load_csv(csv)
    bars = bars[bars.index <= TRAIN_END]
    s = f3.Session(bars)
    out = {"data": [str(bars.index[0]), str(bars.index[-1])], "trading_days": len(s.days)}
    h6, sk6 = f3.run_h6(s)
    out["H6"] = verdict("H6 turn of the month", h6, f3.h6_benchmark_pool(s)) | {"skipped_missing_bar": sk6}
    h7, sk7 = f3.run_h7(s)
    out["H7"] = verdict("H7 overnight-gap reversal", h7) | {"skipped_gap_already_filled": sk7}
    h8, sk8 = f3.run_h8(s)
    out["H8"] = verdict("H8 pre-FOMC drift", h8, f3.h8_benchmark_pool(s)) | {"skipped_missing": sk8}
    Path("runs").mkdir(exist_ok=True)
    Path("runs/family3_results.json").write_text(json.dumps(out, indent=2, default=str))
    for k in ("H6", "H7", "H8"):
        r = out[k]
        b = r["stats_1tick"]
        print(f"{r['name']}: n={b['n']} net=${b['net']:,.0f} mean=${b['mean']:.2f} PF={b['pf']:.2f} "
              f"t={b['t']:.2f}  -> {'PASS' if r['PASS'] else 'FAIL'}")
    return out


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/mnq_train.csv")
