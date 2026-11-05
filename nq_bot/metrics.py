"""Performance metrics from closed trades only."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def summarize(trades: pd.DataFrame, starting_equity: float) -> dict:
    if trades.empty:
        return {"trades": 0, "note": "no trades"}
    pnl = trades["net"].astype(float)
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    equity = starting_equity + pnl.cumsum()
    peak = np.maximum.accumulate(np.concatenate([[starting_equity], equity.values]))[1:]
    dd = (equity.values - peak)
    max_dd = float(dd.min())
    max_dd_pct = float((dd / peak).min() * 100)

    daily = trades.assign(d=pd.to_datetime(trades["exit_ts"]).map(lambda x: x.date())).groupby("d")["net"].sum()
    # daily returns on equity; zero-trade days are excluded (understates vol slightly - noted in docs)
    daily_ret = daily / starting_equity
    sharpe = float(daily_ret.mean() / daily_ret.std() * math.sqrt(252)) if len(daily_ret) > 1 and daily_ret.std() > 0 else float("nan")
    downside = daily_ret[daily_ret < 0]
    sortino = float(daily_ret.mean() / downside.std() * math.sqrt(252)) if len(downside) > 1 and downside.std() > 0 else float("nan")
    gross_win, gross_loss = wins.sum(), -losses.sum()
    return {
        "trades": int(len(pnl)),
        "net_profit": round(float(pnl.sum()), 2),
        "win_rate_pct": round(100 * len(wins) / len(pnl), 1),
        "profit_factor": round(float(gross_win / gross_loss), 2) if gross_loss > 0 else float("inf"),
        "avg_win": round(float(wins.mean()), 2) if len(wins) else 0.0,
        "avg_loss": round(float(losses.mean()), 2) if len(losses) else 0.0,
        "expectancy_per_trade": round(float(pnl.mean()), 2),
        "avg_r": round(float(trades["r_multiple"].dropna().mean()), 3) if "r_multiple" in trades else None,
        "max_drawdown_usd": round(max_dd, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "sharpe_daily_ann": round(sharpe, 2),
        "sortino_daily_ann": round(sortino, 2),
        "commissions": round(float(trades["commission"].sum()), 2),
        "ending_equity": round(float(equity.iloc[-1]), 2),
    }


def breakdown(trades: pd.DataFrame, by: str) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    g = trades.groupby(by)["net"]
    return pd.DataFrame({"trades": g.size(), "net": g.sum().round(2), "avg": g.mean().round(2),
                         "win_rate_pct": (g.apply(lambda s: (s > 0).mean() * 100)).round(1)})


def monte_carlo(pnl: np.ndarray, starting_equity: float, n: int = 5000, seed: int = 1) -> dict:
    """Bootstrap-resample trade P&L to see the spread of outcomes the same edge could produce."""
    if len(pnl) < 10:
        return {"note": "fewer than 10 trades - Monte Carlo not meaningful"}
    rng = np.random.default_rng(seed)
    sims = rng.choice(pnl, size=(n, len(pnl)), replace=True)
    curves = starting_equity + sims.cumsum(axis=1)
    peaks = np.maximum.accumulate(np.hstack([np.full((n, 1), starting_equity), curves]), axis=1)[:, 1:]
    max_dd = ((curves - peaks) / peaks).min(axis=1) * 100
    final = curves[:, -1] - starting_equity
    return {
        "runs": n,
        "p_losing": round(float((final < 0).mean()) * 100, 1),
        "net_p5": round(float(np.percentile(final, 5)), 2),
        "net_p50": round(float(np.percentile(final, 50)), 2),
        "net_p95": round(float(np.percentile(final, 95)), 2),
        "max_dd_pct_p50": round(float(np.percentile(max_dd, 50)), 2),
        "max_dd_pct_p95_worst": round(float(np.percentile(max_dd, 5)), 2),
    }
