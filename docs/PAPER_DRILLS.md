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
3. Make sure your IB account has a **CME real-time market data** subscription. Without one, add `--delayed` to
   `bracket` / `duplicate` (wide 150-pt buffers; `--ref <price>` if IB sends no price at all). Otherwise make sure it has a **CME real-time market data** subscription (paper accounts use the live account's subscriptions). Without it, `drill bracket` stops with "No market price available".
4. Run drills when CME Globex is open (Sun 6 PM – Fri 5 PM ET, except the daily 5–6 PM ET break).

All commands run in **PowerShell 7** inside `Documents\nq_bot`. Leave TWS open so you can see the orders.

## The drills

| # | What it proves | Do this | Pass if |
|---|---|---|---|
| 1 | Paper lock | `py cli.py --config config/drills/live_port.yaml drill status` (copy of settings with `port: 7496`) | It refuses: "not a paper port" |
| 2 | Connects to the right contract | `py cli.py drill status` | Shows `MNQZ6`, position `+0`, no working orders |
| 3 | Bracket + server-side stop | `py cli.py drill bracket --side buy` | One BUY fill; status lists a SELL **STP** (~20 pts below) and a SELL **LMT** (~40 pts above); same in TWS |
| 4 | Duplicate-order prevention | `py cli.py drill duplicate` | `EVENT rejected: position or entry already working`; still exactly +1 |
| 5 | Crash protection | Close the PowerShell window entirely, then look in TWS | STP and LMT are **still working** at IB |
| 6 | Restart refuses an open position | Open PowerShell again, `py cli.py paper` | Refuses: "Existing NQ/MNQ positions … close them manually" |
| 7 | Restart adopts, doesn't stack | `py cli.py drill reconcile` | Status still shows exactly **one** STP (no second stop added) |
| 8 | Missing-stop repair | In TWS, cancel **only** the STP. Then `py cli.py drill reconcile --stop <the old stop price>` | `EVENT protection: replace_stop`; a new SELL STP for 1 appears |
| 9 | Clean exit | `py cli.py drill flatten` | Position `+0`, no working orders |
| 10 | Short side | Repeat 3 → 9 with `--side sell` | Mirror image (BUY STP above, BUY LMT below) |
| 11 | Contract roll | `py cli.py --config config/drills/roll45.yaml drill status` (copy with `roll_days_before_expiry: 45`) | Shows `MNQH7` (next quarter). Repeat for real on **Dec 10, 2026** with the normal setting |
| 12 | Kill switch survives restart | Create `logs\risk_state.json` containing `{"killed_reason": "drill", "peak_equity": 0}`, run `py cli.py paper`, then `py cli.py reset-kill` (pick `logs/risk_state.json`, type RESET) | `paper` refuses with "Kill switch is set"; after reset it starts |
| 13 | Disconnect handling | Start `py cli.py paper` while flat, then close TWS | Bot logs "Disconnected from IB … Exiting" and stops |

`py cli.py paper` runs the (failed) ORB strategy on the paper account. That's fine for drills 6, 12 and 13 —
it's paper money and it's there only to exercise the runner. Stop it with **Ctrl+C** (it flattens on exit).

## Summary (2026-11-09)

All 13 drills pass on the IB paper account (TWS, no CME real-time subscription, so `--delayed`). Three real
defects were found and fixed along the way, each now covered by code or a test:
1. A new session cancelled a working stop it hadn't placed and flattened (drill 4) - reconciliation now adopts
   existing orders first (regression test added).
2. IB warning 10349 briefly marked market close-out orders "Cancelled" (drill 9) - TIF set explicitly.
3. Closing TWS crashed the runner with a traceback instead of the clean exit path (drill 13) - handled.
Paper P&L from the drills: -$41.66 including $0.61/side commissions (fake money; not a strategy result).

## Record results

Fill in this table and commit it — it's evidence for the portfolio.

| # | Date | Pass/Fail | Notes |
|---|---|---|---|
| 1 | 2026-11-09 | Pass | `RuntimeError: Port 7496 is not a paper port [4002, 7497]; refusing.` - before any connection |
| 2 | 2026-11-09 | Pass | Connected to TWS paper (API 7497); MNQZ6, roll 2026-12-10; position +0; no working orders |
| 3 | 2026-11-09 | Pass | `--delayed` (no CME real-time sub; ref from IB's last 1-min bar 27946.25). BUY 1 filled @ 27943.75, commission $0.61. SELL STP 27796.25 + SELL LMT 28246.25 working at IB. TWS asked to bypass API order precautions (accepted, paper login only) |
| 4 | 2026-11-09 | Fail → fixed | Duplicate entry correctly rejected, BUT the new session didn't know about the STP/LMT already working at IB, cancelled them and flattened at market (safe direction, wrong action). Fixed: reconciliation now adopts working orders before deciding a position is unprotected; regression test added. Re-run 12:28: **Pass** - duplicate rejected; no cancels/flatten; position +1 with STP 27773.5 + LMT 28223.5 still working (drill 3 re-run filled BUY @ 27923.75) |
| 5 | 2026-11-09 | Pass | PowerShell closed; TWS Orders panel 12:29 still shows ProfitTaker SELL LMT 28223.50 and StopLoss SELL STP 27773.50 working (server-side at IB) |
| 6 | 2026-11-09 | Pass | `py cli.py paper` refused: "Existing NQ/MNQ positions: ['MNQZ6 +1']. Close them manually before starting." Nothing sent |
| 7 | 2026-11-09 | Pass | `drill reconcile` adopted the working orders: position +1, exactly one STP 27773.5 + one LMT 28223.5, no new orders sent |
| 8 | 2026-11-09 | Pass | Cancelled the STP in TWS - IB also cancelled the LMT (same OCA group). `drill reconcile --stop 27773.5` placed a new SELL 1 STP @ 27773.5 (ref=protect). Target is not re-created (stop is mandatory, target is not). The `protection` event wasn't printed (drill showed only the 2nd poll's events) - fixed |
| 9 | 2026-11-09 | Pass | Cancelled STP, SELL 1 MKT filled @ 27911.25; position +0, no working orders. IB warning 10349 (TIF preset) briefly marked the market order Cancelled before it filled - fixed by setting TIF=DAY explicitly on flatten/reduce orders |
| 10 | 2026-11-09 | Pass | Short side: SELL 1 filled @ 27908.25; BUY STP 28055.5 above + BUY LMT 27605.5 below. Duplicate rejected, still -1 with both orders. Flatten: BUY 1 MKT, position +0, no working orders, no TIF warning (fix confirmed) |
| 11 | 2026-11-09 | Pass | roll45 config -> MNQH7 (expiry 2027-03-19, roll by 2027-02-02); normal config stays MNQZ6 until 2026-12-10. Real roll check due Dec 10 |
| 12 | 2026-11-09 | Pass | "Restored risk state ... killed=drill" then "Kill switch is set (drill)" - refused to start. (First attempt didn't create the file: logs\ folder missing.) Bonus: `py cli.py paper` with no real-time data halted itself after ~2 min: "Market data stale - flattened and halted for the day" |
| 13 | 2026-11-09 | Partial → fixed | Closed TWS 12 s after start: the bot stopped by itself (no zombie), but via an unhandled `ConnectionError: Socket disconnect` traceback instead of the clean "Disconnected from IB ... Exiting" path (ib_async raises from `sleep()` rather than letting `is_connected()` go False). Fixed: disconnects are now caught and logged cleanly; a second Ctrl+C during the exit flatten is also ignored. Re-run 21:21: **Pass** - "Disconnected from IB (ConnectionError). Server-side bracket orders remain. Exiting." No traceback |

If anything fails, copy the PowerShell output into a chat — that's exactly what these drills are for.
Never paste API keys, account numbers or passwords.
