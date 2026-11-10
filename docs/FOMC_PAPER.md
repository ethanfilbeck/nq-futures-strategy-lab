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

## Hands-free mode (Windows Task Scheduler)
Install once, from the repo folder: `.\scripts\install_fomc_task.ps1`. The task runs
`py cli.py fomc-paper --if-due` every weekday at 12:40 PM Central and at logon. It exits at once unless today is a
Fed entry day or a paper trade is already open (then it resumes it), wakes the PC if needed, and the tracker keeps
the PC awake while a trade is open. Output: `logs\fomc_paper\task.log`.

What stays manual, on purpose:
- **Being logged into Windows** (the task doesn't store your Windows password).
- **TWS logged into Paper.** Turn on TWS's own auto-restart (*File → Global Configuration → Lock and Exit →
  Auto restart*) so it reconnects daily on its own; IBKR still requires a fresh login about once a week.
  Fully unattended logins need a third-party tool (IBC) that stores your IB password in a file. That is your call,
  and not set up here.
- Windows **wake timers** must be allowed (Power Options → Change advanced power settings → Sleep →
  Allow wake timers → Enable) for the task to wake a sleeping PC.

## Phone alerts (Discord)
With `ALERT_WEBHOOK_URL` set in `.env`, the tracker posts to a Discord channel when it: announces a Fed trade
that day, enters, exits, gets stopped out, re-places a missing stop, can't reach TWS, loses or regains the IB
connection (expect a pair around TWS's nightly restart during the overnight hold), skips a late entry, refuses
to trade, or crashes. Times are shown in Central time. Every message says PAPER.

Setup: in Discord, create a server (or use your own), then channel *Edit Channel → Integrations → Webhooks →
New Webhook → Copy Webhook URL*. Put `ALERT_WEBHOOK_URL=<that URL>` in `.env` (git-ignored; the prepublish check
also blocks Discord webhook URLs). Check it with `py cli.py alert-test`. Treat the URL like a password: anyone
with it can post to that channel. If it leaks, delete the webhook in Discord and make a new one.

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
