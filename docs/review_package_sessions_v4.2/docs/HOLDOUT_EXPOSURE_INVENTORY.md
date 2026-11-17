# Holdout exposure inventory: every holdout session and every earlier computation that touched it

Written 2026-11-11 (~23:55 CT). This is the exposure inventory Ethan asked for in decision D2. Machine-readable
version: `docs/HOLDOUT_EXPOSURE_SESSIONS.csv`, one row per holdout session (346), with columns session,
weekday, excluded_by (E1–E5), category, tests.

**Built from timestamps and earlier code only.** No price, return or statistic was computed to produce it.

## 1. Method

The exposure footprint was rebuilt by re-running the **day-selection and window logic** of every earlier
experiment against the bar **timestamps**:
- `nq_bot/family3.py`: trading day = weekday with at least 300 RTH bars; the H8 window, and the
  random-long pool;
- `run_h8_placebo.py`: sham offsets, the ±3-trading-day ban, and the Wednesday pool;
- `run_h8_es_replication.py`, `run_h8_m2k_replication.py`, `run_h8_gold_control.py`: each market's own
  random-long pool;
- `run_family3_holdout.py` and `run_h8_contract_level.py`: the real events.

**The reconstruction matches the saved outputs exactly.** MNQ Wednesday pool: 318 windows (`h8_placebo.json`:
`wednesday_pool_n` 318). MNQ sham windows: 341 (59 + 59 + 59 + 56 + 54 + 54, matching the per-offset n).
Real events: 59 on MNQ, MES and M2K, 55 on gold (`h8_gold_control.json`: n 55).

**Unit of exposure.** Every earlier window ran from 14:00 ET on session *p* to 13:55 ET on the next session
*e*. It overlaps this study's observation units for **two** sessions: *p* (its last two RTH hours) and *e*
(its entire overnight plus RTH to 13:55). A session counts as exposed if either of its components overlaps any
window in any market.

## 2. Categories

Each session gets the highest applicable category, in the order A > P > B > U.

| Category | Definition | What was computed and reported | All holdout sessions | Eligible after E1–E5 |
|---|---|---|---|---|
| **A: H8-specific** | Inside a real H8 event window, in any market | Per-event trades: MNQ (`family3_holdout`, then contract-level), MES, M2K, gold, and NKD (computed, not reported). **Holdout-specific statistics were reported:** MNQ n 11, net +$368, t 0.34, contract-level t −0.27. M2K and gold report `by_year` sums for 2025 and 2026. | **22** | **21** |
| **P: placebo** | Inside an H8-placebo sham window or Wednesday-pool window (MNQ, MES or M2K) | Per-window P&L computed in memory. **Only pooled statistics were saved or reported**, mixing 2019–2026: per-offset n, net, mean, t; Wednesday pool n and mean; bootstrap p. **All 116 involve MNQ itself** (sham: 116; Wednesday pool: 114). | **116** | **111** |
| **B: replication benchmark only** | Inside a random-long 24-hour window of the MES, M2K or gold replication pool, and nothing above | Per-window P&L computed in memory for **every consecutive trading-day pair in 2019–2026** in those markets. Only the pool mean and the 95th percentile of 2,000 bootstrap means were reported. **No MNQ price inside these sessions was used in any computation.** | **203** | **186** |
| **U: unexposed** | None of the above | — | **5** | **0** |

**All five unexposed sessions are scheduled half-days (E1), which no earlier pool used:** 2025-07-04,
2025-11-27, 2025-12-24, 2026-06-19 and 2026-07-03. **No eligible holdout session is unexposed.**

### Additional flag: the contract-window download

`data/mnq_contracts.csv` holds actual MNQ contract prices from **Monday through Wednesday** of each holdout
FOMC week, plus the first 1–2 hours of Thursday's Globex session (verified from its timestamps).
`run_h8_contract_level.py` computed only the H8 window and its stop scan on these bars. The rest were
**loaded but used in no computation**.

They are flagged in the lists below:
- **†** = the full session sits in the contract file (11 Mondays);
- **‡** = the start of the overnight sits in the file (11 Thursdays).

All 22 are Category B sessions.

## 3. How each kind of exposure affects independence

This section reasons about what each kind of exposure can reveal. The percentage of sessions exposed plays
no part in the argument.

- **A.** Reported per-event and holdout-specific outcomes are a direct view of ON(e) and part of RTH(e)
  on those days. They also show these were selected event days. **These sessions are not independent of
  prior results.**
- **P.** Every P window was evaluated individually in memory. Only pooled figures reached a person, so
  nothing was seen about any single holdout session. Still, the sessions entered statistics that shaped
  earlier conclusions (the H8 placebo verdict). The same MNQ prices were processed, so **they cannot be
  called untouched.**
