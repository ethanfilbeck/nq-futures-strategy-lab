# Phase 4, synthetic-data stage: report v2 (decisions U1–U6, expanded calibration)

Written 2026-11-12. **Synthetic data only.**
- All development and testing ran in a cloud copy of the repository with **no `data/` folder**.
- The synthetic tests now also refuse to open anything under the project's real `data/` folder (U6).
- No real price was loaded, no study result was calculated, nothing was committed or pushed, and nothing was
  added to `PREREG_HASH.txt`.
- The pinned data and protocol hashes are unchanged.

---

## 1. Protocol updates (DRAFT v4.1)

`docs/DRAFT_PREREG_SESSIONS_awaiting_signoff.md`. Only these passages changed (the full diff against v4
replaces four lines and adds text; no count, threshold, hypothesis, test or sample rule changed):

| Decision | Change | Section |
|---|---|---|
| U1 | d⁻ = the immediately preceding session **with RTH trading**, with E5 covering a no-RTH session in between. Every frozen count was always computed this way. | §4.7 |
| U2 | "Regime stability not assessable" adopted as an official development label. The minimum k = 20 is not lowered and the regimes are not redefined. | §7 |
| U3 | Exact EWMA start-up rule written out (§2 below) | §7 |
| U4 | S7 (GARCH-t) **withdrawn**. No new dependency or optimiser; the five primary tests unchanged. The runner records "WITHDRAWN; not computed". | §11 |
| U5 | Exact volatility-group specification written out (§3 below) | §6.2 |
| — | Change log, Appendix D part 4 | App. D |

## 2. U3: the exact volatility-scaling start-up rule

**Protocol v4, §7, verbatim:**
> σ̂²_S(d) = λ·σ̂²_S(prev) + (1−λ)·r_S(prev)², with λ = 0.94; updated only with returns of sessions in the
> analysis set, in time order. Excluded sessions are skipped, neither updating nor being scaled. Initialised as
> the mean of r² over the first 20 analysis sessions of each period, which are then dropped.

**What v4 left open:** the session index at which the initial value is placed. Two readings exist:

| Reading | σ̂² of the first scaled session (t = 20) | Comment |
|---|---|---|
| **A, implemented** | `mean(r[0..19]²)` | The initial value **is** the variance forecast for t = 20. Each r enters once. |
| B | `0.94·mean(r[0..19]²) + 0.06·r[19]²` | The initial value is placed at t = 19 and the recursion applied once, so r[19] is counted twice. |

The two readings differ only by a weight that decays as 0.94ᵗ; after about 75 sessions the difference is
below 1%. **v4.1 now states reading A explicitly.**

**Implementation** (`nq_bot/sessions.py`, `ewma_scale`):
```python
s2 = float(np.mean(r[:burn] ** 2))          # burn = 20  -> sigma2[20] = mean(r[0..19]^2)
for t in range(burn, len(r)):
    z[t] = r[t] / math.sqrt(s2)             # z[t] = r[t] / sigma[t]
    s2 = lam * s2 + (1 - lam) * r[t] ** 2   # sigma2[t+1] = lam*sigma2[t] + (1-lam)*r[t]^2
```
z[0..19] stay NaN (dropped). `inputs_from_sample` applies it to the analysis sessions in time order, so excluded
sessions neither update nor are scaled.

**Verified by tests:**
- `test_ewma_startup_rule_exact` recomputes z[20] and z[21] by hand, to a relative 1e-12;
- `test_ewma_is_causal` changes r[300:] and shows z[0..299] unchanged and z[300]'s scale unchanged.

## 3. U5: the exact volatility-group formula

**Specification (v4.1 §6.2; `vol_tercile_membership`):**

