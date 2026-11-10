# Pre-registration: H8 (pre-FOMC drift) replication on S&P 500 micro futures (MES)
Written 2026-11-09, before any ES/MES data was downloaded. SHA-256 in `docs/PREREG_HASH.txt`.

## Why
H8 passed barely on MNQ training data (t 3.02) and weakly on the MNQ holdout (11 trades, t 0.34).
The original evidence (Lucca & Moench, *Journal of Finance* 2015) is in the **S&P 500**, so if the effect is real
it should also appear in S&P futures. This is a **replication of one pre-specified rule**, not a new search:
no other rule or market is tested.

## Caveat stated in advance
ES and NQ are highly correlated (daily correlation around 0.9). A pass is supporting evidence, **not**
independent proof. A fail is strong evidence against H8.

## Data
- Databento `GLBX.MDP3`, schema `ohlcv-1m`, symbol `MES.v.0` (volume-rolled continuous), 2019-05-06 → 2026-10-31.
  Downloaded once. The MES micro contract started trading 2019-05-06, which is why the window starts there.
- Events: the 59 scheduled FOMC statement days in that window — the 48 used in training plus the 11 holdout events
  (lists in `nq_bot/family3.py`, from federalreserve.gov).

## Rule (identical to H8)
Buy 1 MES at the open of the 14:00 ET bar on the trading day before the statement; sell at the close of the
13:55 ET bar on statement day; 3% disaster stop checked on every bar. Same fill model (1 tick against us on market
orders, stop −1 tick or the gap-through open). MES: $5 per point, 0.25 tick, $0.62 per side assumed.

## Judged on all 59 events (decided now)
**Replication passes** only if all hold:
1. Net P&L > 0 and profit factor ≥ 1.20.
2. t-statistic of mean net trade ≥ 2.0 (one pre-specified test, so the multiple-testing bar does not apply;
   still requires real evidence).
3. Mean net per trade above the 95th percentile of 2,000 random draws of 59 long holds 14:00 → 13:55 next day
   started on non-FOMC days (same benchmark as H8).
4. Net positive in both halves: 2019-05 → 2022-12 and 2023-01 → 2026-10.

Otherwise: **replication fails**, and H8 is treated as a likely false positive. Forward paper tracking would then
be kept only as a record, with no further effort spent on it.
Run once. No rule changes afterwards.
