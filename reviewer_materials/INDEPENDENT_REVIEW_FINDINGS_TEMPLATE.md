# Independent review: findings template

**Project:** overnight vs regular-session MNQ study. Protocol DRAFT v4.2 (unsigned). Snapshot: commit
`a48eaac` plus the 55-file overlay.

Fill this in as the reviewer. Copy a finding block as often as needed. Passing tests are not evidence of
statistical validity; please base conclusions on inspection, calculation or reproducible synthetic checks.

## Reviewer details

| Field | Entry |
|---|---|
| Reviewer name and affiliation | |
| Area(s) of expertise | |
| Sections reviewed (guide §3 A, §4 B, §5 C, §6 D, or parts of them) | |
| Sections **not** reviewed | |
| Review dates | |
| Snapshot verified? (bundle `git bundle verify` OK; HEAD `a48eaac8…`; 55/55 overlay checksums match `WORKING_TREE_INVENTORY.txt`; manifest SHA-256 `72fd7d2e…`) | Yes / No / Partly. Details: |
| Synthetic commands run, with environment (OS, Python, numpy, pandas, pytest) | |
| Conflicts of interest | |

## Scales

**Classification:** one of
- **Acceptable**
- **Acceptable with limitations**
- **Requires correction**
- **Cannot be determined from supplied evidence**

**Severity:**

| Severity | Meaning |
|---|---|
| Critical | Would invalidate the study's conclusions or its integrity guarantees |
| High | Must be fixed before any real-data run |
| Medium | Should be fixed, or disclosed prominently |
| Low | Minor; wording or style |
| Info | Observation only |

**Affects:** tick any that apply.
- [ ] research validity
- [ ] reproducibility
- [ ] software reliability

## Finding block (copy for each finding)

```
Finding ID:            R-__
Area:                  A / B / C / D   (guide section and question number, e.g. A2)
Location:              file / function / line / protocol section / test name
Evidence examined:     what you read, ran or calculated (commands and outputs, or attach them)
Explanation:           what is wrong, or why it is acceptable
Severity:              Critical / High / Medium / Low / Info
Classification:        Acceptable / Acceptable with limitations / Requires correction /
                       Cannot be determined from supplied evidence
Affects:               [ ] research validity  [ ] reproducibility  [ ] software reliability
Recommended correction
or additional evidence:
```

---

## Required sections

### S1. Contract identity and roll handling (unresolved)

**Context:**
- Roll sessions are excluded by rule E4, using exact switch dates from `runs/rollmap_MNQ.json` (Databento
  symbology `MNQ.v.0`, 31 contract periods).
- `nq_bot/integrity.py` has `Gate.contract_identity`, but `run_sessions_study.py` **does not call it**.
- The study series is a spliced, unadjusted front-month series.

**Questions:**
- Is the roll calendar sufficient evidence of contract identity?
- Should the runner call `Gate.contract_identity`, or check the roll map against the data's symbol information,
  before any real-data run?
- Can a roll be missed or misdated without detection?

| Finding ID | Location | Evidence examined | Explanation | Severity | Classification | Affects | Recommendation |
|---|---|---|---|---|---|---|---|
| R-S1-1 | | | | | | | |

### S2. P1 calibration (statistical validity)

**Context:**
- Synthetic false-positive rates: 1.33% (iid) and 1.50% (common GARCH) at nominal 1%; 0.33–0.34% at 0.2%.
- 99% interval coverage: 98.3–98.6%.
- Going from 999 to 9,999 resamples changed neither rate.
- Not measured at Holm's thresholds 0.0025, 0.0033 and 0.005.
- Files: `docs/SESSIONS_CALIBRATION.json`, `docs/SESSIONS_CALIBRATION_P1_B9999.json`; `wpc_on`, `vs_on`,
  `_boot_p1`, `centered_p`; protocol §6.1 and §7.2.

**Questions:**
- What causes the excess: the statistic, the centered non-studentized test, or the block bootstrap?
- Is the method valid?
- Should P1 remain inferential, or become descriptive only?
- What evidence would be required before P1 could be confirmatory?

| Finding ID | Location | Evidence examined | Explanation | Severity | Classification | Affects | Recommendation |
|---|---|---|---|---|---|---|---|
| R-S2-1 | | | | | | | |

### S3. V1 limitations

**Context:**
- V1 is descriptive only (decision U7): its estimate and descriptive interval are reported, and it is never
  tested.
- It has no pipeline halt (U9, v4.2) and a fixed verdict label.
- Scenario 2 gave 19.4% false positives at 1% and 80.1% coverage.
- Code: `run_family` V1 branch, `assert_v1_descriptive_only`, `official_verdict`, `o2_secondary`, runner
  `sensitivities`.

