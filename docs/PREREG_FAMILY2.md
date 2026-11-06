# Pre-registration: Strategy Family 2 on MNQ (written 2026-11-06, before any test)

Frozen before the first run; SHA-256 recorded in `docs/PREREG_HASH.txt`. Rule changes after seeing results
are not allowed on this data; any variation is a new hypothesis for new data.

## Why only three, and why the bar is higher

Three strategies have already been tested and rejected on this data (ORB, H1, H2). Every additional idea tested on
the same six years raises the chance that one passes by luck. So this family is limited to three ideas with a reason
that does not come from looking at this data, and the significance bar rises from t ≥ 2.5 to **t ≥ 3.0**
(Harvey, Liu & Zhu, *Review of Financial Studies* 2016, argue new trading factors should clear t ≈ 3).
The other categories requested (support/resistance, market-structure shifts, volume confirmation, generic momentum
breakouts) are **not** tested now; they overlap these three or ORB and would only add more chances of a false pass.

## Hypotheses

### H3 — Overnight drift (academic; also a methodology check)
- Source: Boyarchenko, Larsen & Whelan, "The Overnight Drift", *Review of Financial Studies* 36(9), 2023: U.S. index
  futures (S&P, Nasdaq-100, Dow E-minis) earned large positive returns 2:00–3:00 a.m. ET (European open), 1998–2020.
- Known before testing: the same authors (NY Fed *Liberty Street Economics*, July 2026) report the effect averaged
  close to zero from 2021 to 2025. **Expected result: positive before 2021, about zero after, fails after costs.**
  If our pipeline reproduces that pattern, it is evidence the pipeline measures real effects correctly.
- Rule: every weekday morning, buy 1 MNQ at the open of the 02:00 ET bar, sell at the open of the 03:00 ET bar.
- Protective stop: entry − max(10, 1.5 × median |02:00→03:00 move| over the previous 20 sessions) points.
- Skip if either bar is missing or fewer than 10 prior sessions exist.

### H4 — Liquidity sweep reversal at the prior day's high/low (popular retail idea)
- Rationale: widely taught claim that stops cluster beyond obvious levels, and a quick run through them followed by
  a reversal ("sweep") marks exhaustion. No peer-reviewed support found; this tests the popular claim directly.
- Levels: previous regular session (9:30–16:00 ET) high = PDH, low = PDL.
- Window: signals only from 9:45 to 15:00 ET.
- Short: a bar's high exceeds PDH by ≥ 2 points (the sweep). If a bar within that bar and the next 4 bars closes back
  below PDH, signal at that close; enter at the next bar's open.
  Stop = highest high since the sweep began + 2 points (at least 8 points from the signal close). Target = 2R.
- Long: mirror image at PDL.
- At most one sweep trade per side per day; only the first sweep per side counts.

### H5 — VWAP pullback in a trend (popular retail idea)
- Rationale: commonly taught trend-continuation entry — in an established intraday trend, buy the pullback to VWAP.
- Window: signals only from 10:00 to 14:00 ET.
- Trend: the bot's existing regime rules (EMA 20/50 alignment, slow-EMA slope, price vs VWAP, volatility filter) —
  unchanged from `settings.yaml`.
- Long: regime bullish; the bar's low touches or crosses VWAP, and it closes above VWAP and above its open.
  Stop = min(bar low, VWAP) − 0.5 × ATR (at least 8 points from the signal close). Target = 2R.
- Short: mirror image in a bearish regime.
- At most one trade per side per day.

## Common rules (all three)
- Data: Databento `MNQ.v.0` 1-minute, 2019-05-06 → 2025-06-30. Holdout (2025-07 →) not downloaded or viewed.
- Fills: market entries at the next bar's open + 1 tick; stops at the stop price − 1 tick (or the open if gapped through);
  targets only if price trades 1 tick through; stop assumed first when both are touched in one bar.
- Costs: $0.62 per contract per side (IBKR MNQ, Nov 2026).
- Size: 1 contract; account-size limits loosened so sizing never filters a signal. H4/H5 keep the bot's
  2-trades-per-day, 2-losses-in-a-row and 15:55 flatten rules. H3 has one trade per day by design.
- No parameters are tuned. Each hypothesis is one test.

## Pass criteria (all required)
1. Net profit factor ≥ 1.20 at 1-tick slippage.
2. t-statistic of mean net trade ≥ **3.0**.
3. Net positive in ≥ 4 of the 6 calendar years 2019–2024, **and** net positive from 2021-01-01 on.
4. Still net positive at 2-tick slippage.
5. At least 200 trades.

If one passes: run it once on the holdout (2025-07 → 2026-10), then paper trading only. If none passes: document it,
leave the holdout untouched, and run the paper system with no strategy enabled (or the ORB labeled as a plumbing test).
