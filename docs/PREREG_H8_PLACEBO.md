# Pre-registration: H8 placebo tests (sham dates and day-of-week-matched null)

Frozen 2026-11-11, before any sham-date or Wednesday-null statistic was computed. Run once.

## Honest limitation, recorded up front

This is a **pre-specified analysis, not a blind pre-registration.** The MNQ, MES and M2K bars are already on
disk and the real H8 results are already known (MNQ training t 3.02 on 48 events, MNQ holdout t 0.34 on 11,
MES t 3.56, M2K t 2.45). I cannot un-see those. What is committed in advance here is the sham-date
construction, the pooling rule, the statistic, and the decision table below — all fixed before a single
placebo number is computed. That is weaker than freezing a hash before buying data, and the result should be
read with that discount.

## Why these tests exist

Every H8 "replication" so far re-measures the same 59 FOMC dates in markets that move together (MES ~0.95 with
NQ, M2K ~0.85). Correlated markets agreeing is close to arithmetic, not independent evidence. Neither test so
far asks the question that actually matters: **is the pre-FOMC window special, or would any 24-hour
mid-afternoon-to-mid-afternoon hold on a Tuesday-into-Wednesday have done the same?** These two tests ask it,
and they cost nothing because they run on data already paid for.

## Rule under test (unchanged, frozen)

Identical to `family3.run_h8`: enter long at the **prior trading day's** 14:00 ET bar open + 1 tick; exit at
the event day's 13:55 ET bar close - 1 tick; disaster stop at entry x 0.97. Per-market point value, tick and
commission as already used for each market. No parameter is re-fit for these tests.

## Test A - sham-date placebo

1. Sham offsets are fixed at **-21, -14, -7, +7, +14, +21 calendar days** from each of the 59 real FOMC dates.
   Six sham series, each with up to 59 pseudo-events. No other offset will be computed or reported.
2. A sham date is dropped if it falls within **3 trading days** of any real FOMC date (either side), so that
   no sham window overlaps a real event window or the post-statement drift.
3. A sham date is dropped if it is not a trading day in that market, or is the first trading day in the file.
4. Each sham series is run through the identical rule and reported with n, net, mean, t.
5. Primary market: **MNQ, all 59 events** (`mnq_train.csv` + `mnq_holdout.csv` concatenated). MES and M2K are
   run as secondaries and reported, but the verdict is read off MNQ.

**Primary statistic:** the rank of the real FOMC t-statistic among the seven values {real, six shams}.

| Outcome | Reading |
|---|---|
| Real t is the highest of the seven **and** no sham reaches t >= 2.0 | **PLACEBO CLEAN** - the pre-FOMC window is special. Strongest free evidence for H8 so far; status unchanged but better supported. |
| Real t is the highest, but at least one sham reaches t >= 2.0 | **PARTIAL** - some of the drift is generic calendar drift. H8 survives but its effect size must be discounted by roughly the best sham mean, and that discount gets written into the results doc. |
| Real t is **not** the highest of the seven | **PLACEBO FAILS** - the window is not special. H8 is downgraded from "replicated candidate" to "calendar artifact, not a Fed effect," and the forward paper test continues only as a curiosity, not as a candidate strategy. |

## Test B - day-of-week-matched null

The existing benchmark pools *all* consecutive trading-day pairs and compares **means** via 2,000 bootstrap
draws. Two weaknesses: FOMC statements are almost always Wednesday, so the pool is contaminated by other
weekdays; and comparing means ignores that t rewards consistency, which is what the four checks lean on.

1. Pool = consecutive trading-day pairs where the **exit day is a Wednesday** and neither day is within 3
   trading days of a real FOMC date.
2. Draw **10,000** bootstrap samples of size n_real (with replacement) from that pool, computing the
   **t-statistic** of each sample, not just its mean. Seed fixed at 7.
3. Report the empirical p-value: the fraction of samples with t >= the real t.

| Outcome | Reading |
|---|---|
| p < 0.05 | H8's t-statistic is not reproducible by a random Wednesday-matched 24-hour long hold. |
| p >= 0.05 | It is. The four pre-registered checks H8 already passed were too easy, and that gets recorded plainly. |

## Committed in advance

- Both tests run exactly once, on all three markets, and the full output is written to
  `docs/RESULTS_H8_PLACEBO.md` **whatever it says**. A placebo failure is the single most useful result this
  project could produce right now, because it would stop ~8 events a year of pointless paper trading.
- No sham offset, pool definition, market or statistic will be added, dropped or re-weighted after seeing any
  number. If something in the above turns out to be impossible to compute, that fact gets written down and the
  test is declared INVALID rather than quietly re-specified.
- Per-trade prices stay out of the repo (licensed Databento data); only aggregates are published.
