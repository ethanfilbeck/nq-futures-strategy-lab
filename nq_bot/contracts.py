"""Contract specs and front-month resolution.

NQ:  $20 per index point, tick 0.25 = $5.00
MNQ: $2  per index point, tick 0.25 = $0.50
Quarterly cycle H(Mar) M(Jun) U(Sep) Z(Dec); expires on the third Friday of the month.
Continuous symbols (NQ1!, NQ=F, NQ.c.0) are for charts/research only - they can't be ordered.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class ContractSpec:
    root: str
    tick_size: float
    point_value: float

    @property
    def tick_value(self) -> float:
        return self.tick_size * self.point_value

    def round_to_tick(self, price: float) -> float:
        return round(round(price / self.tick_size) * self.tick_size, 2)


SPECS = {
    "NQ": ContractSpec("NQ", 0.25, 20.0),
    "MNQ": ContractSpec("MNQ", 0.25, 2.0),
}

MONTH_CODES = {3: "H", 6: "M", 9: "U", 12: "Z"}


def third_friday(year: int, month: int) -> date:
    d = date(year, month, 1)
    offset = (4 - d.weekday()) % 7  # Friday = 4
    return d + timedelta(days=offset + 14)


@dataclass(frozen=True)
class FrontMonth:
    root: str
    year: int
    month: int
    expiry: date
    roll_date: date

    @property
    def contract_month(self) -> str:  # IB lastTradeDateOrContractMonth
        return f"{self.year}{self.month:02d}"

    @property
    def local_symbol(self) -> str:  # IB style, e.g. MNQZ6
        return f"{self.root}{MONTH_CODES[self.month]}{self.year % 10}"

    @property
    def tv_symbol(self) -> str:  # TradingView style, e.g. MNQZ2026
        return f"{self.root}{MONTH_CODES[self.month]}{self.year}"


def front_month(root: str, today: date, roll_days: int = 8) -> FrontMonth:
    """Contract to trade on `today`: the nearest quarterly not yet inside its roll window.

    Equity-index liquidity moves to the next quarter roughly 8 days before expiry,
    so we switch at expiry - roll_days. Always confirm against the broker before ordering.
    """
    year = today.year
    for _ in range(3):
        for m in (3, 6, 9, 12):
            exp = third_friday(year, m)
            roll = exp - timedelta(days=roll_days)
            if today < roll:
                return FrontMonth(root, year, m, exp, roll)
        year += 1
    raise RuntimeError("could not resolve front month")
