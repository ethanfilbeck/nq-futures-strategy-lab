# Independent audit of the PBO implementation

Run 2026-11-11, after `PBO_ANALYSIS.md`. The brief was explicitly *not* to re-run the existing scripts and
report that they pass. CSCV was **re-implemented from scratch** in a throwaway script that shares no
computation with `nq_bot/pbo.py` — it literally slices the data for each of the 12,870 splits — and the
matrix was checked against the original per-trade files rather than against itself.

**The audit found and fixed a real defect.** The headline numbers in `PBO_ANALYSIS.md` were computed on a
matrix that silently discarded $322.70 of P&L. Corrected figures are below and `PBO_ANALYSIS.md` is
superseded on those numbers.

Findings are labelled: **[VERIFIED]** independently reproduced by separate code or against source data ·
**[REPRODUCED]** re-ran and matched, but not independently derived · **[CONCERN]** methodological issue ·
**[UNRESOLVED]** open.

---

## F1. CSCV engine — [VERIFIED]

A naive implementation (explicit `np.vstack` of block slices per split, independent ranking and logit code)
was run against the fast block-aggregate version:

| Matrix | Naive | Production | λ vectors identical |
|---|---|---|---|
| as published | 10.5983% | 10.5983% | **yes**, to 1e-9 |
| roll-adjusted | 14.7708% | 14.7708% | **yes**, to 1e-9 |
| intraday subgroup | 60.7848% | 60.7848% | — |
| event subgroup | 25.9363% | 25.9363% | — |

The block-aggregate reformulation is exact, not an approximation. Partition construction, in-sample and
out-of-sample ranking, the tie rule, ω = rank/(N+1) and λ = ln(ω/(1−ω)) are all confirmed by independent
code. The three known-answer tests (noise → 50.1%, real edge → 0.0%, regime flip → 70.0%) were re-checked.

## F2. The return matrix silently dropped $322.70 — [CONCERN, now fixed]

Column sums were compared against the original per-trade files. **Four of six CSV-sourced columns did not
match:**

| Strategy | Source total | Matrix total | Lost | Sessions |
|---|---|---|---|---|
| ORB | −$6,720.98 | −$6,520.88 | **−$200.10** | 15 |
| H3 overnight drift | −$575.74 | −$463.80 | **−$111.94** | **56** |
| H4 liquidity sweep | +$1,203.88 | +$1,179.86 | +$24.02 | 2 |
| H5 VWAP pullback | −$2,336.26 | −$2,279.36 | −$56.90 | 9 |
| H1, H2 | — | — | exact match | 0 |

