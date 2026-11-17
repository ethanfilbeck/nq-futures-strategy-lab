# Overnight vs regular-session study: research audit v3 (decisions U7, L4, D8; bootstrap review)

Written 2026-11-12. **Synthetic data only.**
- Development and testing used a cloud copy of the repository with **no `data/` folder**.
- **No real NQ or MNQ price was loaded, and no study result was calculated.**
- Nothing was committed or pushed. `PREREG_HASH.txt` is unchanged (11 lines).
- Supersedes report v2 for the items below. Report v2 and `SESSIONS_CALIBRATION.json` are kept unchanged.

---

## 1. U7: V1 made descriptive only

The full specification is in `SESSIONS_ADDENDUM_U7_L4.md` §A1–A2.

**Every place V1 reached a report, summary or verdict (inspected first), and what each now does:**

| # | Location | Before | Now |
|---|---|---|---|
| 1 | `run_family`: Holm input | V1's bootstrap p was in the 5-test Holm family. A small V1 p took the first slot and loosened the other four thresholds. | V1's slot is fixed at p = 1 with m = 5 (**U8**). The other four face 0.002 / 0.0025 / 0.0033 / 0.005, exactly as before whenever V1 was not significant. |
| 2 | `run_family`: V1 result fields | `p_two_sided`, `p_holm`, `holm_reject`, `q_bh`, `ci99`, `ci998`, classification "established" | Only `p_two_sided_descriptive_only`, `ci99_descriptive_only`, `ci998_descriptive_only`, the effect sizes, classification "descriptive only (decision U7)" and a disclosure note citing 19.4%. A guard rejects any inferential V1 field. |
| 3 | `run_family`: pipeline check | `pipeline_check_v1_established` (needed V1 significant) | `pipeline_check_v1_descriptive` = point estimate > 0 (**U9**) |
| 4 | Runner halt branch | Halted if V1 not established | Halts if the V1 point estimate ≤ 0; the message names the point estimate |
| 5 | `stability` | Re-estimated V1 by regime if established | V1 is never "established", so it is not assessed |
| 6 | `official_verdict` | V1 got an INCONCLUSIVE label that depended on its classification and stability | Fixed label "NOT A CONFIRMATORY CLAIM - descriptive estimate only (decision U7)…". V1's inputs are never read. |
| 7 | `o2_secondary` | V1's one-sided descriptive p | Kept, plus the disclosure note. O2 still cannot reach the verdict. |
| 8 | Sensitivity S9 | V1's p by block length | Kept, plus a `note_V1` entry. Sensitivities cannot change a verdict. |
| 9 | B guard (`1/(B+1) ≤ 0.01/M_TESTS`) | m = 5 | Unchanged; still m = 5 |

**Disclosure.**
- The 19.4% result is scenario 2: independent volatility clustering in the overnight and RTH series. There
  were 3,884 rejections in 20,000 repetitions at nominal 1% (Wilson 18.9–20.0%), and the 99% interval covered
  80.1%.
- Report v2 and the calibration JSON hold the original results unchanged.
- **Correction:** while writing the code note I first attributed the 19.4% to scenario 10 (common volatility).
  Before testing I checked the JSON and corrected it to scenario 2. Scenario 10 gives 1.64%.

**Not changed:**
- The other four tests and any protocol definition.
- The protocol file hash, `716e0003…37506021`, is unchanged; a test now checks it.
- No substitute V1 method was introduced.

## 2. L4: 60-value minimum history, frozen

The full justification is in the addendum §A3. In short:
- 60 is enough for a **descriptive** split. With independent values the first cut-off's rank error is about
  ±6 percentile points.
- Overlapping 20-session means hold far less information than 60 independent values, so the earliest groups
  are imprecise. That will be disclosed.
- No inferential result depends on the groups.

**Verified by new synthetic tests:**

| Test | What it checks |
|---|---|
| `test_l4_constants_frozen` | Window 20 and minimum 60 as constants and as function defaults; `vol_tercile_split` uses the defaults, with no override |
| `test_l4_first_eligible_assignment_and_boundaries` | Sessions 0–79 are unassigned (so the first 60 are). Session 80 is the first assigned, and its group equals a hand calculation from the 1/3 and 2/3 quantiles of `T[20..79]`. Sessions 81, 150 and 299 also match hand calculations from `T[20..d−1]`. A tie at a cut-off goes to the lower group. |
| `test_l4_short_samples_and_no_look_ahead_at_the_boundary` | Samples of 0, 1, 20, 79 and 80 sessions assign nothing. Multiplying RV by 50 from session 79, 80 or 81 onward leaves every group up to and including that session unchanged. Earlier data can move later groups but never makes a session before 80 eligible. |
| `test_l4_assigned_count_is_n_minus_80` | Exactly 80 unassigned for n = 81, 500 and 1,230 |
| Existing U5 test | Present-and-future replacement at sessions 90, 150, 250 and 399 leaves each group unchanged |

