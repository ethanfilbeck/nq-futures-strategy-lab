# NQ / MNQ Futures Strategy Lab — a system that decides whether a strategy has an edge

> **⚠️ Not a profitable bot. Every strategy tested here failed (see Results). This is a research and
> software-engineering project, not trading advice. Nothing has been traded with real money.**

A Python research-and-execution system for Micro E-mini Nasdaq-100 futures (MNQ): causal feature
pipeline, conservative bar-by-bar simulator, walk-forward and Monte Carlo testing, pre-registered
hypotheses, a hard-limit risk engine, and an Interactive Brokers **paper-only** execution adapter.

The goal is **not** a bot that is forced to trade. It is a system that can say *no* — and so far it has,
three times, on six years of real data.

## Results so far (2019-05 → 2025-06 MNQ, real costs; 2025-07 → 2026-10 held out, unseen)

| Strategy | How it was tested | Trades | Profit factor | Net per contract | Verdict |
|---|---|---|---|---|---|
| Opening-range breakout + VWAP/trend filter | full period + 5-fold walk-forward | 1,204 OOS | 0.83 | −$6,120 | **Fail** — [details](docs/RESULTS_ORB.md) |
| Intraday momentum H1 (first half-hour, Gao et al. 2018) | pre-registered, no tuning | 1,277 | 0.84 | −$6,059 | **Fail** — [details](docs/RESULTS_INTRADAY_MOMENTUM.md) |
| Intraday momentum H2 (rest-of-day, Baltussen et al. 2021) | pre-registered, no tuning | 1,277 | 0.93 | −$2,611 | **Fail** — [details](docs/RESULTS_INTRADAY_MOMENTUM.md) |

Nothing has been traded with real money. All execution is locked to an IB paper account.

**Research status: closed.** After three disciplined tests, the strategy search is stopped on purpose. Trying
idea after idea until one looks profitable on the same data is how overfitting happens. Any future hypothesis must
be pre-registered, needs a reason that comes from outside this data, and counts toward the multiple-testing bar.

## Methodology (how leakage and self-deception are prevented)

- **Causal features only.** Every indicator at bar *t* uses bars ≤ *t*; unit tests truncate the future and assert past values don't change.
- **Conservative fills.** Orders fill at the *next* bar's open with slippage; stops fill first if stop and target touch in the same bar; targets must trade through by a tick.
- **Real costs.** IBKR MNQ commission + CME + NFA fees ($0.614/side), 1-tick slippage, 2-tick stress test.
- **Walk-forward.** Parameters are chosen on past data and judged only on the next unseen window.
- **Pre-registration.** New hypotheses are written down with pass/fail criteria and hashed (`docs/PREREG_HASH.txt`) *before* the first test. Failures are published, not tuned away.
- **Untouched holdout.** The last 16 months are not downloaded until a strategy passes everything else.
- **Monte Carlo** reshuffles trade order to show the spread of outcomes the same trades could produce.

## Security and fault-tolerance controls

- `scripts/prepublish_check.py` blocks a push if any committed file contains API keys, broker account IDs, emails, local paths, `.env`, market data or trade logs.

- Secrets live in a git-ignored `.env`, are read from the environment, and are never logged or written to the journal.
- Paper lock: refuses non-paper IB ports and non-`DU` accounts; live needs four separate opt-ins including a typed confirmation.
- Server-side protection: every entry is an IB bracket, so the stop survives a crash or disconnect.
- Reconciliation: the stop is matched against the broker's real position on every poll (resized, replaced if missing, cancelled if orphaned); unknown fills or mismatches flatten and halt.
- Startup refuses any existing NQ/MNQ position or working order in any contract month; exits at the roll date while flat.
- Risk state (daily losses, halts, kill switch, peak equity) is saved atomically after every bar, so a restart can't reset limits.
- Watchdogs: stale data, abnormal bars, disconnects and engine exceptions halt entries and flatten where possible.

## What it does on every 1-minute bar

```
data ─► features (VWAP, ATR, EMAs, opening range) ─► regime classifier ─► ORB strategy
     ─► event blackout ─► risk gates + position sizing ─► bracket order (entry + stop + target)
     ─► broker-confirmed fills ─► partial at 1R, stop to breakeven ─► flatten 15:55 ET
```

## Project layout

