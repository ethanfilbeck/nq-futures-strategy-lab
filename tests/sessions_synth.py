"""Synthetic 1-minute bars with KNOWN session returns and volumes, for testing nq_bot/sessions.py.

No real market data is read or written here. Every price is generated.

Calendar (ET, mirrors CME equity futures):
  session d:  Globex 18:00 on the calendar day before d -> 09:29 on d   (930 bars, "pre")
              RTH 09:30 -> 15:59                                       (390 bars)
              post-close 16:00 -> 16:59                                (60 bars)
  half day:   RTH 09:30 -> 12:59 (210 bars), no post-close
  globex-only (Good-Friday-like): 18:00 -> 09:14 (915 bars), no RTH, no post
  holidays:   no bars at all

ON(d) = sum of increments in post(d_prev) + pre(d); RTH(d) = sum of increments in RTH(d). Increments are
target/n plus zero-sum noise, so ln O(d) - ln C(d_prev) and ln C(d) - ln O(d) equal the targets exactly.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

TZ = "America/New_York"


@dataclass
class Spec:
    start: str
    end: str
    on_draw: Callable[[np.random.Generator, int], np.ndarray]
    rth_draw: Callable[[np.random.Generator, int], np.ndarray]
    holidays: Iterable[str] = ()
    half_days: Iterable[str] = ()
    globex_only: Iterable[str] = ()
    vol_on: int = 10
    vol_rth: int = 30
    noise: float = 2e-6
    seed: int = 0
    roll_jumps: dict[str, float] = field(default_factory=dict)   # UTC timestamp -> price factor


def gaussian(sd: float):
    return lambda rng, n: rng.normal(0.0, sd, n)


def student_t(df: float, scale: float):
    return lambda rng, n: scale * rng.standard_t(df, n) / np.sqrt(df / (df - 2))


def make(spec: Spec) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (bars indexed by UTC timestamp, truth per session with ON, RTH, V_ON, V_RTH, kind)."""
    rng = np.random.default_rng(spec.seed)
    days = pd.bdate_range(spec.start, spec.end)
    hol = set(pd.to_datetime(list(spec.holidays)))
    half = set(pd.to_datetime(list(spec.half_days)))
    gx = set(pd.to_datetime(list(spec.globex_only)))
    days = [d for d in days if d not in hol]
    n = len(days)
    on_t, rth_t = spec.on_draw(rng, n), spec.rth_draw(rng, n)
    ts: list[pd.Timestamp] = []
    inc: list[float] = []
    vol: list[int] = []
    truth = []
    prev_post: tuple[list[pd.Timestamp], int] | None = None

    def seg(times: list[pd.Timestamp], target: float, v: int) -> None:
        k = len(times)
        if k == 0:
            return
        e = rng.normal(0, spec.noise, k)
        e -= e.mean()
        ts.extend(times)
        inc.extend((target / k + e).tolist())
        vol.extend([v] * k)

    def minutes(a: pd.Timestamp, b: pd.Timestamp) -> list[pd.Timestamp]:
        return list(pd.date_range(a, b, freq="1min", inclusive="left"))

    for i, d in enumerate(days):
        prev_cal = d - pd.Timedelta(days=1)
        pre_end = d + pd.Timedelta(hours=9, minutes=15) if d in gx else d + pd.Timedelta(hours=9, minutes=30)
        pre = minutes(prev_cal + pd.Timedelta(hours=18), pre_end)
        on_target = on_t[i]
        if prev_post is not None and prev_post[0]:
            share = len(prev_post[0]) / (len(prev_post[0]) + len(pre))
            seg(prev_post[0], on_target * share, spec.vol_on)
            seg(pre, on_target * (1 - share), spec.vol_on)
        else:
            seg(pre, on_target, spec.vol_on)
        kind = "globex_only" if d in gx else "half" if d in half else "normal"
        if d in gx:
            prev_post = ([], 0)
            truth.append({"session": d, "ON": on_target, "RTH": np.nan, "kind": kind})
            continue
        rth_end = d + pd.Timedelta(hours=13) if d in half else d + pd.Timedelta(hours=16)
        seg(minutes(d + pd.Timedelta(hours=9, minutes=30), rth_end), rth_t[i], spec.vol_rth)
        post = [] if d in half else minutes(d + pd.Timedelta(hours=16), d + pd.Timedelta(hours=17))
        prev_post = (post, spec.vol_on)
        truth.append({"session": d, "ON": on_target, "RTH": rth_t[i], "kind": kind})
    # pending post bars of the last session carry no session of their own; emit them with zero target
    if prev_post and prev_post[0]:
        seg(prev_post[0], 0.0, spec.vol_on)
    et = pd.DatetimeIndex(ts).tz_localize(TZ)
    utc = et.tz_convert("UTC")
    level = 10_000.0 * np.exp(np.concatenate([[0.0], np.cumsum(inc)]))
    o, c = level[:-1], level[1:]
    bars = pd.DataFrame({"open": o, "high": np.maximum(o, c) * (1 + 1e-7), "low": np.minimum(o, c) * (1 - 1e-7),
                         "close": c, "volume": np.array(vol, dtype=float)}, index=utc)
    bars.index.name = "timestamp"
    for when, factor in spec.roll_jumps.items():
        m = bars.index >= pd.Timestamp(when, tz="UTC")
        bars.loc[m, ["open", "high", "low", "close"]] *= factor
    tr = pd.DataFrame(truth).set_index("session")
    return bars, tr


def write_csv(bars: pd.DataFrame, path: Path) -> Path:
    out = bars.reset_index()
    out["timestamp"] = out["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S+00:00")
    out.to_csv(path, index=False)
    return path


def rollmap(switch_dates: Iterable[str]) -> dict:
    periods = [{"from": "2000-01-01", "to": "x", "contract": "SYN0"}]
    periods += [{"from": d, "to": "x", "contract": f"SYN{i + 1}"} for i, d in enumerate(switch_dates)]
    return {"symbol": "SYNTHETIC", "periods": periods}
