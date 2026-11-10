"""Print Databento's cost estimate for a download BEFORE paying for it.

    py scripts\\databento_cost.py MES.v.0 2019-05-06 2026-11-01
"""
import os
import sys
from pathlib import Path

import databento as db

for line in Path(".env").read_text().splitlines() if Path(".env").exists() else []:
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

symbol, start, end = sys.argv[1:4]
client = db.Historical(os.environ["DATABENTO_API_KEY"])
cost = client.metadata.get_cost(dataset="GLBX.MDP3", schema="ohlcv-1m", symbols=[symbol],
                                stype_in="continuous" if "." in symbol else "raw_symbol", start=start, end=end)
print(f"{symbol} {start} -> {end} ohlcv-1m: estimated ${cost:.2f}")
