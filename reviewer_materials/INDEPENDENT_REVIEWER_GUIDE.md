# Independent reviewer guide: overnight vs regular-session MNQ study

Prepared 2026-11-12 for the independent reviewer.

**Status:**
- Protocol v4.2 is an **unsigned draft**. Nothing has been approved or validated.
- No real-data analysis has been run and no study result exists.
- This is a historical, descriptive market-behaviour study. It is **not** a trading strategy and makes no
  profitability claim.

**What we ask.** An honest, evidence-based assessment of the methodology and software. Negative findings are
as useful as positive ones.

**Passing tests are not proof.** The 136 synthetic tests show that the code does what the protocol describes
on generated data. **Please do not treat them as evidence that any statistical procedure is valid for real
data.**

---

## 1. How to use this guide

1. **Reconstruct the snapshot** using `REVIEW_DELIVERY_CHECKLIST.md` §E: bundle `a48eaac` plus the 55-file
   overlay, verified against `WORKING_TREE_INVENTORY.txt`.
2. **Read in this order:**
   1. `docs/FINAL_REVIEW_HANDOFF_MANIFEST_v1.md` (revision 3), the current state of the handoff;
   2. `docs/DRAFT_PREREG_SESSIONS_v4.2_awaiting_signoff.md`, the protocol under review;
   3. `docs/review_package_sessions_v4.2/protocol/protocol_v4.1_to_v4.2.diff`;
   4. `docs/INDEPENDENT_REVIEW_GUIDE_v1.md`: background on each statistic, with a function-level checklist;
   5. `docs/REMAINING_LIMITATIONS_v1.md` and `docs/INDEPENDENT_REVIEW_PACKAGE_AUDIT_v1.md`.
3. **Superseded statements inside the frozen snapshot.** `REMAINING_LIMITATIONS_v1.md` (item L-PC) and the
   package audit (§7) say the tests were not run on Ethan's PC. **That is no longer true.** Manifest
   revision 3 §8 and the Windows transcript show 136/136 passing on Windows, twice. Those files were left
   unedited so the snapshot checksums stay valid.
4. **Answer each question** in §3–§6 using the scale in §2, and fill in the findings table in §7.

## 2. Verdict scale and evidence standard

Classify **every** finding as one of:

| Classification | Meaning |
|---|---|
| **Acceptable** | Correct as specified and implemented, for the stated purpose |
| **Acceptable with limitations** | Usable, but only with the limitation stated alongside any result |
| **Requires correction** | Wrong, unsafe or misleading; must change before any real-data run |
| **Cannot be determined from supplied evidence** | The package does not contain what is needed to decide; say what is missing |

**Each conclusion needs evidence**, such as:
- file path and line or function;
- a calculation;
- a reproducible test or script (synthetic data only), with its command and output;
- a citation.

Opinions without evidence should be marked as such.

## 3. A. Statistical validity

