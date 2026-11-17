# Final review handoff manifest, v1: overnight vs regular-session study

Written 2026-11-12 ~23:00 CT (2026-11-13 ~05:00 UTC).

**Revision 2 (2026-11-12 ~23:50 CT).** Records Ethan's Windows test run (§8) and the 13,745 pandas deprecation
warnings (§8a), and adds three evidence files (§6). The 55-file snapshot, the bundle and the overlay are
**unchanged**, so documents inside the snapshot were deliberately not edited (§8b).

**Revision 3 (2026-11-12 ~23:45 CT).** Ethan supplied the complete PowerShell transcript, and his `Tee-Object` capture
is on the PC. The Windows result is now **evidence-backed, not just reported**, and the pandas version is
**confirmed as 3.1.1** (§8, §8a). Two evidence files were added (§6). The snapshot, bundle and overlay are still
unchanged.

This manifest identifies **exactly** the project snapshot an independent reviewer should receive and test.
- **Protocol v4.2 is an unsigned draft and is not approved.** v4.1 and v4.2 were not edited, and no v4.3 exists.
- No real price was loaded and no study result was calculated.
- Nothing was committed or pushed.

**Evidence labels:**
- **[CODE]** verified by inspection;
- **[SYNTH]** verified by synthetic testing;
- **[RUN]** a command was executed and its output is saved in `docs/review_handoff_v1/evidence/`;
- **[PRIOR]** reported earlier and not re-verified;
- **[OPEN]** unresolved.

---

## 1. Exact snapshot

| Item | Value |
|---|---|
| Repository | `C:\Users\thebo\OneDrive\Documents\nq_bot` (origin `github.com/ethanfilbeck/nq-futures-strategy-lab`) |
| Commit | **`a48eaac8d7825ef8171d9762de27fcc33b3d3798`** on `main`, equal to `origin/main` |
| Working-tree changes tested | **2 modified tracked files + 53 untracked files = 55 files** (§2–3) |
| Added after testing, for handoff only | `docs/review_handoff_v1/` (15 files since revision 3, §6) and this manifest |

**How the snapshot is delivered:**
1. **`nq_bot_a48eaac.bundle`**: a git bundle of `main` at `a48eaac`, with complete history (`git bundle verify`: OK).
2. **`working_tree_overlay.tar.gz`**: the 55 working-tree files with their paths.
3. **`WORKING_TREE_INVENTORY.txt`**: status, SHA-256, size and path of each of the 55.

**Reconstruction has been verified twice [RUN]:**
- **On the Linux shell attached to your PC:** clone the bundle → check out `a48eaac` → extract the overlay.
  Result: **55/55 files match the inventory**, and `git status` shows the same 55 changes.
- **In the cloud workspace:** the same reconstruction from the staged copies gives **55/55 matches**, and the
  tests in §8 were run on that reconstructed tree.

**Reviewer's reconstruction commands:**

```
git clone -b main nq_bot_a48eaac.bundle nq_bot && cd nq_bot
git rev-parse HEAD                          # must print a48eaac8d7825ef8171d9762de27fcc33b3d3798
tar -xzf ../working_tree_overlay.tar.gz     # restores the 55 files
# verify: every line "<status> <sha256> <bytes> <path>" of WORKING_TREE_INVENTORY.txt
#         must satisfy  sha256(<path>) == <sha256>
```

**Rebuild check (rev. 3)** [RUN]:
- The overlay is reproducible byte for byte: rebuilding it gives the same SHA-256 (`0c23df51…`).
- The bundle is **not** byte-reproducible, because git may pack the same objects differently. Rebuilding it gave
  `28ccee07…` instead of `3f3f87f1…`. Both bundles verify, record `main` = `a48eaac`, and contain the identical set
  of 570 objects.
- So send the **original** `nq_bot_a48eaac.bundle` (`3f3f87f1…`). A reviewer should check the bundle by the commit
  hash and `git bundle verify`, not by rebuilding it.

`-b main` is needed: without it, `git clone` warns "remote HEAD refers to nonexistent ref". A plain
`git checkout a48eaac` after cloning also works.

## 2. Modified tracked files (2)

