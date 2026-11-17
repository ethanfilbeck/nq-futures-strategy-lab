# Independent review guide, v1: overnight vs regular-session study (protocol DRAFT v4.2)

Prepared 2026-11-12 for an independent reviewer. Revision 2 (22:45 CT): adds the Holm wording discrepancy section (§4) and checklist item H-d; nothing else changed.

**Status:**
- **Protocol v4.2 is an unsigned draft. It has not been approved.**
- No real price has been loaded and no study result exists.
- Passing the synthetic tests shows that the code does what the protocol says on generated data. **It does
  not establish that any statistical procedure is valid for the real data.**

**Evidence labels:**
- **[CODE]** verified by code inspection;
- **[SYNTH]** verified by synthetic testing;
- **[PRIOR]** reported by previous work and not independently re-verified;
- **[OPEN]** unresolved.

**Companions:**
- `INDEPENDENT_REVIEW_PACKAGE_AUDIT_v1.md`: package checksums and discrepancies PD-1 to PD-13.
- `REMAINING_LIMITATIONS_v1.md`.
- The package itself: `docs/review_package_sessions_v4.2/`.

---

## 1. What the study measures

Using 1-minute MNQ (Micro E-mini Nasdaq-100) futures bars, 2020-01-02 → 2025-06-30 (development) and
2025-07-01 → 2026-10-30 (holdout), it describes how the **overnight** period (ON, the previous session's
16:00 ET close to today's 09:30 open) differs from the **regular session** (RTH, 09:30 → 16:00 ET).

| ID | Quantity | Role |
|---|---|---|
| V1 | Log ratio of per-hour variance, RTH over ON | **Descriptive only** (U7) |
| T1 / T2 | Difference in Hill tail index (lower / upper tail) of volatility-scaled returns, ON minus RTH | Inferential |
| P1 | Δ_P = 100·(WPC_ON − VS_ON): weighted price contribution of the overnight period minus its volume share | Inferential, **with an unresolved calibration problem** (§5) |
| L1 | Δp: how much more often \|ON\| > \|RTH\| on the top 5% \|close-to-close\| days than on other days | Inferential |

Alongside these: descriptive distributions, value at risk and expected shortfall, realized-variance shares,
the hourly *volatility* profile, and volatility-group splits (protocol §6.2).

## 2. What it explicitly does not do

From protocol §2, §6.2 and §6.3; enforced by `assert_no_forbidden` [CODE][SYNTH]:
- **No trading rule, signal, position, strategy return, Sharpe ratio or profitability statement.**
- **No hourly mean returns**, no correlation, covariance or regression of ON with RTH, no Var(CC), no RTH
  statistic conditioned on ON, and no half-hour returns. These overlap with earlier, rejected trading
  hypotheses (H1–H3, H7).
- **No confirmatory verdict:** the official verdict is fixed at INCONCLUSIVE (D2-a), because no holdout
  session is unexposed to earlier experiments.
- **No new data purchases, no broker or account connection, no live execution.** The study's code imports
  no broker, webhook or live module (§9).

## 3. Protocol history: v4.1 → v4.2

| Version | File | SHA-256 | Status |
|---|---|---|---|
| v4.1 | `docs/DRAFT_PREREG_SESSIONS_awaiting_signoff.md` (package: `protocol/…v4.1…`) | `716e00037ab4…37506021` | Historical, preserved unchanged |
| v4.2 | `docs/DRAFT_PREREG_SESSIONS_v4.2_awaiting_signoff.md` | `99b54fd35718…ecebea` | **Current unsigned draft** |

- Earlier versions (v2 → v4.1) are logged in Appendix D, parts 1–4.
- v4.2 adds decisions U7, U8, U9, L4, P1 and the D8 status (Appendix D, part 5). The full diff is in
  `protocol/protocol_v4.1_to_v4.2.diff`.
- **No sample count, exclusion, threshold, minimum size, B, seed, block length, or definition of T1, T2, P1 or
  L1 changed** [CODE]: diff inspection and a count of every frozen number, audit v5 §2.

### Why U7 required the U9 amendment

- v4.1 §7: "**Pipeline check:** V1 not established in development → halt, and report a data or code fault."
- "Established" means a Holm-adjusted p ≤ 0.01 in the literature direction.
- U7 then made V1's p-value descriptive only, so V1 can **never** be established.
- Read literally, v4.1 §7 would halt every development run and suppress every other result.
- Any substitute halt based on V1's value (such as "halt if V1 ≤ 0", tried in an interim build and not
  approved) would still let V1's outcome decide what is reported.
