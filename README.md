# NQ / MNQ Futures Strategy Lab — a system that decides whether a strategy has an edge

> **⚠️ Not a money-making bot.** 11 of 12 tested strategies failed. One (the pre-FOMC drift) passed and replicated
> on two more markets (S&P 500 and Russell 2000), and is now being tested forward **on paper only**. This is a research and software-engineering
> project, not trading advice. Nothing has been traded with real money.

A Python research-and-execution system for Micro E-mini Nasdaq-100 futures (MNQ): causal feature pipeline,
conservative bar-by-bar simulator, walk-forward and Monte Carlo testing, pre-registered hypotheses, a hard-limit
risk engine, an **unattended paper-trading runner**, a TradingView port with an authenticated webhook receiver, and
an Interactive Brokers **paper-only** execution adapter verified with 13 failure drills.

The goal is **not** a bot that is forced to trade. It is a system that can say *no* — it said no 11 times — and
that makes the one *yes* earn it.

## Headline

| | |
|---|---|
| Ideas tested (2019-05 → 2025-06 MNQ, real costs) | **12**, all but the first pre-registered and hashed before running |
| Rejected | **11** |
| Survivor | **H8 pre-FOMC drift**: passed on MNQ (t 3.02), weak but positive on 16 months of held-out MNQ data (t 0.34), **replicated on S&P 500 micro futures** (59 events, t 3.56) **and Russell 2000 micro futures** (59 events, t 2.45), beating random long holds in both |
| Status of H8 | Replicated in two markets, **forward paper trading** on an IB paper account (`fomc-paper`), ~8 events a year. Not real money. |
| Broker drills | 13 of 13 pass on an IB paper account; 3 bugs found and fixed |
| Security review | Webhook receiver threat-modeled; 2 denial-of-service weaknesses found and fixed ([report](docs/SECURITY_WEBHOOK.md)) |

## Results (2019-05 → 2025-06 MNQ unless noted; $0.62/side + 1 tick slippage, 1 contract)

| Strategy | How it was tested | Trades | PF | Net per contract | Verdict |
|---|---|---|---|---|---|
| Opening-range breakout + VWAP/trend filter | full period + 5-fold walk-forward | 1,204 OOS | 0.83 | −$6,120 | **Fail** — [details](docs/RESULTS_ORB.md) |
| H1 first half-hour momentum (Gao et al. 2018) | pre-registered | 1,277 | 0.84 | −$6,059 | **Fail** — [details](docs/RESULTS_INTRADAY_MOMENTUM.md) |
| H2 rest-of-day momentum (Baltussen et al. 2021) | pre-registered | 1,277 | 0.93 | −$2,611 | **Fail** — [details](docs/RESULTS_INTRADAY_MOMENTUM.md) |
| H3 overnight drift (Boyarchenko et al. 2023) | pre-registered, t ≥ 3 | 1,576 | 0.98 | −$576 | **Fail** — [details](docs/RESULTS_FAMILY2.md) |
| H4 liquidity sweep of prior-day high/low | pre-registered, t ≥ 3 | 288 | 1.20 | +$1,204 | **Fail** (t 0.71) — [details](docs/RESULTS_FAMILY2.md) |
| H5 VWAP pullback in a trend | pre-registered, t ≥ 3 | 1,399 | 0.94 | −$2,336 | **Fail** — [details](docs/RESULTS_FAMILY2.md) |
| H6 turn of the month | pre-registered, t ≥ 3 + beat random longs | 73 | 1.14 | +$2,892 | **Fail** (worse than random long holds) — [details](docs/RESULTS_FAMILY3.md) |
| H7 overnight-gap reversal | pre-registered, t ≥ 3 | 439 | 0.92 | −$3,742 | **Fail** — [details](docs/RESULTS_FAMILY3.md) |
| **H8 pre-FOMC drift** (Lucca & Moench 2015) | pre-registered, t ≥ 3 + beat random longs | 48 | 3.34 | +$7,115 | **Pass** (t 3.02) — [details](docs/RESULTS_FAMILY3.md) |
| ↳ H8 on held-out MNQ (2025-07 → 2026-10) | run once, rule frozen | 11 | — | +$368 | Consistent, weak (t 0.34) |
| ↳ H8 on S&P 500 micro (MES), 2019-05 → 2026-10 | pre-registered replication, run once | 59 | 3.55 | +$5,141 (MES) | **Replicates** (t 3.56) — [details](docs/RESULTS_H8_ES_REPLICATION.md) |
| ↳ H8 on Russell 2000 micro (M2K), 2019-05 → 2026-10 | pre-registered replication, run once | 59 | 2.29 | +$2,325 (M2K) | **Replicates** (t 2.45) — [details](docs/RESULTS_H8_M2K_REPLICATION.md) |
| H9 CPI / jobs-report days | pre-registered, t ≥ 3.5 + beat random longs | 141 | 1.05 | +$1,247 | **Fail** — [details](docs/RESULTS_FAMILY4.md) |
| H10 pre-holiday | pre-registered, t ≥ 3.5 + beat random longs | 59 | 1.84 | +$3,876 | **Fail** (t 1.70) — [details](docs/RESULTS_FAMILY4.md) |
| H11 opening-hour trend after a high-range day | pre-registered, t ≥ 3.5 | 253 | 1.08 | +$1,983 | **Fail** — [details](docs/RESULTS_FAMILY4.md) |

