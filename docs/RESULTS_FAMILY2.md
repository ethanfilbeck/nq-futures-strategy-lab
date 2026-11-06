# Results: Strategy Family 2 (H3, H4, H5) on MNQ — ALL FAILED

Rules frozen in `PREREG_FAMILY2.md` before testing (SHA-256 and time in `PREREG_HASH.txt`). Same data as before
(Databento `MNQ.v.0` 1-minute, 2019-05-06 → 2025-06-30), $0.62/side, 1-tick slippage, 1 contract. No tuning.
Holdout (2025-07 → 2026-10) still not downloaded.

## Headline

| | H3 Overnight drift | H4 Liquidity sweep | H5 VWAP pullback |
|---|---|---|---|
| Trades | 1,576 | 288 | 1,399 |
| Win rate | 44.4% | 32.6% | 33.2% |
| Profit factor | 0.98 | 1.20 | 0.94 |
| Net (1 contract) | −$576 | +$1,204 | −$2,336 |
| Before commissions | +$1,379 | +$1,561 | −$602 |
| t-stat of mean trade | −0.33 | 0.71 | −0.95 |
| Net before 2021 | +$913 | −$153 | +$639 |
| Net since 2021 | −$1,489 | +$1,356 | −$2,976 |
| Net at 2-tick slippage | −$2,009 | +$962 | −$3,504 |
| Positive years 2019–2024 | 1 of 6 | 2 of 6 | 1 of 6 |
| Monte Carlo: chance of ending negative | 64% | 26% | 83% |

## Pass criteria

| Check | H3 | H4 | H5 |
|---|---|---|---|
| Profit factor ≥ 1.20 | ✗ | ✓ (1.20, barely) | ✗ |
| t-stat ≥ 3.0 | ✗ | ✗ (0.71) | ✗ |
| ≥ 4 of 6 years positive and positive since 2021 | ✗ | ✗ (2 of 6) | ✗ |
| Positive at 2-tick slippage | ✗ | ✓ | ✗ |
| ≥ 200 trades | ✓ | ✓ | ✓ |
| **Result** | **FAIL** | **FAIL** | **FAIL** |

## Notes per hypothesis

**H3 — overnight drift (methodology check passed, strategy failed).** The average 2:00→3:00 a.m. ET move was
+2.27 points before 2021 and +0.16 points since — the same "positive, then disappeared after 2020" pattern the
original authors reported in July 2026. The pipeline reproduced a known published effect, which is evidence it
measures real effects correctly. As a trade it fails: +$1,379 before costs over six years, wiped out by
~$2.24 round-trip costs, and most of the profit came from 2020.

**H4 — liquidity sweep (the closest call, still a clear fail).** Profit factor exactly 1.20, but the t-statistic is
0.71 — far below 3.0 — and only 2 of 6 full years were positive. **One half-year (2025, 23 trades) made +$1,407,
more than the strategy's entire net.** Without 2025 it lost about $200. That is the signature of luck, not an
edge. The popular "sweep and reclaim" idea did not show a reliable effect on MNQ.

**H5 — VWAP pullback.** Lost money before costs. 2020 was the only good year; every year since lost.

| Year (net $) | 2019* | 2020 | 2021 | 2022 | 2023 | 2024 | 2025* |
|---|---|---|---|---|---|---|---|
| H3 | −279 | +1,192 | −108 | −190 | −1,121 | −661 | +593 |
| H4 | −86 | −66 | +107 | −226 | +174 | −105 | +1,407 |
| H5 | −39 | +678 | −524 | −487 | −774 | −278 | −913 |

\*partial years.

## Running tally on this data

Six strategies tested (ORB, H1, H2, H3, H4, H5), six rejected. Per the pre-registration: holdout untouched, no
rule variations tested. Testing more ideas on these same six years would mostly measure luck.
