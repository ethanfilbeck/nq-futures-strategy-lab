"""The power preflight must refuse a sample that cannot clear its bar, and must not refuse everything.

A gate that says no to every input is not a control, it is an obstacle; one that says yes to everything is
decoration. Both failure modes are tested here, alongside the four defects the Monte Carlo audit found in
the first version of the script (docs/POWER_GATE_AUDIT.md).
"""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import preflight_power as pp  # noqa: E402

# --------------------------------------------------------------------------------------------------
# arithmetic
# --------------------------------------------------------------------------------------------------


def test_required_sharpe_at_50pct_power_is_the_bare_closed_form():
    assert pp.required_sharpe(3.5, 7.5) == pytest.approx(3.5 / math.sqrt(7.5))
    assert pp.required_sharpe(3.5, 7.5) == pytest.approx(1.278, abs=0.001)


def test_required_sharpe_falls_as_the_sample_lengthens():
    assert pp.required_sharpe(3.5, 30) < pp.required_sharpe(3.5, 7.5)
    assert pp.required_sharpe(3.5, 30) == pytest.approx(0.639, abs=0.001)


def test_required_per_observation_matches_the_closed_form():
    assert pp.required_per_observation(3.5, 59) == pytest.approx(3.5 / math.sqrt(59))


# --------------------------------------------------------------------------------------------------
# DEFECT 1: the first version reported the Sharpe needed for a 50% chance, i.e. a coin flip.
# Monte Carlo confirmed P(t >= 3.5) = 50.1% at the then-"required" Sharpe.
# --------------------------------------------------------------------------------------------------


def test_power_raises_the_requirement_and_matches_the_simulated_value():
    """Simulation found S = 1.59 at 7.5y and 0.79 at 30y for 80% power."""
    assert pp.required_sharpe(3.5, 7.5, power=0.8) == pytest.approx(1.59, abs=0.01)
    assert pp.required_sharpe(3.5, 30.0, power=0.8) == pytest.approx(0.79, abs=0.01)
    assert pp.required_sharpe(3.5, 7.5, power=0.8) > pp.required_sharpe(3.5, 7.5, power=0.5)


def test_z_for_power_is_zero_at_a_coin_flip_and_rejects_impossible_values():
    assert pp.z_for_power(0.5) == pytest.approx(0.0)
    assert pp.z_for_power(0.8) == pytest.approx(0.8416, abs=0.001)
    for bad in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError):
            pp.z_for_power(bad)


# --------------------------------------------------------------------------------------------------
# DEFECT 2: serial correlation was ignored. At rho = 0.20 the audit measured a naive false-positive
# rate of 0.275% against a nominal 0.023% - a twelve-fold inflation.
# --------------------------------------------------------------------------------------------------


def test_autocorrelation_inflates_the_requirement():
    assert pp.autocorr_inflation(0.0) == pytest.approx(1.0)
    assert pp.autocorr_inflation(0.20) == pytest.approx(1.2247, abs=0.001)
    assert pp.required_sharpe(3.5, 30, 0.8, rho=0.2) > pp.required_sharpe(3.5, 30, 0.8, rho=0.0)


def test_negative_autocorrelation_lowers_the_requirement():
    """Mean-reverting equity curves genuinely need less, and the gate must not over-refuse them."""
    assert pp.autocorr_inflation(-0.2) < 1.0
    assert pp.required_sharpe(3.5, 30, 0.8, rho=-0.2) < pp.required_sharpe(3.5, 30, 0.8)


def test_autocorrelation_outside_the_unit_interval_is_rejected():
    for bad in (1.0, -1.0, 1.5):
        with pytest.raises(ValueError):
            pp.autocorr_inflation(bad)


# --------------------------------------------------------------------------------------------------
# DEFECT 3, the serious one: overlapping observations. The audit measured naive false-positive rates
# at t >= 3.5 under a PURE NULL of 22.3% at a 21-day hold and 42.5% at 252 days.
# --------------------------------------------------------------------------------------------------


def test_independent_observations_shrinks_with_the_holding_period():
    assert pp.independent_observations(30, 1) == 30 * 252
    assert pp.independent_observations(30, 21) == 360
    assert pp.independent_observations(30, 252) == 30


def test_hold_days_of_zero_or_less_does_not_divide_by_zero():
    assert pp.independent_observations(30, 0) == 30 * 252
    assert pp.independent_observations(30, -5) == 30 * 252


def test_a_long_sample_with_overlap_and_autocorrelation_is_refused():
    """30 years looks ample until a monthly hold and realistic autocorrelation are declared."""
    assert pp.main(["--years", "30", "--bar", "3.5", "--hold-days", "21", "--autocorr", "0.25"]) == 2


# --------------------------------------------------------------------------------------------------
# DEFECT 4: MinBTL evaluated at the REQUIRED Sharpe flatters the result, because a high threshold is
# easy not to reach by luck. It must also be reported at the plausible Sharpe.
# --------------------------------------------------------------------------------------------------


def test_min_backtest_length_is_longer_at_a_plausible_sharpe_than_at_an_inflated_one():
    assert pp.min_backtest_length(12, 1.0) > pp.min_backtest_length(12, 1.59)
    assert pp.min_backtest_length(12, 1.0) == pytest.approx(2 * math.log(12), abs=0.001)


def test_min_backtest_length_grows_with_trials_and_is_zero_when_undefined():
    assert pp.min_backtest_length(12, 1.0) > pp.min_backtest_length(2, 1.0)
    assert pp.min_backtest_length(1, 1.0) == 0.0      # one trial is not a search
    assert pp.min_backtest_length(12, 0.0) == 0.0     # no division by zero


# --------------------------------------------------------------------------------------------------
# end-to-end verdicts
# --------------------------------------------------------------------------------------------------


def test_the_actual_mnq_sample_is_REFUSED_at_the_projects_bar():
    assert pp.main(["--years", "7.5", "--bar", "3.5"]) == 2


def test_a_long_free_daily_history_PASSES():
    """The gate must not refuse everything, or it carries no information."""
    assert pp.main(["--years", "30", "--bar", "3.5"]) == 0


def test_fifty_nine_events_is_now_REFUSED_where_the_first_version_passed_it():
    """H8's own sample. 0.57 SD per event at 80% power, against a 0.40 ceiling.

    The first version compared against an unjustified 0.5 cut at 50% power and let this through, which is
    exactly the sample we know produced a failed holdout.
    """
    assert pp.main(["--observations", "59", "--bar", "3.5"]) == 2
    assert pp.main(["--observations", "400", "--bar", "3.5"]) == 0


def test_a_lower_bar_does_not_quietly_rescue_the_short_sample():
    """Lowering the bar is prohibited by RESEARCH_BUDGET rule 3; this records what it would buy."""
    assert pp.main(["--years", "7.5", "--bar", "3.5"]) == 2
    assert pp.main(["--years", "7.5", "--bar", "2.0"]) == 2   # still refused at 80% power
    assert pp.main(["--years", "7.5", "--bar", "1.5"]) == 0   # only a bar this low passes


def test_degenerate_inputs_are_refused_not_crashed():
    assert pp.main(["--observations", "1", "--bar", "3.5"]) == 2
    assert pp.main(["--years", "0", "--bar", "3.5"]) == 2
    assert pp.main(["--years", "7.5", "--bar", "0"]) == 2
    assert pp.main(["--years", "30", "--bar", "3.5", "--power", "1.5"]) == 2
    assert pp.main(["--years", "30", "--bar", "3.5", "--autocorr", "1.5"]) == 2