**Why H8 is still not "proven":** all three markets were tested on the same Fed meetings (48 of the 59 are the MNQ
training dates), so luck specific to those particular meetings would show up in all three. The Russell 2000 test is the
more informative replication (it moves less with the Nasdaq, and random long holds there lost money), but it is
weaker (t 2.45) and rests on a few good meetings. Published
research found the drift had faded in 2016–2019; it reappeared in 2020–2026, a period of unusual rate
uncertainty. The deciding evidence is forward: FOMC meetings no test has seen.

**Methodology checks:** H3 reproduced a published finding (the 2–3 a.m. ET drift was +2.27 pts/day before 2021 and
+0.16 after). Long-only calendar ideas (H6, H9, H10) are benchmarked against random long holds of the same length,
because in a rising market any long-only rule looks profitable.

**Strategy search on this data is closed.** Each extra idea tested on the same data raises the odds of a lucky pass;
the bar rose from t ≥ 3.0 to t ≥ 3.5 as the count grew. New ideas need new data.

## Automated paper trading (Sniper Den-style architecture, simulated orders only)

Live 1-minute bars → the same engine as the backtests → simulated broker with bracket stops/targets → journal,
restart-safe risk state and a daily report. Safeguards: stale or disconnected feed, bad/duplicate bars, missing
stop, oversize position, invalid order quantity, kill file / Ctrl+C. Signals come from the bot's own strategy **or**
from TradingView alerts through an authenticated webhook receiver (shared secret, IP allowlist, replay and flood
protection), the same pattern as commercial alert-to-broker services. A readiness script replays real sessions and
proves the paper runner makes **exactly** the same trades as the backtester. Details, architecture and the
comparison with TradingView-webhook-router setups: [`docs/AUTOMATION.md`](docs/AUTOMATION.md).
What you still configure yourself: [`docs/MANUAL_SETUP.md`](docs/MANUAL_SETUP.md).

## Methodology (how leakage and self-deception are prevented)

- **Causal features only.** Every indicator at bar *t* uses bars ≤ *t*; unit tests truncate the future and assert past values don't change.
- **Conservative fills.** Orders fill at the *next* bar's open with slippage; stops fill first if stop and target touch in the same bar; targets must trade through by a tick.
- **Real costs.** IBKR MNQ commission + CME + NFA fees ($0.614/side), 1-tick slippage, 2-tick stress test.
- **Walk-forward.** Parameters are chosen on past data and judged only on the next unseen window.
- **Pre-registration.** New hypotheses are written down with pass/fail criteria and hashed (`docs/PREREG_HASH.txt`) *before* the first test. Failures are published, not tuned away.
- **Untouched holdout.** The last 16 months were downloaded only after H8 passed, and used once, for H8 only.
- **Replication on a second market.** A passing rule is re-tested, unchanged, on a related market (H8 → S&P 500 micro).
- **Monte Carlo** reshuffles trade order to show the spread of outcomes the same trades could produce.

