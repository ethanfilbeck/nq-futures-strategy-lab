"""DIAGNOSTIC ONLY (approved by Ethan 2026-11-12): P1 calibration with 9,999 inner bootstrap resamples.

SYNTHETIC data only; no market data is read. Nothing here changes a method, threshold or protocol rule.

Re-runs calibration scenarios 4 (iid Gaussian) and 8 (common GARCH volatility) for P1, 20,000 repetitions each,
with the frozen production code path (nq_bot.sessions.point_stats, stationary_indices with mean block 20,
bootstrap_family, centered_p, percentile_ci) and the data generators of scripts/sessions_calibration.py,
imported unchanged.

Paired design: every repetition computes BOTH
  * B = 999   (the original calibration setting; reproduces SESSIONS_CALIBRATION.json exactly), and
  * B = 9,999 (the diagnostic setting),
on the SAME synthetic dataset. Seeds (identical to the original seed rule):
  data rng      = default_rng([scenario_id, rep, 1])
  bootstrap rng = default_rng([scenario_id, rep, 2])   (a fresh generator for each B)

Runs in chunks so a long job can be resumed:
    python scripts/sessions_calibration_p1_b9999.py run --scenario 4 --start 0 --stop 5000
    python scripts/sessions_calibration_p1_b9999.py summarise --out runs/sessions_calibration_p1_b9999.json
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sessions_calibration as C  # noqa: E402

from nq_bot import sessions as S  # noqa: E402

B_ORIG, B_DIAG = 999, 9999
SCENARIOS = (4, 8)
REPS = 20000
CHUNK_DIR = Path("runs/sessions_calibration_p1_b9999_chunks")
ALPHAS = (0.05, 0.01, 0.002)


def one(args):
    sid, rep = args
    _, which, truth, _ = C.SCENARIOS[sid]
    assert which == ("P1",)
    on, rth, v_on, v_rth = C.make(sid, np.random.default_rng([sid, rep, 1]))
    z = np.zeros(C.N)
    th = S.point_stats(on, rth, z, z, v_on, v_rth, C.V1M, which)["P1"]
    out = []
    for b in (B_ORIG, B_DIAG):
        idx = S.stationary_indices(C.N, S.BLOCK_DEV, b, np.random.default_rng([sid, rep, 2]))
        bt = S.bootstrap_family(on, rth, z, z, v_on, v_rth, C.V1M, idx, which)["P1"]
        lo, hi = S.percentile_ci(bt, 0.99)
        out += [S.centered_p(th, bt), float(lo <= truth["P1"] <= hi)]
    return rep, out


def run(sid: int, start: int, stop: int, workers: int) -> None:
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    f = CHUNK_DIR / f"s{sid}_{start:05d}_{stop:05d}.npy"
    if f.exists():
        print(f"{f} exists; skipping")
        return
    t0 = time.time()
    res = np.full((stop - start, 5), np.nan)
    with Pool(workers) as pool:
        for i, (rep, vals) in enumerate(pool.imap_unordered(one, [(sid, r) for r in range(start, stop)], chunksize=10)):
            res[rep - start] = [rep, *vals]
            if (i + 1) % 500 == 0:
                print(f"s{sid} {start + i + 1}/{stop}  {time.time() - t0:.0f}s", flush=True)
    assert np.isfinite(res).all()
    np.save(f, res)
    print(f"wrote {f} in {time.time() - t0:.0f}s", flush=True)


def summarise(out: str) -> None:
    rep: dict = {"diagnostic_only": True, "synthetic_only": True, "approved": "Ethan, 2026-11-12",
                 "n_sessions": C.N, "mean_block": S.BLOCK_DEV, "B_compared": [B_ORIG, B_DIAG],
                 "seed_rule": "data rng = default_rng([scenario_id, rep, 1]); bootstrap rng = "
                              "default_rng([scenario_id, rep, 2]), a fresh generator for each B",
                 "python": platform.python_version(), "numpy": np.__version__, "scenarios": {}}
    for sid in SCENARIOS:
        files = sorted(CHUNK_DIR.glob(f"s{sid}_*.npy"))
        a = np.concatenate([np.load(f) for f in files])
        reps = np.sort(a[:, 0].astype(int))
        assert np.array_equal(reps, np.arange(REPS)), f"scenario {sid}: incomplete or duplicated reps"
        p999, c999, p9999, c9999 = a[:, 1], a[:, 2], a[:, 3], a[:, 4]
        n = len(a)
        sc: dict = {"id": sid, "description": C.SCENARIOS[sid][3], "reps": n, "chunks": [f.name for f in files]}
        for label, p, c in (("B_999", p999, c999), ("B_9999", p9999, c9999)):
            row: dict = {}
            for al in ALPHAS:
                k = int(np.sum(p <= al))
                row[f"alpha_{al}"] = {"rejections": k, "expected": al * n, "rate": k / n, "wilson95": list(C.wilson(k, n))}
            k = int(c.sum())
            row["ci99_coverage"] = {"covered": k, "expected": 0.99 * n, "rate": k / n, "wilson95": list(C.wilson(k, n))}
            sc[label] = row
        paired: dict[str, Any] = {}
        for al in ALPHAS:
            r1, r2 = p999 <= al, p9999 <= al
            only1, only2 = int(np.sum(r1 & ~r2)), int(np.sum(~r1 & r2))
            paired[f"alpha_{al}"] = {"reject_999_only": only1, "reject_9999_only": only2,
                                     "both": int(np.sum(r1 & r2)),
                                     "mcnemar_z": (only2 - only1) / np.sqrt(only1 + only2) if only1 + only2 else 0.0}
        cb, cc = int(np.sum((c999 == 1) & (c9999 == 0))), int(np.sum((c999 == 0) & (c9999 == 1)))
        paired["ci99_coverage"] = {"covered_999_only": cb, "covered_9999_only": cc,
                                   "mcnemar_z": (cc - cb) / np.sqrt(cb + cc) if cb + cc else 0.0}
        paired["corr_p999_p9999"] = float(np.corrcoef(p999, p9999)[0, 1])
        sc["paired_comparison"] = paired
        rep["scenarios"][f"P1_scenario_{sid}"] = sc
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--scenario", type=int, choices=SCENARIOS, required=True)
    r.add_argument("--start", type=int, required=True)
    r.add_argument("--stop", type=int, required=True)
    r.add_argument("--workers", type=int, default=2)
    s = sub.add_parser("summarise")
    s.add_argument("--out", default="runs/sessions_calibration_p1_b9999.json")
    a = ap.parse_args()
    if a.cmd == "run":
        run(a.scenario, a.start, a.stop, a.workers)
    else:
        summarise(a.out)


if __name__ == "__main__":
    main()
