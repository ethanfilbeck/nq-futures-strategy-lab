# Independent reviewer outreach

Prepared 2026-11-12. **No independent review has taken place yet.** This document is for finding and
approaching a reviewer.

---

## Part 1. Who should review this project

The project spans four areas of expertise. **One person is unlikely to cover all four well.** A primary
statistical reviewer, plus one or two secondary reviewers or a reviewer with the right collaborators, is
realistic.

| Area | Essential qualifications | Optional / helpful |
|---|---|---|
| **1. Statistical methodology and multiple testing** (highest priority) | Graduate-level training or published work in statistics, econometrics or quantitative finance. Hands-on experience with **bootstrap inference for dependent data** (block or stationary bootstrap), **size and coverage calibration by Monte Carlo**, and **family-wise error control** (Holm, Bonferroni). Able to judge whether a centered, non-studentized bootstrap test of a ratio statistic is valid. | Extreme-value methods (Hill estimator, tail-index comparison); volatility models (GARCH); realized-variance methods |
| **2. Financial research design and preregistration** | Experience designing or refereeing empirical finance studies. Understands holdout contamination, data snooping and multiple-hypothesis risk in market data. Familiar with preregistration or registered-report practice. | Market microstructure (overnight vs regular-session trading, price discovery, Barclay & Hendershott-type measures); publication record in empirical finance |
| **3. Historical futures data integrity** | Working knowledge of **CME equity-index futures**: Globex vs regular session hours, contract months and **roll mechanics**, continuous-contract construction, daylight-saving transitions, early closes and holidays, price limits and circuit breakers | Experience with Databento (or similar) 1-minute data and symbology; exchange-calendar handling in code |
| **4. Python software quality and reproducibility** | Professional or research-software experience with **Python, pandas, NumPy and pytest**. Able to judge test adequacy, error handling, reproducibility (git, checksums, line endings) and lint and type-check tooling. | Research-software engineering; continuous integration; Windows/Linux portability |

**Independence requirements (essential):**
- No role in designing or writing this project.
- No financial interest in any outcome.
- Willingness to report negative findings.
- Agreement not to redistribute the materials, which include the repository's full history.

**What the reviewer does not need:**
- trading or brokerage experience;
- access to market data (none is supplied);
- any interest in profitability, because the project makes no profitability claim.

**Where such reviewers may be found (suggestions only; nobody has been contacted):**
- statistics, economics or finance faculty;
- graduate students in those fields, supervised by faculty;
- university research-software or data-science consulting services;
- independent statistical consultants.

At Murray State, an academic advisor or department may be able to suggest names.

---

## Part 2. Outreach message (template; edit before sending)

**Subject:** Request for an independent methodological and software review: student research project on
overnight vs regular-session futures behaviour

Dear [Name],

I am Ethan Filbeck, a Computer Science student at Murray State University. I am looking for an independent
reviewer for an **academic research and software-engineering project**, and I am contacting you because of
your expertise in [statistics / empirical finance / futures data / research software].

**The project.** It is a **historical, descriptive study** of how Micro E-mini Nasdaq-100 futures (MNQ) behave
overnight compared with the regular trading session (09:30–16:00 ET), using 1-minute data from 2020 to 2026.
It compares four things:
1. volatility per hour;
2. tail heaviness;
3. the overnight share of price discovery;
4. how often the overnight move dominates on extreme days.

**This is not a request to validate a trading system.** The project produces no trading signals and makes no
profitability claim. An automated guard rejects any result that names a trading quantity (profit, signal,
position, Sharpe ratio and similar).

**Current status:**
- **The official verdict is fixed in advance as INCONCLUSIVE.** No holdout data is free of exposure to earlier
  experiments, so the study cannot confirm or reject anything in this phase.
- **The protocol, draft v4.2, is unsigned.** It has not been approved.
- **No real study results have been calculated** under v4.2 or any earlier version. All analysis code has been
  run on synthetic data only.
- **136 synthetic tests pass** on Windows and Linux. I understand that passing tests does not show the
  statistics are valid, which is why I am asking for an independent review.

**Known limitations I would like you to assess, not just accept:**
- **Statistical:**
  - In synthetic calibration, one test (P1, price discovery) rejects true nulls at about 1.3–1.5% instead of
    1%, and more bootstrap resamples do not fix this.
  - A second measure (V1, variance ratio) was demoted to descriptive-only after its test was badly oversized
    (about 19%) under one volatility pattern.
  - Because of these, a 1% family-wise error rate is not verified.
  - The protocol's wording about the Holm correction does not exactly match the code: the decisions agree, but
    the adjusted p-values can differ.
- **Data integrity:**
  - Contract identity is established only through an exact roll calendar; a separate contract-identity check
    in the code is not called by the study runner.
  - One pinned file hash depends on Windows line endings.
  - The licensed market data cannot be shared, so data-level checks can be inspected but not re-run.
- **Software:**
  - The project's lint and type-check gate fails on helper scripts.
  - Newer pandas versions emit 13,745 deprecation warnings that will become errors in a future pandas release.
- **Literature:** two key papers could not be obtained in full text.

**What I would ask you to deliver:**
1. A completed findings form (`INDEPENDENT_REVIEW_FINDINGS_TEMPLATE.md`). Each finding classified as
   *Acceptable*, *Acceptable with limitations*, *Requires correction*, or *Cannot be determined from supplied
   evidence*, with supporting evidence (file and line, calculation, or reproducible synthetic test).
2. A short overall statement:
   - (a) whether the methodology is fit for its descriptive purpose;
   - (b) what must be corrected before any real-data run;
   - (c) what you could not assess.
3. Optionally, a list of additional evidence you would need for a complete assessment.

**Materials.** A reviewer guide, the protocol, the exact tested code snapshot (git bundle plus checksummed
archive), test transcripts and calibration results. The full scope is in the attached cover note and
`INDEPENDENT_REVIEWER_GUIDE.md`. Real-data access is not required, and no data will be supplied.

**Questions for you:**
- Would you be willing to review all or part of this, e.g. only the statistical sections?
- What time would you estimate, and what fee, if any?
- What timeline would suit you, and would you want any confidentiality terms?

I'm happy to send a short summary first, if that helps you decide.

Thank you for considering this.

Sincerely,
Ethan Filbeck
Murray State University
[preferred contact details]

---

## Part 3. Notes for Ethan before sending

- **Fill in** the reviewer's name, their area, and your contact details. Do not attach the package to a first
  contact; send it only after the reviewer agrees (see the secure-sending steps in the final report).
- **Partial reviews.** If a reviewer covers only some areas, record which sections of
  `INDEPENDENT_REVIEWER_GUIDE.md` they reviewed. That way the uncovered areas stay visibly open.
- **Do not describe** the project as approved, validated or profitable, or as ready for live trading. None of
  these is true.
