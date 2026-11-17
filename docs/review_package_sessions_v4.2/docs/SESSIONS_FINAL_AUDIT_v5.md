# Overnight vs regular-session study: final audit v5 and independent-review preparation

Written 2026-11-12 ~22:30 CT. **Synthetic data only.**
- No real NQ or MNQ price was loaded, and no study result was calculated.
- No trading account or broker was connected. Nothing was committed or pushed.

This audit covers the decisions of 21:46 CT: protocol v4.2 (U9), L4 session 81, the P1 limitation, and the
nine independent-review preparation checks. It supersedes audit v4 for these items. Every earlier audit,
report and calibration file is kept unchanged.

---

## 1. Protocol v4.2 (U9 approved)

**Files:**

| File | Role | SHA-256 |
|---|---|---|
| `DRAFT_PREREG_SESSIONS_awaiting_signoff.md` | **v4.1, preserved unchanged as the historical record** | `716e00037ab4d7e20b9f9a44a0af6a146e646f1f631101470a2c8ceb37506021` |
| `DRAFT_PREREG_SESSIONS_v4.2_awaiting_signoff.md` | **v4.2, new.** Not signed, not hashed into `PREREG_HASH.txt` | `99b54fd3571885baae6d58677513dbc43327c6731242914ebd0fe936afecebea` |
| `protocol_v4.1_to_v4.2.diff` | Full unified diff (in the review package) | — |

**Why v4.1 became incompatible with U7:**
- v4.1 §7 says: "**Pipeline check:** V1 not established in development → halt, and report a data or code
  fault". §6.1 calls V1 a "Calibration check".
- "Established" needs a Holm-adjusted p ≤ 0.01. U7 forbids V1's p-value from ever establishing significance,
  so V1 can never be established.
- Read literally, v4.1 would therefore halt every development run and suppress every other result.
- Any repair that kept a V1-based halt would let V1's outcome decide what gets reported, which U7 and U9
  forbid.

**How v4.2 meets the seven requirements:**

| # | Requirement | v4.2 text | Code / test |
|---|---|---|---|
| 1 | V1 does not decide whether the pipeline continues | §7: v4.1 pipeline check struck through, "Removed in v4.2 (U9)" | `run_dev` has no V1 branch. `test_v42_nonpositive_v1_is_reported_and_the_run_completes` (negative V1 → full run, verdict written); `test_v42_no_v1_outcome_halt_exists_in_the_code` |
| 2 | V1 descriptive only | §6.1 V1 row; §7 classification and effect sizes; §0 U7 | `assert_v1_descriptive_only` guard; `test_u7_v1_carries_no_inferential_field_and_guard_rejects_one` |
| 3 | V1 cannot establish significance | §7 Holm placeholder; classification is fixed as "descriptive only" | V1 never receives `p_holm` or `holm_reject`; Holm never rejects V1 (U8 tests) |
| 4 | V1 cannot influence the official verdict | §7 verdict: fixed V1 label; the function does not read V1's inputs | `test_u7_official_verdict_ignores_every_v1_input` (15 cases) |
| 5 | Integrity and computation halts preserved | §7 lists them: hash mismatches, bar-integrity gate, frozen counts, O2 CSV membership, minimum sizes, non-finite replicates, B guard, forbidden quantities, run-once and commit locks | Unchanged code paths; their existing tests pass (§8) |
| 6 | Five-slot Holm with placeholder 1.0 | §7 Holm bullet; §7.1 Holm row | `holm_with_placeholder`; three U8 tests |
| 7 | Other four tests unchanged | Definitions and thresholds untouched (see §2) | `test_u7_other_four_tests_do_not_depend_on_v1` |

**Change log:** v4.2 Appendix D, part 5 (10 items).

**Code changes this round:**
- **`sessions.py`:**
  - the pipeline flag is renamed `v1_point_estimate_positive_reported_only` and nothing acts on it;
  - added `P1_CALIBRATION_NOTE`, `FWER_NOTE` and `CALIBRATION_DISCLOSURES`;
  - P1 entries carry the note;
  - `official_verdict` returns the disclosures and `render_verdict` prints them. **No label or classification
    rule changed.**
