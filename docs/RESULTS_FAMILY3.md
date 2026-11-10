# Results: Strategy Family 3 (pre-registered 2026-11-09; hash in `docs/PREREG_HASH.txt`)

Data: Databento `MNQ.v.0` 1-minute, 2019-05-06 → 2025-06-30 (training only). 1 MNQ, $0.62/side,
1 tick per market order. Each hypothesis was run once with the frozen rules (`run_family3_prereg.py`).
Two bugs were found by synthetic unit tests **before** the real run (slippage math double-counted; one test
expectation wrong) and fixed; no rule was changed.

| Hypothesis | Trades | Net | Mean / trade | PF | t | Verdict |
|---|---|---|---|---|---|---|
| H6 turn of the month (−1…+3) | 73 | +$2,892 | +$39.61 | 1.14 | 0.45 | **Fail** |
| H7 overnight-gap reversal | 439 | −$3,742 | −$8.52 | 0.92 | −0.74 | **Fail** |
| H8 pre-FOMC drift (14:00 day before → 13:55 announcement day) | 48 | +$7,115 | +$148.23 | 3.34 | 3.02 | **Passed all pre-registered checks (barely)** |

## H6 — turn of the month: fail
- Lost money from 2021 on (−$1,386); 2020 alone made +$4,222.
- Worse than simply being long: random 5-session long holds started on non-month-turn days averaged **+$91.62**
  per trade; the turn-of-month window averaged +$39.61 (95th-percentile bar: $266.58).
- The 1926–2005 effect does not show up in MNQ in 2019–2025.

## H7 — overnight-gap reversal: fail
- 35% win rate; 241 stops, 95 gap fills, 103 time exits. Negative in 5 of 6 full years (only 2024 positive).
- Fading large Nasdaq gaps at the open lost money after costs.

## H8 — pre-FOMC drift: passed, with heavy caveats
| Check (pre-registered) | Result | |
|---|---|---|
| PF ≥ 1.20 | 3.34 | ✅ |
| t ≥ 3.0 | 3.02 | ✅ (by 0.02) |
| ≥ 4 of 6 years 2019–2024 positive, and positive 2021+ | 4 of 6 (2019 −$91, 2021 −$303); 2021+ = +$6,149 | ✅ |
| Positive at 2-tick slippage | +$7,067 (t 3.00) | ✅ |
| Beats random long holds of the same length (95th pct) | +$148.23 vs 95th pct $99.06 (random mean $9.51) | ✅ |

Independent re-computation from the raw CSV with separate code reproduced every trade (n 48, net $7,114.98,
t 3.022). No disaster stop was hit.

**Why this is not yet evidence of a tradable edge** (sensitivity checks run after the verdict; they do not change it):
- **Fragile:** removing the single best trade (2024-07-31, +$991) drops t to 2.79; removing the best 3 drops it to 2.32.
- **Small sample:** 48 events, ~8 per year. Median trade +$68.51; the 6 worst lost $257–$525 each.
- **Multiple testing:** this is the 9th idea tested on the same data. t = 3.02 (≈ p 0.004) only just survives a
  Bonferroni bar for 9 tests (0.05 / 9 ≈ 0.0056).
- **The literature says it faded:** Kurov, Wolfe & Gilbert found the drift indistinguishable from ordinary days in
  2016–2019. Our 2019 events were also slightly negative; the gains are concentrated in 2022–2024, a period of
  unusually high rate uncertainty (consistent with research that the drift appears when uncertainty is high).
- **It is not what the bot does:** each trade holds ~24 hours, overnight, with a 3% disaster stop (≈ $1,100 on
  1 MNQ at 2025 prices) — outside the intraday bot's flat-by-15:55 design.

## Next step (pre-registered): one holdout run
Per `PREREG_FAMILY3.md`, a passing hypothesis is run **once** on the untouched holdout (2025-07-01 → 2026-10-31),
then paper only. The holdout protocol is fixed in `docs/PREREG_FAMILY3_HOLDOUT.md` before downloading the data.

## Holdout result (run once, 2026-11-09, per `PREREG_FAMILY3_HOLDOUT.md`)
Data 2025-07-01 → 2026-11-01 (Databento flagged 2025-09-17, 2025-09-24 and 2025-11-28 as degraded-quality days;
2025-09-17 is an FOMC exit day). 11 events, none skipped, no disaster stop hit.

| | Holdout | Training |
|---|---|---|
| Trades | 11 | 48 |
| Net | +$367.86 | +$7,114.98 |
| Mean / trade | +$33.44 | +$148.23 |
| Wins | 7 of 11 | 32 of 48 |
| t | 0.34 | 3.02 |

**Verdict: HOLDOUT CONSISTENT** under the frozen rule (net > 0 and mean > the $9.51 random-long benchmark).
This is weak support only: the mean per trade fell ~78% from training, and 11 trades with t = 0.34 cannot
distinguish an edge from luck. Status: **unproven candidate**. Next, per the protocol: paper-track future FOMC
events only (about 8 per year), reported separately from backtests. No real money.