- **Clarification for you:** "60 prior sessions" is implemented as 60 prior *trailing means*, so the first
  **80** sessions are unassigned.
- **Foreseeable effect (calendar knowledge, not data):** the first cut-offs are built from January–April
  2020.
- Sample counts are unaffected.

## 3. D8: library access (Murray State University Libraries, checked 2026-11-12 in your Chrome)

**Method.**
- Searched the library's discovery system (Primo, "Articles" scope) by exact title.
- The default search, which shows only full text the library holds, did not return either paper.
- I then searched by title with results expanded to items without full text, and opened the record.
- **I did not sign in**, enter any credentials or request anything.

| | Paper 1 | Paper 2 |
|---|---|---|
| Title | Overnight returns of stock indexes: Evidence from ETFs and futures | Is risk higher during non-trading periods? The risk trade-off for intraday versus overnight market returns |
| Authors | Qingfu Liu; Yiuman Tse | Christoph Riedel; Niklas Wagner |
| Publication | *International Review of Economics & Finance* 48 (March 2017), 440–451. DOI 10.1016/j.iref.2017.01.005 (from the catalogue record ID) | *Journal of International Financial Markets, Institutions & Money* 39 (November 2015), 53–64 |
| Catalogue status | Record found; "Peer reviewed", "Open access" flag, **"No full-text"** | Record found; "Peer reviewed", "Open access" flag, **"No full-text"** |
| Full text accessible through the library? | **No** | **No** |
| Actually reviewed? | **No.** Neither the paper nor an abstract was read (the record showed none). | **No.** Same. |
| Remaining limitations | The record says "Please sign in to check if there are additional request options" and offers **Interlibrary Loan**. Both need your sign-in. The "Open access" flag suggests a free copy may exist elsewhere; I did not look, because the task was library access. | Same. The catalogue also lists an SSRN working paper by the same authors with a **different subtitle** ("Tail Risk Evidence from Overnight Market Returns"). It is not the journal article and was **not substituted**. |

**Consequence for the study.**
- Both papers stay cited as **not reviewed**. No claim in the literature review or protocol may rest on them
  beyond their bibliographic existence.
- To close D8, you could sign in and request them through Interlibrary Loan, or tell me whether an
  open-access copy may be used.

## 4. Bootstrap calibration assessment (analysis only; nothing re-run)

### 4.1 Inner B = 999 (calibration) versus B = 10,000 (frozen real run)

**p-value grid.**
- With B = 999 the p-value moves in steps of 0.001; with B = 10,000, in steps of about 0.0001.
- The centered p = (1 + h)/(B + 1) is a valid Monte Carlo p-value when the statistic is pivotal and
  α(B + 1) is a whole number (Davidson & MacKinnon 2000).
- B = 999 satisfies this for every level the calibration checked: 0.05 → 50, 0.01 → 10, 0.002 → 2.
- B = 10,000 gives 100.01 at 1% and 20.002 at 0.2%. Rejection then needs h ≤ 99 (or ≤ 19), which is very
  slightly conservative (by about 10⁻⁶) and never liberal.
- The statistics here are not exactly pivotal. So this guarantees only that finite B adds no size error of
  its own; it says nothing about the bootstrap's approximation error.

**Threshold blurring.** Finite B makes rejection a smooth function of the ideal p (binomial):

| Ideal p | P(reject at 1%), B = 999 | B = 9,999 |
|---|---|---|
| 0.005 | 0.97 | 1.00 |
| 0.008 | 0.72 | 0.98 |
| 0.010 | 0.46 | 0.49 |
| 0.012 | 0.24 | 0.03 |
| 0.015 | 0.07 | 0.00 |

- The blurring is roughly symmetric around 1%. When the ideal p-value is close to uniform near 1%, it leaves
  the rejection rate essentially unchanged to first order.
- **Its main cost is power, not size** (Davidson & MacKinnon 2000).
- So the B = 999 rates are a close but not exact estimate of the B = 10,000 rates. The difference is second
  order and is not quantified.

