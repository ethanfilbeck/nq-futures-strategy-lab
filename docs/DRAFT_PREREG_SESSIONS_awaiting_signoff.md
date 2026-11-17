# Pre-registration (DRAFT v4): overnight vs regular-session behaviour in MNQ — descriptive study

**Status: DRAFT v4.1, 2026-11-12 ~13:00 CT (v4 plus decisions U1–U6 of 12:22 CT; no count, threshold or test changed). Not signed, not hashed, not committed. Only the synthetic-data code stage has run; no real-data analysis has started.**
**Official confirmatory verdict, fixed in advance: INCONCLUSIVE** (decision D2-a = O1; §8).
v3 → v4 changes: Appendix D, part 2. v2 → v3 changes: Appendix D, part 1. Companions: `LITERATURE_SESSIONS.md`, `DATA_FEASIBILITY_SESSIONS.md`,
`HOLDOUT_EXPOSURE_INVENTORY.md` with `HOLDOUT_EXPOSURE_SESSIONS.csv`. Scripts: `scripts/sessions_preflight/`.

---

## 0. Decision record

| # | Ethan's decision (2026-11-11) | Where implemented |
|---|---|---|
| C7 | Approved with restrictions: descriptive only; overlaps documented | §2, §6.3, §10 |
| Budget | Not line 13; no data purchases | §3 |
| D1 | **Symmetric FOMC treatment:** the same predefined exclusion in development and holdout; sensitivity includes them in both; exact dates and reasoning documented | §5.1 E6, Appendix C |
| D2 | Holdout split into unexposed / H8-specific / placebo-exposed; confirmatory analysis uses **genuinely unexposed** observations only; percentage not used as an argument | §8, Appendix E |
| **D2-a** (2026-11-11 23:34) | **O1 is the official confirmatory outcome: INCONCLUSIVE.** O2 is retained only as a labelled secondary analysis of a restricted population, never described as clean or untouched. O3 is documented as the only route to genuinely new confirmation; no purchase without separate approval. | §7, §8 |
| D2 (overlap) | Mutually exclusive A/P/B breakdown, reconciled to 334 and 318 | Appendix E |
| D3 | 0.15 not approved without justification; alternative thresholds as sensitivity | §6.1 P1, §6.4 |
| **D3-a** (23:34) | **Volume-share comparison approved conditionally, as a descriptive measure only.** Exact formula, units, missing data, zero-volume intervals, price movement and overnight volume specified before analysis. Barclay & Hendershott's limitations stated. Thresholds 0.10–0.25 kept as predefined sensitivity. | §6.1 P1, §6.4 |
| D4 | 1% family-wise error across the 5 tests retained; exact procedures to be specified | §7 |
| **D4** (23:34) | **§7 conditionally approved.** Formulas, directions, intervals, effect sizes, minimum sizes and holdout rules to be verified before Phase 4. | §7.1 verification table |
| D5 | Mean returns: descriptive only | §6.2 |
| D6 | 2019 excluded from primary; may appear in the data-quality discussion | §3, §5.3 |
| D7 | MES removed; reasons documented | §3.1 |
| D8 | Ethan is checking library access to the two paywalled papers; nothing unverified is reproduced | `LITERATURE_SESSIONS.md` |
| D8 status | **Liu & Tse (2017) and Riedel & Wagner (2015): availability through Murray State UNKNOWN, pending Ethan's check.** Access is not assumed. Until checked, every detail beyond their abstracts remains marked *unverified*, and no test depends on one. | — |

## 1. Question

Does MNQ behave measurably differently overnight than during US regular trading hours, in volatility, return
distribution shape, vol-scaled tail characteristics, price discovery and extreme moves? Is that stable
across 2020–2025 regimes? How does it compare with published findings for other markets?

## 2. What this study is not

- No entry or exit signal, sizing rule, strategy, strategy return, Sharpe ratio, profitability claim or
  "tradeable" language.
- **No predictive regressions**, and no statistic linking one period's quantity to a later period's return.
- No mean return over an hour or a sub-session window.
- No suggestion that any result is a source of trading profit.
- The results file opens by stating that `RESEARCH_BUDGET.md` rule 1 makes any trading idea drawn from this
  data permanently ineligible.

## 3. Data (hashes preserved and re-verified ~23:50 CT, unchanged since first recorded)

| File | Content | SHA-256 |
|---|---|---|
| `data/mnq_train.csv` | MNQ.v.0 1-min, 2,167,313 bars, 2019-05-06 00:00 → 2025-06-30 23:59 UTC | `a2d8d017cceb0d551e213ba6cdc48cd91dd5d91183ab82cdc69fc506bcb55fe1` |
| `data/mnq_holdout.csv` | 474,794 bars, 2025-07-01 00:00 → 2026-10-30 20:59 UTC | `8b00498f4d8427e821ec50d4654e991f07e9cdac6c87aa56dee27b995532be8f` |
| `runs/rollmap_MNQ.json` | Exact roll calendar, 30 switches | `e1beaeeda0c6ab73bf03cfb75b1345fe3748c354e9f817b197385c6bef5a9005` |
| `nq_bot/family3.py` | Development FOMC list (`FOMC_DAYS`) | `b97fdfd3e9ef925223556a9b3f745802b865fe0c1edc929ca7afa74685600331` |
| `docs/HOLDOUT_EXPOSURE_SESSIONS.csv` | Exposure category per holdout session (§8) | `a462425b30c59eb1b832bf8650588b874b5b5d94cec78fd454c27a0165b88683` |

These three are read only for the exposure inventory (timestamps), never for analysis:

| File | SHA-256 |
|---|---|
| `data/mes_2019_2026.csv` | `3a412eda694b9d1d87a246d04414b40a592772283f8508c7c9a1f2c1906d1aff` |
| `data/m2k_2019_2026.csv` | `ce1e80bf123fbbbe96a1113b0feef6c4bf202d5d086f3ee6ee33fd71279ad2e9` |
| `data/mgc_2019_2026.csv` | `d2c0696393d6e81c6b6917e9f331965b5dca93ce913845acb5e2ca8b5b470459` |

The runner aborts if any analysis-file hash differs.

| Period | Session dates | Role |
|---|---|---|
| Development | 2020-01-02 → 2025-06-30 | Estimation |
| Holdout | 2025-07-01 → 2026-10-30 | Split by exposure (§8); confirmatory use per decision D2-a |
| 2019 | 2019-05-07 → 2019-12-31 | Data-quality discussion only (D6) |

### 3.1 Why MES is removed (D7)

1. **No roll map.** MES.v.0 splices contracts without back-adjustment, like MNQ, and `scripts/roll_map.py`
   has not been run for MES. Without it, MES roll sessions could only be found with the heuristic detector,
   which `nq_bot/rolls.py` documents as missing 11 of 25 rolls in 2019–21. That is exactly the
   contamination that inflated H8 by 60% on MES.
2. **No independent evidence.** MES is ~0.95 correlated with MNQ. Agreement would be close to arithmetic, as
   the H8 replications showed.
3. **Not cleaner.** Every MES holdout session is itself exposed: the MES real-event, sham, Wednesday-pool and
   replication-pool windows (inventory §2). MES cannot supply the unexposed holdout that MNQ lacks.
4. **More risk than benefit.** It adds a data source, a roll problem and code paths, and answers no research
   question that MNQ cannot.

## 4. Session boundaries and timezone handling (frozen; unchanged from v2)

1. Timestamps are UTC, tz-aware, and mark the bar **start**: bar *t* covers [t, t + 60 s). A bar exists only
   if a trade occurred in that minute.
2. Conversion: `tz_convert('America/New_York')` with the IANA tz database; the tzdata version is logged. All
   boundaries are **ET wall-clock times**.
3. DST: CME (Central) and ET change together. The DST instant (Sunday 02:00 local) always falls inside the
   weekly close (Fri 17:00 → Sun 18:00 ET). No session spans a DST change, and the code asserts this.
4. CME session date of a bar = the calendar date of (ET + 6 h).
5. RTH bars: ET minute-of-day in [570, 960).
6. O(d) = `open` of the earliest bar in [570, 575) on *d*. C(d) = `close` of the latest bar in [955, 960) on
   *d*.
