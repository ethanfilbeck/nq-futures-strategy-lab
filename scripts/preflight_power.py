"""Refuse a hypothesis that cannot clear its own bar even if it is true.

The companion to `preflight_coverage.py`. That one asks "can this data support the rule at all?" before
money is spent. This one asks "can this SAMPLE support the BAR at all?" before a budget line is spent.

A t-statistic on an annualised Sharpe S over T years is approximately S * sqrt(T). To clear a bar B with
probability `power`, not merely to have a coin-flip chance at it:

    S >= (B + z_power) / sqrt(T)   *   sqrt((1 + rho) / (1 - rho))

The `z_power` term and the autocorrelation term were both MISSING from the first version of this script
(2026-11-11) and were found by the Monte Carlo audit in `docs/POWER_GATE_AUDIT.md`. Without them the gate
reported the Sharpe needed for a **50% chance** of clearing the bar and treated every observation as
independent, so it was optimistic on two axes at once and would have approved H8's own 59-event sample.

For this project's data the result is brutal either way: 7.5 years at B = 3.5 and 80% power demands a NET
Sharpe of 1.59 (1.28 at 50% power), against a documented range for a single liquid index future traded
directionally that tops out near 0.9. That is the structural reason eleven of twelve hypotheses failed at
literally zero cost, and the reason a thirteenth on the same sample would be a coin flip dressed as a
t-statistic.

OVERLAPPING OBSERVATIONS ARE THE MOST DANGEROUS CASE and the reason `--hold-days` exists. Holding h days
while rebalancing daily does not create new information, it reuses it. The audit measured the naive
false-positive rate at t >= 3.5 under a pure null: 0.025% at h = 1, but **22.3% at h = 21** and **42.5% at
h = 252**. A 30-year daily study with a monthly hold therefore clears t >= 3.5 on noise about one time in
five. Pass `--hold-days` and compute the final t on NON-OVERLAPPING observations, or with Newey-West.

Running this BEFORE pre-registration is the difference between a null that is informative and a null that
was guaranteed. See `docs/RESEARCH_PROTOCOL.md`.
"""
from __future__ import annotations

import argparse
import math
import statistics
import sys

# Top of the credible published range of NET annualised Sharpe for a single liquid index future traded
# directionally by a retail account with no options and no cross-section.
#
# THIS IS A JUDGEMENT, NOT A MEASUREMENT, and it decides outcomes - so it is deliberately GENEROUS. It sits
# above cross-asset time-series momentum (~0.8) and at the level of a 13-country carry cross-section (0.91),
# neither of which is available on one instrument. Note also that most published figures are GROSS of the
# costs a retail account pays, so comparing a required NET Sharpe against them already favours proceeding.
CEILING = 1.0

# Largest credible per-observation effect (mean/sd) for an event study. H8, the strongest effect this
# project found in twelve attempts, measured 0.33 on the contracts actually held. 0.4 is therefore already
# generous; above it, an "effect" is being hoped for rather than expected.
EFFECT_CEILING = 0.4

TRADING_DAYS = 252

REFERENCE = [
    ("cross-asset time-series momentum (Moskowitz/Ooi/Pedersen 2012)", 0.80),
    ("equity carry, 13-country cross-section (Koijen et al. 2018)", 0.91),
    ("equity basis, single-market timing (Hazelkorn et al. 2020)", 0.38),
    ("volatility-managed market, OUT of sample (Cederburg et al. 2020)", 0.42),
    ("buy-and-hold NDX, 2010-2025", 0.90),
]


def z_for_power(power: float) -> float:
    """One-sided normal quantile. power=0.5 -> 0.0 (a coin flip); 0.8 -> 0.8416."""
    if not 0.0 < power < 1.0:
        raise ValueError("power must be strictly between 0 and 1")
    return statistics.NormalDist().inv_cdf(power)


def autocorr_inflation(rho: float) -> float:
    """Lo (2002): the factor by which an iid standard error understates the truth under AR(1).

    The audit measured the consequence directly: at rho = 0.20 the naive false-positive rate at t >= 3.5
    is 0.275% against a nominal 0.023%, a twelve-fold inflation.
    """
    if not -1.0 < rho < 1.0:
        raise ValueError("rho must be strictly between -1 and 1")
    return math.sqrt((1.0 + rho) / (1.0 - rho))


def required_sharpe(bar: float, years: float, power: float = 0.5, rho: float = 0.0) -> float:
    """Annualised Sharpe needed to reach t = bar over `years`, with probability `power`.

    power defaults to 0.5 so the bare closed form B/sqrt(T) is still available; the CLI defaults to 0.8.
    """
    return (bar + z_for_power(power)) / math.sqrt(years) * autocorr_inflation(rho)


def required_per_observation(bar: float, n: int, power: float = 0.5) -> float:
    """Mean/sd needed per observation to reach t = bar over n INDEPENDENT observations."""
    return (bar + z_for_power(power)) / math.sqrt(n)


def independent_observations(years: float, hold_days: int) -> int:
    """Non-overlapping observations in `years` when each position is held `hold_days`.

    Overlapping holds reuse information rather than adding it; see the module docstring for the measured
    false-positive rates.
    """
    return max(int(years * TRADING_DAYS / max(hold_days, 1)), 0)


