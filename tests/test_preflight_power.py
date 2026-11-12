"""The power preflight must refuse a sample that cannot clear its bar, and must not refuse everything.

A gate that says no to every input is not a control, it is an obstacle; a gate that says yes to every
input is decoration. Both failure modes are tested here alongside the arithmetic.
"""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import preflight_power as pp  # noqa: E402


def test_required_sharpe_matches_the_closed_form():
    assert pp.required_sharpe(3.5, 7.5) == pytest.approx(3.5 / math.sqrt(7.5))
    # the number that closed calendar-spread carry, and that the MNQ sample cannot reach
    assert pp.required_sharpe(3.5, 7.5) == pytest.approx(1.278, abs=0.001)


def test_required_sharpe_falls_as_the_sample_lengthens():
    assert pp.required_sharpe(3.5, 30) < pp.required_sharpe(3.5, 7.5)
    assert pp.required_sharpe(3.5, 30) == pytest.approx(0.639, abs=0.001)


def test_required_per_observation_matches_the_closed_form():
    assert pp.required_per_observation(3.5, 59) == pytest.approx(3.5 / math.sqrt(59))


def test_min_backtest_length_grows_with_trials_and_is_zero_when_undefined():
    assert pp.min_backtest_length(12, 1.0) > pp.min_backtest_length(2, 1.0)
    assert pp.min_backtest_length(1, 1.0) == 0.0      # one trial is not a search
    assert pp.min_backtest_length(12, 0.0) == 0.0     # no division by zero


def test_the_actual_mnq_sample_is_REFUSED_at_the_projects_bar():
    """7.5 years at t >= 3.5 needs Sharpe 1.28. This is the whole point of the gate."""
    assert pp.main(["--years", "7.5", "--bar", "3.5"]) == 2


def test_a_long_free_daily_history_PASSES():
    """The gate must not refuse everything, or it carries no information."""
    assert pp.main(["--years", "30", "--bar", "3.5"]) == 0


def test_fifty_nine_events_passes_but_twenty_does_not():
    assert pp.main(["--observations", "59", "--bar", "3.5"]) == 0
    assert pp.main(["--observations", "20", "--bar", "3.5"]) == 2


def test_degenerate_inputs_are_refused_not_crashed():
    assert pp.main(["--observations", "1", "--bar", "3.5"]) == 2
    assert pp.main(["--years", "0", "--bar", "3.5"]) == 2
    assert pp.main(["--years", "7.5", "--bar", "0"]) == 2


def test_a_lower_bar_does_not_quietly_rescue_the_sample():
    """Lowering the bar is prohibited by RESEARCH_PROTOCOL; this records what it would buy."""
    assert pp.main(["--years", "7.5", "--bar", "3.5"]) == 2
    assert pp.main(["--years", "7.5", "--bar", "2.0"]) == 0   # only a bar this low would pass