| File | SHA-256 (working tree) | Change against `a48eaac` |
|---|---|---|
| `pytest.ini` | `70e05743b7c622702640084e61b59780d28756ba0b82d7cfdf1b36d93a7197c3` | Adds the `slow` marker (2 lines) |
| `tests/test_tooling.py` | `b204db943bc611a5ef16ac5357f23e828d988ad3e5915b2f91339711f4e9aa01` | Adds `"sessions"` to the RESEARCH list, so the broker-import guard also checks `nq_bot/sessions.py` (1 line) |

Full diff: `docs/review_handoff_v1/tracked_modifications_vs_a48eaac.diff`.

## 3. Untracked files (53)

The full list, with SHA-256 and sizes, is in `WORKING_TREE_INVENTORY.txt`.

| Group | Files | Key hashes |
|---|---|---|
| Study code | `nq_bot/sessions.py`, `run_sessions_study.py`, `tests/test_sessions.py`, `tests/sessions_synth.py`, `scripts/sessions_calibration.py`, `scripts/sessions_calibration_p1_b9999.py` | `4bb9b7f4…`, `d4176746…`, `24ce2848…`, `5536e067…`, `ef815568…`, `f5d29f81…` |
| Pre-flight scripts (timestamp-only; hashes recorded in protocol §13) | `scripts/sessions_preflight/` (6 files) | `251eb57e…`, `4727b928…`, `895f4068…`, `ec850ce0…`, `84d3890c…`, `7848b5de…`, all matching §13 |
| Reviewer aid (new; PD-4) | `scripts/review/holm_v41_v42_comparison.py` | `6dea2e83…` |
| Protocols | `docs/DRAFT_PREREG_SESSIONS_awaiting_signoff.md` (**v4.1, historical**), `docs/DRAFT_PREREG_SESSIONS_v4.2_awaiting_signoff.md` (**v4.2, unsigned**) | §4 |
| Calibration | `docs/SESSIONS_CALIBRATION.json`, `docs/SESSIONS_CALIBRATION_P1_B9999.json` | `e32b7992…`, `3fba6b9d…` |
| Inventory | `docs/HOLDOUT_EXPOSURE_SESSIONS.csv`, `docs/HOLDOUT_EXPOSURE_INVENTORY.md` | `a462425b…` (matches the runner pin), `586bd177…` |
| Study documents | `LITERATURE_SESSIONS.md`, `DATA_FEASIBILITY_SESSIONS.md`, `SESSIONS_ADDENDUM_U7_L4.md`, `SESSIONS_FINAL_AUDIT_v5.md`, `SESSIONS_RESEARCH_AUDIT_v3.md` and `…_v4.md` (historical), `SESSIONS_SYNTHETIC_TEST_REPORT.md` (historical, report v2) | inventory |
| Independent-review documents | `docs/INDEPENDENT_REVIEW_GUIDE_v1.md` (revision 2), `docs/INDEPENDENT_REVIEW_PACKAGE_AUDIT_v1.md`, `docs/REMAINING_LIMITATIONS_v1.md` | `8acf5e1a…`, `cc094563…`, `05c805d5…` |
| Review package | `docs/review_package_sessions_v4.2/` (23 files plus `MANIFEST.sha256`) | §5 |

**Deliberately not included** (git-ignored, not part of the tested study code) [CODE]:
- `data/`: the licensed Databento files. Not redistributable. Only real-data runs need them, and those are
  not authorized.
- `.env`: possible secrets.
- Ignored outputs from earlier phases under `runs/`.
- `logs/`, `_to_delete/` and caches.

The synthetic tests need none of these.

## 4. Protocol hashes [CODE][RUN]

| File | Version | SHA-256 |
|---|---|---|
| `docs/DRAFT_PREREG_SESSIONS_awaiting_signoff.md` | **v4.1, historical, preserved** | `716e00037ab4d7e20b9f9a44a0af6a146e646f1f631101470a2c8ceb37506021` |
| `docs/DRAFT_PREREG_SESSIONS_v4.2_awaiting_signoff.md` | **v4.2, current, unsigned, not approved** | `99b54fd3571885baae6d58677513dbc43327c6731242914ebd0fe936afecebea` |
| `docs/PREREG_HASH.txt` | Unchanged against `a48eaac` (11 lines). **Contains neither v4.1 nor v4.2.** | — |

## 5. Review package