### 4.2 Interval coverage

- At B = 999 each 99% endpoint rests on about 5 tail replicates, against about 50 at B = 10,000.
- The endpoints are therefore noisier, but the expected coverage of an order-statistic endpoint is about
  nominal.
- Observed coverage for the valid tests was:
  - T1/T2: 99.1–99.3%
  - L1: 99.0–99.3%
  - P1: 98.3–98.4%
  - V1 (descriptive now): 98.2–98.5% outside scenario 2
- The P1 shortfall of about 0.6–0.7 points is more likely finite-sample (n = 1,230) percentile-interval error
  than a B effect. **The two cannot be separated without a re-run** (4.4).

### 4.3 Outer repetitions = 20,000

| Quantity | Monte Carlo SE | 95% half-width | Detects |
|---|---|---|---|
| Rate at 1% (200 expected) | 0.070 pp | ≈0.14 pp | 1.3% vs 1.0% (z ≈ 4); adequate |
| Rate at 0.2% (40 expected) | 0.032 pp | ≈0.06 pp (±31% relative) | Doubling, not a 20% error; adequate for gross faults only |
| 99% coverage | 0.070 pp | ≈0.14 pp | 98.4% vs 99.0%; adequate |

20,000 is adequate for the decisions it supports: detecting miscalibration and sizing the mild P1 excess. It
cannot certify exactness at Holm's 0.2% step.

### 4.4 Proposed additional calibration (NOT run; needs your approval)

| What | Why | Cost |
|---|---|---|
| Re-run scenarios **4 and 8 (P1)** with inner **B = 9,999**, 20,000 reps each, same seed rule; new output file, existing JSON untouched | P1 is the one inferential test that is mildly liberal (1.33% and 1.50% at 1%; Wilson lower bounds above 1%) and under-covers (98.3–98.4%). The re-run would show whether that comes from B (removable by the frozen B = 10,000) or from the method at n = 1,230 (to be disclosed). | Estimated ≈ 4 h on 2 cores (10× the inner work of the 7,290 s run, for 40,000 of its 210,000 reps) |