7. d⁻ = the immediately preceding CME session **with RTH trading** (U1, 2026-11-12). If a session with Globex trading but no RTH lies between d⁻ and d, rule E5 excludes d (§5.4), so an overnight is never bridged across such a session. *(v4 wrote "with any Globex trading"; the frozen counts in §5.2 were always computed under this wording, so no count changes.)*
8. RTH(d) = ln C(d) − ln O(d): 6.5 h.
9. ON(d) = ln O(d) − ln C(d⁻): 16:00 ET on d⁻ → 09:30 ET on d. That is 16.5 trading hours on a normal
   night; the 17:00–18:00 halt has 0 bars in every year.
10. Long overnight: the calendar gap from d⁻ to d is more than 1 day.
11. Realized variance (descriptive): 5-minute grid, last price at or before each grid point. RTH has 78
    intervals; 18:00–09:30 has 186 intervals; 16:00→18:00 is one squared return.

## 5. Sample construction

### 5.1 Exclusion rules (frozen)

| Rule | Definition | Reason |
|---|---|---|
| **E1** | *d* is an early close: last RTH bar at or before 13:15 ET | Not a full session |
| **E2** | d⁻ is an early close | The overnight would start at 13:00/13:15, so it is not comparable |
| **E3** | O(d), C(d) or C(d⁻) is missing | No price at a boundary |
| **E4** | A contract switch from `rollmap_MNQ.json` falls in (C(d⁻), O(d)] | Spliced, unadjusted series |
| **E5** | The overnight spans a CME session that had Globex trading but **no RTH** (§5.4) | ON would span a partial extra session |
| **E6** | *d* is a scheduled FOMC statement day, or the session immediately before one, in **both** periods (D1). Dates: Appendix C. | Symmetric treatment (reasoning below) |

**Why E6 exists and why it is symmetric (D1).** The holdout's FOMC pairs are exactly the H8-specific
(Category A) sessions, so they must leave the holdout's primary analysis. FOMC pairs are also structurally
different days: a scheduled 14:00 statement falls inside RTH(d), and the preceding session is a
pre-announcement day. Removing them from one period only would make the two periods differ in composition,
biasing RTH volatility, price discovery and extreme-move comparisons between them. So the identical rule
applies to both.

The rule uses the **same scheduled-statement list H8 used**: `family3.py` `FOMC_DAYS` plus
`HOLDOUT_FOMC_DAYS`. Unscheduled 2020 actions (2020-03-03 and 2020-03-15) are **not** excluded, because they
were not in H8's footprint and are not scheduled-event days.

**Sensitivity S5:** E6 removed in both periods.

### 5.2 Count reconciliation (each figure re-derived by `reconcile_counts.py`, timestamps only)

**Where every number comes from:**

| Figure | Definition | How calculated |
|---|---|---|
| **1,417** | Development sessions (2020-01-02 → 2025-06-30) with at least one RTH bar | Count of session dates with ≥ 1 bar in [570, 960) |
| **1,367** | Development sessions with all 390 RTH minutes present | A **coverage statistic, not a sample**: 1,417 − 46 early closes − 4 non-early sessions with < 390 bars (2020-03-09, 03-12, 03-16, 03-18: market-wide circuit-breaker halts) |
| **346** | Holdout sessions with ≥ 1 RTH bar | Same as 1,417 |
| **334** | Holdout full 390-bar sessions | 346 − 12 early closes; the holdout has no short non-early sessions |
| **1,308** | Development eligible | 1,417 after E1–E5, sequential table below |
| **318** | Holdout eligible | 346 after E1–E5 |
| **1,230** | Development primary | 1,308 − 78 (E6) |
| **297** | Holdout after E6 | 318 − 21 (E6). **Not the confirmatory sample:** see §8 |

**Sequential removal (rules applied in order E1 → E6):**

| Step | Development removed → remaining | Holdout removed → remaining |
|---|---|---|
| Start | 1,417 | 346 |
| E1 | −46 → 1,371 | −12 → 334 |
| E2 | −39 → 1,332 | −10 → 324 |
| E3 | −0 → 1,332 | −0 → 324 |
| E4 | −21 → 1,311 | −5 → 319 |
| E5 | −3 → **1,308** | −1 → **318** |
| E6 | −78 → **1,230** | −21 → **297** |

**Standalone hits (each rule on its own, before overlaps):**

| Rule | Dev | Holdout | Overlaps that explain the difference from the sequential count |
|---|---|---|---|
| E1 | 46 | 12 | — |
| E2 | 46 | 12 | 7 dev and 2 holdout sessions are both early and follow an early close (e.g. the day after Thanksgiving follows Thanksgiving) |
| E3 | 85 | 22 | **Fully nested** in E1/E2: every hit is an early-close session missing C(d) or C(d⁻). It removes 0 after them. |
| E4 | 22 | 5 | Dev: 2024-06-19 is also E1 (Juneteenth early close). The 8 dev E4/E6 overlaps are listed below; there E4 is applied first. Holdout: 2026-06-17 is also E6. |
| E5 | 3 | 1 | None |
| E6 | 86 | 22 | 8 dev sessions are also roll sessions (2020-09-16, 2021-03-17, 2022-03-16, 2022-06-15, 2022-12-14, 2023-06-14, 2024-09-18, 2025-06-18). Holdout: 1 (2026-06-17). |

**Sub-samples used by specific measures:**
- V1 uses Tue–Fri sessions that are not long overnights: development 983 (1,061 without E6); holdout
  per §8.
- The first holdout overnight, ON(2025-07-01), starts at the development-period price C(2025-06-30). This is
  recorded.

### 5.2a Holdout count history: what each number means, and what changed (v4 clarification, 2026-11-12)

**The holdout's numbers are nested sets, not competing totals.** All were re-derived ~00:35 CT from the raw
timestamps of both files.

| Figure | Exactly what it counts | Relationship |
|---|---|---|
| **347** | Session dates in 2025-07-01 → 2026-10-30 with **any** bar, Globex or RTH | All sessions |
| **346** | Sessions with **at least one RTH bar** | 347 − 1: **2026-04-03** (Good Friday) had Globex trading until 09:14 ET and no RTH |
| **334** | Sessions with **all 390 RTH minutes** | 346 − 12 scheduled early closes: 2025-07-03, 07-04, 09-01, 11-27, 11-28, 12-24; 2026-01-19, 02-16, 05-25, 06-19, 07-03, 09-07. In the holdout this equals "346 after E1", because no non-early session is short. |
| **318** | **Eligible** observations | 334 after E2 (−10), E3 (−0), E4 (−5) and E5 (−1) |

**334 was never the total holdout.** It is the full-session count. Where earlier text said otherwise or used a
wrong label:

| Where | What it said | What is correct | Cause |
|---|---|---|---|
| Chat summary after Phase 2, and `DATA_FEASIBILITY_SESSIONS.md` v1 §1 | "333 in the holdout", meaning full sessions | **334** full sessions | A v1 script built session tables per file, then de-duplicated by session date keeping the first. The development file contains **120 Globex bars (0 RTH)** for session 2025-07-01, so the real session was dropped. Already corrected in v2 (A.2). |
| `DATA_FEASIBILITY_SESSIONS.md` v1 §5 | "Sessions with any RTH trading: 1,420 / **347**" | 1,420 / 347 count **any-bar** sessions. With RTH: **1,417 / 346**. | Mislabelled column. The development half was corrected in v2. **The holdout half (347 → 346, the extra date being 2026-04-03) is corrected here for the first time**, and in that document's correction note. |
| Ethan's 2026-11-11 23:34 request, "reconcile against all 334 holdout sessions" | — | Appendix E reconciles against all three levels: 346, 334 and 318 | 334 read as a total. The table above fixes the meaning. |

**No dates were added, removed or silently reclassified between inventory versions:**
- The inventory has a single source file, `docs/HOLDOUT_EXPOSURE_SESSIONS.csv`. Its SHA-256 is
  `a462425b…b88683`, identical when first written (v3) and re-checked now (v4).
- It has **346 rows, no duplicates, and exactly the same session dates as the 346 sessions with RTH.**
  2026-04-03 is absent because it has no RTH.
