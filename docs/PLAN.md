# NQ Bot — Research & Deployment Plan (Nov 4, 2026)

> **Status update (Nov 4, 2026, evening):** the ORB strategy and both pre-registered intraday-momentum hypotheses
> failed on 2019–2025 MNQ data. See `RESULTS_ORB.md` and `RESULTS_INTRADAY_MOMENTUM.md`. Holdout untouched;
> nothing goes to paper or live trading as a strategy. IB paper is used only to drill the execution mechanics
> (`PAPER_DRILLS.md`). **Strategy search is closed:** three disciplined tests is the limit on this data; testing more
> ideas until one looks good would be overfitting. Any future idea must be pre-registered with an outside rationale.

Prices, fees and margins below that come from third-party pages are marked *verify*. Confirm them
with the broker/exchange before relying on them. Nothing in this document is a backtest result.

---

## 0. Market facts the code depends on

| | NQ | MNQ |
|---|---|---|
| Point value | $20 | $2 |
| Tick | 0.25 = $5.00 | 0.25 = $0.50 |
| Notional at ~28,400 | ~$568,000 | ~$56,800 |
| Expiry | 3rd Friday of Mar/Jun/Sep/Dec | same |

- Front month today is **Z26 (Dec 2026)**, expiring Dec 18. The bot rolls to **H27** on Dec 10 (8 days early, when volume moves). `python cli.py contract` prints this.
- NQ1!, NQ=F and Databento's `NQ.c.0`/`NQ.v.0` are *continuous chart series*. They are fine for research and cannot be ordered. The bot qualifies the real contract with the broker and checks its multiplier before trading.
- Your two Google screenshots a few minutes apart showed 28,423.50 and 28,741.50 for "the same" symbol. Search snippets and AI overviews are stale or mixed sources, which is exactly why the bot only acts on the broker's own feed.
- Globex trades nearly 24h Sun–Fri with a daily break; this build trades **RTH only (9:30–16:00 ET)** and is flat by 15:55, avoiding overnight gaps and overnight margin.

**Account-size reality:** at the default 0.5%-of-equity risk, a $10,000 account risks $50 per trade. A 20-point stop costs ~$42 per MNQ (with costs) but ~$405 per NQ, so **NQ is not tradable at this size with sane risk — start with MNQ.** The sizing code returns 0 contracts rather than round up.

**Margin cap (IBKR, Nov 4, 2026):** MNQ intraday initial margin is $4,756.62 (overnight $6,795.17); NQ is $47,566.22 intraday. With the 50% margin-utilisation limit, a $10,000 account can hold only **1 MNQ** — so the partial-profit step never fires below ~$19,000 equity. All-in MNQ cost is $0.614 per contract per side ($0.25 commission + $0.353 CME + $0.011 NFA).

**Event blackout caveat:** CPI, PPI and jobs reports come out at 8:30 ET, before this strategy's 9:30 start, so their blackout never blocks an entry — the opening range on those days already contains the reaction. Only FOMC (2:00 PM ET) interacts with the bot, by flattening any open trade at 1:45.

## 1. Broker / API options

