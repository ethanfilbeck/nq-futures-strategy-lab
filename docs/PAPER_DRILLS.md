# Interactive Brokers Paper Drills

These drills test the **software** — connection handling, order protection, restarts, roll logic —
not whether any strategy makes money. Every drill uses an IB **paper** account (ID starts with `DU`)
and 1 MNQ. The code refuses non-paper ports and accounts.

## One-time setup

1. Log in to **TWS** (or IB Gateway) with your **paper** username.
2. TWS → *Edit → Global Configuration → API → Settings*:
   - tick **Enable ActiveX and Socket Clients**
   - **untick** Read-Only API
   - Socket port **7497** (Gateway paper: 4002 — then set `ibkr.port` in `config/settings.yaml`)
   - Trusted IPs: add `127.0.0.1`
3. Make sure your IB account has a **CME real-time market data** subscription (paper accounts use the live account's subscriptions). Without it, `drill bracket` stops with "No market price available".
4. Run drills when CME Globex is open (Sun 6 PM – Fri 5 PM ET, except the daily 5–6 PM ET break).

All commands run in **PowerShell 7** inside `Documents\nq_bot`. Leave TWS open so you can see the orders.

## The drills

| # | What it proves | Do this | Pass if |
|---|---|---|---|
| 1 | Paper lock | In `settings.yaml` set `port: 7496`, run `py cli.py drill status`, then set it back to `7497` | It refuses: "not a paper port" |
| 2 | Connects to the right contract | `py cli.py drill status` | Shows `MNQZ6`, position `+0`, no working orders |
| 3 | Bracket + server-side stop | `py cli.py drill bracket --side buy` | One BUY fill; status lists a SELL **STP** (~20 pts below) and a SELL **LMT** (~40 pts above); same in TWS |
| 4 | Duplicate-order prevention | `py cli.py drill duplicate` | `EVENT rejected: position or entry already working`; still exactly +1 |
| 5 | Crash protection | Close the PowerShell window entirely, then look in TWS | STP and LMT are **still working** at IB |
| 6 | Restart refuses an open position | Open PowerShell again, `py cli.py paper` | Refuses: "Existing NQ/MNQ positions … close them manually" |
| 7 | Restart adopts, doesn't stack | `py cli.py drill reconcile` | Status still shows exactly **one** STP (no second stop added) |
| 8 | Missing-stop repair | In TWS, cancel **only** the STP. Then `py cli.py drill reconcile --stop <the old stop price>` | `EVENT protection: replace_stop`; a new SELL STP for 1 appears |
| 9 | Clean exit | `py cli.py drill flatten` | Position `+0`, no working orders |
| 10 | Short side | Repeat 3 → 9 with `--side sell` | Mirror image (BUY STP above, BUY LMT below) |
| 11 | Contract roll | Set `roll_days_before_expiry: 45` in `settings.yaml`, run `py cli.py drill status`, then set it back to `8` | Shows `MNQH7` (next quarter). Repeat for real on **Dec 10, 2026** with the normal setting |
| 12 | Kill switch survives restart | Create `logs\risk_state.json` containing `{"killed_reason": "drill", "peak_equity": 0}`, run `py cli.py paper`, then `py cli.py reset-kill` (type RESET) | `paper` refuses with "Kill switch is set"; after reset it starts |
| 13 | Disconnect handling | Start `py cli.py paper` while flat, then close TWS | Bot logs "Disconnected from IB … Exiting" and stops |

`py cli.py paper` runs the (failed) ORB strategy on the paper account. That's fine for drills 6, 12 and 13 —
it's paper money and it's there only to exercise the runner. Stop it with **Ctrl+C** (it flattens on exit).

## Record results

Fill in this table and commit it — it's evidence for the portfolio.

| # | Date | Pass/Fail | Notes |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |
| 6 | | | |
| 7 | | | |
| 8 | | | |
| 9 | | | |
| 10 | | | |
| 11 | | | |
| 12 | | | |
| 13 | | | |

If anything fails, copy the PowerShell output into a chat — that's exactly what these drills are for.
Never paste API keys, account numbers or passwords.
