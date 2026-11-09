# Automated Paper-Trading System (Sniper Den-style architecture, simulated orders only)

## How Sniper Den-type services work (general pattern, not their private code)

```
TradingView chart + script ──alert──► webhook (paid TradingView plan) ──► order-routing service
      (signals)                                                          (TradersPost, PickMyTrade, …)
                                                                                   │
                                                                                   ▼
                                                                 Tradovate / prop-firm accounts
```
The plumbing is commodity. What matters is whether the signal has an edge, which none of ours has so far.

## What this project runs instead (all components owned, all orders simulated)

```
Databento live 1-min bars ──► PaperRunner ──► features ─► regime ─► strategy ─► risk engine ─► SimBroker
 (or replayed history)          │                                                             (bracket: stop
                                │                                                              + target, next-bar
                                ├─ journal: every decision, skip, fill, flatten (JSONL)        fills, slippage,
                                ├─ risk_state.json saved every bar (restart-safe)              IBKR fees)
                                ├─ daily report (Markdown + JSON) per session
                                └─ watchdogs: stale feed, bad bars, missing stop, oversize position, KILL file
```

| Component | Sniper Den-style | This project | Status |
|---|---|---|---|
| Market monitoring | TradingView chart | Databento live CME 1-min bars → `PaperRunner`; TradingView script as a free visual mirror | Built; live feed needs your Databento live subscription |
| Signal generation | Pine script alerts | Same engine as the backtests (no separate logic to drift) | Built, tested |
| Transport | Webhook | Either in-process (Python strategy), **or** TradingView webhook → authenticated receiver (`--strategy tradingview --webhook`) | Both built, tested |
| Order routing / execution | Router → Tradovate | `SimBroker` (simulated); `IBKRBroker` for IB **paper** later | Built; IB paper waits on account approval |
| Stops & targets | Router / broker brackets | Bracket on every entry; stop reconciled every bar; missing stop = emergency flatten | Built, tested |
| Position sizing | Fixed contracts | Equity-, stop- and margin-based, capped; invalid quantities refused | Built, tested |
| Logging & reporting | Members dashboard | JSONL journal + daily report per session | Built, tested |
| Emergency stop | Toggle in dashboard | `py cli.py kill` (or Ctrl+C) → flatten + halt, persists across restarts | Built, tested |

Why not Tradovate: its API needs a funded live account (≥ $1,000) plus an API add-on (~$25/month).

## Sniper Den-style mode: TradingView webhooks → paper runner

```
TradingView (Holdout ORB script) ─alert JSON─► https://<tunnel>/tv ─► cloudflared ─► 127.0.0.1:8787 receiver
                                                                                         │ checks
                                                                                         ▼
                              risk engine (limits, sizing, blackouts) ─► SimBroker bracket ─► journal + report
```
TradingView only *asks* for a trade. The bot still decides size, applies every risk limit, and fills against
real Databento bars. The sender's quantity is ignored.

**Receiver security** (`nq_bot/webhook.py`, 19 tests): localhost-only listener; ≥24-char shared secret compared in
constant time and never logged; TradingView's four documented sender IPs as an allowlist (through the tunnel's
`CF-Connecting-IP`); 4 KB body limit; strict JSON schema (MNQ/NQ only, finite prices, stop/target on the right
sides); alert time must be within 2 minutes of the latest market bar (blocks replayed old alerts); duplicate
suppression; 10 requests/minute rate limit; instant reply (TradingView gives up after 3 s); every accept/reject
written to the journal.

**Setup (needs TradingView Essential or higher — $14.95/month — with 2-factor login enabled):**
1. Make a secret: `py -c "import secrets; print(secrets.token_urlsafe(32))"` → put `WEBHOOK_SECRET=…` in `.env`.
2. Re-paste `tradingview/holdout_orb.pine` into the Pine Editor (it now sends `passphrase` and `time`), add it to
   the 1-minute MNQ1! chart, and paste the same secret into its **Webhook passphrase** setting.
3. Start the runner: `py cli.py paper-live --strategy tradingview --webhook`.
4. In a second window, open a tunnel: `winget install -e --id Cloudflare.cloudflared` once, then
   `cloudflared tunnel --url http://127.0.0.1:8787`. Copy the `https://….trycloudflare.com` address it prints.
5. TradingView → Alert → Condition: *Holdout ORB* → *Any alert() function call* → Notifications → Webhook URL:
   `https://….trycloudflare.com/tv`. Note: quick-tunnel URLs change every time `cloudflared` restarts, so update
   the alert's URL when that happens. (TradingView's Nov 2026 plan page lists "Alerts that don't expire" on Essential.)
7. Make sure the chart's MNQ data is **real-time**, not delayed (no "D" badge next to the symbol). Delayed CME data
   is ~10 minutes old, and the receiver rejects alerts more than 2 minutes behind the live bars.
8. Check `logs/paper/decisions_*.jsonl` for `"event": "webhook"` lines (accepted / rejected with a reason).

The TradingView alert log shows the alert text, including the passphrase. Don't share screenshots of it, and
change the secret if you do.

## Commands

```
py cli.py paper-replay --csv data/mnq_train.csv --days 5     # rehearse on real past sessions (no subscription)
py scripts/readiness_check.py data/mnq_train.csv --days 5    # pass/fail pre-week checks
py cli.py paper-live                                         # live data, simulated orders (needs Databento live)
py cli.py paper-live --strategy none                         # monitor + report only, never enters
py cli.py paper-live --strategy tradingview --webhook        # TradingView alerts in, simulated orders out
py cli.py kill                                               # emergency stop from a second PowerShell window
py cli.py reset-kill                                         # clear a kill after you've reviewed why
```
Outputs land in `logs/paper/`: `decisions_*.jsonl`, `risk_state.json`, `report_YYYY-MM-DD.md` / `.json`.

## Which strategy runs

No strategy has passed testing (6 of 6 rejected — see `RESULTS_*.md`). The default (`orb_vwap`) is therefore a
**plumbing test**: it exercises every part of the system with a strategy we already know loses money, so its
simulated P&L means nothing about profitability. `--strategy none` runs the same system without ever entering.