- v3's priority categories and v4's overlap cells are **two views of the same rows**, both derived only
  from the CSV's `tests` column:
  - A_H8 21 = "A only" 10 + "A and B" 11;
  - P_placebo 111 = "P and B" 111;
  - B_replication_pool 186 = "B only" 186.
- **Only labels changed between versions, never membership.** v3's "Tier B / negligible" wording was
  withdrawn; "O2 confirmatory" became "O2 secondary".

### 5.3 2019 (D6)

2019 is excluded from every analysis. It appears only in the data-quality discussion
(`DATA_FEASIBILITY_SESSIONS.md` §4), for these reasons:
- median overnight coverage 922 of 930 minutes, 10th percentile 887;
- 23:00–01:00 ET minute coverage of 93–95%;
- median overnight volume of 24 contracts per minute, against 138–559 in later years;
- 165 intra-session gaps over 15 minutes.

What that would do to the measures:
- stale prices bias realized variance down and lump moves into later intervals;
- bid-ask bounce from trade-only prices inflates variance;
- O(d) and C(d) may be single small trades.

Sensitivity S1 from v2 (including 2019) is **withdrawn** under D6.

### 5.4 The four sessions with overnight trading and no RTH (verified, treatment frozen)

| Session | Weekday | Globex bars | First → last bar (ET) | Previous RTH session | Following session, excluded by E5 |
|---|---|---|---|---|---|
| 2021-04-02 | Fri | 915 | Thu 18:00 → Fri 09:14 | 2021-04-01 | 2021-04-05 |
| 2023-04-07 | Fri | 915 | Thu 18:00 → Fri 09:14 | 2023-04-06 | 2023-04-10 |
| 2025-01-09 | Thu | 930 | Wed 18:00 → Thu 09:29 | 2025-01-08 | 2025-01-10 |
| 2026-04-03 | Fri | 915 | Thu 18:00 → Fri 09:14 | 2026-04-02 | 2026-04-06 |

Three are Good Fridays, where Globex traded until 09:15 ET. 2025-01-09 traded until 09:30 ET, the date
of the US market closure for the national day of mourning. The bar times are verified. The reasons are
consistent with those dates but not otherwise checked here.

**Frozen treatment:**
- the no-RTH session itself has no RTH and is never an observation;
- the following session is excluded (E5), because its ON(d) would run from the prior RTH close through a
  partial extra Globex session;
- no session's overnight is ever bridged across a no-RTH session.

### 5.5 Price limits: censoring, reopening and distortion in either direction

**v2's statement that limits "can only make overnight tails look thinner", and that a SUPPORTED result
"cannot be produced by censoring", is withdrawn. Both were wrong.**

**Verified rules (CME FAQ):**
- Overnight band of ±5% until **2020-10-12**, then ±7% plus a 3.5% dynamic circuit breaker.
- Overnight hours 17:00–08:30 CT.
- A contract limit-locked at 08:23 and still locked at 08:25 CT halts until 08:30 CT, then reopens from an
  indicative opening with limits expanded to 7% down.
- References are VWAP/fixing based.
- During RTH, down-only limits of 7%, 13% and 20% apply, coordinated with market-wide circuit breakers.

**Mechanisms that can distort observed tails:**

| Mechanism | Effect on ON tails | Effect on RTH tails | Direction |
|---|---|---|---|
| Overnight path capped at the band | Limits the intra-overnight path; realized variance stale while locked | — | Thinner ON path |
| Reopening after a lock (indicative open at 08:30 CT = 09:30 ET) | O(d) is a reopening print that can **overshoot or undershoot** equilibrium | The correction lands in RTH(d) | **Either**: can fatten both tails at once |
| Deferred move | Part of the overnight move is postponed past 09:30 | Appears in RTH(d) | ON thinner, RTH fatter |
| RTH limits and circuit-breaker halts (2020-03-09, 12, 16, 18) | — | RTH paths halted; endpoints intact | RTH extremes truncated within the session |
| Vol-scaling feedback | EWMA σ̂ built on censored or stale returns is mis-estimated, so later z-scores are inflated or deflated | Same | **Either** |
| Reference mismatch | The band is set on CME's reference, not our C(d⁻) = 15:59 close, so the censoring point varies day to day in ON units | Same for RTH limits | Prevents a clean Tobit-style correction |
| Dynamic circuit breaker (after Oct 2020) | Two-minute pauses; small path effects | — | Small |

**Conclusion: the net direction of distortion in T1, T2, P1 and L1 cannot be signed in advance.**

**Mitigation (frozen):**
- **S2:** exclude 2020-01-02 → 2020-10-09.
- **S3:** exclude the limit-lock-consistent sessions 2020-03-09, 03-17 and 03-18 (2020-03-16 is already E4).
- **S3b:** exclude those sessions and the session after each.
- **Descriptive flag:** count of |ON| ≥ 4.5% before 2020-10-12 and ≥ 6.5% after.
- **Label rule (cannot change a verdict):** a claim whose primary estimate **changes sign** under S2, S3 or S3b is
  reported as "*[verdict] — sensitive to price-limit episodes*".

## 6. Measures

### 6.1 Tested family (5 tests)

| ID | Statistic | Units | Literature direction |
|---|---|---|---|
| **V1** | `L = ln(mean RTH²/6.5) − ln(mean ON²/16.5)`, V1 sub-sample | log ratio; reported also as the ratio e^L of per-hour variances | L > 0. **Calibration check.** |
| **T1** | `Δα_lo = α̂_ON − α̂_RTH`: Hill tail index of −z, k = ⌊0.05·n⌋. `z_S(d) = r_S(d)/σ̂_S(d)`, σ̂² an EWMA (λ = 0.94) of the same series' own past squares through *d−1*; 20-session burn-in dropped. | tail-index units | Δα_lo < 0 (Riedel & Wagner) |
| **T2** | `Δα_hi`: same on +z | tail-index units | None; either sign |
| **P1** | `Δ_P = 100·(WPC_ON − VS_ON)`, specified exactly below (descriptive; D3-a) | percentage points | Δ_P > 0 |
| **L1** | `Δp = P(|ON| > |RTH| ∣ extreme day) − P(|ON| > |RTH| ∣ other day)`, extreme = top 5% of \|CC\|, re-ranked in each replicate | percentage points | Δp > 0 |

### P1 in detail (answers D3)

**The statistic.** The weighted price contribution of the overnight period (Barclay & Warner 1993):

`WPC_ON = Σ_d (|CC_d| / Σ_j |CC_j|) · (ON_d / CC_d) = Σ_d sign(CC_d)·ON_d / Σ_d |CC_d|`

- **Units:** dimensionless, the share of cumulative daily price movement attributable to the overnight.
- **Range:** usually between 0 and 1, but it can fall outside that range when ON and RTH move in opposite
  directions.
- **Caveat:** Wang & Yang (JEDC 2015) examine how accurately WPC measures price discovery in exactly this
  overnight/daytime setting. That is a known limitation, recorded here, not a reason to drop the measure.

**Why the v2 threshold of 0.15 is not defensible.** It came from a rough reading of an ES variance share. No
paper uses 0.15 as a materiality line, and no statistical argument makes 0.15 special. A fixed number of that
kind is a judgement dressed up as a test, so **v3 does not propose it as primary.**

**Proposed replacement, P1-V (recommended): compare WPC with the overnight's share of trading volume.**

`VS_ON = Σ_d volume(ON span of d) / Σ_d [volume(ON span) + volume(RTH span)]` over the same sessions. Volume
is summed from MNQ 1-minute bars over 16:00 d⁻ → 09:29 d, and over 09:30 → 15:59. VS_ON is a proportion, so
`Δ_P = WPC_ON − VS_ON` is in **percentage points**, and its two terms are directly comparable.

This is the benchmark the WPC literature itself uses:
- Barclay & Warner (1993) introduced WPC to compare a group's share of cumulative price change with its
  **share of trades and volume** (the stealth-trading test).
- Barclay & Hendershott (RFS 2003) apply that logic to trading after hours. They find more information
  revealed per hour during the day, while after-hours trading generates significant, albeit inefficient,
  price discovery despite low volume.

