# Pre-registration: S1, statistical arbitrage between MES and M2K

Written 2026-11-11, frozen before the spread between these two series was examined in any way. No price
ratio, correlation, stationarity statistic or chart of this pair has been computed or viewed. This is
hypothesis **13 of a budget of 15** (`docs/RESEARCH_BUDGET.md`).

## 1. The economic hypothesis

MES (S&P 500) and M2K (Russell 2000) are both claims on the earnings of the US corporate sector, differing
mainly in the size of the companies they hold. Their log price ratio is therefore the **size factor** — a
documented, slowly-varying risk premium (Fama & French 1993; Fama & French, "Size, Value, and Momentum in
International Stock Returns", *JFE* 2012). Because both legs are claims on the same economy, there is an
economic reason for the ratio to be tethered rather than to wander without limit, and a reason for deviations
beyond normal variation to revert.

**S1: the log ratio ln(MES) − ln(M2K) is mean-reverting at a multi-day horizon, and deviations beyond two
rolling standard deviations revert far enough to pay two-legged transaction costs.**

### Why this pair and not the others
Fixed in advance, and no other pair will be tested under this hypothesis:
- **MNQ/MES is rejected.** The Nasdaq-100's constituents are largely a subset of the S&P 500's, so the ratio
  is a sector bet on a few megacap technology names rather than two distinct claims. It is also the most
  persistently trending of the three equity ratios, which is the opposite of what this hypothesis needs.
- **MNQ/M2K is rejected** for the same constituent-overlap reason, in weaker form.
- **MGC (gold) is rejected.** Gold is not a claim on corporate earnings and tracks real interest rates; there
  is no economic reason for a stationary ratio against an equity index. Pairing it would be data mining.
- **NKD is rejected on data quality.** It has 279 of 390 US-session minutes traded and is already recorded as
  unusable for a rule needing specific New York minutes (`docs/RESULTS_H8_NKD_REPLICATION.md`).

### The reason to expect failure, recorded before testing
The size premium is itself time-varying and has trended for a decade — small caps underperformed large caps
persistently from roughly 2014 to 2024. **A ratio that trends has no fixed mean to revert to, and a
mean-reversion strategy on a trending ratio loses money systematically.** Using a rolling mean mitigates but
does not remove this. Separately, MES/M2K is among the most heavily automated relative-value trades in
existence, so any minute-level dislocation is arbitraged by faster participants. The honest prior for S1 is
**failure**, and the value of the test is that it closes the direction rather than that it finds an edge.

## 2. Two stages. Stage B runs only if Stage A passes

Splitting the test this way means no trading rule is fitted to a spread that does not mean-revert in the first
place, and Stage A has no parameters to tune.

### Stage A — the statistical precondition (no trading rule, no parameters)
Series: the close of the 15:59 ET one-minute bar for each market, one observation per shared trading day.
Spread: `s(t) = ln(MES close) − ln(M2K close)`. The hedge ratio is **1 in log space**, i.e. equal notional on
both legs — not fitted, so there is nothing to optimise.

| Test | Statistic | Pre-registered threshold |
|---|---|---|
| A1 | Augmented Dickey-Fuller on `s(t)`, constant and no trend, 1 lag | **t_ADF < −2.86** (reject a random walk at 5%) |
| A2 | Variance ratio of `s(t)` at a 20-day horizon | **VR(20) < 0.85** (sub-random-walk variance growth = mean reversion) |
| A3 | Half-life implied by an AR(1) fit on `s(t)` | **≤ 30 trading days** (longer is untradeable at this account size) |
| A4 | Out-of-sample agreement | A1 and A2 must hold **in the same direction** on the holdout period |

Dickey-Fuller critical values are the standard tabulated τ_μ values (1% −3.43, 5% −2.86, 10% −2.57), and both
tests are implemented inline with numpy so the whole computation is auditable and adds no dependency.

**Stage A fails if any of A1–A4 fails.** On failure, no trading rule is written or tested, statistical
arbitrage is closed as a research direction, and the result is published to `docs/RESULTS_STATARB_S1.md`.

### Stage B — the trading rule, only on a Stage A pass
One parameter set. No variations will be tested.

| Item | Rule |
|---|---|
| Rolling window | 60 trading days for the mean and standard deviation of `s(t)` |
| Entry | at the next day's 15:59 close when \|z\| ≥ 2.0; short the rich leg, long the cheap leg |
| Exit | at the 15:59 close when \|z\| ≤ 0.5, or after 30 trading days held, whichever comes first |
| Disaster stop | spread moves to \|z\| ≥ 4.0 at any daily close |
| Sizing | **1 MES : 3 M2K**, fixed. At 2026-11-10 closes (MES 7,614.5, M2K 2,821.8) that is $38,072 against $42,327 — an 11% residual imbalance, net long small-caps, which is reported and benchmarked against, not ignored |
| Positions | one spread at a time, no pyramiding |

## 3. Transaction costs and slippage

Both legs, every entry and exit, with no netting:

| Leg | Commission (round turn) | Slippage, 1 tick each side | Per round turn |
|---|---|---|---|
| 1 × MES | $1.24 | 0.25 × $5 × 2 = $2.50 | $3.74 |
| 3 × M2K | $3.72 | 3 × (0.10 × $5 × 2) = $3.00 | $6.72 |
| **Spread total** | | | **$10.46** |

That is 0.026% of the ~$40,000 per-side notional. **Friction is explicitly not expected to be the binding
constraint here**, unlike every intraday hypothesis in this project — a multi-day spread move of 2% dwarfs it.
If S1 fails it will be because the spread does not revert, not because costs ate the edge. The run is also
reported at **double slippage** (2 ticks per side per leg, $17.96 per round turn) and must stay positive there.

## 4. Statistical evaluation

- Primary statistic: the **t-statistic of mean P&L per spread trade**, net of the costs above.
- **Bar: t ≥ 3.5.** Twelve hypotheses have already been tested on this project's data; this is the thirteenth,
  so the bar stays at the Family 4 level (Harvey, Liu & Zhu, *RFS* 2016).
- Also required: profit factor ≥ 1.20; net positive at double slippage; **beat a benchmark** of holding the
  same 11% residual long-small-cap exposure passively over the same holding periods, so that a result cannot
  be the size premium itself in disguise; at least 20 completed trades, or the test is declared
  underpowered rather than passed or failed.

## 5. Out-of-sample requirements

- **Training:** 2019-05-06 → 2025-06-30 — the same split used for all 12 earlier hypotheses.
- **Holdout:** 2025-07-01 → 2026-10-31. Already on disk, since MES and M2K were bought as full ranges for the
  H8 replications, so it cannot be "not downloaded yet" as the MNQ holdout was. It is instead protected by
  this document: the holdout is **not examined at all** until Stage A's training result and, if reached,
  Stage B's training result are written down and committed.
- **No tuning after seeing the holdout.** If the holdout fails, S1 fails. There is no re-specification, no
  window adjustment and no threshold adjustment. Any change to sections 2–4 after any result is seen voids S1
  and spends a further hypothesis from the budget.

## 6. Failure conditions

| Outcome | Reading |
|---|---|
| Any of A1–A4 fails | **S1 FAILS at Stage A.** Statistical arbitrage is closed. No trading rule is written. |
| Stage A passes, Stage B training t < 3.5 | **S1 FAILS.** Published; no holdout examination. |
| Stage B training passes, holdout fails | **S1 FAILS.** The training result is recorded as not replicated. |
| Fewer than 20 completed trades | **UNDERPOWERED** — neither pass nor fail; recorded, and no further variant tested to chase a sample. |
| Everything passes | **S1 is a candidate**, exactly as H8 is: a candidate for forward paper testing under a separate forward pre-registration, never for real money on backtests alone. |

A pass does not authorise real money. The `PREREG_H8_FORWARD.md` standard — forward events on unseen data,
with prerequisites — applies to any survivor of this project, S1 included.

## 7. Commitments

- This file's SHA-256 goes into `docs/PREREG_HASH.txt` and is verified by `scripts/verify_prereg.py` in CI.
- `run_statarb_s1.py` implements exactly the above and refuses to re-run once its result file exists.
- The result is published to `docs/RESULTS_STATARB_S1.md` **whatever it says**, including a Stage A failure,
  which is the most likely outcome.
- Per-trade prices stay out of the repository (licensed Databento data); only aggregates are published.
- No real money, no live brokerage execution, no order placement. Research and paper only.
