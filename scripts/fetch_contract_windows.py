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
import time
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nq_bot import family3 as f3  # noqa: E402
from nq_bot.data import _normalize  # noqa: E402

EVENTS = f3.FOMC_DAYS + f3.HOLDOUT_FOMC_DAYS


def front_contract(periods: list[dict], day: pd.Timestamp) -> tuple[str, str] | None:
    """(symbol, stype) the continuous series pointed at on `day`.

    An instrument id is recycled over time, so it is only unambiguous inside its own period - which is
    exactly the window each request uses, so carrying the stype per window is safe and lets a partially
    resolved roll map still be used.
    """
    for p in periods:
        if pd.Timestamp(p["from"]) <= day <= pd.Timestamp(p["to"]):
            return str(p["contract"]), str(p.get("stype", "raw_symbol"))
    return None


def windows(periods: list[dict]) -> list[tuple[str, str, str, str]]:
    """(contract, start, end) covering each event's hold: the day before the event through the event day."""
    out, seen, uncovered = [], set(), []
    for ds in EVENTS:
        ev = pd.Timestamp(ds)
        start, end = ev - pd.Timedelta(days=4), ev + pd.Timedelta(days=1)
        hit = front_contract(periods, ev - pd.Timedelta(days=1))
        if not hit:
            uncovered.append(str(ev.date()))
            continue
        c, st = hit
        key = (c, st, start.date(), end.date())
        if key not in seen:
            seen.add(key)
            out.append((c, str(start.date()), str(end.date()), st))
    if uncovered:
        print(f"  {len(uncovered)} of {len(EVENTS)} events have NO contract in the roll map and cannot be "
              f"priced: {uncovered[:4]}{' ...' if len(uncovered) > 4 else ''}")
    return out


MAX_COST_DEFAULT = 3.00
RETRIES = 4                       # a read timeout is a reason to retry, not to abandon 58 good quotes
PERMANENT = ("symbology_invalid", "422", "not found", "unauthor", "forbidden")


def _transient(e: Exception) -> bool:
    """A network hiccup is retryable; a rejected request is not, and must fail immediately."""
    return not any(k in f"{type(e).__name__} {e}".lower() for k in PERMANENT)


def with_retry(fn, what: str):
    """Call fn(), retrying transient failures with backoff. Raises the last error if all attempts fail."""
    for attempt in range(1, RETRIES + 1):
        try:
            return fn()
        except Exception as e:
            if not _transient(e) or attempt == RETRIES:
                raise
            wait = 2 ** attempt
            print(f"    {what}: {type(e).__name__} (attempt {attempt}/{RETRIES}), retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def cache_path(market: str) -> Path:
    return Path("runs") / f".quote_cache_{market}.json"


def load_cache(market: str) -> dict:
    p = cache_path(market)
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        return {}


def save_cache(market: str, cache: dict) -> None:
    p = cache_path(market)
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(cache, indent=2))


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
    kinds = sorted({p.get("stype", "raw_symbol") for p in m["periods"]})
    print(f"roll map validated: {len(m['periods'])} contract periods, all with a symbol and ordered dates"
          f"  (identified by {', '.join(kinds)})")

    w = windows(m["periods"])
    if not w:
        print("REFUSED: no windows were produced from the roll map.")
        return 2
    covered = len({ds for ds in EVENTS
                   if front_contract(m["periods"], pd.Timestamp(ds) - pd.Timedelta(days=1))})
    print(f"coverage: {covered} of {len(EVENTS)} events have a contract in the roll map"
          + ("" if covered == len(EVENTS) else "  <-- INCOMPLETE, the uncovered events cannot be priced"))
    print(f"{market}: {len(w)} contract windows for {len(EVENTS)} events\n")

    client = db.Historical(key)
    print("exactly what will be requested, if you confirm:")
    print(f"  dataset GLBX.MDP3   schema ohlcv-1m   stype_in {'/'.join(kinds)}   venue CME Globex")
    # dict[str, Any], not dict[str, str]: splatting a str-valued dict into the SDK signatures
    # (whose later positionals are int | None) is a type error even though every value here is a str.
    kw: dict[str, Any] = dict(dataset="GLBX.MDP3", schema="ohlcv-1m")
    total, total_bars = 0.0, 0
    per: list[tuple[str, str, str, str, float, int]] = []
    cache = load_cache(market)
    reused = 0
    for c, a, b, st in w:
        key = f"{st}|{c}|{a}|{b}"
        if key in cache:                              # quotes are free but slow; don't re-ask 59 times
            cost, bars = float(cache[key]["cost"]), int(cache[key]["bars"])
            reused += 1
        else:
            try:
                raw = with_retry(
                    lambda c=c, a=a, b=b, st=st: client.metadata.get_cost(
                        symbols=[c], start=a, end=b, stype_in=st, **kw), f"{c} {a}")
                cost = float(raw)
            except Exception as e:                    # a window we cannot price is one we cannot buy
                how = (f"after {RETRIES} attempts" if _transient(e)
                       else "- the request was rejected, so retrying would not help")
                print(f"REFUSED: could not price {c} {a}..{b} {how}: {type(e).__name__}: {e}")
                print(f"  Nothing was downloaded. {len(per)} quotes are cached, so re-running resumes "
                      "from here rather than starting over.")
                save_cache(market, cache)
                return 2
            # NaN silently defeats a `total > max_cost` comparison, so reject non-finite quotes
            if not math.isfinite(cost) or cost < 0:
                print(f"REFUSED: {c} {a}..{b} returned an unusable quote ({raw!r}). Nothing downloaded.")
                save_cache(market, cache)
                return 2
            try:                                      # record count is also unbilled metadata
                bars = int(with_retry(
                    lambda c=c, a=a, b=b, st=st: client.metadata.get_record_count(
                        symbols=[c], start=a, end=b, stype_in=st, **kw), f"{c} {a} count"))
            except Exception:
                bars = -1                             # not fatal: the COST authorises the charge
            cache[key] = {"cost": cost, "bars": bars}
        per.append((c, a, b, st, cost, bars))
        total += cost
        total_bars += max(bars, 0)
    save_cache(market, cache)
    if reused:
        print(f"  ({reused} of {len(w)} quotes reused from {cache_path(market)})")
    if len(per) != len(w):                            # coverage: priced set must equal requested set
        print(f"REFUSED: priced {len(per)} windows but {len(w)} were requested.")
        return 2
    print(f"    {'contract':12s} {'from':12s} {'to':12s} {'bars':>10s} {'cost':>10s}")
    for c, a, b, st, cost, bars in per:
        print(f"    {c:12s} {a:12s} {b:12s} {bars if bars >= 0 else '?':>10} ${cost:>9.4f}")
    empty = [(c, a, b) for c, a, b, _, _, bars in per if bars == 0]
    if empty:
        print(f"\n  WARNING: {len(empty)} window(s) contain ZERO bars - that contract has no data in that "
              f"range, so those events cannot be priced: {empty[:5]}")
    print(f"\n  {len(w)} requests, {total_bars:,} bars, estimated total ${total:.4f}  "
          f"(ceiling ${max_cost:.2f})")
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
    assert [(c, a, b, st) for c, a, b, st, _, _ in per] == list(w), "priced windows differ from download set"
    for i, (c, a, b, st) in enumerate(w, 1):
        data = client.timeseries.get_range(symbols=[c], start=a, end=b, stype_in=st, **kw)
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