- **B.** No MNQ price in these sessions entered any computation. But the same calendar spans were processed
  in MES (~0.95 correlated with MNQ), M2K and gold, and reported as pooled means. **They are therefore
  exposed, through correlated markets, and are not clean or untouched.**
  - Ethan's decision D2-a (2026-11-11 23:34): under the strict definition the holdout has **no** unexposed
    sessions, so the official confirmatory verdict is INCONCLUSIVE.
  - The "B only" Mondays, Thursdays and Fridays (185) are used only as a **labelled secondary analysis of a
    restricted population selected by exposure**.
  - The 22 contract-file sessions (†, ‡) add a further disclosure: MNQ contract prices loaded, never used.
- **General.** Anyone who lived through 2025–26 knows the broad market direction. That applies to every
  session and cannot be removed.

## 2a. Session counts and version consistency

The inventory covers the **346 holdout sessions with RTH trading**:
- 347 session dates had any trading; **2026-04-03** (Good Friday) had Globex only and no RTH, so it has no
  observation to classify;
- 334 of the 346 are full 390-minute sessions; the other 12 are scheduled early closes;
- 318 are eligible after rules E2–E5.

**The CSV (SHA-256 `a462425b…b88683`) has been unchanged since it was written.** Every category or cell
figure in either version of this inventory is derived from that one file. No session has been added,
removed or reclassified between versions; only the wording changed. Details: protocol v4 §5.2a.

**Use restriction (D2-a, 2026-11-11):** nothing in this inventory makes any holdout subset a clean or
independent confirmation sample. The official verdict is INCONCLUSIVE. The "B only" Mon/Thu/Fri subset
serves only a secondary, descriptive analysis of a restricted population.

## 3a. Mutually exclusive overlap breakdown

See protocol v4 Appendix E. Summary of the 318 eligible sessions:
- A only: 10
- A and B: 11
- P and B: 111
- B only: 186
- P only, A and P, A, P and B, U: 0

Reconciled to 346 and 334 in that appendix.

## 4. Exact dates

