# Result: H8 (pre-FOMC drift) replication on MES — run once, 2026-11-10

> **SUPERSEDED IN PART, 2026-11-11.** A contract-roll defect inflated this result; see
> `AUDIT_2026_11_ROLLS.md`. Roll-adjusted figures: MES t 3.56 -> **1.66**, which FAILS the pre-registered bar of 2.0.


Pre-registration: `PREREG_H8_ES_REPLICATION.md` (hash in `PREREG_HASH.txt`, frozen before any ES data was
downloaded). Data: Databento `MES.v.0` 1-minute, 2019-05-06 → 2026-10-31 (2,640,477 bars; Databento flagged a
few days as degraded quality, e.g. 2020-02-27/28). 59 scheduled FOMC statements, none skipped, no stop hit.

| | MES (this test) | MNQ training (48) | MNQ holdout (11) |
|---|---|---|---|
| Net | **+$5,140.59** | +$7,114.98 | +$367.86 |
| Mean / trade | +$87.13 | +$148.23 | +$33.44 |
| Profit factor | 3.55 | 3.34 | — |
| t | **3.56** | 3.02 | 0.34 |
| Wins | 37 of 59 | 32 of 48 | 7 of 11 |

| Pre-registered check | Result | |
|---|---|---|
| Net > 0 and PF ≥ 1.20 | +$5,140.59, PF 3.55 | ✅ |
| t ≥ 2.0 | 3.56 | ✅ |
| Beats random 24-h long holds (95th pct) | $87.13 vs $55.27 (random mean $5.87) | ✅ |
| Both halves positive | 2019–2022 +$1,784.03; 2023–2026 +$3,356.56 | ✅ |

**Verdict: REPLICATION PASSES** — supporting evidence, not independent proof.

## Sensitivity (computed after the verdict; does not change it)
- Less fragile than on MNQ: dropping the best 1 / 2 / 3 trades leaves t = 3.36 / 3.16 / 2.95. Median trade +$40.01.
- The 11 events after June 2025 made +$563.86 on MES (t 0.88): positive, but on their own still not significant.

## What this does and doesn't show
- **Does:** the same frozen rule works in the S&P 500, the market where the effect was originally published
  (Lucca & Moench 2015), and it beats simply being long by a wide margin.
- **Doesn't:** 48 of the 59 events are the same dates already used on MNQ, and ES/NQ move together (~0.9
  correlation), so this is largely the same evidence seen through a second, closely related market.
  Published work found the drift had faded in 2016–2019; it appears to have returned in 2020–2026, a period of
  unusually high rate uncertainty. If that uncertainty fades, the effect may fade with it.
- **Status:** H8 is upgraded from "marginal" to **"replicated candidate."** The decisive evidence is still forward:
  new FOMC events that no test has seen (`py cli.py fomc-paper`, IB paper account). Paper only; about 8 events
  a year.
