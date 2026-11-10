# Pre-registration: Strategy Family 4 on MNQ (written 2026-11-09, before any test)

Frozen before the first run; SHA-256 recorded in `docs/PREREG_HASH.txt`. Rule changes after seeing results
are not allowed on this data; any variation is a new hypothesis for new data.

## Context and bar
Nine ideas have been tested on this data (8 rejected, H8 marginal). This family adds three more, for 12 in total,
so the significance bar rises to **t ≥ 3.5**. If none passes, the strategy search on this data is closed.
All three come from published research or from the intraday-momentum literature already cited, not from
looking at this data. None of their results on MNQ has been seen before this file was frozen.

## Hypotheses

### H9 — Macro announcement-day premium (CPI and jobs report)
- Source: Savor & Wilson, "How Much Do Investors Care About Macroeconomic Risk? Evidence from Scheduled
  Economic Announcements", *Journal of Financial and Quantitative Analysis* 48(2), 2013 (equity returns are
  much higher on days with scheduled CPI, employment and FOMC announcements).
- Events: BLS CPI and Employment Situation release days (08:30 ET), 2019-05-06 → 2025-06-30, from the BLS
  release archives (bls.gov/bls/news-release/cpi.htm and empsit.htm, read 2026-11-09), listed in
  `nq_bot/family4.py`. FOMC days are excluded (already tested as H8).
- Rule: buy 1 MNQ at the close of the 15:59 ET bar on the trading day before the release; sell at the close of the
  15:59 ET bar on release day. Disaster stop 3% below entry. Skip if the release day is not a trading day.

### H10 — Pre-holiday effect
- Sources: Ariel, "High Stock Returns before Holidays", *Journal of Finance* 45(5), 1990; Lakonishok & Smidt,
  *Review of Financial Studies* 1988.
- Trading day = weekday with ≥ 300 one-minute bars between 09:30 and 16:00 ET (same as Family 3).
  Pre-holiday day = a trading day whose next weekday is not a trading day (exchange holidays and early-close
  days). Defined from the data's own session calendar so no list can be cherry-picked.
- Rule: buy 1 MNQ at the 15:59 ET close on the trading day before the pre-holiday day; sell at the 15:59 ET close
  on the pre-holiday day. Disaster stop 3%.

### H11 — Opening-hour trend after a high-range day
- Rationale: intraday momentum is reported to be stronger after volatile days (Gao, Han, Li & Zhou, *Journal of
  Financial Economics* 2018, condition on volatility). H1 traded the first half hour every day and failed;
  this tests only the high-volatility condition, with a different window.
- Condition: the previous session's regular-hours range (09:30–15:59 high − low) is > 1.5 × the median range of
  the 20 sessions before it (need ≥ 10).
- Signal: opening-hour return = close of the 10:29 bar − open of the 09:30 bar. If > 0, go long; if < 0, short.
  Enter at the open of the 10:30 ET bar.
- Stop: for a long, the opening-hour low − 1 point; for a short, the opening-hour high + 1 point; at least
  10 points from entry. No target. Time exit at the 15:55 ET bar open. One trade per day.

## Common rules (same as Family 3)
- Data: Databento `MNQ.v.0` 1-minute, 2019-05-06 → 2025-06-30.
- Fills: market entries/exits 1 tick against us; stops at the stop price −1 tick or the bar open if gapped through;
  stop checked from the bar after entry for H9/H10, from the entry bar for H11.
- Costs: $0.62 per side. Size: 1 contract.

## Pass criteria (all required)
1. Net profit factor ≥ 1.20 at 1-tick slippage.
2. t-statistic of mean net trade ≥ **3.5**.
3. Net positive in ≥ 4 of the 6 calendar years 2019–2024, and net positive from 2021-01-01 on.
4. Still net positive at 2-tick slippage.
5. H9 and H10 (long-only holds): mean net P&L per trade above the 95th percentile of 2,000 random draws of the
   same number of 1-session close-to-close long holds started on non-event trading days.
   H11: at least 150 trades.

If one passes: run it once on 2025-07-01 → 2026-10-31 (fix that protocol in writing before running), then paper
only. If none passes: document it and close the strategy search on this data.
