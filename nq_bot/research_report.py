"""One standard summary for every backtest, so no result is ever assembled by hand again.

Reports what the November 2026 audit showed was missing: transaction costs separated from gross, a
confidence interval rather than a bare t, drawdown, and ROLL EXPOSURE - how many holds crossed a contract
roll and what that artifact was worth (docs/AUDIT_2026_11_ROLLS.md).

Every figure is from a backtest or a simulation. Nothing here is live-money performance.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from . import rolls as rollmod


@dataclass
class Costs:
    """Per-round-turn costs the backtest already charged, so gross can be recovered."""
    commission_rt: float
    slippage_rt: float          # ticks x tick value x 2 sides, in dollars

    @property
    def total(self) -> float:
        return self.commission_rt + self.slippage_rt


def _t(x: np.ndarray) -> float:
    if len(x) < 2:
        return float("nan")
    sd = x.std(ddof=1)
    return float(x.mean() / (sd / math.sqrt(len(x)))) if sd > 0 else float("nan")


def _ci95(x: np.ndarray) -> tuple[float, float]:
    """95% confidence interval for the mean. Normal approximation; n here is usually well under 100,
    so this is slightly optimistic and is labelled as an approximation wherever it is printed."""
    if len(x) < 2:
        return (float("nan"), float("nan"))
    se = x.std(ddof=1) / math.sqrt(len(x))
    return (float(x.mean() - 1.96 * se), float(x.mean() + 1.96 * se))


def _drawdown(x: np.ndarray) -> float:
    eq = np.concatenate([[0.0], np.cumsum(x)])
    peak = np.maximum.accumulate(eq)
    return float((eq - peak).min())


def summarize(trades: Sequence[Any], pnl: Sequence[float], costs: Costs, *,
              bars=None, roll_map: dict | None = None, label: str = "") -> dict:
    """The standard block. `trades` need `.entry_ts`, `.exit_ts`, `.exit`, `.entry`, `.side`, `.kind`."""
    x = np.asarray(list(pnl), dtype=float)
    if len(x) == 0:
        return {"label": label, "n": 0, "note": "no trades"}
    wins, losses = x[x > 0].sum(), -x[x < 0].sum()
    lo, hi = _ci95(x)

    # costs: what the backtest charged, and what the result would be without it
    gross = x + costs.total
    out: dict[str, Any] = {
        "label": label, "n": int(len(x)),
        "net": float(x.sum()), "expectancy_per_trade": float(x.mean()), "median": float(np.median(x)),
        "sd_per_trade": float(x.std(ddof=1)) if len(x) > 1 else float("nan"),
        "profit_factor": float(wins / losses) if losses > 0 else float("inf"),
        "win_rate": float((x > 0).mean()),
        "t_stat": _t(x), "mean_ci95_approx": [lo, hi], "ci_excludes_zero": bool(lo > 0 or hi < 0),
        "max_drawdown": _drawdown(x),
        "costs": {"per_round_turn": costs.total, "commission_rt": costs.commission_rt,
                  "slippage_rt": costs.slippage_rt, "total_charged": float(costs.total * len(x))},
        "gross_of_all_costs": {"net": float(gross.sum()), "t_stat": _t(gross)},
        "double_slippage": {"net": float((x - costs.slippage_rt).sum()), "t_stat": _t(x - costs.slippage_rt)},
        "exit_kinds": {},
        "by_year": {},
    }
    for tr, v in zip(trades, x):
        out["exit_kinds"][tr.kind] = out["exit_kinds"].get(tr.kind, 0) + 1
        y = tr.entry_ts.year
        out["by_year"][y] = round(out["by_year"].get(y, 0.0) + float(v), 2)
    out["by_year"] = dict(sorted(out["by_year"].items()))

    # fragility: does the result survive losing its best trades?
    s = np.sort(x)[::-1]
    out["t_dropping_best"] = {k: _t(s[k:]) for k in (1, 2, 3) if len(s) - k > 1}

    # ROLL EXPOSURE - required. Absent a roll map this says so rather than implying a clean result.
    if roll_map is None and bars is not None:
        roll_map = rollmod.from_symbols(bars) if "symbol" in getattr(bars, "columns", []) \
            else rollmod.detect(bars)
    if roll_map is None:
        out["roll_exposure"] = {"checked": False,
                                "warning": "NOT CHECKED - pass bars or roll_map. An unadjusted continuous "
                                           "series inflates any hold that crosses a roll."}
    else:
        spanning, adj_pnl = 0, []
        for tr, v in zip(trades, x):
            if rollmod.spans(tr.entry_ts, tr.exit_ts, roll_map):
                spanning += 1
                adj = rollmod.adjust_exit(tr.exit, tr.entry_ts, tr.exit_ts, roll_map)
                # price_mult is what one point is worth here, recovered from this trade's own gross
                mult = ((v + costs.commission_rt) / ((tr.exit - tr.entry) * tr.side)
                        if (tr.exit - tr.entry) * tr.side else 0.0)
                adj_pnl.append((adj - tr.entry) * tr.side * mult - costs.commission_rt)
            else:
                adj_pnl.append(float(v))
        a = np.asarray(adj_pnl, dtype=float)
        out["roll_exposure"] = {"checked": True, "holds_spanning_a_roll": spanning,
                                "rolls_in_map": len(roll_map),
                                "share_of_holds": round(spanning / len(x), 4),
                                "artifact_dollars": float(x.sum() - a.sum()),
                                "net_roll_adjusted": float(a.sum()), "t_roll_adjusted": _t(a)}
        if spanning:
            out["roll_exposure"]["warning"] = (
                f"{spanning} of {len(x)} holds cross a contract roll, worth ${x.sum() - a.sum():,.2f}. "
                "Adjusting prices is only a PROXY: re-run on the actual contract held before believing "
                "either figure (docs/AUDIT_2026_11_ROLLS.md).")
    return out


def render(summary: dict) -> str:
    """The summary as a short Markdown block."""
    s = summary
    if not s.get("n"):
        return f"**{s.get('label', 'run')}**: no trades.\n"
    lo, hi = s["mean_ci95_approx"]
    L = [f"**{s['label'] or 'run'}** — SIMULATED, not live performance", "",
         f"| n | {s['n']} |", "|---|---|",
         f"| Net | ${s['net']:,.2f} |",
         f"| Expectancy / trade | ${s['expectancy_per_trade']:,.2f} (median ${s['median']:,.2f}) |",
         f"| t-statistic | {s['t_stat']:.2f} |",
         f"| Mean 95% CI (approx) | ${lo:,.2f} to ${hi:,.2f}"
         f"{' — excludes zero' if s['ci_excludes_zero'] else ' — includes zero'} |",
         f"| Profit factor | {s['profit_factor']:.2f} |",
         f"| Win rate | {s['win_rate']:.1%} |",
         f"| Max drawdown | ${s['max_drawdown']:,.2f} |",
         f"| Costs charged | ${s['costs']['total_charged']:,.2f} "
         f"(${s['costs']['per_round_turn']:.2f}/trade) |",
         f"| Gross of all costs | ${s['gross_of_all_costs']['net']:,.2f}, "
         f"t {s['gross_of_all_costs']['t_stat']:.2f} |",
         f"| At double slippage | ${s['double_slippage']['net']:,.2f}, "
         f"t {s['double_slippage']['t_stat']:.2f} |"]
    if s.get("t_dropping_best"):
        drops = ", ".join(f"−{k}: {v:.2f}" for k, v in s["t_dropping_best"].items())
        L.append(f"| t dropping best trades | {drops} |")
    r = s.get("roll_exposure", {})
    if not r.get("checked"):
        L.append(f"| **Roll exposure** | **{r.get('warning', 'not checked')}** |")
    else:
        L.append(f"| Roll exposure | {r['holds_spanning_a_roll']} of {s['n']} holds cross a roll; "
                 f"artifact ${r.get('artifact_dollars', 0):,.2f}, "
                 f"t roll-adjusted {r.get('t_roll_adjusted', float('nan')):.2f} |")
        if r.get("warning"):
            L.append(f"| **Warning** | {r['warning']} |")
    L += ["", "By year: " + ", ".join(f"{y} ${v:,.0f}" for y, v in s["by_year"].items()), ""]
    return "\n".join(L)
