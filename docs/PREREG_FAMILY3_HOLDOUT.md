# Holdout protocol for H8 (pre-FOMC drift) — frozen 2026-11-09 before the holdout data is downloaded

H8 passed the Family 3 pre-registered checks on training data (see `RESULTS_FAMILY3.md`). This file fixes how the
single holdout run is judged, before any holdout data exists on disk.

- Data: Databento `MNQ.v.0` 1-minute, 2025-07-01 → 2026-10-31, downloaded once (`data/mnq_holdout.csv`).
- Rules: exactly the H8 rules in `PREREG_FAMILY3.md` (buy 1 MNQ at the 14:00 ET bar open on the trading day before
  each scheduled FOMC statement; sell at the 13:55 ET bar close on statement day; 3% disaster stop; same fills/costs).
- Events (scheduled statements, federalreserve.gov fomccalendars, read 2026-11-09): 2025-07-30, 2025-09-17,
  2025-10-29, 2025-12-10, 2026-01-28, 2026-03-18, 2026-04-29, 2026-06-17, 2026-07-29, 2026-09-16, 2026-10-28
  (11 events).
- With only 11 trades a significance test has almost no power, so the holdout can only falsify, not confirm:
  - **Holdout fail** if net P&L ≤ 0, or mean per trade ≤ the training random-long benchmark mean ($9.51).
  - **Holdout consistent** otherwise. "Consistent" does not mean proven: it only allows paper tracking of future
    FOMC events (about 8 per year), reported separately from backtests.
- Run once. No rule changes afterwards, whatever the result.
