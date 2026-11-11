# Pre-registration: H8 replication on Nikkei 225 futures (NKD)

Frozen 2026-11-11, **before any Nikkei data was downloaded**. Run once.

## Why this market and not Micro Dow

Micro Dow (MYM) was the obvious next replication and is deliberately **not** being run. MYM is ~0.95
correlated with ES, shares all 59 dates, and would near-certainly pass while adding no information. NKD is the
one market left that makes a real prediction either way: Japanese equities, a different economy and investor
base, reacting to a US Federal Reserve statement.

## Contract and data (fixed before download)

- Symbol `NKD.v.0` (volume-rolled continuous), dataset `GLBX.MDP3`, schema `ohlcv-1m`, 2019-05-06 to 2026-11-01.
- **$5.00 per index point; minimum tick 5.00 index points = $25.00** (CME Nikkei 225 futures fact card).
- Commission assumed **$5.00 round turn** ($2.50/side) - deliberately on the high side.
- Events: all 59 (`FOMC_DAYS` + `HOLDOUT_FOMC_DAYS`). Rule unchanged from `family3.run_h8`; no re-fitting.

## Differences from the US tests, recorded in advance

These are stated now so they cannot be produced afterwards as excuses for a bad result:

1. **Friction is ~11x higher.** One tick each side plus commission is about **$55 per trade** on NKD, versus
   $2.24 on MNQ and $3.74 on MES. Expected gross on a 0.4% move at a Nikkei level near 40,000 is roughly
   $800, so friction is ~7% of the expected move - a real drag but not disqualifying.
2. **The 1-tick fill model is more optimistic here.** NKD trades a small fraction of MNQ's volume, so assuming
   a fill one tick from the bar open is a friendlier assumption than it is on MNQ.
3. **The hold spans the entire Tokyo cash session.** 14:00 ET is roughly 04:00 JST, so this trade is carried
   through all of Japan's 09:00-15:00 JST session, then Europe, then the US morning. That is a genuinely
   different exposure profile from the US tests, not a like-for-like repeat.

## Data-quality guard (pre-registered)

If fewer than **50 of the 59** events produce a trade (more than 9 skipped for missing 14:00 or 13:55 bars),
the test is declared **INVALID on data coverage** and no verdict is reported. `scripts/validate_data.py` runs
on the file before the test, and its output goes into the results doc either way.

## Pre-registered checks

1. net > 0 and profit factor >= 1.20
2. t >= 2.0
3. mean beats the 95th percentile of random 24-hour long holds in the same market
4. both halves positive (2019-2022 and 2023-2026)

## Outcome table (fixed before download)

| Outcome | Reading |
|---|---|
| All four clear | **REPLICATION PASSES** - the drift transmits to a different economy's equity market. The best paid evidence for H8 so far, and it supports a global risk-premium mechanism rather than a US microstructure quirk. |
| net > 0 and 0 < t < 2.0 | **DIRECTIONALLY CONSISTENT, NOT SIGNIFICANT** - exactly what an attenuated real effect abroad looks like, and also what noise looks like. H8 status unchanged; recorded as weak support, not a pass. |
| net <= 0 or t <= 0 | **NO DRIFT IN NIKKEI** - H8 looks US-specific. Not fatal, since the published effect (Lucca & Moench 2015) is a US finding, but it removes the global risk-premium explanation and weakens the mechanism story. Recorded as a failed replication, not omitted. |

## Committed in advance

- One download, one run, result published to `docs/RESULTS_H8_NKD_REPLICATION.md` whatever it says.
- This closes paid replication for H8 for good. If NKD does not settle it, no further market will, and the
  only remaining evidence is forward paper trades on events no test has seen (~8 per year).
- Databento spend for this test is capped at one download of the range above. Per-trade prices stay out of the
  repo; only aggregates are published.