- **`run_sessions_study.py`:**
  - the V1 halt branch is removed;
  - the result `protocol` field is set to "v4.2";
  - the holdout's defensive refusal message no longer mentions a halt.

## 2. Every v4.2 amendment checked against v4.1

The amendments were made by a script with 19 exact-match replacements; each target occurred exactly once in
v4.1. The diff has 11 hunks.

**Lines removed from v4.1, all replaced by amended text:**
- title;
- status;
- companions line;
- D8 status row;
- V1 row of §6.1;
- "Development family" line;
- "Classification in development" line;
- V1 effect-size row;
- pipeline-check bullet (kept, struck through);
- stability bullet;
- §7.1 Holm row;
- §11 S9 row;
- §14 D8 row.

**Every other v4.1 line is unchanged**, including all of §3–§5 (data, sessions, exclusions, counts), the
definitions of T1, T2, P1 and L1, P1's exact specification, the EWMA rule, the bootstrap, the p-value formula,
the Holm formula, the intervals, the minimum sizes, the O2 rules and prohibitions, the sensitivities and the
appendices.

**Frozen numbers.** Each appears at least as often in v4.2 as in v4.1, and none is altered:

| Number | v4.1 | v4.2 |
|---|---|---|
| 1,417 | 7 | 7 |
| 1,308 | 3 | 4 |
| 1,230 | 3 | 5 |
| 346 | 18 | 18 |
| 334 | 18 | 18 |
| 318 | 15 | 16 |
| 297 | 2 | 3 |
| 185 | 4 | 4 |
| 983 | 2 | 2 |
| 781 | 2 | 2 |
| 538 | 2 | 2 |
| seed 20261111 | 1 | 1 |
| B 10,000 | 3 | 3 |
| λ 0.94 | 2 | 2 |
| Holm threshold formula | 1 | 1 |

The increases are the new decision rows and the new §7 halt list.

**Amendment by amendment:**

| Amendment | Changes a research definition? |
|---|---|
| L4 one-based statement (§6.2) | No. It restates the existing v4.1 formula, under which the first 80 analysis sessions were already unassigned. |
| Holm placeholder | No. The thresholds faced by the four tests are those of v4.1 whenever V1 was not significant. |
| §7.2 disclosures | No. They report calibration results and restrict claims; no method changed. |
| D8 row | Records a fact (checked; not reviewed). |

## 3. L4: session 81 confirmed

- Protocol v4.2 §6.2 gives the one-based statement: session *s* has *s − 21* prior averages; the minimum of 60
  is first met at **session 81**; sessions 1–80 are unassigned. The minimum of 60 is fixed.
- **Tests (all pass):**
  - `test_l4_one_based_numbering_of_the_warm_up`: one-based 1–80 unassigned, **80 has 59 prior averages,
    81 has 60 and is assigned**;
  - `test_l4_first_eligible_assignment_and_boundaries`: the first assignment matches a hand calculation;
    ties go low;
  - `test_l4_short_samples_and_no_look_ahead_at_the_boundary`: changing data from session 80, 81 or 82
    (one-based) onward never changes an earlier group;
  - `test_volatility_groups_depend_only_on_earlier_sessions`;
  - `test_l4_assigned_count_is_n_minus_80`;
  - `test_l4_constants_frozen`.

## 4. P1 limitation (preserved and disclosed)

- **Protocol v4.2 §7.2 (binding):**
  - P1 rejected 1.33% (iid) and 1.50% (common volatility) at nominal 1%, and 0.33–0.34% at 0.2%.
  - Its 99% intervals cover 98.3–98.6%.
  - With **9,999 resamples the rejection rates are unchanged** (1.34%, 1.50%), so the excess comes from the
    method at n = 1,230.
- A development "established" label for P1 **is not established confirmatory evidence until P1's statistical
  validity has been independently reviewed.**
