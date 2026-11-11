"""Data-integrity gate. Every experiment calls this BEFORE it computes anything, and a failure stops it.

Why this exists. Twice in two days a defect in the DATA PATH, not the method, changed this project's
numbers: contract-roll contamination inflated H8 (docs/AUDIT_2026_11_ROLLS.md), and the PBO return matrix
silently discarded $322.70 of P&L settled on exchange half-days (docs/PBO_INDEPENDENT_AUDIT.md). Neither was
caught by a test, because neither produced anything that looked wrong. Both were caught only by reconciling a
derived dataset against its source by hand.

So that reconciliation is no longer a thing anyone has to remember. A `Gate` collects checks and
`enforce()` raises `DataIntegrityError`, which no experiment catches.

The gate proves consistency between a source and what was derived from it. It cannot prove the source is
right: a roll-contaminated price series is internally consistent and would pass. Data integrity and
statistical integrity are separate problems and this module addresses only the first.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from . import rolls as rollmod

MONEY_TOL = 0.01          # dollars; totals must agree to the cent


class DataIntegrityError(RuntimeError):
    """Raised when a derived dataset does not reconcile with its source. Never caught by an experiment."""


@dataclass
class Gate:
    """Collects integrity checks for one experiment, then enforces them all at once."""

    experiment: str
    checks: list[dict] = field(default_factory=list)

    # ---------------------------------------------------------------- recording
    def _add(self, name: str, ok: bool, detail: str, **extra: Any) -> None:
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail, **extra})

    @property
    def failures(self) -> list[dict]:
        return [c for c in self.checks if not c["ok"]]

    # ---------------------------------------------------------------- the checks
    def bars(self, frame: pd.DataFrame, label: str) -> Gate:
        """Price data is well-formed: tz-aware, ordered, unique, OHLC-consistent, no NaN."""
        idx = frame.index
        tz_ok = isinstance(idx, pd.DatetimeIndex) and idx.tz is not None
        self._add(f"{label}: index is a timezone-aware DatetimeIndex", tz_ok, str(type(idx).__name__))
        self._add(f"{label}: timestamps strictly increasing", bool(idx.is_monotonic_increasing), "")
        dupes = int(idx.duplicated().sum())
        self._add(f"{label}: no duplicate timestamps", dupes == 0, f"{dupes} duplicates")
        need = ["open", "high", "low", "close", "volume"]
        missing = [c for c in need if c not in frame.columns]
        self._add(f"{label}: has OHLCV columns", not missing, f"missing {missing}")
        if not missing:
            nan = int(frame[need].isna().sum().sum())
            self._add(f"{label}: no NaN in OHLCV", nan == 0, f"{nan} NaN cells")
            bad = int(((frame["high"] < frame[["open", "close"]].max(axis=1))
                       | (frame["low"] > frame[["open", "close"]].min(axis=1))).sum())
            self._add(f"{label}: high/low consistent with open/close", bad == 0, f"{bad} bad bars")
        return self

    def contract_identity(self, frame: pd.DataFrame, label: str) -> Gate:
        """Record how roll dates are known: exactly from a symbol column, or by heuristic.

        Not a pass/fail on its own - a heuristic is allowed - but it must be stated, because every figure
        derived from a heuristic roll map inherits that uncertainty.
        """
        if "symbol" in frame.columns:
            rmap = rollmod.from_symbols(frame)
            self._add(f"{label}: contract identity", True,
                      f"EXACT from symbol column: {frame['symbol'].nunique()} contracts, "
                      f"{len(rmap)} transitions", roll_source="symbol", rolls=len(rmap))
        else:
            rmap = rollmod.detect(frame)
            self._add(f"{label}: contract identity", True,
                      f"HEURISTIC (no symbol column): {len(rmap)} suspected rolls. Figures derived from "
                      "this inherit the detector's uncertainty.", roll_source="heuristic", rolls=len(rmap))
        return self

    def reconcile_total(self, label: str, source_total: float, derived_total: float,
                        tol: float = MONEY_TOL) -> Gate:
        """A derived P&L total must equal its source's to the cent. This is the check that caught the
        $322.70 the PBO matrix was dropping."""
        diff = float(derived_total) - float(source_total)
        self._add(f"{label}: derived total reconciles with source", abs(diff) <= tol,
                  f"source ${source_total:,.2f} vs derived ${derived_total:,.2f} (diff ${diff:+,.2f})",
                  source_total=float(source_total), derived_total=float(derived_total), diff=diff)
        return self

    def reconcile_count(self, label: str, source_rows: int, derived_rows: int) -> Gate:
        self._add(f"{label}: row count reconciles", int(source_rows) == int(derived_rows),
                  f"source {source_rows} vs derived {derived_rows}")
        return self

    def no_dates_lost(self, label: str, before: Iterable[date], after: Iterable[date]) -> Gate:
        """No trading date may disappear during processing."""
        lost = sorted(set(before) - set(after))
        self._add(f"{label}: no dates lost in processing", not lost,
                  f"{len(lost)} lost: {[str(d) for d in lost[:8]]}" if lost else "none",
                  lost=len(lost))
        return self

    def zero_is_not_missing(self, label: str, frame: pd.DataFrame) -> Gate:
        """A genuine zero (no position that day) is data; a NaN is absence. The two must never be conflated,
        so after alignment there must be no NaN at all and zeros must be counted explicitly."""
        nan = int(frame.isna().sum().sum())
        zeros = {c: int((frame[c] == 0).sum()) for c in frame.columns}
        self._add(f"{label}: no NaN left after alignment (zero != missing)", nan == 0,
                  f"{nan} NaN cells; genuine no-position days per column: "
                  + ", ".join(f"{k.split()[0]}={v}" for k, v in zeros.items()), zeros=zeros)
        return self

    def documented(self, label: str, note: str) -> Gate:
        """Record a transformation so the run is reproducible from its own log."""
        self._add(f"{label}: transformation documented", bool(note.strip()), note)
        return self

    # ---------------------------------------------------------------- enforcement
    def enforce(self, write_to: str | Path | None = None) -> dict:
        """Raise unless every check passed. Always writes the record first, pass or fail."""
        record = {"experiment": self.experiment, "checks": self.checks,
                  "n_checks": len(self.checks), "n_failed": len(self.failures),
                  "passed": not self.failures}
        if write_to:
            p = Path(write_to)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(record, indent=2, default=str))
        if self.failures:
            lines = "\n".join(f"  FAIL  {c['check']}: {c['detail']}" for c in self.failures)
            raise DataIntegrityError(
                f"{self.experiment}: {len(self.failures)} of {len(self.checks)} integrity checks failed. "
                f"The experiment is stopped; its results would not be trustworthy.\n{lines}")
        return record

    def report(self) -> str:
        head = f"Data integrity: {len(self.checks) - len(self.failures)}/{len(self.checks)} passed"
        return "\n".join([head] + [f"  {'ok  ' if c['ok'] else 'FAIL'}  {c['check']}: {c['detail']}"
                                   for c in self.checks])


def trade_total(trades: Sequence[Any], pt: float, comm: float) -> float:
    """Total net P&L straight from trade objects - the independent side of a reconciliation."""
    return float(sum((t.exit - t.entry) * t.side * pt - comm for t in trades))