- **v4.2 removes the V1 halt** and keeps every data-integrity and computation-failure halt (§9 below).

### Why V1 is descriptive only

Synthetic calibration scenario 2 has GARCH(1,1) volatility clustering that evolves *independently* in the
ON and RTH series. Under it, V1's bootstrap test:
- rejected a true null in **19.42%** of 20,000 repetitions at nominal 1% (Wilson 95% 18.88–19.97%);
- had 99% intervals that covered only **80.1%**.

Longer blocks (40, 100) only partly helped (13.6%, 10.6%). With a *shared* volatility path (scenario 10),
V1 was 1.64% [SYNTH, PRIOR run: `SESSIONS_CALIBRATION.json`].

Which regime the real data resembles cannot be known without examining it. V1 therefore keeps its estimate
and effect sizes, but its p-value and intervals are labelled descriptive and never reach a decision.

## 4. The five-slot Holm correction

**How it works** [CODE][SYNTH]:
- `holm_with_placeholder` builds the family {V1, T1, T2, P1, L1}. **V1's entry is the constant 1.0.** This is
  an administrative placeholder, not V1's observed p, which is never an input.
- It then applies standard Holm at α = 0.01 with m = 5:
  - sort the p-values ascending;
  - reject while p₍ᵢ₎ ≤ 0.01/(5 − i + 1), stopping at the first failure;
  - p̃₍ᵢ₎ = max over j ≤ i of min(1, (5 − j + 1)·p₍ⱼ₎).
- Because V1's 1.0 sorts last, the four inferential tests face 0.002, 0.0025, 0.0033 and 0.005 by their own
  rank, and V1 is never rejected.
- Keeping five slots for four tests is **intentionally conservative**: with m = 4 the first threshold would be
  0.0025.

### Holm wording discrepancy: please rule on it (audit PD-4)

**What v4.2 says** (§7, Holm bullet, U8; v4.2 is **not edited**): T1, T2, P1 and L1 "face the same thresholds
as in v4.1 whenever V1 was not significant (0.002, 0.0025, 0.0033, 0.005 in step-down order)". The addendum
§A1 and audit v5 §2 repeat this.

**What the implementation does** (`holm_with_placeholder`): V1's slot is always 1.0, so V1 sorts last, and the
four tests take ranks 1–4 among themselves.

**The difference:**