- **No claim is made that the four-test family has a verified 1% family-wise error rate.**
- The same text is attached in code to every P1 result (`calibration_note`), to `calibration_disclosures` in
  the family results and the official verdict, and to the printed verdict file
  (`test_v42_p1_and_fwer_disclosures_are_attached`).
- **The frozen P1 method is unchanged.**

**Artifacts preserved:**

| File | SHA-256 |
|---|---|
| `SESSIONS_CALIBRATION.json` (original, 210,000 repetitions) | `e32b7992…5164da27` |
| `SESSIONS_CALIBRATION_P1_B9999.json` (diagnostic, 40,000 paired repetitions) | `3fba6b9d…6514451` |

`test_u7_protocol_and_calibration_artifacts_preserved` pins both, plus v4.1 and v4.2.

## 5. Independent-review preparation checks

| # | Check | Result |
|---|---|---|
| 1 | Development and holdout counts against the frozen inventory | **Reconciled** (§6) |
| 2 | Every v4.2 amendment against v4.1 | **Done** (§2) |
| 3 | Protocol hashes | v4.1 `716e0003…` unchanged, in the cloud and on your PC. v4.2 `99b54fd3…`. `PREREG_HASH.txt` 11 lines, unchanged; `check.py` prereg gate: 11 hashes match. **Neither v4.1 nor v4.2 is in `PREREG_HASH.txt`** (neither is signed). |
| 4 | V1 descriptive-only restrictions | Reviewed (§7). |
| 5 | Five-slot Holm implementation | Reviewed (§7). |
| 6 | P1 calibration limitations | Reviewed (§4). |
| 7 | O2 cannot influence the official verdict | `test_o2_cannot_change_the_official_verdict_removed_randomised_altered` passes: the verdict file is identical with O2 prices randomised, O2 removed and O2 membership altered, and it is written before O2 is computed. `official_verdict` has no O2 parameter. |
| 8 | All synthetic tests and project checks | §8 |
| 9 | Unresolved limitations for an independent reviewer | §9 |

## 6. Count reconciliation with the frozen inventory

Sources compared:
- protocol v4.1/v4.2 §5.2, §5.2a and Appendix E;
- `run_sessions_study.py` frozen gates;
- `HOLDOUT_EXPOSURE_SESSIONS.csv` (SHA-256 `a462425b…b88683`, matches the runner pin);
- `HOLDOUT_EXPOSURE_INVENTORY.md`;
- `DATA_FEASIBILITY_SESSIONS.md` v2.

The CSV holds only session dates, weekdays, exclusion labels and test labels, with no prices. No market-data
file was opened.

| Figure | Protocol | Runner gate | Inventory CSV (recounted now) | Status |
|---|---|---|---|---|
| Holdout sessions with RTH | 346 | — | **346 rows**, 2025-07-01 → 2026-10-30 | ✓ |
| Holdout E1 / E2 / E3 / E4 / E5 | 12 / 10 / 0 / 5 / 1 | — | `excluded_by`: E1 12, E2 10, E4 5, E5 1 | ✓ |
| Holdout eligible | 318 | 318 | 346 − 28 = **318** | ✓ |
| Eligible categories | A_H8 21, P_placebo 111, B 186 | — | **21 / 111 / 186** | ✓ |
| Holdout primary after E6 | 297 | 297 | 318 − 21 (the E6 removals are exactly the 21 A_H8 sessions, Appendix E) | ✓ (arithmetic plus Appendix E; E6 is not a CSV column) |
| O2 ("B only", Mon/Thu/Fri) | 185 | 185 | Mon 59 + Thu 62 + Fri 64 = **185** (one Tuesday, 2025-12-23, excluded) | ✓ |
| Development start → E1…E5 | 1,417 → 1,371 → 1,332 → 1,332 → 1,311 → **1,308** | 1,308 | — (no development inventory CSV) | ✓ Arithmetic re-checked: 1,417 − 46 − 39 − 0 − 21 − 3 = 1,308 |
| Development primary | 1,230 | 1,230 | — | ✓ 1,308 − 78. E6 standalone 86, minus 8 sessions already removed by E4 = 78. |
| Holdout E6 | 21 | — | — | ✓ 22 standalone − 1 (2026-06-17, already E4) |
| V1 sub-sample (development) | 983 | MIN_V1 500 | — | Consistent; recorded in v4.1 |
| O2 matched development | 781 (V1 538) | — | — | Recorded in v4.1 |

