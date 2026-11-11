# Result: S1, statistical arbitrage between MES and M2K — FAILS AT STAGE A, 2026-11-11

Pre-registration: `PREREG_STATARB_S1.md` (hash in `PREREG_HASH.txt`, frozen before the spread was examined in
any way). Data already on disk: MES and M2K 1-minute bars, bought earlier for the H8 replications. **No new
data was purchased and no trading rule was written.**

## The test

Spread `s(t) = ln(MES 15:59 close) − ln(M2K 15:59 close)` on 1,535 shared trading days, 2019-05-06 →
2025-06-30. Hedge ratio fixed at 1 in log space (equal notional), so Stage A has no fitted parameter.

| Check | Result | Threshold | |
|---|---|---|---|
| A1 Augmented Dickey-Fuller t (constant, no trend, 1 lag) | **−1.03** | < −2.86 | FAIL |
| A2 Variance ratio at 20 days | **0.903** | < 0.85 | FAIL |
| A3 Half-life from an AR(1) fit | **398 trading days** | ≤ 30 | FAIL |
| A4 Holdout agreement | **not examined** | — | not reached |

**Verdict: S1 FAILS AT STAGE A.** The log ratio cannot be distinguished from a random walk, so no trading rule
was written, and statistical arbitrage is closed as a research direction for this project.

## Why, in the data's own terms

The spread ranged from **0.517 to 1.059** in logs across the sample. That is an S&P 500 / Russell 2000 price
ratio moving from **1.68 to 2.88** — the ratio nearly doubled over six years. There is no fixed level for a
mean-reversion strategy to revert to; the series trends.

The half-life is the decisive number. Even taking the AR(1) point estimate at face value, a deviation needs
**398 trading days — about 1.6 years — to decay by half.** No threshold, window or entry rule makes that
tradeable, and the 11% residual leg imbalance alone would dominate the result over that horizon.

The variance ratio of 0.903 is mildly below the random-walk value of 1.0, so there is a whisper of mean
reversion in the series. It is nowhere near the pre-registered 0.85 and is swamped by the trend. Reading 0.903
as an edge would be exactly the error this protocol exists to prevent.

## This was the predicted outcome, and it was predicted in writing

The pre-registration recorded, before any statistic was computed:

> The size premium is itself time-varying and has trended for a decade — small caps underperformed large caps
> persistently from roughly 2014 to 2024. **A ratio that trends has no fixed mean to revert to, and a
> mean-reversion strategy on a trending ratio loses money systematically.** [...] The honest prior for S1 is
> **failure**, and the value of the test is that it closes the direction rather than that it finds an edge.

That is what happened. The test cost $0 and about an hour.

## Two things this result preserves

1. **The MES/M2K holdout (2025-07 → 2026-10) was never examined.** Because the training checks failed, there
   was no reason to look, and the script refuses to look until a training result is committed. That period
   remains clean out-of-sample data for a future pre-registered hypothesis.
2. **No trading rule exists to be tempted by.** Stage B was never written. There is no z-score backtest, no
   equity curve and no parameter set that could later be re-examined "just to see."

## What it does and does not establish

- **Does:** the MES/M2K log ratio is not mean-reverting over 2019-2025 at any horizon short enough to trade.
  A classic pairs-trading approach on these two instruments has no statistical basis in this sample.
- **Does not:** rule out relative-value trading in general, other pairs, other horizons, or a cointegrating
  relationship with a time-varying hedge ratio. Those are untested, and under
  `docs/RESEARCH_BUDGET.md` they would each cost a budget line and require their own pre-registration. None
  is currently planned, because the economic case for the best-justified pair has now been tested and failed.
- **Does not** claim the spread is a pure random walk — only that it is statistically indistinguishable from
  one here, which is the relevant fact for a strategy that needs reversion.

**Budget: 13 of 15 hypotheses spent. Two remain.**