[E#] = excluded from the sample by that rule anyway. † / ‡ = contract-file flag (§2).

### A_H8: 22 sessions (21 eligible after E1–E5)

- **Tue (11):** 2025-07-29, 2025-09-16, 2025-10-28, 2025-12-09, 2026-01-27, 2026-03-17, 2026-04-28, 2026-06-16, 2026-07-28, 2026-09-15, 2026-10-27
- **Wed (11):** 2025-07-30, 2025-09-17, 2025-10-29, 2025-12-10, 2026-01-28, 2026-03-18, 2026-04-29, 2026-06-17 [E4], 2026-07-29, 2026-09-16, 2026-10-28

### P_placebo: 116 sessions (111 eligible after E1–E5)

- **Tue (58):** 2025-07-01, 2025-07-08, 2025-07-15, 2025-07-22, 2025-08-05, 2025-08-12, 2025-08-19, 2025-08-26, 2025-09-02 [E2], 2025-09-09, 2025-09-23, 2025-09-30, 2025-10-07, 2025-10-14, 2025-10-21, 2025-11-04, 2025-11-11, 2025-11-18, 2025-11-25, 2025-12-02, 2025-12-16, 2025-12-30, 2026-01-06, 2026-01-13, 2026-01-20 [E2], 2026-02-03, 2026-02-10, 2026-02-17 [E2], 2026-02-24, 2026-03-03, 2026-03-10, 2026-03-24, 2026-03-31, 2026-04-07, 2026-04-14, 2026-04-21, 2026-05-05, 2026-05-12, 2026-05-19, 2026-05-26 [E2], 2026-06-02, 2026-06-09, 2026-06-23, 2026-06-30, 2026-07-07, 2026-07-14, 2026-07-21, 2026-08-04, 2026-08-11, 2026-08-18, 2026-08-25, 2026-09-01, 2026-09-08 [E2], 2026-09-22, 2026-09-29, 2026-10-06, 2026-10-13, 2026-10-20
- **Wed (58):** 2025-07-02, 2025-07-09, 2025-07-16, 2025-07-23, 2025-08-06, 2025-08-13, 2025-08-20, 2025-08-27, 2025-09-03, 2025-09-10, 2025-09-24, 2025-10-01, 2025-10-08, 2025-10-15, 2025-10-22, 2025-11-05, 2025-11-12, 2025-11-19, 2025-11-26, 2025-12-03, 2025-12-17, 2025-12-31, 2026-01-07, 2026-01-14, 2026-01-21, 2026-02-04, 2026-02-11, 2026-02-18, 2026-02-25, 2026-03-04, 2026-03-11, 2026-03-25, 2026-04-01, 2026-04-08, 2026-04-15, 2026-04-22, 2026-05-06, 2026-05-13, 2026-05-20, 2026-05-27, 2026-06-03, 2026-06-10, 2026-06-24, 2026-07-01, 2026-07-08, 2026-07-15, 2026-07-22, 2026-08-05, 2026-08-12, 2026-08-19, 2026-08-26, 2026-09-02, 2026-09-09, 2026-09-23, 2026-09-30, 2026-10-07, 2026-10-14, 2026-10-21

### B_replication_pool: 203 sessions (186 eligible after E1–E5)

- **Mon (69):** 2025-07-07 [E2], 2025-07-14, 2025-07-21, 2025-07-28 †, 2025-08-04, 2025-08-11, 2025-08-18, 2025-08-25, 2025-09-01 [E1], 2025-09-08, 2025-09-15 †, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27 †, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01 [E2], 2025-12-08 †, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19 [E1], 2026-01-26 †, 2026-02-02, 2026-02-09, 2026-02-16 [E1], 2026-02-23, 2026-03-02, 2026-03-09, 2026-03-16 †, 2026-03-23, 2026-03-30, 2026-04-06 [E5], 2026-04-13, 2026-04-20, 2026-04-27 †, 2026-05-04, 2026-05-11, 2026-05-18, 2026-05-25 [E1], 2026-06-01, 2026-06-08, 2026-06-15 †, 2026-06-22 [E2], 2026-06-29, 2026-07-06 [E2], 2026-07-13, 2026-07-20, 2026-07-27 †, 2026-08-03, 2026-08-10, 2026-08-17, 2026-08-24, 2026-08-31, 2026-09-07 [E1], 2026-09-14 †, 2026-09-21, 2026-09-28, 2026-10-05, 2026-10-12, 2026-10-19, 2026-10-26 †
- **Tue (1):** 2025-12-23
- **Thu (67):** 2025-07-03 [E1], 2025-07-10, 2025-07-17, 2025-07-24, 2025-07-31 ‡, 2025-08-07, 2025-08-14, 2025-08-21, 2025-08-28, 2025-09-04, 2025-09-11, 2025-09-18 [E4] ‡, 2025-09-25, 2025-10-02, 2025-10-09, 2025-10-16, 2025-10-23, 2025-10-30 ‡, 2025-11-06, 2025-11-13, 2025-11-20, 2025-12-04, 2025-12-11 ‡, 2025-12-18 [E4], 2026-01-08, 2026-01-15, 2026-01-22, 2026-01-29 ‡, 2026-02-05, 2026-02-12, 2026-02-19, 2026-02-26, 2026-03-05, 2026-03-12, 2026-03-19 [E4] ‡, 2026-03-26, 2026-04-02, 2026-04-09, 2026-04-16, 2026-04-23, 2026-04-30 ‡, 2026-05-07, 2026-05-14, 2026-05-21, 2026-05-28, 2026-06-04, 2026-06-11, 2026-06-18 ‡, 2026-06-25, 2026-07-02, 2026-07-09, 2026-07-16, 2026-07-23, 2026-07-30 ‡, 2026-08-06, 2026-08-13, 2026-08-20, 2026-08-27, 2026-09-03, 2026-09-10, 2026-09-17 [E4] ‡, 2026-09-24, 2026-10-01, 2026-10-08, 2026-10-15, 2026-10-22, 2026-10-29 ‡
- **Fri (66):** 2025-07-11, 2025-07-18, 2025-07-25, 2025-08-01, 2025-08-08, 2025-08-15, 2025-08-22, 2025-08-29, 2025-09-05, 2025-09-12, 2025-09-19, 2025-09-26, 2025-10-03, 2025-10-10, 2025-10-17, 2025-10-24, 2025-10-31, 2025-11-07, 2025-11-14, 2025-11-21, 2025-11-28 [E1], 2025-12-05, 2025-12-12, 2025-12-19, 2025-12-26 [E2], 2026-01-02, 2026-01-09, 2026-01-16, 2026-01-23, 2026-01-30, 2026-02-06, 2026-02-13, 2026-02-20, 2026-02-27, 2026-03-06, 2026-03-13, 2026-03-20, 2026-03-27, 2026-04-10, 2026-04-17, 2026-04-24, 2026-05-01, 2026-05-08, 2026-05-15, 2026-05-22, 2026-05-29, 2026-06-05, 2026-06-12, 2026-06-26, 2026-07-10, 2026-07-17, 2026-07-24, 2026-07-31, 2026-08-07, 2026-08-14, 2026-08-21, 2026-08-28, 2026-09-04, 2026-09-11, 2026-09-18, 2026-09-25, 2026-10-02, 2026-10-09, 2026-10-16, 2026-10-23, 2026-10-30

### U_unexposed: 5 sessions (0 eligible after E1–E5)

- **Wed (1):** 2025-12-24 [E1]
- **Thu (1):** 2025-11-27 [E1]
- **Fri (3):** 2025-07-04 [E1], 2026-06-19 [E1], 2026-07-03 [E1]

## 5. Scripts (load timestamps only)

`scripts/sessions_preflight/exposure_inventory.py` (`895f4068…ae37017`) reads the timestamps of MNQ,
MES, M2K and MGC. `classify_holdout_exposure.py` (`251eb57e…062161`) writes the CSV
(`a462425b…b88683`).

In building this inventory I opened earlier phases' **already-published** result files (`h8_placebo.json`,
the replication JSONs) to check the reconstruction counts. Those files contain earlier H8 statistics,
including the M2K and gold `by_year` sums for 2025 and 2026. Nothing new was calculated, and none of it is a
quantity in this study.