| # | Question | Where to look | What the project already reports | Known gap |
|---|---|---|---|---|
| A1 | **Bootstrap assumptions and dependence.** Is a stationary block bootstrap with mean block 20 sessions on joint (ON, RTH) pairs appropriate for daily index-futures returns, given volatility clustering, cross-period dependence and calendar effects? Is the holdout's whole-week block (mean 4 weeks) appropriate? Is resampling pre-computed EWMA-scaled z values, without re-running the EWMA inside replicates, defensible? | `nq_bot/sessions.py`: `stationary_indices` (l. 391), `week_block_indices` (l. 404), `bootstrap_family` (l. 488 ff.), `ewma_scale`; protocol v4.2 §7 "Resampling" | Calibration under iid, GARCH(1,1) independent and GARCH(1,1) common volatility; scenario 2 longer-block diagnostics | No real-data dependence diagnostics (deliberately: no data analysis) |
| A2 | **P1 false positives and coverage.** Why does P1 reject 1.33% (iid) and 1.50% (common GARCH) at nominal 1%, and 0.33–0.34% at 0.2%, with 99% intervals covering 98.3–98.6%? Is the centered (basic, non-studentized) bootstrap of a ratio statistic with a sign discontinuity valid here? | `wpc_on`, `vs_on`, `_boot_p1`, `centered_p` (l. 422), `percentile_ci`; `scripts/sessions_calibration.py` `make()` scenarios 4 and 8; both calibration JSONs; protocol §6.1 "P1 exact specification", §7.2 | The paired B = 999 vs 9,999 diagnostic shows **no** change in size (1.33% → 1.34%; 1.50% → 1.50%) and only +0.2 points of coverage, i.e. the problem is not the resample count | P1's rate at Holm's later thresholds (0.0025, 0.0033, 0.005) was never measured. Per-replicate calibration data is not included (regenerable from seeds; about 2 h and 6 h). |
| A3 | **Should P1 stay inferential?** Or become descriptive only, as V1 is? What evidence would be needed before it could ever be confirmatory? | Protocol §7.2; `P1_CALIBRATION_NOTE` in `sessions.py`; guide v1 §5 | P1 is flagged as not established confirmatory evidence until reviewed | A reviewer judgment |
| A4 | **V1 descriptive-only treatment.** Is the restriction complete, so that V1 cannot establish significance, affect other tests, halt the pipeline or reach the verdict? Is it right to keep reporting V1's descriptive interval when its coverage was 80.1% in scenario 2? | `run_family` V1 branch, `assert_v1_descriptive_only` (l. 652), `stability`, `official_verdict` (l. 706), `o2_secondary` (l. 742), runner `sensitivities` (`note_V1`) and `run_dev` (no V1 halt); tests `test_u7_*`, `test_v42_*` | Scenario 2: 19.4% false positives at 1%; decisions U7/U9 in protocol §0 and Appendix D part 5 | — |
| A5 | **Holm, five-slot procedure.** Is the implementation correct, including step-down stopping, adjusted p-values and ties? Is V1's placeholder 1.0 applied on the only route into Holm? Does the v4.2 sentence "face the same thresholds as in v4.1 whenever V1 was not significant" describe the implementation accurately? | `holm` (l. 439), `holm_with_placeholder` (l. 457); tests `test_holm_*`, `test_u8_*`; `scripts/review/holm_v41_v42_comparison.py` and its output; guide v1 §4 (question H-d) | 200,000 random cases: rejection decisions identical in all 188,433 cases with V1 not significant; adjusted p-values differ in 69,935 (37.1%) | Wording issue PD-4 is unresolved and needs the reviewer's view |
| A6 | **Family-wise error interpretation.** Is it justified to state only that "a 1% FWER is **not** verified", given that Holm assumes valid p-values and P1 is liberal? Can any bound be given? | Protocol §7.2; `FWER_NOTE`; calibration JSONs | No verified FWER is claimed | The four nulls cannot hold in one synthetic process, so no family-level simulation exists |
| A7 | **Sample sizes and minimum observations.** Are the minimums adequate, and are refusals (not truncation) correct? Development ≥ 1,000; V1 ≥ 500; regime ≥ 150; Hill k ≥ 20; O2 ≥ 100 and V1 ≥ 80. Also: the Hill index on near-Gaussian tails, regimes that are "not assessable" (k < 20 in 2020–2022), and the L4 warm-up (first group at session 81). | `sessions.py` l. 52–53 (`MIN_*`), `require` (l. 595), `stability`, `hill`, `vol_tercile_membership` (l. 839); protocol §7 minimum-size table, §6.2 | Frozen counts 1,230 development primary, 983 V1, O2 185 | — |

## 4. B. Research protocol

| # | Question | Where to look |
|---|---|---|
| B1 | Are v4.1 and the unsigned v4.2 internally consistent, and is every amendment listed in Appendix D part 5? Known wording issues: PD-3 (stale "v4" wording, §6.1 heading "5 tests") and PD-4 (Holm sentence). | `protocol_v4.1_to_v4.2.diff`; protocol Appendix D; package audit §5 |
| B2 | Is the official verdict INCONCLUSIVE enforced in code for every possible development outcome? | `official_verdict` (l. 706), `render_verdict`; `test_official_verdict_is_inconclusive_for_every_possible_development_outcome` |
| B3 | Is O2 prevented from changing the official verdict? The verdict is written before O2 is computed, `official_verdict` has no O2 parameter, and it is re-checked after O2. | `run_sessions_study.run_holdout` (l. 221–287); `test_o2_cannot_change_the_official_verdict_removed_randomised_altered`, `test_official_verdict_has_no_path_for_o2`; protocol §8 prohibitions |
| B4 | Are the development and holdout exposure limitations disclosed accurately? The holdout's A/P/B exposure to earlier experiments; O2 is not a clean holdout; development data was used before. | `docs/HOLDOUT_EXPOSURE_INVENTORY.md`, `docs/HOLDOUT_EXPOSURE_SESSIONS.csv`; protocol §8, Appendix E, §10 overlap table |
| B5 | Do the frozen rules prevent outcome-driven changes? The runner refuses without a hashed protocol, refuses on data-hash or count mismatch, runs each stage once, and opens the holdout only after development results are committed; forbidden quantities fail the run. Is anything still open to adjustment after results are seen? | `require_frozen_protocol` (l. 91), `verify_pins` (l. 101), `check_counts` (l. 120), run-once checks (l. 184, 223), `git_is_committed` (l. 77); `assert_no_forbidden` (l. 922); manifest PD-9 (freeze procedure) |

