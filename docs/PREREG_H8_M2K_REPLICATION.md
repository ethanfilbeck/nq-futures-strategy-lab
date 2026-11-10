# Pre-registration: H8 (pre-FOMC drift) replication on Russell 2000 micro futures (M2K)
Written 2026-11-10, before any Russell 2000 data was downloaded. SHA-256 in `docs/PREREG_HASH.txt`.

## Why
H8 passed on MNQ training data (t 3.02), was weak but positive on the MNQ holdout (t 0.34), and replicated on
S&P 500 micro futures (MES, t 3.56). The MES test is weak independent evidence because the S&P 500 and the
Nasdaq-100 move together (daily correlation around 0.9). The Russell 2000 (small caps) moves less in step with the
Nasdaq-100 (noticeably lower daily correlation), and small caps are more sensitive to interest rates, so it is the most informative
second market available on CME micro futures. This is a **replication of one pre-specified rule on one market**,
not a search: Dow futures (MYM) are **not** tested, and no other rule or market is tried.

## Caveats stated in advance
- The 59 event dates are the same as in the MES test (48 training + 11 holdout), so this is new evidence about
  *markets*, not about *dates*. Forward paper trading remains the only test on unseen dates.
- Small caps are more volatile than large caps, so the 3% disaster stop is more likely to be hit. The rule is
  kept identical anyway: changing it after seeing two markets would be tuning.

## Data
- Databento `GLBX.MDP3`, schema `ohlcv-1m`, symbol `M2K.v.0` (volume-rolled continuous), 2019-05-06 → 2026-10-31.
  Downloaded once. M2K started trading 2019-05-06, the same day as MES.
- Events: the same 59 scheduled FOMC statement days as the MES test (`FOMC_DAYS + HOLDOUT_FOMC_DAYS` in
  `nq_bot/family3.py`).

## Rule (identical to H8)
Buy 1 M2K at the open of the 14:00 ET bar on the trading day before the statement; sell at the close of the
13:55 ET bar on statement day; 3% disaster stop checked on every bar. Same fill model (1 tick against us on market
orders, stop −1 tick or the gap-through open). M2K contract specs: $5 per index point, tick 0.10 ($0.50);
$0.62 per side assumed. The only code change from the MES run is the point value and tick size.

## Judged on all 59 events (decided now, same bar as MES)
**Replication passes** only if all hold:
1. Net P&L > 0 and profit factor ≥ 1.20.
2. t-statistic of mean net trade ≥ 2.0.
3. Mean net per trade above the 95th percentile of 2,000 random draws of 59 long holds 14:00 → 13:55 next day
   started on non-FOMC days (same benchmark and seed as MES).
4. Net positive in both halves: 2019-05 → 2022-12 and 2023-01 → 2026-10.

## How the result will be read (decided now)
- **Pass:** H8 holds in three index futures, including one that moves much less with the Nasdaq. Status becomes
  "replicated in two markets". Still paper only until forward events confirm it.
- **Fail:** H8 is at best a large-cap effect and possibly a false positive shared by two highly correlated
  markets. Status becomes "mixed evidence". Forward paper tracking continues as a record (it costs nothing), but
  no real-money use is considered on backtest evidence alone.

Either way the result is published in `docs/RESULTS_H8_M2K_REPLICATION.md`, the README and the results dashboard.
Run once. No rule changes afterwards.
