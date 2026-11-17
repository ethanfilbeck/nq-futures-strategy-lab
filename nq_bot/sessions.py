"""Overnight vs regular-session behaviour in MNQ: a descriptive study.

Implements docs/DRAFT_PREREG_SESSIONS_awaiting_signoff.md (protocol v4). Section numbers in comments refer
to that document. HISTORICAL ACADEMIC RESEARCH ONLY: nothing in this module produces, evaluates or implies a
trading rule, signal, position, strategy return or profitability statement. Any trading idea drawn from this
data is permanently ineligible under docs/RESEARCH_BUDGET.md rule 1.

Design rules that the tests enforce:
- No hourly or sub-window MEAN of returns (H3 overlap), no corr/cov/regression of ON and RTH, no Var(CC), no
  RTH statistic conditioned on ON's sign or size (H7 overlap), no half-hour returns (H1/H2), and nothing that
  links a quantity to a later period's return (protocol section 6.3). `assert_no_forbidden` scans every result.
- The official verdict is INCONCLUSIVE (decision D2-a = O1). `official_verdict` takes development results
  only; O2 (the restricted secondary population) cannot reach it by construction (section 7).
- A minute with no bar is a minute with no trade: it contributes zero volume and no price, and is never
  imputed. A zero-volume BAR is a data error and stops the run (section 6.1, P1 specification).
"""
from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .integrity import DataIntegrityError

# ---------------------------------------------------------------- frozen protocol constants
TZ = "America/New_York"
RTH_START, RTH_END = 570, 960            # 09:30 <= minute-of-day < 16:00 ET (section 4.5)
OPEN_WIN_END = 575                       # O(d): earliest bar in [09:30, 09:35)       (section 4.6)
CLOSE_WIN_START = 955                    # C(d): latest bar in [15:55, 16:00)          (section 4.6)
EARLY_CLOSE_LAST_MAX = 795               # early close: last RTH bar at or before 13:15 (E1)
SESSION_SHIFT_H = 6                      # CME session date = date(ET + 6 h)           (section 4.4)
RTH_HOURS, ON_HOURS = 6.5, 16.5          # V1 per-hour normalisation                   (section 6.1)
EWMA_LAMBDA, EWMA_BURN = 0.94, 20        # T1/T2 scaling                               (section 7)
HILL_FRAC, EXTREME_FRAC = 0.05, 0.05     # Hill k and the L1 extreme set               (section 6.1)
B_DEFAULT, BLOCK_DEV, BLOCK_HO_WEEKS = 10_000, 20, 4
SEED_DEV, SEED_HO = 20261111, 20261112
ALPHA_FWER, M_TESTS = 0.01, 5
REGIMES = {"R1": ("2020-01-01", "2020-12-31"), "R2": ("2021-01-01", "2021-12-31"),
           "R3": ("2022-01-01", "2022-12-31"), "R4": ("2023-01-01", "2025-06-30")}
LIMIT_REGIME_END = pd.Timestamp("2020-10-12")       # +/-5% overnight band until this date (section 5.5)
LIMIT_FLAG_PRE, LIMIT_FLAG_POST = 0.045, 0.065      # descriptive |ON| flags (section 5.5)
LIMIT_LOCK_SESSIONS = ("2020-03-09", "2020-03-17", "2020-03-18")   # S3 (2020-03-16 is already E4)

# Minimum sizes (section 7). Below these an analysis is refused, and the refusal is reported.
MIN_DEV_SESSIONS, MIN_V1, MIN_REGIME, MIN_HILL_K = 1000, 500, 150, 20
MIN_O2_SESSIONS, MIN_O2_V1 = 100, 80

# Literature direction of each test: +1 / -1 / 0 (either sign). Section 6.1 and 7.1.
DIRECTION = {"V1": +1, "T1": -1, "T2": 0, "P1": +1, "L1": +1}
TESTS = tuple(DIRECTION)

# Decision U7 (Ethan, 2026-11-12, option 3). Calibration scenario 2 (volatility clustering that evolves independently in the
# overnight and RTH series) rejected V1's true null in 19.4% of replications at 1% (3,884 / 20,000; Wilson 95%
# 18.9-20.0%) (see SESSIONS_CALIBRATION.json). V1 therefore keeps its
# point estimate, its effect sizes and its role as a pipeline integrity check, but its p-value and intervals are
# DESCRIPTIVE ONLY: V1 never establishes significance and never reaches the official verdict. No substitute
# method is used. The other four tests are unchanged. Holm: see decision U8 below.
DESCRIPTIVE_ONLY = ("V1",)
INFERENTIAL_TESTS = tuple(t for t in TESTS if t not in DESCRIPTIVE_ONLY)
V1_ROLE = "descriptive only (decision U7)"
V1_CALIBRATION_NOTE = ("V1 p-value and intervals are descriptive only (decision U7): with volatility "
                       "clustering that evolves independently in the two periods (calibration scenario 2) the V1 "
                       "bootstrap test rejected a true null in 19.4% of 20,000 calibration replications at the 1% level. V1 cannot establish significance and does not "
                       "influence the official verdict.")
# Decision U8 (approved 2026-11-12). Holm keeps all five slots (m = M_TESTS = 5). V1's slot receives the fixed
# value HOLM_PLACEHOLDER_P = 1.0. This is an ADMINISTRATIVE PLACEHOLDER, NOT an observed V1 p-value: V1 remains
# descriptive only and cannot establish statistical significance. T1, T2, P1 and L1 keep their existing
# definitions and face the thresholds 0.01/5, 0.01/4, 0.01/3, 0.01/2 in step-down order. Keeping five slots for
# four inferential tests is intentionally conservative (dropping V1 would loosen the first threshold to 0.0025).
HOLM_PLACEHOLDER_P = 1.0
HOLM_PLACEHOLDER_NOTE = ("V1's Holm slot holds the fixed administrative placeholder 1.0 (decision U8). It is not "
                         "an observed V1 p-value. V1 is descriptive only and cannot establish significance. The "
                         "five-slot correction is intentionally conservative; T1, T2, P1 and L1 are unchanged.")
# Protocol v4.2, section 7.2 (binding disclosures; decision P1 of 2026-11-12). Nothing here changes a method.
P1_CALIBRATION_NOTE = ("P1 calibration limitation: under its true null the frozen centered block-bootstrap test "
                       "rejected 1.33-1.50% at nominal 1% and 0.33-0.34% at 0.2% (20,000 synthetic repetitions); "
                       "9,999 resamples did not reduce this, so it is a property of the method at n = 1,230, not of "
                       "B. Its 99% intervals covered about 98.3-98.6%. A development 'established' label for P1 is "
                       "NOT established confirmatory evidence until P1's statistical validity has been "
                       "independently reviewed.")
FWER_NOTE = ("The four inferential tests are corrected by Holm at 1% over five slots, but a 1% family-wise error "
             "rate is NOT verified: P1 is mildly liberal, so the realised rate may slightly exceed 1%.")
