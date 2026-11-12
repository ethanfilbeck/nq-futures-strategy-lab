"""Exact contract transitions for a continuous symbol, from Databento symbology (a FREE metadata call).

    py scripts\\roll_map.py MNQ.v.0 2019-05-06 2026-11-01
    py scripts\\roll_map.py MES.v.0 2019-05-06 2026-11-01 --out runs/rollmap_MES.json

Why this exists: the November 2026 audit found that unadjusted continuous series inflate every hold that
crosses a roll (docs/AUDIT_2026_11_ROLLS.md). nq_bot.rolls.detect can only GUESS the roll dates. This gets
them exactly, for nothing, so the correction rests on facts rather than a heuristic.

symbology.resolve is a metadata endpoint and is not billed; this script downloads no market data.

Databento does NOT support continuous -> raw_symbol directly - that returns 422
symbology_invalid_request. It does support continuous -> instrument_id and instrument_id ->
raw_symbol, so this resolves in two hops and falls back to instrument ids if the second fails.
"""
import json
import os
import sys
from pathlib import Path


def _entries(res, symbol):
    """Pull the interval list out of a resolve response, tolerating client-version differences."""
    mappings = res.get("result", res) if isinstance(res, dict) else res
    if isinstance(mappings, dict):
        return mappings.get(symbol) or mappings.get(str(symbol))
    return None


def _rows(entries):
    out = []
    for e in entries or []:
        out.append({"from": e.get("d0") or e.get("start_date"),
                    "to": e.get("d1") or e.get("end_date"),
                    "value": e.get("s") or e.get("symbol")})
    out.sort(key=lambda r: str(r["from"]))
    return out


def main(symbol: str, start: str, end: str, out: str | None) -> int:
    import databento as db
    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY is not set (expected in .env).")
    client = db.Historical(key)

    # Databento supports continuous -> instrument_id and instrument_id -> raw_symbol, but NOT
    # continuous -> raw_symbol directly (that returns 422 symbology_invalid_request). So: two hops.
    res = client.symbology.resolve(dataset="GLBX.MDP3", symbols=[symbol], stype_in="continuous",
                                   stype_out="instrument_id", start_date=start, end_date=end)
    entries = _entries(res, symbol)
    if not entries:
        print("Unexpected response from continuous -> instrument_id; printing it raw:")
        print(json.dumps(res, indent=2, default=str)[:4000])
        return 1
    rows = _rows(entries)
    print(f"{symbol}: {len(rows)} contract periods, {start} -> {end}")

    # hop two: instrument_id -> raw_symbol, so the periods carry human-readable contract codes
    ids = sorted({str(r["value"]) for r in rows if r["value"] is not None})
    id_to_sym: dict[str, str] = {}
    try:
        res2 = client.symbology.resolve(dataset="GLBX.MDP3", symbols=ids, stype_in="instrument_id",
                                        stype_out="raw_symbol", start_date=start, end_date=end)
        for i in ids:
            got = _rows(_entries(res2, i))
            if got:
                id_to_sym[i] = str(got[0]["value"])
    except Exception as e:
        print(f"  note: instrument_id -> raw_symbol failed ({type(e).__name__}: {e}).")
        print("  Falling back to instrument ids, which identify the contract just as well for download.")

    periods = []
    for r in rows:
        iid = str(r["value"])
        periods.append({"from": r["from"], "to": r["to"],
                        "contract": id_to_sym.get(iid, iid),
                        "instrument_id": iid,
                        "stype": "raw_symbol" if iid in id_to_sym else "instrument_id"})

    print(f"\n{'contract':14s} {'instrument_id':14s} {'from':12s} {'to':12s}")
    for r in periods:
        print(f"{str(r['contract']):14s} {r['instrument_id']:14s} {str(r['from']):12s} {str(r['to']):12s}")
    print(f"\n{len(periods) - 1} roll dates = each period's 'from' after the first.")
    if not id_to_sym:
        print("NOTE: contract codes unavailable; the download will use instrument ids instead.")

    path = Path(out or f"runs/rollmap_{symbol.split('.')[0]}.json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"symbol": symbol, "start": start, "end": end, "periods": periods},
                               indent=2, default=str))
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    o = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3], o))