| Item | Value |
|---|---|
| `docs/review_package_sessions_v4.2/MANIFEST.sha256` | SHA-256 **`ff391179e67312bda7f0b781f3502091f8beb98603846c3c17335f795105e824`** |
| `sha256sum -c MANIFEST.sha256` (on your PC) | **23/23 OK** [RUN] |
| Package copies against working-tree originals | All identical (package audit §2) |

## 6. Handoff folder `docs/review_handoff_v1/` (created after testing)

| File | SHA-256 | Purpose |
|---|---|---|
| `nq_bot_a48eaac.bundle` | `3f3f87f19ff1d6443156fc3d65dafc19dc8edf8409634ffd44e903d49a637106` | Commit `a48eaac` with full history |
| `working_tree_overlay.tar.gz` | `0c23df51948e039ea2c7566436595c52d0a2fee61e922542928fb84684b801bb` | The 55 working-tree files |
| `WORKING_TREE_INVENTORY.txt` | `3625c65677433a2467332e0e9659a90e4ae60bc851e9c44460f31d8bf65e494e` | Per-file hashes of the 55 |
| `tracked_modifications_vs_a48eaac.diff` | `438d909675b42266727b0abeeb1589eb0bf48a21631cb029bc83f445380eb4d0` | Diff of the 2 modified tracked files |
| `evidence/pc_test_run_test_sessions.txt` | `19a8e88d0daeabe7026ac7aa3cf691b7732f85074108e2c1cfe05ce88c222c0c` | Test run on your PC's files (§8) |
| `evidence/pc_collected_nodeids.txt` | `a2a36ad2a563523f31c2d8acd5861e97895b1bea28ce8b1fdca294fb4fc01bd7` | The 136 collected test ids |
| `evidence/cloud_reconstructed_snapshot_checks.txt` | `dba2cae6d79d621e6a6f9ec1b0fec4c7bbfdaddcfbff98a28daa062c30f12688` | Tests and checks on the reconstructed snapshot |
| `evidence/reconcile_counts_output_pc.txt` | `02e6de211781960602301e8bd48094a25b002a861dda4c78431a98472530c6f9` | Timestamp-only count verification (§9) |
| `evidence/holm_v41_v42_comparison_output_pc.txt` and `…_cloud.txt` | both `9e7e8f8183dd18e2cfb36e1d802a23285d93ed3ae53d5b5d11ce66c2987bd9c2` | PD-4 comparison, identical on both machines |
| `evidence/windows_pytest_run_REPORTED_SUMMARY.txt` (rev. 2) | `0302a8a717676faef4ad575786cadde2ae1c964f80e3b55e99db911394bd6f07` | Ethan's reported summary, written before the full output arrived. **Superseded by the two rev. 3 files**, and kept unedited as history. |
| `evidence/pandas_deprecation_warnings_reproduction.txt` (rev. 2) | `8cd2e2332ebbe082aa4f61605f352dc3c88b6e48e3062e5e932f70c2c0027f7b` | Reproduction and analysis of the 13,745 warnings |
| `evidence/windows_powershell_transcript_2026-11-12.txt` (rev. 3) | `bf56e059dc64fda304f2fa39d4228b35c752776e8b3a27d0abd49709f735f376` | **Complete PowerShell session supplied by Ethan, verbatim**: failed System32 attempt, the `-v` run (146.03 s), the version print and the captured run (141.73 s) |
| `evidence/windows_pytest_test_sessions_full_output.txt` (rev. 3; written on Windows by `Tee-Object`, CRLF line endings) | `3eadbc45adb6f230660ffe70e0cafcef8279faa647e752a039115eee18e23587` | Versions plus the full 136-test run |
| `evidence/pandas_deprecation_warnings_counts.json` (rev. 2) | `fc439c1e32a2baf0cf2ce5cfda76f5415289561d5cb4ac1479474e9fee45405e` | Warning counts by source line |

## 7. Holm wording discrepancy (preserved; v4.2 not edited)

- v4.2 §7 says that under the V1 placeholder the four tests "face the same thresholds as in v4.1 whenever V1
  was not significant".
- `scripts/review/holm_v41_v42_comparison.py` (seed 1, 200,000 random p-vectors) gave the same output on your
  PC and in the cloud [RUN]:
  - **188,433** cases had V1 not rejected under v4.1;
  - **0** differed in any rejection decision;
  - **69,935 (37.1%)** differed in at least one Holm-adjusted p-value.
