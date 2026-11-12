# Research protocol
The rules every new idea follows. They exist because the easiest person to fool is yourself, and an AI assistant
that proposes ideas makes it easier, not harder.

1. **Ideas are hypotheses.** An idea from a paper, a chart or an AI is a hypothesis until a pre-registered test
   says otherwise. It is never described as an edge before that.
2. **Pre-register first.** Write `docs/PREREG_<name>.md` with the exact rule, data, costs and pass/fail bar.
   Record its SHA-256 in `docs/PREREG_HASH.txt` and push, **before** any data for it is downloaded or any test
   is run. `scripts/verify_prereg.py` (in CI) fails if a pre-registration is edited afterwards.
3. **Run once.** The runner script refuses to run again once its result file exists. No parameter changes after
   seeing results. A changed rule is a new hypothesis with a new pre-registration, and the old result stays.
4. **Publish failures.** Every result gets a `docs/RESULTS_<name>.md`, pass or fail. Nothing is deleted.
   Sensitivity checks done after the verdict are labeled as such and cannot change it.
5. **Count the tests.** Each extra idea on the same data raises the odds of a lucky pass. The pass bar rose from
   t ≥ 2.5 to 3.0 to 3.5 across families. **Search on the 2019-2026 MNQ data is closed**; new ideas need new
   data or a replication market chosen in advance.
6. **Benchmark long-only ideas** against random long holds of the same length (2,000 draws, 95th percentile).
7. **Check the usual biases.**
   - Look-ahead: features use only past bars; tests truncate the future and assert nothing changes.
   - Survivorship: index futures do not have it the way stock lists do, but continuous series hide rolls.
     Trades are simulated on the series and checked for roll-day jumps (`scripts/validate_data.py`).
   - Costs: commission and one tick of slippage per side, re-run at two ticks.
   - Stability: by year, by half, with the best trades removed.
8. **Label every number** as backtest, held-out, replication or forward paper. Never mix them in one total.
9. **No real money on backtests alone.** Forward paper results on unseen events are the deciding evidence.

## Validate data before using it
```
py scripts\validate_data.py data\mnq_train.csv
py scripts\validate_data.py data\m2k_2019_2026.csv --tick 0.10
```

## Pre-flight any market before paying for it
`metadata.get_record_count` is free. Run this **before** every paid download, and record the result in the
pre-registration:
```
py scripts\preflight_coverage.py NKD.v.0 2019-05-06 2026-11-01
```
A market can be open nearly 23 hours and still have no trade in the specific minute a rule needs - "the
market is open" and "the market trades every minute" are different claims, and for an event-window rule only
the second one matters. NKD was bought for $6.25 and came back INVALID on data coverage: 16 of 59 events,
against a floor of 50, and no filter choice could have lifted it above 25
(`docs/RESULTS_H8_NKD_REPLICATION.md`). The pre-flight would have refused it for nothing.

Every pre-registration for a new market must therefore state, in advance:
- bars/day from the pre-flight, against a dense reference market;
- the minimum number of events that makes the test valid, and that **no verdict is reported below it**.
The second of those is what stopped a 16-event number from entering the record, so it stays mandatory.

## Pre-flight the POWER before spending an idea

The coverage pre-flight asks whether the data can support the rule. This one asks whether the **sample can
support the bar** - and it must run **before** a pre-registration is written, not after a null result:
```
py scripts\preflight_power.py --years 7.5 --bar 3.5 --trials 12
py scripts\preflight_power.py --observations 59 --bar 3.5
```
A t-statistic on an annualised Sharpe `S` observed over `T` years is approximately `S * sqrt(T)`, so
clearing a bar `B` requires `S >= B / sqrt(T)`. **This does not depend on the hypothesis.** For this
project's 7.5 years of MNQ data at `B = 3.5` it demands a net Sharpe of **1.28**, which is above every
documented effect for a single liquid index future traded directionally:

| Reference | Net Sharpe |
|---|---|
| Cross-asset time-series momentum (Moskowitz/Ooi/Pedersen 2012) | 0.80 |
| Equity carry, 13-country cross-section (Koijen et al. 2018) | 0.91 |
| Equity basis, single-market **timing** (Hazelkorn et al. 2020) | 0.38 |
| Volatility-managed market, **out of sample** (Cederburg et al. 2020) | 0.42 |
| Buy-and-hold NDX, 2010-2025 | 0.90 |

So a hypothesis tested on this sample at this bar can only pass by being stronger than anything in the
published record, or by luck. **That is the structural reason eleven of twelve failed at literally zero
cost**, and the reason a thirteenth on the same sample would be a coin flip dressed as a t-statistic.

This matters because of what a null result is worth. A null from a powered test is evidence the effect is
absent. A null from an underpowered test is evidence of nothing at all, and spending a budget line to buy
one is the most expensive way to learn nothing. The gate exits non-zero and refuses.

**The only honest lever is sample length, and it is free.** Lowering the bar is prohibited
(`RESEARCH_BUDGET.md` rule 3) and widening the ceiling is just the bar by another name. Longer daily
history costs nothing: 30 years brings the required Sharpe to 0.64, which is inside the documented range.
A hypothesis that needs 1-minute MNQ data is therefore limited to what 7.5 years can show, whereas a
daily-horizon hypothesis can be screened over decades first - and the paid data and the remaining budget
lines are then spent only on something that already survived.

The gate was itself audited by Monte Carlo the day it was written, and **four defects were found and
fixed** - it had reported the Sharpe for a 50% chance rather than a powered one, ignored serial
correlation, ignored overlapping observations, and evaluated Bailey's MinBTL at a flattering Sharpe.
The overlap defect was the serious one: a 30-year daily study with a monthly hold clears t >= 3.5 on
**pure noise about one time in five**. Always declare `--hold-days` and `--autocorr`, and compute the
final t on non-overlapping observations or with Newey-West. See `docs/POWER_GATE_AUDIT.md`, including
its section 6 on where the gate can still be wrong in both directions.

Hypotheses closed by this gate before costing anything:
`docs/FEASIBILITY_CALENDAR_SPREAD.md` (calendar-spread carry) and volatility management, which Moreira &
Muir (JF 2017) report as a 25% Sharpe improvement in sample but which Cederburg et al. (JFE 2020) show
degrades out of sample for the market factor specifically - 0.42 managed against 0.46 unmanaged, with 53 of
103 strategies higher and 50 lower, i.e. a coin flip.
