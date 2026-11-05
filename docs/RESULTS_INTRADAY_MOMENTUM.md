# Results: Pre-registered Intraday Momentum (H1, H2) on MNQ — BOTH FAILED

Rules were frozen in `PREREG_INTRADAY_MOMENTUM.md` before testing (SHA-256 and time in `PREREG_HASH.txt`).
Same data and costs as the ORB study. No parameters were tuned; each hypothesis is a single test.

## Headline (1 MNQ contract, 1-tick slippage)

| | H1 first half-hour (Gao et al. 2018) | H2 rest of day (Baltussen et al. 2021) |
|---|---|---|
| Trades | 1,277 | 1,277 |
| Win rate | 42.8% | 44.8% |
| Profit factor | 0.84 | 0.93 |
| Net P&L | **−$6,059** | **−$2,611** |
| Before commissions | −$4,476 | −$1,028 |
| t-stat of mean trade | −2.25 | −0.97 |
| Post-publication (Jun 2020 →) net | −$8,269 | −$4,211 |
| Net at 2-tick slippage | −$7,336 | −$3,888 |
| Monte Carlo: chance of ending negative | 98.7% | 84.4% |
| Stops hit | 436 | 413 |

## Pass criteria (from the pre-registration)

| Check | H1 | H2 |
|---|---|---|
| Profit factor ≥ 1.20 | ✗ 0.84 | ✗ 0.93 |
| t-stat ≥ 2.5 | ✗ −2.25 | ✗ −0.97 |
| Positive in ≥ 4 of 6 years (2019–2024) | ✗ 1 of 6 | ✗ 3 of 6 |
| Positive after publication | ✗ | ✗ |
| Positive at 2-tick slippage | ✗ | ✗ |
| **Result** | **FAIL** | **FAIL** |

## By year (net $, 1 contract)

| Year | 2019* | 2020 | 2021 | 2022 | 2023 | 2024 | 2025* |
|---|---|---|---|---|---|---|---|
| H1 | −239 | +2,343 | −2,363 | −2,810 | −1,211 | −577 | −1,204 |
| H2 | +159 | +1,399 | −361 | +767 | −1,015 | −1,318 | −2,242 |

## What the data says, before costs

- Correlation of the last half-hour return with the predictor: H1 0.075, H2 0.066 (OLS slopes positive), but the
  direction was right only ~49–51% of days. The positive correlation comes mostly from a few huge-move days, mainly 2020.
- **Diagnostic, not a new test:** the papers' original rule had no stop. Without the stop, H1 still loses before costs
  (−$4,943); H2 makes +$512 before costs over six years but −$2,924 after costs. Gross by year for H2 was positive
  2019–2022 and negative 2023–2025. So the stop didn't cause the failure; the effect is small on MNQ, has weakened
  since 2023, and is smaller than the round-trip cost (~$2.24 per contract).
- High-volatility days were *worse*, not better, for both — the opposite of Gao et al.'s finding for SPY.

## Account test ($10,000 default risk rules, reported only)

Both runs hit the 10% drawdown kill switch (H1 in Sept 2021, H2 in Aug 2022) and stopped — the risk system worked as designed.

## Verdict

Neither hypothesis passes. As pre-registered: the holdout stays untouched and no rule variations are tested on this data.
These results are consistent with Baltussen et al.'s own caution that the effect may not survive trading costs for most investors.

**Sources:** Gao, Han, Li & Zhou (2018), *Journal of Financial Economics* 129(2):394–414.
Baltussen, Da, Lammers & Martens (2021), *Journal of Financial Economics* 142(1):377–403.