- **The rejection decisions are identical. The thresholds faced by tests ranked after V1, and the adjusted
  p-values, are not.**
- The reviewer is asked (guide §4, checklist **H-d**) whether the protocol wording accurately represents the
  implementation.

## 8. Test results

| Run | Tree | Environment | Result |
|---|---|---|---|
| **`py -m pytest tests/test_sessions.py -v` on Windows** (run by Ethan from `C:\Users\thebo\OneDrive\Documents\nq_bot`) | **Your PC's working tree**: the handed-off tree (it matched the inventory before and after; the run's `__pycache__` files are dated after this snapshot was built) | Windows 11, PowerShell 7.7.0, Python 3.12.10, numpy 2.5.4, pandas 3.1.1, pytest 9.2.0 | **136 collected, 136 passed, 0 failed, 0 skipped, 13,745 warnings, 146.03 s.** A second identical run captured with `Tee-Object` gave **136 passed, 13,745 warnings, 141.73 s**. Versions printed in that capture: **Python 3.12.10, numpy 2.5.4, pandas 3.1.1, pytest 9.2.0**. Full output: `evidence/windows_powershell_transcript_2026-11-12.txt` (whole session, verbatim) and `evidence/windows_pytest_test_sessions_full_output.txt` (the capture; identical to transcript lines 321–517 apart from line endings). [RUN, by Ethan; output preserved] |
| `tests/test_sessions.py`, all 136 collected tests, run in pieces (4 batches of 12, then 88 one at a time; each shell call is limited to 180 s) [RUN] | **Your PC's working tree** (CRLF line endings on 59 tracked files, see §10) | Linux shell attached to your PC: Python 3.10.12, numpy 2.2.6, pandas 2.3.3, pytest 9.2.0 | **136 of 136 passed**, every one exit code 0. Not a single uninterrupted run. |
| `python -m pytest tests/test_sessions.py -W error::RuntimeWarning` [RUN] | **Reconstructed snapshot** (bundle + overlay) | Cloud: Python 3.13, numpy 2.5.4 | **136 passed** in 209.7 s |
| `python scripts/check.py` [RUN] | **Reconstructed snapshot** | Cloud | **RESULT: FAILED.** ruff **FAIL** (65 findings); pytest PASS (254 passed, 2 skipped: the old webhook tests needing `data/mnq_train.csv`); prereg PASS (11 hashes); prepublish PASS; pip-audit PASS; mypy **FAIL** (20 errors) |
| ruff and mypy restricted to the study code (excluding `scripts/sessions_preflight/` and the `docs/` package copies) [RUN] | Reconstructed snapshot | Cloud | ruff: all checks passed; mypy: no issues in 48 files |

**The first attempt, from `C:\Windows\System32`, was not a test result.** The transcript shows:
- pytest's root directory was `C:\Windows\System32`;
- "collected 0 items" and `UsageError: file or directory not found: tests/test_sessions.py`;
- then a `KeyboardInterrupt` while pytest tried to write its cache directory there (no `pytest.ini`, so the cache
  was enabled).

No test ran. Pytest may have left a `.pytest_cache` folder in `C:\Windows\System32`. It is harmless and outside
the project, and I did not check for it.

### 8a. The 13,745 warnings in the Windows run (not suppressed)

**Reproduced exactly** [RUN]:
- Setup: the reconstructed snapshot, run in a cloud environment with **pandas 3.1.1**, numpy 2.5.4, Python 3.13.18.
- Result: **136 passed, 13,745 warnings**, the same count on two runs.
- The same tests give **0** warnings with pandas 2.3.3 (the Linux shell attached to your PC) and with pandas 3.0.5
  (the cloud default).
- **Confirmed (rev. 3):** the Windows capture prints `pandas 3.1.1`, and its warnings summary lists the same source
  lines and per-line counts as the table below (10,829 at `sessions.py:266`, 2,900 at `test_sessions.py:568`, …).

**What they are.** All of them are `Pandas4Warning` deprecations, meaning names scheduled for removal in a future
pandas major version.

