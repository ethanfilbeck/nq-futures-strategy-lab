"""Probability of Backtest Overfitting by combinatorially symmetric cross-validation (CSCV).

Method from Bailey, Borwein, Lopez de Prado & Zhu, "The probability of backtest overfitting",
Journal of Computational Finance 20(4), 39-69 (2017). See docs/QUANTITATIVE_RESEARCH_LITERATURE_REVIEW.md.

The question CSCV answers: across many balanced train/test splits, how often does the configuration that
looked BEST in-sample land BELOW MEDIAN out-of-sample? That frequency is the PBO. It is a property of the
SELECTION PROCEDURE, not of any strategy.

What PBO is not: it is not a profitability test. A low PBO does not show a strategy has an edge; it shows the
selection procedure is not obviously picking noise. A high PBO is evidence that it is.

CSCV is non-parametric and operates on the joint matrix of returns, so correlated strategies are handled
directly - it never assumes the trials are independent.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd


def _sharpe_from_blocks(mask: np.ndarray, cnt: np.ndarray, s1: np.ndarray, s2: np.ndarray) -> np.ndarray:
    """Sharpe of every strategy for every combination, from per-block aggregates.

    mask: (C, S) boolean, which blocks are in this side of the split.
    cnt: (S,) rows per block. s1: (S, N) sums. s2: (S, N) sums of squares.
    Returns (C, N). Sharpe here is mean/sd of DAILY P&L, not annualised: annualising multiplies every
    strategy by the same constant, so it cannot change a rank, which is all CSCV uses.
    """
    n = mask @ cnt                                        # (C,)
    tot = mask.astype(float) @ s1                         # (C, N)
    sq = mask.astype(float) @ s2                          # (C, N)
    nn = n[:, None]
    mean = tot / nn
    var = (sq - nn * mean**2) / (nn - 1)
    sd = np.sqrt(np.maximum(var, 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(sd > 0, mean / sd, 0.0)
    return out


def cscv(matrix: pd.DataFrame, s_blocks: int = 16) -> dict:
    """Run CSCV on a T x N matrix of per-period P&L. `s_blocks` must be even.

    Rows are split into `s_blocks` contiguous equal blocks in time order; every balanced choice of
    half the blocks forms the training set and its complement the test set.
    """
    if s_blocks % 2:
        raise ValueError("s_blocks must be even")
    names = list(matrix.columns)
    n_strats = len(names)
    if n_strats < 2:
        raise ValueError("CSCV needs at least 2 strategies")
    arr = matrix.to_numpy(dtype=float)
    t_total = len(arr)
    per = t_total // s_blocks
    if per < 2:
        raise ValueError(f"{t_total} rows is too few for {s_blocks} blocks")
    used = per * s_blocks
    arr = arr[:used]                                       # trailing rows dropped, reported below

    blocks = arr.reshape(s_blocks, per, n_strats)
    cnt = np.full(s_blocks, per, dtype=float)
    s1 = blocks.sum(axis=1)                                # (S, N)
    s2 = (blocks**2).sum(axis=1)                           # (S, N)

    combos = list(combinations(range(s_blocks), s_blocks // 2))
    mask = np.zeros((len(combos), s_blocks), dtype=bool)
    for i, c in enumerate(combos):
        mask[i, list(c)] = True

    is_sharpe = _sharpe_from_blocks(mask, cnt, s1, s2)     # (C, N)
    oos_sharpe = _sharpe_from_blocks(~mask, cnt, s1, s2)   # (C, N)

    winner = is_sharpe.argmax(axis=1)                      # (C,)
    rows = np.arange(len(combos))
    star = oos_sharpe[rows, winner]                        # winner's OOS Sharpe

    # rank of the winner among N OOS values, 1 = worst, N = best; ties share the average rank
    less = (oos_sharpe < star[:, None]).sum(axis=1)
    equal = (oos_sharpe == star[:, None]).sum(axis=1)
    rank = less + (equal + 1) / 2.0                        # average rank over ties, includes the winner

    omega = rank / (n_strats + 1.0)
    lam = np.log(omega / (1.0 - omega))
    pbo = float((lam <= 0).mean())

    sel = {names[i]: int((winner == i).sum()) for i in range(n_strats)}
    return {
        "n_strategies": n_strats, "strategies": names,
        "rows_used": int(used), "rows_dropped": int(t_total - used),
        "s_blocks": s_blocks, "block_size": int(per), "n_combinations": len(combos),
        "pbo": pbo,
        "lambda_mean": float(lam.mean()), "lambda_median": float(np.median(lam)),
        "median_oos_rank_of_winner": float(np.median(rank)),
        "winner_oos_below_median_count": int((lam <= 0).sum()),
        "selected_in_sample_counts": dict(sorted(sel.items(), key=lambda kv: -kv[1])),
        "mean_is_sharpe_of_winner": float(is_sharpe[rows, winner].mean()),
        "mean_oos_sharpe_of_winner": float(star.mean()),
        "prob_winner_oos_sharpe_negative": float((star < 0).mean()),
        "_lambda": lam, "_is_star": is_sharpe[rows, winner], "_oos_star": star,
    }


def daily_matrix(series: dict[str, pd.Series], calendar: list) -> pd.DataFrame:
    """Align per-strategy daily P&L onto one calendar.

    A day on which a strategy held no position has P&L of exactly zero. That is a REAL observation, not a
    missing one, so it is filled with 0 deliberately. A strategy that could not be evaluated at all over
    part of the calendar is a different matter and must be excluded by the caller, not zero-filled.
    """
    idx = pd.Index(sorted(calendar), name="session")
    out = pd.DataFrame(index=idx)
    for name, s in series.items():
        out[name] = s.reindex(idx).fillna(0.0).astype(float)
    return out


def summary_text(res: dict) -> str:
    p = res["pbo"]
    verdict = ("the selection procedure is picking noise" if p >= 0.5 else
               "elevated - treat the selected winner with caution" if p >= 0.25 else
               "no strong sign that selection is picking noise")
    L = [f"PBO = {p:.1%}  ({res['winner_oos_below_median_count']} of {res['n_combinations']} splits put the "
         f"in-sample winner below the out-of-sample median)",
         f"  reading: {verdict}",
         f"  strategies {res['n_strategies']}, rows {res['rows_used']} (dropped {res['rows_dropped']}), "
         f"S={res['s_blocks']} blocks of {res['block_size']}",
         f"  winner's mean Sharpe: in-sample {res['mean_is_sharpe_of_winner']:+.4f} -> "
         f"out-of-sample {res['mean_oos_sharpe_of_winner']:+.4f}",
         f"  P(winner's OOS Sharpe < 0) = {res['prob_winner_oos_sharpe_negative']:.1%}",
         "  selected in-sample most often: " +
         ", ".join(f"{k} {v}" for k, v in list(res["selected_in_sample_counts"].items())[:5])]
    return "\n".join(L)