| Option | API | Fit | Notes |
|---|---|---|---|
| **Interactive Brokers** (recommended first) | TWS API via `ib_async` (Python) | Best for this project | Free paper account (`DU…`), native bracket/OCA orders held server-side, mature Python library. Futures commission ~$0.85 standard / ~$0.25 micro per contract plus exchange fees (*verify*). Needs TWS or IB Gateway running. |
| Tradovate (NinjaTrader group) | REST + WebSocket | Good, cloud-native | Supports bots via API; third-party pages say the API is a paid add-on on the free plan (~$30/mo, *verify*). Popular with prop firms, which have their own automation rules. |
| NinjaTrader desktop | NinjaScript (C#) | Good if you want C# | Windows desktop; strong for strategy dev, but leaves Python. |
| Rithmic-based brokers | R-protocol API | Low-latency | More complex; not needed for 1-minute bars. |
| TradingView alerts → webhook bridge (e.g. PickMyTrade → Tradovate) | Webhooks | Easiest, least control | Fine for prototypes; you lose fill confirmation logic and the risk engine lives elsewhere. Not recommended for this design. |

The code isolates the broker behind `broker/base.py`, so Tradovate can be added later as another adapter.

## 2. Strategy and why it *might* have an edge

**Chosen: opening-range breakout (ORB) with a VWAP and trend-regime filter, RTH only, one trade per direction per day.**

- Rules: wait for the first 15 min (configurable); long only if a 1-min bar closes above the OR high **and** above session VWAP **and** the regime is bullish (fast EMA > slow EMA, slow EMA rising, price > VWAP, volatility not extreme). Short is the mirror image. Stop = tighter of OR midpoint or 1.5×ATR; partial at 1R with stop to breakeven; final target 2R; no entries after 11:30; flat by 15:55.
- Why it might work: there is published academic work on intraday momentum in US index products — e.g. Gao, Han, Li & Zhou (Journal of Financial Economics, 2018) on early-session returns predicting late-session returns, and Zarattini & Aziz (SSRN, 2023) on opening-range breakouts in QQQ. The proposed mechanism is that overnight information and institutional rebalancing get resolved in the first part of the session, producing follow-through on some days.
- Why it might not: published edges shrink after publication, those studies used specific instruments/periods, and your costs and slippage are real. The ORB's small number of parameters is a feature — fewer knobs means less room to overfit.
- **"AI" honestly scoped:** the regime engine is deliberately rule-based and measurable. A machine-learning classifier (e.g. gradient boosting on the same features) is a *later* experiment and only replaces the rules if it beats them **out of sample** after costs. LLM-style "sentiment" is not used for trade decisions.
- Strategies from the brief that are deferred: pure mean reversion (works against ORB on the same days — test separately), order-flow (needs tick/MBO data and much more work), multi-timeframe confirmation (easy to add as a regime feature once the baseline is measured).

## 3. Architecture

| Layer | Module | Key behaviour |
|---|---|---|
| Market data | `data.py`, `live.py` | Databento for history; IB 1-min bars live; stale-data watchdog |
| Strategy engine | `strategy.py` | Emits a `Signal` (side, entry ref, stop, target, partial) |
| Analysis / regime | `features.py`, `regime.py` | Causal indicators only; six regime labels |
| Risk engine | `risk.py` | Gates every entry; sizes from equity, stop distance, costs, margin |
| Order execution | `broker/*.py` | Brackets; duplicate guard; rejection/cancel handling; entry timeout |
| Position management | `engine.py` | Broker-confirmed fills only; partials; breakeven; session flatten |
| Logging / performance | `journal.py`, `metrics.py` | JSON-lines decision log; full metric set |
| Monitoring / shutdown | `live.py`, `risk.py` | Disconnect, stale data, abnormal bars, kill switch, webhook alerts |

Stack: Python 3.10+, pandas/numpy, `ib_async`, `databento`. Secrets live in `.env` (git-ignored) and are never logged. Hosting: run on your own PC for paper; for later always-on use, a small cloud VM in a US-East region running IB Gateway plus the bot under a process supervisor (systemd), with alerts to your phone.

## 4. Data feeds required

| Purpose | Feed | Cost model |
|---|---|---|
| Backtesting | Databento `GLBX.MDP3`, schema `ohlcv-1m`, symbol `MNQ.v.0` / `NQ.v.0` (or specific contracts) | Pay-as-you-go historical from ~$0.50/GB (*verify* in portal) |
| Live/paper bars | Interactive Brokers CME real-time data | Monthly market-data subscription through IB (*verify* current price) |
| Economic calendar | BLS release schedule (CPI, PPI, NFP), Federal Reserve FOMC calendar → `config/events.csv` | Free; you maintain it |

Continuous Databento series are not back-adjusted; the strategy compares prices only within one session, so roll gaps don't leak into signals.

## 5. Realistic assessment

- Most retail day traders lose money. A large study of Brazilian futures day traders (Chague, De-Losso & Giovannetti, 2019) found the overwhelming majority of those who persisted for a year lost money. Assume the null hypothesis: **this strategy has no edge until real out-of-sample data says otherwise.**
- Sanity check from this build: on *random* synthetic data the bot loses roughly its trading costs (profit factor ~0.8). That's the correct behaviour for a strategy with no edge, and it shows how big the cost hurdle is at 1-contract MNQ size.
- Even a genuinely positive system can have long losing streaks; the Monte Carlo output shows the range of drawdowns the same trades could produce in a different order.
- Risks beyond strategy: futures losses can exceed account equity in fast markets; broker or internet outages; data errors; contract-roll mistakes; your own temptation to override the limits after losses.
- Taxes: US futures are generally Section 1256 contracts (60/40 treatment) — check with a tax professional.

## 6. Risk-management framework (defaults in `settings.yaml`)

| Control | Default | Effect when hit |
|---|---|---|
| Risk per trade | min(0.5% equity, $100) | size shrinks; 0 contracts = skip |
| Daily loss (incl. open P&L) | $250 | flatten + no entries rest of day |
| Trades per day | 2 | no more entries |
| Consecutive losses | 2 | no entries rest of day |
| Cooldown after a loss | 30 min | entries blocked |
| Max contracts | 2 | hard cap |
| Margin utilisation | ≤ 50% of equity | caps size |
| Profit protection | after +$200, stop if 50% given back | no entries rest of day |
| Max drawdown from peak | 10% | **kill switch**, persists until you restart deliberately |
| Abnormal bar | range > 6× ATR | flatten + halt day |
| Stale data (RTH) | 120 s without a bar | flatten + halt day |
| Event blackout | ±15 min of listed events | no entries; flatten before high-impact |
| Session | flat by 15:55 ET | no overnight risk |

Never: averaging down, martingale, size increases after losses, trading without a stop, trading a position the broker hasn't confirmed. The bot has no code path that raises size or loosens limits on its own.

## 7. Backtesting plan

1. **Data:** 2019-01 → 2026-10 MNQ 1-minute bars (covers 2020 crash, 2021 rally, 2022 bear, 2023–26 regimes, plenty of CPI/FOMC days).
2. **Hold out** 2025-07 → 2026-10 entirely. Don't look at it until step 6.
3. **Baseline** on 2019 → mid-2025 with default settings. Read `by_regime`, `by_hour`, `by_side`.
4. **Walk-forward** (`cli.py walkforward`, 5 folds, small grid). Only the concatenated out-of-sample result counts.
5. **Stress:** double slippage (`slippage_ticks: 2`), double commission, 30-min OR, events file populated vs empty.
6. **Holdout test:** run once on the untouched period with the final settings.
7. **Monte Carlo:** read `p_losing` and `max_dd_pct_p95_worst`.

**Pass gate (all required) before paper:**
- ≥ 200 out-of-sample trades; profit factor ≥ 1.2 after costs; positive expectancy at 2× slippage.
- Max drawdown within what you'd tolerate in real money; Monte Carlo 95th-percentile drawdown < 2× historical.
- Holdout period not materially worse than walk-forward OOS.
- Results not dependent on one year, one side, or one hour of the day.

Win rate alone is never a criterion (a 2R target system can be healthy at ~40%).

## 8. Paper-trading plan

1. IB paper account + CME data subscription + futures permission; TWS paper on port 7497.
2. `python cli.py paper` during RTH; watch the decision log and IB's order window side by side.
3. **Week 1 — mechanics:** verify brackets appear, stops/targets sit at the right prices, partial + breakeven fires, 15:55 flatten works, rejected orders are reported.
4. **Fault drills:** kill the bot mid-trade (stop must stay at IB); unplug network; restart with an open position (bot must refuse); set a tiny daily-loss limit to watch it trip; run across the Dec 10 roll and confirm the switch to MNQH7.
5. **Weeks 2–12 — performance:** at least 60–100 paper trades. Compare paper fills to what the backtester would have assumed on the same days (slippage reality check).
6. **Gate to even discuss live:** paper results within the backtest's expected range, zero unexplained position mismatches, every fault drill passed. Then 1 MNQ only, with limits at or below these defaults.

## 9–10. Code
See `README.md` for layout, install and commands. IBKR adapter is written to IB's documented API but was not run against TWS in the build environment — the fault drills in §8 are its real test.

---

## 11. Safety verification (Nov 4, 2026) — what was checked, fixed, and tested

All covered by `tests/test_safety.py` (21 tests pass in total).

| Question | Finding | Status |
|---|---|---|
| Can 0.5% risk exceed the $250 daily limit? | No by design: each trade's budget is the smallest of 0.5% of equity, $100, and what's left of today's $250. Two max losses (the consecutive-loss halt) = ~$200. **Can overshoot** by slippage on a gap-through stop or by one bar's move before the open-P&L check runs. | OK, with known overshoot |
| Partial + breakeven with real fills? | Works in sim (tested to the cent). Partial is a market order *after* price touches 1R, so it can fill below 1R. Added stop reconciliation for IB: resized after partial entry fills, replaced if missing, cancelled if orphaned. Stuck partial entries now cancel the remainder. | Fixed; needs IB paper drills |
| Rollover without stray positions? | Never holds overnight. **Fixed:** a long-running bot kept trading the old month after the roll date — it now exits while flat. Startup refuses any NQ/MNQ position or order in **any** month. | Fixed |
| Does the 10% kill switch close positions? | **Was entries-only** and ignored open losses. **Fixed:** drawdown now includes open P&L and flattens; kill persists across days and restarts until `reset-kill`. | Fixed |
| Safe recovery after disconnect/restart? | Disconnect: brackets stay at IB, bot exits. **Fixed:** restarting used to reset today's loss count and the kill switch — risk state is now saved after every bar. Startup refuses open positions/orders, so recovery is manual by design. | Fixed; manual recovery |

Still only provable on an IB paper account: bracket child resizing, stop replacement, reconnect behaviour, the Dec 10 roll.