**Notes for the reviewer:**
- The development counts were derived in earlier phases from timestamps only (`reconcile_counts.py`, hash in
  protocol §13). I did **not** re-run that script, because it opens the market-data files. A reviewer who
  wants an independent re-derivation can run it, since it loads timestamps only.
- "318" also appears in `HOLDOUT_EXPOSURE_INVENTORY.md` as the H8 Wednesday-pool window count (318 windows).
  That is a coincidence of value with the holdout eligible count, not the same set.
- The count history (333→334, 347→346) is documented in protocol §5.2a.

## 7. V1 and Holm implementation reviewed

**V1:**
- In code, V1 appears only:
  - as an estimate and effect sizes;
  - as descriptive p-values and intervals (development, O2 and S9);
  - in the reported-only sign flag;
  - as a fixed verdict label.
- It is absent from stability, from the classification rules and from every halt.
- The guard rejects any inferential V1 field.

**Holm:**
- `run_family` → `holm_with_placeholder` → `holm` is the only route into the correction.
- The family must be exactly the five tests. V1's entry is the constant 1.0.
- Thresholds 0.002 / 0.0025 / 0.0033 / 0.005 are tested at their exact boundaries.
- A property test covers 2,000 random p-vectors × 7 observed V1 values.

## 8. Test and check results

| Gate | Result |
|---|---|
| `python -m pytest tests/test_sessions.py -W error::RuntimeWarning` (fast + slow) | **136 passed**, 0 failed |
| `scripts/check.py` | ruff PASS; pytest **254 passed, 2 skipped** (the old webhook tests: "needs data/mnq_train.csv (not in the repo)"); prereg PASS (11 hashes); prepublish PASS; pip-audit PASS; mypy PASS |
| Coverage | `sessions.py` 99% (568 statements, 2 missed); `run_sessions_study.py` 97% (7 missed: the real-data entry points and a defensive holdout refusal, by design) |
| Real-data guard | The cloud copy has **no `data/` folder**. The U6 autouse fixture blocks any read under `data/`. `runs/` has no sessions development or holdout result, only the synthetic diagnostic. |

**New or changed tests this round:**
- Replaced the halt test with `test_v42_nonpositive_v1_is_reported_and_the_run_completes`.
- New `test_v42_no_v1_outcome_halt_exists_in_the_code` and `test_v42_p1_and_fwer_disclosures_are_attached`.
- Renamed `test_u7_v1_sign_is_reported_not_inferential`.
- The artifact test now also pins v4.2 and the P1 diagnostic.

## 9. Unresolved limitations: list for the independent reviewer

