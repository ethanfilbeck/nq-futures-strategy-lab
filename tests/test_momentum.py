"""Mechanics of the pre-registered intraday momentum strategy (no performance claims)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nq_bot.backtest import run_backtest
from nq_bot.config import load_settings, override
from nq_bot.features import add_features
from nq_bot.momentum import add_momentum_features

ROOT = Path(__file__).resolve().parents[1]
TZ = "America/New_York"


def momentum_cfg(variant="first_half_hour"):
    c = load_settings(ROOT / "config/settings.yaml")
    return override(c, {"strategy.name": "intraday_momentum", "momentum.variant": variant,
                        "session.flatten_time": "15:59", "events.file": "none.csv",
                        "risk.starting_equity": 100_000.0, "risk.max_risk_per_trade_usd": 5_000.0,
                        "risk.max_risk_per_trade_pct": 2.0, "risk.max_contracts": 1,
                        "risk.max_daily_loss_usd": 5_000.0, "risk.max_drawdown_pct": 90.0})


def session(day, start, path):
    """390 RTH bars for `day` whose closes follow `path` (array of 390), small ranges."""
    idx = pd.date_range(f"{day} 09:30", periods=390, freq="1min", tz=TZ)
    close = np.asarray(path, dtype=float)
    open_ = np.concatenate([[start], close[:-1]])
    return pd.DataFrame({"open": open_, "high": np.maximum(open_, close) + 0.25,
                         "low": np.minimum(open_, close) - 0.25, "close": close,
                         "volume": 100.0}, index=idx)


def make_days(n=14, up_day_last=True):
    frames, px = [], 20000.0
    for i, d in enumerate(pd.bdate_range("2025-03-03", periods=n)):
        drift = 0.05 if (i % 2 == 0) else -0.05
        if i == n - 1:
            drift = 0.2 if up_day_last else -0.2
        path = px + np.cumsum(np.full(390, drift))
        frames.append(session(d.date(), px, path))
        px = path[-1]
    df = pd.concat(frames)
    # one post-close bar (16:00), as in real 24h futures data, so the time exit has a bar to fill on
    t = df.index[-1] + pd.Timedelta(minutes=1)
    last = df["close"].iloc[-1]
    df.loc[t] = [last, last + 0.25, last - 0.25, last, 50.0]
    return df


def test_features_are_causal():
    cfg = momentum_cfg()
    bars = make_days()
    f = add_momentum_features(add_features(bars, cfg), cfg)
    last = f[f["session_date"] == f["session_date"].iloc[-1]]
    before_10 = last[last["minute_of_day"] < 9 * 60 + 59]
    assert before_10["mom_p1000"].isna().all()               # 10:00 price unknown before 9:59 bar closes
    assert last.loc[last["minute_of_day"] < 15 * 60 + 29, "mom_p1530"].isna().all()
    # previous close = last bar close of the prior session
    prev_day = f[f["session_date"] == f["session_date"].unique()[-2]]
    assert last["mom_prev_close"].iloc[0] == prev_day["close"].iloc[-1]
    # truncating the final day after 15:29 must not change anything known at 15:29
    cut = bars[bars.index <= bars.index[-1] - pd.Timedelta(minutes=30)]
    f2 = add_momentum_features(add_features(cut, cfg), cfg)
    t = f2.index[-1]
    for col in ("mom_prev_close", "mom_p1000", "mom_p1530", "mom_stop_pts"):
        assert f2.loc[t, col] == f.loc[t, col]


@pytest.mark.parametrize("up,side", [(True, 1), (False, -1)])
def test_direction_entry_and_time_exit(up, side):
    cfg = momentum_cfg()
    res = run_backtest(make_days(up_day_last=up), cfg)
    t = res["trades"].iloc[-1]
    assert t["side"] == side
    assert pd.Timestamp(t["entry_ts"]).strftime("%H:%M") == "15:30"   # filled at the 15:30 bar open
    assert t["exit_kind"] == "flatten"                                 # time exit, not a target
    assert pd.Timestamp(t["exit_ts"]).strftime("%H:%M") == "16:00"


def test_one_trade_per_day_and_needs_history():
    cfg = momentum_cfg("rest_of_day")
    t = run_backtest(make_days(n=14), cfg)["trades"]
    days = pd.to_datetime(t["entry_ts"]).map(lambda x: x.date())
    assert days.is_unique
    assert len(t) <= 14 - 10        # first 10 sessions build the stop estimate
