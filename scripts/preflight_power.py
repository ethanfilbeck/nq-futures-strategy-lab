"""Refuse a hypothesis that cannot clear its own bar even if it is true.

The companion to `preflight_coverage.py`. That one asks "can this data support the rule at all?" before
money is spent. This one asks "can this SAMPLE support the BAR at all?" before a budget line is spent.

The arithmetic is unavoidable and does not depend on the hypothesis. A t-statistic on an annualised Sharpe
S observed over T years is approximately S * sqrt(T), so clearing a bar B requires

    S >= B / sqrt(T)

For this project's data that is brutal: 7.5 years at B = 3.5 demands a NET Sharpe of 1.28. No published
effect for a single liquid index future traded directionally is anywhere near that - cross-asset
time-series momentum is ~0.8 gross, equity carry 0.91 as a 13-country cross-section, and the
single-market basis timing variant 0.38. Buy-and-hold NDX itself is ~0.9.

So a test on 7.5 years at t >= 3.5 can only be passed by an effect stronger than anything in the
literature, or by luck. That is the structural reason eleven of twelve hypotheses failed at literally zero
cost, and the reason a thirteenth on the same sample would be a coin flip dressed as a t-statistic.

Running this BEFORE pre-registration is the difference between a null that is informative and a null that
was guaranteed. See docs/RESEARCH_PROTOCOL.md and docs/FEASIBILITY_CALENDAR_SPREAD.md for the first
hypothesis closed by it.
"""
from __future__ import annotations

import argparse
import math
import sys

# Top of the credible published range of NET annualised Sharpe for a single liquid index future traded
# directionally by a retail account with no options and no cross-section. Deliberately generous: it sits
# above cross-asset time-series momentum (~0.8) and at the level of a 13-country carry cross-section
# (0.91), neither of which is available here. A hypothesis needing more than this is not being tested,
# it is being hoped for.
CEILING = 1.0

TRADING_DAYS = 252

REFERENCE = [
    ("cross-asset time-series momentum (Moskowitz/Ooi/Pedersen 2012)", 0.80),
    ("equity carry, 13-country cross-section (Koijen et al. 2018)", 0.91),
    ("equity basis, single-market timing (Hazelkorn et al. 2020)", 0.38),
    ("volatility-managed market, OUT of sample (Cederburg et al. 2020)", 0.42),
    ("buy-and-hold NDX, 2010-2025", 0.90),
]


def required_sharpe(bar: float, years: float) -> float:
    """Annualised Sharpe needed for t = bar over `years` of data."""
    return bar / math.sqrt(years)


def required_per_observation(bar: float, n: int) -> float:
    """Mean/sd needed per observation for t = bar over n independent observations."""
    return bar / math.sqrt(n)


def min_backtest_length(trials: int, expected_max_sharpe: float) -> float:
    """Bailey et al. (2014) minimum backtest length, in years, for `trials` independent attempts.

    Below this length the expected maximum in-sample Sharpe across the trials exceeds the bar by chance
    alone, so the winner tells you nothing.
    """
    if trials < 2 or expected_max_sharpe <= 0:
        return 0.0
    return 2.0 * math.log(trials) / (expected_max_sharpe**2)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--years", type=float, help="length of the sample in years (daily-or-finer sampling)")
    g.add_argument("--observations", type=int, help="number of INDEPENDENT observations (e.g. 59 events)")
    p.add_argument("--bar", type=float, default=3.5, help="the pre-registered t bar (default 3.5)")
    p.add_argument("--ceiling", type=float, default=CEILING,
                   help=f"highest credible net Sharpe for this instrument (default {CEILING})")
    p.add_argument("--trials", type=int, default=0,
                   help="if given, also report Bailey's minimum backtest length for this many attempts")
    p.add_argument("--label", default="hypothesis", help="name, for the printed verdict")
    a = p.parse_args(argv)

    if a.bar <= 0:
        print("REFUSED: a bar must be positive.")
        return 2

    print(f"Power preflight: {a.label}   bar t >= {a.bar}")
    print("=" * 78)

    if a.observations is not None:
        if a.observations < 2:
            print(f"REFUSED: {a.observations} observations cannot support any test.")
            return 2
        per = required_per_observation(a.bar, a.observations)
        print(f"  independent observations        {a.observations}")
        print(f"  required mean/sd per observation{per:>12.2f}")
        if per >= 0.5:
            print(f"\nREFUSED: {per:.2f} standard deviations per observation, sustained, is not a")
            print("  realistic effect size. The sample is too small for this bar whatever the idea.")
            return 2
        print("\nPASS on per-observation effect size. State the expected effect in the "
              "pre-registration\n  and confirm it exceeds the figure above.")
        return 0

    years = a.years
    if years <= 0:
        print("REFUSED: sample length must be positive.")
        return 2
    req = required_sharpe(a.bar, years)
    print(f"  sample length                   {years:>10.1f} years")
    print(f"  required NET annualised Sharpe  {req:>10.2f}")
    print(f"  credible ceiling                {a.ceiling:>10.2f}")
    print("\n  for scale, documented net Sharpes:")
    for name, s in REFERENCE:
        print(f"    {name:<62}{s:>5.2f}")

    if a.trials >= 2:
        mbtl = min_backtest_length(a.trials, req)
        print(f"\n  Bailey minimum backtest length for {a.trials} attempts at this Sharpe: "
              f"{mbtl:.1f} years")
        if mbtl > years:
            print(f"  WARNING: {years:.1f} years is below that. The best of {a.trials} attempts would")
            print("  clear the bar by chance alone.")

    print()
    if req > a.ceiling:
        print(f"REFUSED: this sample needs a net Sharpe of {req:.2f} to reach t = {a.bar}, above the")
        print(f"  credible ceiling of {a.ceiling:.2f} for this instrument. Even a TRUE effect of")
        print("  published size would fail, so a null result would carry no information.")
        print("\n  Do not spend a budget line. Either lengthen the sample (longer free daily history")
        print("  costs nothing and is the only honest lever) or do not run the test.")
        extra = (a.bar / a.ceiling) ** 2
        print(f"\n  Years needed for a Sharpe-{a.ceiling:.2f} effect to reach t = {a.bar}: {extra:.1f}")
        return 2

    print(f"PASS: a net Sharpe of {req:.2f} is within the credible range. Proceed to pre-registration,")
    print("  and state the expected Sharpe in it so the bar can be checked against the claim.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
