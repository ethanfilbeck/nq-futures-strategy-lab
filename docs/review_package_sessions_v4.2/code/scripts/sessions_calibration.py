"""Monte Carlo calibration of the sessions-study tests on SYNTHETIC data only (no market data is read).

    py scripts/sessions_calibration.py --reps 20000 --out runs/sessions_calibration.json

For each scenario, the production code path is used unchanged: nq_bot.sessions.point_stats,
stationary_indices (mean block 20), bootstrap_family, centered_p and percentile_ci. The only deviation from the
protocol is B: 999 bootstrap replicates instead of 10,000. That changes the Monte Carlo resolution of each p
(steps of 0.001), not the test being calibrated; 1/(B+1) = 0.001 still lies below Holm's first threshold of 0.002.

Why one null scenario per test: the five nulls cannot hold in one data-generating process. V1's null (equal
variance PER HOUR) makes overnight variance 16.5/6.5 times RTH's per session, while L1's null (delta-p = 0 by
symmetry) needs EQUAL per-session variance. Each test is therefore calibrated under its own null; Holm then
controls the family-wise rate for any dependence among valid p-values.

Seeds: data rng = default_rng([scenario_id, rep, 1]); bootstrap rng = default_rng([scenario_id, rep, 2]).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nq_bot import sessions as S  # noqa: E402

N = 1230                  # development primary sample (protocol section 5.2)
B = 999
DATES = pd.bdate_range("2020-01-02", periods=N)
V1M = np.asarray(DATES.dayofweek.isin([1, 2, 3, 4]))     # Tue-Fri, about 984 (protocol: 983)
SD_ON = 0.006
SD_RTH_PH = SD_ON * math.sqrt(S.RTH_HOURS / S.ON_HOURS)   # equal per-hour variance
ALPHAS = (0.05, 0.01, 0.002)

SCENARIOS = {
    # id: (name, tests computed, true theta per test, description)
    1: ("V1_null_iid", ("V1",), {"V1": 0.0}, "iid Gaussian, equal per-hour variance"),
    2: ("V1_null_garch", ("V1",), {"V1": 0.0}, "GARCH(1,1) clustering (a=0.08, b=0.90), equal per-hour unconditional variance"),
    3: ("T_null_t4", ("T1", "T2"), {"T1": 0.0, "T2": 0.0}, "iid Student-t(4) in both series, different scales (same tail shape)"),
    4: ("P1_null", ("P1",), {"P1": 0.0}, "iid Gaussian, equal per-hour variance; volume share set to the population WPC 16.5/23"),
    5: ("L1_null", ("L1",), {"L1": 0.0}, "iid Gaussian, equal per-session variance (delta-p = 0 by symmetry)"),
    6: ("V1_coverage_ratio3", ("V1",), {"V1": math.log(3.0)}, "iid Gaussian, per-hour variance ratio 3 (coverage only)"),
    # volatility clustering through ONE common GARCH(1,1) volatility (a=0.08, b=0.90) scaling both series, so
    # the ratio of conditional variances is constant and each null holds exactly (P1: population WPC = share)
    7: ("T_null_common_garch", ("T1", "T2"), {"T1": 0.0, "T2": 0.0}, "common GARCH volatility, t(4) innovations in both series"),
    8: ("P1_null_common_garch", ("P1",), {"P1": 0.0}, "common GARCH volatility, Gaussian innovations, equal per-hour variance; volume share 16.5/23"),
    9: ("L1_null_common_garch", ("L1",), {"L1": 0.0}, "common GARCH volatility, Gaussian innovations, equal per-session variance"),
    10: ("V1_null_common_garch", ("V1",), {"V1": 0.0}, "common GARCH volatility, Gaussian innovations, equal per-hour variance"),
    # DIAGNOSTICS ONLY (not protocol rules): V1 under scenario 2 with longer bootstrap blocks
    11: ("DIAG_V1_garch_block40", ("V1",), {"V1": 0.0}, "scenario 2 data, mean block 40 (= sensitivity S9's long block)"),
    12: ("DIAG_V1_garch_block100", ("V1",), {"V1": 0.0}, "scenario 2 data, mean block 100 (diagnostic only)"),
}
BLOCK = {11: 40, 12: 100}


def common_vol(rng: np.random.Generator, n: int, a: float = 0.08, b: float = 0.90) -> np.ndarray:
    """Conditional sd path of a unit-variance GARCH(1,1); used to scale both ON and RTH."""
    w = 1 - a - b
    s2 = 1.0
    burn = 500
    e = rng.normal(size=n + burn)
    sd = np.empty(n)
    for i in range(n + burn):
        if i >= burn:
            sd[i - burn] = math.sqrt(s2)
        r = math.sqrt(s2) * e[i]
        s2 = w + a * r * r + b * s2
    return sd


def garch(rng: np.random.Generator, n: int, uncond_sd: float, a: float = 0.08, b: float = 0.90) -> np.ndarray:
    w = uncond_sd ** 2 * (1 - a - b)
    s2 = uncond_sd ** 2
    out = np.empty(n)
    burn = 500
    e = rng.normal(size=n + burn)
    for i in range(n + burn):
        r = math.sqrt(s2) * e[i]
        if i >= burn:
            out[i - burn] = r
        s2 = w + a * r * r + b * s2
    return out


def make(sid: int, rng: np.random.Generator):
    v_on, v_rth = np.full(N, 10.0), np.full(N, 30.0)
    if sid in (1, 4):
        on, rth = rng.normal(0, SD_ON, N), rng.normal(0, SD_RTH_PH, N)
        if sid == 4:
            share = S.ON_HOURS / (S.ON_HOURS + S.RTH_HOURS)        # population WPC = var share = 16.5/23
            v_on, v_rth = np.full(N, share * 1000), np.full(N, (1 - share) * 1000)
    elif sid == 2:
        on, rth = garch(rng, N, SD_ON), garch(rng, N, SD_RTH_PH)
    elif sid == 3:
        on = SD_ON * rng.standard_t(4, N) / math.sqrt(2)
        rth = 0.012 * rng.standard_t(4, N) / math.sqrt(2)
    elif sid == 5:
        on, rth = rng.normal(0, 0.01, N), rng.normal(0, 0.01, N)
    elif sid == 6:
        on = rng.normal(0, SD_ON, N)
        rth = rng.normal(0, SD_RTH_PH * math.sqrt(3.0), N)
    elif sid in (11, 12):
        on, rth = garch(rng, N, SD_ON), garch(rng, N, SD_RTH_PH)
    else:
        sd = common_vol(rng, N)
        if sid == 7:
            on = sd * SD_ON * rng.standard_t(4, N) / math.sqrt(2)
            rth = sd * 0.012 * rng.standard_t(4, N) / math.sqrt(2)
        elif sid == 9:
            on, rth = sd * rng.normal(0, 0.01, N), sd * rng.normal(0, 0.01, N)
        else:
            on, rth = sd * rng.normal(0, SD_ON, N), sd * rng.normal(0, SD_RTH_PH, N)
            if sid == 8:
                share = S.ON_HOURS / (S.ON_HOURS + S.RTH_HOURS)
                v_on, v_rth = np.full(N, share * 1000), np.full(N, (1 - share) * 1000)
    return on, rth, v_on, v_rth


def one(args):
    sid, rep = args
    name, which, truth, _ = SCENARIOS[sid]
    on, rth, v_on, v_rth = make(sid, np.random.default_rng([sid, rep, 1]))
    need_z = ("T1" in which) or ("T2" in which)
    z_on = S.ewma_scale(on) if need_z else np.zeros(N)
    z_rth = S.ewma_scale(rth) if need_z else np.zeros(N)
    th = S.point_stats(on, rth, z_on, z_rth, v_on, v_rth, V1M, which)
    idx = S.stationary_indices(N, BLOCK.get(sid, S.BLOCK_DEV), B, np.random.default_rng([sid, rep, 2]))
    bt = S.bootstrap_family(on, rth, z_on, z_rth, v_on, v_rth, V1M, idx, which)
    res = {}
    for t in which:
        p = S.centered_p(th[t], bt[t])
        lo, hi = S.percentile_ci(bt[t], 0.99)
        res[t] = (p, lo <= truth[t] <= hi)
    return sid, res


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score 95% interval (closed form; no extra dependency)."""
    if n == 0:
        return float("nan"), float("nan")
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=20000)
    ap.add_argument("--reps-diag", type=int, default=5000)
    ap.add_argument("--scenarios", default="1,2,3,4,5,6")
    ap.add_argument("--out", default="runs/sessions_calibration.json")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    sids = [int(s) for s in a.scenarios.split(",")]
    reps = {s: (a.reps_diag if s in BLOCK else a.reps) for s in sids}
    jobs = [(s, r) for s in sids for r in range(reps[s])]
    t0 = time.time()
    tally: dict[int, dict[str, dict]] = {s: {} for s in sids}
    with Pool(a.workers) as pool:
        for i, (sid, res) in enumerate(pool.imap_unordered(one, jobs, chunksize=50)):
            for t, (p, cov) in res.items():
                d = tally[sid].setdefault(t, {"n": 0, "cov": 0, **{f"rej_{al}": 0 for al in ALPHAS}})
                d["n"] += 1
                d["cov"] += int(cov)
                for al in ALPHAS:
                    d[f"rej_{al}"] += int(p <= al)
            if (i + 1) % 5000 == 0:
                print(f"{i + 1}/{len(jobs)} done, {time.time() - t0:.0f}s", flush=True)
    report: dict[str, Any] = {"synthetic_only": True, "n_sessions": N, "B": B, "mean_block": S.BLOCK_DEV,
              "seed_rule": "data rng = default_rng([scenario_id, rep, 1]); bootstrap rng = default_rng([scenario_id, rep, 2])",
              "elapsed_seconds": round(time.time() - t0), "scenarios": {}}
    for sid in sids:
        name, which, truth, desc = SCENARIOS[sid]
        sc: dict[str, Any] = {"id": sid, "description": desc, "reps": reps[sid], "mean_block": BLOCK.get(sid, S.BLOCK_DEV),
              "diagnostic_only": sid in BLOCK, "tests": {}}
        for t, d in tally[sid].items():
            n = d["n"]
            row: dict[str, Any] = {"true_theta": truth[t]}
            if sid != 6:   # 6 is a coverage-only scenario (alternative true)
                for al in ALPHAS:
                    k = d[f"rej_{al}"]
                    lo, hi = wilson(k, n)
                    row[f"alpha_{al}"] = {"rejections": k, "expected": al * n, "rate": k / n, "wilson95": [lo, hi]}
            lo, hi = wilson(d["cov"], n)
            row["ci99_coverage"] = {"covered": d["cov"], "expected": 0.99 * n, "rate": d["cov"] / n, "wilson95": [lo, hi]}
            sc["tests"][t] = row
        report["scenarios"][name] = sc
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
