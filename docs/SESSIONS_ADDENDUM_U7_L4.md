# Addendum to DRAFT protocol v4.1: decisions U7, U8 and L4 (implementation clarifications)

Written 2026-11-12; revision 2 (15:20 CT) recorded U8, L4 and the U9 conflict; **revision 3 (22:00 CT): U9 resolved by protocol v4.2 (`DRAFT_PREREG_SESSIONS_v4.2_awaiting_signoff.md`), L4 session 81 confirmed.** The protocol text itself is now v4.2; this addendum keeps the implementation notes. Status: **draft, awaiting review.** Not signed, not hashed, not in `PREREG_HASH.txt`.

- The protocol file `DRAFT_PREREG_SESSIONS_awaiting_signoff.md` is **unchanged**: SHA-256 `716e0003…37506021`,
  checked before and after this work.
- This addendum records two decisions by Ethan on 2026-11-12, and how the code applies them.
- It changes no hypothesis, sample rule, exclusion, count, threshold, statistic, block length, B, seed or
  minimum size. It changes what one test is allowed to mean.

## A1. Decision U7: V1 is descriptive only (option 3 / option (c) in report v2)

**The reason.** Calibration scenario 2 has volatility clustering that evolves independently in the overnight
and RTH series (GARCH(1,1), a = 0.08, b = 0.90). Under it, the V1 bootstrap test rejected a true null in
**19.42%** of 20,000 repetitions at nominal 1% (3,884 rejections; Wilson 95% 18.88–19.97%). Its 99% interval
covered **80.1%**. The original results stay in `SESSIONS_CALIBRATION.json` (SHA-256 `e32b7992…5164da27`,
unchanged).

**What V1 keeps:**
1. Its point estimate: the log per-hour variance ratio, RTH over overnight.
2. Its effect sizes: the ratio, and the per-hour RTH and overnight variances.
3. Nothing else: since protocol v4.2 V1 is not a pipeline condition (A2 below).

**What changes:**
- V1's p-value and its 99% and 99.8% intervals are still computed. They are reported only under the keys
  `p_two_sided_descriptive_only`, `ci99_descriptive_only` and `ci998_descriptive_only`, with a disclosure note
  that cites the 19.4% result.
- V1 has no Holm-adjusted p, no rejection flag and no BH q-value. Its classification is always
  "descriptive only (decision U7)". A guard (`assert_v1_descriptive_only`) fails the run if any inferential
  V1 field appears.
- **No substitute method.** V1 has no replacement test, interval or block rule.
- **Official verdict.** V1's line is a fixed text: "NOT A CONFIRMATORY CLAIM - descriptive estimate only
  (decision U7); reported as a pipeline integrity check". The function never reads V1's classification or
  stability.
- **Regime stability** is computed only for established claims, so V1 is no longer assessed.
- **O2 and sensitivity S9** still report V1's descriptive p-values (O2 one-sided, S9 by block length), each
  with the same disclosure note. Neither can reach the verdict.

**The other four tests (T1, T2, P1, L1) are unchanged.** Their statistics, bootstrap, p-values, intervals,
classification rules and Holm thresholds are as before.

**Holm: decision U8 (approved 2026-11-12).**

- Holm keeps all **five** slots (m = 5).
- V1's slot receives the fixed value **1.0**. This value is an **administrative placeholder**:
  - it is **not an observed V1 p-value** (the observed V1 p is never an input to the correction);
  - V1 remains **descriptive only** and **cannot establish statistical significance**;
  - T1, T2, P1 and L1 **keep their existing definitions**;
  - keeping five slots for four inferential tests is **intentionally conservative**.
- Thresholds in step-down order are unchanged: 0.01/5 = 0.002, 0.0025, 0.0033, 0.005. V1 is never rejected.
- Code: `holm_with_placeholder` (the only route into Holm from `run_family`), constants `HOLM_PLACEHOLDER_P`
  and `HOLM_PLACEHOLDER_NOTE`; the note is written into every result file.
- Test `test_u8_v1_cannot_change_holm_adjusted_results_of_the_other_four`: for 2,000 random p-vectors of the
  four tests and seven observed V1 values from 10⁻⁹ to 1, the four adjusted p-values and decisions are always
  identical to Holm with the placeholder.

## A2. Pipeline check: resolved by protocol v4.2 (U9 approved 2026-11-12)

