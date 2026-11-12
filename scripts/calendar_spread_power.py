"""Power arithmetic behind docs/FEASIBILITY_CALENDAR_SPREAD.md.

Free: no data access, no network. Reproduces the table in that document's Verdict
section so the no-go decision can be checked rather than taken on trust.

Sharpe figures are quoted from the published papers; see the document for citations.
A t-statistic for an annualised Sharpe S observed over T years is approximately
S * sqrt(T), so the years needed to reach a bar B is (B / S) ** 2.
"""

import math

BAR = 3.5  # docs/RESEARCH_BUDGET.md rule 3, for a remaining budget line
AVAIL = 7.5  # usable MNQ history, 2019-05 to 2026-11

VARIANTS = [
    ("Koijen 2018 equity carry, CROSS-SECTION 13 indices", 0.91),
    ("Koijen 2018 equity carry, region-grouped", 0.54),
    ("Hazelkorn 2020 equity basis, CROSS-SECTION", 0.83),
    ("Hazelkorn 2020 equity basis, TIMING (single mkt)", 0.38),
]


def t_reachable(sharpe: float, years: float = AVAIL) -> float:
    return sharpe * math.sqrt(years)


def years_needed(sharpe: float, bar: float = BAR) -> float:
    return (bar / sharpe) ** 2


def main() -> None:
    print(f"Available history: {AVAIL:.1f} years;  bar t >= {BAR}\n")
    print(f"{'variant':<52}{'Sharpe':>7}{'t in 7.5y':>11}{'yrs for 3.5':>13}")
    print("-" * 83)
    for name, s in VARIANTS:
        print(f"{name:<52}{s:>7.2f}{t_reachable(s):>11.2f}{years_needed(s):>13.1f}")

    req = BAR / math.sqrt(AVAIL)
    print(f"\nSharpe required to clear t={BAR} in {AVAIL:.1f} years: {req:.2f}")
    print("No equity-index carry/basis variant above reaches it; nor does Koijen's")
    print("diversified all-asset global carry factor (1.20).")

    quarters = AVAIL * 4
    print(f"\nQuarterly roll cycles available: {quarters:.0f}")
    print(f"Per-trade mean/sd needed for t={BAR} on those: {BAR / math.sqrt(quarters):.2f}")


if __name__ == "__main__":
    main()