**Questions:**
- Is the restriction enforced in every code path?
- Can V1 influence any other result or the verdict?
- Should its descriptive interval be reported at all?

| Finding ID | Location | Evidence examined | Explanation | Severity | Classification | Affects | Recommendation |
|---|---|---|---|---|---|---|---|
| R-S3-1 | | | | | | | |

### S4. Holm adjustment (five slots, V1 placeholder 1.0)

**Context:** `holm`, `holm_with_placeholder`; protocol v4.2 §7 and §7.1. Comparison script
`scripts/review/holm_v41_v42_comparison.py` gives:
- rejection decisions identical to v4.1 in all 188,433 cases with V1 not significant;
- adjusted p-values differ in 69,935 (37.1%) of those cases.

**Questions:**
- Is the implementation correct?
- Does v4.2's sentence "face the same thresholds as in v4.1 whenever V1 was not significant" accurately describe
  it?
- Is the family-wise error statement in §7.2 justified?

| Finding ID | Location | Evidence examined | Explanation | Severity | Classification | Affects | Recommendation |
|---|---|---|---|---|---|---|---|
| R-S4-1 | | | | | | | |

### S5. Data and hash portability

**Context:**
- On a Windows checkout with `core.autocrlf=true`, 59 tracked files have CRLF line endings.
- The pinned `runs/rollmap_MNQ.json` hash (`e1beaeed…`) matches CRLF bytes only; an LF checkout gives
  `eaded078…`.
- The git bundle is not byte-reproducible on rebuild (same objects); the overlay archive is.
- `scripts/check.py` fails on the full snapshot: 65 ruff findings and 20 mypy errors, in
  `scripts/sessions_preflight/` and the package's test-file copy.
- pandas 3.1.1 emits 13,745 deprecation warnings (`dayofweek`).

**Questions:**
- Are the pinned hashes portable?
- Can the snapshot be reconstructed and verified from the supplied artifacts?
- How serious are the warnings and the failing quality gate?

| Finding ID | Location | Evidence examined | Explanation | Severity | Classification | Affects | Recommendation |
|---|---|---|---|---|---|---|---|
| R-S5-1 | | | | | | | |

### S6. Missing evidence

| Missing item | Needed for | Could you complete that part without it? | What you would need |
|---|---|---|---|
| Licensed market-data files (not supplied) | Re-running count verification and real-data integrity checks; checking the roll map against the data | | |
| Full texts of Liu & Tse (2017) and Riedel & Wagner (2015) | T1 expected direction; P1 literature context | | |
| Per-replicate calibration data (only aggregates supplied; regenerable from seeds) | Independent re-analysis of calibration | | |
| P1 calibration at 0.0025, 0.0033, 0.005 | Family-wise error assessment | | |
| Monte Carlo scenarios with censoring, missing bars, roll jumps or volume variation | Calibration realism | | |
| Any end-to-end real-data run (deliberately not done; protocol unsigned) | Runner behaviour on real files | | |
| Other (please list) | | | |

### S7. Other areas (guide §3–§6)

| Finding ID | Area / question | Location | Evidence examined | Explanation | Severity | Classification | Affects | Recommendation |
|---|---|---|---|---|---|---|---|---|
| R-__ | A1 bootstrap and dependence | | | | | | | |
| R-__ | A7 minimum sizes | | | | | | | |
| R-__ | B1 v4.1 / v4.2 consistency | | | | | | | |
| R-__ | B2 INCONCLUSIVE enforcement | | | | | | | |
| R-__ | B3 O2 isolation | | | | | | | |
| R-__ | B4 exposure disclosure | | | | | | | |
| R-__ | B5 outcome-driven change prevention | | | | | | | |
| R-__ | C2 sessions and DST | | | | | | | |
| R-__ | C3 missing, duplicate, conflicting data | | | | | | | |
| R-__ | C4 timestamp-only count verification | | | | | | | |
| R-__ | D1 test suite adequacy | | | | | | | |
| R-__ | D4 safeguards enforced in code | | | | | | | |

## Overall statement

| Question | Reviewer's answer |
|---|---|
| (a) Is the methodology fit for its stated descriptive purpose? | |
| (b) What must be corrected before any real-data run? (list finding IDs) | |
| (c) What could not be assessed, and why? | |
| (d) Any concern about research integrity, such as outcome-driven changes or undisclosed exposure? | |

**Reviewer declaration.** I reviewed the materials listed above independently. My findings are based on the
evidence cited. I make no statement about the profitability or trading suitability of anything in this project.

Signature: ____________________  Date: ____________
