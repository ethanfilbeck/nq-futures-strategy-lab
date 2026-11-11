"""H8 re-run on the ACTUAL contract held for each event. No splicing, no price adjustment.

    py run_h8_contract_level.py MNQ data/mnq_contracts.csv data/mnq_train.csv

This is the correction the November 2026 audit calls for (docs/AUDIT_2026_11_ROLLS.md). A trader buys the
front contract at 14:00 the day before the statement and sells THAT SAME contract at 13:55 on statement day.
They never roll, so there is no roll cost to model - the only error was that a spliced continuous series
misrepresents the price path. Running each event on one contract's real prices removes the artifact instead
of estimating it.

Prices come from the per-contract file (scripts/fetch_contract_windows.py). The trading-day CALENDAR comes
from the continuous file, which is unaffected by the roll defect because only dates are taken from it.
"""
import sys
from pathlib import Path

import pandas as pd

from nq_bot import family3 as f3
from nq_bot.data import load_csv, times
from nq_bot.research_report import Costs, render, summarize

SPEC = {"MNQ": (2.0, 0.25), "MES": (5.0, 0.25), "M2K": (5.0, 0.10)}
COMM_RT = 1.24
EVENTS = f3.FOMC_DAYS + f3.HOLDOUT_FOMC_DAYS


def trading_days(bars) -> list:
    """Dates with a real regular session, from the continuous file. Dates only - no prices used."""
    t = times(bars)
    mins = t.hour * 60 + t.minute
    rth = (mins >= 570) & (mins < 960) & (t.weekday < 5)
    counts = pd.Series(1, index=t[rth]).groupby(t[rth].date).sum()
    return [d for d, n in counts.items() if n >= 300]


def bar_at(frame, day, hm: str):
    """The single bar at `hm` ET on `day` within one contract's frame."""
    h, m = map(int, hm.split(":"))
    t = times(frame)
    sel = frame[(t.hour == h) & (t.minute == m) & (pd.Series([x.date() for x in frame.index],
                                                             index=frame.index) == day)]
    if sel.empty:
        return None
    return sel.index[0], sel.iloc[0]


def main(market: str, contracts_csv: str, continuous_csv: str) -> None:
    pt, tick = SPEC[market]
    f3.TICK = tick
    cal = trading_days(load_csv(continuous_csv))
    idx = {d: i for i, d in enumerate(cal)}
    per = load_csv(contracts_csv)
    if "symbol" not in per.columns:
        raise SystemExit(f"{contracts_csv} has no symbol column - re-run scripts/fetch_contract_windows.py")

    trades, pnl, skipped, used = [], [], [], []
    for ds in EVENTS:
        ev = pd.Timestamp(ds).date()
        i = idx.get(ev)
        if i is None or i == 0:
            skipped.append((ds, "event day not a trading day"))
            continue
        prev = cal[i - 1]
        # the contract that actually traded most on the entry day: the one a trader would have bought
        day_bars = per[[x.date() == prev for x in per.index]]
        if day_bars.empty:
            skipped.append((ds, "no contract bars on the entry day"))
            continue
        contract = day_bars.groupby("symbol")["volume"].sum().idxmax()
        frame = per[per["symbol"] == contract]
        a, b = bar_at(frame, prev, "14:00"), bar_at(frame, ev, "13:55")
        if a is None or b is None:
            skipped.append((ds, f"{contract}: missing 14:00 or 13:55 bar"))
            continue
        # identical rule to f3.run_h8, on one contract only
        entry_px = float(a[1].open) + f3.TICK
        stop = entry_px * 0.97
        path = frame[(frame.index > a[0]) & (frame.index <= b[0])]
        hit = path[path["low"] <= stop]
        if not hit.empty:
            ts, r = hit.index[0], hit.iloc[0]
            exit_px, kind, exit_ts = min(stop, float(r["open"])) - f3.TICK, "stop", ts
        else:
            exit_px, kind, exit_ts = float(b[1].close) - f3.TICK, "time", b[0]
        trades.append(f3.Trade(a[0], exit_ts, 1, entry_px, exit_px, kind))
        pnl.append((exit_px - entry_px) * pt - COMM_RT)
        used.append((ds, contract))

    print(f"{market}: {len(trades)} of {len(EVENTS)} events priced on the actual contract held, "
          f"{len(skipped)} skipped")
    for ds, why in skipped[:10]:
        print(f"   skipped {ds}: {why}")
    print(f"contracts used: {len({c for _, c in used})}\n")
    summ = summarize(trades, pnl, Costs(commission_rt=COMM_RT, slippage_rt=tick * pt * 2),
                     roll_map={}, label=f"H8 on {market}, actual contract held (no splice)")
    print(render(summ))
    out = Path("runs") / f"h8_contract_level_{market}.json"
    out.parent.mkdir(exist_ok=True)
    import json
    out.write_text(json.dumps({"market": market, "events_priced": len(trades),
                               "skipped": [{"event": d, "why": w} for d, w in skipped],
                               "contracts": sorted({c for _, c in used}), "summary": summ}, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
