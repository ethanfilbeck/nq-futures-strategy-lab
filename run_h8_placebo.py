"""The pre-registered H8 placebo tests (docs/PREREG_H8_PLACEBO.md). Run once.

    py run_h8_placebo.py

Test A: the same frozen rule on sham dates offset -21/-14/-7/+7/+14/+21 days from each real FOMC date.
Test B: a Wednesday-matched null, bootstrapping the t-statistic rather than the mean.

Costs nothing: runs on MNQ, MES and M2K bars already on disk. The verdict is read off MNQ.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from nq_bot import family3 as f3
from nq_bot.data import load_csv

NAME = "h8_placebo"
OFFSETS = (-21, -14, -7, 7, 14, 21)   # frozen in the pre-registration; no others are computed
NEAR = 3                              # drop sham dates within this many trading days of a real event
BOOT = 10_000
SEED = 7
REAL = f3.FOMC_DAYS + f3.HOLDOUT_FOMC_DAYS

# market -> (csv paths, $/point, tick, commission round turn)
MARKETS = {
    "MNQ (Nasdaq 100 micro, all 59)": (["data/mnq_train.csv", "data/mnq_holdout.csv"], 2.0, 0.25, 1.24),
    "MES (S&P 500 micro)":            (["data/mes_2019_2026.csv"], 5.0, 0.25, 1.24),
    "M2K (Russell 2000 micro)":       (["data/m2k_2019_2026.csv"], 5.0, 0.10, 1.24),
}


def tstat(x) -> float:
    x = np.asarray(x, dtype=float)
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 1 else float("nan")


def load(paths):
    """One ET-indexed frame from one or more CSVs, de-duplicated and sorted."""
    frames = [load_csv(p) for p in paths]
    bars = pd.concat(frames).sort_index()
    return bars[~bars.index.duplicated(keep="first")]


def banned_days(s: f3.Session) -> set:
    """Trading days within NEAR trading days of any real FOMC date, either side."""
    out = set()
    for ds in REAL:
        d = pd.Timestamp(ds).date()
        i = s.day_index.get(d)
        if i is None:
            continue
        for j in range(i - NEAR, i + NEAR + 1):
            if 0 <= j < len(s.days):
                out.add(s.days[j])
    return out


def sham_dates(s: f3.Session, offset: int, banned: set) -> list[str]:
    """Each real FOMC date shifted by `offset` calendar days, minus anything near a real event."""
    keep = []
    for ds in REAL:
        d = (pd.Timestamp(ds) + pd.Timedelta(days=offset)).date()
        if d in banned or d not in s.day_index or s.day_index[d] == 0:
            continue
        keep.append(str(d))
    return keep


def series_pnl(s: f3.Session, bars, dates, pt, comm) -> np.ndarray:
    trades, _ = f3.run_h8(s, dates)
    return np.array([(t.exit - t.entry) * t.side * pt - comm for t in trades], dtype=float)


def wednesday_pool(s: f3.Session, banned: set, pt, comm) -> np.ndarray:
    """Consecutive trading-day pairs whose EXIT day is a Wednesday and which avoid every real event."""
    pool = []
    for i in range(len(s.days) - 1):
        p, e = s.days[i], s.days[i + 1]
        if p in banned or e in banned or e.weekday() != 2:
            continue
        a, b = s.bar(p, "14:00"), s.bar(e, "13:55")
        if a and b:
            t = f3._hold(s, a[0], a[1].open + f3.TICK, b[0], b[1].close, 0.03)
            pool.append((t.exit - t.entry) * t.side * pt - comm)
    return np.array(pool, dtype=float)


def main(outdir="runs", allow_rerun=False):
    out_json = Path(outdir) / f"{NAME}.json"
    if out_json.exists() and not allow_rerun:
        raise SystemExit(f"{out_json} already exists. These tests are pre-registered to run once.")

    results = {}
    for market, (paths, pt, tick, comm) in MARKETS.items():
        print(f"\n===== {market} =====", flush=True)
        f3.TICK = tick
        bars = load(paths)
        s = f3.Session(bars)
        banned = banned_days(s)

        real = series_pnl(s, bars, REAL, pt, comm)
        t_real = tstat(real)
        print(f"real FOMC      n={len(real):3d}  net=${real.sum():10,.2f}  mean=${real.mean():8.2f}  t={t_real:5.2f}")

        shams = {}
        for off in OFFSETS:
            dates = sham_dates(s, off, banned)
            pnl = series_pnl(s, bars, dates, pt, comm)
            shams[off] = {"n": len(pnl), "net": float(pnl.sum()), "mean": float(pnl.mean()), "t": tstat(pnl)}
            print(f"sham {off:+3d} days  n={len(pnl):3d}  net=${pnl.sum():10,.2f}  mean=${pnl.mean():8.2f}"
                  f"  t={shams[off]['t']:5.2f}")

        sham_ts = [v["t"] for v in shams.values()]
        real_is_best = all(t_real > t for t in sham_ts)
        any_sham_significant = any(t >= 2.0 for t in sham_ts)
        best_sham = max(shams.items(), key=lambda kv: kv[1]["t"])

        pool = wednesday_pool(s, banned, pt, comm)
        rng = np.random.default_rng(SEED)
        draws = rng.choice(pool, size=(BOOT, len(real)), replace=True)
        boot_t = draws.mean(axis=1) / (draws.std(axis=1, ddof=1) / np.sqrt(len(real)))
        p_emp = float((boot_t >= t_real).mean())
        print(f"Wednesday null pool n={len(pool)}  mean=${pool.mean():.2f}  "
              f"bootstrap p(t >= {t_real:.2f}) = {p_emp:.4f}")

        if not real_is_best:
            verdict = "PLACEBO FAILS - the pre-FOMC window is not special"
        elif any_sham_significant:
            verdict = "PARTIAL - real is best, but a sham also reaches t>=2.0; discount the effect size"
        else:
            verdict = "PLACEBO CLEAN - real is best and no sham reaches t>=2.0"
        print(f"  Test A: {verdict}")
        print(f"  Test B: {'PASS' if p_emp < 0.05 else 'FAIL'}  p={p_emp:.4f} vs 0.05")

        results[market] = {
            "real": {"n": len(real), "net": float(real.sum()), "mean": float(real.mean()), "t": t_real},
            "shams": {str(k): v for k, v in shams.items()},
            "real_is_best": bool(real_is_best), "any_sham_t_ge_2": bool(any_sham_significant),
            "best_sham_offset": str(best_sham[0]), "best_sham_t": best_sham[1]["t"],
            "best_sham_mean": best_sham[1]["mean"],
            "wednesday_pool_n": len(pool), "wednesday_pool_mean": float(pool.mean()),
            "wednesday_bootstrap_p": p_emp, "test_b_pass": bool(p_emp < 0.05),
            "test_a_verdict": verdict,
        }

    Path(outdir).mkdir(exist_ok=True)
    out_json.write_text(json.dumps({"offsets": list(OFFSETS), "near_trading_days": NEAR, "bootstrap": BOOT,
                                    "seed": SEED, "markets": results}, indent=2))
    primary = next(iter(MARKETS))
    print(f"\nPRIMARY ({primary}): {results[primary]['test_a_verdict']}")
    print(f"Wednesday-matched null: p = {results[primary]['wednesday_bootstrap_p']:.4f}")


if __name__ == "__main__":
    main(allow_rerun="--rerun" in sys.argv)
