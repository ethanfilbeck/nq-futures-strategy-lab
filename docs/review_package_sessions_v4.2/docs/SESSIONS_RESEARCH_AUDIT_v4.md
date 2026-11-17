# Overnight vs regular-session study: research audit v4 (decisions U8, U9, L4, P1 diagnostic, D8)

Written 2026-11-12 / 13. **Synthetic data only.**
- Development and testing used a cloud copy of the repository with **no `data/` folder**.
- **No real NQ or MNQ price was loaded, and no study result was calculated.**
- Nothing was committed or pushed. `PREREG_HASH.txt` is unchanged (11 lines).
- Report v2, audit v3 and `SESSIONS_CALIBRATION.json` are kept unchanged. This audit supersedes v3 for the
  items below.

---

## 1. U8: five Holm slots, V1 placeholder 1.0 (approved; implemented)

- New function `holm_with_placeholder` is the only route into Holm from `run_family`.
  - It builds the five-slot family with V1's slot set to `HOLM_PLACEHOLDER_P = 1.0`.
  - It rejects any family that is not exactly V1, T1, T2, P1 and L1, so the V1 slot cannot be dropped.
- **Documented in code, in every result file (`holm_family.placeholder_note`) and in the addendum (§A1):**
  - 1.0 is an **administrative placeholder, not an observed V1 p-value**;
  - V1 is **descriptive only** and **cannot establish significance**;
  - T1, T2, P1 and L1 **keep their existing definitions**;
  - the five-slot correction is **intentionally conservative**.
- **Thresholds are unchanged.** In step-down order they are 0.002, 0.0025, 0.0033 and 0.005; V1 is never
  rejected.
- **Tests:**
  - `test_u8_v1_cannot_change_holm_adjusted_results_of_the_other_four` (requested). For 2,000 random p-vectors
    × 7 observed V1 values (10⁻⁹ … 1), the adjusted p-values and decisions of the four are always identical.
  - `test_u8_thresholds_are_the_frozen_five_slot_ones`. Exact boundaries; the first step failing stops all.
  - `test_u8_run_family_uses_the_placeholder_and_documents_it`.
  - The earlier `test_u7_other_four_tests_do_not_depend_on_v1` also still passes.

## 2. U9: protocol review. The halt IS pre-registered, so I stopped and changed nothing.

Exact wording in `DRAFT_PREREG_SESSIONS_awaiting_signoff.md` (v4.1, SHA-256 `716e0003…37506021`):
- **§7, bullet after the effect-size table:** "**Pipeline check:** V1 not established in development → halt,
  and report a data or code fault."
- **§6.1, tested-family table, V1 row:** "L > 0. **Calibration check.**"

**What this means:**
- The protocol requires more than a positive V1 estimate: it requires V1 to be *established*, which needs
  significance.
- Under U7, V1 can never be established, so §7 read literally halts **every** run.
- The code still holds last round's unapproved U9 variant (halt if the V1 estimate ≤ 0). Comments now mark it
  **PENDING**.
- I made no further change. Removing the halt would alter a frozen requirement, which needs your explicit
  ruling and a documented protocol version update.

**Options (addendum §A2):**
- (a) Remove the §7 check, keeping every integrity and failure gate. This is your proposal, and needs v4.2.
- (b) Keep the ≤ 0 variant as a versioned clarification. You have already declined this.
- (c) Keep §7 literally, which is unworkable with U7.

**Unaffected either way:**
- All data-integrity checks: pinned hashes, frozen-count gates and `DataIntegrityError` paths.
- All computation-failure guards: non-finite bootstrap, minimum sizes and the B guard.
- V1 cannot influence the official verdict (§6 below).

## 3. L4: 60 prior averages (approved; frozen)

**Exact relationship, one-based numbering:**
- Session *s* has a 20-session average T_s = mean RV_RTH of sessions *s−20 … s−1*. It exists only for
  *s* ≥ 21.
- Before session *s* there are *s − 21* such averages (T_21 … T_{s−1}).
- The fixed minimum of 60 is first met at ***s* = 81**. Its cut-offs use T_21 … T_80, built from RV of sessions
  1–79.
