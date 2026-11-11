# Audit, November 2026: contract-roll contamination inflated H8

**This is the most consequential finding in the project. H8 did not clear its pre-registered bar on clean
data, and its two "replications" fail outright once the defect is removed.**

## The defect

Research runs on Databento continuous symbols (`MNQ.v.0`, `MES.v.0`, `M2K.v.0`, `MGC.v.0`). These splice
quarterly contracts **without back-adjustment**, so the series jumps by the calendar spread at every roll.
For equity index futures the jump is **positive** (positive carry) and scales with interest rates.

A trader holding **one** contract from Tuesday to Wednesday experiences no jump. The spliced series does. So
any strategy holding **across** a roll books that gap as profit it would never have received. Every
affected strategy here is long-only, so the contamination is one-directional: it inflates.

`data.fetch_databento`'s docstring asserted this could not happen:

> *"Continuous series are unadjusted: expect price jumps at rolls; the strategy only compares prices within
> one session, so this does not leak across rolls."*

That was **true when written** — the bot was intraday-only (ORB, H1, H2), and those strategies do close the
same session. It became **false** when Families 3 and 4 added overnight and multi-day holds, and nobody
revisited it. The claim then sat in the code as a standing reassurance that the risk had been considered.

## Why H8 specifically, and why this is systematic rather than bad luck

Quarterly futures rolls land in the **third week of March, June, September and December**. FOMC meetings in
those months land in the **same third week**. The two calendars coincide by construction, so the pre-FOMC
window is far more likely to span a roll than an arbitrary window is. The placebo test's sham windows,
shifted 7/14/21 days, mostly miss the rolls — which means the placebo was partly measuring
roll contamination rather than a Fed effect.

Measured directly: **11 of 59** real FOMC holds on MES span a roll, and **12 of 59** on M2K, against **0 to 5**
for any sham series.

## Roll identification

Twelve discontinuities, exactly one per quarter from 2022-09 to 2025-06, were identified on MNQ. All share the
signature of a roll and none that of news:

| | Value |
|---|---|
| Time of day | 19:00 or 20:00 ET, every one — not a news hour |
| Sign | **positive, every one** |
| Size | +0.64% to +1.38%, growing with interest rates |
| Volume | 134 to 1,271, at or below the file's median of 253 |
| Next 30 minutes | −0.12% to +0.23%, i.e. no follow-through |

Gold's rolls are visible too and are tiny (median **+0.11%**), consistent with gold's near-zero carry, which
is why the gold control is unaffected.

### The detector is sensitive to its input window, which is why this correction is not the final answer

Running the same detector over MNQ **training only** finds 4 contaminated holds and gives a roll-adjusted
t of **2.63**. Running it over **training plus holdout** finds 5 (it additionally flags 2022-06-14 at
+0.29%, which is small enough to be a false positive) and gives **2.47**. Both are below the 3.0 bar, so the
*verdict* is robust — but the *number* is not, and neither figure should be quoted as the corrected result.

This is the limit of adjusting a spliced series, and the reason the fix is not finished. Price adjustment is
a **proxy**. The exact model is to price each event on the single contract a trader actually held: they buy
the front contract at 14:00 and sell *that* contract at 13:55 the next day, never rolling, so there is no
roll cost at all — only a data artifact. `scripts/roll_map.py` (free metadata) plus
`scripts/fetch_contract_windows.py` (a few cents) plus `run_h8_contract_level.py` do that, and their output
supersedes every adjusted figure in this document.

The detector is a heuristic and is documented as such in `nq_bot/rolls.py`: the largest positive
overnight-session one-minute move per expiry month, screened on volume. Its known weakness is that when
carry is near zero (2020-2021) the true gap is smaller than ordinary overnight noise, so low-rate periods
produce false positives of negligible dollar size. **It understates nothing that matters and the sign of the
bias is certain.** The exact fix is the `symbol` column, now retained on download.

## Impact, every hypothesis that holds overnight