def min_backtest_length(trials: int, sharpe: float) -> float:
    """Bailey et al. (2014) minimum backtest length in years, for `trials` independent attempts.

    `sharpe` is the Sharpe the search must not clear by chance. Evaluating it at the REQUIRED Sharpe
    flatters the result (a high threshold is easy to not reach by luck), so the CLI reports it at the
    plausible Sharpe as well. That asymmetry was an audit finding.
    """
    if trials < 2 or sharpe <= 0:
        return 0.0
    return 2.0 * math.log(trials) / (sharpe**2)


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--years", type=float, help="length of the sample in years")
    g.add_argument("--observations", type=int, help="number of INDEPENDENT observations (e.g. 59 events)")
    p.add_argument("--bar", type=float, default=3.5, help="the pre-registered t bar (default 3.5)")
    p.add_argument("--power", type=float, default=0.8,
                   help="probability of clearing the bar if the effect is real (default 0.8)")
    p.add_argument("--autocorr", type=float, default=0.0,
                   help="expected AR(1) autocorrelation of the strategy's returns (default 0)")
    p.add_argument("--hold-days", type=int, default=1,
                   help="days each position is held; >1 means overlapping observations if rebalanced daily")
    p.add_argument("--ceiling", type=float, default=CEILING,
                   help=f"highest credible NET Sharpe for this instrument (default {CEILING})")
    p.add_argument("--effect-ceiling", type=float, default=EFFECT_CEILING,
                   help=f"highest credible per-observation effect for an event study (default {EFFECT_CEILING})")
    p.add_argument("--trials", type=int, default=0, help="also report Bailey minimum backtest length")
    p.add_argument("--label", default="hypothesis", help="name, for the printed verdict")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    a = _parse(argv)
    if a.bar <= 0:
        print("REFUSED: a bar must be positive.")
        return 2
    try:
        z = z_for_power(a.power)
        infl = autocorr_inflation(a.autocorr)
    except ValueError as e:
        print(f"REFUSED: {e}")
        return 2

    print(f"Power preflight: {a.label}   bar t >= {a.bar}   power {a.power:.0%}")
    print("=" * 78)
    if a.power <= 0.5:
        print("  NOTE: at power <= 50% a true effect of exactly the required size is a coin flip.\n")

    if a.observations is not None:
        if a.observations < 2:
            print(f"REFUSED: {a.observations} observations cannot support any test.")
            return 2
        per = required_per_observation(a.bar, a.observations, a.power)
        print(f"  independent observations         {a.observations:>10}")
        print(f"  required mean/sd per observation {per:>10.2f}")
        print(f"  credible effect ceiling          {a.effect_ceiling:>10.2f}")
        print("    for scale: H8, the strongest of twelve attempts, measured 0.33 per event")
        if per > a.effect_ceiling:
            print(f"\nREFUSED: {per:.2f} standard deviations per observation, sustained, exceeds the")
            print(f"  credible ceiling of {a.effect_ceiling:.2f}. The sample is too small for this bar")
            print("  whatever the idea, so a null result would carry no information.")
            need = math.ceil(((a.bar + z) / a.effect_ceiling) ** 2)
            print(f"\n  Observations needed at the ceiling effect: {need}")
            return 2
        print("\nPASS on per-observation effect size. State the expected effect in the pre-registration")
        print("  and confirm it exceeds the figure above.")
        return 0

    years = a.years
    if years <= 0:
        print("REFUSED: sample length must be positive.")
        return 2
    req = required_sharpe(a.bar, years, a.power, a.autocorr)
    n_indep = independent_observations(years, a.hold_days)
    print(f"  sample length                    {years:>10.1f} years")
    print(f"  holding period                   {a.hold_days:>10} days")
    print(f"  non-overlapping observations     {n_indep:>10}")
    if a.autocorr:
        print(f"  AR(1) autocorrelation            {a.autocorr:>10.2f}  (inflates requirement x{infl:.3f})")
    print(f"  required NET annualised Sharpe   {req:>10.2f}")
    print(f"  credible ceiling                 {a.ceiling:>10.2f}")
    print("\n  for scale, documented net Sharpes:")
    for name, s in REFERENCE:
        print(f"    {name:<62}{s:>5.2f}")

    if a.hold_days > 1:
        print(f"\n  OVERLAP WARNING: a {a.hold_days}-day hold rebalanced daily reuses information rather")
        print("  than adding it. The audit measured naive false-positive rates at t >= 3.5 under a pure")
        print("  null of 22.3% at a 21-day hold and 42.5% at 252 days. Compute the final t on the")
        print(f"  {n_indep} non-overlapping observations, or with Newey-West. Do NOT report a naive t.")

    if a.trials >= 2:
        print(f"\n  Bailey minimum backtest length for {a.trials} attempts:")
        print(f"    evaluated at the required Sharpe {req:.2f}: {min_backtest_length(a.trials, req):>6.1f} years")
        at_ceil = min_backtest_length(a.trials, a.ceiling)
        print(f"    evaluated at the credible Sharpe {a.ceiling:.2f}: {at_ceil:>6.1f} years  <- the honest one")
        if at_ceil > years:
            print(f"    WARNING: {years:.1f} years is below that. The best of {a.trials} attempts would")
            print("    clear the bar by chance alone.")

    print()
    if req > a.ceiling:
        print(f"REFUSED: this sample needs a net Sharpe of {req:.2f} to reach t = {a.bar} with")
        print(f"  {a.power:.0%} power, above the credible ceiling of {a.ceiling:.2f} for this instrument.")
        print("  Even a TRUE effect of published size would fail, so a null would carry no information.")
        print("\n  Do not spend a budget line. Either lengthen the sample (longer free daily history")
        print("  costs nothing and is the only honest lever) or do not run the test.")
        print(f"\n  Years needed for a Sharpe-{a.ceiling:.2f} effect: "
              f"{((a.bar + z) / a.ceiling) ** 2 * infl**2:.1f}")
        return 2

    print(f"PASS: a net Sharpe of {req:.2f} is within the credible range. Proceed to pre-registration,")
    print("  and state the expected Sharpe in it so the bar can be checked against the claim.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
