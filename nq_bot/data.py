"""Market data loading.

- load_csv: your own 1-minute OHLCV export (timestamp,open,high,low,close,volume).
- fetch_databento: CME Globex MDP 3.0 (GLBX.MDP3) 1-minute bars; needs DATABENTO_API_KEY.
- synthetic_bars: RANDOM data for testing the plumbing only. Results on it mean nothing.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

TZ = "America/New_York"


def _normalize(df: pd.DataFrame, tz: str = TZ) -> pd.DataFrame:
    df = df.rename(columns=str.lower)
    need = ["open", "high", "low", "close", "volume"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    idx = pd.DatetimeIndex(df.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx
    df.index = idx.tz_convert(tz)
    df = df[need].astype(float).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    bad = (df["high"] < df[["open", "close"]].max(axis=1)) | (df["low"] > df[["open", "close"]].min(axis=1))
    if bad.any():
        raise ValueError(f"{int(bad.sum())} bars have high/low inconsistent with open/close")
    return df


def load_csv(path: str, tz_of_file: str = "UTC") -> pd.DataFrame:
    """CSV with a timestamp column of bar OPEN times. Naive timestamps are read as `tz_of_file`."""
    raw = pd.read_csv(path)
    ts_col = next(c for c in raw.columns if c.lower() in ("timestamp", "ts_event", "datetime", "time", "date"))
    idx = pd.to_datetime(raw[ts_col], utc=False)
    if getattr(idx.dt, "tz", None) is None:
        idx = idx.dt.tz_localize(tz_of_file)
    raw.index = pd.DatetimeIndex(idx)
    return _normalize(raw.drop(columns=[ts_col]))


def fetch_databento(symbol: str, start: str, end: str, out_csv: str | None = None) -> pd.DataFrame:
    """Download 1-minute bars. symbol examples: 'MNQ.v.0' (volume-rolled continuous),
    'NQ.c.0' (calendar-rolled), or a specific contract like 'MNQZ6'.
    Continuous series are unadjusted: expect price jumps at rolls; the strategy only
    compares prices within one session, so this does not leak across rolls.
    Check the cost estimate in your Databento portal before large pulls."""
    import databento as db  # pip install databento

    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError("Set DATABENTO_API_KEY in your environment / .env")
    stype = "continuous" if "." in symbol else "raw_symbol"
    client = db.Historical(key)
    data = client.timeseries.get_range(dataset="GLBX.MDP3", schema="ohlcv-1m", symbols=[symbol],
                                       stype_in=stype, start=start, end=end)
    df = data.to_df()  # prices already converted to floats, index = ts_event (UTC)
    df = _normalize(df[["open", "high", "low", "close", "volume"]])
    if out_csv:
        df.tz_convert("UTC").rename_axis("timestamp").to_csv(out_csv)
    return df


def synthetic_bars(days: int = 60, start_price: float = 20000.0, seed: int = 7) -> pd.DataFrame:
    """RANDOM-WALK RTH bars for software tests. Not market data. Never draw conclusions from it."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2025-01-06", periods=days)
    frames, price = [], start_price
    for d in dates:
        idx = pd.date_range(f"{d.date()} 09:30", periods=390, freq="1min", tz=TZ)
        drift = rng.normal(0, 0.02)
        vol = abs(rng.normal(4.0, 1.5)) + 1.0
        rets = rng.normal(drift, vol, 390)
        close = price + np.cumsum(rets)
        open_ = np.concatenate([[price], close[:-1]])
        spread = np.abs(rng.normal(0, vol * 0.6, 390))
        high = np.maximum(open_, close) + spread
        low = np.minimum(open_, close) - spread
        q = lambda a: np.round(a * 4) / 4  # noqa: E731
        frames.append(pd.DataFrame({"open": q(open_), "high": q(high), "low": q(low), "close": q(close),
                                    "volume": rng.integers(200, 3000, 390).astype(float)}, index=idx))
        price = close[-1]
    df = pd.concat(frames)
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)
    return df
