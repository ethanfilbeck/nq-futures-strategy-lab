"""S1: statistical arbitrage between MES and M2K (docs/PREREG_STATARB_S1.md). Run once.

    py run_statarb_s1.py                # Stage A, training period only
    py run_statarb_s1.py --holdout      # Stage A on the holdout; refuses until the training result exists

Stage A tests whether the log ratio mean-reverts at all. It has no parameters, so there is nothing to tune.
Stage B (the trading rule) is only written if Stage A passes; see the pre-registration.

Dickey-Fuller and the variance ratio are implemented here with numpy and the standard tabulated critical
values, so the computation is auditable and adds no dependency.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from nq_bot.data import load_csv, times

NAME = "statarb_s1_stageA"
TRAIN_END = "2025-06-30 23:59"
HOLDOUT_START, HOLDOUT_END = "2025-07-01", "2026-10-31 23:59"
DF_CRIT_5PCT = -2.86        # Dickey-Fuller tau_mu, constant without trend, 5%
VR_HORIZON, VR_MAX = 20, 0.85
HALFLIFE_MAX = 30


def daily_closes(csv: str) -> pd.Series:
    """The close of each day's 15:59 ET bar, indexed by date."""
    bars = load_csv(csv)
    t = times(bars)
    sel = bars[(t.hour == 15) & (t.minute == 59)]
    s = pd.Series(sel["close"].to_numpy(), index=pd.DatetimeIndex(sel.index).date)
    return s[~s.index.duplicated(keep="first")]


def ols_t(y: np.ndarray, X: np.ndarray, col: int) -> float:
    """t-statistic of coefficient `col` in an OLS of y on X (X includes its own constant)."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = len(y) - X.shape[1]
    s2 = float(resid @ resid) / dof
    cov = s2 * np.linalg.inv(X.T @ X)
    return float(beta[col] / np.sqrt(cov[col, col]))


def adf(s: np.ndarray, lags: int = 1) -> float:
    """Augmented Dickey-Fuller t-statistic: constant, no trend, `lags` lagged differences."""
    ds = np.diff(s)
    n = len(ds) - lags
    y = ds[lags:]
    cols = [np.ones(n), s[lags:-1]] + [ds[lags - i - 1: -i - 1] for i in range(lags)]
    return ols_t(y, np.column_stack(cols), 1)


def variance_ratio(s: np.ndarray, q: int) -> float:
    """Var(q-step change) / (q x Var(1-step change)). 1 = random walk, <1 = mean reverting."""
    d1 = np.diff(s)
    dq = s[q:] - s[:-q]
    return float(dq.var(ddof=1) / (q * d1.var(ddof=1)))


def half_life(s: np.ndarray) -> float:
    """Trading days for a deviation to decay by half, from an AR(1) fit. inf if not mean reverting."""
    X = np.column_stack([np.ones(len(s) - 1), s[:-1]])
    beta, *_ = np.linalg.lstsq(X, s[1:], rcond=None)
    b = float(beta[1])
    return float(-np.log(2) / np.log(b)) if 0 < b < 1 else float("inf")


def stage_a(spread: np.ndarray, label: str) -> dict:
    t_adf, vr, hl = adf(spread), variance_ratio(spread, VR_HORIZON), half_life(spread)
    print(f"\n--- Stage A, {label} (n={len(spread)} trading days) ---")
    print(f"  A1  ADF t           = {t_adf:7.3f}   (threshold < {DF_CRIT_5PCT})")
    print(f"  A2  VR({VR_HORIZON})            = {vr:7.3f}   (threshold < {VR_MAX})")
    print(f"  A3  half-life       = {hl:7.1f} days (threshold <= {HALFLIFE_MAX})")
    print(f"      spread mean {spread.mean():.4f}, sd {spread.std(ddof=1):.4f}, "
          f"range {spread.min():.4f} to {spread.max():.4f}")
    return {"n": len(spread), "adf_t": t_adf, f"vr_{VR_HORIZON}": vr, "half_life_days": hl,
            "mean": float(spread.mean()), "sd": float(spread.std(ddof=1))}


def main(holdout: bool = False) -> None:
    out_json = Path("runs") / f"{NAME}{'_holdout' if holdout else ''}.json"
    train_json = Path("runs") / f"{NAME}.json"
    if out_json.exists():
        raise SystemExit(f"{out_json} already exists. S1 is pre-registered to run once.")
    if holdout and not train_json.exists():
        raise SystemExit("Refusing to examine the holdout: the training result must be written and "
                         "committed first (docs/PREREG_STATARB_S1.md section 5).")

    mes, m2k = daily_closes("data/mes_2019_2026.csv"), daily_closes("data/m2k_2019_2026.csv")
    days = sorted(set(mes.index) & set(m2k.index))
    s = pd.Series(np.log(mes[days].to_numpy()) - np.log(m2k[days].to_numpy()),
                  index=pd.DatetimeIndex(days))
    period = ((s.index >= HOLDOUT_START) & (s.index <= HOLDOUT_END)) if holdout else (s.index <= TRAIN_END)
    spread = s[period].to_numpy()
    label = "HOLDOUT 2025-07 to 2026-10" if holdout else "TRAINING 2019-05 to 2025-06"
    res = stage_a(spread, label)

    if holdout:
        # A4 is agreement in direction only: the holdout is far too short for a powered ADF
        res["A4_same_direction"] = bool(res["adf_t"] < 0 and res[f"vr_{VR_HORIZON}"] < 1.0)
        print(f"  A4  same direction  = {res['A4_same_direction']}  (ADF t < 0 and VR < 1.0)")
    else:
        checks = {"A1 ADF rejects a random walk": bool(res["adf_t"] < DF_CRIT_5PCT),
                  f"A2 VR({VR_HORIZON}) < {VR_MAX}": bool(res[f"vr_{VR_HORIZON}"] < VR_MAX),
                  f"A3 half-life <= {HALFLIFE_MAX} days": bool(res["half_life_days"] <= HALFLIFE_MAX)}
        res["checks"] = checks
        for k, v in checks.items():
            print(f"  {'PASS' if v else 'FAIL'}  {k}")
        res["verdict"] = ("TRAINING CHECKS PASS - examine the holdout next" if all(checks.values())
                          else "S1 FAILS AT STAGE A - the spread does not mean-revert; "
                               "no trading rule is written and statistical arbitrage is closed")
        print(f"\n{res['verdict']}")
    Path("runs").mkdir(exist_ok=True)
    out_json.write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main(holdout="--holdout" in sys.argv)