| Element | Definition |
|---|---|
| Input | RV_RTH(d): 5-minute RTH realized variance of each analysis session (78 intervals, §4.11), in time order |
| Trailing measure | `T[d] = mean(RV_RTH[d−20], …, RV_RTH[d−1])`, the previous 20 analysis sessions, never d itself |
| Cut-offs | `c1[d], c2[d]` = the 1/3 and 2/3 quantiles (numpy default linear interpolation) of `{T[j] : j < d, T[j] defined}`, an **expanding window of earlier sessions only** |
| Assignment | group 1 (low) if `T[d] ≤ c1[d]`; group 2 if `c1[d] < T[d] ≤ c2[d]`; group 3 (high) if `T[d] > c2[d]`. Ties go to the lower group. |
| Unassigned | the first 20 sessions (T undefined) and the next 60 (fewer than 60 earlier T values), so the first 80 analysis sessions of a period. Reported as a count. |
| Use | Descriptive distribution statistics of ON and RTH per group only. **No test uses the groups.** |

**Does membership depend on the outcomes being evaluated? No:**
- Session d's group is a function of RV_RTH of sessions **strictly before d** only.
- It never uses session d's ON, RTH or RV, nor any later session.
- `test_volatility_groups_depend_only_on_earlier_sessions` replaces session d's RV and every later session's
  with wildly different values; d's group is unchanged in all four trials.
- `test_volatility_group_formula_on_a_hand_case` checks the formula and the 80-session start on a hand
  example.

**This is a change from the v4 synthetic build, which used full-sample cut-offs.** Those let session d's own RTH
variance enter later sessions' trailing means, and therefore the cut-offs, so the "no dependence" statement
could not have been confirmed. The expanding window is what v4's word "causal" requires. **The minimum history
of 60 earlier T values is a new constant chosen now, without data, and needs your approval** (§6, item L4).

## 4. Expanded Monte Carlo calibration

**Design:**
- **Production code path unchanged:** `point_stats`, `stationary_indices`, `bootstrap_family`,
  `centered_p`, `percentile_ci`.
- n = 1,230 sessions (the development primary size), with a Tue–Fri V1 mask (about 984; the protocol has 983).
- Mean block 20 (frozen), two-sided centered p, 99% percentile interval.
- **One deviation: B = 999 instead of 10,000,** to make 210,000 repetitions feasible (2 h 1 min on 2 cores).
  B sets the resolution of each p in steps of 0.001; 0.001 is still below Holm's first threshold of 0.002.
- **Seed rule:** data rng = `default_rng([scenario_id, rep, 1])`; bootstrap rng =
  `default_rng([scenario_id, rep, 2])`, rep = 0…19,999. Every repetition is individually reproducible.
- **Confidence intervals:** Wilson score 95% (closed form, no new dependency).
- **Why one null per test:** the five nulls cannot hold in one dataset. V1's null (equal variance *per hour*)
  forces unequal per-session variance, while L1's null holds only with *equal* per-session variance. Each test
  is calibrated under its own exact null; Holm then controls the family-wise rate for valid p-values under
  any dependence.
- Script: `scripts/sessions_calibration.py`. Full results: `SESSIONS_CALIBRATION.json`.

### 4.1 False-positive rate at nominal 1% (20,000 repetitions, 200 expected)

| # | Scenario (exact null) | Test | Rejections | Rate | Wilson 95% CI | Verdict on calibration |
|---|---|---|---|---|---|---|
| 1 | iid Gaussian, equal per-hour variance | V1 | 266 | 1.33% | 1.18–1.50% | Mildly liberal |
| 10 | Common GARCH volatility (a 0.08, b 0.90) | V1 | 328 | 1.64% | 1.47–1.83% | Mildly liberal |
| **2** | **Independent GARCH clustering in ON and RTH** | **V1** | **3,884** | **19.42%** | **18.88–19.97%** | **Badly oversized** |
| 3 | iid Student-t(4), same shape | T1 | 67 | 0.34% | 0.26–0.43% | Conservative |
| 3 | same | T2 | 55 | 0.28% | 0.21–0.36% | Conservative |
| 7 | Common GARCH, t(4) | T1 | 64 | 0.32% | 0.25–0.41% | Conservative |
| 7 | same | T2 | 60 | 0.30% | 0.23–0.39% | Conservative |
| 4 | iid Gaussian; volume share = population WPC | P1 | 266 | 1.33% | 1.18–1.50% | Mildly liberal |
| 8 | Common GARCH | P1 | 300 | 1.50% | 1.34–1.68% | Mildly liberal |
| 5 | iid Gaussian, equal session variance | L1 | 218 | 1.09% | 0.96–1.24% | **Consistent with 1%** |
| 9 | Common GARCH | L1 | 159 | 0.80% | 0.68–0.93% | Slightly conservative |

