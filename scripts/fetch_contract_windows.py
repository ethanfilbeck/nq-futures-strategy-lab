"""Download the ACTUAL front contract over each H8 hold window, so the re-run needs no price adjustment.

    py scripts\\fetch_contract_windows.py runs/rollmap_MNQ.json              # cost estimate only
    py scripts\\fetch_contract_windows.py runs/rollmap_MNQ.json --confirm    # then download
    py scripts\\fetch_contract_windows.py runs/rollmap_MNQ.json --confirm --max-cost 5.00

COST. --confirm authorises a BILLED download against the Databento account. An early estimate of
"a few cents" was wrong by about an order of magnitude; extrapolating from the one measured pull
(MNQ full range, 2.17M bars, ~$9.50) this is roughly $1-5. That is an extrapolation, not a
measurement. The script therefore prints the REAL per-window estimate from the free metadata API,
refuses to download above --max-cost (default $3.00), and lists every request it will make.

Why: adjusting a spliced series is a PROXY. A trader buys the front contract at 14:00 and sells THAT
contract at 13:55 the next day - never rolling, so there is no roll cost, only a data artifact. Holding one
contract's real prices across the window removes the artifact instead of estimating it
(docs/AUDIT_2026_11_ROLLS.md).

Each window is one contract over six calendar days. The estimate is printed first, the ceiling is
enforced, and nothing downloads without --confirm.
"""
import json
import math
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


MAX_COST_DEFAULT = 3.00


def main(mapfile: str, confirm: bool, max_cost: float = MAX_COST_DEFAULT) -> int:
    import databento as db
    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY is not set (expected in .env).")
    m = json.loads(Path(mapfile).read_text())
    market = m["symbol"].split(".")[0]

    # the roll map decides which contract each event is priced on, so validate it before trusting it
    bad = []
    for i, per_ in enumerate(m["periods"]):
        c, a, b = per_.get("contract"), per_.get("from"), per_.get("to")
        if not c or not str(c).strip():
            bad.append(f"period {i}: empty contract")
            continue
        try:
            d0, d1 = pd.Timestamp(a), pd.Timestamp(b)
        except Exception:
            bad.append(f"period {i} ({c}): unparseable dates {a!r}..{b!r}")
            continue
        if pd.isna(d0) or pd.isna(d1) or d0 > d1:
            bad.append(f"period {i} ({c}): bad range {a}..{b}")
    if bad:
        print("REFUSED: the roll map is not usable:")
        for line in bad:
            print(f"    {line}")
        return 2
    print(f"roll map validated: {len(m['periods'])} contract periods, all with a symbol and ordered dates")

    w = windows(m["periods"])
    if not w:
        print("REFUSED: no windows were produced from the roll map.")
        return 2
    print(f"{market}: {len(w)} contract windows for {len(EVENTS)} events\n")

    client = db.Historical(key)
    print("exactly what will be requested, if you confirm:")
    print("  dataset GLBX.MDP3   schema ohlcv-1m   stype_in raw_symbol   venue CME Globex")
    total = 0.0
    per = []
    for c, a, b in w:
        try:
            raw = client.metadata.get_cost(dataset="GLBX.MDP3", schema="ohlcv-1m", symbols=[c],
                                           stype_in="raw_symbol", start=a, end=b)
            cost = float(raw)
        except Exception as e:                       # a window we cannot price is a window we cannot buy
            print(f"REFUSED: could not price {c} {a}..{b}: {type(e).__name__}: {e}")
            print("  Nothing was downloaded. Every window must have a quote before any charge.")
            return 2
        # NaN silently defeats a `total > max_cost` comparison, so reject non-finite quotes explicitly
        if not math.isfinite(cost) or cost < 0:
            print(f"REFUSED: {c} {a}..{b} returned an unusable quote ({raw!r}). Nothing was downloaded.")
            return 2
        per.append((c, a, b, cost))
        total += cost
    if len(per) != len(w):                            # coverage: priced set must equal requested set
        print(f"REFUSED: priced {len(per)} windows but {len(w)} were requested.")
        return 2
    for c, a, b, cost in per[:8]:
        print(f"    {c:10s} {a} .. {b}   ${cost:.4f}")
    if len(per) > 8:
        print(f"    ... and {len(per)-8} more windows")
    print(f"\n  {len(w)} requests, estimated total ${total:.4f}  (ceiling ${max_cost:.2f})")
    print("  this is Databento's own figure from the free metadata API, not an extrapolation")
    if total > max_cost:
        print(f"\nREFUSED: ${total:.4f} exceeds the --max-cost ceiling of ${max_cost:.2f}. "
              "Nothing was downloaded. Raise the ceiling deliberately if the figure is acceptable.")
        return 2
    if not confirm:
        print("\nestimate only - nothing downloaded. Re-run with --confirm to authorise the charge.")
        return 0
    print("\n--confirm given: downloading now. This is a BILLED request.")

    frames = []
    assert [(c, a, b) for c, a, b, _ in per] == list(w), "priced windows differ from the ones to download"
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
    mc = float(sys.argv[sys.argv.index("--max-cost") + 1]) if "--max-cost" in sys.argv else MAX_COST_DEFAULT
    sys.exit(main(sys.argv[1], "--confirm" in sys.argv, mc))
