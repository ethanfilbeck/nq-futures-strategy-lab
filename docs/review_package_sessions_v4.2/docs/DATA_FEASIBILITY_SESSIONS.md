# Data feasibility: overnight vs regular session, MNQ

> **CORRECTIONS, 2026-11-11 (same night).** Found while verifying counts for protocol v2. The text below is
> left as written so the errors stay visible.
> - **Holdout full-RTH sessions are 334, not 333.** The original count combined the two files and
>   de-duplicated by session date, which dropped the real 2025-07-01 session in favour of its overnight
>   fragment from the development file.
> - **Holdout: the §5 figure of 347 counted sessions with *any* bar, not "with RTH".** With RTH: **346**. The
>   extra date is 2026-04-03 (Good Friday, Globex only). Corrected 2026-11-12; see protocol v4 §5.2a.
> - **Development sessions with any RTH are 1,417, not 1,420.** The original count included 3 dates with Globex
>   trading but no RTH.
> - **Roll exclusions are 26 effective, not 27.** The 2024-06-19 switch coincides with the Juneteenth early
>   close, which is excluded by a separate rule first.
> - The frozen analysis samples, after all exclusion rules, are **1,308 development and 318 holdout**
>   (primary 1,230 and 297 after the FOMC-pair exclusion). See `DRAFT_PREREG_SESSIONS_awaiting_signoff.md`
>   §5.1 and Appendix A.

Written 2026-11-11. **Only bar counts, timestamps and volume were computed.** No price change, return,
volatility or other price-derived number was calculated, so the protocol can still be frozen blind.
Script: run in the session's scratch space against `data/mnq_train.csv` and `data/mnq_holdout.csv`; its
output totals are reproduced here. Nothing was purchased or downloaded.

## 1. Verdict

**The owned data supports the volatility, price-discovery and large-move questions. It supports the tail
question with modest power, and it cannot answer the mean-return question.** No new data is required.

| Research question | Feasible on owned data? | Why |
|---|---|---|
| Realized volatility by session | **Yes, well powered** | ~1,345 clean development sessions; variance differences are large relative to sampling error |
| Price discovery (weighted price contribution) | **Yes** | Needs only session endpoints and close-to-close returns |
| Large price movements | **Yes, moderate power** | Top-5% days ≈ 67 in development, ≈ 16 in the holdout |
| Tail risk after volatility scaling | **Moderate power in development; directional only in the holdout** | Hill estimator on 5% of ~1,345 ≈ 67 exceedances |
| Return distributions: means | **No: underpowered by design** | See §7. A null result here is uninformative and is pre-declared as such. |
| Stability across regimes | **Yes, for the volatility measures** | Four calendar regimes of 1–2.5 years each |

## 2. What is on disk

| File | Instrument | Coverage (UTC) | Bars | Contract identity |
|---|---|---|---|---|
| `data/mnq_train.csv` | MNQ.v.0 1-min OHLCV | 2019-05-06 00:00 → 2025-06-30 23:59 | 2,167,313 | **No `symbol` column** (downloaded before the fix) |
| `data/mnq_holdout.csv` | MNQ.v.0 1-min OHLCV | 2025-07-01 00:00 → 2026-10-30 20:59 | 474,794 | No `symbol` column |
| `runs/rollmap_MNQ.json` | Exact roll calendar from Databento symbology | 2019-05-06 → 2026-11-01 | 31 periods, **30 switches** | Exact |
| `data/mnq_contracts.csv` | 31 individual MNQ contracts | FOMC event windows only | 250,846 | Exact, but **too sparse for this study** |
| `data/mes_2019_2026.csv` | MES.v.0 | 2019-05-06 → 2026-10-30 | — | No symbol column; **no MES roll map yet** |

The two MNQ files are contiguous: the holdout begins at the minute after training ends.

## 3. Integrity checks

| Check | Development file | Holdout file |
|---|---|---|
| Duplicate timestamps | 0 | 0 |
| Strictly increasing | Yes | Yes |
| Zero or missing volume | 0 | 0 |
| Timezone | tz-aware UTC; converted with `America/New_York` (DST handled by the tz database) | same |
| Bar timestamp convention | Bar **start** (Databento); the 09:30 bar covers 09:30:00–09:30:59 | same |

OHLCV-1m has **no bar in a minute with no trade**, so a missing minute means "no trade", not "missing
data". The protocol therefore takes prices *at or before* a boundary rather than requiring an exact minute.

## 4. Coverage by session

CME session date = the date of the 09:30 open. The session starts at 18:00 ET the previous evening.

| Year | Sessions | Median RTH bars (of 390) | Median overnight bars (of 930) | Overnight 10th pct | Median overnight 1-min volume |
|---|---|---|---|---|---|
| 2019 (from May 6) | 171 | 390 | **922 (99.1%)** | **887** | **24** |
| 2020 | 259 | 390 | 930 | 930 | 157 |
| 2021 | 259 | 390 | 930 | 930 | 138 |
| 2022 | 258 | 390 | 930 | 930 | 262 |
| 2023 | 258 | 390 | 930 | 930 | 147 |
| 2024 | 259 | 390 | 930 | 930 | 187 |
| 2025 (Jan–Jun) | 128 | 390 | 930 | 930 | 302 |
| 2025 (Jul–Dec, holdout) | 131 | 390 | 930 | 930 | 242 |
| 2026 (holdout) | 216 | 390 | 930 | 930 | 559 |

- **2019 is thin overnight:** MNQ launched 2019-05-06. Minute coverage in the 23:00–01:00 ET hours was 93–95%,
  and the median overnight trade size was 24 contracts per minute. Thin trading biases realized variance
  through bid-ask bounce and stale prices. **The protocol drops 2019 from the primary analysis, on this
  liquidity evidence alone,** and keeps it as a sensitivity check.
