# Independent-review package audit, v1

Audit of `docs/review_package_sessions_v4.2/`. Written 2026-11-12 ~22:45 CT (2026-11-13 04:45 UTC).

**Evidence labels used throughout:**
- **[CODE]** verified by code inspection in this audit;
- **[SYNTH]** verified by synthetic testing run in this audit;
- **[PRIOR]** reported by previous work and not independently re-verified here;
- **[OPEN]** still unresolved.

**Nothing in this audit changed a research rule, a protocol file, or any file inside the package.**
Discrepancies are reported, not repaired. Protocol v4.2 is an **unsigned draft**; it is not approved.

---

## 1. Freeze record

| Item | Value |
|---|---|
| Repository | `C:\Users\thebo\OneDrive\Documents\nq_bot` (`github.com/ethanfilbeck/nq-futures-strategy-lab`) |
| Branch / HEAD | `main` at `a48eaac8d7825ef8171d9762de27fcc33b3d3798` ("FOMC-cycle candidate REJECTED, and the refuting paper is by an original author", 2026-11-12 04:44:52 UTC); in sync with `origin/main` |
| Tracked files modified | `pytest.ini`, `tests/test_tooling.py` (uncommitted) |
| Untracked | 13 files in `docs/`, the package folder, `nq_bot/sessions.py`, `run_sessions_study.py`, `scripts/sessions_calibration.py`, `scripts/sessions_calibration_p1_b9999.py`, `scripts/sessions_preflight/`, `tests/sessions_synth.py`, `tests/test_sessions.py` |
| `docs/PREREG_HASH.txt` | 11 lines, unchanged against HEAD. **Neither v4.1 nor v4.2 is recorded in it.** |
| Commits / pushes | None made |

**Protocol hashes:**

| File | Status | SHA-256 |
|---|---|---|
| `docs/DRAFT_PREREG_SESSIONS_awaiting_signoff.md` | **v4.1**, historical | `716e00037ab4d7e20b9f9a44a0af6a146e646f1f631101470a2c8ceb37506021` |
| `docs/DRAFT_PREREG_SESSIONS_v4.2_awaiting_signoff.md` | **v4.2**, current unsigned draft | `99b54fd3571885baae6d58677513dbc43327c6731242914ebd0fe936afecebea` |

## 2. File inventory and checksums [CODE]

**Results:**
- **Files present:** 23 package files plus `MANIFEST.sha256` (24 on disk).
- **Manifest:** 23 entries, one for every package file. No file is missing from the manifest, and the manifest
  names no file that is absent.
- **`sha256sum -c MANIFEST.sha256` on your PC: 23 OK, 0 FAILED.**
- **Manifest's own hash:** `ff391179e67312bda7f0b781f3502091f8beb98603846c3c17335f795105e824`. The manifest does not
  cover itself; record this hash when sending the package.

**Package copies against the working tree.** Every package copy was compared byte for byte (`cmp`) with its
working-tree original on your PC. **All 23 are identical**; the one with a different name is the v4.1 copy, see
PD-1.

