# Results: Strategy Family 4 (pre-registered 2026-11-09; hash in `docs/PREREG_HASH.txt`)

Data: Databento `MNQ.v.0` 1-minute, 2019-05-06 → 2025-06-30 (training only). 1 MNQ, $0.62/side, 1 tick per market
order. Each hypothesis run once with the frozen rules (`run_family4_prereg.py`); synthetic unit tests for the
mechanics passed before the real run. Bar: t ≥ 3.5 (12 ideas tested on this data in total).

| Hypothesis | Trades | Net | Mean / trade | PF | t | Verdict |
|---|---|---|---|---|---|---|
| H9 macro announcement days (CPI + jobs report, close→close) | 141 | +$1,247 | +$8.85 | 1.05 | 0.23 | **Fail** |
| H10 pre-holiday (close→close) | 59 | +$3,876 | +$65.69 | 1.84 | 1.70 | **Fail** |
| H11 opening-hour trend after a high-range day | 253 | +$1,983 | +$7.84 | 1.08 | 0.36 | **Fail** |

## Details
- **H9:** worse than simply being long — random 1-day long holds averaged +$18.73; announcement days +$8.85
  (95th-percentile bar $75.78). Large losses in 2020 (−$2,102) and 2022 (−$3,882). 4 release days skipped
  because the market had no regular session (e.g. Good Friday jobs reports).
- **H10:** the closest call. Positive in 5 of 6 full years, PF 1.84, +$3,970 from 2021 on — but t = 1.70 is far from
  3.5, and +$65.69 per trade does not beat the 95th percentile of random 1-day longs ($102.90; random mean +$15.03).
  With 59 trades, this is indistinguishable from the market's general upward drift plus noise.
  Pre-holiday days were taken from the data's own session calendar (59 days, listed in `runs/family4_results.json`).
- **H11:** 105 of 253 trades stopped out; negative in 3 of 6 full years. Conditioning on high-range days did not
  rescue opening-hour momentum (compare H1).

## Conclusion
None passed. Per the pre-registration, **the strategy search on this data is closed**: 12 ideas tested,
11 rejected, 1 marginal (H8, now in forward paper tracking via `py cli.py fomc-paper`). Further ideas would need
new data that has not been looked at.
