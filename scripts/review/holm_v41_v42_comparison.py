"""Reviewer aid (audit PD-4): compare v4.1 Holm (V1's observed p in the five-test family) with v4.2 Holm
(V1's slot = administrative placeholder 1.0). Synthetic random p-values only; no data is read.

    python scripts/review/holm_v41_v42_comparison.py

Uses the project's own `holm` and `holm_with_placeholder`, unchanged.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from nq_bot import sessions as S  # noqa: E402

N, SEED = 200_000, 1


def main() -> None:
    rng = np.random.default_rng(SEED)
    n_v1_not_rejected = dec_diff = adj_diff = 0
    for _ in range(N):
        both = np.stack([rng.uniform(0, 0.02, 5), rng.uniform(0, 1, 5)])
        v = np.asarray(rng.choice(both), dtype=float)                      # one of the two rows, at random
        p = {t: float(x) for t, x in zip(S.TESTS, v)}
        a41, r41 = S.holm(p)                       # v4.1: observed V1 p in the family
        if r41["V1"]:
            continue
        n_v1_not_rejected += 1
        a42, r42, _ = S.holm_with_placeholder(p)   # v4.2: V1 slot = 1.0
        if any(r41[t] != r42[t] for t in S.INFERENTIAL_TESTS):
            dec_diff += 1
        if any(abs(a41[t] - a42[t]) > 1e-15 for t in S.INFERENTIAL_TESTS):
            adj_diff += 1
    print(f"random p-vectors: {N:,}; seed {SEED}")
    print(f"V1 not rejected under v4.1: {n_v1_not_rejected:,}")
    print(f"  ...with any rejection-decision difference for T1/T2/P1/L1: {dec_diff:,}")
    print(f"  ...with any adjusted-p difference for T1/T2/P1/L1: {adj_diff:,} "
          f"({100 * adj_diff / n_v1_not_rejected:.1f}%)")


if __name__ == "__main__":
    main()
