"""Free pre-flight: will a market have enough 1-minute bars to answer an event-window question?

    py scripts\\preflight_coverage.py NKD.v.0 2019-05-06 2026-11-01

Run this BEFORE paying for any new market (docs/RESEARCH_PROTOCOL.md). It uses Databento's
metadata.get_record_count, which is not billed, to compare bars-per-trading-day against a dense
reference market. A thin market can be open nearly 23 hours and still have no trade in the specific
minute a rule needs - "the market is open" and "the market trades every minute" are different claims.

Exists because the NKD replication was bought for $6.25 and came back INVALID on data coverage:
only 16 of 59 events had the two New York minutes the H8 rule needs
(docs/RESULTS_H8_NKD_REPLICATION.md).
"""
import os
import sys

REFERENCE = 1434        # MES bars/trading-day, a continuously traded US index future
FLOOR = 0.80            # refuse below this fraction of the reference


def main(symbol: str, start: str, end: str, dataset: str = "GLBX.MDP3") -> int:
    import databento as db
    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY is not set (expected in .env).")
    client = db.Historical(key)                              # metadata calls below are not billed
    n = client.metadata.get_record_count(dataset=dataset, schema="ohlcv-1m", symbols=[symbol],
                                         stype_in="continuous" if ".v." in symbol or ".c." in symbol else "raw_symbol",
                                         start=start, end=end)
    days = len({d for d in __import__("pandas").bdate_range(start, end).date})
    per_day = n / days if days else 0.0
    ratio = per_day / REFERENCE
    print(f"{symbol} {start} -> {end}: {n:,} bars over ~{days:,} weekdays = {per_day:,.0f} bars/day")
    print(f"  reference (MES, continuously traded): {REFERENCE:,} bars/day -> this market is {ratio:.0%} as dense")
    if ratio >= FLOOR:
        print(f"  OK: dense enough for a rule that needs specific minutes (floor {FLOOR:.0%}).")
        return 0
    print(f"  REFUSE: below the {FLOOR:.0%} floor. A rule needing specific minutes will drop events here.")
    print("  Do not buy this market for an event-window test without widening the rule's entry/exit windows")
    print("  first, and pre-registering that change before any download.")
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
