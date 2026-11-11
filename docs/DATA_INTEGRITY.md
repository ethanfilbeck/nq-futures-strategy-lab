# Data integrity: a permanent gate, not a habit

Twice in two days a defect in the **data path**, not the method, changed this project's numbers:

| | What happened | How it was caught |
|---|---|---|
| `AUDIT_2026_11_ROLLS.md` | Unadjusted continuous series inflated every hold crossing a contract roll, moving H8 from a pass to a fail | A hand check of overnight price jumps |
| `PBO_INDEPENDENT_AUDIT.md` | The PBO return matrix silently discarded $322.70 settled on exchange half-days | Reconciling column sums against the original trade files by hand |

**Neither was caught by a test, and neither produced anything that looked wrong.** PBO of 14.8% is an
unremarkable number. A roll-inflated t of 3.02 looks like a pass. Both were found only because someone
reconciled a derived dataset against its source by hand — which is exactly the kind of check that gets
skipped on a tired evening.

So it is no longer a thing anyone has to remember.

## The gate

`nq_bot/integrity.py`. An experiment builds a `Gate`, records checks as it loads and transforms data, and
calls `enforce()` **before computing anything**. A failure raises `DataIntegrityError`, which no experiment
catches. The record is written to `runs/<experiment>_integrity.json` whether it passes or fails.

| Check | What it guarantees |
|---|---|
| `bars()` | tz-aware index, strictly increasing, no duplicates, OHLCV present, no NaN, high/low consistent with open/close |
| `contract_identity()` | States whether roll dates are **exact** (from a `symbol` column) or **heuristic**, so every downstream figure inherits a stated provenance |
| `reconcile_total()` | A derived P&L total equals its source's **to the cent**. This is the check that would have caught the $322.70 |
| `reconcile_count()` | Row counts match |
| `no_dates_lost()` | No trading date disappears during processing |
| `zero_is_not_missing()` | No NaN survives alignment, and genuine no-position days are counted explicitly — a zero is data, a NaN is absence, and the two are never conflated |
| `documented()` | Every transformation is recorded in the run's own log, so the run is reproducible from it |

## It is tested by being made to fail

`tests/test_integrity.py` mostly breaks things deliberately. A gate that only ever passes is decoration. It
asserts the gate raises on: a total that does not reconcile (including the exact four-column failure that
actually occurred), lost dates, NaN surviving alignment, malformed bars, and duplicate timestamps. It also
asserts the record is written **even when the gate fails**.

## New experiments must use it

`tests/test_tooling.py::test_new_experiments_must_use_the_data_integrity_gate` is a **ratchet**. Every
`run_*.py` must reference `nq_bot.integrity`, except those on an explicit `NOT_YET_GATED` allowlist. That
list may only shrink: adding a new ungated experiment fails the suite, and gating a listed one *also* fails
until it is removed from the list.

Currently gated: `run_pbo.py`. Everything else is pre-existing debt, listed in the allowlist and visible.
Retro-fitting the older experiments is worthwhile but was not done in the same change that introduced the
gate, so that the gate's own behaviour could be verified in isolation.

## What this does not do

The gate proves a derived dataset is **consistent with its source**. It cannot prove the source is right.
A roll-contaminated price series is internally consistent and passes every check above — which is precisely
why the roll audit needed separate work. **Data integrity and statistical integrity are different problems,
and this addresses only the first.**
