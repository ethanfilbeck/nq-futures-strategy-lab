"""Daily performance report (Markdown + JSON) for the paper runner. Every figure is SIMULATED."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd


def _day_trades(trades: list[dict], day) -> pd.DataFrame:
    t = pd.DataFrame(trades)
    if t.empty:
        return t
    return t[pd.to_datetime(t["exit_ts"]).map(lambda x: x.date()) == day]


def _day_events(journal_path, day) -> list[dict]:
    if not journal_path or not Path(journal_path).exists():
        return []
    out = []
    for line in Path(journal_path).read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(rec.get("at", ""))[:10] == str(day):
            out.append(rec)
    return out


def write_daily_report(outdir, day, trades, journal_path, *, bars, gaps, halted, killed, strategy, equity) -> Path:
    t = _day_trades(trades, day)
    ev = _day_events(journal_path, day)
    skips = Counter(e.get("reason", "").split(":")[0].split("(")[0].strip() for e in ev if e.get("event") == "skip")
    issues = [e for e in ev if e.get("event") in ("data_issue", "emergency")
              or (e.get("event") == "order_event" and e.get("status") in ("rejected", "cancelled"))]
    flattens = [e.get("reason") for e in ev if e.get("event") == "flatten"]
    n = len(t)
    wins = int((t["net"] > 0).sum()) if n else 0
    net = float(t["net"].sum()) if n else 0.0
    data = {
        "date": str(day), "mode": "SIMULATED (paper)", "strategy": strategy,
        "trades": n, "wins": wins, "win_rate_pct": round(100 * wins / n, 1) if n else None,
        "net_usd": round(net, 2), "gross_usd": round(float(t["gross"].sum()), 2) if n else 0.0,
        "commissions_usd": round(float(t["commission"].sum()), 2) if n else 0.0,
        "avg_r": round(float(t["r_multiple"].mean()), 3) if n else None,
        "ending_equity_sim": round(float(equity), 2),
        "bars_received": bars, "intraday_gaps": gaps,
        "halted": halted, "killed": killed,
        "signals_skipped": dict(skips), "problems": len(issues), "rule_flattens": flattens,
    }
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    (out / f"report_{day}.json").write_text(json.dumps(data, indent=2, default=str))
    lines = [
        f"# Daily report {day} - SIMULATED (paper)",
        "",
        f"Strategy: **{strategy}**. No real orders were sent.",
        "",
        "| Trades | Win rate | Net | Gross | Commissions | Avg R | Sim equity |",
        "|---|---|---|---|---|---|---|",
        f"| {n} | {data['win_rate_pct'] if n else '-'}% | ${net:,.2f} | ${data['gross_usd']:,.2f} | "
        f"${data['commissions_usd']:,.2f} | {data['avg_r'] if n else '-'} | ${equity:,.2f} |",
        "",
        "## Trades",
    ]
    if n:
        lines += ["| Side | Qty | Entry time | Entry | Exit time | Exit | Exit type | Net |", "|---|---|---|---|---|---|---|---|"]
        for _, r in t.iterrows():
            lines.append(f"| {'long' if r['side'] > 0 else 'short'} | {r['qty']} | {pd.Timestamp(r['entry_ts']):%H:%M} | "
                         f"{r['entry_price']} | {pd.Timestamp(r['exit_ts']):%H:%M} | {r['exit_price']} | {r['exit_kind']} | ${r['net']:,.2f} |")
    else:
        lines.append("No trades. No qualifying setup appeared (the bot does not force trades).")
    lines += ["", "## System health",
              f"- 1-minute bars received: {bars} (gaps inside the day: {gaps})",
              f"- Halted today: {halted or 'no'}",
              f"- Kill switch: {killed or 'off'}",
              f"- Problems logged (bad data, emergencies, rejected/cancelled orders): {len(issues)}",
              f"- Positions closed by rule: {', '.join(str(x) for x in flattens) if flattens else 'none'}"]
    if skips:
        lines += ["", "## Signals skipped by risk rules"] + [f"- {k}: {v}" for k, v in skips.most_common()]
    path = out / f"report_{day}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