The hypothesis: **is overnight trading more informative per contract than RTH trading** (Δ_P > 0)? It has a
literature direction, it uses no number chosen by me, and VS_ON is computed mechanically in Phase 4, not
looked at now.

Read at abstract and excerpt level: Barclay & Hendershott 2003 (abstract and opening pages), Barclay &
Warner 1993 (abstract and secondary descriptions), Wang & Yang 2015 (abstract). They are added to the
literature list as such, and none of their numbers is reproduced.

**Status (D3-a): approved conditionally, as a descriptive measure only.** P1 describes where price
movement occurs relative to where trading volume occurs. It is not evidence of a trading opportunity, and
the results file must not describe it as one. P1-T, the fixed-threshold option, is retired; its values
live on only as sensitivity checks (§6.4).

#### P1 exact specification (frozen)

All sums run over the **same session set** *S*: the analysis sample after E1–E6, or a stated sensitivity
sample. Each session *d* contributes to both the price terms and the volume terms, or to neither.

| Term | Definition | Units |
|---|---|---|
| Daily price movement | `CC_d = ON_d + RTH_d = ln C(d) − ln C(d⁻)` (§4). It enters only as `|CC_d|` (weight) and `sign(CC_d)`. | log return; dimensionless |
| WPC_ON | `Σ_{d∈S} sign(CC_d)·ON_d / Σ_{d∈S} |CC_d|`, with sign(0) = 0. This equals Barclay & Warner's weighted form `Σ_d w_d·(ON_d/CC_d)` with `w_d = |CC_d| / Σ|CC|`, and avoids division by CC_d. | proportion (dimensionless). Not bounded in [0,1]. |
| Overnight volume | `V_ON(d)` = sum of `volume` over every 1-minute bar with ET timestamp in **[16:00 on d⁻, 09:30 on d)**. That is the 16:00–16:59 post-close bars plus the 18:00–09:29 Globex bars, the same span as ON_d, which starts at C(d⁻) = close of the 15:59 bar. | contracts |
| RTH volume | `V_RTH(d)` = sum of `volume` over bars in **[09:30, 16:00) on d** | contracts |
| VS_ON | `Σ_{d∈S} V_ON(d) / Σ_{d∈S} [V_ON(d) + V_RTH(d)]`. A pooled ratio of sums, **not** a mean of daily ratios, so a few low-volume days cannot dominate it. | proportion in [0,1] |
| Δ_P | `100 × (WPC_ON − VS_ON)` | **percentage points** |

**Missing and zero-volume handling:**
- **A minute with no bar is a minute with no trade.** It contributes 0 to volume and nothing to price. It is
  not missing data, and no value is imputed. This is the `zero_is_not_missing` convention in
  `nq_bot/integrity.py`.
- **Zero-volume bars:** none exist in either file (verified: 0 rows with volume ≤ 0). If one ever appears,
  the integrity gate raises an error and the run stops; it is not silently kept or dropped.
- **Missing price boundaries:** a session lacking O(d), C(d) or C(d⁻) is excluded by E3 from both the price
  and the volume terms. No observed case.
- **Sessions with CC_d = 0:** these add 0 to both sums in WPC, which is correct under the weighted form, and
  their volume still counts in VS_ON. The count of such sessions is reported.
- **Roll sessions (E4)** are excluded from both terms. The overnight volume of a roll night mixes two
  contracts.
- **Long overnights (Mondays, post-holiday):** included in the primary sample. V_ON(d) then covers Sunday's
  18:00 open onward, and the weekend itself has no trading, so no bars. Weekday-only is sensitivity S6.
- **Bootstrap:** WPC_ON, VS_ON and Δ_P are recomputed together in every replicate from the same resampled
  sessions.

**Interpretation rule (fixed):**
- Δ_P > 0 is described only as "overnight's share of cumulative price movement exceeds its share of contract
  volume in MNQ".
- Δ_P < 0 is described as the reverse.
- No statement about profitability, predictability or trading is permitted.

#### Limits on borrowing from Barclay & Hendershott (2003)

Their work is **context, not validation** of this measure:
1. **Different market.** Their setting is individual Nasdaq **stocks**, trading after hours on fragmented
   ECNs, where about 4% of volume occurred after hours. MNQ is a single, centrally cleared **futures**
   contract trading continuously on Globex, with a much larger overnight share.
2. **Different period.** Their sample is from around 2000. Market structure, algorithmic participation and
   overnight futures liquidity have changed fundamentally since.
3. **Different information.** Stock-level after-hours price discovery is driven largely by firm-specific
   news such as earnings. Index-futures overnight movement reflects macro, foreign-market and aggregate
   information. The mechanisms they model may not transfer.
4. **Different measurement.** They use per-hour and per-trade comparisons and their own measures. P1 is one
   pooled ratio comparison, so their conclusions do not map one-to-one onto Δ_P.
5. **Instrument-specific volume.** MNQ is a micro contract with a retail-heavy mix, and price discovery for
   the Nasdaq-100 complex may be led by NQ or QQQ (Hasbrouck 2003 found the ETF led for the Nasdaq-100).
   **VS_ON describes MNQ's volume, not the volume of the market that discovers the price.** This is P1's
   largest limitation.
6. **WPC's own accuracy** in the overnight/daytime setting is debated (Wang & Yang 2015).
7. **Read at abstract level only** (§ literature 4a). No result of theirs is reproduced or relied on
   numerically.

### 6.2 Descriptive only (D5): no tests, no t-statistics, no profit framing

- **Return distributions of ON and RTH, raw and vol-scaled:** mean, median, standard deviation, skewness,
  excess kurtosis, and the 1/5/95/99th percentiles. No annualisation, no Sharpe ratio, no
  difference-of-means test, no interpretation of means as returns available to anyone.
- Empirical 1% and 5% VaR and expected shortfall, per session type.
- 5-minute realized-variance shares; the overnight variance share `Σ ON² / Σ(ON² + RTH²)`.
- 24-bucket hourly **volatility** profile (squared 5-minute returns only).
- Splits: weekday vs long overnight; causal volatility terciles, **specified exactly (U5, 2026-11-12):**
  - input: RV_RTH(d), the 5-minute RTH realized variance (§4.11) of each analysis session, in time order;
  - trailing measure: `T[d] = mean(RV_RTH[d−20 .. d−1])`, the previous 20 analysis sessions, never d itself;
  - cut-offs: `c1[d], c2[d]` = the 1/3 and 2/3 quantiles (numpy linear interpolation) of
    `{T[j] : j < d, T[j] defined}`. This is an **expanding window of earlier sessions only**;
  - group: 1 (low) if T[d] ≤ c1[d]; 2 if c1[d] < T[d] ≤ c2[d]; 3 (high) if T[d] > c2[d];
  - unassigned: the first 20 sessions (T undefined) and the next 60 (fewer than 60 earlier T values), i.e. the
    first 80 analysis sessions of a period; reported as a count;
  - **independence from outcomes:** session d's group depends only on RV_RTH of sessions strictly before d. It
    never uses session d's ON, RTH or RV, nor any later session. *(The v4 synthetic build used full-sample
    cut-offs, which let session d's own RTH variance enter other sessions' trailing means and so the cut-offs.
    Replaced, because v4 calls the split "causal".)*
  - These groups are used only to describe ON and RTH distributions. They enter no test.
- Price-limit flags (§5.5).

### 6.3 Forbidden quantities (enforced by a failing unit test)

| Forbidden | Reason |
|---|---|
| Any mean, sum or cumulative return over an hour or sub-window | H3 |
| corr(ON, RTH), cov(ON, RTH), Var(CC), any regression of RTH on ON, any RTH statistic conditioned on ON's sign or size | H7 |
| Half-hour returns | H1, H2, Liu & Tse |
| Anything linking a quantity to a later period's return | Decision C7 |

### 6.4 Threshold sensitivity for P1 (D3 / D3-a; fixed now and never chosen from results)

Reported regardless of the primary choice:
- WPC_ON's 99% interval against each of **0.10, 0.15, 0.20, 0.25**;
- against the **clock-time share 16.5/23 = 0.717**;
- against the **overnight variance share**.

All of these are descriptive. None can change a verdict.

