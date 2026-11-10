"""Bar-by-bar backtest using the live engine + SimBroker, plus walk-forward and Monte Carlo."""
from __future__ import annotations

import itertools
import logging

import numpy as np
import pandas as pd

from .broker.sim import SimBroker
from .config import override
from .contracts import SPECS
from .data import times
from .engine import Engine
from .events import EventCalendar
from .features import add_features
from .journal import Alerts, Journal
from .metrics import breakdown, monte_carlo, summarize

log = logging.getLogger("nq_bot.backtest")

COLS = ["open", "high", "low", "close", "minute_of_day", "session_date", "rth", "atr", "atr_ratio",
        "ema_fast", "ema_slow", "ema_slow_slope", "vwap", "or_high", "or_low", "or_mid", "bar_range"]


def run_backtest(bars: pd.DataFrame, cfg, journal_dir=None, quiet=True, featured=None, trade_from=None) -> dict:
    spec = SPECS[cfg.instrument.root]
    feats = featured if featured is not None else add_features(bars, cfg)
    cols = COLS
    if cfg.strategy.name == "intraday_momentum":
        from .momentum import MOM_COLS, add_momentum_features
        if "mom_prev_close" not in feats.columns:
            feats = add_momentum_features(feats, cfg)
        cols = COLS + MOM_COLS
    elif cfg.strategy.name in ("sweep", "vwap_pullback"):
        from .family2 import F2_COLS, add_family2_features
        if "pdh" not in feats.columns:
            feats = add_family2_features(feats, cfg)
        cols = COLS + F2_COLS
    broker = SimBroker(spec, cfg.instrument.slippage_ticks)
    events = EventCalendar(cfg.events.file, cfg.session.timezone,
                           cfg.events.blackout_before_minutes, cfg.events.blackout_after_minutes)
    eng = Engine(cfg, broker, spec, Journal(journal_dir, enabled=journal_dir is not None),
                 Alerts(enabled=not quiet), events)

    eng.entries_from = trade_from
    records = feats[cols].to_dict("records")
    for ts, row in zip(feats.index, records):
        broker.process_bar(ts, row["open"], row["high"], row["low"], row["close"])
        eng.on_bar(ts, row)
        if eng.risk.killed_reason and eng.trade is None and broker.position() == 0:
            log.warning("Backtest stopped by kill switch at %s: %s", ts, eng.risk.killed_reason)
            break
    if broker.position() != 0:  # close anything left at the final close
        last = feats.iloc[-1]
        broker.flatten("end of data")
        broker.process_bar(feats.index[-1], last["close"], last["close"], last["close"], last["close"])
        eng.sync_broker(feats.index[-1])

    trades = pd.DataFrame(eng.trades)
    out = {"trades": trades, "summary": summarize(trades, cfg.risk.starting_equity),
           "killed": eng.risk.killed_reason}
    if not trades.empty:
        out["by_hour"] = breakdown(trades, "entry_hour")
        out["by_regime"] = breakdown(trades, "regime")
        out["by_side"] = breakdown(trades, "side")
        out["monte_carlo"] = monte_carlo(trades["net"].to_numpy(dtype=float), cfg.risk.starting_equity)
    return out


def _score(summary: dict) -> float:
    """Objective for in-sample selection: expectancy penalised by drawdown, min sample size."""
    if summary.get("trades", 0) < 20:
        return -np.inf
    return summary["net_profit"] / (1 + abs(summary["max_drawdown_usd"]))


def walk_forward(bars: pd.DataFrame, cfg, grid: dict, n_folds: int = 4) -> dict:
    """Anchored walk-forward. Days are cut into n_folds+1 equal chunks; fold k picks params on
    chunks 0..k and trades them, unchanged, on chunk k+1. Test windows never overlap, and
    only the concatenated out-of-sample trades are reported."""
    days = sorted(set(times(bars).date))
    chunk = len(days) // (n_folds + 1)
    if chunk < 20:
        raise ValueError("need at least ~20 trading days per chunk (more data or fewer folds)")
    keys = list(grid)
    combos = [dict(zip(keys, v)) for v in itertools.product(*grid.values())]
    oos: list[pd.DataFrame] = []
    folds: list[dict[str, object]] = []
    for k in range(n_folds):
        split = days[(k + 1) * chunk - 1]
        end = days[-1] if k == n_folds - 1 else days[(k + 2) * chunk - 1]
        # test run starts 25 days early so indicators are warm; only trades entered after
        # `split` are counted (risk state from warm-up days is a small, conservative bias).
        train = bars[times(bars).date <= split]
        warm = days[max(0, (k + 1) * chunk - 25)]
        test_full = bars[(times(bars).date >= warm) & (times(bars).date <= end)]
        best, best_s = None, -np.inf
        for c in combos:
            s = _score(run_backtest(train, override(cfg, c))["summary"])
            if s > best_s:
                best, best_s = c, s
        if best is None:
            folds.append({"fold": k, "params": None, "note": "no combo met min sample"})
            continue
        res = run_backtest(test_full, override(cfg, best))
        t = res["trades"]
        if not t.empty:
            t = t[pd.to_datetime(t["entry_ts"]).map(lambda x: x.date()) > split].reset_index(drop=True)
        fold_rec: dict[str, object] = {"fold": k, "train_end": str(split), "test_end": str(end),
                                       "params": best, "oos": summarize(t, cfg.risk.starting_equity)}
        folds.append(fold_rec)
        if not t.empty:
            oos.append(t)
    oos_trades = pd.concat(oos, ignore_index=True) if oos else pd.DataFrame()
    return {"folds": folds, "oos_summary": summarize(oos_trades, cfg.risk.starting_equity),
            "oos_trades": oos_trades}
