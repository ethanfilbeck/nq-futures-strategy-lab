# Result: H8 priced on the actual contracts held — U1 RESOLVED, 2026-11-11

**This supersedes every roll-adjusted H8 figure in this repository.** No continuous series and no price
adjustment is used anywhere in it.

## Method

Each event is priced on the single contract a trader would actually have held: buy the front contract at
14:00 ET the day before the statement, sell **that same contract** at 13:55 ET on statement day. No roll
occurs inside a 24-hour hold, so there is no roll cost to model — the earlier error was only that a spliced
series misrepresented the price path.

- Exact contract periods from Databento symbology (`scripts/roll_map.py`, unbilled metadata): 31 periods,
  MNQM9 → MNQZ6, contiguous, unbroken H/M/U/Z cycle, no duplicates, **59 of 59 events covered**.
- Per-contract 1-minute bars over each hold window (`scripts/fetch_contract_windows.py`): 59 windows,
  **250,846 bars, $0.9158** against a $3.00 ceiling.
- `run_h8_contract_level.py` **asserts per event** that the entry bar and the exit bar carry the same
  contract symbol. That invariant, not a comment, is what guarantees no splice entered the result.
- **59 of 59 events priced, 0 skipped, 31 contracts used.**

## Result

| Split | n | Net | Mean/event | t | Pre-registered bar | Verdict |
|---|---|---|---|---|---|---|
| **Training (the 48 H8 was discovered on)** | 48 | +$5,527 | +$115.16 | **2.50** | **3.0** | **FAILS** |
| **Holdout (run once, 11)** | 11 | **−$253** | **−$22.97** | **−0.27** | — | **negative** |
| All 59 events | 59 | +$5,275 | +$89.40 | 2.18 | — | — |

All 59: profit factor 2.19, win rate 62.7%, max drawdown −$965.96, **0 stops hit**. Costs charged $132.16
($2.24/event). Gross of all costs t 2.24; at double slippage t 2.16 — execution remains irrelevant to the
verdict. Fragility: dropping the best 1 / 2 / 3 events gives t 1.92 / 1.65 / 1.39.

## Every estimate of H8, in one place

| Basis | Training (48) | Holdout (11) | All 59 |
|---|---|---|---|
| As published, spliced continuous series | 3.02 | 0.34 | 2.89 |
| Heuristic roll-adjusted | 2.63 | 0.25 | 2.36 |
| Exact-date roll-adjusted | 2.46 | — | — |
| **Actual contracts held (definitive)** | **2.50** | **−0.27** | **2.18** |

The adjustments were directionally right: 2.46–2.63 against a true 2.50. The audit's conclusion was correct
and its arithmetic was close. But only this row rests on the prices a trader would have paid.

## What this settles

1. **H8 never cleared its pre-registered bar on correct data.** Its t ≥ 3.0 requirement was met only because
   the price series was spliced. On the contracts actually held it is **2.50**.
2. **2.50 is also below the 5% familywise threshold of 2.63** for the 12 hypotheses tested
   (`QUANTITATIVE_RESEARCH_LITERATURE_REVIEW.md` §4a). H8 is inside the range the best of 12 noise trials
   would produce.
3. **The holdout is now negative.** It was +$368 (t 0.34) on the spliced series and is **−$253 (t −0.27)** on
   the real contracts. The only clean out-of-sample test H8 ever had does not merely fail to confirm it — it
   loses money.
4. **Execution assumptions are irrelevant**, as the cost audit predicted. Zero cost gives 2.24, double
   slippage 2.16.

## Status

**H8 is not a candidate strategy.** It is a hypothesis that failed its pre-registered bar once its data was
corrected, and whose out-of-sample test is negative. It joins the other eleven.

That makes the project's record **0 of 12 hypotheses passing a pre-registered bar on clean data.**

The forward paper test remains scheduled for Dec 8–9 and costs nothing to let run, but its purpose is now
clearly falsification rather than validation: on this effect size, 80% power would need decades. The forward
pre-registration (`DRAFT_H8_FORWARD_awaiting_signoff.md`) should be read again before Dec 8 with this result
in hand, and the honest option of simply stopping is now on the table.

## Caveats recorded

- Databento flagged **reduced data quality** on 2024-09-18, 2025-09-17 and 2026-03-15/16. The first two are
  FOMC statement days, so two of the 59 events rest on degraded bars. Not enough to change a verdict this
  far from its bar, but recorded rather than omitted.
- The training/holdout split is reproduced exactly as pre-registered: `FOMC_DAYS` (48) and
  `HOLDOUT_FOMC_DAYS` (11), unchanged.
- Per-event prices stay out of the repository (licensed Databento data); only aggregates are published.
