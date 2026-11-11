"""Experiment E1: Probability of Backtest Overfitting across all 12 tested hypotheses.

    py run_pbo.py

Research only. Changes no strategy rule, no pre-registration, no published result, and buys no data.
Method and caveats: docs/PBO_ANALYSIS.md, docs/QUANTITATIVE_RESEARCH_LITERATURE_REVIEW.md.

P&L is attributed to each trade's EXIT day, the day it is realised. For multi-day holds (H6) that makes the
series spikier than a mark-to-market series would be; recorded as a limitation rather than smoothed away.
"""
import json
from pathlib import Path

import pandas as pd

from nq_bot import family3 as f3
from nq_bot import family4 as f4
from nq_bot import rolls
from nq_bot.data import load_csv, times
from nq_bot.pbo import cscv, daily_matrix, summary_text

TRAIN_END = "2025-06-30 23:59"
CSV_SOURCES = {
    "ORB": "runs/edge/trades.csv",
    "H1 first-half-hour": "runs/momentum/trades_first_half_hour.csv",
    "H2 rest-of-day": "runs/momentum/trades_rest_of_day.csv",
    "H3 overnight drift": "runs/family2_regen/trades_H3.csv",
    "H4 liquidity sweep": "runs/family2_regen/trades_H4.csv",
    "H5 VWAP pullback": "runs/family2_regen/trades_H5.csv",
}


def calendar(bars) -> list:
    t = times(bars)
    mins = t.hour * 60 + t.minute
    rth = (mins >= 570) & (mins < 960) & (t.weekday < 5)
    counts = pd.Series(1, index=t[rth]).groupby(t[rth].date).sum()
    return [d for d, n in counts.items() if n >= 300]


def from_csv(path: str) -> pd.Series:
    d = pd.read_csv(path)
    ts = pd.to_datetime(d["exit_ts"], utc=True, format="mixed").dt.tz_convert("America/New_York")
    return d.groupby([x.date() for x in ts])["net"].sum()


def from_trades(trades, pt=2.0, comm=1.24, roll_map=None) -> pd.Series:
    rows = {}
    for tr in trades:
        ex = rolls.adjust_exit(tr.exit, tr.entry_ts, tr.exit_ts, roll_map) if roll_map else tr.exit
        d = tr.exit_ts.date()
        rows[d] = rows.get(d, 0.0) + (ex - tr.entry) * tr.side * pt - comm
    return pd.Series(rows)


def build(bars, cal, roll_map=None) -> tuple[pd.DataFrame, dict]:
    s = f4.Session4(bars)
    series, notes = {}, {}
    for name, path in CSV_SOURCES.items():
        if not Path(path).exists():
            notes[name] = f"EXCLUDED: {path} missing"
            continue
        series[name] = from_csv(path)
        notes[name] = f"from {path} (intraday or same-session exit; no roll adjustment applies)"
    for name, fn, mod in (("H6 turn of month", "run_h6", f3), ("H7 gap reversal", "run_h7", f3),
                          ("H8 pre-FOMC", "run_h8", f3), ("H9 macro days", "run_h9", f4),
                          ("H10 pre-holiday", "run_h10", f4), ("H11 opening hour", "run_h11", f4)):
        r = getattr(mod, fn)(s)
        tr = r[0] if isinstance(r, tuple) else r
        series[name] = from_trades(tr, roll_map=roll_map)
        spanning = sum(1 for x in tr if roll_map and rolls.spans(x.entry_ts, x.exit_ts, roll_map))
        notes[name] = (f"regenerated from nq_bot.{mod.__name__.split('.')[-1]}.{fn}, {len(tr)} trades"
                       + (f", {spanning} roll-adjusted" if roll_map else ""))
    return daily_matrix(series, cal), notes


def main() -> None:
    bars = load_csv("data/mnq_train.csv")
    bars = bars[bars.index <= TRAIN_END]
    cal = calendar(bars)
    rm = rolls.detect(bars)
    print(f"calendar: {len(cal)} sessions, {cal[0]} -> {cal[-1]}; {len(rm)} rolls detected\n")

    out = {"sessions": len(cal), "first": str(cal[0]), "last": str(cal[-1]), "rolls_detected": len(rm)}
    for tag, roll_map in (("as_published", None), ("roll_adjusted", rm)):
        M, notes = build(bars, cal, roll_map)
        print(f"===== {tag}: {M.shape[1]} strategies x {M.shape[0]} sessions =====")
        nz = {c: int((M[c] != 0).sum()) for c in M.columns}
        print("  active days per strategy: " + ", ".join(f"{k.split()[0]} {v}" for k, v in nz.items()))
        res = cscv(M, 16)
        print(summary_text(res) + "\n")
        sens = {}
        for s_blocks in (8, 10, 12, 14, 16):
            r = cscv(M, s_blocks)
            sens[s_blocks] = {"pbo": r["pbo"], "combinations": r["n_combinations"],
                              "block_size": r["block_size"], "rows_dropped": r["rows_dropped"]}
            print(f"  S={s_blocks:2d}: PBO {r['pbo']:6.1%}  ({r['n_combinations']:>6,} splits, "
                  f"blocks of {r['block_size']}, {r['rows_dropped']} rows dropped)")
        print()
        out[tag] = {k: v for k, v in res.items() if not k.startswith("_")}
        out[tag]["active_days"] = nz
        out[tag]["sources"] = notes
        out[tag]["sensitivity_by_block_count"] = sens
        out[tag]["net_by_strategy"] = {c: float(M[c].sum()) for c in M.columns}

    Path("runs").mkdir(exist_ok=True)
    Path("runs/pbo.json").write_text(json.dumps(out, indent=2, default=str))
    print("wrote runs/pbo.json")


if __name__ == "__main__":
    main()