### 4.2 Holm's first-step threshold, 0.2% (20,000 repetitions, 40 expected)

| Scenario | Test | Rejections | Rate (Wilson 95%) |
|---|---|---|---|
| 1 | V1 | 57 | 0.29% (0.22–0.37%) |
| 10 | V1 | 72 | 0.36% (0.29–0.45%) |
| 2 | V1 | 2,304 | **11.52%** (11.08–11.97%) |
| 3 | T1 / T2 | 5 / 4 | 0.03% / 0.02% |
| 7 | T1 / T2 | 5 / 6 | 0.03% / 0.03% |
| 4 | P1 | 65 | 0.32% (0.26–0.41%) |
| 8 | P1 | 66 | 0.33% (0.26–0.42%) |
| 5 | L1 | 31 | 0.16% (0.11–0.22%) |
| 9 | L1 | 31 | 0.16% (0.11–0.22%) |

5% results are in the JSON: V1 iid 5.8%, P1 5.9%, L1 4.9%, T 3.0–3.2%; scenario 2 32%.

### 4.3 Coverage of the nominal 99% percentile intervals (20,000 repetitions, 19,800 expected)

| Scenario | Test | Coverage | Wilson 95% CI |
|---|---|---|---|
| 1 V1 null iid | V1 | 98.46% | 98.27–98.62% |
| **6 V1 alternative, true ratio 3** | V1 | 98.46% | 98.27–98.62% |
| 10 V1 null, common GARCH | V1 | 98.22% | 98.03–98.40% |
| **2 V1 null, independent GARCH** | V1 | **80.10%** | **79.54–80.65%** |
| 3 / 7 | T1 | 99.11% / 99.17% | 98.97–99.23% / 99.03–99.29% |
| 3 / 7 | T2 | 99.29% / 99.28% | 99.16–99.39% / 99.15–99.38% |
| 4 / 8 | P1 | 98.38% / 98.30% | 98.19–98.54% / 98.12–98.47% |
| 5 / 9 | L1 | 98.99% / 99.29% | 98.84–99.12% / 99.16–99.39% |

### 4.4 Diagnostic only, not a rule change: V1 under scenario 2 with longer blocks (5,000 repetitions)

| Mean block | False positives at 1% (50 expected) | Coverage of 99% interval |
|---|---|---|
| 20 (frozen) | 19.4% | 80.1% |
| 40 (= S9 long block) | 13.6% (12.7–14.6%) | 85.9% |
| 100 | 10.6% (9.8–11.5%) | 89.1% |

Longer blocks help only a little, so this is **not** a block-length problem. With persistence 0.98 and
*separate* volatility paths, the log ratio of two means of squares is dominated by rare high-volatility episodes
that a 5.5-year sample rarely contains. When ON and RTH share one volatility path (scenario 10), it cancels in
the ratio and V1 behaves almost nominally.

### 4.5 What the calibration means

1. **T1, T2 and L1 are valid at 1%** in every scenario (T conservative, so less powerful).
2. **P1 and V1 are mildly liberal** under independent and common-volatility data: about 1.3–1.6% where 1% is
   nominal, and 0.29–0.36% at Holm's first step where 0.2% is nominal. Their 99% intervals cover 98.2–98.5%.
   By Holm's union bound, the family-wise false-positive rate under the realistic scenarios is therefore at
   most a little above the 1% target, and can be bounded but not set exactly.
