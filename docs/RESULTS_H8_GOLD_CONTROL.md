# Result: H8 negative control on Micro Gold futures (MGC) — run once, 2026-11-10

Pre-registration: `PREREG_H8_GOLD_CONTROL.md` (hash in `PREREG_HASH.txt`, frozen and pushed to GitHub as commit
`fc28828` **before** any gold data was downloaded). Data: Databento `MGC.v.0` 1-minute, 2019-05-06 → 2026-10-31
(2,556,633 bars; a few days flagged degraded, e.g. 2020-02-27/28, 2020-05-05). 59 scheduled FOMC statements,
**4 skipped** for missing 14:00 or 13:55 bars, leaving 55 events.

**Reading is inverted.** Gold carries no equity risk premium, so clearing the four checks here would have counted
*against* H8. See the pre-registration for the full decision table, written before the data existed.

## Result

| | MGC gold (this control) | MNQ training | MES | M2K |
|---|---|---|---|---|
| Events | 55 (4 skipped) | 48 | 59 | 59 |
| **t** | **0.59** | 3.02 | 3.56 | 2.45 |
| Net | +$1,647.61 | +$7,114.98 | +$5,140.59 | +$2,324.75 |
| Mean / event | +$29.96 | +$148.23 | +$87.13 | +$39.40 |
| Median / event | +$6.76 | — | +$40.01 | +$37.26 |
| Profit factor | 1.41 | 3.34 | 3.55 | 2.29 |
| Wins | 30 of 55 (54.5%) | 32 of 48 | 37 of 59 | 34 of 59 |
| Stops hit | 1 | 0 | 0 | 2 |

Dollar figures are per 1 contract of each market and are **not comparable across markets**. The t-statistics are
unit-free and are the row to read.

| Pre-registered check | Result | |
|---|---|---|
| Net > 0 and PF ≥ 1.20 | +$1,647.61, PF 1.41 | **cleared** |
| t ≥ 2.0 | 0.59 | not met |
| Beats random 24-h long holds (95th pct) | $29.96 vs $90.75 (random mean $12.34) | not met |
| Both halves positive | 2019–2022 −$0.48; 2023–2026 +$1,648.09 | not met |

**Verdict as pre-registered: INCONCLUSIVE — positive but short of the bar. H8 status unchanged, caveat recorded.**
One of four checks cleared, so this is neither the "control found nothing" outcome nor the "drift present in gold"
outcome. It is the middle branch written down in advance.

Net by year: 2019 +$162, 2020 +$563, 2021 −$432, 2022 −$294, 2023 +$409, 2024 +$747, 2025 −$240, 2026 +$731
(2019 and 2026 partial).

## Sensitivity (computed after the verdict; does not change it)
- **The result rests on a single event.** Dropping the best trade takes t from 0.59 to **−0.13**; dropping the
  best two gives −0.41, the best three −0.69. The median event is +$6.76, barely above the cost of trading.
- For gold to have reached t = 2.0 it would have needed a mean of about **$101 per event**, 3.4× what it showed.
- The one stop-out (2026-03-17, −$1,504.43) is close to the size of the whole result, a reminder that a 3% stop
  on gold is a large dollar amount.
- The 10 events after June 2025 made +$888.41.

## What this does and doesn't show
- **Does:** gold shows no pre-FOMC drift that clears the bar the equity markets cleared, and what it does show
  disappears when one event is removed. The t-statistic is 0.59 against 3.02, 3.56 and 2.45 in the three equity
  indexes. That is the pattern the equity risk-premium explanation predicts.
- **Doesn't:** this is not proof that gold has no drift. With 55 events and gold's volatility, the test could
  only have detected a large effect; a small one would look exactly like this. A control that fails to find
  something is weaker evidence than one that finds nothing where a lot was expected.
- **Also doesn't:** rescue H8. By construction no outcome here could raise its status, and none did. H8 remains
  "replicated in two markets", resting on 59 shared Fed dates.
- **Caveat recorded in advance, and it still applies:** gold responds to real interest rates, so it is an
  imperfect control. A completely unrelated market (an agricultural future) would be cleaner.
- **Status:** unchanged. The deciding evidence is still forward — FOMC events no test has seen
  (`py cli.py fomc-paper`, IB paper account, first on 2026-12-08/09). No real money on this basis.

## Research spending closed
This was the last paid replication. Four markets have now been tested on the same 59 dates, and a fifth would
add nothing that forward events will not answer better. Databento credits remaining: about $87.
