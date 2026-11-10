# Pre-registration: Strategy Family 3 on MNQ (written 2026-11-09, before any test)

Frozen before the first run; SHA-256 recorded in `docs/PREREG_HASH.txt`. Rule changes after seeing results
are not allowed on this data; any variation is a new hypothesis for new data.

## Why these three, and the bar

Six ideas have already been rejected on this data (ORB, H1–H5). With nine tests in total, roughly one could
clear an ordinary significance bar by luck, so the bar stays at **t ≥ 3.0** (Harvey, Liu & Zhu, *RFS* 2016).
All three ideas come from published research, not from looking at this data. None of their results on MNQ
has been seen before this file was frozen.

## Hypotheses

### H6 — Turn of the month (calendar effect)
- Sources: Lakonishok & Smidt (1988); Xu & McConnell, "Equity Returns at the Turn of the Month" (1926–2005:
  0.15%/day on days −1…+3 vs 0.01% otherwise, t = 7.8); Carchano & Tornero, "Calendar Anomalies in Stock Index
  Futures" (the only significant and persistent calendar effect in S&P 500 futures).
- Trading days = weekdays with a regular session (≥ 300 one-minute bars between 09:30 and 16:00 ET).
  Day −1 = last trading day of a month; day +3 = third trading day of the next month.
- Rule (the paper's −1…+3 window): buy 1 MNQ at the close of the 15:59 ET bar on trading day −2; sell at the
  close of the 15:59 ET bar on day +3. Holds overnight and over weekends (outside the intraday bot's 15:55 rule).
- Disaster stop: 5% below entry, checked on every 1-minute bar while held (all sessions).

### H7 — Overnight-gap reversal (intraday)
- Sources: CXO Advisory, "Overnight/Intraday Return Reversal Trading"; "NASDAQ-100 Index Futures: Intraday
  Momentum or Reversal?", *Journal of Investment Management* (overnight returns relate mostly to intraday reversals).
- Gap = open of the 09:30 ET bar − close of the previous session's 15:59 ET bar (points).
  z = gap ÷ standard deviation of the previous 20 sessions' gaps (need ≥ 10 prior sessions).
- Signal when |z| ≥ 1.0 and |gap| ≥ 10 points: trade against the gap (gap up → short, gap down → long),
  entering at the open of the 09:31 ET bar.
- Target = previous session's 15:59 close (gap fill). Stop = entry ∓ max(10, 0.5 × |gap|) points, on the side
  away from the target. Time exit at 15:55 ET. One trade per day at most.

### H8 — Pre-FOMC announcement drift (replication check)
- Source: Lucca & Moench, *Journal of Finance* 2015 (large S&P 500 gains in the 24 hours before scheduled FOMC
  statements). Kurov, Wolfe & Gilbert report it "essentially disappeared after 2015" (≈ 0.09%/event in 2016–2019,
  not different from ordinary days). **Expected result: fail.**
- Events: the 48 scheduled FOMC statements (14:00 ET, second meeting day) from 2019-06-19 to 2025-06-18, taken
  from the Federal Reserve's calendars (federalreserve.gov fomccalendars and fomchistorical2019/2020 pages, read
  2026-11-09). Unscheduled 2020 actions and notation votes are excluded.
- Rule: buy 1 MNQ at the open of the 14:00 ET bar on the trading day before the announcement; sell at the close
  of the 13:55 ET bar on announcement day (before the 14:00 release).
- Disaster stop: 3% below entry, checked on every 1-minute bar while held.

## Common rules
- Data: Databento `MNQ.v.0` 1-minute, 2019-05-06 → 2025-06-30. Holdout (2025-07 →) not used.
- Fills: entries +1 tick against us, exits −1 tick (market orders); stops at the stop price −1 tick, or at the
  bar's open if it gapped through; H7 targets fill only if price trades 1 tick through; stop assumed first when
  stop and target are touched in the same bar.
- Costs: $0.62 per contract per side. Size: 1 contract, $2/point.
- No parameters are tuned. Each hypothesis is one test.

## Pass criteria
H7 (intraday, same as Family 2 — all required):
1. Net profit factor ≥ 1.20 at 1-tick slippage. 2. t-statistic of mean net trade ≥ 3.0.
3. Net positive in ≥ 4 of the 6 calendar years 2019–2024, and net positive from 2021-01-01 on.
4. Still net positive at 2-tick slippage. 5. At least 200 trades.

H6 and H8 (multi-session holds; about 74 and 48 trades, so the 200-trade rule cannot apply) — all required:
1. Net profit factor ≥ 1.20 at 1-tick slippage. 2. t-statistic of mean net trade ≥ 3.0.
3. Net positive in ≥ 4 of the 6 calendar years 2019–2024, and net positive from 2021-01-01 on.
4. Still net positive at 2-tick slippage.
5. **Beats simply being long:** mean net P&L per trade is above the 95th percentile of 2,000 random draws of the
   same number of long holds with the same holding length (in sessions for H6; 14:00→13:55 next day for H8),
   started on non-event trading days. Without this, any long-only rule profits from the market's rise.
   NQ rose a lot in 2019–2025, so being long alone is expected to look profitable.

If one passes: run it once on the holdout (2025-07 → 2026-10), then paper trading only. If none passes: document
it and leave the holdout untouched.
