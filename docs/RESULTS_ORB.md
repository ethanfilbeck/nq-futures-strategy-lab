# Results: Opening-Range Breakout (ORB) on MNQ — FAILED

**Data:** Databento `GLBX.MDP3` `ohlcv-1m`, `MNQ.v.0` (volume-rolled continuous), 2019-05-06 → 2025-06-30,
2,167,313 one-minute bars, 1,588 regular sessions. Holdout 2025-07 → 2026-10 not downloaded.
**Costs:** $0.62 per contract per side (IBKR, Nov 2026) + 1 tick slippage on market/stop fills; targets fill only if traded through by 1 tick.

## 1. Edge test — 1 MNQ contract, sizing never filters a signal

| Metric | Value |
|---|---|
| Trades | 1,602 |
| Win rate | 32.5% |
| Profit factor | **0.88** |
| Net P&L | **−$6,721** (−$4.20 / trade, −0.08 R) |
| Before commissions | −$4,735 (it loses before costs too) |
| t-statistic of mean trade | −2.25 |
| Max drawdown | −$7,537 |
| Monte Carlo (5,000 reshuffles) | ends negative in 99% of runs |

| Year | 2019* | 2020 | 2021 | 2022 | 2023 | 2024 | 2025* |
|---|---|---|---|---|---|---|---|
| Net $ | −389 | −815 | −1,513 | −3,152 | −695 | −206 | +49 |

\*partial years. Both sides, both trend regimes and every entry hour lost money.

## 2. Walk-forward (5 anchored folds, 8 parameter combinations, only unseen data counted)

Grid: opening range 15/30 min × reward:risk 1.5/2.0 × ATR stop 1.0/1.5.

| Fold | Trained through | Tested through | Chosen params | OOS trades | OOS net | PF |
|---|---|---|---|---|---|---|
| 0 | 2020-05-11 | 2021-05-20 | OR 30, RR 2.0, ATR 1.5 | 247 | −$1,479 | 0.79 |
| 1 | 2021-05-20 | 2022-05-30 | OR 15, RR 2.0, ATR 1.0 | 290 | −$2,273 | 0.73 |
| 2 | 2022-05-30 | 2023-06-08 | OR 30, RR 1.5, ATR 1.5 | 225 | −$780 | 0.89 |
| 3 | 2023-06-08 | 2024-06-18 | OR 30, RR 1.5, ATR 1.5 | 216 | −$424 | 0.92 |
| 4 | 2024-06-18 | 2025-06-30 | OR 30, RR 1.5, ATR 1.5 | 226 | −$1,165 | 0.87 |
| **All OOS** | | | | **1,204** | **−$6,120** | **0.83** |

Every fold lost on unseen data, so the best settings chosen on past data didn't carry forward.

## 3. Your actual account settings ($10,000, 0.5% risk)

142 trades, PF 0.77, −$487. Most signals were skipped: in the edge test the average losing trade cost ~$51 per MNQ
(≈25 points incl. costs), right at or above the $50 per-trade budget, so the bot mostly traded only on calmer days.

## 4. Bug found and fixed during testing

The first run compared each bar's volatility with a median that included the quiet overnight session, so a normal
open looked ~3× "too volatile" and half the entry window was blocked. The baseline now compares each minute with
the same minute on the previous 20 sessions. All results above use the fix.

## Verdict

Fails every pre-set gate in `PLAN.md` §7 (needed PF ≥ 1.2 out of sample). Not paper-traded or tuned further.
