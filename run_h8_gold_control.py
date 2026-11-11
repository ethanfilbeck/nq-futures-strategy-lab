"""The single pre-registered H8 NEGATIVE CONTROL on Micro Gold futures, MGC
(docs/PREREG_H8_GOLD_CONTROL.md). Run once.

    py run_h8_gold_control.py data\\mgc_2019_2026.csv

Same code path and the same frozen rule as the MES and M2K replications; only the contract specs differ.

This test is read BACKWARDS from the others. Gold carries no equity risk premium, so if H8 is the equity
effect its authors described, the rule should find little or nothing here. A result that clears the usual
four checks therefore counts AGAINST H8: it would mean the drift is not equity-specific and the three equity
"replications" are most likely one shared set of 59 dates counted three times. No outcome here raises H8's
status. See the pre-registration for the full reading, decided before the data was downloaded.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from nq_bot import family3 as f3
from nq_bot.data import load_csv

NAME = "h8_gold_control"
PT, TICK, COMM_RT = 10.0, 0.10, 1.24    # MGC: 10 troy oz, $10 per $1/oz, tick 0.10 ($1.00); $0.62 per side
EVENTS = f3.FOMC_DAYS + f3.HOLDOUT_FOMC_DAYS


def net(t):
    return (t.exit - t.entry) * t.side * PT - COMM_RT


def tstat(x):
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 1 else float("nan")


def main(csv, outdir="runs", allow_rerun=False):
    out_json = Path(outdir) / f"{NAME}.json"
    if out_json.exists() and not allow_rerun:
        raise SystemExit(f"{out_json} already exists. This test is pre-registered to run once.")
    f3.TICK = TICK            # fills slip 1 MGC tick (0.10), not the MNQ tick (0.25)
    bars = load_csv(csv)
    s = f3.Session(bars)
    trades, skipped = f3.run_h8(s, EVENTS)
    # self-check: every entry is the 14:00 bar's open plus exactly one M2K tick
    for t in trades:
        o = bars.loc[t.entry_ts, "open"]
        assert abs((t.entry - o) - TICK) < 1e-9, f"tick model wrong at {t.entry_ts}"
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
    # Inverted reading: this is a control. All four checks clearing = the effect shows up where the equity
    # explanation says it should not = evidence AGAINST H8 being an equity risk premium.
    if all(checks.values()):
        verdict = "DRIFT PRESENT IN GOLD - H8 DOWNGRADED to possible date artifact"
    elif tstat(pnl) <= 0 or pnl.sum() <= 0:
        verdict = "NO DRIFT IN GOLD - control found nothing, equity explanation survives; H8 status unchanged"
    else:
        verdict = "INCONCLUSIVE - positive but short of the bar; H8 status unchanged, caveat recorded"
    by_year = {}
    for t, v in zip(trades, pnl):
        by_year[t.entry_ts.year] = by_year.get(t.entry_ts.year, 0.0) + float(v)
    out = {"market": "MGC (Micro Gold)", "data": [str(bars.index[0]), str(bars.index[-1])], "n": len(pnl),
           "skipped": skipped, "net": float(pnl.sum()), "mean": float(pnl.mean()), "median": float(np.median(pnl)),
           "pf": pf, "t": tstat(pnl), "win_rate": float((pnl > 0).mean()),
           "stops_hit": sum(t.kind == "stop" for t in trades), "random_mean": float(pool.mean()), "random_p95": p95,
           "net_2019_2022": half1, "net_2023_2026": half2, "by_year": by_year, "checks": checks,
           "control_checks_all_cleared": all(checks.values()), "verdict": verdict,
           "trades_file": f"runs/{NAME}_trades.jsonl (git-ignored: prices derived from licensed data)"}
    Path(outdir).mkdir(exist_ok=True)
    rows = [{"entry": str(t.entry_ts), "exit": str(t.exit_ts), "entry_px": t.entry, "exit_px": t.exit,
             "kind": t.kind, "net": round(net(t), 2)} for t in trades]
    (Path(outdir) / f"{NAME}_trades.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))  # git-ignored
    out_json.write_text(json.dumps(out, indent=2, default=lambda o: bool(o) if isinstance(o, np.bool_) else str(o)))
    print(f"n={out['n']} skipped={skipped} net=${out['net']:,.2f} mean=${out['mean']:.2f} PF={pf:.2f} t={out['t']:.2f}"
          f" stops={out['stops_hit']}")
    print(f"random 24h longs: mean ${out['random_mean']:.2f}, 95th pct ${p95:.2f}")
    print(f"2019-2022 ${half1:,.2f} | 2023-2026 ${half2:,.2f}")
    print("  (a CLEARED check here is evidence against H8, not for it)")
    for k, v in checks.items():
        print(f"  {'CLEARED' if v else 'not met'}  {k}")
    print(out["verdict"])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/mgc_2019_2026.csv")