- **Sessions 1–80 are unassigned. Session 81 is the first assigned. Session 80 has only 59 prior averages.**

**Discrepancy to confirm.** Your approval says "first eligible assignment at session 80 using one-based
numbering". With 60 prior averages that is session 81. The "80" in audit v3 was the zero-based code index.
Making session 80 eligible would need 59, which would change the frozen 60, so **nothing was changed**.

**Verified:**
- `test_l4_one_based_numbering_of_the_warm_up` (new): one-based sessions 1–80 unassigned, 81 assigned; 59 vs
  60 prior averages.
- The four L4 tests from v3 still pass (boundary, hand-computed cut-offs, no look-ahead at 79/80/81, 80
  unassigned for every n).
- The U5 future-replacement test still passes.

The minimum stays fixed and was not tuned on any result. Sample counts are unaffected.

## 4. P1 diagnostic calibration rerun, 9,999 inner resamples (approved; synthetic only)

**Setup:**
- **Method:** the frozen production code path, unchanged: `point_stats`, `stationary_indices` (mean block 20),
  `bootstrap_family`, `centered_p` and `percentile_ci`.
- **Data:** the existing data generators, imported unchanged from `scripts/sessions_calibration.py`, whose hash
  `ef815568…` is unchanged.
- **Scenarios:** 4 (iid Gaussian) and 8 (common GARCH volatility), with n = 1,230 and 20,000 repetitions each.
- **Paired design:** every repetition computes P1 with **both** B = 999 and B = 9,999 on the **same**
  synthetic dataset.
- **Seeds:** data `default_rng([scenario, rep, 1])`; bootstrap `default_rng([scenario, rep, 2])`, a fresh
  generator for each B. These are identical to the original seed rule.
- **Environment:** Python 3.13.18, numpy 2.5.4, 2 workers.
- **Run:** in 16 resumable chunks. One container restart occurred; the interrupted chunk was re-run from its
  seeds, and every repetition 0–19,999 is present exactly once.
- **Script:** `scripts/sessions_calibration_p1_b9999.py` (new). Output: `SESSIONS_CALIBRATION_P1_B9999.json`
  (new).
- **Original artifacts:** `SESSIONS_CALIBRATION.json` (`e32b7992…`) is untouched.

**Reproducibility check.** The B = 999 arm reproduces the original calibration **exactly**:
- scenario 4: 1,181 / 266 / 65 rejections and 19,675 covered;
- scenario 8: 1,200 / 300 / 66 and 19,661.

**False-positive rates (true null; Wilson 95% intervals):**

| Scenario | Level | Expected | B = 999 | B = 9,999 | Paired: rejected by 999 only / 9,999 only | McNemar z |
|---|---|---|---|---|---|---|
| 4 iid | 5% | 1,000 | 1,181 = 5.91% (5.59–6.24) | 1,194 = 5.97% (5.65–6.31) | 54 / 67 | 1.18 |
| 4 iid | **1%** | 200 | **266 = 1.33% (1.18–1.50)** | **267 = 1.34% (1.19–1.50)** | 22 / 23 | 0.15 |
| 4 iid | 0.2% | 40 | 65 = 0.33% (0.26–0.41) | 68 = 0.34% (0.27–0.43) | 11 / 14 | 0.60 |
| 8 common GARCH | 5% | 1,000 | 1,200 = 6.00% (5.68–6.34) | 1,199 = 6.00% (5.67–6.33) | 57 / 56 | −0.09 |
| 8 common GARCH | **1%** | 200 | **300 = 1.50% (1.34–1.68)** | **300 = 1.50% (1.34–1.68)** | 32 / 32 | 0.00 |
| 8 common GARCH | 0.2% | 40 | 66 = 0.33% (0.26–0.42) | 66 = 0.33% (0.26–0.42) | 19 / 19 | 0.00 |

**Coverage of the nominal 99% interval (19,800 expected):**

