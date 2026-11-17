# Remaining limitations, v1: overnight vs regular-session study (protocol DRAFT v4.2, unsigned)

Written 2026-11-12. This is a register for the independent reviewer.

**Evidence labels:**
- **[CODE]** verified by code inspection;
- **[SYNTH]** verified by synthetic testing;
- **[PRIOR]** reported by previous work and not independently re-verified;
- **[OPEN]** unresolved.

**Passing synthetic tests does not establish statistical validity on real data.** No limitation below was
resolved by changing a frozen rule.

## A. Statistical validity (highest priority)

| ID | Limitation | Evidence | Status | What would resolve it |
|---|---|---|---|---|
| L-P1 | **P1 over-rejects its true null.** 1.33% (iid) and 1.50% (common volatility) at nominal 1%; 0.33–0.34% at 0.2%. Its 99% intervals cover 98.3–98.6%. Not fixed by 9,999 resamples. | [SYNTH] (both calibration files) | **[OPEN]** Cause unknown; P1's development label is not confirmatory evidence (v4.2 §7.2) | Reviewer's diagnosis (guide §5). A validated, pre-registered method in a new protocol version. Unexposed data (O3) for any confirmation. |
| L-P1-thr | P1's rejection rate at Holm's later thresholds (0.0025, 0.0033, 0.005) was **not measured** | [CODE] calibration recorded only 0.05, 0.01 and 0.002 | [OPEN] | Synthetic calibration at those levels (new work, needs approval) |
| L-FWER | **The family-wise error rate is not verified at 1%.** Holm's guarantee needs valid p-values, and P1's are not. Dependence between tests is unknown for real data. | [CODE] reasoning; [SYNTH] per-test rates | [OPEN] Disclosed; no verified number claimed | Resolve L-P1; no single synthetic process satisfies all four nulls at once |
| L-V1 | **V1's interval can be badly over-confident** (80.1% coverage, 19.4% false positives at 1% under independent volatility clustering). V1 is now descriptive only, but its descriptive interval is still reported. | [SYNTH] scenario 2 | [OPEN] Mitigated by U7 | Reviewer's view on whether to report V1's interval at all |
| L-T | T1 and T2 are conservative (about 0.3% at 1%; 2.92–3.21% at 5%), so they have lower power | [SYNTH] | Accepted, disclosed | — |
| L-L1 | L1 is near nominal (0.80–1.09% at 1%) | [SYNTH] | — | — |
| L-HILL | The Hill index assumes Pareto-type tails; on near-Gaussian tails it is a k-dependent heaviness index, not a structural parameter | [PRIOR] protocol §7.1 | Disclosed; sensitivity S8 varies k | — |
| L-STAB | Tail regime stability is "not assessable" for 2020, 2021 and 2022 (Hill k < 20) | [PRIOR] expected from frozen counts; [SYNTH] refusal logic | Accepted (U2) | — |

## B. Calibration design

| ID | Limitation | Evidence | Status |
|---|---|---|---|
| L-SCN | The scenarios are Gaussian, t(4), GARCH(1,1) independent or common, constant volume, and n = 1,230. There is **no** price-limit censoring, missing bars, roll jumps, intraday seasonality, volume variation or real cross-dependence inside the Monte Carlo; those are covered only by unit tests. | [CODE] `scripts/sessions_calibration.py` | [OPEN] Reviewer question C-a |
| L-REP | 20,000 repetitions give about ±0.14 points at 1% and about ±31% relative at 0.2%; adequate for gross faults only at the 0.2% level | [CODE] arithmetic | Disclosed |
| L-B | B = 999 versus the frozen 10,000 was measured only for P1 (no size effect; +0.2 points coverage) | [SYNTH] | [OPEN] for T1, T2, L1 (expected second order) |

## C. Data and counts