CALIBRATION_DISCLOSURES = {"P1": P1_CALIBRATION_NOTE, "family_wise_error": FWER_NOTE}
V1_INFERENTIAL_KEYS = ("p_two_sided", "p_holm", "holm_reject", "q_bh_information_only", "ci99",
                       "ci998_bonferroni")
V1_VERDICT_LABEL = ("NOT A CONFIRMATORY CLAIM - descriptive estimate only (decision U7); "
                    "reported as a pipeline integrity check")

O2_CAPTION = ("Secondary analysis. Restricted population: Mondays, Thursdays and Fridays in the 2025-07 -> "
              "2026-10 holdout, selected because no MNQ prices from these sessions were used in earlier "
              "experiments. Exposed through correlated-market computations. Not a clean holdout; not "
              "representative of the full trading week; cannot confirm or reject any claim.")

RULES = ("E1", "E2", "E3", "E4", "E5", "E6")


class InsufficientSample(RuntimeError):
    """A pre-registered minimum size is not met. The analysis is refused, not run on fewer observations."""


class ForbiddenQuantityError(RuntimeError):
    """A result contains a quantity the protocol forbids (section 6.3)."""


# ---------------------------------------------------------------- loading
def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_hashes(expected: Mapping[str | Path, str]) -> None:
    """Every pinned file must match its recorded SHA-256 (section 3). Raises before anything is read."""
    bad = [f"{p}: expected {h[:12]}..., found {sha256_file(p)[:12]}..." for p, h in expected.items()
           if sha256_file(p) != h]
    if bad:
        raise DataIntegrityError("pinned file hash mismatch:\n  " + "\n  ".join(bad))


def read_bars(paths: Iterable[str | Path]) -> pd.DataFrame:
    """Concatenate RAW BARS from several files, then de-duplicate by timestamp (never by session).

    v1's count bug came from building per-file session tables and de-duplicating sessions; a session that
    straddles two files then lost its RTH half. Here sessions are built once, from the merged bars.
    Duplicate timestamps must carry identical rows; a disagreement is a data error, not something to resolve
    silently.
    """
    frames = []
    for p in paths:
        f = pd.read_csv(p, usecols=["timestamp", "open", "high", "low", "close", "volume"])
        f["timestamp"] = pd.to_datetime(f["timestamp"], utc=True)
        frames.append(f)
    bars = pd.concat(frames, ignore_index=True)
    dup = bars.duplicated("timestamp", keep=False)
    if dup.any():
        d = bars[dup]
        conflicting = d.groupby("timestamp").nunique().gt(1).any(axis=1)
        if conflicting.any():
            raise DataIntegrityError(f"{int(conflicting.sum())} duplicated timestamps carry different values "
                                     f"across files, e.g. {conflicting[conflicting].index[0]}")
        bars = bars.drop_duplicates("timestamp")
    bars = bars.sort_values("timestamp").set_index("timestamp")
    return bars


def check_bars(bars: pd.DataFrame) -> None:
    """Bar sanity beyond integrity.Gate.bars: positive prices, and NO zero-volume bars (P1 specification)."""
    if pd.DatetimeIndex(bars.index).tz is None:
        raise DataIntegrityError("timestamps must be timezone-aware")
    if not bars.index.is_monotonic_increasing or bars.index.has_duplicates:
        raise DataIntegrityError("timestamps must be strictly increasing and unique")
    if bars[["open", "high", "low", "close", "volume"]].isna().any().any():
        raise DataIntegrityError("NaN in OHLCV")
    if (bars[["open", "high", "low", "close"]] <= 0).any().any():
        raise DataIntegrityError("non-positive price")
    zero = int((bars["volume"] <= 0).sum())
    if zero:
        raise DataIntegrityError(f"{zero} zero-volume bar(s): a bar exists only when a trade occurred, so a "
                                 "zero-volume bar is a data error (P1 specification)")


# ---------------------------------------------------------------- sessions (section 4)
def session_table(bars: pd.DataFrame) -> pd.DataFrame:
    """One row per CME session date with any bar. Prices are the protocol's boundary prices; nothing else.

    Columns: n_bars, n_rth, last_rth_min, O, C, vol_pre (session bars before 09:30 on d), vol_rth,
    vol_post (bars at or after 16:00 on d, i.e. 16:00-16:59), offset_ok (one UTC offset per session).
    """
    utc_idx = pd.DatetimeIndex(bars.index)
    et = utc_idx.tz_convert(TZ)
    minute = et.hour * 60 + et.minute
    sess = pd.DatetimeIndex((et + pd.Timedelta(hours=SESSION_SHIFT_H)).date)
    cal_date = pd.DatetimeIndex(et.date)
    same_day = cal_date == sess
    rth = same_day & (minute >= RTH_START) & (minute < RTH_END)
    pre = ~same_day | (minute < RTH_START)                      # 18:00 prev evening .. 09:29 on d
    post = same_day & (minute >= RTH_END)                       # 16:00 .. 16:59 on d
    df = pd.DataFrame({"s": sess, "m": minute, "rth": rth, "pre": pre, "post": post,
                       "open": bars["open"].to_numpy(), "close": bars["close"].to_numpy(),
                       "vol": bars["volume"].to_numpy(dtype=float),
                       "off": (et.tz_localize(None) - utc_idx.tz_convert("UTC").tz_localize(None)).total_seconds()})
    g = df.groupby("s")
    out = pd.DataFrame({"n_bars": g.size(),
                        "n_rth": g["rth"].sum().astype(int),
                        "offset_ok": g["off"].nunique() == 1})
    r = df[df.rth]
    out["last_rth_min"] = r.groupby("s")["m"].max()
    ow = r[r.m < OPEN_WIN_END].sort_values("m").groupby("s").first()
    cw = r[r.m >= CLOSE_WIN_START].sort_values("m").groupby("s").last()
    out["O"], out["C"] = ow["open"], cw["close"]
    out["vol_pre"] = df[df.pre].groupby("s")["vol"].sum()
    out["vol_rth"] = r.groupby("s")["vol"].sum()
    out["vol_post"] = df[df.post].groupby("s")["vol"].sum()
    out[["vol_pre", "vol_rth", "vol_post"]] = out[["vol_pre", "vol_rth", "vol_post"]].fillna(0.0)
    if not out["offset_ok"].all():
        bad = list(out.index[~out["offset_ok"]][:3])
        raise DataIntegrityError(f"session(s) span a DST change, which the CME schedule rules out: {bad}")
    return out.sort_index()


@dataclass(frozen=True)
class Calendar:
    """Event inputs to the exclusion rules. All dates are session dates (naive, ET calendar)."""

    roll_switch_utc: tuple[pd.Timestamp, ...]          # E4: from runs/rollmap_MNQ.json, 00:00 UTC
    fomc_statement_days: tuple[pd.Timestamp, ...]       # E6: FOMC_DAYS + HOLDOUT_FOMC_DAYS


def rollmap_switches(rollmap: Mapping[str, Any]) -> tuple[pd.Timestamp, ...]:
    """Contract switch instants: each period after the first starts at 00:00 UTC on its 'from' date."""
    return tuple(pd.Timestamp(p["from"], tz="UTC") for p in rollmap["periods"][1:])


