"""The single pre-registered H8 replication on MES (docs/PREREG_H8_ES_REPLICATION.md). Run once.

    py run_h8_es_replication.py data\\mes_2019_2026.csv
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from nq_bot import family3 as f3
from nq_bot.data import load_csv

PT, COMM_RT = 5.0, 1.24          # MES $/point, $0.62 per side
EVENTS = f3.FOMC_DAYS + f3.HOLDOUT_FOMC_DAYS


def net(t):
    return (t.exit - t.entry) * t.side * PT - COMM_RT


def tstat(x):
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 1 else float("nan")


def main(csv):
    bars = load_csv(csv)
    s = f3.Session(bars)
    trades, skipped = f3.run_h8(s, EVENTS)
    pnl = np.array([net(t) for t in trades])
    fomc = {pd.Timestamp(x).date() for x in EVENTS}
    pool = []
    for i in range(len(s.days) - 1):
        p, e = s.days[i], s.days[i + 1]
        if p in fomc or e in fomc:
            continue
        a, b = s.bar(p, "14:00"), s.bar(e, "13:55")
        if a and b:
            pool.append(net(f3._hold(s, a[0], a[1].open + f3.TICK, b[0], b[1].close, 0.03)))
    pool = np.array(pool)
    draws = np.random.default_rng(7).choice(pool, size=(2000, len(pnl)), replace=True).mean(axis=1)
    p95 = float(np.percentile(draws, 95))
    half1 = float(sum(net(t) for t in trades if t.entry_ts.year <= 2022))
    half2 = float(sum(net(t) for t in trades if t.entry_ts.year >= 2023))
    wins, losses = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    pf = float(wins / losses) if losses else float("inf")
    checks = {"net>0 and PF>=1.20": pnl.sum() > 0 and pf >= 1.20, "t>=2.0": tstat(pnl) >= 2.0,
              "beats random 24h longs (>95th pct)": pnl.mean() > p95, "both halves positive": half1 > 0 and half2 > 0}
    out = {"data": [str(bars.index[0]), str(bars.index[-1])], "n": len(pnl), "skipped": skipped,
           "net": float(pnl.sum()), "mean": float(pnl.mean()), "pf": pf, "t": tstat(pnl),
           "win_rate": float((pnl > 0).mean()), "random_mean": float(pool.mean()), "random_p95": p95,
           "net_2019_2022": half1, "net_2023_2026": half2, "checks": checks,
           "verdict": "REPLICATION PASSES (supporting, not independent)" if all(checks.values()) else "REPLICATION FAILS",
           "trades": [{"entry": str(t.entry_ts), "exit": str(t.exit_ts), "entry_px": t.entry, "exit_px": t.exit,
                       "kind": t.kind, "net": round(net(t), 2)} for t in trades]}
    Path("runs").mkdir(exist_ok=True)
    Path("runs/h8_es_replication.json").write_text(json.dumps(out, indent=2, default=lambda o: bool(o) if isinstance(o, np.bool_) else str(o)))
    print(f"n={out['n']} skipped={skipped} net=${out['net']:,.2f} mean=${out['mean']:.2f} PF={pf:.2f} t={out['t']:.2f}")
    print(f"random 24h longs: mean ${out['random_mean']:.2f}, 95th pct ${p95:.2f}")
    print(f"2019-2022 ${half1:,.2f} | 2023-2026 ${half2:,.2f}")
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    print(out["verdict"])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/mes_2019_2026.csv")
