# Result: H8 replication on Nikkei 225 (NKD) - INVALID ON DATA COVERAGE, 2026-11-11

Pre-registration: `PREREG_H8_NKD_REPLICATION.md` (hash in `PREREG_HASH.txt`, frozen before any Nikkei data was
downloaded). Data: Databento `NKD.v.0` 1-minute, 2019-05-05 -> 2026-10-30, 1,712,724 bars, cost $6.25.

**Verdict: INVALID ON DATA COVERAGE. No result is reported, and none will be.** Only **16 of 59** events
produced a trade, against a pre-registered floor of 50. Per the pre-registration, no net, mean, profit factor
or t-statistic was computed, and none appears anywhere in this repository.

## Why

NKD does not trade densely enough during the US session for a rule that depends on two specific New York
minutes. Median RTH coverage is **279 of 390 possible minutes** (10th percentile 197); MES is 390 of 390. The
file validator independently flagged **323 gaps over 15 minutes inside regular hours**.

Loosening the session filter does not rescue it:

| Session filter | Trading days | Usable events (of 59) |
|---|---|---|
| >= 300 RTH bars (the filter in use) | 705 | **16** |
| >= 200 RTH bars | 1,738 | 26 |
| >= 100 RTH bars | 1,879 | 25 |
| >= 50 RTH bars | 1,925 | 25 |
| >= 1 RTH bar (no density filter at all) | 1,935 | **25** |

MES, for comparison, yields 59 of 59 at every threshold. Once density stops binding, NKD's ceiling is 25
events, because the constraint becomes a 14:00 or 13:55 bar that does not exist at all (6 events are missing
the 13:55 bar outright even with no filter). **25 is below the floor of 50 under every possible filter**, so
there is no re-specification that produces a valid test. The instrument cannot answer the question.

This diagnostic measured bar availability only. No price, return or P&L was computed from the NKD file at any
point, so nothing in this document is informed by what the result would have been.

## My error, recorded plainly

I recommended this download and it was a waste of $6.25. Before spending, I verified the contract
specifications ($5/index point, 5.00-point tick) and the trading hours (CME lists NKD as nearly 23 hours), and
I wrote three caveats about friction, fill optimism and the Tokyo session overlap into the pre-registration.
**I did not check bar density at the two minutes the rule actually uses.** "The market is open" and "the
market trades every minute" are different claims, and only the second one matters here. That was checkable in
advance for free - Databento's `metadata.get_record_count` is not billed - and I did not check it.

`scripts/preflight_coverage.py` now exists so this cannot recur: it compares bars-per-day against a reference
market using free metadata calls, and `docs/RESEARCH_PROTOCOL.md` requires it before any paid download.
On this data it would have reported ~885 bars/day for NKD against ~1,434 for MES and refused.

## What this does and does not mean for H8

- **Nothing either way.** This is not a failed replication; it is a test that could not be run. H8 is neither
  supported nor weakened by it, and it is not counted among H8's tests.
- **Paid replication for H8 is now closed**, as the pre-registration committed in advance. MYM was already
  ruled out as ~0.95 correlated with ES and therefore uninformative, and NKD was the last market that made a
  real prediction either way. No further market will be bought for this hypothesis.
- H8 remains a **"replicated candidate"** on the evidence that does exist: MES t 3.56 and M2K t 2.45 (same 59
  dates, correlated markets), a clean placebo result in all three markets (`RESULTS_H8_PLACEBO.md`), an
  inconclusive gold control, and the one genuinely clean out-of-sample test still failing at **t 0.34 on 11
  events**. The decisive evidence is forward: ~8 events a year, next Dec 8-9, IB paper only.