def build_sample(sessions: pd.DataFrame, cal: Calendar, start: str, end: str) -> pd.DataFrame:
    """Apply E1..E6 in order (section 5.1) to sessions dated in [start, end]; compute ON, RTH, volumes.

    d_rth_prev is the previous session WITH RTH trading. A session that had Globex trading but no RTH
    between d_rth_prev and d triggers E5 (section 5.4); ON is then never bridged across it. E2/E3 refer to
    d_rth_prev, which reproduces the reconciled counts in section 5.2 (see unresolved issue U1 in the
    synthetic-testing report for the wording of section 4.7).
    Returns ALL sessions with RTH in the window, with an 'excluded_by' column ('' = eligible).
    """
    s = sessions
    has_rth = s["n_rth"] > 0
    rth_sessions = s.index[has_rth]
    rows = []
    switches = [t.tz_convert(TZ) for t in cal.roll_switch_utc]
    fomc = set(pd.DatetimeIndex(cal.fomc_statement_days))
    before_fomc = set()
    for e in fomc:
        if e not in rth_sessions:        # a statement day outside the loaded data marks nothing (defect found
            continue                     # in synthetic testing: it used to mark the last loaded session)
        prior = rth_sessions[rth_sessions < e]
        if len(prior):
            before_fomc.add(prior[-1])
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    for i, d in enumerate(rth_sessions):
        if not (lo <= d <= hi) or i == 0:
            continue
        p = rth_sessions[i - 1]
        r, rp = s.loc[d], s.loc[p]
        early = bool(r.last_rth_min <= EARLY_CLOSE_LAST_MAX)
        prev_early = bool(rp.last_rth_min <= EARLY_CLOSE_LAST_MAX)
        missing = pd.isna(r.O) or pd.isna(r.C) or pd.isna(rp.C)
        c_prev_t = (p + pd.Timedelta(hours=16)).tz_localize(TZ)
        o_t = (d + pd.Timedelta(hours=9, minutes=30)).tz_localize(TZ)
        roll = any(c_prev_t < t <= o_t for t in switches)
        between = s.index[(s.index > p) & (s.index < d)]
        no_rth_between = bool(len(between)) and not bool(s.loc[between, "n_rth"].gt(0).any())
        fomc_pair = d in fomc or d in before_fomc
        rule = ("E1" if early else "E2" if prev_early else "E3" if missing else "E4" if roll
                else "E5" if no_rth_between else "E6" if fomc_pair else "")
        on = float(np.log(r.O) - np.log(rp.C)) if not missing else np.nan
        rt = float(np.log(r.C) - np.log(r.O)) if not missing else np.nan
        rows.append({"session": d, "prev": p, "excluded_by": rule, "is_fomc_pair": fomc_pair,
                     "ON": on, "RTH": rt, "V_ON": float(rp.vol_post + r.vol_pre), "V_RTH": float(r.vol_rth),
                     "long_overnight": (d - p).days > 1, "weekday": d.dayofweek})
    out = pd.DataFrame(rows).set_index("session")
    return out


def exclusion_counts(sample: pd.DataFrame) -> dict[str, int]:
    """Sequential removals per rule, as reported in section 5.2."""
    c = sample["excluded_by"].value_counts()
    res = {k: int(c.get(k, 0)) for k in RULES}
    res["start"] = len(sample)
    res["eligible_E1_E5"] = int((~sample["excluded_by"].isin(RULES[:5])).sum())
    res["primary_E1_E6"] = int((sample["excluded_by"] == "").sum())
    return res


def analysis_set(sample: pd.DataFrame, drop_e6: bool = True) -> pd.DataFrame:
    """The analysis sample: E1-E5 always removed; E6 removed unless the S5 sensitivity is requested."""
    keep = ~sample["excluded_by"].isin(RULES[:5])
    if drop_e6:
        keep &= sample["excluded_by"] != "E6"
    return sample[keep].copy()


def v1_mask(sample: pd.DataFrame) -> np.ndarray:
    """V1 sub-sample: Tue-Fri sessions that are not long overnights (section 6.1)."""
    return (sample["weekday"].isin([1, 2, 3, 4]) & ~sample["long_overnight"]).to_numpy()


# ---------------------------------------------------------------- statistics (section 6.1)
def ewma_scale(r: np.ndarray, lam: float = EWMA_LAMBDA, burn: int = EWMA_BURN) -> np.ndarray:
    """Causal vol-scaling (protocol v4 section 7, "EWMA rule"; exact start-up rule U3).

    Sessions are the analysis sessions of one period, in time order, indexed t = 0, 1, ...
      start-up:  sigma2[20] = mean(r[0..19]^2)            (the 20 burn-in sessions; z[0..19] = NaN, dropped)
      recursion: sigma2[t]  = lam*sigma2[t-1] + (1-lam)*r[t-1]^2   for t >= 21, lam = 0.94
      scaling:   z[t] = r[t] / sqrt(sigma2[t])             for t >= 20
    So sigma2[t] uses r[0..t-1] only. The initial value is assigned to the FIRST SCALED session (t = 20), not
    to the last burn-in session; the other reading would give sigma2[20] = lam*init + (1-lam)*r[19]^2 and
    count r[19] twice.

    Uses only returns of sessions passed in (excluded sessions neither update nor are scaled). z[t] depends
    only on r[0..t-1] for the scale, which the look-ahead test checks by truncation.
    """
    r = np.asarray(r, dtype=float)
    z = np.full(len(r), np.nan)
    if len(r) <= burn:
        return z
    s2 = float(np.mean(r[:burn] ** 2))
    for t in range(burn, len(r)):
        z[t] = r[t] / math.sqrt(s2)
        s2 = lam * s2 + (1 - lam) * r[t] ** 2
    return z


def hill(x: np.ndarray, k: int) -> float:
    """Hill tail index on the upper tail of x: [ mean(ln x_(i), i<=k) - ln x_(k+1) ]^-1 (section 7.1)."""
    x = np.sort(np.asarray(x, dtype=float)[np.isfinite(x)])[::-1]
    if k < 1 or len(x) <= k:
        raise InsufficientSample(f"Hill needs more than k={k} observations, got {len(x)}")
    if x[k] <= 0:
        raise ValueError("Hill threshold X_(k+1) must be positive")
    return float(1.0 / np.mean(np.log(x[:k]) - np.log(x[k])))


def _hill_rows_k(X: np.ndarray, kvec: np.ndarray) -> np.ndarray:
    """Hill index per row with a per-row k; NaN entries are ignored (sorted to the end)."""
    if (kvec < 1).any():
        raise InsufficientSample("a bootstrap replicate has Hill k < 1 (too few finite vol-scaled values)")
    S = -np.sort(np.where(np.isnan(X), np.inf, -X), axis=1)     # descending; NaN rows sorted LAST (as -inf)
    S = np.where(np.isfinite(S), S, np.nan)
    r = np.arange(S.shape[0])
    thr = S[r, kvec]
    if not np.all(thr > 0):
        raise ValueError("Hill threshold X_(k+1) must be positive in every replicate")
    logs = np.log(np.where(np.arange(S.shape[1])[None, :] < kvec[:, None], S, 1.0))
    sums = logs.sum(axis=1)
    return 1.0 / (sums / kvec - np.log(thr))