## 7. Statistical procedures (D4: conditionally approved; verified in §7.1)

**Resampling (development).**
- Stationary block bootstrap (Politis–Romano) on joint session pairs in session order: block lengths
  geometric with mean 20 sessions, B = 10,000, seed 20261111.
- **What is resampled and what is recomputed:**
  - the vol-scaled values z_S(d) are computed **once** on the original series (EWMA rule below), and the
    pairs (z_ON, z_RTH) are resampled;
  - the Hill indices, the extreme-day ranking, WPC_ON, VS_ON and every mean of squares are recomputed in each
    replicate;
  - the EWMA is **not** re-run inside replicates. Resampling blocks of an already-causal z series keeps each
    z's information set fixed. *This corrects v3, which said in one sentence that EWMA scaling was
    recomputed and in another that it was not.*
- **EWMA rule:**
  - σ̂²_S(d) = λ·σ̂²_S(prev) + (1−λ)·r_S(prev)², with λ = 0.94;
  - updated only with returns of sessions in the analysis set, in time order. Excluded sessions are skipped,
    neither updating nor being scaled.
  - Initialised as the mean of r² over the first 20 analysis sessions of each period, which are then dropped.
  - **Exact start-up rule (U3, 2026-11-12).** Index a period's analysis sessions t = 0, 1, … in time order.
    `σ̂²[20] = mean(r[0..19]²)`; `σ̂²[t] = λ·σ̂²[t−1] + (1−λ)·r[t−1]²` for t ≥ 21; `z[t] = r[t]/σ̂[t]` for
    t ≥ 20; z[0..19] are dropped. The initial value belongs to the **first scaled session** (t = 20). The other
    possible reading, assigning it to t = 19 and applying the recursion once, would count r[19]² twice.

**Development family: V1, T1, T2, P1, L1.**
- Null θ₀ = 0 for each.
- p-value, two-sided centered bootstrap: `p = (1 + #{b : |θ*_b − θ̂| ≥ |θ̂ − θ₀|}) / (B + 1)`.
- **Holm step-down, family-wise error 0.01, m = 5:**
  - order p₍₁₎ ≤ … ≤ p₍₅₎;
  - reject H₍ᵢ₎ for i = 1, 2, … while p₍ᵢ₎ ≤ 0.01/(5 − i + 1), and stop at the first failure;
  - Holm-adjusted p: `p̃₍ᵢ₎ = max_{j ≤ i} min(1, (5 − j + 1)·p₍ⱼ₎)`, and H is rejected exactly when p̃ ≤ 0.01.
  - Benjamini–Hochberg q-values are reported, labelled "information only".
- **Classification in development:**
  - *established*: p̃ ≤ 0.01 and θ̂ in the literature direction (T2: either sign);
  - *contradicted*: p̃ ≤ 0.01 with θ̂ opposite;
  - *not established*: anything else.
- **Intervals:**
  - 99% percentile interval [q₀.₀₀₅, q₀.₉₉₅] of θ*;
  - 99.8% Bonferroni-simultaneous interval [q₀.₀₀₁, q₀.₉₉₉].
  - The classification uses p̃ only. Any disagreement between interval and p̃ is reported, not resolved
    after the fact.
- **Effect sizes**, each with both intervals:

| Test | Reported in natural units |
|---|---|
| V1 | e^L, the per-hour variance ratio RTH : ON, plus both per-hour variances |
| T1, T2 | α̂_ON, α̂_RTH, Δα |
| P1 | WPC_ON, VS_ON and Δ_P in percentage points |
| L1 | P(|ON| > |RTH| ∣ extreme), P(… ∣ other), Δp in percentage points |

- **Pipeline check:** V1 not established in development → halt, and report a data or code fault.
- **Stability**, for each established claim:
  - re-estimate within R1 2020, R2 2021, R3 2022 and R4 2023-01-01 → 2025-06-30, each with its own
    bootstrap;
  - *stable* = same sign in at least 3 of 4 regimes, and no regime with a two-sided p < 0.05 in the opposite
    direction.

**Minimum sizes (analysis is refused below these, and the refusal is reported):**

| Analysis | Minimum | Expected |
|---|---|---|
| Development primary sample | 1,000 sessions | 1,230 |
| V1 sub-sample | 500 | 983 |
| Each regime | 150 sessions | approx. 200–500 |
| Hill k | 20 exceedances | ≈ 61 in development |
| O2 secondary (§8) | 100 sessions | 185 |
| O2 V1 sub-sample | 80 | 125 |
| O2 Hill, L1 | report point estimate only (k < 20) | k ≈ 9 |

**Official verdict (D2-a = O1, fixed now).** No eligible holdout session is unexposed (§8), so no
confirmatory evaluation exists.

- **The official confirmatory verdict for every claim, and for the phase, is INCONCLUSIVE**, whatever the
  development results show.
- Development classifications are reported beside it, explicitly labelled "development sample (previously
  used data)":
  - established and stable → "**INCONCLUSIVE — consistent with the literature in development; no unexposed
    evaluation data**";
  - contradicted in development → "**INCONCLUSIVE — development evidence contradicts the literature
    direction; no unexposed evaluation data**";
  - established, but regime stability **not assessable** because a regime's Hill k is below the pre-registered
    minimum of 20 (decision U2, 2026-11-12; expected for T1/T2 in 2020, 2021 and 2022) → "**INCONCLUSIVE —
    established in development; regime stability not assessable (tail sample below the pre-registered minimum);
    no unexposed evaluation data**". The minimum is not lowered and the regimes are not redefined;
  - otherwise → "**INCONCLUSIVE — not established in development**".
- The words SUPPORTED and REJECTED are reserved for a future, separately pre-registered evaluation on
  genuinely new data (O3), and are not used in this phase.
- **Prohibited uses of O2 (binding):**
  1. O2 may **not** upgrade, downgrade or qualify the official INCONCLUSIVE verdict for any claim or for the
     phase.
  2. O2 may **not** be described as confirmation, replication, out-of-sample validation, an untouched or clean
     holdout, or independent evidence. Agreement between O2 and development is reported only as "the
     restricted secondary population's estimate is in the same / opposite direction as the matched
     development estimate".
  3. O2 may **not** be generalised to the full trading week or to Tuesdays and Wednesdays.
  4. O2 p-values are **descriptive**. No Holm decision is made on them and none appears in a verdict line.
  5. O2 may **not** be pooled with the development sample or with any H-series sample.
  6. The results file's verdict section is written from §7 alone, and the code generates it **before** O2 is
     computed. A unit test fails if the verdict text depends on any O2 value.

**No test, threshold, hypothesis, sample rule or sensitivity changes after any result is seen.**

### 7.1 Verification of every formula and rule (D4)

Checked before any data is analysed. The synthetic tests in §9 must re-verify each item numerically.

| Item | Verification |
|---|---|
| L (V1) | ln of the ratio of per-hour mean squared returns. Squares are not demeaned: daily means are about 10⁻⁴ against σ about 10⁻², so the bias is about 10⁻⁴ relative, negligible and identical for both. 16.5 counts trading hours (17:00–18:00 halt excluded); 6.5 is RTH. e^L is the ratio. Correct. |
| Hill α̂ | `α̂ = [ (1/k) Σ_{i=1}^{k} ln X₍ᵢ₎ − ln X₍ₖ₊₁₎ ]⁻¹` on X = −z (lower) or +z (upper), descending order statistics, k = ⌊0.05n⌋. Needs X₍ₖ₊₁₎ > 0, which holds at k = 5% for any symmetric-ish z. **Asserted in code.** **Limitation:** Hill assumes a Pareto-type tail. On near-Gaussian tails it still returns a finite, k-dependent value, so α̂ is read as a tail-heaviness index, not a structural parameter. S8 varies k. Riedel & Wagner use the GPD shape ξ; for heavy tails ξ = 1/α. |
| Direction of T1 | A heavier tail means **smaller** α. Riedel & Wagner's "overnight fatter" means α_ON < α_RTH, so Δα_lo < 0. Correct sign. |
| WPC identity | `w_d·ON_d/CC_d = (|CC_d|/Σ|CC|)·ON_d/CC_d = sign(CC_d)·ON_d/Σ|CC|`. Identical, and defined at CC_d = 0. |
| L1 | Extreme set = the ⌈0.05n⌉ largest \|CC\|; ties are broken by earlier date (deterministic). Both proportions use disjoint sets. Δp ∈ [−100, 100] percentage points. |
| Centered p | Standard bootstrap test of θ = θ₀ using the distribution of θ* − θ̂ as the null distribution. The +1 terms prevent p = 0. |
| Holm | Formula above is the standard step-down; the adjusted form is monotone. Verified by hand on the example p = (0.001, 0.004, 0.02, 0.3, 0.5): thresholds 0.002, 0.0025 → rejects H₍₁₎ only; p̃ = (0.005, 0.016, 0.06, 0.6, 0.6). This example becomes a unit test. |
| Intervals | Percentile intervals from the same 10,000 replicates; the 99.8% level equals 0.01/5 per side-pair. |
| Directions | V1 > 0; T1 < 0; T2 none; P1 > 0 (Barclay & Hendershott context, descriptive); L1 > 0. Tests are two-sided; direction enters only the classification. |
| Holdout rules | Under O1 the holdout produces no verdict. O2 rules are in §8 and are secondary-only. |