| Scenario | B = 999 | B = 9,999 | Covered by 999 only / 9,999 only | McNemar z |
|---|---|---|---|---|
| 4 | 98.38% (98.19–98.54) | 98.59% (98.41–98.74) | 24 / 66 | 4.43 |
| 8 | 98.31% (98.12–98.47) | 98.48% (98.30–98.64) | 30 / 64 | 3.51 |

The correlation of the paired p-values is 0.9989 in both scenarios.

**Interpretation:**
1. **The over-rejection belongs to the method, not to the resample count.** At 1% and 0.2% the B = 9,999
   rates are essentially identical to B = 999: 1.33% → 1.34% and 1.50% → 1.50%. Disagreements are few and
   balanced (McNemar |z| ≤ 1.2). P1's centered block-bootstrap test at n = 1,230 is mildly liberal under both
   null scenarios. The frozen B = 10,000 will not remove this.
2. **Coverage has a small resample-count component.** It improves by 0.17–0.21 points with 9,999 resamples,
   which is statistically clear (McNemar z = 3.5–4.4). It stays **below 99%**: both Wilson upper bounds are
   below 98.75%. Most of the shortfall (about 0.4–0.5 points) is therefore the method's finite-sample
   behaviour.
3. **No method, threshold or protocol rule was changed.** The results update only the disclosure:
   - P1 is mildly liberal, about 1.3–1.5× nominal at 1% and 1.65× at 0.2%;
   - its 99% intervals cover about 98.5% even with about 10,000 resamples;
   - the cause is the method, not B.
4. **Runtime:** about 0.45–0.65 s per paired repetition (≈ 6 h of wall time).

## 5. D8

Unchanged from audit v3 §3.
- Liu & Tse (2017) and Riedel & Wagner (2015) have library catalogue records with **no full text**.
- Both remain **not reviewed**; nothing was substituted.
- Interlibrary Loan needs your sign-in.

## 6. Final checks

| # | Check | Result |
|---|---|---|
| 1 | Isolated synthetic tests: `python -m pytest tests/test_sessions.py` (fast + slow) | **134 passed**, 0 failed (130 in v3, plus 3 U8 tests and 1 one-based L4 test) |
| 2 | `scripts/check.py`: ruff, pytest, prereg, prepublish, pip-audit, mypy | **All PASS.** pytest 252 passed, 2 skipped (the old webhook tests: "needs data/mnq_train.csv (not in the repo)"). **11 pre-registration hashes unchanged.** |
| 3 | Holm correction | The U8 tests pass (2,000 × 7 property test, exact boundaries, `run_family` wiring). m = 5 and α = 0.01 are unchanged. |
| 4 | V1 cannot influence the official verdict | `test_u7_official_verdict_ignores_every_v1_input` (15 cases) passes; `official_verdict` never reads V1's inputs. Holm: V1 shifted to p = 1/(B+1) leaves all four other tests identical. |
| 5 | O2 cannot influence the official verdict | `test_o2_cannot_change_the_official_verdict_removed_randomised_altered` passes. The verdict file is identical with O2 prices randomised, O2 removed and O2 membership altered, and is written before O2 is computed. |
| 6 | Frozen sample counts | Development 1,308 / 1,230 and holdout 318 / 297 in `run_sessions_study.py` are unchanged. All MIN_\*, α, m, B, seeds, block length, EWMA, Hill fraction, tercile constants and DIRECTION are unchanged (line-by-line comparison with audit v3). |
| 7 | Protocol hash | `DRAFT_PREREG_SESSIONS_awaiting_signoff.md` is still `716e00037ab4…37506021`. **No version update was made**: the only candidate (removing the §7 V1 halt) awaits your ruling (§2). |
| 8 | No real market prices loaded | The cloud copy has no `data/` folder. The U6 autouse guard blocks any read under `data/` in every sessions test. The calibration and diagnostic use generated numbers only. |
| 9 | No actual study results | No development or holdout run was executed; `runs/` holds only synthetic calibration output. |

## 7. Remaining limitations and unresolved issues