## 5. C. Data integrity and reproducibility

| # | Question | Where to look | Note |
|---|---|---|---|
| C1 | **Contract identity and rolls.** The series is a spliced, unadjusted front-month series. Roll sessions are excluded via exact switch dates from `runs/rollmap_MNQ.json` (Databento symbology `MNQ.v.0`, 31 contract periods, 30 switches) under rule E4. | `rollmap_switches` (l. 218), `build_sample` (l. 223 ff.); protocol §5.1 E4, Appendix A.1; `test_roll_discontinuity_is_excluded_and_cannot_move_any_result` | **Observation for you:** `integrity.Gate.contract_identity` exists, but the sessions runner does not call it. Contract identity rests on the roll map. Please assess whether that suffices. |
| C2 | **Session boundaries and DST.** CME session date = date(ET + 6 h); RTH 09:30–16:00 ET; boundary windows 09:30–09:35 and 15:55–16:00; a session spanning a DST change raises. | `session_table` (l. 172–208); tests `test_exact_recovery_of_returns_and_volumes_across_dst`, `test_session_spanning_a_dst_change_is_a_data_error` | — |
| C3 | **Missing, duplicate and conflicting observations.** Missing minutes count as zero volume and are never imputed; missing boundary windows trigger E3; a zero-volume bar raises; duplicate timestamps across files are dropped only if identical, and conflicting ones raise. | `read_bars` (l. 129–152), `check_bars` (l. 155–168); `integrity.Gate.bars`; tests `test_missing_*`, `test_zero_volume_bar_stops_the_run`, `test_overlapping_files_*` | — |
| C4 | **Timestamp-only count verification.** Is the re-run (counts reproduce 1,308 / 1,230 and 318 / 297) adequate? It is a re-run of the original script, which reads only the `timestamp` column, not an independent implementation. | `scripts/sessions_preflight/reconcile_counts.py`, `verify_counts_and_rolls.py`; `evidence/reconcile_counts_output_pc.txt` | **The data files are not supplied**, so you can inspect the script and its output but not re-run it |
| C5 | **Windows/Linux line endings and hash portability.** 59 tracked files are CRLF on the Windows checkout. The pinned `runs/rollmap_MNQ.json` hash (`e1beaeed…`) matches CRLF bytes only; an LF checkout gives `eaded078…`. | Manifest §10 HF-2; `PINNED` in `run_sessions_study.py`; `.gitattributes` | Affects real-data runs only. Please recommend a fix approach. |
| C6 | **Reconstruction.** Can the handoff be rebuilt from the supplied files and verified file by file? | Checklist §E; `WORKING_TREE_INVENTORY.txt`; `evidence/cloud_reconstructed_snapshot_checks.txt` | The bundle is not byte-reproducible on rebuild (same objects); the overlay is |

## 6. D. Software quality

