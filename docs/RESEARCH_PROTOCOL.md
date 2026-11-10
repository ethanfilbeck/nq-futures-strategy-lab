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
