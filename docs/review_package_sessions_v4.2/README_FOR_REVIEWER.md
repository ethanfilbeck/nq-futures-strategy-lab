# Independent-review package: overnight vs regular-session study (protocol DRAFT v4.2)

Prepared 2026-11-12 for an independent reviewer.

**Scope.** This is a descriptive, historical, academic study of MNQ (Micro E-mini Nasdaq-100) futures:
overnight vs regular-session (RTH) volatility, tails, price-discovery share and extreme-day dominance. It is
not a trading strategy.

**Status:**
- No real price has been loaded and no study result exists.
- Everything here was produced and tested on synthetic data.
- Protocol v4.2 is unsigned. Nothing is hashed into the project's `PREREG_HASH.txt`, and nothing is committed.

## Suggested reading order

1. `docs/SESSIONS_FINAL_AUDIT_v5.md`: what changed last, the verification results, and **§9, the list of
   unresolved limitations and the questions for you**.
2. `protocol/DRAFT_PREREG_SESSIONS_v4.2_awaiting_signoff.md`: the protocol under review. Appendix D part 5
   is the change log, and §7.2 holds the binding calibration disclosures.
3. `protocol/protocol_v4.1_to_v4.2.diff`: every change from v4.1. `protocol/…v4.1…` is the preserved prior
   version (SHA-256 `716e0003…`).
4. `docs/SESSIONS_ADDENDUM_U7_L4.md`: implementation notes for decisions U7, U8, U9 and L4.
5. `calibration/`: Monte Carlo results.
   - `SESSIONS_CALIBRATION.json`: 12 scenarios, B = 999.
   - `SESSIONS_CALIBRATION_P1_B9999.json`: P1 paired diagnostic, B = 999 vs 9,999.
6. `code/`: the analysis module, runner, synthetic tests and calibration scripts.
7. Background:
   - `docs/LITERATURE_SESSIONS.md`;
   - `docs/DATA_FEASIBILITY_SESSIONS.md`;
   - `docs/HOLDOUT_EXPOSURE_INVENTORY.md` with `HOLDOUT_EXPOSURE_SESSIONS.csv`, which holds session dates and
     labels only, no prices;
   - audits v3 and v4, and synthetic report v2 (history).

## Key decisions you are asked to scrutinise

| Decision | Summary |
|---|---|
| D2-a | The official confirmatory verdict is fixed at **INCONCLUSIVE**, because no holdout session is unexposed. O2 is secondary and descriptive and cannot change it. |
| U7 / U8 / U9 | V1 (per-hour variance ratio) is **descriptive only**. Holm keeps five slots, with V1's slot fixed at the placeholder 1.0. V1 no longer gates the pipeline. |
| P1 | Mildly liberal in synthetic calibration, and not fixed by more resamples. It is **not** to be treated as established confirmatory evidence until you have reviewed its validity. No verified 1% family-wise error rate is claimed. |
| L4 | The first volatility-group assignment is at session 81 (one-based), after 60 prior 20-session averages. |

## Re-running the checks (synthetic only)

This needs the full project repository; the package holds copies of the study's own files.

```
python -m pytest tests/test_sessions.py -W error::RuntimeWarning   # 136 tests, about 3.5 min
python scripts/check.py                                            # ruff, pytest, prereg, prepublish, pip-audit, mypy
```

The P1 diagnostic can be regenerated from its seeds with `python scripts/sessions_calibration_p1_b9999.py run …`
(16 chunks, about 6 h on 2 cores) and then `summarise`. The per-repetition chunk files are not included; the JSON
is the preserved output.

The sessions tests refuse to open anything under the project's `data/` folder.

## Integrity

`MANIFEST.sha256` lists the SHA-256 of every file in this package. Verify it with `sha256sum -c MANIFEST.sha256`.