| Hypothesis | Holds spanning a roll | t as published | t roll-adjusted | Bar | Verdict change |
|---|---|---|---|---|---|
| H6 turn of the month | 1 of 73 | 0.45 | 0.42 | 3.0 | none — failed before, fails now |
| H7 overnight-gap reversal | 0 of 439 | −0.74 | −0.74 | 3.0 | none |
| **H8 pre-FOMC, MNQ training** | **4 of 48** | **3.02** | **2.63** | **3.0** | **PASS → FAIL** |
| **H8 replication, MES** | **11 of 59** | **3.56** | **1.66** | **2.0** | **PASS → FAIL** |
| **H8 replication, M2K** | **12 of 59** | **2.45** | **1.44** | **2.0** | **PASS → FAIL** |
| H8 gold negative control | 0 of 55 | 0.59 | 0.59 | — | none — still inconclusive |
| H9 macro announcement days | 1 of 141 | 0.23 | 0.16 | 3.5 | none |
| H10 pre-holiday | 0 of 59 | 1.70 | 1.70 | 3.5 | none |
| H11 opening-hour trend | 0 of 253 | 0.36 | 0.36 | 3.5 | none |

**The eleven failures stand. The one pass does not.** The artifact was worth about **$1,158 of H8's $7,115**
on MNQ (16%), **$3,101 of $5,141** on MES (60%), and **$1,012 of $2,325** on M2K (44%).

## Effect on the placebo test

The placebo's **qualitative** conclusion survives. On roll-adjusted prices the real FOMC window is still the
highest of all seven series in all three markets:

| | real | best sham |
|---|---|---|
| MNQ | 2.63 | 0.91 (−7d) |
| MES | 1.66 | 0.72 (−7d) |
| M2K | 1.44 | 0.26 (−14d) |

So the pre-FOMC window does appear to be special, and is not generic calendar drift. But the margin is much
smaller than reported, the real window's own significance is gone, and part of what the original placebo
measured was the roll. The earlier claim that it was "the strongest thing H8 has" is withdrawn.

## H8's revised status

**Downgraded from "replicated candidate" to "unconfirmed, and below its original bar."** The honest record:

- MNQ training, roll-adjusted: **t 2.63 against a pre-registered bar of 3.0 — a fail.**
- MNQ holdout, roll-adjusted: t 0.34 → **0.25** on 11 events — already a fail. **Correction, same
  day:** this document first stated the holdout contained no roll. It contains one, on the
  2026-06-16 event, at +0.18%. The gap is small and the verdict is unchanged, but the original claim
  was wrong and is retracted here rather than silently edited.
- MES replication, roll-adjusted: t 1.66 against 2.0 — a fail.
- M2K replication, roll-adjusted: t 1.44 against 2.0 — a fail.
- Gold control: unaffected, still inconclusive.
- Placebo: the window is still the best of seven, but no longer significant on its own.

H8 is now **a weak positive signal that has never cleared a pre-registered bar on clean data.** It is not a
candidate strategy. It is a reason to keep collecting forward events, nothing more.

## The forward test is unaffected, and is now the only clean evidence

`fomc-paper` trades the **actual front contract** on an IB paper account, with real IB fills. There is no
splicing and therefore no roll artifact. One guard is still needed and is recorded as the next engineering
task: the runner should refuse, or explicitly log, a hold whose window spans a contract roll, since rolling
mid-hold would introduce the real-world version of this problem (paying the spread).

The December 8-9, 2026 window does not span a roll: the December contract's roll falls after it.

## Fixes made

1. `nq_bot/rolls.py` — `detect` (heuristic), `from_symbols` (exact), `spans`, `adjust_exit`.
2. `data.fetch_databento` now **keeps the `symbol` column**, so roll dates on any future download are exact
   rather than inferred, and `_normalize` carries it through as a string.
3. The false docstring is replaced with a warning that states what actually happens and points here.
4. `tests/test_tooling.py::test_roll_detection_finds_an_injected_gap` — a regression test on synthetic bars.

## What this says about the research process

The protocol worked exactly as designed on everything it covered: pre-registration, frozen hashes, holdouts,
rising bars, a negative control, a placebo. **None of that catches a defect in the price series itself.**
Every hypothesis was tested honestly against contaminated data, and the contamination happened to favour the
one hypothesis whose event calendar coincides with the roll calendar.

The transferable lesson is that **data-layer assumptions need the same pre-registered scepticism as
hypotheses do**, and a comment asserting that a risk does not apply is not evidence that it does not. The
project's own validator (`scripts/validate_data.py`) checked ordering, duplicates, OHLC consistency, the tick
grid, gaps and large moves — and reported MNQ as clean, because a roll jump is not malformed data. It is
correct data about the wrong thing.