**Cause.** The matrix was built on the 1,535-session calendar (`family3.Session`'s ≥300-bar rule). Trades
settling on the 53 excluded **exchange half-days** were dropped by `reindex`. H1 and H2 were unaffected
because they need 15:29 and 15:59 bars, which half-days do not have. H3 was worst hit: 56 sessions, 19.4% of
its total P&L.

A second case appeared once the calendar was widened: H3 trades 02:00–03:00 ET and so can settle on a date
with **no regular session at all** ($22.22 over 3 dates).

**Fix.** `daily_matrix` now **raises** on any P&L dated outside the calendar rather than discarding it, with
an explicit `on_off_calendar="report"` opt-out that records exactly what was excluded. The matrix calendar is
now the **union** of regular sessions and every date any strategy actually traded — 1,591 sessions — which
drops nothing by construction. Regression test: `tests/test_pbo.py::test_daily_matrix_refuses_to_drop_off_calendar_pnl`.

This is precisely the failure the brief named — *"do not silently fill missing returns or remove unfavorable
observations"* — and the first version did it. Caught only because column sums were checked against source.

## F3. Corrected results — [VERIFIED]

Complete calendar, 1,591 sessions, nothing dropped. S = 16.

| | As published | Roll-adjusted |
|---|---|---|
| **All 12** | 8.2% | **11.3%** |
| **Intraday / high-frequency (8)** | **56.6%** | **56.6%** |
| Event / low-frequency (4) | 18.5% | 25.5% |
| Winner's Sharpe IS → OOS (all 12) | +0.0740 → +0.0505 | +0.0683 → +0.0381 |

Compared with `PBO_ANALYSIS.md`: all-12 moved 14.8% → **11.3%**, intraday 60.8% → **56.6%**, event 25.9% →
**25.5%**. **No conclusion changes.** The intraday subgroup remains well above 50%; the overall figure
remains low.

Intraday PBO is **identical** under both matrices, which is itself a consistency check: intraday strategies
have no roll exposure, so roll adjustment must not move them, and it does not.

## F4. Module-derived strategies — [VERIFIED]

H6–H11 were re-derived straight from `family3`/`family4` by a separate code path and matched the matrix to
the cent: H6 $2,891.88, H7 −$3,741.61, H8 $7,114.98, H9 $1,247.46, H10 $3,875.92, H11 $1,982.78. Trade counts
73 / 439 / 48 / 141 / 59 / 253 as published.

## F5. Roll handling is consistent — [VERIFIED]

The concern: CSV-sourced strategies are never roll-adjusted, since they come from stored trade files. Checked
by testing every stored trade's hold window against the detected roll minutes:

| | Trades | Median hold | Max hold | Holds spanning a roll |
|---|---|---|---|---|
| ORB | 1,602 | 0.17h | 6.00h | **0** |
| H1 | 1,277 | 0.50h | 0.50h | **0** |
| H2 | 1,277 | 0.50h | 0.50h | **0** |
| H3 | 1,576 | 1.00h | 1.00h | **1** |
| H4 | 288 | 0.05h | 2.15h | **0** |
| H5 | 1,399 | 0.12h | 5.92h | **0** |

Rolls occur at 19:00–20:00 ET; these strategies close intraday or hold 02:00–03:00, so they cannot straddle
one. **One** H3 trade of 1,576 does. The inconsistency is real but immaterial — and it is now measured rather
than assumed.

## F6. Is daily Sharpe a fair ranking across wildly different trade frequencies? — [VERIFIED, and the concern largely dissolves]

This was the strongest methodological objection: H8 is active 48 days, H3 1,576. For a strategy active on k
of T sessions, daily Sharpe ≈ (per-trade t-statistic)/√T when σ ≫ μ. Since T is identical for every column,
**ranking by daily Sharpe should be ranking by per-trade t-statistic.** Measured:

| Strategy | Trades | t per-trade | Daily Sharpe × √T |
|---|---|---|---|
| H8 pre-FOMC | 48 | 2.626 | 2.483 |
| H10 pre-holiday | 59 | 1.705 | 1.679 |
| H4 liquidity sweep | 288 | 0.712 | 0.700 |
| H6 turn of month | 73 | 0.421 | 0.423 |
| H11 opening hour | 253 | 0.355 | 0.356 |
| H9 macro days | 141 | 0.160 | 0.161 |
| H3 overnight drift | 1,576 | −0.329 | −0.267 |
| H7 gap reversal | 439 | −0.737 | −0.738 |
| H5 VWAP pullback | 1,399 | −0.946 | −0.919 |
| H2 rest-of-day | 1,277 | −0.974 | −0.974 |
| ORB | 1,602 | −2.254 | −2.157 |
| H1 first half-hour | 1,277 | −2.249 | −2.249 |

**Correlation 0.9997.** Daily Sharpe is a frequency-fair ranking statistic here, so comparing a 48-day
strategy against a 1,576-day one in one CSCV run is legitimate. The subgroup split remains worth reporting,
but not because the pooled comparison was invalid. (H3's gap — −0.329 vs −0.267 — is the largest, and is a
residue of F2.)

## F7. Correlation between strategies — [VERIFIED], with a [CONCERN] on interpretation

Mean absolute pairwise correlation of the 12 daily series: **0.036**; maximum **0.470**. Effective number of
independent return streams (participation ratio of the correlation eigenvalues): **11.33 of 12**.

CSCV never assumes independence — it is non-parametric and works on the joint matrix — so this does not
affect the PBO figures. It matters for the *multiple-testing* arithmetic in
`QUANTITATIVE_RESEARCH_LITERATURE_REVIEW.md`, and it **corrects a claim made there**. That document said the
12 trials "are not independent, so the effective N is below 12, which makes the true thresholds slightly
lower" — i.e. that correlation helped H8. Measured, effective N is 11.33, so the thresholds barely move and
**that mitigation is negligible.** The literature review's §4c thresholds stand essentially as written.

**[CONCERN]** The 11.33 figure measures correlation of *daily return streams*. The event strategies trade on
near-disjoint days, which forces low correlation regardless of whether they share an underlying driver. For
multiple-testing purposes the right notion is correlation of the *test statistics*, which this does not
measure. Treat 11.33 as an upper bound on independence, not a precise effective trial count.

## F8. Sensitivity is wider than first reported — [CONCERN]

`PBO_ANALYSIS.md` reported sensitivity across S only. The audit added the **direction of row trimming**,
since T is not divisible by S and the surplus rows had always been dropped from the *end* — the most recent
data.

Roll-adjusted, complete calendar:

| S | Splits | Trim tail | Trim head | Spread |
|---|---|---|---|---|
| 8 | 70 | 11.4% | 10.0% | 1.4 pp |
| 10 | 252 | 10.7% | 10.3% | 0.4 pp |
| 12 | 924 | **20.2%** | 15.2% | 5.0 pp |
| 14 | 3,432 | 14.7% | **6.5%** | **8.2 pp** |
| 16 | 12,870 | 11.3% | 13.4% | 2.1 pp |

Across both axes the overall PBO ranges **6.5% to 20.2%**. It is **not monotone in S**, and at S = 14 the
trim direction alone moves it 8.2 points. **The overall PBO should be reported as a range of roughly 7–20%,
never as a point estimate.** The intraday subgroup is far more stable, 51–61% across every variation tested.

## F9. Comparison with the published methodology — [REPRODUCED]

Matches Bailey et al. (2017) on: equal-size contiguous blocks; all C(S, S/2) balanced splits; Sharpe as the
performance measure; rank of the in-sample winner within the out-of-sample set; logit transform;
PBO = P(λ ≤ 0).

**[CONCERN] Not implemented:** the paper also presents performance-degradation regression (OOS on IS Sharpe),
probability of loss, and first/second-order stochastic dominance. This implementation reports the winner's
mean IS and OOS Sharpe and P(OOS Sharpe < 0), which covers degradation and loss only informally. Those are
additional diagnostics, not corrections, and their absence does not affect the PBO figures.

**[CONCERN] Procedure mismatch, restated.** CSCV models "pick the best of N." This project ran "test each
hypothesis against a fixed pre-registered bar." PBO answers the related question — *would selecting the
apparent winner have generalised?* — which is the right question about H8, but the mapping is not exact.

## F10. [UNRESOLVED]

1. **Roll adjustment rests on a heuristic detector.** Every roll-adjusted figure here inherits that, and the
   fix needs the contract-level re-run that is still pending (`AUDIT_2026_11_ROLLS.md`).
2. **Multi-day P&L attribution.** H6's roughly five-session holds are booked entirely to the exit day. No
   mark-to-market data exists to do better. Effect on H6's daily Sharpe is unquantified.
3. **Effective trial count for multiple testing** — see F7's concern. Not resolved by this audit.
4. **ORB column choice.** The full-sample ORB run is used, not the walk-forward OOS, because the latter
   starts 2020-05. The full-sample run is the *more favourable* ORB result, so the intraday subgroup's PBO is
   if anything understated. Not re-run both ways.

---

# Verdict: are the PBO findings trustworthy enough for the project's final conclusions?

**Split, and the split matters.**

**Trustworthy — use it.** *Selection among the eight intraday strategies was overfitting.* PBO 51–61% across
every variation tested — both matrices, five block counts, both trim directions, and both calendars — with
the selected winner's out-of-sample Sharpe **negative**. The engine is independently verified, the inputs are
reconciled to source, and the finding survived a defect that moved other numbers. This belongs in the final
conclusions, and it converts "eleven intraday hypotheses failed" from an observation into a measurement.

**Trustworthy only as a range.** *Overall PBO is low* — somewhere around **7–20%**, best estimate ~11%. The
direction is solid; the point estimate is not. Any final write-up should give the range.

**Not trustworthy as support for H8, and was never capable of being so.** PBO is computed entirely within
2019-05 → 2025-06 and structurally cannot see the holdout, which failed. A low PBO says the selection
procedure was not obviously picking noise. It says nothing about whether H8 still works, and H8's status is
unchanged: unconfirmed, below its original bar on roll-adjusted data, sitting on the 5% multiple-testing
line.

**One meta-finding worth keeping.** The first PBO run produced plausible numbers from a matrix that was
quietly losing money. Nothing in the result looked wrong — 14.8% is an unremarkable figure — and no test
failed. It was caught only by reconciling column sums against the original per-trade files. That is the
second time in two days that a defect in the *data path*, not the *method*, changed the numbers. The
methodology literature does not protect against this, and the project's standing lesson should be that every
derived dataset is reconciled to its source before anything is computed from it.