| Package path | Working-tree original | Role |
|---|---|---|
| `README_FOR_REVIEWER.md` | (package only) | Entry point |
| `protocol/DRAFT_PREREG_SESSIONS_v4.1_awaiting_signoff.md` | `docs/DRAFT_PREREG_SESSIONS_awaiting_signoff.md` (**renamed in package**, identical bytes) | Historical protocol v4.1 |
| `protocol/DRAFT_PREREG_SESSIONS_v4.2_awaiting_signoff.md` | `docs/…v4.2…` | **Current unsigned draft** |
| `protocol/protocol_v4.1_to_v4.2.diff` | (package only) | Unified diff, 11 hunks |
| `docs/SESSIONS_FINAL_AUDIT_v5.md` | `docs/` | Current audit |
| `docs/SESSIONS_ADDENDUM_U7_L4.md` | `docs/` | Implementation notes, revision 3 |
| `docs/SESSIONS_RESEARCH_AUDIT_v4.md`, `…v3.md` | `docs/` | **Historical** |
| `docs/SESSIONS_SYNTHETIC_TEST_REPORT.md` | `docs/` | **Historical** (report v2) |
| `docs/LITERATURE_SESSIONS.md` | `docs/` | Phase 1 literature review (predates the D8 library check) |
| `docs/DATA_FEASIBILITY_SESSIONS.md` | `docs/` | Phase 2 feasibility (v2) |
| `docs/HOLDOUT_EXPOSURE_INVENTORY.md`, `HOLDOUT_EXPOSURE_SESSIONS.csv` | `docs/` | Frozen holdout inventory. The CSV is pinned in the runner as `a462425b…b88683` and holds dates and labels only. |
| `calibration/SESSIONS_CALIBRATION.json` | `docs/` | Original calibration (`e32b7992…`) |
| `calibration/SESSIONS_CALIBRATION_P1_B9999.json` | `docs/` | P1 diagnostic (`3fba6b9d…`) |
| `code/nq_bot/sessions.py`, `code/run_sessions_study.py`, `code/pytest.ini` | repo root | Study code |
| `code/tests/test_sessions.py`, `sessions_synth.py`, `test_tooling.py` | `tests/` | Synthetic tests |
| `code/scripts/sessions_calibration.py`, `sessions_calibration_p1_b9999.py` | `scripts/` | Calibration scripts |

**The cloud workspace used for testing** is at the same HEAD (`a48eaac`). Its eight study code files are
byte-identical to the package copies (`cmp`).

## 3. README accuracy [CODE]

| README statement | Finding |
|---|---|
| The study is descriptive, historical and academic; not a trading strategy | Accurate (protocol §1–2; module docstrings) |
| "No real price has been loaded and no study result exists" | Accurate for this study; no `sessions_*` development or holdout result exists on your PC (`runs/` checked) |
| "**Everything here was produced and tested on synthetic data**" | **Inaccurate as worded (PD-5).** The code, tests and calibration are synthetic. But the frozen counts, the holdout inventory and the data-feasibility report were derived in earlier phases from the **timestamps** (and, in one audit, volumes) of the real data files, and the literature review comes from web sources. |
| "Protocol v4.2 is unsigned. Nothing is hashed…" | Accurate |
| `protocol/…v4.1…` is the preserved prior version, SHA-256 `716e0003…` | Hash accurate. The file name differs from the original (PD-1). |
| Calibration file descriptions (12 scenarios, B = 999; P1 paired diagnostic) | Accurate |
| "136 tests, about 3.5 min" | Accurate: 136 passed in 215 s in this audit |
| Re-running needs the full repository | Accurate. The package lacks `nq_bot/integrity.py`, `rolls.py`, `family3.py`, `data.py` and `scripts/sessions_preflight/` (PD-11). |
| Key decisions table (D2-a, U7/U8/U9, P1, L4) | Accurate summary of the protocol and code |

## 4. Version identification, history and "approved" wording [CODE]

**Is v4.2 described anywhere as approved or signed? No.**
- v4.2's status line reads "Not signed, not hashed, not committed".
- Its §14 has an open "Sign-off of v4.2" row and an empty signature line.
- The README, audit v5 (§1 table and R14) and the addendum all say unsigned or draft.

**Wording a reader could misread (PD-7).** These phrases refer to Ethan's approval of a *decision*, not of
the protocol:
- the audit v5 heading "Protocol v4.2 (U9 approved)";
- the addendum heading "resolved by protocol v4.2 (U9 approved 2026-11-12)";
- "approved" in decision rows (U8, L4, P1, D4 "conditionally approved").

**Historical versus current.** The README labels audits v3 and v4 and report v2 as "(history)". **The files
themselves carry no "superseded" banner** (PD-6). Each contains statements that are no longer current:

| Historical document | Outdated statements |
|---|---|
| Report v2 | V1 is in the inferential Holm family; 106 tests |
| Audit v3 | U8 and U9 shown as open; a V1 point-estimate halt |
| Audit v4 | The halt marked PENDING; L4 "session 81" awaiting confirmation |

A reviewer reading out of order could take these as current.