| Aspect | v4.1 (V1's observed p in the family) | v4.2 (placeholder 1.0) |
|---|---|---|
| **Rejection decisions** of T1, T2, P1, L1 when V1 is not significant | — | **Always identical** |
| **Threshold faced** by a test ranked *after* V1 in v4.1 | e.g. 0.0033 | moves up one step, e.g. 0.0025 |
| **Holm-adjusted p̃** of the four | includes V1's term in the running maximum and a different multiplier | can differ |

**Why the decisions are identical (proof sketch).**
- Suppose V1 sits at rank *i* and is not rejected under v4.1. Then V1's p exceeds 0.01/(5 − i + 1).
- Every test ranked after V1 has a p at least that large.
- In v4.2 such a test moves up to rank *i* and faces exactly that threshold, so it is still not rejected.
- Tests ranked before V1 keep their ranks and thresholds.

**Numerical check** [SYNTH], reproducible with `python scripts/review/holm_v41_v42_comparison.py` (seed 1; uses the project's own `holm` and `holm_with_placeholder`):
- 200,000 random five-test p-vectors, half uniform on [0, 0.02] and half on [0, 1];
- **188,433** had V1 not rejected under v4.1;
- **0** differed in any rejection decision;
- **69,935 (37%)** differed in at least one adjusted p-value of the four.

**Reviewer question H-d:** does v4.2's wording accurately represent the implementation? The rejection
decisions agree; the stated "same thresholds" does not hold for tests ranked after V1, and the reported
adjusted p-values can differ from what v4.1 would have printed.
- If the wording is inaccurate, any correction belongs to a **future protocol version approved by Ethan**. No
  v4.3 has been created.
- The implementation itself is not in question: it follows v4.2's rule ("V1's slot receives the fixed
  administrative placeholder p = 1.0").

### Why Holm does not repair improperly calibrated p-values

- Holm controls the family-wise error rate at α **only if each true-null p-value is valid**:
  P(p ≤ u) ≤ u under its null, for the thresholds used.
- Holm is a rule about *which* thresholds to compare valid p-values against. It does not change the p-values
  themselves.
- If a test rejects its true null more often than nominal, Holm passes that excess straight through. For
  example, P1 at Holm's first step:
  - nominal rate 0.2%;
  - observed **0.33–0.34%** in synthetic data.
- Two consequences:
  - **No verified 1% family-wise error rate is claimed for the four tests** (v4.2 §7.2).
  - P1's rate at Holm's later thresholds (0.0025, 0.0033, 0.005) **was not measured**. Calibration recorded
    only 0.05, 0.01 and 0.002.
- The overall family-wise rate also depends on the dependence between tests and on which nulls are true.
  Both are unknown for the real data. **The family-wise error rate is therefore unresolved, not bounded by a
  verified number.**

## 5. Why P1 remains statistically unresolved

**Observed under P1's true null** [SYNTH; `SESSIONS_CALIBRATION.json` and
`SESSIONS_CALIBRATION_P1_B9999.json`, 20,000 repetitions each, n = 1,230, mean block 20]:

| Scenario | 1% level, B = 999 | 1% level, B = 9,999 | 0.2% level, B = 999 / 9,999 | 99% coverage, B = 999 / 9,999 |
|---|---|---|---|---|
| 4: iid Gaussian | 1.33% (1.18–1.50) | 1.34% (1.19–1.50) | 0.33% / 0.34% | 98.38% / 98.59% |
| 8: common GARCH volatility | 1.50% (1.34–1.68) | 1.50% (1.34–1.68) | 0.33% / 0.33% | 98.31% / 98.48% |

**What this shows:**
- The paired comparison shows the excess is **not** caused by the number of resamples:
  - McNemar |z| ≤ 1.2 for rejections;
  - coverage improved by about 0.2 points (z = 3.5–4.4) but stays below 99%.
- **It belongs to the method at this sample size.**

**Why the excess occurs is not established.** Hypotheses for the reviewer, none tested:
1. WPC_ON = Σ sign(CC)·ON / Σ|CC| is a **ratio statistic** containing a sign discontinuity. The centered
   ("basic") bootstrap test is not studentized, so it can understate the sampling spread of a non-pivotal,
   possibly skewed statistic.
2. The **stationary block bootstrap** with mean block 20 is used even in the iid scenario. Block resampling
   adds its own finite-sample bias in variance estimation.
3. **Centering choice:** the null distribution is taken as θ* − θ̂. Asymmetry around θ̂ can make two-sided
   tails too thin.

**Evidence the reviewer could ask for** (each would be new synthetic work, run only with approval, and
changing no frozen method):
- the Monte Carlo variance of θ̂ against the mean bootstrap variance;
- rejection rates at 0.0025, 0.0033 and 0.005;
- behaviour at several n;
- a studentized or bias-corrected comparison, as a diagnostic only.

**Before P1 could become confirmatory** (reviewer to decide what is sufficient):
1. An explanation of the over-rejection.
2. A method, pre-registered in a new protocol version before any data is seen, whose rejection rate is
   within Monte Carlo error of nominal at every Holm threshold, and whose coverage is about 99%, across
   scenarios including heavy tails, volume variability and price-limit censoring.
3. Independent review of that calibration.
4. Under D2-a, **genuinely unexposed evaluation data (O3).** Nothing in this phase is confirmatory for any test.

**Current rule (v4.2 §7.2):**
- P1 results carry a calibration note.
- A development "established" label for P1 **is not established confirmatory evidence** until P1 is
  independently reviewed.
- Whether P1 should be **descriptive only**, like V1, is a reviewer question. Changing it would require a new
  protocol version.

## 6. L4: volatility groups and session 81

Protocol v4.2 §6.2; `vol_tercile_membership` [CODE][SYNTH]:
- **Trailing mean.** Session *s* (one-based, in time order within a period) has T_s = mean RTH realized
  variance of sessions *s−20 … s−1*. T_s exists for *s* ≥ 21 and never uses session *s*.
- **Cut-offs.** These are the 1/3 and 2/3 quantiles of the earlier values T_21 … T_{s−1}, an expanding window.
  The group is low if T_s ≤ c1, middle if T_s ≤ c2, otherwise high; ties go to the lower group.
- **Warm-up.** At least **60 prior averages** are required. Session *s* has *s − 21* prior averages, so:
  - sessions 1–80 are unassigned (session 80 has 59);
  - **session 81 is the first assigned**; its cut-offs use T_21 … T_80, built from sessions 1–79.
- The minimum of 60 is frozen.
- **Tests:**
  - `test_l4_one_based_numbering_of_the_warm_up`;
  - `test_l4_first_eligible_assignment_and_boundaries`;
  - `test_l4_short_samples_and_no_look_ahead_at_the_boundary`;
  - `test_volatility_groups_depend_only_on_earlier_sessions`, which shows future data cannot change an
    earlier group;
  - `test_l4_assigned_count_is_n_minus_80`;
  - `test_l4_constants_frozen`.
- The groups feed **no test**; they only split descriptive statistics.

## 7. Why O2 cannot change the official verdict

O2 is a secondary, restricted holdout population: 185 "B only" Monday, Thursday and Friday sessions, exposed
through correlated-market experiments.

**Protections** [CODE][SYNTH]:
1. `official_verdict(dev_classification, dev_stability)` has **no parameter** through which O2 or any holdout
   value can enter. It returns INCONCLUSIVE for the phase whatever its inputs.
2. `run_holdout` computes and **writes the verdict file first**, from the development results only, before
   loading holdout bars. Only then does it compute O2.
3. After O2, it re-renders the verdict and raises `DataIntegrityError` if the text differs (l. 282–283;
   untested, because it cannot trigger by construction).
4. `test_o2_cannot_change_the_official_verdict_removed_randomised_altered`: the verdict file is identical with
   O2 prices randomised. With O2 removed from the inventory, or its membership altered, the run is refused
   after the verdict was written, and the verdict is unchanged.
5. Protocol §8 lists six binding prohibitions on how O2 may be used or described.

## 8. Frozen sample counts

| Count | Value | Status |
|---|---|---|
| Development sessions with RTH | 1,417 | [PRIOR] from timestamps (`reconcile_counts.py`) |
| Development eligible (E1–E5) | **1,308** (1,417 − 46 − 39 − 0 − 21 − 3) | [PRIOR]; arithmetic re-checked [CODE]; runner gate [CODE] |
| Development primary (E6) | **1,230** (1,308 − 78; E6 standalone 86 minus 8 already removed by E4) | [PRIOR]; arithmetic re-checked; runner gate. **Not re-derived from the data files in this review.** |
| V1 sub-sample (development) | 983 | [PRIOR] |
| Holdout sessions with RTH | **346** | [CODE] 346 rows in the hashed inventory CSV |
| Holdout eligible | **318** (−12 E1, −10 E2, −5 E4, −1 E5) | [CODE] recounted from the CSV `excluded_by` column |
| Holdout primary | **297** (318 − 21 E6) | [CODE] E6 re-derived from `family3.HOLDOUT_FOMC_DAYS` and the CSV: the 21 eligible E6 sessions are exactly the 21 A_H8 sessions; 2026-06-17 is already E4 |
| O2 | **185** (Mon 59 + Thu 62 + Fri 64 "B only") | [CODE] recounted from the CSV; runner gate |
| Earlier labels 333 / 347 | Corrected history (protocol §5.2a) | [PRIOR] |

The runner refuses to proceed if any computed count differs from these (`check_counts`, `Gate.reconcile_count`).

## 9. Software architecture and safety

| Layer | Where | What it does | Evidence |
|---|---|---|---|
| Freeze and pin checks | `run_sessions_study.require_frozen_protocol`, `verify_pins` → `sessions.verify_hashes` | Refuses unless `docs/PREREG_SESSIONS.md`'s hash is in `PREREG_HASH.txt` (see PD-9), and unless the 2 data files, the roll map, `family3.py` and the exposure CSV match pinned SHA-256 values | [CODE][SYNTH] `test_runner_refuses_on_hash_mismatch_and_count_mismatch` |
| Ingestion boundary | `sessions.read_bars` (the only reader of price files); `run_sessions_study.load` | Reads `timestamp, open, high, low, close, volume` from local CSVs only. Concatenates raw bars, de-duplicates by timestamp, and **raises** if duplicates disagree. No network access. | [CODE] |
| Bar integrity | `integrity.Gate.bars` then `sessions.check_bars` | tz-aware, strictly increasing, unique, no NaN, high/low consistent, positive prices, **no zero-volume bar**; failure raises `DataIntegrityError` | [CODE][SYNTH] |
| Session classification | `session_table`, `build_sample`, `exclusion_counts`, `analysis_set`, `v1_mask` | CME session = date(ET + 6 h); O(d) and C(d) from the 09:30–09:35 and 15:55–16:00 windows; exclusions E1–E6 applied in order; DST-spanning session raises | [CODE][SYNTH] |
| Count gates | `check_counts`, O2 membership checks in `run_holdout` | Frozen counts and CSV membership must match | [CODE][SYNTH] |
| Statistics | `ewma_scale`, `hill`, `wpc_on`, `vs_on`, `extreme_mask`, `point_stats`, `stationary_indices`, `bootstrap_family`, `centered_p`, `percentile_ci`, `effect_sizes`, `classify` | Protocol §6–7 | [CODE][SYNTH] numerical; **validity [OPEN]** |
| Multiple testing | `holm_with_placeholder` → `holm`; `bh_q` (information only) | §4 above | [CODE][SYNTH] |
| V1 restriction | `assert_v1_descriptive_only`; `official_verdict` fixed V1 label | §3 | [CODE][SYNTH] |
| Outputs | `run_dev` / `run_holdout` → `runs/sessions_dev.json`, `runs/sessions_holdout.json`, `runs/sessions_official_verdict.txt` via `_write`; `assert_no_forbidden` on every result | Run-once locks; holdout only after development results are committed (`git_is_committed`) | [CODE][SYNTH] |
| Error handling | `DataIntegrityError`, `InsufficientSample`, `ForbiddenQuantityError`, `Refused` (a `SystemExit`), `ValueError` (non-finite replicate or p; B too small; wrong Holm family), explicit `AssertionError` (V1 guard; raised, not `assert`, so it survives `python -O`) | No caller catches them; any failure stops the run | [CODE] |
| Synthetic vs real separation | `tests/sessions_synth.py` generates bars into temporary folders. An autouse fixture `_no_real_data` fails any `open` under the project's `data/`. Calibration scripts generate arrays in memory. | [CODE][SYNTH]; limits in audit SW-3 |
| Coverage | `sessions.py` 99%; `run_sessions_study.py` 97% | Uncovered: real-data entry points and defensive branches (audit SW-2) | [SYNTH] |

**No broker, order, live trading or credentials** [CODE, by runtime check]:
- Importing `run_sessions_study` loads only these project modules: `nq_bot`, `nq_bot.sessions`,
  `nq_bot.integrity`, `nq_bot.rolls`, `nq_bot.data`, `nq_bot.family3`.
- **No broker client, web framework or HTTP client is imported.** `socket` is loaded by numpy and pandas
  themselves, not by project code.
- The repository does contain `nq_bot/broker/`, `live.py` and `webhook.py` from earlier, separate work. **The
  research pipeline imports none of them.**
- `nq_bot/data.py` defines `fetch_databento`, which would need an API key, but the pipeline never calls it.
- The research pipeline requires **no credentials, broker connection or account access.**

## 10. Reviewer checklist

**Statistics: P1**

| # | Question | Inspect |
|---|---|---|
| P1-a | Why does P1 reject 1.33–1.50% at nominal 1%? Is the cause the statistic (ratio, sign discontinuity), the centered non-studentized test, or the block bootstrap? | `sessions.wpc_on`, `vs_on`, `_boot_p1`, `centered_p`, `stationary_indices`; `scripts/sessions_calibration.py` `make()` scenarios 4 and 8; `SESSIONS_CALIBRATION_P1_B9999.json` |
| P1-b | Is the underlying method valid for MNQ-like data at n = 1,230? | Protocol v4.2 §6.1 "P1 exact specification", §7, §7.2 |
| P1-c | Is 98.3–98.6% coverage of the 99% interval acceptable? | `percentile_ci`; calibration JSONs |
| P1-d | Should P1 be descriptive only, like V1? (That would need a new protocol version.) | §7.2; `official_verdict` |
| P1-e | What evidence is required before P1 could be confirmatory? | §5 above |

**Statistics: V1**

| # | Question | Inspect |
|---|---|---|
| V1-a | Is the descriptive-only restriction enforced in **every** path: development family, stability, verdict, O2, S9, halts? | `run_family` (V1 branch), `assert_v1_descriptive_only`, `stability` (established claims only), `official_verdict` (V1 inputs not read), `o2_secondary` (calibration note), `run_sessions_study.sensitivities` (`note_V1`), `run_dev` (no V1 halt) |
| V1-b | Can V1 change any other result or the verdict? | `test_u7_other_four_tests_do_not_depend_on_v1`, `test_u7_official_verdict_ignores_every_v1_input`, `test_v42_nonpositive_v1_is_reported_and_the_run_completes` |

**Statistics: Holm**

| # | Question | Inspect |
|---|---|---|
| H-a | Is the five-slot step-down correct, including the adjusted p-values and ties? | `sessions.holm`, `holm_with_placeholder`; `test_u8_thresholds_are_the_frozen_five_slot_ones`; `test_holm_hand_example_exactly`; `test_holm_stops_at_first_failure_and_rejects_iff_adjusted_below_alpha` |
| H-b | Is the placeholder applied consistently, with no other route into Holm? | `run_family` (the only caller); `test_u8_run_family_uses_the_placeholder_and_documents_it`; `test_u8_v1_cannot_change_holm_adjusted_results_of_the_other_four` |
| H-c | Is the remaining family-wise uncertainty described accurately (§4)? | v4.2 §7.2; `FWER_NOTE` in `sessions.py` |
| **H-d** | **Does v4.2's sentence "face the same thresholds as in v4.1 whenever V1 was not significant" accurately represent the implementation, given identical rejection decisions but different adjusted p-values (37% of 188,433 cases)?** | v4.2 §7 Holm bullet; `holm`, `holm_with_placeholder`; §4 above; audit PD-4 |

**Statistics: synthetic calibration**

| # | Question | Inspect |
|---|---|---|
| C-a | Do scenarios 1–12 represent the relevant data problems? They lack censoring, missing bars, roll jumps, intraday seasonality and volume variation (scenarios 4 and 8 use constant volume). | `scripts/sessions_calibration.py` `make()` |
| C-b | Are 20,000 repetitions adequate? About ±0.14 points at 1% and ±31% relative at 0.2%. | audit v3 §4.3 |
| C-c | Is the uncertainty communicated correctly (Wilson intervals; no claim beyond measured levels)? | Calibration JSONs; v4.2 §7.2 |

**Design, counts, verdict**

| # | Question | Inspect |
|---|---|---|
| D-a | Are the exclusions E1–E6 and the counts correct? Development counts can be re-derived with `scripts/sessions_preflight/reconcile_counts.py` (timestamps only). | Protocol §5; `build_sample`; §8 above |
| D-b | Is O2 isolated from the verdict? | §7 above |
| D-c | Are T1's expected direction (from Riedel & Wagner) and P1's context adequately sourced, given D8? | `LITERATURE_SESSIONS.md`; limitations L-D8 |
| D-d | Is the L4 warm-up appropriate? | §6 above |

## 11. Unresolved limitations

The full list, with evidence status, is in `REMAINING_LIMITATIONS_v1.md`. The most important:
- P1's calibration;
- the unverified family-wise error rate;
- V1's unreliable descriptive interval;
- calibration scenario realism;
- development counts not independently re-derived;
- both literature sources unreviewed;
- real-data entry points untested end to end;
- the protocol unsigned.
