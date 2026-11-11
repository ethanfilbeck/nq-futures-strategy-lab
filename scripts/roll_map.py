"""Exact contract transitions for a continuous symbol, from Databento symbology (a FREE metadata call).

    py scripts\\roll_map.py MNQ.v.0 2019-05-06 2026-11-01
    py scripts\\roll_map.py MES.v.0 2019-05-06 2026-11-01 --out runs/rollmap_MES.json

Why this exists: the November 2026 audit found that unadjusted continuous series inflate every hold that
crosses a roll (docs/AUDIT_2026_11_ROLLS.md). nq_bot.rolls.detect can only GUESS the roll dates. This gets
them exactly, for nothing, so the correction rests on facts rather than a heuristic.

symbology.resolve is a metadata endpoint and is not billed. If Databento ever starts billing it, the
response will say so before any charge; this script downloads no market data either way.
"""
import json
import os
import sys
from pathlib import Path


def main(symbol: str, start: str, end: str, out: str | None) -> int:
    import databento as db
    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY is not set (expected in .env).")
    client = db.Historical(key)
    res = client.symbology.resolve(dataset="GLBX.MDP3", symbols=[symbol], stype_in="continuous",
                                   stype_out="raw_symbol", start_date=start, end_date=end)

    # the shape has moved between client versions, so be explicit rather than assume
    mappings = res.get("result", res) if isinstance(res, dict) else res
    entries = mappings.get(symbol) if isinstance(mappings, dict) else None
    if not entries:
        print("Unexpected response shape; printing it raw so it can be handled:")
        print(json.dumps(res, indent=2, default=str)[:4000])
        return 1

    rows = []
    for e in entries:
        rows.append({"from": e.get("d0") or e.get("start_date"), "to": e.get("d1") or e.get("end_date"),
                     "contract": e.get("s") or e.get("symbol")})
    rows.sort(key=lambda r: str(r["from"]))
    print(f"{symbol}: {len(rows)} contract periods, {start} -> {end}\n")
    print(f"{'front contract':16s} {'from':12s} {'to':12s}")
    for r in rows:
        print(f"{str(r['contract']):16s} {str(r['from']):12s} {str(r['to']):12s}")
    print(f"\n{len(rows) - 1} roll dates = each period's 'from' after the first.")
    path = Path(out or f"runs/rollmap_{symbol.split('.')[0]}.json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"symbol": symbol, "start": start, "end": end, "periods": rows}, indent=2,
                               default=str))
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    o = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3], o))
