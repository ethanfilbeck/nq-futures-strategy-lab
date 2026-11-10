# H8 forward paper tracking (`py cli.py fomc-paper`)

H8 (pre-FOMC drift) passed its pre-registered training test barely and its one holdout run weakly
(`RESULTS_FAMILY3.md`). The only honest next step is forward evidence: trade every future scheduled FOMC
statement on the **IB paper account** with the frozen rules, and report those trades separately.

**Rules (unchanged from `PREREG_FAMILY3.md`):** buy 1 MNQ at 14:00 ET on the trading day before the statement;
3% protective stop; sell at 13:55 ET on statement day. Dates come from the FOMC rows in `config/events.csv`.

## How to run
1. TWS logged into **Paper** (API on, port 7497, as in `PAPER_DRILLS.md`). Keep the PC awake.
2. Any time before 14:00 ET (1:00 PM Central) on the day before the statement:
   `py cli.py fomc-paper` — it waits, buys at 14:00 ET, holds overnight, sells at 13:55 ET next day, then exits.
3. One-time plumbing check (any time the market is open): `py cli.py fomc-paper --test-now`
   (buy 1, place the GTC stop, sell ~20 s later; logged to `test_trades.jsonl`, never counted as a result).

## Safety
- Paper only: the IB adapter refuses live ports and non-`DU` accounts; this command has no live option.
- The stop is **GTC and held at IB**, so it survives the overnight break, TWS's nightly restart, a crash or a
  sleeping PC. The tracker reconnects for up to an hour; restarting it resumes the open trade from
  `logs/fomc_paper/state.json` and re-places the stop if it's missing.
- It never enters late (only 14:00–14:05 ET), never touches an MNQ position it didn't open, and exits late with
  a "late" label if it wasn't running at 13:55.

## Results
`logs/fomc_paper/forward_trades.jsonl` — each line labeled **FORWARD PAPER (IB paper account) - not a backtest**.
About 8 events a year, so it takes years to accumulate meaningful evidence. No real money on this basis.
