# Pre-registration: H8 negative control on Micro Gold futures (MGC)
Written 2026-11-10, before any gold data was downloaded. SHA-256 in `docs/PREREG_HASH.txt`.

## This test is designed to disconfirm H8, not to support it
H8 (pre-FOMC drift) has now "passed" in three markets: MNQ (t 3.02), MES (t 3.56) and M2K (t 2.45). All three
used the **same 59 FOMC statement dates**, and all three are US equity indexes. That leaves two explanations
that the existing evidence cannot tell apart:

- **A** - the published explanation (Lucca & Moench 2015): an **equity risk premium**, paid for holding equity
  exposure into an announcement. If so, the effect belongs to stocks.
- **B** - something specific to those 59 calendar days (a market-wide move, a sample artifact, or luck). If so,
  every equity index shows it for the same reason, and the three replications are one result counted
  three times.

Gold carries no equity risk premium. Under explanation **A**, the same rule applied to gold should show little
or nothing. Under **B**, gold should show the drift too. This test can therefore only leave H8 where it is or
weaken it. **No outcome of this test raises H8's status.** That asymmetry is the reason for running it.

Honest caveat stated in advance: gold is not perfectly inert to Fed decisions, because it responds to real
interest rates. It is a weaker control than a completely unrelated market (an agricultural future, say), and the
result is read with that in mind.

## Data
- Databento `GLBX.MDP3`, schema `ohlcv-1m`, symbol `MGC.v.0` (volume-rolled continuous),
  2019-05-06 -> 2026-10-31. Downloaded once, after this file is hashed and pushed.
- Events: the same 59 scheduled FOMC statement days as the MES and M2K tests
  (`FOMC_DAYS + HOLDOUT_FOMC_DAYS` in `nq_bot/family3.py`).

## Rule (identical to H8, nothing tuned for gold)
Buy 1 MGC at the open of the 14:00 ET bar on the trading day before the statement; sell at the close of the
13:55 ET bar on statement day; 3% disaster stop checked on every bar. Same fill model (1 tick against us on
market orders, stop -1 tick or the gap-through open). MGC contract specs: 10 troy ounces, $10 per $1/oz of
price, tick 0.10 ($1.00); $0.62 per side assumed, as in every other test. The only code change from the M2K
run is the point value and tick size.

## How the result will be read (decided now, before the data exists)
Applying the same four checks used for MES and M2K (net > 0 and PF >= 1.20; t >= 2.0; mean per event above the
95th percentile of 2,000 random same-length long holds; both halves positive):

| Outcome in gold | Reading | H8 status |
|---|---|---|
| Fails the checks (in particular t < 2.0) | Consistent with the equity-premium explanation. The control did its job and found nothing. | **Unchanged**: "replicated in two markets" |
| Passes all four checks | The drift is not equity-specific. The three equity replications are most likely one shared date effect. | **Downgraded** to "possible date artifact" |
| Positive but short of the bar (0 < t < 2.0) | Inconclusive. Reported as inconclusive, with the numbers. | **Unchanged**, with this caveat recorded |

Forward paper trading on the IB paper account continues either way; it costs nothing and remains the only test
on dates no backtest has seen. A downgrade would mean no further replication work is worth paying for.

Run once. No rule changes afterwards. Result published in `docs/RESULTS_H8_GOLD_CONTROL.md` whichever way it
goes, and reflected in the README and the results dashboard.