## 8. Holdout (D2, D2-a)

Inventory, method and dates: `HOLDOUT_EXPOSURE_INVENTORY.md`. Mutually exclusive overlap breakdown:
**Appendix E**.

**Finding.** Of the 318 eligible holdout sessions, **none** is unexposed under the strict definition.
- Every eligible session overlaps a window computed in an earlier experiment: in MNQ, or in MES, M2K or gold.
- The five sessions that touched nothing are all scheduled half-days (E1).

**O1: official, adopted.** There is no confirmatory holdout. The official verdict is INCONCLUSIVE (§7).

**O2: secondary analysis of a restricted population. Not clean, not untouched, not a confirmation.**

| | |
|---|---|
| Population | Eligible holdout sessions in which **no MNQ price was used** by any earlier experiment (overlap cell "B only"), **restricted to Mondays, Thursdays and Fridays.** The single Tuesday in that cell, 2025-12-23, is dropped so that the weekday composition can be matched exactly. **n = 185:** Mon 59, Thu 62, Fri 64. V1 sub-sample (Thu/Fri, not long overnight): **125**. |
| How it was selected | **By exposure to other experiments, not at random and not by market behaviour.** These sessions were still processed in MES, M2K and gold random-long pools, so they are exposed through correlated markets. |
| Development comparison | Development primary sessions on the same weekdays: **781** (Mon 241, Thu 271, Fri 269). V1 sub-sample (Thu/Fri non-long): **538**. Every O2 statistic is shown beside this matched development estimate, never beside the all-week estimate. |
| Labelling | Every O2 table carries the caption: "*Secondary analysis. Restricted population: Mondays, Thursdays and Fridays in the 2025-07 → 2026-10 holdout, selected because no MNQ prices from these sessions were used in earlier experiments. Exposed through correlated-market computations. Not a clean holdout; not representative of the full trading week; cannot confirm or reject any claim.*" |
| Procedure | The same statistics as development. Stationary bootstrap over calendar weeks (mean block 4 weeks), B = 10,000, seed 20261112. V1 and P1: one-sided centered p in the development direction, reported **as a description of agreement only**. T1, T2 and L1: point estimates only (k ≈ 9). EWMA scaling is updated on all eligible holdout sessions in time order; sensitivity **S-z** updates it on O2 sessions only, because the primary rule lets A and P sessions' returns enter as lagged volatility inputs. That is disclosed. |
| Effect on verdicts | **None.** Secondary descriptive analysis only; the six prohibitions in §7 apply. It is never independent confirmation. |

**O3: the only route to genuinely new, independent confirmation, documented and not authorised.**
- Sessions after 2026-10-30 have never been downloaded.
- A future, separately pre-registered evaluation on such data, specified before purchase and approved by
  Ethan, is the only way any claim in this study could become SUPPORTED or REJECTED.
- **No purchase without separate approval.**

**Labelled sensitivity analyses (H-series):**
- **H-A:** O2 plus the cells containing A;
- **H-P:** O2 plus "P and B";
- **H-ALL:** all 318 eligible sessions;
- **H-E6:** E6 removed.

Each is reported separately; none is merged with another after results are seen.

**Preservation.** The holdout file is opened by the analysis code exactly once, after the development results
are committed (§9).

## 9. Order of operations, and the synthetic-data test plan

1. Ethan reviews v4 and freezes the protocol (sign-off).
2. **Code development on synthetic data only.** No real data file is opened by the new code.
   `nq_bot/sessions.py`, `run_sessions_study.py` and `tests/test_sessions.py` are tested against generated
   datasets with **known** properties:

| Synthetic case | Known property | The code must… |
|---|---|---|
| Gaussian ON and RTH with set per-hour variances (e.g. a ratio of 3.0) | e^L = 3.0 | recover the ratio within its bootstrap interval in ≥ 95% of 200 seeds |
| Equal variances | L = 0 | reject at ≤ the nominal rate (size check, 1,000 seeds) |
| Student-t / Pareto tails with set α (e.g. ON 3, RTH 6) | Δα_lo = −3 | recover the sign and approximate magnitude; Gaussian tails give a finite, k-dependent α (documented) |
| Construction with set WPC and set volume split | WPC, VS known exactly | match to floating-point tolerance; handle CC = 0 sessions |
| Missing minutes and multi-hour gaps, including a missing 09:30–09:34 window | E3 fires; no imputation | exclude exactly the right sessions; zero-is-not-missing holds |
| A zero-volume bar | — | raise `DataIntegrityError` |
| Overlapping and duplicated timestamps across two files, including the 2025-06-30/07-01 boundary that broke v1's count | — | concatenate raw bars, de-duplicate by timestamp, assign the session once; reproduce 334, not 333 |
| Injected roll jump at 00:00 UTC | — | E4 removes the session; results are unchanged by the jump |
| DST weekends, Good Friday no-RTH sessions, half-days and the day after | — | E1, E2 and E5 fire on exactly the listed dates |
| **Distorted distributions:** overnight returns censored at ±5% with the excess deferred to the RTH open; overshooting reopening prints; stale prices during a lock | known censoring | document the direction and size of the distortion in T1, T2, P1 and L1; S2/S3 flags fire |
| Forbidden quantities | — | the test fails if output contains any hourly mean, corr/cov(ON, RTH), Var(CC) or RTH-conditional-on-ON statistic |
| Holm hand example (§7.1) | p̃ = (0.005, 0.016, 0.06, 0.6, 0.6) | match exactly |
| Verdict independence | — | the verdict text is identical whether O2 inputs are present, absent or randomised |
| Locks | — | the development run refuses a second run; the holdout run refuses before the development results are committed; the holdout run refuses if O2 membership differs from the hashed CSV |

3. Ethan reviews the documents, code and synthetic test results.
4. On Ethan's instruction only: hash this file, the code and the exposure CSV into `PREREG_HASH.txt`, then
   commit and push.
5. `py run_sessions_study.py dev` runs once → `docs/RESULTS_SESSIONS_DEV.md` is written and committed.
6. `py run_sessions_study.py holdout` runs once: O2 secondary and H-series, all labelled.

## 10. Overlap with previous research

| Earlier | Overlap | Guard |
|---|---|---|
| **H3** (02:00–03:00 mean) | The ON(d) mean contains that hour; the hourly volatility profile includes its variance | ON mean is descriptive only; no hourly or window mean anywhere (§6.3) |
| **H7** (gap reversal) | **ON(d) is H7's gap variable** (log instead of points). EWMA scaling resembles H7's z. **WPC (P1) depends partly on same-day ON/RTH co-movement**, the phenomenon H7 traded. | No RTH statistic conditioned on ON; no corr/cov/regression/Var(CC); WPC is one unconditional aggregate, never split by gap. A unit test fails the build if a forbidden quantity appears. |
| **H8** and follow-ups | Holdout exposure categories A, P, B; development FOMC pairs | E6 (symmetric); §8 |
| H1/H2, Liu & Tse | None | Half-hour returns forbidden |