- The result could only change disclosure text, never a frozen method.
- **No family-wise calibration is proposed.** The four remaining nulls cannot hold in one data-generating
  process (L1's null needs equal per-session variance; the others do not). Holm's guarantee rests on the
  per-test results.

## 5. Test results

| Gate | Result |
|---|---|
| `tests/test_sessions.py`, fast | **128 passed** (130 collected: 106 from v2 plus 24 new; 2 of them are slow), RuntimeWarnings promoted to errors |
| `tests/test_sessions.py`, slow | **2 passed** |
| `scripts/check.py` | ruff, pytest (**248 passed, 2 skipped**), prereg (**11 hashes unchanged**), prepublish, pip-audit, mypy: **all PASS** |
| Skips | The 2 skips are `tests/test_webhook.py:123`, "needs data/mnq_train.csv (not in the repo)". This ran in the cloud copy, which has no data. On your PC, run only `py -m pytest tests/test_sessions.py` (U6). |
| Coverage | `sessions.py` 99% (554 statements, 2 missed); `run_sessions_study.py` 97% (6 missed, the real-data entry points, by design) |

**New tests (24 collected):**
- **U7 guard:** `test_u7_v1_carries_no_inferential_field_and_guard_rejects_one`.
- **Independence of the other four:** `test_u7_other_four_tests_do_not_depend_on_v1`. V1 is shifted until its
  p hits 1/(B+1); every field of T1, T2, P1 and L1 is identical.
- **Holm hand case:** `test_u7_holm_uses_m5_with_v1_slot_fixed_at_one`.
- **Verdict ignores V1:** `test_u7_official_verdict_ignores_every_v1_input`, 15 combinations of V1
  classification × stability. The verdict is identical to the reference.
- **Pipeline check reads only the point estimate:** `test_u7_pipeline_check_is_descriptive_not_inferential`.
- **Protocol and calibration hashes:** `test_u7_protocol_and_calibration_artifacts_preserved`.
- **L4:** four tests (§2).

**Updated tests:**
- The run-family, minimum-size and verdict-exhaustive tests now expect the descriptive V1 fields.
- The pipeline-halt test now uses per-hour RTH variance at a quarter of the overnight level, so the V1 point
  estimate is negative.
- The U2 stability test expects V1 absent.

**Integrity checks:**
- **Verdict versus V1:** proven by the 15-case test and by the code (V1's inputs are not read).
- **Verdict versus O2:** the existing invariance test (randomised, removed and altered O2) still passes.
- **Frozen counts:** `expected_dev` = 1,308 / 1,230 and every MIN_\*, B, seed and block constant are
  unchanged. A diff of `run_sessions_study.py` against report v2 shows only the halt branch and the S9 note.
- **Protocol v4.1:** the hash is unchanged.
- **Data:** the cloud copy has no `data/` folder, and the U6 guard blocks reads under `data/` in every test.
  The PC's pinned data hashes were not touched.

## 6. Remaining statistical limitations

| # | Limitation |
|---|---|
| L1 | P1 is mildly liberal (1.33–1.50% at 1%, 0.32–0.33% at 0.2%) and under-covers (98.3–98.4%). By Holm's union bound the family-wise rate of the four inferential tests can exceed 1% slightly. |
| L2 | T1/T2 are conservative (about 0.3% at 1%), so they have lower power |
| L3 | Calibration used B = 999 and the real run uses 10,000; the difference is second order and unquantified (§4) |
| L5 | No price-limit censoring or missing data inside the Monte Carlo (covered by unit tests only) |
| L6 | Tail regime stability is not assessable for 2020–2022 (U2, accepted) |
| L7 | P1 relies on MNQ volume as the price-discovery proxy |
| L8 | The real-data entry points are untested end to end, by design |
| L10 | V1 inference is unreliable if the two volatility paths are not shared. V1 is now descriptive, but its reported descriptive interval can still be badly over-confident. |
| L11 | The earliest volatility groups (from about late April 2020) rest on four months of overlapping trailing means |

## 7. Unresolved issues (need your decision)

| # | Issue |
|---|---|
| **U8** | Holm with V1's slot fixed at p = 1 and m = 5 (implemented), or drop V1 so m = 4 (looser) |
| **U9** | Pipeline check on the V1 point estimate > 0 (implemented), or remove the halt |
| **L4 wording** | Confirm that "60 prior sessions" means 60 prior trailing means (first 80 sessions unassigned), as implemented |
| **D8** | Sign in for Interlibrary Loan, or allow an open-access copy; until then both papers are "not reviewed" |
| **C-B** | Approve or decline the P1 B = 9,999 re-calibration (§4.4) |
| — | Sign-off and hashing of protocol v4.1 plus this addendum; no real-data run before that |

## 8. Exact files changed (all uncommitted)

| File | Change | Lines | SHA-256 |
|---|---|---|---|
| `nq_bot/sessions.py` | U7 constants, `run_family`, `assert_v1_descriptive_only`, `official_verdict`, `o2_secondary` note | 899 | `9d61fc67db990d39aa9f47bf43f8e24cd1eed8eecba380d396af760b2d6add23` |
| `run_sessions_study.py` | Halt branch (U9), S9 note | 312 | `369fa1618cda6e77def0a343ff755e6e5f7bcec0d5349b56dd2073d37d84ac1a` |
| `tests/test_sessions.py` | 5 tests updated, 10 test functions added (24 collected) | 1,079 | `d5532da6e938264a8d99767d3ee1fd4624219d907711cd2490d9cfdbce9474c0` |
| `docs/SESSIONS_ADDENDUM_U7_L4.md` | New | — | `651599048e3d1934f6dfd5f2d9a13b077b96a45612dddba8b44c58175fbe5a1f` |
| `docs/SESSIONS_RESEARCH_AUDIT_v3.md` | New (this file) | — | — |

**Unchanged:**

| File | SHA-256 |
|---|---|
| Protocol v4.1 | `716e0003…37506021` |
| `SESSIONS_CALIBRATION.json` | `e32b7992…5164da27` |
| `scripts/sessions_calibration.py` | `ef815568…00e6b3ff` |
| `tests/sessions_synth.py` | `5536e067…e51f1ce5` |
| `tests/test_tooling.py` | `b204db94…` |
| `pytest.ini` | `70e05743…` |

Report v2 and every other document are also unchanged.

## 9. Confirmation

- No actual study result was calculated.
- No real NQ or MNQ price was loaded or read.
- No new data was bought.
- Nothing was committed or pushed.
- No live trading, broker connection or strategy code was touched.

**Stopped here for independent review.** The actual-data analysis has not started.

**Reference:** Davidson, R. and MacKinnon, J. G. (2000), "Bootstrap tests: how many bootstraps?",
*Econometric Reviews* 19(1), 55–68, doi:10.1080/07474930008800459.