| # | Question | Where to look | Current evidence |
|---|---|---|---|
| D1 | **The 136 Windows tests.** Do they test the right properties? Are any tautological or too weak? Pay particular attention to the slow Monte Carlo checks and their tolerances. | `tests/test_sessions.py`; `evidence/windows_powershell_transcript_2026-11-12.txt`, `windows_pytest_test_sessions_full_output.txt` | 136/136 passed twice on Windows (Python 3.12.10, numpy 2.5.4, pandas 3.1.1, pytest 9.2.0); also on the Linux shell (pandas 2.3.3) and in the cloud (pandas 3.0.5 and 3.1.1) |
| D2 | **The 13,745 pandas deprecation warnings.** Are they benign today? How serious is the future-compatibility risk (removal of `dayofweek` breaks `sessions.py:266` and `:748`)? Rename, or pin `pandas<4`? | `evidence/pandas_deprecation_warnings_reproduction.txt`, `…_counts.json` | 10,829 from `sessions.py:266`, 2,900 from `test_sessions.py:568`, 16 others; not suppressed |
| D3 | **Outstanding lint and type-check failures.** `scripts/check.py` fails on the full snapshot. ruff: 65 findings, 60 in `scripts/sessions_preflight/` and 5 S607 in the package's copy of the test file. mypy: 20 errors, all in `scripts/sessions_preflight/`. The study code alone passes. | `evidence/cloud_reconstructed_snapshot_checks.txt`; `pyproject.toml` (ruff, mypy configuration); manifest §8 | Unresolved. The pre-flight scripts' hashes are recorded in protocol §13. |
| D4 | **Are safeguards enforced in code rather than only documented?** Real-data guard in tests; forbidden-quantity guard; V1 guard; Holm family check; count and hash gates; run-once and commit locks; no broker, webhook or live imports. | `_no_real_data` fixture (`tests/test_sessions.py` l. 32 ff.); `assert_no_forbidden`; `assert_v1_descriptive_only`; `holm_with_placeholder`; `tests/test_tooling.py` RESEARCH/EXECUTION lists; package audit SW-1 to SW-4 | Known weaknesses: the artifact-hash test skips everything after the first missing file (SW-1); real-data entry points are untested (SW-2); the guard covers only `open` and `io.open` (SW-3) |

## 7. Findings table (please complete)

| ID | Area | Finding | Classification | Evidence (file:line, calculation, test command and output) | Recommended action |
|---|---|---|---|---|---|
| A1 | Bootstrap and dependence | | | | |
| A2 | P1 calibration and coverage | | | | |
| A3 | P1 inferential status | | | | |
| A4 | V1 descriptive-only | | | | |
| A5 | Holm five-slot and wording | | | | |
| A6 | FWER interpretation | | | | |
| A7 | Minimum sizes | | | | |
| B1 | v4.1 / v4.2 consistency | | | | |
| B2 | INCONCLUSIVE enforcement | | | | |
| B3 | O2 isolation | | | | |
| B4 | Exposure disclosure | | | | |
| B5 | Outcome-driven change prevention | | | | |
| C1 | Contract identity and rolls | | | | |
| C2 | Sessions and DST | | | | |
| C3 | Missing, duplicate, conflicting data | | | | |
| C4 | Count verification | | | | |
| C5 | Line endings and hash portability | | | | |
| C6 | Reconstruction | | | | |
| D1 | Test suite | | | | |
| D2 | pandas deprecations | | | | |
| D3 | Lint and type-check failures | | | | |
| D4 | Safeguards in code | | | | |
| — | Anything else you find | | | | |

Please end with an overall statement covering: (a) whether the methodology is fit for its descriptive purpose,
(b) what must be corrected before any real-data run, and (c) what you could not assess.

## 8. Boundaries for the review

- **Allowed:** read-only inspection, and running the synthetic tests and synthetic calibration scripts.
- **Not allowed under this review:**
  - loading or analysing real market prices;
  - computing the study's actual results;
  - changing hypotheses or thresholds;
  - developing trading rules or signals;
  - connecting brokers, accounts or webhooks.
- The licensed data files are deliberately not supplied.

## 9. Evidence not available to you

| Missing | Effect on the review |
|---|---|
| Market-data files (licensed) | Count verification, data-integrity behaviour on real data and the roll map's derivation cannot be re-run, only inspected |
| Full texts of Liu & Tse (2017) and Riedel & Wagner (2015) (library: no full text) | T1's expected direction and P1's literature context rest on abstracts (D8) |
| Per-replicate calibration data | Only aggregates are supplied. Regenerate with `scripts/sessions_calibration.py` (about 2 h on 2 cores) and `scripts/sessions_calibration_p1_b9999.py` (about 6 h). |
| P1 calibration at 0.0025, 0.0033 and 0.005 | Never run |
| Synthetic scenarios with censoring, missing bars, roll jumps or volume variation inside the Monte Carlo | Not run |
| Any end-to-end real-data run | By design; the protocol is unsigned |