def wpc_on(on: np.ndarray, rth: np.ndarray) -> float:
    """Weighted price contribution of the overnight: sum(sign(CC)*ON) / sum(|CC|), sign(0) = 0."""
    cc = on + rth
    den = np.sum(np.abs(cc))
    return float(np.sum(np.sign(cc) * on) / den) if den > 0 else float("nan")


def vs_on(v_on: np.ndarray, v_rth: np.ndarray) -> float:
    """Overnight share of contract volume, pooled ratio of sums (not a mean of daily ratios)."""
    tot = np.sum(v_on) + np.sum(v_rth)
    return float(np.sum(v_on) / tot) if tot > 0 else float("nan")


def extreme_mask(on: np.ndarray, rth: np.ndarray, frac: float = EXTREME_FRAC) -> np.ndarray:
    """Top ceil(frac*n) sessions by |CC|; ties broken by earlier position (deterministic)."""
    n = len(on)
    k = int(math.ceil(frac * n))
    order = np.lexsort((np.arange(n), -np.abs(on + rth)))
    m = np.zeros(n, dtype=bool)
    m[order[:k]] = True
    return m


def point_stats(on, rth, z_on, z_rth, v_on, v_rth, v1m, which: tuple[str, ...] = TESTS) -> dict[str, float]:
    """theta-hat for the requested tests (default: all five) on one sample."""
    on, rth = np.asarray(on, float), np.asarray(rth, float)
    v1m = np.asarray(v1m, bool)
    out: dict[str, float] = {}
    if "V1" in which:
        out["V1"] = math.log(np.mean(rth[v1m] ** 2) / RTH_HOURS) - math.log(np.mean(on[v1m] ** 2) / ON_HOURS)
    if "T1" in which or "T2" in which:
        zo, zr = np.asarray(z_on, float), np.asarray(z_rth, float)
        fin = np.isfinite(zo) & np.isfinite(zr)
        k = int(math.floor(HILL_FRAC * fin.sum()))
        out["T1"] = hill(-zo[fin], k) - hill(-zr[fin], k)
        out["T2"] = hill(zo[fin], k) - hill(zr[fin], k)
    if "P1" in which:
        out["P1"] = 100.0 * (wpc_on(on, rth) - vs_on(np.asarray(v_on, float), np.asarray(v_rth, float)))
    if "L1" in which:
        ext = extreme_mask(on, rth)
        D = np.abs(on) > np.abs(rth)
        out["L1"] = 100.0 * (D[ext].mean() - D[~ext].mean())
    return {k: v for k, v in out.items() if k in which}