v4.1 §7 said: "Pipeline check: V1 not established in development → halt, and report a data or code fault", and
§6.1 called V1 a "Calibration check". Under U7 V1 can never be established, so that rule would halt every run.
**v4.2 removes it** (v4.2 §7 and Appendix D, part 5).

Implementation:
- `run_dev` no longer has any V1-based branch. A negative V1 is reported; every claim, the descriptives, the
  sensitivities and the official verdict are still produced (`test_v42_nonpositive_v1_is_reported_and_the_run_completes`).
- `run_family` reports `v1_point_estimate_positive_reported_only` and nothing acts on it
  (`test_v42_no_v1_outcome_halt_exists_in_the_code`).
- All data-integrity and computation-failure halts are kept (listed in v4.2 §7).
- The interim U9 variant (halt if V1 ≤ 0) of audits v3/v4 is withdrawn.

## A3. Decision L4: minimum history of 60 prior averages for volatility groups (approved 2026-11-12)

**Rule (unchanged from v4.1 §6.2, now frozen):**
- `T[d]` = mean RTH realized variance of the previous 20 analysis sessions.
- The cut-offs are the 1/3 and 2/3 quantiles of the earlier `T` values.
- A group is assigned only once **at least 60 earlier `T` values** exist.
- Constants: `TERCILE_WINDOW = 20`, `TERCILE_MIN_HISTORY = 60`.

**Clarification of "60 prior sessions" (zero-based code indices):**
- The implemented minimum is 60 earlier *trailing means*, not 60 earlier sessions.
- `T` itself needs 20 earlier sessions, so **sessions 0–79 (the first 80) receive no group**. The first 60
  sessions are therefore unassigned, as required.
- **Session 80 (the 81st) is the first assigned.** Its cut-offs come from `T[20..79]`, which uses RV of
  sessions 0–78.
- A test checks this exactly: `test_l4_first_eligible_assignment_and_boundaries`.

**One-based numbering (decision L4; session 81 confirmed by Ethan 2026-11-12 21:46 CT):**

| One-based session s | 20-session average T_s | Prior averages available (T_21 … T_{s−1}) | Group |
|---|---|---|---|
| 1–20 | undefined (fewer than 20 earlier sessions) | 0 | none |
| 21 | mean of sessions 1–20 | 0 | none |
| 80 | mean of sessions 60–79 | **59** (T_21 … T_79) | **none** |
| **81** | mean of sessions 61–80 | **60** (T_21 … T_80, built from sessions 1–79) | **first assigned** |

With the fixed minimum of **60 prior averages**, the first eligible session is **81 in one-based numbering** (index 80 in zero-based code numbering). Confirmed; written into protocol v4.2 §6.2.
Test: `test_l4_one_based_numbering_of_the_warm_up`.

**Why 60, and what it does and does not buy:**
1. **It is a descriptive split only.** No test, interval or verdict uses the groups, so imprecise early
   cut-offs cannot change an inferential result.
2. **Precision.** For independent values, the sampling error of the 1/3 quantile in probability terms is
   √(⅓·⅔/60) ≈ 0.061.
   - The first cut-off therefore sits roughly between the 27th and 39th percentile of the history (±1 SE).
   - By 600 values the SE is about 0.019.
   - The window expands, so cut-offs settle as history grows.
3. **The honest limit.** Consecutive `T` values share 19 of 20 sessions.
   - The 60 values therefore span only about 79 sessions (about four months).
   - They carry roughly the information of three or four non-overlapping windows.
   - So 60 does **not** make the earliest cut-offs precise. It only guarantees they rest on more than one
     window of history.
4. **Cost.**
   - 80 of the 1,230 development sessions (6.5%) are unassigned.
   - A larger minimum would discard more sessions; a smaller one would base cut-offs on less than two
     windows.
5. **Foreseeable consequence, from the public calendar and not from the data.**
   - The development window starts 2020-01-02.
   - The first cut-offs (session 80, about late April 2020) are built from trailing means covering the
     January–April 2020, including the March 2020 market turmoil.
   - Groups for mid-2020 sessions may therefore lean "low" until the history broadens. This will be
     disclosed with the results.
6. **Not tuned.**
   - 60 was chosen before any real data was loaded and is now frozen.
   - No real results were used, and none will be used, to revisit it.
   - It changes no sample count. The frozen counts (1,308 eligible, 1,230 primary) are computed before and
     independently of groups.