## 5. Documentation discrepancies (reported, not repaired)

| ID | Discrepancy | Evidence | What would resolve it |
|---|---|---|---|
| **PD-1** | The package renames v4.1 to `DRAFT_PREREG_SESSIONS_v4.1_awaiting_signoff.md`. v4.2's header and change log cite the original name `DRAFT_PREREG_SESSIONS_awaiting_signoff.md`. | [CODE] Identical bytes and hash `716e0003…` | Note in the cover message. No content issue. |
| **PD-2** | v4.1's own title line says "(DRAFT v4)" while its status line says v4.1 (pre-existing in v4.1) | [CODE] | Historical; leave. v4.2's title is correct. |
| **PD-3** | v4.2 carries forward text that is now stale: §6.1 heading "Tested family (5 tests)" (four inferential plus V1 descriptive); §9 step 1 "Ethan reviews v4 and freezes"; §13 "`runs/` contains no `sessions_*` file"; §0 decision D4 "1% family-wise error across the 5 tests retained" (D4 is the target; §7.2 says it is not verified) | [CODE] §13 is still true on your PC; the cloud workspace's `runs/` holds the synthetic P1 diagnostic output | A future v4.3 wording pass, if you want one. No rule is affected. |
| **PD-4** | v4.2 §7 (and the addendum §A1, audit v5 §2) says that under the placeholder the four tests "face the same thresholds as in v4.1 whenever V1 was not significant". **This is imprecise.** A test that v4.1 ranked after a non-significant V1 moves up one step. | [CODE] Proof: such a test's p is at least V1's p, which exceeds the threshold at V1's rank, so it is still not rejected. [SYNTH] Brute force over 200,000 random p-vectors: 188,433 cases with V1 not significant under v4.1; **0 differ in any rejection decision; 69,935 (37%) differ in at least one adjusted p-value.** | Reword in a v4.3 to "**rejection decisions** are identical to v4.1's whenever V1 was not significant; adjusted p-values may differ". This changes wording, not a rule. **Not changed here.** |
| **PD-5** | The README "everything synthetic" wording (§3) | [CODE] | Cover-message clarification |
| **PD-6** | Historical documents lack "superseded" banners (§4) | [CODE] | Cover message, or banners in a later revision; history is not edited here |
| **PD-7** | "U9 approved" headings can be misread as protocol approval (§4) | [CODE] | Cover message |
| **PD-8** | Code docstrings are stale: `sessions.py` says "Implements … (protocol v4)" and the runner says "(protocol v4)". Results files record `"protocol": "v4.2"`. | [CODE] | Comment-only fix after review |
| **PD-9** | The runner requires the frozen protocol at `docs/PREREG_SESSIONS.md`, whose hash must be in `PREREG_HASH.txt` (`require_frozen_protocol`). Neither draft has that name. The freeze step (copy v4.2 to that path, hash, commit) is described only in the runner's refusal message. | [CODE] | Write the freeze procedure into the sign-off instructions |
| **PD-10** | `LITERATURE_SESSIONS.md` predates the D8 library check. It summarises Liu & Tse and Riedel & Wagner from abstracts and citing papers, with some items marked *unverified*. **T1's expected direction (Δα_lo < 0, "Riedel & Wagner") rests on an unreviewed paper's abstract.** | [CODE] Protocol §6.1 T1 row; literature doc §1 and §3 | Obtain the full text through Interlibrary Loan and check it (D8) |
| **PD-11** | The package cannot run on its own: it lacks the runner's dependencies and `scripts/sessions_preflight/` (`reconcile_counts.py` etc., needed to re-derive development counts). The manifest does not cover itself. | [CODE] | Send with the repository at HEAD `a48eaac` plus the working-tree files listed above; record the manifest hash |
| **PD-12** | **T-test calibration:** report v2 says the T tests' 5% false-positive rate is "3.0–3.2%". The calibration JSON gives T1 3.205% and T2 3.045% (scenario 3), and T1 2.945% and T2 2.920% (scenario 7), i.e. **2.92–3.21%**. | [CODE] Read from `SESSIONS_CALIBRATION.json` | The JSON is the primary record. Report v2 is not edited. No further evidence is needed unless the JSON itself is doubted (re-run with seeds `[scenario, rep, 1/2]`, about 2 h). |
| **PD-13** | The cloud working copy of report v2 differs from your PC copy on that one line ("2.9–3.2%"). The package contains the **PC copy**. | [CODE] | None; noted for provenance |