**Can H3 or H7 be reproduced under other names?** Not from what the code outputs. Their defining statistics
(an hourly mean; an RTH return conditioned on the gap's direction) are never computed, and the guard test
enforces that. **The residual overlap (same ON variable; P1's partial dependence on co-movement) is real and
disclosed.**

## 11. Sensitivities (none can change a verdict)

| ID | Sensitivity |
|---|---|
| S2 | Exclude the ±5% overnight-limit regime, 2020-01-02 → 2020-10-09 |
| S3 / S3b | Exclude the limit-lock-consistent sessions (2020-03-09, 03-17, 03-18) / those plus the following session |
| S4 | Exclude Databento degraded days, mapped as v2 §11 (list in Appendix A.5) |
| S5 | E6 removed in both periods |
| S6 | Tue–Fri non-long sessions only, for T1, P1 and L1 |
| ~~S7~~ | **WITHDRAWN (decision U4, 2026-11-12).** GARCH(1,1)-t scaling would need a likelihood optimiser outside the project's dependencies; no new dependency or optimiser is introduced. The five primary tests are unchanged. The runner records S7 as "WITHDRAWN; not computed". |
| S8 | Hill k of 2.5% and 10% |
| S9 | Block lengths 10 and 40 sessions (holdout: 2 and 8 weeks) |
| S-z | O2 only: EWMA scaling updated on O2 sessions alone (§8) |
| P1 thresholds | §6.4 |
| H-A, H-P, H-ALL, H-E6 | §8 |

## 12. Pre-specified literature comparisons (descriptive)

Unchanged from v2: the Bondarenko & Muravyev variance shares and volatility ordering; the Riedel & Wagner
tail direction, including weekend vs weekday; the Boyarchenko et al. 2026 decay of the mean. P1-V adds the
Barclay & Hendershott (2003) direction: overnight price discovery per contract compared with during the day.

## 13. Confirmation that nothing has been calculated

Every script run against MNQ data in this phase loads `timestamp` (plus `volume` in the coverage audit
only). Scripts and hashes:

| Script | SHA-256 | Loads |
|---|---|---|
| `coverage_audit.py` | `4727b928…d9ff723` | timestamp, volume |
| `verify_counts_and_rolls.py` | `7848b5de…436bd2` | timestamp |
| `reconcile_counts.py` | `84d3890c…6dfd` | timestamp |
| `exposure_inventory.py` | `895f4068…ae37017` | timestamp (MNQ, MES, M2K, MGC) |
| `classify_holdout_exposure.py` | `251eb57e…062161` | timestamp |
| The 2020 gap scan and the contract-file date scan | inline | timestamp |
| `o2_population.py` (O2 and matched-development counts, v4) | `ec850ce0…3ac3e1df` | timestamp, plus the exposure CSV |
| Overlap breakdown (Appendix E) | inline, run on the exposure CSV in the cloud workspace | dates and test labels only |

- **`open`, `high`, `low` and `close` have never been loaded in this phase.**
- **No price, return, volatility, realized variance, tail statistic, WPC, volume share, extreme-move
  statistic or holdout result for this study has been calculated.**
- `runs/` contains no `sessions_*` file.
- I did open earlier phases' already-published H8 result files to check the exposure reconstruction
  (inventory §5). They contain only H8 quantities.

## 14. Remaining items before final sign-off

| # | Item | Status |
|---|---|---|
| D2-a | O1 official (INCONCLUSIVE); O2 secondary, restricted and labelled; O3 documented | **Decided**, implemented in §7–8 |
| D3-a | Volume-share comparison, descriptive; specification and limitations | **Decided conditionally**, specified in §6.1. Ethan to confirm the specification is complete. |
| D4 | §7 procedures | **Conditional**: §7.1 verification done analytically. The numerical re-verification happens in the synthetic tests (§9), which Ethan reviews before the freeze takes effect. |
| D8 | Library availability of Liu & Tse and Riedel & Wagner | **Pending Ethan.** Recorded as UNKNOWN. |
| — | Overlap breakdown (Appendix E) and count history (§5.2a) | Done. Ethan to review. |
| — | O2 prohibitions (§7) | Added per Ethan 23:39 |
| — | **Freeze** | When Ethan signs below. Synthetic-data code work starts after that; real-data runs only after code review and hashing. |

Signed: ____________  Date: ________

---

## Appendix A: verification records (preserved from v2, with additions)

**A.1 Roll switches.** All 30 switches happen at 00:00 UTC (19:00/20:00 ET), inside (C(d⁻), O(d)].
Contracts follow H→M→U→Z, 1–4 days before expiry, about 61 bars within ±30 minutes. The exceptions are
2019 (50–60 bars) and 2020-03-16 (21 bars, the limit-down night). There are 22 in development (21 effective;
2024-06-19 is also E1) and 5 in the holdout.

| Session (E4) | Old → new | Days to expiry | | Session (E4) | Old → new | Days to expiry |
|---|---|---|---|---|---|---|
| 2019-06-19 | M9→U9 | 2 (2019, not in study) | | 2023-03-15 | H3→M3 | 2 |
| 2019-09-16 | U9→Z9 | 4 (2019) | | 2023-06-14 | M3→U3 | 2 (also E6) |
| 2019-12-16 | Z9→H0 | 4 (2019) | | 2023-09-13 | U3→Z3 | 2 |
| 2020-03-16 | H0→M0 | 4 | | 2023-12-14 | Z3→H4 | 1 |
| 2020-06-17 | M0→U0 | 2 | | 2024-03-13 | H4→M4 | 2 |
| 2020-09-16 | U0→Z0 | 2 (also E6) | | 2024-06-19 | M4→U4 | 2 (E1 first) |
| 2020-12-14 | Z0→H1 | 4 | | 2024-09-18 | U4→Z4 | 2 (also E6) |
| 2021-03-17 | H1→M1 | 2 (also E6) | | 2024-12-19 | Z4→H5 | 1 |
| 2021-06-14 | M1→U1 | 4 | | 2025-03-20 | H5→M5 | 1 |
| 2021-09-13 | U1→Z1 | 4 | | 2025-06-18 | M5→U5 | 2 (also E6) |
| 2021-12-13 | Z1→H2 | 4 | | **Holdout** 2025-09-18 | U5→Z5 | 1 |
| 2022-03-16 | H2→M2 | 2 (also E6) | | 2025-12-18 | Z5→H6 | 1 |
| 2022-06-15 | M2→U2 | 2 (also E6) | | 2026-03-19 | H6→M6 | 1 |
| 2022-09-14 | U2→Z2 | 2 | | 2026-06-17 | M6→U6 | 2 (also E6/A) |
| 2022-12-14 | Z2→H3 | 2 (also E6) | | 2026-09-17 | U6→Z6 | 1 |

The timing of the price discontinuity at these switches (19:00/20:00 ET, never a news hour) comes from an
earlier phase's audit (`AUDIT_2026_11_ROLLS.md`, 12 MNQ rolls). No price was examined for this
verification.

**A.2 Count corrections from v1.** The holdout has 334 full sessions, not 333 (a de-duplication bug, fixed).
Development has 1,417 sessions with RTH, not 1,420. Reconciliation: §5.2.

**A.3 H8 session pairs.** Statement days are all Wednesdays and each d⁻ is the Tuesday before; 22 sessions.
Inventory Category A.

**A.4 2020 overnight gaps of 20 minutes or more:**
- 2020-03-09 (1 gap, longest 27 min), 03-16 (14, 50), 03-17 (4, 27), 03-18 (6, 58): consistent with
  limit-locks;
- 2020-07-01 (1, 121): a data outage matching the degraded days.

**A.5 Degraded days** (Databento, retrieved by Ethan 2026-11-11 23:10 CT): 2020-02-27, 2020-02-28,
2020-05-05, 2020-06-30, 2020-07-01, 2021-12-05, 2022-01-02, 2022-11-06, 2024-09-18, 2025-09-17, 2025-09-24,
2025-11-28, 2026-01-31, 2026-03-15, 2026-03-16, 2026-03-21, 2026-04-10, 2026-05-24. These are UTC dates;
the mapping rule is in S4.

## Appendix C: E6 exclusion dates (54 FOMC pairs, 108 sessions)

Format: statement day (d⁻). All statement days are Wednesdays, except the two marked Thu, whose d⁻ is a
Wednesday.

**Development (43 pairs, 86 sessions; 78 removed by E6 after E4 overlaps):**
- **2020:** 01-29 (01-28), 04-29 (04-28), 06-10 (06-09), 07-29 (07-28), 09-16 (09-15)\*, 11-05 Thu (11-04),
  12-16 (12-15)
- **2021:** 01-27 (01-26), 03-17 (03-16)\*, 04-28 (04-27), 06-16 (06-15), 07-28 (07-27), 09-22 (09-21),
  11-03 (11-02), 12-15 (12-14)
- **2022:** 01-26 (01-25), 03-16 (03-15)\*, 05-04 (05-03), 06-15 (06-14)\*, 07-27 (07-26), 09-21 (09-20),
  11-02 (11-01), 12-14 (12-13)\*
- **2023:** 02-01 (01-31), 03-22 (03-21), 05-03 (05-02), 06-14 (06-13)\*, 07-26 (07-25), 09-20 (09-19),
  11-01 (10-31), 12-13 (12-12)
- **2024:** 01-31 (01-30), 03-20 (03-19), 05-01 (04-30), 06-12 (06-11), 07-31 (07-30), 09-18 (09-17)\*,
  11-07 Thu (11-06), 12-18 (12-17)
- **2025:** 01-29 (01-28), 03-19 (03-18), 05-07 (05-06), 06-18 (06-17)\*

\* The statement day is also a roll session; E4 removes it first.

**Holdout (11 pairs, 22 sessions; 21 removed by E6):** 2025-07-30 (07-29), 09-17 (09-16), 10-29 (10-28),
12-10 (12-09); 2026-01-28 (01-27), 03-18 (03-17), 04-29 (04-28), 06-17 (06-16)\*, 07-29 (07-28),
09-16 (09-15), 10-28 (10-27).

## Appendix D: change log

### Part 4: v4 → v4.1 (2026-11-12 ~13:00 CT, decisions U1–U6)

1. **U1:** §4.7 now says d⁻ is the previous session **with RTH**. This matches how every frozen count was
   computed; no count changes.
2. **U2:** "not assessable" regime stability for tail claims is adopted as an official development label
   (§7). The minimum is not lowered and the regimes are not redefined.
3. **U3:** exact EWMA start-up rule written out (§7).
4. **U4:** S7 (GARCH-t) withdrawn (§11).
5. **U5:** exact volatility-group formula, boundaries and assignment (§6.2). The cut-offs are now an
   expanding window of earlier sessions, so group membership cannot depend on the session being described.
6. **U6:** the synthetic tests refuse to open anything in the project's `data/` folder; the older webhook
   tests are untouched and separate (synthetic-testing report).

### Part 3: v4 final-review clarifications (2026-11-12 ~00:40 CT)

1. §5.2a: holdout count history (347 ⊃ 346 ⊃ 334 ⊃ 318). The v1 mislabel of 347 as "with RTH" is corrected, and the inventory is shown unchanged in membership (CSV hash identical).
2. §7: six binding prohibitions on the use of O2; the verdict is generated before O2 is computed, enforced by a unit test.

### Part 2: v3 → v4 (2026-11-12)

1. D2-a = O1. The official verdict is fixed at INCONCLUSIVE. The words SUPPORTED and REJECTED are reserved for a future O3 evaluation. Development labels are reported beside the verdict.
2. O2 is redefined as a secondary, restricted population: "B only" cell, Mondays, Thursdays and Fridays, n = 185. The lone Tuesday, 2025-12-23, is dropped for weekday matching. Matched development comparison: n = 781, V1 538. Mandatory caption. S-z added.
3. P1 is fully specified (formula, units, missing data, zero-volume, CC = 0, rolls, long overnights). It is descriptive only. The limits of borrowing from Barclay & Hendershott are listed. P1-T is retired; its thresholds remain sensitivity checks.
4. §7 rewritten:
   - corrected the v3 contradiction about whether EWMA is recomputed inside bootstrap replicates (it is not);
   - EWMA skip rule;
   - Holm stated with a hand-checked example — **v4 draft first wrote p̃₂ = 0.012; recomputed as 0.016 and corrected**;
   - minimum sizes;
   - §7.1 verification table.
5. §9: synthetic-data test plan (known-property datasets, missing data, overlapping files, distorted and censored distributions, locks).
6. Appendix E: mutually exclusive A/P/B overlap breakdown reconciled to 346, 334 and 318.
7. D8 recorded as UNKNOWN, pending Ethan.

### Part 1: v2 → v3

1. E6 is now symmetric (D1), with exact dates (Appendix C) and reasoning (§5.1).
2. The holdout is split into categories A, P, B and U from a reconstruction that matches the saved outputs
   exactly. **Finding: 0 eligible sessions are unexposed.** D2-a options O1, O2 and O3.
3. The v2 statement that Tier B's information was "negligible" is withdrawn: that was an argument from
   pooling and proportion.
4. P1: the 0.15 threshold is withdrawn as primary. P1-V (volume-share benchmark) is proposed. Threshold
   sensitivity is fixed in §6.4.
5. §7: exact p-value formula, Holm procedure, intervals, effect sizes, holdout family, minimum sizes, and the
   INCONCLUSIVE rule when no confirmatory holdout exists.
6. §5.5: the "can only thin" claim is withdrawn; a two-direction distortion analysis, S3b and a label rule
   are added.
7. §5.2: full count reconciliation with sequential and standalone counts and overlaps.
8. §5.4: the four no-RTH sessions are verified and their treatment frozen.
9. §3.1: MES removal documented. S1 (2019) is withdrawn under D6.
10. New scripts and the exposure CSV are hashed (§13).

## Appendix E: mutually exclusive exposure breakdown (D2)

Built from `docs/HOLDOUT_EXPOSURE_SESSIONS.csv` (hash in §3) using membership flags, not the v3 priority
order:
- **A** = any real-event window;
- **P** = any sham or Wednesday-pool window;
- **B** = any random-long replication-pool window.

| Cell | All 346 holdout sessions | 334 (346 − 12 early closes, E1) | 318 eligible (after E2–E5) | Eligible by weekday |
|---|---|---|---|---|
| A only | 11 | 11 | **10** | Wed 10 (FOMC statement days) |
| P only | 0 | 0 | **0** | — |
| B only | 203 | 196 | **186** | Mon 59, Tue 1, Thu 62, Fri 64 |
| A and P | 0 | 0 | **0** | — |
| A and B | 11 | 11 | **11** | Tue 11 (FOMC day-before) |
| P and B | 116 | 116 | **111** | Tue 53, Wed 58 |
| A, P and B | 0 | 0 | **0** | — |
| U (none) | 5 | 0 | **0** | — |
| **Total** | **346** | **334** | **318** | |

**Reconciliation:**
- **346 → 334:** the 12 E1 early closes are 7 "B only" and all 5 "U" sessions.
- **334 → 318:** the 16 sessions removed by E2–E5 are:
  - "A only": 1, the E4 roll session 2026-06-17;
  - "B only": 10 (E2 5, E4 4, E5 1);
  - "P and B": 5, all E2.
- **Marginals among the 318:** A = 21, P = 111, B = 308. 21 + 111 + 308 − 11 (A∩B) − 111 (P∩B) = 318. ✓

**Why some cells are empty:**
- **P never occurs without B.** The replication pools covered every consecutive pair not touching an FOMC
  date, which includes every sham and Wednesday-pool pair.
- **A and P never co-occur.** The placebo design banned dates within 3 trading days of a real event.
- **The A/B split:** statement-day Wednesdays are "A only", because pool pairs touching an FOMC date were
  skipped. The Tuesdays before them are "A and B", because the (Monday, Tuesday) pair was in the pool.

**Mapping to v3's priority categories:**
- A_H8 (21) = "A only" + "A and B";
- P_placebo (111) = "P and B";
- B_replication_pool (186) = "B only".

**O2 population:** "B only", Mondays, Thursdays and Fridays = 185.

**E6 versus the overlap cells:** the 21 E6 holdout removals are exactly "A only" (10) plus "A and B" (11).