3. **V1 is badly miscalibrated if ON and RTH volatility cluster *independently*** (scenario 2). Whether the
   real data looks more like scenario 10 (shared volatility, as one would expect for one index) or scenario 2
   **cannot be checked without examining the data**, so I have not checked it.
4. Practical weight: V1 is a pipeline/calibration check that cannot carry any verdict, and the official verdict
   is INCONCLUSIVE regardless. **The real exposure is in reporting:** V1's interval and p could be
   over-confident, and its "established" label could pass the pipeline check falsely. Section 6 item **U7** sets
   out the options. Nothing frozen was changed.

## 5. Source code and test results

| File | Lines | SHA-256 |
|---|---|---|
| `nq_bot/sessions.py` | 848 | `06619302…556328ad` |
| `run_sessions_study.py` | 309 | `dc5de2e6…7ca031e2` |
| `tests/test_sessions.py` | 929 | `1359122b…ca5c437f` |
| `tests/sessions_synth.py` | 129 | `5536e067…e51f1ce5` (unchanged) |
| `scripts/sessions_calibration.py` | 203 | `ef815568…00e6b3ff` |
| `tests/test_tooling.py` (+1 line), `pytest.ini` (+2 lines) | — | `b204db94…`, `70e05743…` (unchanged since v1 of this report) |
| `SESSIONS_CALIBRATION.json` | — | `e32b7992…5164da27` |

| Gate | Result |
|---|---|
| `scripts/check.py`: ruff, pytest, prereg (11 hashes unchanged), prepublish, pip-audit, mypy | **all PASS**; **224 passed, 2 skipped** (the older webhook tests, absent data) |
| `tests/test_sessions.py` | **106 passed**, with RuntimeWarnings promoted to errors |
| Coverage | `sessions.py` **99%** (532 statements, 2 missed); `run_sessions_study.py` **97%** (the 6 missed are the real-data entry points and one defensive re-check, deliberately not executed) |

**New since report v1:**
- U6 real-data guard: an autouse fixture plus 2 tests. Opening `data/…` through `open` or `pd.read_csv` fails.
- No webhook, broker or live module is imported by the new tests.
- U3 exact-rule test; U5 causality and hand-case tests; S7-withdrawn test; calibration-script smoke test.

## 6. Remaining limitations and unresolved issues

| # | Item | Status / needs |
|---|---|---|
| **U7** | **V1 inference is badly oversized if ON and RTH volatility cluster independently** (§4) | **Your decision, before any data.** (a) Keep V1 as frozen, adding a pre-declared caveat that its p and interval may be over-confident. (b) Pre-register a different V1 inference now, which would need its own synthetic calibration. (c) Keep V1's point estimate and the halt check, but report its interval and p as descriptive only. I have not changed anything. |
| L1 | P1 and V1 are mildly liberal (1.3–1.6% at nominal 1%); intervals cover about 98.2–98.5% | Disclose in the results; no rule change requested |
| L2 | T1/T2 are conservative (about 0.3% at 1%), so power is lower | Disclose |
| L3 | Calibration used B = 999; the real run uses 10,000 | Disclosed. B affects p resolution, not the test design. |
| L4 | U5's 60-value minimum history is a new constant (chosen without data) | **Needs approval** |
| L5 | The synthetic scenarios do not include price-limit censoring or missing data inside the Monte Carlo (those are covered by the unit tests) | Disclose |
| L6 | Tail-shape regime stability is "not assessable" for 2020–2022 (U2, accepted) | Done |
| L7 | P1 uses MNQ volume, which may not reflect where Nasdaq-100 price discovery happens | Disclosed in the protocol |
| L8 | Real-data entry points are untested end to end, by design | First real run only after sign-off and hashing |
| L9 | Two older webhook tests read `data/mnq_train.csv` if present | You run only `py -m pytest tests/test_sessions.py`; the new tests are guarded |
| D8 | Liu & Tse and Riedel & Wagner library access | Pending your check |

**Stopped here, as instructed.** The code is in your local `nq_bot` folder, uncommitted. Nothing is hashed or
committed until you approve.