| Count | Source | Deprecated | pandas' replacement |
|---|---|---|---|
| 10,829 | `nq_bot/sessions.py:266` (`build_sample`, weekday column, once per session) | `Timestamp.dayofweek` | `day_of_week` |
| 2,900 | `tests/test_sessions.py:568` | `Timestamp.dayofweek` | `day_of_week` |
| 9 | `nq_bot/sessions.py:748` (`o2_secondary`) | `DatetimeIndex.dayofweek` | `day_of_week` |
| 6 | `tests/test_sessions.py:345, 515, 519, 520, 612`; `scripts/sessions_calibration.py:37` | `DatetimeIndex.dayofweek` | `day_of_week` |
| 1 | `tests/test_sessions.py:83` | `DataFrame.join(rsuffix=…)` | `suffixes=` |

Machine-readable counts: `evidence/pandas_deprecation_warnings_counts.json`.

**Effect on results:**
- **Today, none.** The old and new names return identical values, and every test passes.
- **Future risk.** Once pandas removes `dayofweek`, `nq_bot/sessions.py` (including the real-data path),
  `scripts/sessions_calibration.py` and the tests would fail with `AttributeError`.
- **Not fixed and not suppressed.** Renaming is mechanical and doesn't change the method, but it would change
  hash-recorded, tested files, so it needs your decision. The alternative is to pin `pandas<4` for any future
  run.

### 8b. Documents inside the snapshot left as they were

- `docs/REMAINING_LIMITATIONS_v1.md` (item L-PC) and the package audit (§7) still say the tests were not run on
  your PC.
- **This manifest supersedes them on that point.** They were not edited, because editing them would change the
  checksummed 55-file snapshot and the overlay.

**Why `check.py` fails on the full snapshot [CODE]:**
- **60 ruff findings and all 20 mypy errors** come from the six **pre-flight scripts** in
  `scripts/sessions_preflight/`. They are short exec-style scripts that were never linted. Their hashes are
  recorded in protocol §13, so they were **not** edited.
- **5 ruff findings (S607)** come from the **review-package copy** of `tests/test_sessions.py` under `docs/`.
  The project's ruff configuration allows S607 only under `tests/`; the copy is byte-identical to the
  passing original.
- The earlier "all gates pass" results came from a workspace that did not contain these two groups of files.
- **No change was made.** Fixing it means either editing hash-recorded scripts or changing the lint
  configuration, which needs your decision.

## 9. Development counts: timestamp-only verification [RUN]

**What was run, and why it is safe:**
- `scripts/sessions_preflight/reconcile_counts.py` (`84d3890c…`), which executes the first part of
  `verify_counts_and_rolls.py` (`7848b5de…`); both hashes match protocol §13.
- Inputs: `data/mnq_train.csv` (`a2d8d017…`) and `data/mnq_holdout.csv` (`8b00498f…`), both matching the
  runner pins, plus `runs/rollmap_MNQ.json`.
- **Only the `timestamp` column was read** (`usecols=['timestamp']`, plus a header-only read with
  `nrows=0`). **No open, high, low, close or volume value was loaded**, and no study statistic was computed.
- Its inline FOMC lists equal `family3.FOMC_DAYS` within the development window (43 dates) and
  `family3.HOLDOUT_FOMC_DAYS` (11) [RUN].

| Step | Development (re-run) | Frozen | Holdout (re-run) | Frozen |
|---|---|---|---|---|
| Sessions with ≥ 1 RTH bar | 1,417 | 1,417 | 346 | 346 |
| After E1 (early close) | 1,371 (−46) | 1,371 | 334 (−12) | 334 |
| After E2 | 1,332 (−39) | 1,332 | 324 (−10) | 324 |
| After E3 | 1,332 (−0) | 1,332 | 324 (−0) | 324 |
| After E4 (roll) | 1,311 (−21) | 1,311 | 319 (−5) | 319 |
| **After E5 = eligible** | **1,308** (−3) | **1,308** ✓ | **318** (−1) | **318** ✓ |
| **After E6 = primary** | **1,230** (−78) | **1,230** ✓ | **297** (−21) | **297** ✓ |
| Standalone E6 (overlaps with E4) | 86 (8) | 86 (8) | 22 (1) | 22 (1) |

**All counts reproduce exactly.**

**Limits of this verification:**
- It is a **re-run of the original derivation script**, not an independent second implementation, and not
  by an independent party.