## Security and fault-tolerance controls

- Webhook receiver security review (threat model, controls, 2 fixed findings, residual risks): [`docs/SECURITY_WEBHOOK.md`](docs/SECURITY_WEBHOOK.md).

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
nq_bot/family2.py        pre-registered family 2 (H3 overnight drift, H4 sweep, H5 VWAP pullback)
nq_bot/paper.py          unattended paper runner, Databento live feed, replay
nq_bot/report.py         daily performance report
nq_bot/webhook.py        TradingView webhook receiver (authenticated, rate-limited)
nq_bot/external.py       turns webhook signals into risk-checked orders
tradingview/holdout_orb.pine  TradingView (Pine v6) port of the ORB with the same risk limits
nq_bot/risk.py           all risk limits and position sizing
nq_bot/engine.py         the trading loop shared by backtest, replay and live
nq_bot/broker/sim.py     conservative paper broker (next-bar fills, slippage, stop-first)
nq_bot/broker/ibkr.py    Interactive Brokers adapter (paper-locked)
nq_bot/backtest.py       backtest, walk-forward
nq_bot/metrics.py        net, win rate, PF, drawdown, Sharpe, Sortino, expectancy, Monte Carlo
nq_bot/live.py           real-time runner + watchdogs
nq_bot/journal.py        JSON-lines decision log + webhook alerts
cli.py                   commands
tests/                   unit, regression and mocked-integration tests (81)
research_edge.py         1-contract edge study for the ORB
wf_edge.py               ORB walk-forward
run_momentum_prereg.py   runs the pre-registered momentum test exactly as written
run_family2_prereg.py    runs family 2 exactly as written
scripts/readiness_check.py  pre-week checks on real replayed sessions
docs/                    plan, pre-registration, results, paper drills, publishing checklist
scripts/prepublish_check.py  blocks a push containing secrets or licensed data
nq_bot/drill.py          IB paper drills (13 drills, results in docs/PAPER_DRILLS.md)
nq_bot/family3.py        pre-registered family 3 (H6 turn of month, H7 gap reversal, H8 pre-FOMC drift)
nq_bot/family4.py        pre-registered family 4 (H9 macro days, H10 pre-holiday, H11 high-range trend)
nq_bot/fomc_paper.py     forward PAPER tracking of H8 on the IB paper account
run_family3_prereg.py / run_family3_holdout.py / run_family4_prereg.py / run_h8_es_replication.py / run_h8_m2k_replication.py
scripts/check.py         every quality gate in one command (what CI runs)
scripts/verify_prereg.py    fails if a pre-registration was edited after it was frozen
scripts/validate_data.py    sanity-checks a bar file before a backtest uses it
```

## Install

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # then fill in keys
pytest -q                                               # 79 passed, 2 skipped (those need licensed data)
```

## Quality gates

[![CI](https://github.com/ethanfilbeck/nq-futures-strategy-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/ethanfilbeck/nq-futures-strategy-lab/actions/workflows/ci.yml)

```bash
pip install -r requirements-dev.txt
python scripts/check.py        # lint + security rules, tests, pre-registration hashes, publish check, dependency audit, types
```

GitHub Actions runs the same command on Ubuntu and Windows for every push, plus a full-history secret scan
(Gitleaks) and weekly dependency updates (Dependabot). `requirements.lock` pins exact versions for reproducing
results. What each tool does, and which tools were rejected and why: [`docs/TOOLING.md`](docs/TOOLING.md).
How the code is layered and how research is kept apart from execution: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
The rules every new idea follows: [`docs/RESEARCH_PROTOCOL.md`](docs/RESEARCH_PROTOCOL.md).

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
python cli.py fomc-paper                   # forward paper test of H8 at the next FOMC (docs/FOMC_PAPER.md)
python cli.py paper-replay --csv data/mnq_train.csv --days 5   # rehearse the paper runner on real past sessions
python cli.py paper-live                   # live data, SIMULATED orders (needs Databento live)
python cli.py paper-live --strategy tradingview --webhook   # TradingView alerts in, simulated orders out
python cli.py kill                         # emergency stop for a running paper session
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
