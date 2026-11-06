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
| Transport | Webhook | In-process (no internet hop to fail or spoof) | Built |
| Order routing / execution | Router → Tradovate | `SimBroker` (simulated); `IBKRBroker` for IB **paper** later | Built; IB paper waits on account approval |
| Stops & targets | Router / broker brackets | Bracket on every entry; stop reconciled every bar; missing stop = emergency flatten | Built, tested |
| Position sizing | Fixed contracts | Equity-, stop- and margin-based, capped; invalid quantities refused | Built, tested |
| Logging & reporting | Members dashboard | JSONL journal + daily report per session | Built, tested |
| Emergency stop | Toggle in dashboard | `py cli.py kill` (or Ctrl+C) → flatten + halt, persists across restarts | Built, tested |

Why not Tradovate or webhooks right now: Tradovate's API needs a funded live account (≥ $1,000) plus an API
add-on (~$25/month); TradingView webhooks need the Essential plan or higher ($14.95/month) and expire after
2 months on that plan. Neither adds anything the in-process design lacks, and the webhook hop adds a security
surface (a public URL that accepts orders). Both can be added later behind the same risk engine.

## Commands

```
py cli.py paper-replay --csv data/mnq_train.csv --days 5     # rehearse on real past sessions (no subscription)
py scripts/readiness_check.py data/mnq_train.csv --days 5    # pass/fail pre-week checks
py cli.py paper-live                                         # live data, simulated orders (needs Databento live)
py cli.py paper-live --strategy none                         # monitor + report only, never enters
py cli.py kill                                               # emergency stop from a second PowerShell window
py cli.py reset-kill                                         # clear a kill after you've reviewed why
```
Outputs land in `logs/paper/`: `decisions_*.jsonl`, `risk_state.json`, `report_YYYY-MM-DD.md` / `.json`.

## Which strategy runs

No strategy has passed testing (6 of 6 rejected — see `RESULTS_*.md`). The default (`orb_vwap`) is therefore a
**plumbing test**: it exercises every part of the system with a strategy we already know loses money, so its
simulated P&L means nothing about profitability. `--strategy none` runs the same system without ever entering.