```
config/settings.yaml     every tunable: instrument, session, strategy, regime, risk, IBKR
config/events.csv        CPI/PPI/NFP/FOMC times you maintain (blackouts)
nq_bot/contracts.py      tick/point values, front-month + roll date (e.g. MNQZ6 → MNQH7 on Dec 10, 2026)
nq_bot/data.py           CSV loader, Databento downloader, synthetic data (tests only)
nq_bot/features.py       causal indicators — no look-ahead (tested)
nq_bot/regime.py         bullish / bearish / sideways / high-vol / low-vol / no-trade
nq_bot/strategy.py       opening-range breakout with VWAP + trend filter
nq_bot/momentum.py       pre-registered intraday momentum (H1/H2)
nq_bot/risk.py           all risk limits and position sizing
nq_bot/engine.py         the trading loop shared by backtest, replay and live
nq_bot/broker/sim.py     conservative paper broker (next-bar fills, slippage, stop-first)
nq_bot/broker/ibkr.py    Interactive Brokers adapter (paper-locked)
nq_bot/backtest.py       backtest, walk-forward
nq_bot/metrics.py        net, win rate, PF, drawdown, Sharpe, Sortino, expectancy, Monte Carlo
nq_bot/live.py           real-time runner + watchdogs
nq_bot/journal.py        JSON-lines decision log + webhook alerts
cli.py                   commands
tests/                   unit tests (26)
research_edge.py         1-contract edge study for the ORB
wf_edge.py               ORB walk-forward
run_momentum_prereg.py   runs the pre-registered momentum test exactly as written
docs/                    plan, pre-registration, results, paper drills, publishing checklist
scripts/prepublish_check.py  blocks a push containing secrets or licensed data
nq_bot/drill.py          IB paper drills
```

## Install

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # then fill in keys
pytest -q                                               # should print 26 passed
```

## Commands

```bash
python cli.py contract                     # contract to trade today + specs
python cli.py backtest --synthetic         # plumbing check on RANDOM data (expect a small loss = costs)
python cli.py fetch --symbol MNQ.v.0 --start 2019-05-06 --end 2025-07-01 --out data/mnq_train.csv   # holdout stays unseen
python cli.py backtest --csv data/mnq_train.csv
python cli.py walkforward --csv data/mnq_train.csv --folds 5
python cli.py paper                        # IBKR paper account, needs TWS/Gateway running
python cli.py reset-kill                   # clear the drawdown kill switch, deliberately
python cli.py drill status                 # IB paper drills for the execution mechanics (docs/PAPER_DRILLS.md)
```

Backtests write `logs/trades.csv` and a `logs/decisions_*.jsonl` file recording every order,
skip reason, fill, partial, flatten and closed trade.

## What you need (accounts, keys, permissions)

| Need | For | Notes |
|---|---|---|
| Databento account + API key | historical 1-min CME data | pay-as-you-go historical; check the cost estimate before a big pull |
| Interactive Brokers account | paper (and later live) execution | paper account IDs start with `DU`; the bot refuses anything else in paper mode |
| IB futures trading permission | ordering MNQ/NQ | enable in IB account settings |
| IB CME real-time market data subscription | live bars over the API | paper accounts use the live account's subscriptions |
| TWS or IB Gateway running | API connection | enable API, socket port 7497 (TWS paper) or 4002 (Gateway paper), add 127.0.0.1 to trusted IPs |
| Optional webhook URL | alerts to your phone | Discord/Slack-style `ALERT_WEBHOOK_URL` |

## Safety interlocks (all on by default)

- Paper mode only. Live needs `mode: live` **and** `--live` **and** `NQBOT_ENABLE_LIVE=I_UNDERSTAND_THE_RISK` **and** typing `TRADE REAL MONEY`.
- Refuses non-paper IB ports and non-`DU` accounts in paper mode.
- Refuses to start if a position already exists; trades the qualified quarterly contract only, and checks its multiplier.
- Every entry is a bracket: stop and target live on IB's servers, so a crash or disconnect leaves the position protected.
- No position is assumed until the broker reports a fill; unknown fills or position mismatches flatten and halt.
- Stale data, abnormal bars, broker disconnects and engine exceptions halt new entries (and flatten where possible).
- Daily loss and drawdown both count open P&L; hitting either flattens the position.
- Risk state (today's trades, losses, halts, peak equity, kill switch) is saved to `logs/risk_state.json` after every bar, so restarting the bot can't reset today's limits. The kill switch stays on until you run `reset-kill`.
- The protective stop is reconciled against the broker's real position on every poll: resized after partial fills, replaced if missing, cancelled if orphaned.
- At the roll date the bot exits while flat; restarting picks up the new contract. Startup refuses any NQ/MNQ position or working order in any month.

## Before you trust any number

1. Margin ($4,756.62 intraday) and commission ($0.614/side all-in) are IBKR's MNQ figures as of Nov 4, 2026 — recheck them every few months.
2. `config/events.csv` holds CPI, PPI, jobs-report and FOMC dates through Dec 2027 (from BLS and the Fed). It covers live/paper only; historical dates are needed for event-aware backtests.
3. Follow the gates in `docs/PLAN.md` §7–8. Live trading is not part of this build.

## Data and licensing

Market data comes from Databento and is **not included** (their terms restrict redistribution). Trade-level outputs
are also excluded because they contain prices derived from that data; aggregate results are in `docs/`.
To reproduce: create your own Databento key, put it in `.env`, then `python cli.py fetch ...` (about $8 for 2019–2025 MNQ 1-minute bars as of Nov 2026).

## License

MIT — see `LICENSE`.