| # | Item | Status |
|---|---|---|
| **U9** | §7 pre-registers a V1 halt ("V1 not established in development → halt"); unworkable with U7. The code holds the unapproved ≤ 0 variant, marked PENDING. | **Your ruling needed:** (a) remove the check and version the protocol to v4.2, (b) keep the variant, or (c) keep it literally |
| **L4 numbering** | With 60 prior averages, the first eligible session is **81 (one-based)**, not 80 | **Confirm** |
| L1 (updated) | P1 is mildly liberal (1.33–1.50% at 1%; 0.33–0.34% at 0.2%) **because of the method, not B**. Its 99% intervals cover about 98.5% even with 9,999 resamples. The four-test Holm family can exceed 1% FWER slightly. | Disclose |
| L2 | T1/T2 are conservative (about 0.3% at 1%), so power is lower | Disclose |
| L3 (narrowed) | B = 999 vs 10,000 now measured for P1: no effect on size, +0.2 points coverage. Not measured for T1, T2 or L1. | Disclose |
| L5 | No price-limit censoring or missing data inside the Monte Carlo | Disclose |
| L6 | Tail regime stability is not assessable for 2020–2022 (U2) | Accepted |
| L7 | P1 uses MNQ volume as the price-discovery proxy | Disclosed in the protocol |
| L8 | Real-data entry points are untested end to end, by design | After sign-off only |
| L10 | V1's descriptive interval can be badly over-confident (scenario 2: 80% coverage) | Disclosed (U7) |
| L11 | The earliest volatility groups rest on overlapping averages from January–April 2020 | Disclose |
| D8 | Liu & Tse and Riedel & Wagner have not been reviewed (no full text) | Interlibrary Loan needs your sign-in |
| — | Sign-off and hashing of v4.1 plus the addendum | Before any real-data run |

## 8. Exact files changed this round (all uncommitted)

| File | Change this round | Lines | SHA-256 |
|---|---|---|---|
| `nq_bot/sessions.py` | U8: `HOLM_PLACEHOLDER_P`, `HOLM_PLACEHOLDER_NOTE`, `holm_with_placeholder`, `run_family` wiring, note in `holm_family`; PENDING comment on the U9 check (no behaviour change) | 920 | `d77343b0dacc3fb4f47bbccf9b1e406ce68e8a595fac11491df3a000b477af1d` |
| `run_sessions_study.py` | PENDING comment on the U9 halt only (no behaviour change) | 313 | `f0420a2f61a89e1c9cbd1596cea1c76e8d185e82ed7f6f4e454c7fe8c4c81ca2` |
| `tests/test_sessions.py` | +3 U8 tests, +1 one-based L4 test, 1 U7 assertion updated for the note | 1,139 | `38e159e3a6dc382179098d82804af114006ab20a4e283dcce3dab8241b584489` |
| `scripts/sessions_calibration_p1_b9999.py` | New diagnostic script | 139 | `f5d29f8153a770268d815ae78761c0a4bc0b2aba0598bdd4ae960019a3e32766` |
| `docs/SESSIONS_CALIBRATION_P1_B9999.json` | New diagnostic output | — | `3fba6b9d3a44b7a72262befa417874c37b263c1122cd0efb2195442ce6514451` |
| `docs/SESSIONS_ADDENDUM_U7_L4.md` | Revision 2: U8 wording, U9 conflict with exact protocol text, L4 one-based table | — | `52c37a905f7d6018b8eedec3dc0029605421b14773509156e5dd8dec537b3619` |
| `docs/SESSIONS_RESEARCH_AUDIT_v4.md` | New (this file) | — | — |

**Unchanged:**

| File | SHA-256 |
|---|---|
| Protocol v4.1 | `716e0003…` |
| `SESSIONS_CALIBRATION.json` | `e32b7992…` |
| `scripts/sessions_calibration.py` | `ef815568…` |
| `tests/sessions_synth.py` | `5536e067…` |

Audit v3, report v2 and `PREREG_HASH.txt` are also unchanged.

## 9. Confirmation

- No real market price was loaded.
- No actual study result was calculated.
- Nothing was committed or pushed.
- No broker, live-trading, order or strategy code was touched.
- No new hypothesis or project was started.

**Stopped for review.**