# ---------------------------------------------------------------- bootstrap and inference (section 7)
def stationary_indices(n: int, mean_block: float, B: int, rng: np.random.Generator) -> np.ndarray:
    """Politis-Romano stationary bootstrap: B x n index matrix, geometric blocks with the given mean,
    wrapping around the end of the series."""
    p = 1.0 / mean_block
    idx = np.empty((B, n), dtype=np.int64)
    new = rng.random((B, n)) < p
    starts = rng.integers(0, n, size=(B, n))
    idx[:, 0] = starts[:, 0]
    for t in range(1, n):
        idx[:, t] = np.where(new[:, t], starts[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def week_block_indices(week_id: np.ndarray, mean_weeks: float, B: int, rng: np.random.Generator) -> np.ndarray:
    """Stationary bootstrap over calendar weeks (O2, section 8): resample whole weeks in blocks, expand to
    sessions, truncate to the original number of sessions."""
    weeks = np.unique(week_id)
    members = [np.flatnonzero(week_id == w) for w in weeks]
    n, W = len(week_id), len(weeks)
    out = np.empty((B, n), dtype=np.int64)
    wid = stationary_indices(W, mean_weeks, B, rng)
    for b in range(B):
        seq: list[int] = []
        j = 0
        while len(seq) < n:
            seq.extend(members[wid[b, j % W]].tolist())
            j += 1
        out[b] = seq[:n]
    return out


def centered_p(theta: float, boot: np.ndarray, theta0: float = 0.0, side: int = 0) -> float:
    """Centered bootstrap p-value. side=0 two-sided; side=+1/-1 one-sided in that direction.
    p = (1 + #{|theta*-theta| >= |theta-theta0|}) / (B+1) for the two-sided case."""
    if not np.all(np.isfinite(boot)) or not np.isfinite(theta):
        raise ValueError("non-finite bootstrap replicate or estimate: a NaN would silently count as 'not more "
                         "extreme' and bias p downward (defect found in synthetic testing)")
    d = boot - theta
    obs = theta - theta0
    if side == 0:
        hits = np.sum(np.abs(d) >= abs(obs))
    elif side > 0:
        hits = np.sum(d >= obs)
    else:
        hits = np.sum(d <= obs)
    return float((1 + hits) / (len(boot) + 1))


def holm(pvals: Mapping[str, float], alpha: float = ALPHA_FWER) -> tuple[dict[str, float], dict[str, bool]]:
    """Holm step-down. Returns (adjusted p, rejected). Adjusted p_(i) = max_{j<=i} min(1, (m-j+1) p_(j))."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    adj: dict[str, float] = {}
    rej: dict[str, bool] = {}
    running, stop = 0.0, False
    for i, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[name] = running
        if not stop and p <= alpha / (m - i):
            rej[name] = True
        else:
            stop = True
            rej[name] = False
    return adj, rej


def holm_with_placeholder(p_observed: Mapping[str, float], alpha: float = ALPHA_FWER
                          ) -> tuple[dict[str, float], dict[str, bool], dict[str, float]]:
    """Holm over the five-slot family with each descriptive-only test's slot set to the administrative
    placeholder HOLM_PLACEHOLDER_P (decision U8, approved 2026-11-12). The observed V1 p-value is ignored here;
    it is not an input. Returns (adjusted p, rejected, the p-values actually entered into Holm)."""
    if set(p_observed) != set(TESTS):
        raise ValueError(f"Holm family must be exactly {TESTS}")
    p_family = {t: (HOLM_PLACEHOLDER_P if t in DESCRIPTIVE_ONLY else float(p_observed[t])) for t in TESTS}
    adj, rej = holm(p_family, alpha)
    return adj, rej, p_family


def bh_q(pvals: Mapping[str, float]) -> dict[str, float]:
    """Benjamini-Hochberg q-values (reported for information only)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    q = [0.0] * m
    running = 1.0
    for i in range(m - 1, -1, -1):
        running = min(running, items[i][1] * m / (i + 1))
        q[i] = running
    return {items[i][0]: q[i] for i in range(m)}


def percentile_ci(boot: np.ndarray, level: float) -> tuple[float, float]:
    if not np.all(np.isfinite(boot)):
        raise ValueError("non-finite bootstrap replicate")
    a = (1 - level) / 2
    return float(np.quantile(boot, a)), float(np.quantile(boot, 1 - a))


def bootstrap_family(on, rth, z_on, z_rth, v_on, v_rth, v1m, idx: np.ndarray,
                     which: tuple[str, ...] = TESTS) -> dict[str, np.ndarray]:
    """Recompute all five statistics in every replicate (rows of idx). z values are resampled, not re-scaled
    (section 7: the EWMA is not re-run inside replicates)."""
    on, rth = np.asarray(on, float), np.asarray(rth, float)
    zo, zr = np.asarray(z_on, float), np.asarray(z_rth, float)
    vo, vr = np.asarray(v_on, float), np.asarray(v_rth, float)
    v1m = np.asarray(v1m, bool)
    ON, RT = on[idx], rth[idx]
    M = v1m[idx]
    rth_ph = np.sum(np.where(M, RT ** 2, 0), axis=1) / M.sum(axis=1) / RTH_HOURS
    on_ph = np.sum(np.where(M, ON ** 2, 0), axis=1) / M.sum(axis=1) / ON_HOURS
    V1 = np.log(rth_ph) - np.log(on_ph)
    out: dict[str, np.ndarray] = {}
    out["V1"] = V1
    if "T1" in which or "T2" in which:
        out.update(_boot_tails(zo, zr, idx))
    CC = ON + RT
    if "P1" in which:
        out["P1"] = _boot_p1(ON, CC, vo[idx], vr[idx])
    if "L1" in which:
        out["L1"] = _boot_l1(ON, RT, CC)
    return {k: v for k, v in out.items() if k in which}


def _boot_tails(zo: np.ndarray, zr: np.ndarray, idx: np.ndarray) -> dict[str, np.ndarray]:
    okz = np.isfinite(zo) & np.isfinite(zr)
    OK = okz[idx]                                   # burn-in rows are excluded from T1/T2 in every replicate
    kvec = np.floor(HILL_FRAC * OK.sum(axis=1)).astype(np.int64)
    ZO = np.where(OK, zo[idx], np.nan)
    ZR = np.where(OK, zr[idx], np.nan)
    T1 = _hill_rows_k(-ZO, kvec) - _hill_rows_k(-ZR, kvec)
    T2 = _hill_rows_k(ZO, kvec) - _hill_rows_k(ZR, kvec)
    return {"T1": T1, "T2": T2}


def _boot_p1(ON: np.ndarray, CC: np.ndarray, VO: np.ndarray, VR: np.ndarray) -> np.ndarray:
    wpc = np.sum(np.sign(CC) * ON, axis=1) / np.sum(np.abs(CC), axis=1)
    vs = VO.sum(axis=1) / (VO.sum(axis=1) + VR.sum(axis=1))
    return 100.0 * (wpc - vs)


def _boot_l1(ON: np.ndarray, RT: np.ndarray, CC: np.ndarray) -> np.ndarray:
    n = ON.shape[1]
    kx = int(math.ceil(EXTREME_FRAC * n))
    absc = np.abs(CC)
    # rank by |CC| desc, ties by earlier position in the replicate (deterministic)
    order = np.lexsort((np.broadcast_to(np.arange(n), absc.shape), -absc), axis=1)
    ext = np.zeros_like(absc, dtype=bool)
    np.put_along_axis(ext, order[:, :kx], True, axis=1)
    D = np.abs(ON) > np.abs(RT)
    return 100.0 * ((D & ext).sum(axis=1) / kx - (D & ~ext).sum(axis=1) / (n - kx))


def effect_sizes(name: str, on, rth, v_on, v_rth, v1m, theta: float, z_on=None, z_rth=None) -> dict[str, float]:
    """Natural-unit effect sizes reported with every test (section 7)."""
    on, rth, v1m = np.asarray(on, float), np.asarray(rth, float), np.asarray(v1m, bool)
    if name == "V1":
        return {"variance_ratio_per_hour_rth_to_on": math.exp(theta),
                "rth_variance_per_hour": float(np.mean(rth[v1m] ** 2) / RTH_HOURS),
                "on_variance_per_hour": float(np.mean(on[v1m] ** 2) / ON_HOURS)}
    if name in ("T1", "T2"):
        zo, zr = np.asarray(z_on, float), np.asarray(z_rth, float)
        fin = np.isfinite(zo) & np.isfinite(zr)
        k = int(math.floor(HILL_FRAC * fin.sum()))
        sgn = -1.0 if name == "T1" else 1.0
        return {"alpha_on": hill(sgn * zo[fin], k), "alpha_rth": hill(sgn * zr[fin], k),
                "delta_alpha": theta, "hill_k": k}
    if name == "P1":
        return {"wpc_on": wpc_on(on, rth), "vs_on": vs_on(np.asarray(v_on, float), np.asarray(v_rth, float)),
                "delta_pp": theta, "sessions_with_cc_zero": int(np.sum((on + rth) == 0))}
    if name == "L1":
        ext = extreme_mask(on, rth)
        D = np.abs(on) > np.abs(rth)
        return {"p_on_dominant_extreme_pct": 100 * float(D[ext].mean()),
                "p_on_dominant_other_pct": 100 * float(D[~ext].mean()), "delta_pp": theta,
                "n_extreme": int(ext.sum())}
    raise KeyError(name)


def classify(theta: float, p_adj: float, direction: int, alpha: float = ALPHA_FWER) -> str:
    """Development classification (section 7)."""
    if p_adj > alpha:
        return "not established"
    if direction == 0 or np.sign(theta) == direction:
        return "established"
    return "contradicted"


@dataclass
class Inputs:
    on: np.ndarray
    rth: np.ndarray
    z_on: np.ndarray
    z_rth: np.ndarray
    v_on: np.ndarray
    v_rth: np.ndarray
    v1m: np.ndarray
    dates: pd.DatetimeIndex


def inputs_from_sample(s: pd.DataFrame) -> Inputs:
    on, rth = s["ON"].to_numpy(float), s["RTH"].to_numpy(float)
    return Inputs(on, rth, ewma_scale(on), ewma_scale(rth), s["V_ON"].to_numpy(float),
                  s["V_RTH"].to_numpy(float), v1_mask(s), pd.DatetimeIndex(s.index))


def require(n: int, minimum: int, what: str) -> None:
    if n < minimum:
        raise InsufficientSample(f"{what}: {n} < pre-registered minimum {minimum}. Analysis refused.")


def run_family(x: Inputs, B: int = B_DEFAULT, mean_block: float = BLOCK_DEV, seed: int = SEED_DEV,
               min_sessions: int = MIN_DEV_SESSIONS, min_v1: int = MIN_V1, min_k: int = MIN_HILL_K) -> dict:
    """The development family: point estimates, bootstrap, centered p, Holm at 1%, intervals, effect sizes,
    classification."""
    n = len(x.on)
    if 1.0 / (B + 1) > ALPHA_FWER / M_TESTS:
        raise ValueError(f"B={B} cannot produce p <= {ALPHA_FWER / M_TESTS} (Holm's first threshold): the smallest "
                         f"attainable p is 1/(B+1). Need B >= {math.ceil(M_TESTS / ALPHA_FWER) - 1}.")
    require(n, min_sessions, "analysis sample")
    require(int(x.v1m.sum()), min_v1, "V1 sub-sample")
    k = int(math.floor(HILL_FRAC * int(np.isfinite(x.z_on).sum())))
    require(k, min_k, "Hill k")
    theta = point_stats(x.on, x.rth, x.z_on, x.z_rth, x.v_on, x.v_rth, x.v1m)
    idx = stationary_indices(n, mean_block, B, np.random.default_rng(seed))
    boot = bootstrap_family(x.on, x.rth, x.z_on, x.z_rth, x.v_on, x.v_rth, x.v1m, idx)
    p = {t: centered_p(theta[t], boot[t]) for t in TESTS}
    p_adj, rej, p_family = holm_with_placeholder(p)
    q = bh_q(p_family)
    out: dict[str, Any] = {"n_sessions": n, "n_v1": int(x.v1m.sum()), "B": B, "mean_block": mean_block,
                           "seed": seed, "tests": {},
                           "holm_family": {"m": M_TESTS, "alpha_fwer": ALPHA_FWER,
                                           "descriptive_only_slots_fixed_at_p_1": list(DESCRIPTIVE_ONLY),
                                           "placeholder_note": HOLM_PLACEHOLDER_NOTE}}
    for t in TESTS:
        eff = effect_sizes(t, x.on, x.rth, x.v_on, x.v_rth, x.v1m, theta[t], x.z_on, x.z_rth)
        if t in DESCRIPTIVE_ONLY:
            out["tests"][t] = {
                "theta": theta[t], "direction_expected": DIRECTION[t], "classification": V1_ROLE, "effect": eff,
                "p_two_sided_descriptive_only": p[t],
                "ci99_descriptive_only": percentile_ci(boot[t], 0.99),
                "ci998_descriptive_only": percentile_ci(boot[t], 0.998),
                "calibration_note": V1_CALIBRATION_NOTE,
            }
            continue
        out["tests"][t] = {
            "theta": theta[t], "p_two_sided": p[t], "p_holm": p_adj[t], "holm_reject": rej[t],
            "q_bh_information_only": q[t],
            "ci99": percentile_ci(boot[t], 0.99), "ci998_bonferroni": percentile_ci(boot[t], 0.998),
            "direction_expected": DIRECTION[t],
            "classification": classify(theta[t], p_adj[t], DIRECTION[t]),
            "effect": eff,
        }
    # Protocol v4.2 (decision U9, approved 2026-11-12): V1 does not determine whether the pipeline continues.
    # Its sign is REPORTED only; a non-positive estimate is a result, not a fault. Halts remain only for data-
    # integrity and computation failures (pins, frozen counts, minimum sizes, non-finite replicates, B guard).
    out["v1_point_estimate_positive_reported_only"] = bool(theta["V1"] > 0)
    out["calibration_disclosures"] = dict(CALIBRATION_DISCLOSURES)
    out["tests"]["P1"]["calibration_note"] = P1_CALIBRATION_NOTE
    assert_v1_descriptive_only(out)
    return out


def assert_v1_descriptive_only(family: Mapping[str, Any]) -> None:
    """Decision U7 guard: a family result must carry no inferential V1 field."""
    v1 = family["tests"]["V1"]
    bad = [k for k in V1_INFERENTIAL_KEYS if k in v1]
    if bad or v1.get("classification") != V1_ROLE:
        raise AssertionError(f"V1 must be descriptive only (decision U7); found inferential fields {bad} "
                             f"or classification {v1.get('classification')!r}")


def stability(x: Inputs, family: dict, B: int = B_DEFAULT, mean_block: float = BLOCK_DEV,
              seed: int = SEED_DEV, regimes: Mapping[str, tuple[str, str]] = REGIMES,
              min_regime: int = MIN_REGIME, min_k: int = MIN_HILL_K) -> dict:
    """Per-regime re-estimation for each established claim (section 7). Heterogeneity is descriptive.

    For T1/T2 a regime whose Hill k (5% of its finite vol-scaled values) is below the pre-registered minimum
    is REFUSED, not computed; the claim's stability is then reported as not assessable (stable = None).
    Decision U2 (2026-11-12): accepted as "not assessable"; the minimum is not lowered and the regimes are not
    redefined. With the frozen regimes, 2020-2022 are expected to give k of about 10-11, below 20."""
    res: dict[str, Any] = {}
    est = [t for t in TESTS if family["tests"][t]["classification"] == "established"]
    for t in est:
        main_sign = np.sign(family["tests"][t]["theta"])
        per: dict[str, Any] = {}
        refused = []
        for j, (rname, (a, b)) in enumerate(regimes.items()):
            m = np.asarray((x.dates >= pd.Timestamp(a)) & (x.dates <= pd.Timestamp(b)))
            nreg = int(m.sum())
            require(nreg, min_regime, f"regime {rname}")
            sub = Inputs(x.on[m], x.rth[m], x.z_on[m], x.z_rth[m], x.v_on[m], x.v_rth[m], x.v1m[m], x.dates[m])
            if t in ("T1", "T2"):
                k = int(math.floor(HILL_FRAC * int((np.isfinite(sub.z_on) & np.isfinite(sub.z_rth)).sum())))
                if k < min_k:
                    per[rname] = {"n": nreg, "refused": f"Hill k={k} < pre-registered minimum {min_k}"}
                    refused.append(rname)
                    continue
            th = point_stats(sub.on, sub.rth, sub.z_on, sub.z_rth, sub.v_on, sub.v_rth, sub.v1m, (t,))[t]
            idx = stationary_indices(nreg, mean_block, B, np.random.default_rng(seed + j + 1))
            bt = bootstrap_family(sub.on, sub.rth, sub.z_on, sub.z_rth, sub.v_on, sub.v_rth, sub.v1m, idx, (t,))[t]
            per[rname] = {"n": nreg, "theta": th, "p_two_sided": centered_p(th, bt),
                          "same_sign": bool(np.sign(th) == main_sign)}
        if refused:
            res[t] = {"regimes": per, "stable": None,
                      "not_assessable": f"regime(s) {refused} below the Hill-k minimum; see open issue U2"}
            continue
        same = sum(v["same_sign"] for v in per.values())
        opposite_sig = any((not v["same_sign"]) and v["p_two_sided"] < 0.05 for v in per.values())
        res[t] = {"regimes": per, "same_sign_count": same, "stable": same >= 3 and not opposite_sig}
    return res


# ---------------------------------------------------------------- the official verdict (section 7, D2-a)
OFFICIAL_VERDICT = "INCONCLUSIVE"


def official_verdict(dev_classification: Mapping[str, str], dev_stability: Mapping[str, bool | None]) -> dict:
    """Official verdict text. Takes DEVELOPMENT inputs only: there is no parameter through which O2, or any
    holdout statistic, can reach it (decision D2-a = O1). Always INCONCLUSIVE."""
    labels = {}
    for t in TESTS:
        if t in DESCRIPTIVE_ONLY:           # decision U7: fixed label; V1's inputs are never read
            labels[t] = V1_VERDICT_LABEL
            continue
        c = dev_classification[t]
        if c == "established" and dev_stability.get(t, False):
            labels[t] = ("INCONCLUSIVE - consistent with the literature in development; "
                         "no unexposed evaluation data")
        elif c == "established" and dev_stability.get(t, False) is None:
            # Label approved by Ethan 2026-11-12 (decision U2: accept "not assessable"; minimums not lowered)
            labels[t] = ("INCONCLUSIVE - established in development; regime stability not assessable "
                         "(tail sample below the pre-registered minimum); no unexposed evaluation data")
        elif c == "contradicted":
            labels[t] = ("INCONCLUSIVE - development evidence contradicts the literature direction; "
                         "no unexposed evaluation data")
        else:
            labels[t] = "INCONCLUSIVE - not established in development"
    return {"official_verdict_phase": OFFICIAL_VERDICT, "official_verdict_per_claim": labels,
            "basis": "Decision D2-a (O1): no eligible holdout session is unexposed, so no confirmatory "
                     "evaluation exists. Development labels describe previously used data.",
            "calibration_disclosures": dict(CALIBRATION_DISCLOSURES)}


def render_verdict(v: Mapping[str, Any]) -> str:
    lines = [f"OFFICIAL VERDICT: {v['official_verdict_phase']}", v["basis"]]
    lines += [f"  {t}: {lbl}" for t, lbl in v["official_verdict_per_claim"].items()]
    lines += ["Calibration disclosures (protocol v4.2 section 7.2):"]
    lines += [f"  {k}: {txt}" for k, txt in v.get("calibration_disclosures", {}).items()]
    return "\n".join(lines)


# ---------------------------------------------------------------- O2 secondary (section 8)
def o2_secondary(o2: Inputs, matched_dev: Inputs, dev_family: dict, B: int = B_DEFAULT,
                 mean_weeks: float = BLOCK_HO_WEEKS, seed: int = SEED_HO) -> dict:
    """Descriptive comparison of the restricted O2 population with weekday-matched development sessions.
    Cannot change any verdict: nothing here is passed to official_verdict."""
    require(len(o2.on), MIN_O2_SESSIONS, "O2 sessions")
    require(int(o2.v1m.sum()), MIN_O2_V1, "O2 V1 sub-sample")
    if set(o2.dates.dayofweek) - {0, 3, 4} or set(matched_dev.dates.dayofweek) - {0, 3, 4}:
        raise ValueError("O2 and its matched development population must be Mondays, Thursdays and Fridays only")
    th_o2 = point_stats(o2.on, o2.rth, o2.z_on, o2.z_rth, o2.v_on, o2.v_rth, o2.v1m)
    th_dev = point_stats(matched_dev.on, matched_dev.rth, matched_dev.z_on, matched_dev.z_rth,
                         matched_dev.v_on, matched_dev.v_rth, matched_dev.v1m)
    week = np.asarray(o2.dates.isocalendar().year * 100 + o2.dates.isocalendar().week)
    idx = week_block_indices(week, mean_weeks, B, np.random.default_rng(seed))
    boot = bootstrap_family(o2.on, o2.rth, o2.z_on, o2.z_rth, o2.v_on, o2.v_rth, o2.v1m, idx)
    out: dict[str, Any] = {"caption": O2_CAPTION, "n_o2": len(o2.on), "n_matched_development": len(matched_dev.on),
                           "may_change_verdict": False, "descriptive_only": True, "tests": {}}
    for t in TESTS:
        dev_dir = int(np.sign(dev_family["tests"][t]["theta"])) or 1
        entry = {"o2_estimate": th_o2[t], "matched_development_estimate": th_dev[t],
                 "agreement": "same direction" if np.sign(th_o2[t]) == np.sign(th_dev[t]) else "opposite direction"}
        if t in ("V1", "P1"):
            entry["p_one_sided_descriptive"] = centered_p(th_o2[t], boot[t], side=dev_dir)
        if t in DESCRIPTIVE_ONLY:
            entry["calibration_note"] = V1_CALIBRATION_NOTE
        out["tests"][t] = entry
    return out


# ---------------------------------------------------------------- descriptives (section 6.2)
def describe(r: np.ndarray) -> dict[str, float]:
    r = np.asarray(r, float)
    r = r[np.isfinite(r)]
    if len(r) < 20:                     # too few to describe; reported as such rather than computed
        return {"n": len(r), "too_few_to_describe": True}
    m, sd = float(np.mean(r)), float(np.std(r, ddof=1))
    c = r - m
    q = np.quantile(r, [0.01, 0.05, 0.95, 0.99])
    var1, var5 = float(-q[0]), float(-q[1])
    return {"n": len(r), "mean": m, "median": float(np.median(r)), "sd": sd,
            "skewness": float(np.mean(c ** 3) / np.std(r) ** 3),
            "excess_kurtosis": float(np.mean(c ** 4) / np.std(r) ** 4 - 3),
            "p01": float(q[0]), "p05": float(q[1]), "p95": float(q[2]), "p99": float(q[3]),
            "var_1pct": var1, "var_5pct": var5,
            "es_1pct": float(-np.mean(r[r <= q[0]])), "es_5pct": float(-np.mean(r[r <= q[1]]))}


def descriptives(x: Inputs, s: pd.DataFrame) -> dict:
    """Distribution statistics per session type (descriptive only, D5): no tests, no annualisation."""
    long_m = s["long_overnight"].to_numpy()
    pre = x.dates < LIMIT_REGIME_END
    flags = int(np.sum(pre & (np.abs(x.on) >= LIMIT_FLAG_PRE))) + int(np.sum(~pre & (np.abs(x.on) >= LIMIT_FLAG_POST)))
    return {
        "ON_raw": describe(x.on), "RTH_raw": describe(x.rth),
        "ON_scaled": describe(x.z_on), "RTH_scaled": describe(x.z_rth),
        "overnight_variance_share": float(np.sum(x.on ** 2) / np.sum(x.on ** 2 + x.rth ** 2)),
        "ON_raw_weekday_only": describe(x.on[~long_m]), "ON_raw_long_overnight": describe(x.on[long_m]),
        "price_limit_flag_count": flags,
    }


def realized_variance(bars: pd.DataFrame, sample: pd.DataFrame) -> pd.DataFrame:
    """5-minute realized variance per session (section 4.11).

    rv_rth: 78 five-minute intervals 09:30-16:00 on d. rv_globex: 186 intervals 18:00 (calendar day before d)
    -> 09:30 on d. rv_post: ONE squared return from 16:00 on d_prev to 18:00 the evening before d.
    Grid price at time t = close of the last bar that ENDED at or before t (a bar stamped s ends at s+1 min).
    Stale prices are carried (that is what 'last price' means); nothing is imputed.
    """
    close = pd.Series(bars["close"].to_numpy(float),
                      index=pd.DatetimeIndex(bars.index).tz_convert(TZ) + pd.Timedelta(minutes=1))

    def px_at(times: pd.DatetimeIndex) -> np.ndarray:
        pos = close.index.searchsorted(times, side="right") - 1
        out = np.full(len(times), np.nan)
        ok = pos >= 0
        out[ok] = close.to_numpy()[pos[ok]]
        return out

    rows = []
    for d, prev in zip(sample.index, sample["prev"]):
        d = pd.Timestamp(d).tz_localize(TZ)
        prev = pd.Timestamp(prev).tz_localize(TZ)
        g_rth = pd.date_range(d + pd.Timedelta(hours=9, minutes=30), d + pd.Timedelta(hours=16), freq="5min")
        g_glx = pd.date_range(d - pd.Timedelta(days=1) + pd.Timedelta(hours=18),
                              d + pd.Timedelta(hours=9, minutes=30), freq="5min")
        r_rth = np.diff(np.log(px_at(g_rth)))
        r_glx = np.diff(np.log(px_at(g_glx)))
        p16, p18 = px_at(pd.DatetimeIndex([prev + pd.Timedelta(hours=16), g_glx[0]]))
        rows.append({"session": d.tz_localize(None), "rv_rth": float(np.sum(r_rth ** 2)),
                     "rv_globex": float(np.sum(r_glx ** 2)), "rv_post": float(np.log(p18 / p16) ** 2),
                     "n_rth_intervals": len(r_rth), "n_globex_intervals": len(r_glx)})
    return pd.DataFrame(rows).set_index("session")


TERCILE_WINDOW, TERCILE_MIN_HISTORY = 20, 60     # U5 specification


def vol_tercile_membership(rv_rth: np.ndarray, window: int = TERCILE_WINDOW,
                           min_history: int = TERCILE_MIN_HISTORY) -> np.ndarray:
    """Volatility group of each session (U5 specification). Returns 1, 2, 3 (low/mid/high) or 0 (unassigned).

      T[d]  = mean(RV_RTH[d-window .. d-1])            trailing mean of the PREVIOUS `window` sessions' RTH
                                                       realized variance (never includes session d)
      c1[d], c2[d] = 1/3 and 2/3 quantiles (numpy 'linear') of {T[j] : j < d, T[j] defined}  - expanding,
                                                       so the cut-offs use only sessions before d
      group[d] = 1 if T[d] <= c1[d];  2 if c1[d] < T[d] <= c2[d];  3 if T[d] > c2[d]
      unassigned (0) while T[d] is undefined (first `window` sessions) or fewer than `min_history` earlier
      T values exist (so the first window + min_history sessions are unassigned).
    Membership of session d therefore depends only on RV_RTH of sessions strictly before d: never on session d's
    ON, RTH or RV, nor on any later session. A test checks this by changing session d and everything after it.
    """
    rv = np.asarray(rv_rth, float)
    n = len(rv)
    trail = pd.Series(rv).shift(1).rolling(window).mean().to_numpy()
    grp = np.zeros(n, dtype=int)
    hist: list[float] = []
    for d in range(n):
        if np.isfinite(trail[d]) and len(hist) >= min_history:
            c1, c2 = np.quantile(np.asarray(hist), [1 / 3, 2 / 3])
            grp[d] = 1 if trail[d] <= c1 else 2 if trail[d] <= c2 else 3
        if np.isfinite(trail[d]):
            hist.append(float(trail[d]))
    return grp


def vol_tercile_split(x: Inputs, rv_rth: np.ndarray) -> dict:
    """Descriptive distribution statistics of ON and RTH within each causal volatility group (U5)."""
    grp = vol_tercile_membership(rv_rth)
    out: dict[str, Any] = {"unassigned_sessions": int((grp == 0).sum())}
    for g in (1, 2, 3):
        m = grp == g
        out[f"group_{g}"] = {"n": int(m.sum()), "ON_raw": describe(x.on[m]), "RTH_raw": describe(x.rth[m])}
    return out


def hourly_variance_profile(bars: pd.DataFrame, sessions: Iterable[pd.Timestamp]) -> dict[int, float]:
    """Mean of SQUARED 5-minute log returns by ET hour (volatility only; no mean returns, section 6.2).

    Only bars of the given analysis sessions are used, and only 5-minute steps inside one session. (Defect
    found in synthetic testing: an earlier version used every bar in the file, which would have let 2019 and
    the roll-night jumps that E4 removes into the profile.)"""
    et = pd.DatetimeIndex(bars.index).tz_convert(TZ)
    sess = pd.DatetimeIndex((et + pd.Timedelta(hours=SESSION_SHIFT_H)).date)
    keep = np.asarray(sess.isin(pd.DatetimeIndex(list(sessions))))
    c = pd.Series(bars["close"].to_numpy(float)[keep], index=et[keep])
    s_of = pd.Series(np.asarray(sess[keep]), index=et[keep])
    five = c.resample("5min").last().dropna()
    t5 = pd.DatetimeIndex(five.index)
    s5 = s_of.resample("5min").last().reindex(t5).to_numpy()
    r2 = np.diff(np.log(five.to_numpy(float))) ** 2
    same = np.asarray((t5[1:] - t5[:-1]) == pd.Timedelta(minutes=5)) & (s5[1:] == s5[:-1])
    hours = np.asarray(t5[1:].hour)
    prof = pd.Series(r2[same]).groupby(hours[same]).mean()
    return {int(str(h)): float(v) for h, v in prof.items()}


# ---------------------------------------------------------------- forbidden-quantity guard (section 6.3)
FORBIDDEN_TOKENS = frozenset({
    "corr", "correlation", "cov", "covariance", "regress", "regression", "beta", "slope", "rsquared",
    "sharpe", "profit", "profits", "pnl", "trade", "trades", "signal", "signals", "entry", "exit", "position",
    "positions", "strategy", "predict", "prediction", "predictive", "forecast", "lead", "leads", "lag",
    "lags", "lagged", "gap", "gaps",
})
FORBIDDEN_PHRASES = ("hourly_mean", "hour_mean", "window_mean", "subsession_mean", "sub_session_mean",
                     "cumulative_return", "cum_ret", "half_hour", "first_30", "last_30", "var_cc", "conditional_on_on",
                     "given_on", "after_gap", "p&l", "mean_return_by_hour", "r_squared", "r2_score",
                     "oos_r2", "predictive_r2")
_TOKEN_SPLIT = re.compile(r"[^a-z0-9&]+")


def forbidden_reason(key: str) -> str | None:
    """Why a result key is forbidden (section 6.3), or None. Whole-word tokens, so 'flag' is not 'lag'."""
    k = key.lower()
    for ph in FORBIDDEN_PHRASES:
        if ph in k:
            return ph
    hit = set(_TOKEN_SPLIT.split(k)) & FORBIDDEN_TOKENS
    return sorted(hit)[0] if hit else None


def assert_no_forbidden(obj: Any, path: str = "") -> None:
    """Raise if any dictionary key anywhere in obj names a forbidden quantity."""
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            ks = str(k)
            why = forbidden_reason(ks)
            if why:
                raise ForbiddenQuantityError(f"forbidden quantity in results: {path}/{ks} ({why})")
            assert_no_forbidden(v, f"{path}/{ks}")
    elif isinstance(obj, list | tuple):
        for i, v in enumerate(obj):
            assert_no_forbidden(v, f"{path}[{i}]")
