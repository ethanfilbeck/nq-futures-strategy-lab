# Cover note to the independent reviewer

Dear reviewer,

Thank you for agreeing to review this project. It is a student research and software-engineering project by
Ethan Filbeck (Murray State University). I am asking for an honest, independent assessment. Critical findings
are welcome.

## Purpose

The project is a **historical, descriptive study** of how US Nasdaq-100 micro futures (MNQ) behave overnight
compared with the regular trading session (09:30–16:00 ET). It uses 1-minute bars from 2020 to 2026. It
measures four things:
1. volatility per hour;
2. tail heaviness;
3. the overnight share of price discovery;
4. how often the overnight move dominates on extreme days.

**It is not a trading strategy.** The code produces no signals and no positions, and it makes no profitability
claim. Real-data analysis has **not** been run.

## Current status

- **Protocol:** draft v4.2. It is **unsigned and not approved.** v4.1 is preserved for comparison.
- **Verdict:** the official verdict is fixed in advance as **INCONCLUSIVE**, because no holdout data is free of
  exposure to earlier experiments.
- **Code:** the analysis code is complete and tested on synthetic data only. 136 synthetic tests pass on
  Windows, on Linux and in a cloud environment.
- **Snapshot:** the exact tested snapshot (git commit `a48eaac` plus 55 working-tree files) is delivered with
  checksums. See `REVIEW_DELIVERY_CHECKLIST.md`.

## Known limitations (please assess, not just accept)

- **P1 (price-discovery test)** rejects true nulls at about 1.3–1.5% instead of 1% in synthetic calibration.
  More bootstrap resamples do not fix this, and its intervals slightly under-cover. P1 is therefore not treated
  as confirmatory evidence.
- **The 1% family-wise error rate is not verified**, because Holm's guarantee requires valid p-values.
- **V1 (variance ratio)** is reported descriptively only, because its test was badly oversized under one
  synthetic volatility pattern.
- **The protocol wording** about the five-slot Holm correction is imprecise relative to the code (decisions
  match; adjusted p-values can differ).
- **Software:**
  - the project's lint and type-check gate fails on helper scripts;
  - newer pandas emits 13,745 deprecation warnings that will become errors in a future pandas;
  - one pinned file hash depends on Windows line endings.
- **Literature:** two key papers have not been read in full (no library full text).

## What I am asking you to review

Please follow `INDEPENDENT_REVIEWER_GUIDE.md`. It covers:
- **A. Statistical validity:** bootstrap, P1, V1, Holm, family-wise error, minimum sizes.
- **B. Research protocol:** consistency, the INCONCLUSIVE enforcement, O2 isolation, exposure disclosure.
- **C. Data integrity and reproducibility.**
- **D. Software quality.**

For each finding, please give one of these classifications, with evidence:
- Acceptable;
- Acceptable with limitations;
- Requires correction;
- Cannot be determined from supplied evidence.

The market-data files are licensed and are not included, so please limit any reproduction to the synthetic
tests and scripts.

Thank you,
Ethan Filbeck
