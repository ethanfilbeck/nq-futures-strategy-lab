# Result: H8 (pre-FOMC drift) replication on Russell 2000 micro futures (M2K) — run once, 2026-11-10

> **SUPERSEDED IN PART, 2026-11-11.** A contract-roll defect inflated this result; see
> `AUDIT_2026_11_ROLLS.md`. Roll-adjusted figures: M2K t 2.45 -> **1.44**, which FAILS the pre-registered bar of 2.0.


Pre-registration: `PREREG_H8_M2K_REPLICATION.md` (hash in `PREREG_HASH.txt`, frozen and pushed to GitHub before any
Russell 2000 data was downloaded). Data: Databento `M2K.v.0` 1-minute, 2019-05-06 → 2026-10-31 (2,503,777 bars;
Databento flagged a few days as degraded quality, e.g. 2020-02-27/28, 2020-05-05). 59 scheduled FOMC statements,
none skipped. Two download attempts were refused by Databento's monthly spending limit before this one; no data
arrived and the test did not run on either, so this is the single pre-registered run.

| | M2K (this test) | MES replication | MNQ training (48) | MNQ holdout (11) |
|---|---|---|---|---|
| Net | **+$2,324.75** | +$5,140.59 | +$7,114.98 | +$367.86 |
| Mean / trade | +$39.40 | +$87.13 | +$148.23 | +$33.44 |
| Median / trade | +$37.26 | +$40.01 | — | — |
| Profit factor | 2.29 | 3.55 | 3.34 | 1.28 |
| t | **2.45** | 3.56 | 3.02 | 0.34 |
| Wins | 34 of 59 | 37 of 59 | 32 of 48 | 7 of 11 |
| Stops hit | 2 (2020-06-09, 2021-01-26) | 0 | 0 | 0 |

Dollar figures are per 1 contract of each market and are not comparable across markets (M2K and MES are $5 per
index point but on different indexes; MNQ is $2 per point).

| Pre-registered check | Result | |
|---|---|---|
| Net > 0 and PF ≥ 1.20 | +$2,324.75, PF 2.29 | ✅ |
| t ≥ 2.0 | 2.45 | ✅ |
| Beats random 24-h long holds (95th pct) | $39.40 vs $27.49 (random mean −$1.89) | ✅ |
| Both halves positive | 2019–2022 +$945.19; 2023–2026 +$1,379.56 | ✅ |

**Verdict: REPLICATION PASSES.**

Net by year: 2019 +$59, 2020 +$343, 2021 −$85, 2022 +$629, 2023 +$159, 2024 +$522, 2025 +$618, 2026 +$82
(2019 and 2026 partial).

## Sensitivity (computed after the verdict; does not change it)
- More fragile than MES: dropping the best 1 / 2 / 3 trades leaves t = 2.23 / 1.99 / 1.75.
- The 11 events after June 2025 made +$339.36 (t 0.87); the 48 training-period dates made +$1,985.39 (t 2.28).
- Random long holds of the same length lost money on average in the Russell 2000 (−$1.89), unlike in the
  S&P 500 and Nasdaq-100, so this test is a cleaner check that the gain comes from the Fed timing rather than from
  being long in a rising market.

## What this does and doesn't show
- **Does:** the same frozen rule made money, beat random long holds and was positive in both halves in a third
  index market, one that moves noticeably less in step with the Nasdaq-100 and whose own long-hold drift was
  negative over the period. H8 status: **"replicated in two markets"**, as decided in the pre-registration.
- **Doesn't:** the 59 dates are the same as in the MES test (48 of them from MNQ training), so all three markets
  share one set of Fed meetings; luck specific to those particular meetings would show up in all three. The
  effect is weaker in small caps (t 2.45 vs 3.56) and rests on a few good meetings. Published work found the
  drift faded in 2016–2019; it may fade again.
- **Status:** still paper only. The deciding evidence is forward: Fed meetings no test has seen
  (`py cli.py fomc-paper`, IB paper account, about 8 a year, first on 2026-12-08/09).
