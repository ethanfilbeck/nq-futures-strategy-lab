# What you still have to configure by hand (Nov 9–13, 2026)

Nothing here can be done from Claude's side: each needs your account, your money, or your machine.

| # | Item | Why | How | Cost |
|---|---|---|---|---|
| 1 | **Databento live CME subscription** | The live feed for `paper-live`. Without it, use the TradingView chart (free) or `paper-replay`. | Databento portal → Live data → CME Globex (non-professional). | ~$33–37/month (check the portal) |
| 2 | **Live-connection smoke test** | Databento's live servers can't be reached from Claude's workspace, so the live code path is unverified until you run it. | Sunday after 6 PM ET or any weekday: `py cli.py paper-live --strategy none`. Expect "History: … bars" then a new bar each minute in `logs/paper/decisions_*.jsonl`. Ctrl+C to stop. | — |
| 3 | **Keep the PC awake during market hours** | The runner stops if Windows sleeps. | Settings → System → Power → Sleep: Never (while plugged in) for that week. | — |
| 4 | **Start it each morning (or leave running)** | Unattended run. | One PowerShell window in `Documents\nq_bot`: `py cli.py paper-live`. Start before 9:15 ET (8:15 CT). | — |
| 5 | **Optional phone alerts** | Entries, exits, halts, errors. | Create a Discord webhook URL and put `ALERT_WEBHOOK_URL=…` in `.env`. Never share it. | Free |
| 6 | **IB paper (later)** | Real broker plumbing, still simulated money. | After IB approves the account: follow `PAPER_DRILLS.md`. | Market data via IB |
| 7 | **Refresh `config/events.csv`** | Event blackouts. | Already filled through Dec 2027 from BLS/Fed; check before 2028. | — |

## What was verified without you

- 6 strategies backtested on 2019–2025 data; all failed; written up (`RESULTS_*.md`).
- Paper runner replays real sessions bar by bar and produces **identical** trades to the backtester
  (`scripts/readiness_check.py`).
- Stops on every order; exits only by stop / target / 15:55 flatten; nothing held overnight.
- Kill switch flattens, survives a restart, and blocks new entries.
- Stale feed (>120 s silent in market hours), duplicate / out-of-order / malformed bars, missing stop and oversize
  positions all trigger the right response (unit tests).
- A daily report is written for every session.

## What is NOT verified

- The Databento live connection itself (item 2).
- Interactive Brokers paper execution (account not yet approved).
- Any strategy's profitability: none has an edge on the evidence so far.
