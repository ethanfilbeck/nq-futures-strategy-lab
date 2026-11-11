"""The integrity gate is only worth having if it STOPS a broken experiment.

Most of these tests therefore break something deliberately and assert the gate raises. A gate that only
ever passes is decoration.
"""
import json

import pandas as pd
import pytest

from nq_bot.data import synthetic_bars
from nq_bot.integrity import DataIntegrityError, Gate, trade_total


def test_gate_passes_on_clean_data():
    g = Gate("clean").bars(synthetic_bars(days=20), "bars")
    rec = g.enforce()
    assert rec["passed"] and rec["n_failed"] == 0


def test_gate_stops_the_experiment_when_a_total_does_not_reconcile():
    g = Gate("broken").reconcile_total("H3", source_total=-575.74, derived_total=-463.80)
    with pytest.raises(DataIntegrityError, match="integrity checks failed"):
        g.enforce()
    # and it names the actual discrepancy, which is what makes it actionable
    assert any("322" not in c["detail"] and "-463.80" in c["detail"] for c in g.failures)


def test_gate_catches_the_real_defect_that_was_missed():
    """Regression: the PBO matrix lost $322.70 on exchange half-days and nothing noticed."""
    g = Gate("pbo regression")
    for name, src, derived in (("ORB", -6720.98, -6520.88), ("H3", -575.74, -463.80),
                               ("H4", 1203.88, 1179.86), ("H5", -2336.26, -2279.36)):
        g.reconcile_total(name, src, derived)
    with pytest.raises(DataIntegrityError):
        g.enforce()
    assert len(g.failures) == 4


def test_gate_catches_lost_dates():
    before = [pd.Timestamp(f"2025-01-0{d}").date() for d in range(1, 6)]
    g = Gate("x").no_dates_lost("cal", before, before[:3])
    with pytest.raises(DataIntegrityError, match="no dates lost"):
        g.enforce()


def test_gate_distinguishes_a_genuine_zero_from_a_missing_value():
    ok = pd.DataFrame({"a": [0.0, 1.0, 0.0]})
    Gate("x").zero_is_not_missing("m", ok).enforce()          # zeros are fine
    bad = pd.DataFrame({"a": [0.0, None, 2.0]})
    with pytest.raises(DataIntegrityError, match="zero != missing"):
        Gate("y").zero_is_not_missing("m", bad).enforce()


def test_gate_catches_malformed_bars():
    bars = synthetic_bars(days=10).copy()
    bars.iloc[3, bars.columns.get_loc("high")] = -1.0          # high below open/close
    g = Gate("x").bars(bars, "bars")
    with pytest.raises(DataIntegrityError, match="high/low consistent"):
        g.enforce()

    dupe = pd.concat([synthetic_bars(days=5)] * 2).sort_index()
    with pytest.raises(DataIntegrityError, match="duplicate timestamps"):
        Gate("y").bars(dupe, "bars").enforce()


def test_contract_identity_is_recorded_and_distinguishes_exact_from_heuristic():
    bars = synthetic_bars(days=20)
    g = Gate("x").contract_identity(bars, "no symbols")
    assert g.checks[-1]["roll_source"] == "heuristic"
    withsym = bars.copy()
    withsym["symbol"] = "MNQZ5"
    withsym.loc[withsym.index[len(withsym) // 2]:, "symbol"] = "MNQH6"
    g2 = Gate("y").contract_identity(withsym, "with symbols")
    assert g2.checks[-1]["roll_source"] == "symbol"
    assert g2.checks[-1]["rolls"] == 1
    g.enforce(); g2.enforce()                                  # recording, not failing


def test_record_is_written_even_when_the_gate_fails(tmp_path):
    out = tmp_path / "rec.json"
    g = Gate("x").reconcile_total("a", 1.0, 2.0)
    with pytest.raises(DataIntegrityError):
        g.enforce(write_to=out)
    rec = json.loads(out.read_text())
    assert rec["passed"] is False and rec["n_failed"] == 1


def test_trade_total_matches_a_hand_computation():
    class T:
        def __init__(self, e, x, s): self.entry, self.exit, self.side = e, x, s
    trades = [T(100.0, 110.0, 1), T(100.0, 95.0, -1)]
    # (110-100)*1*2 - 1.24  +  (95-100)*-1*2 - 1.24  =  18.76 + 8.76
    assert trade_total(trades, 2.0, 1.24) == pytest.approx(27.52)
