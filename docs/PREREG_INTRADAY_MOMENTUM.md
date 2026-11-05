# Pre-registration: Intraday Momentum on MNQ (written 2026-11-04, before any test)

This file is frozen before the first backtest. Its SHA-256 is recorded in `docs/PREREG_HASH.txt`
at the moment of freezing. Any later change to rules must be logged as a new, separate hypothesis.

## 1. The research behind it

| Paper | Instrument / period | Finding |
|---|---|---|
| Gao, Han, Li & Zhou, "Market Intraday Momentum", *Journal of Financial Economics* 129(2), 2018 | S&P 500 ETF (SPY), 1993–2013; similar in 10 other ETFs | Return from the previous close through the **first half-hour** predicts the **last half-hour** return. Stronger on volatile, high-volume, recession and macro-news days. |
| Baltussen, Da, Lammers & Martens, "Hedging Demand and Market Intraday Momentum", *Journal of Financial Economics* 142(1), 2021 | 60+ futures incl. **Nasdaq-100 (NQ)**, 1974–2020 | The **rest-of-day** return (previous close → 30 min before close) predicts the **last 30 minutes**. Attributed to gamma hedging by option dealers and leveraged-ETF rebalancing; reverses over the next few days. |

**What the research does NOT establish:**
- Neither paper's headline results include transaction costs. Baltussen et al. say the effect may not be exploitable by many investors after costs (they find it could survive in S&P 500 futures at ~1 tick).
- Gao et al. test SPY, not Nasdaq futures. Baltussen et al. include NQ, but their sample ends May 2020 — only our **June 2020 → June 2025** data is genuinely out of sample relative to them.
- Our MNQ data starts May 2019 (MNQ launch), which overlaps ~1 year with Baltussen et al.

## 2. Hypotheses (exactly two; no others will be tested on this data)

- **H1 (Gao et al.):** sign of `r_FH` = (price at 10:00 ET − previous session's 16:00 ET price) predicts the 15:30→16:00 move.
- **H2 (Baltussen et al.):** sign of `r_ROD` = (price at 15:30 ET − previous session's 16:00 ET price) predicts the 15:30→16:00 move.

Because two hypotheses are tested, the significance bar is raised (see §6).

## 3. Rules (identical for H1 and H2 except the predictor)

| Item | Rule |
|---|---|
| Instrument | MNQ, volume-rolled continuous series for research (Databento `MNQ.v.0`); live/paper would trade the front quarterly contract |
| "Previous close" | close of the 15:59 ET one-minute bar of the previous RTH session |
| "Price at 10:00" | close of the 9:59 bar; "price at 15:30" = close of the 15:29 bar |
| Signal time | close of the 15:29 bar (15:30:00 ET) |
| Direction | long if predictor > 0, short if < 0, no trade if exactly 0 |
| Entry | market order, filled at the open of the 15:30 bar + 1 tick adverse slippage |
| Exit | market order at the close of the 15:59 bar, filled at the next bar's open (≈16:00) + 1 tick adverse slippage |
| Profit target | none (time exit only, as in the papers) |
| Protective stop | entry ∓ 1.5 × (median absolute 15:30→16:00 move over the previous 20 sessions, in points), minimum 10 points; filled with 1 tick slippage (or at the open if gapped) |
| Trades per day | at most 1 |
| Skip day if | no 15:29 or 15:59 bar (half-days / missing data), no previous-session close, or fewer than 10 prior sessions for the stop estimate |
| Costs | $0.62 per contract per side (IBKR MNQ all-in, Nov 2026) + slippage above |
| Size (edge test) | 1 contract, all other risk limits loosened so sizing never filters a signal |
| Size (account test) | default `settings.yaml` risk rules on $10,000 (reported, not used for the pass decision) |
| Parameters tuned | **none** — so no walk-forward optimisation is needed; the whole period is a single test |

Regime filter, VWAP, event blackouts: **not used** (the papers find the effect *stronger* on news days).

## 4. Data split

- Test data: 2019-05-06 → 2025-06-30 (already downloaded).
- Holdout: 2025-07-01 → 2026-10-31 — **not downloaded or viewed** unless a hypothesis passes §6.

## 5. Measured and reported (for both hypotheses, pass or fail)

Gross and net P&L per contract, trades, win rate, profit factor, expectancy, t-statistic of mean net trade P&L,
max drawdown, Sharpe/Sortino (daily), results by calendar year, by side, on high- vs low-volatility days
(above/below median first-half-hour absolute return), Monte Carlo of trade order, results at 2-tick slippage,
and the plain statistical relation (correlation and OLS slope of last-half-hour return on the predictor) before costs.

## 6. Pass criteria (all required, decided now)

1. Net profit factor ≥ 1.20 at 1-tick slippage, 1 contract.
2. t-statistic of mean net trade P&L ≥ 2.5 (raised from 2.0 because two hypotheses are tested).
3. Net positive in at least 4 of the 6 full calendar years 2019*–2024 (*2019 partial) **and** net positive over June 2020 → June 2025 (post-publication period).
4. Still net positive at 2-tick slippage.

If neither hypothesis passes: the result is documented as negative, the holdout is left untouched, and no rule tweaks are tested on this data.
If one passes: run it once on the holdout, then IBKR paper trading for ≥ 60 sessions before anything else.