| # | Item | Reviewer's question |
|---|---|---|
| R1 | **P1 is mildly liberal** (1.33–1.50% at 1%; 0.33% at 0.2%) and under-covers (98.3–98.6%); more resamples do not fix it | Is P1's centered stationary-block bootstrap valid enough to carry an "established" development label at all? |
| R2 | **Family-wise error is not verified at 1%** because of R1; Holm only bounds it for valid p-values | Acceptable as disclosed, or should P1 be reported descriptively too? (That would be a protocol change and needs a new version.) |
| R3 | **V1 inference fails under independent volatility clustering** (19.4% at 1%; 80% coverage); V1 is descriptive only | Is "descriptive only" enough, given its descriptive interval can still be badly over-confident? |
| R4 | T1/T2 are conservative (about 0.3% at 1%), so power is lower | Accept? |
| R5 | Calibration used n = 1,230 synthetic sessions with Gaussian / t(4) / GARCH(1,1) data. There is no censoring, missing data or roll jumps inside the Monte Carlo; those are unit-tested only. | Are the scenarios representative enough of index futures? |
| R6 | B = 999 vs 10,000 was measured only for P1 (no size effect; +0.2 points coverage), not for T1, T2 or L1 | Needed? |
| R7 | Tail regime stability is not assessable for 2020–2022 (Hill k < 20) | Accept the "not assessable" label (U2)? |
| R8 | The earliest volatility groups (from session 81, about late April 2020) rest on overlapping averages from January–April 2020, including March 2020 | Disclosure enough? |
| R9 | P1 uses MNQ volume as the price-discovery proxy (limits listed in protocol §6.1) | Accept? |
| R10 | O2 is not a clean holdout; the official verdict is fixed at INCONCLUSIVE (D2-a) | Confirm that the O2 prohibitions are sufficient |
| R11 | **D8:** Liu & Tse (2017) and Riedel & Wagner (2015) have not been reviewed (no full text through the library) | Obtain them through Interlibrary Loan before final interpretation; nothing depends on them |
| R12 | Development counts were not re-derived in this round (that would open the data files; timestamps only) | Optionally re-run `reconcile_counts.py` |
| R13 | Real-data entry points are untested end to end, by design | Review `run_dev` / `run_holdout` code paths by reading |
| R14 | The protocol is still a draft: v4.2 is unsigned and nothing is in `PREREG_HASH.txt` | Sign-off, then hash and commit, before any real-data run |
| R15 | The older webhook tests read `data/mnq_train.csv` if present (U6) | Keep running only `tests/test_sessions.py` locally |
| R16 | Report v2 on your PC (preserved unchanged, and the copy in this package) says the T tests' 5% rate is "3.0–3.2%"; the calibration JSON gives 2.92–3.21% (scenarios 3 and 7). The cloud working copy differs on this one line only ("2.9–3.2%"). Report v2 is not edited; the JSON is authoritative. | Note only |

## 10. Exact files changed this round (all uncommitted)

| File | Change | Lines | SHA-256 |
|---|---|---|---|
| `nq_bot/sessions.py` | U9 flag renamed (reported only); P1/FWER disclosures; verdict disclosures | 933 | `4bb9b7f41f65e2c7633a4b31dfa872d90fcfeaee5f38124c8e80a9f013aad8b9` |
| `run_sessions_study.py` | V1 halt removed; protocol label v4.2; refusal message | 306 | `d41767460a63b03441fbbc54f9f763e1862304c7c4f341783bb0bd3205183137` |
| `tests/test_sessions.py` | 3 v4.2 tests, 1 renamed, artifact pins extended | 1,168 | `24ce2848a1dd561788ba8c8efd68b888016b9f1ed5402ab7fab912c6e68a4e05` |
| `docs/DRAFT_PREREG_SESSIONS_v4.2_awaiting_signoff.md` | **New** | — | `99b54fd3571885baae6d58677513dbc43327c6731242914ebd0fe936afecebea` |
| `docs/SESSIONS_ADDENDUM_U7_L4.md` | Revision 3 (U9 resolved; session 81) | — | see the package manifest |
| `docs/SESSIONS_FINAL_AUDIT_v5.md` | **New** (this file) | — | see the package manifest |
| `docs/review_package_sessions_v4.2/` | **New**: copies plus `MANIFEST.sha256` and `README_FOR_REVIEWER.md` | — | — |

**Unchanged:**

| File | SHA-256 |
|---|---|
| Protocol v4.1 | `716e0003…` |
| `SESSIONS_CALIBRATION.json` | `e32b7992…` |
| `SESSIONS_CALIBRATION_P1_B9999.json` | `3fba6b9d…` |
| `scripts/sessions_calibration.py` | `ef815568…` |
| `scripts/sessions_calibration_p1_b9999.py` | `f5d29f81…` |
| `tests/sessions_synth.py` | `5536e067…` |
| `HOLDOUT_EXPOSURE_SESSIONS.csv` | `a462425b…` |

`PREREG_HASH.txt`, audits v3 and v4, and report v2 are also unchanged.

## 11. Confirmation

- No actual market price was loaded.
- No actual study result was calculated.
- No trading account or broker was connected.
- Nothing was committed or pushed.
- No new hypothesis or strategy work was started.

**Stopped here for independent review.**
