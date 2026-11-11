# Result: H8 placebo tests - run once, 2026-11-11

> **SUPERSEDED IN PART, 2026-11-11.** A contract-roll defect inflated this result; see
> `AUDIT_2026_11_ROLLS.md`. Roll-adjusted figures: MNQ 2.89 -> **2.63**, MES 3.56 -> **1.66**, M2K 2.45 -> **1.44**. The real window is still the best of all seven series in each market, so the qualitative conclusion stands, but it is no longer significant on its own and part of what this test measured was the roll.


Pre-registration: `PREREG_H8_PLACEBO.md` (hash in `PREREG_HASH.txt`, frozen before any placebo statistic was
computed). Data already on disk: MNQ (`mnq_train.csv` + `mnq_holdout.csv`, all 59 events), MES, M2K. No new
data was bought for this. Rule unchanged and not re-fit.

## Test A - sham dates

Same frozen rule, run on dates offset -21/-14/-7/+7/+14/+21 calendar days from each real FOMC date, dropping
any sham date within 3 trading days of a real event.

| Series | MNQ t | MES t | M2K t |
|---|---|---|---|
| **real FOMC (59)** | **2.89** | **3.56** | **2.45** |
| sham -21 days | 0.91 | 0.32 | -0.24 |
| sham -14 days | -0.04 | 0.65 | 0.26 |
| sham -7 days | 1.11 | 1.23 | 0.37 |
| sham +7 days | -0.66 | -0.08 | -0.88 |
| sham +14 days | 1.32 | 0.35 | -0.14 |
| sham +21 days | -0.02 | 0.05 | -1.00 |

Mean per trade, real vs best sham: MNQ $126.83 vs $71.94; MES $87.13 vs $31.92; M2K $39.40 vs $6.04.

**Verdict: PLACEBO CLEAN in all three markets** - the real FOMC t-statistic is the highest of all seven series
in every market, and no sham series anywhere reaches t >= 2.0.

## Test B - Wednesday-matched null

Pool of consecutive trading-day pairs whose exit day is a Wednesday and which avoid every real event window;
10,000 bootstrap samples of 59, comparing the **t-statistic** (not the mean, as the older benchmark did).

| Market | Pool | Pool mean/trade | p(bootstrap t >= real t) |
|---|---|---|---|
| MNQ | 318 pairs | +$17.54 | **0.0074** |
| MES | 318 pairs | +$9.46 | **0.0010** |
| M2K | 317 pairs | -$4.23 | **0.0044** |

**Verdict: PASSES in all three** - a random Wednesday-matched 24-hour long hold reproduces H8's t-statistic
less than 1% of the time.

## What this does and doesn't settle

**Does:** it kills the most obvious benign explanation. The drift is not generic Tuesday-into-Wednesday
afternoon drift, not a day-of-week artifact, and not a mid-afternoon-to-mid-afternoon holding effect. Shift the
same window one, two or three weeks in either direction and it disappears - on all three markets independently
of each other's noise. That is the first H8 test that could plainly have failed and didn't.

**Doesn't:** it does not address the sample. All three markets still use the **same 59 dates**, and the sham
series use those same dates too, so this tests whether the *window* is special, not whether those particular
59 days were lucky. The only test of that remains the MNQ holdout, and it came in at **t = 0.34 on 11 events**.
Nothing here changes that.

Also recorded honestly:
- The 18 sham series are not 18 independent draws. The three markets share dates and move together (MES ~0.95
  with NQ, M2K ~0.85), so this is closer to six independent sham draws seen three times.
- The two mildest-but-positive shams are -7 days on MNQ (t 1.11) and MES (t 1.23). -7 calendar days is about
  5 trading days before the meeting, outside the 3-trading-day exclusion but possibly still inside a real
  pre-event run-up. If anything that pattern is weakly *consistent* with a genuine effect that decays with
  distance from the meeting, rather than evidence against one - but it is also what noise looks like, and it
  was not predicted in advance, so no weight is placed on it.
- MNQ's all-59 figure (t 2.89) is reported here for the first time; previously only the 48-event training
  split (3.02) and the 11-event holdout (0.34) existed separately.

**Status: H8 remains a "replicated candidate," unchanged.** The placebo removes a competing explanation; it
does not promote the hypothesis. The decisive evidence is still forward events no test has seen
(`py cli.py fomc-paper`, IB paper account, ~8 per year). Next one: Dec 8-9.
