"""Overnight vs regular-session descriptive study: runner (protocol v4).

    py run_sessions_study.py dev        # development analysis, once
    py run_sessions_study.py holdout    # O2 secondary + labelled sensitivities, once, after dev is committed

HISTORICAL ACADEMIC RESEARCH ONLY. Produces descriptive statistics; no trading rule, signal or strategy.
The official verdict is INCONCLUSIVE (decision D2-a = O1) and is written BEFORE any holdout statistic is
computed. This script refuses to run until the protocol is frozen (its hash recorded in PREREG_HASH.txt)
and until every pinned data file matches its recorded hash.

Data-integrity gate: nq_bot.integrity is enforced before anything is computed.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nq_bot import sessions as S
from nq_bot.integrity import DataIntegrityError, Gate

# ---------------------------------------------------------------- pinned inputs (protocol section 3)
PINNED = {
    "data/mnq_train.csv": "a2d8d017cceb0d551e213ba6cdc48cd91dd5d91183ab82cdc69fc506bcb55fe1",
    "data/mnq_holdout.csv": "8b00498f4d8427e821ec50d4654e991f07e9cdac6c87aa56dee27b995532be8f",
    "runs/rollmap_MNQ.json": "e1beaeeda0c6ab73bf03cfb75b1345fe3748c354e9f817b197385c6bef5a9005",
    "nq_bot/family3.py": "b97fdfd3e9ef925223556a9b3f745802b865fe0c1edc929ca7afa74685600331",
    "docs/HOLDOUT_EXPOSURE_SESSIONS.csv": "a462425b30c59eb1b832bf8650588b874b5b5d94cec78fd454c27a0165b88683",
}
DEGRADED_UTC_DATES = ("2020-02-27", "2020-02-28", "2020-05-05", "2020-06-30", "2020-07-01", "2021-12-05",
                      "2022-01-02", "2022-11-06", "2024-09-18", "2025-09-17", "2025-09-24", "2025-11-28",
                      "2026-01-31", "2026-03-15", "2026-03-16", "2026-03-21", "2026-04-10", "2026-05-24")


@dataclass
class Config:
    root: Path = Path(".")
    train: str = "data/mnq_train.csv"
    holdout: str = "data/mnq_holdout.csv"
    rollmap: str = "runs/rollmap_MNQ.json"
    exposure_csv: str = "docs/HOLDOUT_EXPOSURE_SESSIONS.csv"
    prereg: str = "docs/PREREG_SESSIONS.md"
    prereg_hashes: str = "docs/PREREG_HASH.txt"
    out_dev: str = "runs/sessions_dev.json"
    out_holdout: str = "runs/sessions_holdout.json"
    verdict_txt: str = "runs/sessions_official_verdict.txt"
    dev_results_doc: str = "docs/RESULTS_SESSIONS_DEV.md"
    pinned: dict[str, str] = field(default_factory=lambda: dict(PINNED))
    fomc_days: tuple[str, ...] = ()
    dev_window: tuple[str, str] = ("2020-01-02", "2025-06-30")
    holdout_window: tuple[str, str] = ("2025-07-01", "2026-10-30")
    expected_dev: dict[str, int] = field(default_factory=lambda: {"eligible_E1_E5": 1308, "primary_E1_E6": 1230})
    expected_holdout: dict[str, int] = field(default_factory=lambda: {"eligible_E1_E5": 318, "primary_E1_E6": 297})
    expected_o2: int = 185
    B: int = S.B_DEFAULT
    mins: dict[str, int] = field(default_factory=lambda: {
        "sessions": S.MIN_DEV_SESSIONS, "v1": S.MIN_V1, "k": S.MIN_HILL_K, "regime": S.MIN_REGIME})
    regimes: dict[str, tuple[str, str]] = field(default_factory=lambda: dict(S.REGIMES))
    is_committed: Callable[[Path, str], bool] | None = None

    def p(self, rel: str) -> Path:
        return self.root / rel


def default_fomc() -> tuple[str, ...]:
    from nq_bot import family3 as f3
    return tuple(f3.FOMC_DAYS) + tuple(f3.HOLDOUT_FOMC_DAYS)


def git_is_committed(root: Path, rel: str) -> bool:
    """True if the file is tracked and has no uncommitted changes."""
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=root,  # noqa: S603, S607
                             capture_output=True).returncode == 0
    clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=root,  # noqa: S603, S607
                           capture_output=True).returncode == 0
    return tracked and clean


# ---------------------------------------------------------------- guards
class Refused(SystemExit):
    pass


def require_frozen_protocol(cfg: Config) -> None:
    pre, hashes = cfg.p(cfg.prereg), cfg.p(cfg.prereg_hashes)
    if not pre.exists() or not hashes.exists():
        raise Refused("REFUSED: the protocol is not frozen (docs/PREREG_SESSIONS.md and its recorded hash are "
                      "required). Sign-off and hashing come before any real-data run.")
    if S.sha256_file(pre) not in hashes.read_text(encoding="utf-8"):
        raise Refused("REFUSED: docs/PREREG_SESSIONS.md does not match any hash in PREREG_HASH.txt; the "
                      "protocol was edited after freezing.")


def verify_pins(cfg: Config, keys: list[str]) -> None:
    S.verify_hashes({cfg.p(k): cfg.pinned[k] for k in keys})


def load(cfg: Config, files: list[str], gate: Gate) -> tuple[pd.DataFrame, pd.DataFrame]:
    bars = S.read_bars([cfg.p(f) for f in files])
    gate.bars(bars, "+".join(files))
    gate.documented("bars", f"raw bars concatenated from {files}, de-duplicated by timestamp only")
    gate.enforce(cfg.p(f"runs/sessions_integrity_{'_'.join(Path(f).stem for f in files)}.json"))
    S.check_bars(bars)
    return bars, S.session_table(bars)


def calendar(cfg: Config) -> S.Calendar:
    rm = json.loads(cfg.p(cfg.rollmap).read_text(encoding="utf-8"))
    fomc = cfg.fomc_days or default_fomc()
    return S.Calendar(S.rollmap_switches(rm), tuple(pd.Timestamp(x) for x in fomc))


def check_counts(gate: Gate, label: str, counts: dict[str, int], expected: dict[str, int]) -> None:
    for k, v in expected.items():
        gate.reconcile_count(f"{label} {k} (frozen in protocol section 5.2)", v, counts[k])


def degraded_sessions(sample: pd.DataFrame) -> set[pd.Timestamp]:
    """S4 mapping: drop session d if [16:00 ET on d_prev, 16:00 ET on d] overlaps a degraded UTC date."""
    out = set()
    for d, prev in zip(sample.index, sample["prev"]):
        a = (pd.Timestamp(prev) + pd.Timedelta(hours=16)).tz_localize(S.TZ).tz_convert("UTC")
        b = (pd.Timestamp(d) + pd.Timedelta(hours=16)).tz_localize(S.TZ).tz_convert("UTC")
        for u in DEGRADED_UTC_DATES:
            lo = pd.Timestamp(u, tz="UTC")
            if a < lo + pd.Timedelta(days=1) and b > lo:
                out.add(pd.Timestamp(d))
    return out


def point_only(x: S.Inputs) -> dict[str, float]:
    return S.point_stats(x.on, x.rth, x.z_on, x.z_rth, x.v_on, x.v_rth, x.v1m)


def subset(x: S.Inputs, m: np.ndarray) -> S.Inputs:
    return S.Inputs(x.on[m], x.rth[m], x.z_on[m], x.z_rth[m], x.v_on[m], x.v_rth[m], x.v1m[m], x.dates[m])


def sensitivities(cfg: Config, sample_all: pd.DataFrame, primary: pd.DataFrame, x: S.Inputs) -> dict[str, Any]:
    """Section 11. Point estimates only; labelled; none can change a verdict. S7 (GARCH) is WITHDRAWN
    (decision U4, 2026-11-12): no new dependency or optimiser is introduced."""
    d = x.dates
    out: dict[str, Any] = {"note": "Sensitivity analyses; reported only; cannot change any verdict."}
    m = ~((d >= pd.Timestamp("2020-01-02")) & (d <= pd.Timestamp("2020-10-09")))
    out["S2_without_5pct_limit_regime"] = point_only(subset(x, m))
    lock = pd.DatetimeIndex(S.LIMIT_LOCK_SESSIONS)
    out["S3_without_limit_lock_sessions"] = point_only(subset(x, ~d.isin(lock)))
    nxt = pd.DatetimeIndex([primary.index[primary.index > s][0] for s in lock if (primary.index > s).any()])
    out["S3b_without_limit_lock_and_following"] = point_only(subset(x, ~d.isin(lock.union(nxt))))
    out["S4_without_degraded_days"] = point_only(subset(x, ~d.isin(pd.DatetimeIndex(list(degraded_sessions(primary))))))
    with_e6 = S.analysis_set(sample_all, drop_e6=False)
    out["S5_fomc_pairs_included"] = point_only(S.inputs_from_sample(with_e6))
    wk = (~primary["long_overnight"]).to_numpy() & primary["weekday"].isin([1, 2, 3, 4]).to_numpy()
    out["S6_tue_fri_non_long_only"] = point_only(subset(x, wk))
    s8 = {}
    fin = np.isfinite(x.z_on) & np.isfinite(x.z_rth)
    for frac in (0.025, 0.10):
        k = int(np.floor(frac * fin.sum()))
        s8[f"k_{frac}"] = {"T1": S.hill(-x.z_on[fin], k) - S.hill(-x.z_rth[fin], k),
                           "T2": S.hill(x.z_on[fin], k) - S.hill(x.z_rth[fin], k), "k": k}
    out["S8_hill_k"] = s8
    s9 = {}
    for blk in (10, 40):
        idx = S.stationary_indices(len(x.on), blk, cfg.B, np.random.default_rng(S.SEED_DEV + blk))
        bt = S.bootstrap_family(x.on, x.rth, x.z_on, x.z_rth, x.v_on, x.v_rth, x.v1m, idx)
        th = point_only(x)
        s9[f"block_{blk}"] = {t: S.centered_p(th[t], bt[t]) for t in S.TESTS}
    s9["note_V1"] = S.V1_CALIBRATION_NOTE
    out["S9_block_length_p_two_sided"] = s9
    out["S7_garch_t_scaling"] = "WITHDRAWN (decision U4, 2026-11-12); not computed"
    return out


# ---------------------------------------------------------------- development run
def run_dev(cfg: Config) -> dict[str, Any]:
    out_p = cfg.p(cfg.out_dev)
    if out_p.exists():
        raise Refused(f"REFUSED: {cfg.out_dev} exists. The development analysis runs once.")
    require_frozen_protocol(cfg)
    verify_pins(cfg, [cfg.train, cfg.rollmap, "nq_bot/family3.py"])
    gate = Gate("sessions_dev")
    bars, sess = load(cfg, [cfg.train], gate)
    sample_all = S.build_sample(sess, calendar(cfg), *cfg.dev_window)
    counts = S.exclusion_counts(sample_all)
    g2 = Gate("sessions_dev_counts")
    check_counts(g2, "development", counts, cfg.expected_dev)
    g2.enforce(cfg.p("runs/sessions_integrity_dev_counts.json"))
    primary = S.analysis_set(sample_all)
    x = S.inputs_from_sample(primary)
    fam = S.run_family(x, B=cfg.B, min_sessions=cfg.mins["sessions"], min_v1=cfg.mins["v1"], min_k=cfg.mins["k"])
    result: dict[str, Any] = {"protocol": "v4.2", "mode": "development", "counts": counts, "family": fam}
    # Protocol v4.2 (U9): no V1-based halt. V1 is reported descriptively whatever its sign. The run stops only on
    # the integrity and computation failures raised above and inside run_family (pins, counts, minimum sizes,
    # non-finite replicates, B guard, forbidden quantities).
    stab = S.stability(x, fam, B=cfg.B, regimes=cfg.regimes, min_regime=cfg.mins["regime"], min_k=cfg.mins["k"])
    verdict = S.official_verdict({t: fam["tests"][t]["classification"] for t in S.TESTS},
                                 {t: v["stable"] for t, v in stab.items()})
    result["stability"] = stab
    result["official"] = verdict
    rv = S.realized_variance(bars, primary)
    result["descriptives"] = S.descriptives(x, primary)
    result["descriptives"]["realized_variance_share_overnight"] = float(
        (rv["rv_globex"] + rv["rv_post"]).sum() / (rv["rv_globex"] + rv["rv_post"] + rv["rv_rth"]).sum())
    result["descriptives"]["hourly_variance_profile"] = S.hourly_variance_profile(bars, primary.index)
    result["descriptives"]["volatility_terciles"] = S.vol_tercile_split(x, rv["rv_rth"].to_numpy())
    result["sensitivities"] = sensitivities(cfg, sample_all, primary, x)
    S.assert_no_forbidden(result)
    _write(out_p, result)
    cfg.p(cfg.verdict_txt).write_text(S.render_verdict(verdict) + "\n", encoding="utf-8")
    return result


# ---------------------------------------------------------------- holdout run (O2 secondary + H-series)
def run_holdout(cfg: Config) -> dict[str, Any]:
    out_p, dev_p = cfg.p(cfg.out_holdout), cfg.p(cfg.out_dev)
    if out_p.exists():
        raise Refused(f"REFUSED: {cfg.out_holdout} exists. The holdout is opened once.")
    if not dev_p.exists():
        raise Refused("REFUSED: development results must exist first.")
    committed = cfg.is_committed or git_is_committed
    if not committed(cfg.root, cfg.dev_results_doc):
        raise Refused(f"REFUSED: {cfg.dev_results_doc} must be committed before the holdout is opened.")
    require_frozen_protocol(cfg)
    verify_pins(cfg, [cfg.train, cfg.holdout, cfg.rollmap, "nq_bot/family3.py", cfg.exposure_csv])
    dev = json.loads(dev_p.read_text(encoding="utf-8"))
    if "official" not in dev:
        raise Refused("REFUSED: the development results are incomplete (no official verdict); nothing to describe.")
    # 1. The official verdict is fixed from development results BEFORE any holdout statistic exists.
    fam = dev["family"]
    verdict = S.official_verdict({t: fam["tests"][t]["classification"] for t in S.TESTS},
                                 {t: v["stable"] for t, v in dev["stability"].items()})
    verdict_text = S.render_verdict(verdict)
    cfg.p(cfg.verdict_txt).write_text(verdict_text + "\n", encoding="utf-8")
    # 2. Data: both files (the holdout's first overnight starts at the development file's last close).
    gate = Gate("sessions_holdout")
    bars, sess = load(cfg, [cfg.train, cfg.holdout], gate)
    cal = calendar(cfg)
    ho_all = S.build_sample(sess, cal, *cfg.holdout_window)
    counts = S.exclusion_counts(ho_all)
    g2 = Gate("sessions_holdout_counts")
    check_counts(g2, "holdout", counts, cfg.expected_holdout)
    # 3. O2 membership from the hashed exposure inventory; must match the sessions exactly.
    exp = pd.read_csv(cfg.p(cfg.exposure_csv), keep_default_na=False)
    exp["session"] = pd.to_datetime(exp["session"])
    g2.reconcile_count("exposure CSV rows = holdout sessions with RTH", len(ho_all), len(exp))
    ho_dates = set(pd.DatetimeIndex(ho_all.index).date)
    g2.no_dates_lost("data sessions present in exposure CSV", ho_dates, set(exp["session"].dt.date))
    g2.no_dates_lost("exposure CSV sessions present in data", set(exp["session"].dt.date), ho_dates)
    o2_dates = exp[(exp["excluded_by"] == "") & (exp["category"] == "B_replication_pool")
                   & exp["weekday"].isin(["Mon", "Thu", "Fri"])]["session"]
    g2.reconcile_count("O2 population (protocol section 8)", cfg.expected_o2, len(o2_dates))
    g2.enforce(cfg.p("runs/sessions_integrity_holdout_counts.json"))
    eligible = S.analysis_set(ho_all, drop_e6=False)               # 318: EWMA runs over these, in time order
    xe = S.inputs_from_sample(eligible)
    o2_mask = eligible.index.isin(o2_dates)
    x_o2 = subset(xe, o2_mask)
    # matched development population: development primary sessions on Mon/Thu/Fri
    dev_all = S.build_sample(sess, cal, *cfg.dev_window)
    dev_primary = S.analysis_set(dev_all)
    xd = S.inputs_from_sample(dev_primary)
    x_dev_m = subset(xd, dev_primary["weekday"].isin([0, 3, 4]).to_numpy())
    o2 = S.o2_secondary(x_o2, x_dev_m, fam, B=cfg.B)
    # 4. Labelled H-series sensitivities: point estimates only.
    cells = exp.set_index("session").reindex(eligible.index)
    h: dict[str, Any] = {"note": "Labelled sensitivity analyses; descriptive; cannot change any verdict."}
    a_rows = cells["category"].eq("A_H8").to_numpy()
    p_rows = cells["category"].eq("P_placebo").to_numpy()
    h["H-A_o2_plus_A"] = point_only(subset(xe, o2_mask | a_rows))
    h["H-P_o2_plus_P"] = point_only(subset(xe, o2_mask | p_rows))
    h["H-ALL_all_318"] = point_only(xe)
    h["H-E6_all_e6_removed"] = point_only(subset(xe, ~eligible["is_fomc_pair"].to_numpy()))
    result: dict[str, Any] = {"protocol": "v4.2", "mode": "holdout-secondary", "counts": counts, "official": verdict,
              "o2_secondary": o2, "h_series": h}
    # 5. The verdict must be exactly what was written before O2 was computed.
    if S.render_verdict(result["official"]) != verdict_text:
        raise DataIntegrityError("official verdict changed after O2 was computed")
    S.assert_no_forbidden(result)
    _write(out_p, result)
    return result


def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
                    encoding="utf-8")


def main(argv: list[str]) -> None:
    if len(argv) != 2 or argv[1] not in ("dev", "holdout"):
        raise SystemExit(__doc__)
    cfg = Config()
    if argv[1] == "dev":
        run_dev(cfg)
    else:
        run_holdout(cfg)


if __name__ == "__main__":
    main(sys.argv)