- **The 16:00 hour** had ~71–73% minute coverage in 2019–2020 because of CME's former 16:15–16:30 ET
  maintenance halt; ~96–97% from 2022 (the residual is half-days). This affects only the hourly volatility
  profile, not session endpoints.

## 5. Gaps, short sessions, rolls

| Item | Development (2020-01-02 → 2025-06-30) | Holdout (2025-07-01 → 2026-10-30) |
|---|---|---|
| Sessions with any RTH trading | 1,420 | 347 |
| Full RTH sessions (390 bars) | **1,367** | **333** |
| Short RTH sessions | 50: scheduled half-days (210 or 225 bars) plus **four circuit-breaker days in March 2020** (376–378 bars: Mar 9, 12, 16, 18) | 12, all half-days |
| Gaps > 15 min (excluding the daily 17:00–18:00 halt) | 571 over the whole file: 165 in 2019, **285 in 2020** (overnight limit-down episodes, mainly Mar 15–18), 121 in 2021, **none from 2022** | 1: 646 min on 2025-11-28 (a scheduled half-day) |
| Contract switches in MNQ.v.0 | **22** | **5** |

**Rolls.** The continuous symbol switches contracts at **00:00 UTC (19:00 or 20:00 ET)**, without
back-adjustment (`AUDIT_2026_11_ROLLS.md`). **Every switch therefore lands inside an overnight window,**
which is exactly the window this study measures. Unhandled, each would add a +0.6% to +1.4% artifact to one
overnight return. That is the same defect that inflated H8, and here it would bias overnight means, variance
and tails all at once. The exact switch dates are in `runs/rollmap_MNQ.json`, so they are known without
guessing. The protocol excludes the 27 affected sessions outright.

**The March 2020 circuit-breaker days are kept.** Excluding them would delete the most extreme days in the
sample from a study of tails and large moves. Session prices are taken at or before each boundary, so
intra-session halts do not invalidate the endpoints.

**Overnight price limits.** CME capped overnight moves at **±5% until 2020-10-12**, then at ±7% plus a 3.5%
dynamic circuit breaker. Overnight returns in March 2020 are therefore **censored**: the true overnight move
was larger than the recorded one. Overnight tail measures are biased toward thinner tails during
2020-01-02 → 2020-10-09. The protocol states the direction of this bias in advance and runs a sensitivity
check without that window.

## 6. How "untouched" each period is

| Period | Previously examined for | Examined for session volatility, tails or price discovery? |
|---|---|---|
| Development 2020–2025-06 | ORB, H1–H11, PBO. **H3 (overnight 2–3 a.m. mean return) and H7 (overnight gap → RTH reversal) looked at overnight returns directly.** | **No** |
| Holdout 2025-07 → 2026-10 | **H8 only:** 11 FOMC windows (14:00 day before → 13:55 statement day), i.e. ~22 of 347 session-days partially seen. A contract-level re-pricing of the same windows. | **No** |

So the holdout is **unexamined for every quantity in this study but not pristine**: about 6% of its
sessions overlap windows whose prices were used for H8, and anyone living through 2025–26 knows the broad
market direction. The protocol runs a sensitivity check excluding the 22 H8 sessions.

The mean-return question is **contaminated in development** by H3 and H7, in addition to being underpowered.
That is a second, independent reason to keep it out of the primary claims.

## 7. Power: computed from assumptions, not from this data

Assumed for planning only (typical published magnitudes, **not** measured here): RTH daily σ ≈ 1.3%,
overnight σ ≈ 0.75%, so the difference has σ ≈ 1.5%. Development n ≈ 1,345 sessions, holdout n ≈ 328.

| Quantity | Standard error (development) | Detectable at α = 0.01 two-sided, 80% power | Published magnitude | Expected outcome |
|---|---|---|---|---|
| Mean(overnight − RTH), %/day | ≈ 0.041 | ≈ **0.14%/day (≈ 35%/yr)** | ≤ 0.05%/day before 2021, ~0 since | **Uninformative.** Expected t ≈ 1. |
| Same, holdout | ≈ 0.083 | ≈ 0.28%/day | — | Uninformative |
| Per-hour variance ratio, RTH vs overnight | small relative to the effect | ratios near 1.3 are detectable | ~4–6× (Bondarenko: US 0.32 vs Asia 0.14 annualised vol) | Near-certain detection |
| Lower-tail Hill index difference (k = 5%) | ≈ 0.6 | ≈ 2.0 | Not reported in an extractable form | Detects only a large difference |

The mean-return row is why this phase cannot rescue a "drift" claim. Even if NQ had the full pre-2021 ES
overnight premium, 5.5 years would not distinguish it from zero. That is pre-declared, so a null cannot later
be read as evidence that the premium is absent.

## 8. Data still needed before the freeze (free; Ethan runs these, since the bridge cannot reach Databento)

1. **Databento degraded-quality days** for GLBX.MDP3 over 2019-05-06 → 2026-10-31, via
   `client.metadata.get_dataset_condition(...)` (free metadata call). The download warning showed
   2020-02-27, 2020-02-28 and 2020-05-05, among others. The list must be pasted into the protocol **before** it
   is hashed, so that a sensitivity exclusion is not chosen after seeing results.
2. *(Optional)* `py scripts\roll_map.py MES.v.0 2019-05-06 2026-11-01`, only if MES is wanted as a robustness
   market. MES is ~0.95 correlated with MNQ, so it is **not** independent evidence; it checks the code, not
   the claim.