- The analysis module's own `build_sample` was not run on real data, because it requires prices. Its count
  gate will check 1,308 / 1,230 at the first authorized real-data run.

## 10. New findings in this pass (reported, not fixed)

| ID | Finding | Evidence | Effect |
|---|---|---|---|
| HF-1 | `scripts/check.py` fails on the complete snapshot (§8) | [RUN] | The project's quality gate is red for the tree as handed off. Tests are unaffected. |
| HF-2 | **Line endings.** On your PC, 59 tracked files have CRLF endings (Windows checkout with `core.autocrlf=true`). A fresh checkout from the bundle gives LF. The differences are line endings only (59/59 identical after removing CR). | [RUN] | The runner pins `runs/rollmap_MNQ.json` to `e1beaeed…`, the **CRLF** bytes on your PC. An LF checkout gives `eaded078…`, so `verify_pins` would refuse a real-data run on a reviewer's Linux checkout. Synthetic tests are unaffected. `nq_bot/family3.py` (pinned) is LF on both. |
| HF-3 | `.git/objects` holds 160 leftover `tmp_obj_*` files (311 KB), probably from earlier interrupted git operations in the synced folder. `git fsck --no-dangling` reports no errors. | [RUN] | Cosmetic. The bundle verifies. |
| HF-4 | The bundle contains the repository's **full history**, including earlier non-study work (`nq_bot/broker/`, `live.py`, `webhook.py`), the same as on GitHub | [CODE] | The study code imports none of it (guide §9). Share the bundle only with someone you'd share the repository with. |

## 11. Remaining unresolved questions

1. **P1 validity:** it rejects 1.33–1.50% at nominal 1% and is not fixed by more resamples. Is the method
   valid, should P1 become descriptive only, and what evidence would be needed? [OPEN]
2. **Family-wise error:** not verified at 1%. P1's rates at 0.0025, 0.0033 and 0.005 were never measured.
   [OPEN]
3. **Holm wording (PD-4, H-d):** does v4.2 accurately describe the implementation? [OPEN]
4. **V1:** should its descriptive interval be reported at all, given 80% coverage in scenario 2? [OPEN]
5. **Calibration realism:** no censoring, missing bars, roll jumps or volume variation in the Monte Carlo.
   [OPEN]
6. **D8:** Liu & Tse (2017) and Riedel & Wagner (2015) are unreviewed; T1's expected direction rests on an
   abstract. [OPEN]
7. **HF-1:** how to bring `check.py` to green without editing hash-recorded scripts. [OPEN; your decision]
8. **HF-2:** whether pinned hashes should be made line-ending-independent before any real-data run. [OPEN]
9. **Windows test run:** 136/136 passed, twice, with full output preserved (§8). [RESOLVED]
10. **pandas deprecations (§8a; pandas 3.1.1 confirmed on Windows):** rename `dayofweek` → `day_of_week` (changes tested files) or pin `pandas<4`. [OPEN; your decision]
11. **Protocol sign-off:** v4.2 unsigned; freeze procedure (PD-9). [OPEN]

The full register is in `docs/REMAINING_LIMITATIONS_v1.md`; package discrepancies PD-1 to PD-13 are in
`docs/INDEPENDENT_REVIEW_PACKAGE_AUDIT_v1.md`.

## 12. Exact files the reviewer must receive

**Required:**
1. `docs/review_handoff_v1/nq_bot_a48eaac.bundle`
2. `docs/review_handoff_v1/working_tree_overlay.tar.gz`
3. `docs/review_handoff_v1/WORKING_TREE_INVENTORY.txt`
4. `docs/FINAL_REVIEW_HANDOFF_MANIFEST_v1.md` (this file; send its SHA-256 separately)

Items 1–3 together contain everything else the reviewer needs:
- commit `a48eaac`;
- the 2 modified tracked files;
- all 53 untracked files, including protocol v4.1 and v4.2, the 23-file review package with its checksum
  list, the three independent-review documents, and both calibration artifacts.

**Recommended:** `docs/review_handoff_v1/tracked_modifications_vs_a48eaac.diff` and
`docs/review_handoff_v1/evidence/` (11 files).

**Not to be sent:** `data/` (licensed) and `.env`.