| ID | Limitation | Evidence | Status | What would resolve it |
|---|---|---|---|---|
| L-DEVCNT | **Development counts 1,308 → 1,230 have not been independently re-derived from the data files** in this review. The arithmetic and the runner gates match. | [PRIOR] (`reconcile_counts.py`, timestamps only); arithmetic [CODE] | [OPEN] | Reviewer, or an approved run, executes `scripts/sessions_preflight/reconcile_counts.py`. It loads timestamps only, with no prices. |
| L-HOCNT | Holdout counts 346 → 318 → 297 and O2 185 | [CODE] recounted from the hashed inventory CSV; E6 re-derived from the FOMC calendar | Verified at the inventory level. The inventory's own derivation from the timestamps is [PRIOR]. | — |
| L-LINEAGE | Earlier mislabels 333 → 334 and 347 → 346 | [PRIOR] protocol §5.2a | Documented; no membership change (CSV hash unchanged) | — |
| L-DATA | One vendor (Databento GLBX.MDP3), 1-minute bars, 18 degraded UTC dates (sensitivity S4). Price-limit censoring in 2020 (S2, S3). | [PRIOR] | Disclosed | — |
| L-VOL | P1 uses MNQ volume as the price-discovery proxy; MNQ may not be where Nasdaq-100 price discovery happens | [PRIOR] protocol §6.1 | Disclosed | — |
| L-L4 | The earliest volatility groups (from session 81, about late April 2020) rest on 60 overlapping averages covering January–April 2020, including March 2020. Groups feed no test. | [CODE][SYNTH] | Disclosed | — |

## D. Literature (D8)

| ID | Limitation | Evidence | Status | What would resolve it |
|---|---|---|---|---|
| L-D8 | **Liu & Tse (2017) and Riedel & Wagner (2015) have not been reviewed.** The library catalogue (checked 2026-11-12, not signed in) shows no full text; Interlibrary Loan needs Ethan's sign-in. | [PRIOR] library check, audit v3 §3 | **[OPEN]** | Obtain and read the full texts |
| L-D8-dir | **T1's expected direction (Δα_lo < 0) comes from Riedel & Wagner's abstract.** It affects the "established" versus "contradicted" label, not the p-value. `LITERATURE_SESSIONS.md` (written before the D8 check) summarises both papers from abstracts and citing papers. | [CODE] protocol §6.1; literature doc | [OPEN] | As above. Nothing may be added from the papers until they are read. |

## E. Documentation (see the package audit for detail)

| ID | Item | Status |
|---|---|---|
| PD-12 | T calibration at 5%: report v2 says "3.0–3.2%"; the JSON gives 2.92–3.21%. The JSON is the primary record; report v2 is not edited. | Explained; no further evidence needed |
| PD-4 | v4.2's wording "same thresholds as in v4.1" is imprecise: rejection decisions are identical (0 of 188,433 cases differ) but adjusted p-values differ in 37% | [CODE][SYNTH]; wording fix would need a v4.3 with approval |
| PD-3, PD-8 | Stale "v4" wording in the v4.2 text (§6.1 heading, §9, §13, §0 D4) and in code docstrings | Wording only |
| PD-6, PD-7 | Historical documents lack "superseded" banners; "U9 approved" refers to the decision, not the protocol | Cover note |
| PD-9 | The freeze procedure (copy to `docs/PREREG_SESSIONS.md`, hash, commit) is written only in the runner's refusal message | Needs writing into the sign-off steps |

## F. Software and process

| ID | Limitation | Evidence | Status |
|---|---|---|---|
| L-E2E | Real-data entry points (`main`, file loading on real files) are untested end to end, by design. The holdout's defensive refusal and the post-O2 verdict re-check are never executed. | [SYNTH] coverage 97% runner, 99% module | Disclosed |
| L-GUARD | The real-data test guard covers `open` and `io.open` (and so `pandas.read_csv`), not memory-mapped or C-level opens | [CODE] | Disclosed |
| L-SKIP | The artifact-hash test skips all remaining checks if one file is missing | [CODE] | Weakness; all files present |
| L-PC | The synthetic tests were run in the cloud on byte-identical files, **not on Ethan's PC** (no `pytest` in the PC command environment) | [CODE] identity by `cmp` | Ethan runs `py -m pytest tests/test_sessions.py` |
| L-WEBHOOK | Older webhook tests read `data/mnq_train.csv` if present (U6) | [PRIOR] | Run only the sessions tests locally |
| L-SIGN | **Protocol v4.2 is unsigned; nothing is in `PREREG_HASH.txt`.** The runner refuses any real-data run until it is. | [CODE] `require_frozen_protocol` | [OPEN], awaiting review and sign-off |
| L-NOCONF | Under D2-a nothing in this phase is confirmatory; the official verdict is INCONCLUSIVE whatever the results | [CODE][SYNTH] | By design |
