"""Download the ACTUAL front contract over each H8 hold window, so the re-run needs no price adjustment.

    py scripts\\fetch_contract_windows.py runs/rollmap_MNQ.json              # cost estimate only
    py scripts\\fetch_contract_windows.py runs/rollmap_MNQ.json --confirm    # then download

Why: adjusting a spliced series is a PROXY. A trader buys the front contract at 14:00 and sells THAT
contract at 13:55 the next day - never rolling, so there is no roll cost, only a data artifact. Holding one
contract's real prices across the window removes the artifact instead of estimating it
(docs/AUDIT_2026_11_ROLLS.md).

Each window is one contract over about three calendar days, so the whole set is a tiny fraction of a
full-range pull. The estimate is printed first and nothing downloads without --confirm.
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nq_bot import family3 as f3  # noqa: E402
from nq_bot.data import _normalize  # noqa: E402

EVENTS = f3.FOMC_DAYS + f3.HOLDOUT_FOMC_DAYS


def front_contract(periods: list[dict], day: pd.Timestamp) -> str | None:
    """The contract the continuous series pointed at on `day`."""
    for p in periods:
        if pd.Timestamp(p["from"]) <= day <= pd.Timestamp(p["to"]):
            return str(p["contract"])
    return None


def windows(periods: list[dict]) -> list[tuple[str, str, str]]:
    """(contract, start, end) covering each event's hold: the day before the event through the event day."""
    out, seen = [], set()
    for ds in EVENTS:
        ev = pd.Timestamp(ds)
        start, end = ev - pd.Timedelta(days=4), ev + pd.Timedelta(days=1)
        c = front_contract(periods, ev - pd.Timedelta(days=1))
        if not c:
            print(f"  no contract found for {ev.date()} - skipped")
            continue
        key = (c, start.date(), end.date())
        if key not in seen:
            seen.add(key)
            out.append((c, str(start.date()), str(end.date())))
    return out


def main(mapfile: str, confirm: bool) -> int:
    import databento as db
    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY is not set (expected in .env).")
    m = json.loads(Path(mapfile).read_text())
    market = m["symbol"].split(".")[0]
    w = windows(m["periods"])
    print(f"{market}: {len(w)} contract windows for {len(EVENTS)} events\n")

    client = db.Historical(key)
    total = 0.0
    for c, a, b in w:
        cost = client.metadata.get_cost(dataset="GLBX.MDP3", schema="ohlcv-1m", symbols=[c],
                                        stype_in="raw_symbol", start=a, end=b)
        total += float(cost)
    print(f"estimated total cost: ${total:.4f}")
    if not confirm:
        print("\nestimate only. re-run with --confirm to download.")
        return 0

    frames = []
    for i, (c, a, b) in enumerate(w, 1):
        data = client.timeseries.get_range(dataset="GLBX.MDP3", schema="ohlcv-1m", symbols=[c],
                                           stype_in="raw_symbol", start=a, end=b)
        df = data.to_df()
        if df.empty:
            print(f"  [{i}/{len(w)}] {c} {a}..{b}: EMPTY")
            continue
        df = df[["open", "high", "low", "close", "volume"]].copy()
        df["symbol"] = c
        frames.append(df)
        print(f"  [{i}/{len(w)}] {c} {a}..{b}: {len(df):,} bars")
    if not frames:
        raise SystemExit("nothing downloaded")
    out = _normalize(pd.concat(frames).sort_index())
    path = Path(f"data/{market.lower()}_contracts.csv")
    out.tz_convert("UTC").rename_axis("timestamp").to_csv(path)
    print(f"\nwrote {path}: {len(out):,} bars, {out['symbol'].nunique()} contracts")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1], "--confirm" in sys.argv))
