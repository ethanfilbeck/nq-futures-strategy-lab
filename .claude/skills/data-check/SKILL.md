---
name: data-check
description: Validate market data before trusting any result computed from it. Use when loading a new CSV, adding a market, seeing a surprising backtest result, or when a result depends on a continuous futures series.
---

# Check the data before believing the result

```
py scripts\validate_data.py data\mnq_train.csv
py scripts\validate_data.py data\m2k_2019_2026.csv --tick 0.10
```

`nq_bot/integrity.py` runs before every backtest and **raises** rather than warning: bar sanity, contract
identity, P&L reconciliation by total and by count, no-dates-lost, zero-is-not-missing.

## The failure that cost this project its best result

A Databento continuous symbol (`MNQ.v.0`) splices quarterly contracts **without back-adjustment**. Every roll
prints the calendar spread as a one-minute jump of +0.64% to +1.38%, growing with interest rates. Any hold
spanning a roll books that gap as profit it never received.

It was **16%** of H8's net on MNQ, **60%** on MES, **44%** on M2K. Because quarterly rolls and FOMC meetings
both fall in the third week of March, June, September and December, it was *systematic*.

`validate_data.py` reported MNQ clean throughout — **a roll jump is not malformed data.** Structural
correctness is not the same as fitness for purpose.

So for anything holding overnight or longer:

- Keep the `symbol` column on download (`nq_bot/data.py` does) and get exact roll dates from symbology
  (`scripts/roll_map.py`), not from the heuristic in `nq_bot/rolls.py`, which missed 11 of 25 rolls in the
  low-carry years 2019–21.
- Price the trade on the **contract actually held** where it matters. `research_report.py` reports roll
  exposure as a first-class field and prints `NOT CHECKED` loudly when no roll map is supplied.
- Treat any third-party continuous series whose roll method is undocumented as unusable for this
  (`docs/DATA_QUALITY_DAILY.md`).

## Never discard observations to make something work

The first PBO matrix silently dropped **$322.70** of P&L on exchange half-days. `pbo.daily_matrix` now raises
instead. Silently discarding observations is the failure the protocol exists to prevent.