## 6. Software defects discovered

**No defect was found that changes a computed quantity, a decision or a verdict.**

Weaknesses found [CODE]:

| ID | Weakness | Effect |
|---|---|---|
| SW-1 | `test_u7_protocol_and_calibration_artifacts_preserved` calls `pytest.skip` on the **first** missing file, so a missing file silently skips the remaining hash checks | A false "pass" if files are moved. On your PC all four files are present. |
| SW-2 | Seven runner lines are never executed by tests: the holdout's defensive "development results incomplete" refusal (l. 234); the post-O2 verdict re-check (l. 283), which cannot trigger by construction; and the command-line entry (l. 298–306). Two module lines are also uncovered: a Hill error branch (l. 339) and an unreachable `KeyError` (l. 565). | Real-data entry points are untested end to end, by design |
| SW-3 | The real-data test guard patches `builtins.open` and `io.open` only. A read through another route (memory-mapping or a C extension opening paths directly) would not be caught. | All current code paths use `open` or `pandas.read_csv`, which the guard covers (tested) |
| SW-4 | The BH q-values ("information only") are computed over the five-slot family including V1's placeholder 1.0 | Not used for any decision; labelled information only |
| PD-8, PD-9 | Above | Documentation and procedure |

## 7. Tests and checks executed in this audit

| Run | Where | Result |
|---|---|---|
| `python -m pytest tests/test_sessions.py -W error::RuntimeWarning` with coverage | Cloud workspace (HEAD `a48eaac`, study files identical to the package) | **136 passed, 0 failed** (215 s). Coverage: `sessions.py` 99% (568 statements, 2 missed), `run_sessions_study.py` 97% (7 missed) |
| `python scripts/check.py` | Cloud workspace | ruff PASS; pytest **254 passed, 2 skipped** (old webhook tests needing `data/mnq_train.csv`, absent in the cloud); prereg PASS (11 hashes); prepublish PASS; pip-audit PASS; mypy PASS |
| Holm v4.1-vs-v4.2 brute force (200,000 cases) | Cloud | See PD-4 |
| Holdout E6 re-derivation from the inventory CSV and `family3.HOLDOUT_FOMC_DAYS` (no prices) | Cloud | 22 E6 sessions in all 346; **21 among the 318 eligible, identical to the 21 A_H8 sessions**; the 22nd (2026-06-17) is already E4; **318 − 21 = 297** ✓ |
| `sha256sum -c MANIFEST.sha256`; `cmp` of all package copies | Your PC | 23 OK; all identical |

**Checks that could not be completed:**
- **Tests on your PC copy:** the PC's command environment has no `pytest`. The cloud files are byte-identical,
  so the result should transfer, but it was not executed on your machine. Run
  `py -m pytest tests/test_sessions.py` there.
- **Development counts (1,308 → 1,230):** not re-derived. That needs `reconcile_counts.py` to open the
  real-data files (timestamps only), which this assignment's stop conditions put out of scope. [PRIOR]
- **D8 full-text review:** not possible without Interlibrary Loan. [OPEN]

## 8. Is the package ready to send?

**Yes, with a cover note.** It is complete, checksum-verified and byte-identical to the working tree. It
contains no approval claim. It needs three items alongside it:
1. this audit, so PD-1 to PD-13 travel with it;
2. `INDEPENDENT_REVIEW_GUIDE_v1.md` and `REMAINING_LIMITATIONS_v1.md`;
3. the repository at HEAD `a48eaac` plus the untracked files listed in §1, so the tests can be run.

**None of the discrepancies needs a research-rule change.** PD-4 and PD-3 are wording issues for a possible
v4.3, which would itself need your approval.
