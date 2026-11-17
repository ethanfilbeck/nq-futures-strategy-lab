"""Synthetic-data tests for the overnight vs regular-session study (protocol v4, section 9).

Every dataset here is GENERATED (tests/sessions_synth.py). No real market data is opened. Tests marked
`slow` run the Monte Carlo size/coverage checks; they run by default and can be skipped with -m "not slow".
Findings that the protocol asks to be DOCUMENTED (price-limit distortions, Hill on Gaussian tails) are written
to the JSON file named by $SESSIONS_SYNTH_REPORT (default: a temp file) as well as asserted where a direction
is certain.
"""
from __future__ import annotations

import ast
import inspect
import json
import math
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import sessions_synth as sy

import run_sessions_study as R
from nq_bot import sessions as S
from nq_bot.integrity import DataIntegrityError

ROOT = Path(__file__).resolve().parent.parent
REAL_DATA_DIR = (ROOT / "data").resolve()


@pytest.fixture(autouse=True)
def _no_real_data(monkeypatch):
    """U6 isolation: any attempt by these tests (or the code under test) to open a file under the project's
    real data/ folder fails the test. Synthetic projects live in temporary folders."""
    import builtins
    import io
    real_open = builtins.open

    def guarded(file, *a, **k):
        if isinstance(file, str | os.PathLike):
            try:
                if REAL_DATA_DIR in Path(file).resolve().parents:
                    raise AssertionError(f"synthetic tests must not open real data: {file}")
            except (OSError, ValueError):
                pass
        return real_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", guarded)
    monkeypatch.setattr(io, "open", guarded)
REPORT_PATH = Path(os.environ.get("SESSIONS_SYNTH_REPORT", Path(tempfile.gettempdir()) / "sessions_synth_report.json"))
REPORT: dict = {}


def record(key: str, value) -> None:
    REPORT[key] = value
    REPORT_PATH.write_text(json.dumps(REPORT, indent=2, default=float))


def build(spec: sy.Spec, switches=(), fomc=(), start=None, end=None):
    bars, truth = sy.make(spec)
    st = S.session_table(bars)
    cal = S.Calendar(tuple(pd.Timestamp(x, tz="UTC") for x in switches), tuple(pd.Timestamp(x) for x in fomc))
    smp = S.build_sample(st, cal, start or spec.start, end or spec.end)
    return bars, truth, st, smp


def arrays_inputs(on, rth, z_on=None, z_rth=None, v_on=None, v_rth=None, v1=None, start="2020-01-02"):
    n = len(on)
    return S.Inputs(np.asarray(on, float), np.asarray(rth, float),
                    np.asarray(S.ewma_scale(on) if z_on is None else z_on, float),
                    np.asarray(S.ewma_scale(rth) if z_rth is None else z_rth, float),
                    np.full(n, 10.0) if v_on is None else np.asarray(v_on, float),
                    np.full(n, 30.0) if v_rth is None else np.asarray(v_rth, float),
                    np.ones(n, bool) if v1 is None else np.asarray(v1, bool),
                    pd.bdate_range(start, periods=n))


# =================================================================== A. session boundaries and the data path
def test_exact_recovery_of_returns_and_volumes_across_dst():
    spec = sy.Spec("2024-02-26", "2024-11-15", sy.gaussian(0.006), sy.gaussian(0.012), seed=3)
    _, truth, st, smp = build(spec)
    m = smp.join(truth, rsuffix="_true")
    assert np.nanmax(np.abs(m.ON - m.ON_true)) < 1e-12
    assert np.nanmax(np.abs(m.RTH - m.RTH_true)) < 1e-12
    # every normal session: 990 overnight minutes at vol_on, 390 RTH minutes at vol_rth
    assert set(smp.V_ON) == {990 * 10.0} and set(smp.V_RTH) == {390 * 30.0}
    assert st["offset_ok"].all()
    # both DST changes of 2024 are inside the window
    assert (st.index == pd.Timestamp("2024-03-11")).any() and (st.index == pd.Timestamp("2024-11-04")).any()
    assert (st.loc[["2024-03-11", "2024-11-04"], "n_bars"] == 1380).all()


def test_session_spanning_a_dst_change_is_a_data_error():
    idx = pd.DatetimeIndex(["2024-03-10 01:30", "2024-03-10 03:30"]).tz_localize(S.TZ).tz_convert("UTC")
    bars = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}, index=idx)
    with pytest.raises(DataIntegrityError, match="DST"):
        S.session_table(bars)


def test_half_day_triggers_E1_and_the_next_session_E2():
    spec = sy.Spec("2024-11-18", "2024-12-06", sy.gaussian(0.005), sy.gaussian(0.01),
                   holidays=["2024-11-28"], half_days=["2024-11-29"], seed=4)
    _, _, _, smp = build(spec)
    assert smp.loc["2024-11-29", "excluded_by"] == "E1"
    assert smp.loc["2024-12-02", "excluded_by"] == "E2"
    assert smp.loc["2024-11-29":"2024-12-02"].shape[0] == 2
    assert smp.loc["2024-11-27", "excluded_by"] == ""
    assert bool(smp.loc["2024-11-29", "long_overnight"])        # Wednesday -> Friday spans the holiday


def test_globex_only_session_triggers_E5_and_is_never_an_observation():
    spec = sy.Spec("2026-03-23", "2026-04-17", sy.gaussian(0.005), sy.gaussian(0.01),
                   globex_only=["2026-04-03"], seed=5)
    _, _, st, smp = build(spec)
    assert st.loc["2026-04-03", "n_rth"] == 0 and st.loc["2026-04-03", "n_bars"] == 915
    assert pd.Timestamp("2026-04-03") not in smp.index            # no RTH: never an observation
    assert smp.loc["2026-04-06", "excluded_by"] == "E5"
    assert smp.loc["2026-04-06", "prev"] == pd.Timestamp("2026-04-02")


def test_missing_boundary_windows_trigger_E3_without_imputation():
    spec = sy.Spec("2024-05-06", "2024-05-24", sy.gaussian(0.005), sy.gaussian(0.01), seed=6)
    bars, _ = sy.make(spec)
    et = bars.index.tz_convert(S.TZ)
    drop_open = (et.date == pd.Timestamp("2024-05-14").date()) & (et.hour == 9) & (et.minute >= 30) & (et.minute < 35)
    drop_close = (et.date == pd.Timestamp("2024-05-20").date()) & (et.hour == 15) & (et.minute >= 55)
    st = S.session_table(bars[~(drop_open | drop_close)])
    smp = S.build_sample(st, S.Calendar((), ()), spec.start, spec.end)
    assert smp.loc["2024-05-14", "excluded_by"] == "E3"          # O(d) missing
    assert smp.loc["2024-05-20", "excluded_by"] == "E3"          # C(d) missing
    assert smp.loc["2024-05-21", "excluded_by"] == "E3"          # C(d_prev) missing for the next session
    assert np.isnan(smp.loc["2024-05-14", "ON"])                 # never imputed


def test_missing_interior_minutes_are_zero_volume_not_missing_data():
    spec = sy.Spec("2024-05-06", "2024-05-24", sy.gaussian(0.005), sy.gaussian(0.01), seed=7)
    bars, truth = sy.make(spec)
    et = bars.index.tz_convert(S.TZ)
    m = et.hour * 60 + et.minute
    rng = np.random.default_rng(1)
    interior = ((m >= 575) & (m < 955)) | ((m >= 60) & (m < 500))
    drop = interior & (rng.random(len(bars)) < 0.10)
    smp = S.build_sample(S.session_table(bars[~drop]), S.Calendar((), ()), spec.start, spec.end)
    full = S.build_sample(S.session_table(bars), S.Calendar((), ()), spec.start, spec.end)
    assert np.allclose(smp.ON, full.ON) and np.allclose(smp.RTH, full.RTH)     # endpoints intact
    lost = pd.Series(bars["volume"][drop].to_numpy(), index=pd.DatetimeIndex((et[drop] + pd.Timedelta(hours=6)).date))
    lost_rth = lost[(m[drop] >= 570) & (m[drop] < 960)].groupby(level=0).sum()
    diff = (full.V_RTH - smp.V_RTH)
    common = lost_rth.index.intersection(diff.index)                 # the first session has no prev: not a row
    assert len(common) >= 13
    assert np.allclose(diff.reindex(common), lost_rth.reindex(common))   # exactly the dropped volume, no imputation


def test_zero_volume_bar_stops_the_run():
    spec = sy.Spec("2024-05-06", "2024-05-10", sy.gaussian(0.005), sy.gaussian(0.01), seed=8)
    bars, _ = sy.make(spec)
    bars.iloc[500, bars.columns.get_loc("volume")] = 0.0
    with pytest.raises(DataIntegrityError, match="zero-volume"):
        S.check_bars(bars)


def test_overlapping_files_with_a_session_split_across_them(tmp_path):
    """Reproduces the v1 count bug's shape: a file boundary at 00:00 UTC inside a session's overnight, with
    an identical overlapping stretch. Sessions must come out identical to a single-file build."""
    spec = sy.Spec("2025-06-16", "2025-07-18", sy.gaussian(0.005), sy.gaussian(0.01), holidays=["2025-07-04"],
                   half_days=["2025-07-03"], seed=9)
    bars, _ = sy.make(spec)
    cut = pd.Timestamp("2025-07-01 00:00", tz="UTC")
    a = bars[bars.index < cut + pd.Timedelta(hours=2)]               # 2 h overlap
    b = bars[bars.index >= cut - pd.Timedelta(hours=1)]
    pa, pb = sy.write_csv(a, tmp_path / "a.csv"), sy.write_csv(b, tmp_path / "b.csv")
    merged = S.read_bars([pa, pb])
    single = S.read_bars([sy.write_csv(bars, tmp_path / "all.csv")])
    pd.testing.assert_frame_equal(S.session_table(merged), S.session_table(single))
    st = S.session_table(merged)
    assert st.loc["2025-07-01", "n_rth"] == 390                      # v1 lost this session's RTH
    assert int((st.n_rth >= 390).sum()) == int((S.session_table(single).n_rth >= 390).sum())


def test_overlapping_files_that_disagree_are_a_data_error(tmp_path):
    spec = sy.Spec("2025-06-23", "2025-07-03", sy.gaussian(0.005), sy.gaussian(0.01), seed=10)
    bars, _ = sy.make(spec)
    a = bars.iloc[:3000].copy()
    b = bars.iloc[2900:].copy()
    b.iloc[50, b.columns.get_loc("close")] *= 1.001
    with pytest.raises(DataIntegrityError, match="different values"):
        S.read_bars([sy.write_csv(a, tmp_path / "a.csv"), sy.write_csv(b, tmp_path / "b.csv")])


def test_roll_discontinuity_is_excluded_and_cannot_move_any_result():
    common = dict(start="2024-01-02", end="2024-08-30", on_draw=sy.gaussian(0.006), rth_draw=sy.gaussian(0.012), seed=11)
    switch = "2024-03-13 00:00"                                       # 19:00/20:00 ET on Tue 2024-03-12
    _, _, _, clean = build(sy.Spec(**common), switches=[switch])
    _, _, _, jumped = build(sy.Spec(**common, roll_jumps={switch: 1.012}), switches=[switch])
    assert jumped.loc["2024-03-13", "excluded_by"] == "E4"
    assert abs(jumped.loc["2024-03-13", "ON"] - clean.loc["2024-03-13", "ON"] - math.log(1.012)) < 1e-12
    a, b = S.analysis_set(clean), S.analysis_set(jumped)
    assert np.allclose(a.ON, b.ON, atol=1e-12) and np.allclose(a.RTH, b.RTH, atol=1e-12)
    # and without the roll map the jump WOULD contaminate the overnight - the reason E4 exists
    _, _, _, unguarded = build(sy.Spec(**common, roll_jumps={switch: 1.012}))
    assert unguarded.loc["2024-03-13", "excluded_by"] == ""


def test_E6_removes_statement_day_and_preceding_session_symmetrically():
    spec = sy.Spec("2024-01-02", "2024-03-29", sy.gaussian(0.005), sy.gaussian(0.01), seed=12)
    _, _, _, smp = build(spec, fomc=["2024-01-31", "2024-03-20"])
    for d in ("2024-01-30", "2024-01-31", "2024-03-19", "2024-03-20"):
        assert smp.loc[d, "excluded_by"] == "E6"
    assert len(S.analysis_set(smp, drop_e6=False)) == len(S.analysis_set(smp)) + 4   # S5 keeps them


def test_fomc_day_outside_the_loaded_data_marks_nothing():
    """Regression: a development-only run must not flag its LAST session as 'the day before' a statement day
    that lies in the (unloaded) holdout. On the real data that would have turned 1,230 into 1,229."""
    spec = sy.Spec("2024-01-02", "2024-03-29", sy.gaussian(0.005), sy.gaussian(0.01), seed=14)
    _, _, _, smp = build(spec, fomc=["2024-01-31", "2024-06-12"])
    assert smp.loc["2024-03-29", "excluded_by"] == ""
    assert (smp.excluded_by == "E6").sum() == 2


def test_exclusion_rules_apply_in_order_with_overlaps_counted_once():
    spec = sy.Spec("2024-06-03", "2024-07-31", sy.gaussian(0.005), sy.gaussian(0.01),
                   holidays=["2024-07-04"], half_days=["2024-06-19", "2024-07-03"], seed=13)
    _, _, _, smp = build(spec, switches=["2024-06-19 00:00"], fomc=["2024-06-12"])
    c = S.exclusion_counts(smp)
    assert smp.loc["2024-06-19", "excluded_by"] == "E1"               # roll + half day: E1 wins (cf. 2024-06-19)
    assert c["E1"] == 2 and c["E2"] == 2 and c["E4"] == 0 and c["E6"] == 2
    assert c["start"] - sum(c[k] for k in S.RULES) == c["primary_E1_E6"]


# =================================================================== B. statistics
def test_ewma_is_causal():
    r = np.random.default_rng(1).normal(0, 0.01, 400)
    z = S.ewma_scale(r)
    r2 = r.copy()
    r2[300:] *= 50                                                    # change the future only
    z2 = S.ewma_scale(r2)
    assert np.array_equal(z[:300], z2[:300], equal_nan=True)          # nothing before the change moves
    assert z2[300] / r2[300] == pytest.approx(z[300] / r[300])         # z[300]'s SCALE uses only r[<300]
    assert np.isnan(z[: S.EWMA_BURN]).all() and np.isfinite(z[S.EWMA_BURN:]).all()
    assert np.isnan(S.ewma_scale(r[:S.EWMA_BURN])).all()             # nothing to scale after burn-in


def test_hill_recovers_pareto_alpha():
    rng = np.random.default_rng(2)
    for a in (2.0, 3.0, 5.0):
        x = rng.pareto(a, 40_000) + 1.0
        assert abs(S.hill(x, 2000) - a) < 0.15 * a


def test_hill_on_gaussian_tails_is_finite_and_k_dependent_documented():
    z = np.random.default_rng(3).normal(size=20_000)
    vals = {frac: S.hill(z, int(frac * len(z))) for frac in (0.025, 0.05, 0.10)}
    assert all(np.isfinite(v) for v in vals.values())
    assert vals[0.025] > vals[0.05] > vals[0.10]                      # rises as k falls: no true tail index
    record("hill_on_gaussian_tails_by_k", vals)


def test_hill_refuses_too_few_observations():
    with pytest.raises(S.InsufficientSample):
        S.hill(np.arange(5.0), 5)


def test_wpc_identity_volume_share_and_zero_cc_sessions():
    rng = np.random.default_rng(4)
    on, rth = rng.normal(0, 0.006, 500), rng.normal(0, 0.012, 500)
    on[:5], rth[:5] = 0.004, -0.004                                   # CC = 0 sessions
    w = (np.abs(on + rth) / np.abs(on + rth).sum())
    with np.errstate(divide="ignore", invalid="ignore"):
        bw = np.nansum(np.where(on + rth != 0, w * on / (on + rth), 0.0))
    assert abs(S.wpc_on(on, rth) - bw) < 1e-12                        # Barclay-Warner weighted form
    assert S.vs_on(np.full(10, 990.0), np.full(10, 1170.0)) == pytest.approx(990 / 2160)
    eff = S.effect_sizes("P1", on, rth, np.full(500, 9900.0), np.full(500, 11700.0), np.ones(500, bool), 0.0)
    assert eff["sessions_with_cc_zero"] == 5


def test_wpc_known_values():
    on, rth = np.array([0.01, -0.02, 0.0]), np.array([0.0, 0.0, 0.03])
    assert S.wpc_on(on, rth) == pytest.approx((0.01 + 0.02 + 0) / 0.06)
    assert S.wpc_on(np.array([0.01]), np.array([-0.01])) != S.wpc_on(np.array([0.01]), np.array([-0.01]))  # NaN


def test_l1_known_construction():
    n = 200
    on, rth = np.full(n, 0.001), np.full(n, 0.002)                   # ordinary days: RTH dominant
    big = np.arange(10)                                               # 5% extreme days, ON dominant
    on[big], rth[big] = 0.05, 0.001
    th = S.point_stats(on, rth, *([np.random.default_rng(0).normal(size=n)] * 2), np.ones(n), np.ones(n), np.ones(n, bool))
    assert th["L1"] == pytest.approx(100.0)
    assert S.extreme_mask(on, rth).sum() == math.ceil(0.05 * n)


def test_l1_ties_broken_by_earlier_position():
    on = np.zeros(40); rth = np.full(40, 0.01)
    m = S.extreme_mask(on, rth)
    assert m[:2].all() and not m[2:].any()


def test_centered_p_and_intervals_behave():
    rng = np.random.default_rng(5)
    boot = rng.normal(2.0, 1.0, 100_000)
    assert S.centered_p(2.0, boot) == pytest.approx(2 * (1 - 0.97725), abs=0.003)     # |theta|=2 sd
    assert S.centered_p(0.0, boot) == pytest.approx(1.0, abs=1e-4)
    assert S.centered_p(2.0, boot, side=+1) == pytest.approx(1 - 0.97725, abs=0.002)
    lo, hi = S.percentile_ci(boot, 0.99)
    assert lo == pytest.approx(2 - 2.5758, abs=0.03) and hi == pytest.approx(2 + 2.5758, abs=0.03)
    lo8, hi8 = S.percentile_ci(boot, 0.998)
    assert lo8 < lo and hi8 > hi


def test_holm_hand_example_exactly():
    p = {"a": 0.001, "b": 0.004, "c": 0.02, "d": 0.3, "e": 0.5}
    adj, rej = S.holm(p, 0.01)
    assert [round(adj[k], 6) for k in "abcde"] == [0.005, 0.016, 0.06, 0.6, 0.6]
    assert rej == {"a": True, "b": False, "c": False, "d": False, "e": False}


def test_holm_stops_at_first_failure_and_rejects_iff_adjusted_below_alpha():
    rng = np.random.default_rng(6)
    for _ in range(500):
        p = dict(zip("abcde", rng.uniform(0, 0.02, 5)))
        adj, rej = S.holm(p, 0.01)
        assert all(rej[k] == (adj[k] <= 0.01) for k in p)
        ordered = sorted(p, key=p.get)
        flags = [rej[k] for k in ordered]
        assert flags == sorted(flags, reverse=True)                   # rejections form a prefix


def test_bh_q_values_are_monotone_and_bounded():
    q = S.bh_q({"a": 0.01, "b": 0.02, "c": 0.03, "d": 0.5, "e": 0.9})
    assert q["a"] <= q["b"] <= q["c"] <= q["d"] <= q["e"] <= 1


def test_stationary_bootstrap_mean_block_and_reproducibility():
    idx = S.stationary_indices(2000, 20, 50, np.random.default_rng(7))
    assert idx.min() >= 0 and idx.max() < 2000
    breaks = np.mean(idx[:, 1:] != (idx[:, :-1] + 1) % 2000)
    assert abs(1 / breaks - 20) < 2
    assert np.array_equal(idx, S.stationary_indices(2000, 20, 50, np.random.default_rng(7)))


def test_week_block_bootstrap_keeps_whole_weeks():
    d = pd.bdate_range("2025-07-07", periods=120)
    d = d[d.dayofweek.isin([0, 3, 4])]
    wk = np.asarray(d.isocalendar().year * 100 + d.isocalendar().week)
    idx = S.week_block_indices(wk, 4, 30, np.random.default_rng(8))
    assert idx.shape == (30, len(d))
    for row in idx:
        w = wk[row]
        starts = np.r_[np.flatnonzero(np.r_[True, w[1:] != w[:-1]]), len(row)]
        for a, b in zip(starts[:-2], starts[1:-1]):                   # every run except the truncated last
            mem = np.flatnonzero(wk == w[a])
            assert (b - a) % len(mem) == 0                            # whole weeks (possibly the same week twice)
            assert (row[a:b] == np.tile(mem, (b - a) // len(mem))).all()


def _family_inputs(n, ratio, rng, on_tail=None, rth_tail=None):
    on = (rng.standard_t(on_tail, n) / math.sqrt(on_tail / (on_tail - 2)) if on_tail else rng.normal(size=n)) * 0.006
    sd_r = 0.006 * math.sqrt(ratio * S.RTH_HOURS / S.ON_HOURS)
    rth = (rng.standard_t(rth_tail, n) / math.sqrt(rth_tail / (rth_tail - 2)) if rth_tail else rng.normal(size=n)) * sd_r
    return arrays_inputs(on, rth)


def test_run_family_recovers_known_effects_and_reports_everything():
    rng = np.random.default_rng(9)
    x = _family_inputs(3000, 3.0, rng, on_tail=3.0, rth_tail=None)
    fam = S.run_family(x, B=999, min_sessions=1000)
    v1 = fam["tests"]["V1"]
    assert v1["effect"]["variance_ratio_per_hour_rth_to_on"] == pytest.approx(math.exp(v1["theta"]))
    assert v1["classification"] == S.V1_ROLE                            # decision U7: never "established"
    assert v1["ci99_descriptive_only"][0] < math.log(3.0) < v1["ci99_descriptive_only"][1]
    assert not set(S.V1_INFERENTIAL_KEYS) & set(v1)
    assert fam["tests"]["T1"]["theta"] < 0 and fam["tests"]["T1"]["classification"] == "established"
    for t in S.INFERENTIAL_TESTS:
        e = fam["tests"][t]
        assert {"theta", "p_two_sided", "p_holm", "holm_reject", "ci99", "ci998_bonferroni", "effect",
                "classification", "q_bh_information_only"} <= set(e)
        assert e["ci998_bonferroni"][0] <= e["ci99"][0] and e["ci99"][1] <= e["ci998_bonferroni"][1]
    assert fam["v1_point_estimate_positive_reported_only"]
    S.assert_no_forbidden(fam)
    f2 = S.run_family(x, B=999, min_sessions=1000)
    assert all(f2["tests"][t]["p_two_sided"] == fam["tests"][t]["p_two_sided"] for t in S.INFERENTIAL_TESTS)
    assert f2["tests"]["V1"]["p_two_sided_descriptive_only"] == fam["tests"]["V1"]["p_two_sided_descriptive_only"]


def test_contradicted_classification_when_effect_has_the_wrong_sign():
    rng = np.random.default_rng(10)
    x = _family_inputs(3000, 3.0, rng, on_tail=None, rth_tail=3.0)   # RTH fatter: T1 opposite to literature
    fam = S.run_family(x, B=999, min_sessions=1000)
    assert fam["tests"]["T1"]["theta"] > 0
    assert fam["tests"]["T1"]["classification"] in ("contradicted", "not established")
    assert S.classify(0.5, 0.001, -1) == "contradicted" and S.classify(-0.5, 0.001, -1) == "established"
    assert S.classify(0.5, 0.02, -1) == "not established" and S.classify(-0.5, 0.001, 0) == "established"


@pytest.mark.slow
def test_v1_interval_coverage_over_200_seeds():
    hits = 0
    for s in range(200):
        x = _family_inputs(1200, 3.0, np.random.default_rng(1000 + s))
        idx = S.stationary_indices(1200, 20, 499, np.random.default_rng(s))
        bt = S.bootstrap_family(x.on, x.rth, x.z_on, x.z_rth, x.v_on, x.v_rth, x.v1m, idx)["V1"]
        lo, hi = S.percentile_ci(bt, 0.99)
        hits += lo < math.log(3.0) < hi
    record("v1_ci99_coverage_200_seeds", hits / 200)
    assert hits / 200 >= 0.95


@pytest.mark.slow
def test_v1_size_under_the_null_1000_seeds():
    rej05 = rej01 = 0
    for s in range(1000):
        x = _family_inputs(600, 1.0, np.random.default_rng(5000 + s))   # equal per-hour variance: L = 0
        idx = S.stationary_indices(600, 20, 299, np.random.default_rng(s))
        bt = S.bootstrap_family(x.on, x.rth, x.z_on, x.z_rth, x.v_on, x.v_rth, x.v1m, idx)["V1"]
        L = S.point_stats(x.on, x.rth, x.z_on, x.z_rth, x.v_on, x.v_rth, x.v1m)["V1"]
        p = S.centered_p(L, bt)
        rej05 += p <= 0.05
        rej01 += p <= 0.01
    record("v1_null_rejection_rate_1000_seeds", {"alpha_0.05": rej05 / 1000, "alpha_0.01": rej01 / 1000})
    assert rej05 / 1000 <= 0.08 and rej01 / 1000 <= 0.025          # binomial slack around nominal


def test_minimum_sizes_refuse():
    rng = np.random.default_rng(11)
    with pytest.raises(ValueError, match="smallest attainable p"):
        S.run_family(_family_inputs(1100, 2.0, rng), B=99)            # Holm could never reject at B=99
    with pytest.raises(S.InsufficientSample, match="analysis sample"):
        S.run_family(_family_inputs(900, 2.0, rng), B=999)
    x = _family_inputs(1100, 2.0, rng)
    x.v1m[:] = False; x.v1m[:400] = True
    with pytest.raises(S.InsufficientSample, match="V1"):
        S.run_family(x, B=999)
    with pytest.raises(S.InsufficientSample, match="Hill k"):
        S.run_family(_family_inputs(300, 2.0, rng), B=999, min_sessions=100, min_v1=100)
    fam = S.run_family(_family_inputs(1100, 3.0, rng), B=999)
    assert fam["tests"]["V1"]["classification"] == S.V1_ROLE and fam["v1_point_estimate_positive_reported_only"]
    x2 = _family_inputs(1100, 3.0, rng)
    with pytest.raises(S.InsufficientSample, match="regime"):
        S.stability(x2, fam, B=99, regimes={"R1": ("2020-01-01", "2020-03-01")})


# =================================================================== C. distorted distributions (documented)
def _censor(on, rth, cap, mode, overshoot=0.01):
    on2, rth2 = on.copy(), rth.copy()
    hit = np.abs(on) > cap
    excess = on[hit] - np.sign(on[hit]) * cap
    if mode == "deferred":                     # overnight capped at the band, the rest lands in RTH
        on2[hit] = np.sign(on[hit]) * cap
        rth2[hit] = rth[hit] + excess
    elif mode == "overshoot":                  # reopening print overshoots, RTH corrects
        os_ = np.sign(on[hit]) * overshoot
        on2[hit] = on[hit] + os_
        rth2[hit] = rth[hit] - os_
    return on2, rth2, int(hit.sum())


def test_price_limit_censoring_and_reopening_overshoot_effects_are_documented():
    rng = np.random.default_rng(12)
    n = 6000
    on = 0.008 * rng.standard_t(3, n) / math.sqrt(3)
    rth = 0.012 * rng.normal(size=n)
    base = S.point_stats(on, rth, S.ewma_scale(on), S.ewma_scale(rth), np.full(n, 9900.0), np.full(n, 11700.0), np.ones(n, bool))
    out = {"baseline": base}
    for mode in ("deferred", "overshoot"):
        o2, r2, nhit = _censor(on, rth, 0.03, mode)
        st = S.point_stats(o2, r2, S.ewma_scale(o2), S.ewma_scale(r2), np.full(n, 9900.0), np.full(n, 11700.0), np.ones(n, bool))
        out[mode] = {"n_sessions_hit": nhit, **st, "change": {k: st[k] - base[k] for k in base}}
    record("price_limit_distortion_synthetic", out)
    # The one certain direction: deferring the excess into RTH thins ON's tail AND fattens RTH's, so
    # delta-alpha (ON - RTH) rises.
    assert out["deferred"]["change"]["T1"] > 0
    # Overshoot fattens BOTH tails (ON pushed out, RTH corrects by the same amount), so its net effect on
    # delta-alpha has no fixed sign - exactly the protocol's section 5.5 conclusion. Recorded, not asserted.
    assert out["overshoot"]["n_sessions_hit"] == out["deferred"]["n_sessions_hit"] > 0


def test_price_limit_flags_and_S2_S3_masks_fire():
    dates = pd.bdate_range("2020-03-02", "2020-12-31")
    n = len(dates)
    on = np.full(n, 0.001); rth = np.full(n, 0.002)
    on[dates.get_loc(pd.Timestamp("2020-03-16"))] = -0.049           # pre-2020-10-12: >= 4.5% flagged
    on[dates.get_loc(pd.Timestamp("2020-11-04"))] = 0.06             # post: < 6.5% not flagged
    x = S.Inputs(on, rth, on, rth, np.ones(n), np.ones(n), np.ones(n, bool), dates)
    smp = pd.DataFrame({"long_overnight": np.zeros(n, bool)}, index=dates)
    assert S.descriptives(x, smp)["price_limit_flag_count"] == 1


# =================================================================== D. the official verdict and O2
def test_official_verdict_is_inconclusive_for_every_possible_development_outcome():
    import itertools
    for combo in itertools.product(["established", "contradicted", "not established"], repeat=5):
        for stable in (True, False):
            v = S.official_verdict(dict(zip(S.TESTS, combo)), {t: stable for t in S.TESTS})
            assert v["official_verdict_phase"] == "INCONCLUSIVE"
            lbls = v["official_verdict_per_claim"]
            assert all(lbls[t].startswith("INCONCLUSIVE") for t in S.INFERENTIAL_TESTS)
            assert lbls["V1"] == S.V1_VERDICT_LABEL                        # decision U7
            txt = S.render_verdict(v)
            assert "SUPPORTED" not in txt and "REJECTED" not in txt


def test_official_verdict_has_no_path_for_o2():
    params = list(inspect.signature(S.official_verdict).parameters)
    assert params == ["dev_classification", "dev_stability"]
    tree = ast.parse(inspect.getsource(S.official_verdict))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {a.arg for a in ast.walk(tree) if isinstance(a, ast.arg)}
    assert not any("o2" in n.lower() or "holdout" in n.lower() for n in names)


def test_o2_secondary_is_labelled_and_cannot_change_a_verdict():
    rng = np.random.default_rng(13)
    d = pd.bdate_range("2025-07-07", "2026-10-30")
    d = d[d.dayofweek.isin([0, 3, 4])][:185]
    n = len(d)
    x = S.Inputs(rng.normal(0, .006, n), rng.normal(0, .012, n), np.r_[np.full(20, np.nan), rng.normal(size=n - 20)],
                 np.r_[np.full(20, np.nan), rng.normal(size=n - 20)], np.full(n, 9900.0), np.full(n, 11700.0),
                 np.asarray(d.dayofweek.isin([3, 4])), d)
    dm = pd.bdate_range("2021-01-04", "2024-12-31"); dm = dm[dm.dayofweek.isin([0, 3, 4])]
    xm = arrays_inputs(rng.normal(0, .006, len(dm)), rng.normal(0, .012, len(dm)))
    xm = S.Inputs(xm.on, xm.rth, xm.z_on, xm.z_rth, xm.v_on, xm.v_rth, xm.v1m, dm)
    fam = {"tests": {t: {"theta": 1.0} for t in S.TESTS}}
    o2 = S.o2_secondary(x, xm, fam, B=199)
    assert o2["caption"] == S.O2_CAPTION and o2["may_change_verdict"] is False and o2["descriptive_only"]
    S.assert_no_forbidden(o2)
    tue = S.Inputs(*[a for a in (x.on, x.rth, x.z_on, x.z_rth, x.v_on, x.v_rth, x.v1m)], d + pd.Timedelta(days=1))
    with pytest.raises(ValueError, match="Mondays, Thursdays and Fridays"):
        S.o2_secondary(tue, xm, fam, B=99)
    small = S.Inputs(x.on[:90], x.rth[:90], x.z_on[:90], x.z_rth[:90], x.v_on[:90], x.v_rth[:90], x.v1m[:90], d[:90])
    with pytest.raises(S.InsufficientSample, match="O2"):
        S.o2_secondary(small, xm, fam, B=99)


# ---------------------------------------------------------------- full runner on synthetic files
def _project(tmp_path: Path, seed: int = 21, ho_override=None) -> R.Config:
    """A synthetic project tree: data, roll map, exposure CSV, frozen protocol. All generated."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "data").mkdir(); (tmp_path / "runs").mkdir(); (tmp_path / "docs").mkdir(); (tmp_path / "nq_bot").mkdir()
    hol = ["2023-11-23", "2023-12-25", "2024-01-01", "2024-07-04", "2024-11-28", "2024-12-25", "2025-01-01",
           "2025-07-04", "2025-11-27", "2025-12-25"]
    half = ["2023-11-24", "2024-07-03", "2024-11-29", "2024-12-24", "2025-07-03", "2025-11-28", "2025-12-24"]
    spec = sy.Spec("2023-10-02", "2025-12-31", sy.gaussian(0.006), sy.gaussian(0.012), holidays=hol,
                   half_days=half, globex_only=["2024-03-29"], seed=seed)
    bars, _ = sy.make(spec)
    split = pd.Timestamp("2024-11-01 00:00", tz="UTC")
    if ho_override is not None:
        bars = ho_override(bars, split)
    sy.write_csv(bars[bars.index < split], tmp_path / "data/train.csv")
    sy.write_csv(bars[bars.index >= split], tmp_path / "data/holdout.csv")
    switches = ["2024-03-13", "2024-06-12", "2024-09-11", "2024-12-11", "2025-03-12", "2025-06-11", "2025-09-17"]
    (tmp_path / "runs/rollmap.json").write_text(json.dumps(sy.rollmap(switches)))
    (tmp_path / "nq_bot/family3.py").write_text("# synthetic stand-in\n")
    fomc = ("2024-01-31", "2024-05-01", "2024-07-31", "2024-12-18", "2025-03-19", "2025-07-30", "2025-10-29")
    cfg = R.Config(root=tmp_path, train="data/train.csv", holdout="data/holdout.csv", rollmap="runs/rollmap.json",
                   fomc_days=fomc, dev_window=("2023-11-01", "2024-10-31"), holdout_window=("2024-11-01", "2025-12-31"),
                   B=999, mins={"sessions": 150, "v1": 100, "k": 8, "regime": 40},
                   regimes={"R1": ("2023-11-01", "2024-01-31"), "R2": ("2024-02-01", "2024-04-30"),
                            "R3": ("2024-05-01", "2024-07-31"), "R4": ("2024-08-01", "2024-10-31")},
                   is_committed=lambda root, rel: (root / rel).exists())
    # exposure CSV: every holdout session with RTH; Mon/Thu/Fri eligible -> "B only", others P / A
    st = S.session_table(S.read_bars([tmp_path / "data/train.csv", tmp_path / "data/holdout.csv"]))
    cal = S.Calendar(S.rollmap_switches(sy.rollmap(switches)), tuple(pd.Timestamp(x) for x in fomc))
    ho = S.build_sample(st, cal, *cfg.holdout_window)
    rows = []
    for d, r in ho.iterrows():
        ex = r.excluded_by if r.excluded_by in ("E1", "E2", "E3", "E4", "E5") else ""
        cat = "A_H8" if r.is_fomc_pair else "B_replication_pool" if d.dayofweek in (0, 3, 4) else "P_placebo"
        rows.append({"session": d.date().isoformat(), "weekday": d.day_name()[:3], "excluded_by": ex,
                     "category": cat, "tests": "synthetic"})
    pd.DataFrame(rows).to_csv(tmp_path / cfg.exposure_csv, index=False)
    dev = S.build_sample(st, cal, *cfg.dev_window)
    cfg.expected_dev = {k: S.exclusion_counts(dev)[k] for k in ("eligible_E1_E5", "primary_E1_E6")}
    cfg.expected_holdout = {k: S.exclusion_counts(ho)[k] for k in ("eligible_E1_E5", "primary_E1_E6")}
    e = pd.DataFrame(rows)
    cfg.expected_o2 = int(((e.excluded_by == "") & (e.category == "B_replication_pool")).sum())
    cfg.pinned = {k: S.sha256_file(tmp_path / k) for k in
                  ("data/train.csv", "data/holdout.csv", "runs/rollmap.json", "nq_bot/family3.py", cfg.exposure_csv)}
    (tmp_path / cfg.prereg).write_text("synthetic frozen protocol\n")
    (tmp_path / cfg.prereg_hashes).write_text(S.sha256_file(tmp_path / cfg.prereg) + "  docs/PREREG_SESSIONS.md\n")
    return cfg


@pytest.fixture(scope="module")
def synthetic_project(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("proj")
    cfg = _project(tmp)
    dev = R.run_dev(cfg)
    (tmp / cfg.dev_results_doc).write_text("dev results (synthetic)\n")
    return cfg, dev


def test_runner_development_end_to_end_on_synthetic_files(synthetic_project):
    cfg, dev = synthetic_project
    assert dev["official"]["official_verdict_phase"] == "INCONCLUSIVE"
    assert set(dev["family"]["tests"]) == set(S.TESTS)
    assert "sensitivities" in dev and "descriptives" in dev and "stability" in dev
    saved = json.loads((cfg.root / cfg.out_dev).read_text())
    S.assert_no_forbidden(saved)
    assert (cfg.root / cfg.verdict_txt).read_text().startswith("OFFICIAL VERDICT: INCONCLUSIVE")
    with pytest.raises(R.Refused, match="runs once"):
        R.run_dev(cfg)


def _holdout_variant(tmp_path, mutate_csv=None, mutate_prices=False):
    def ho(bars, split):
        if not mutate_prices:
            return bars
        b = bars.copy()
        et = b.index.tz_convert(S.TZ)
        rng = np.random.default_rng(99)
        m = (b.index >= split) & np.isin(et.dayofweek, [0, 3, 4])
        f = np.exp(np.cumsum(rng.normal(0, 3e-4, int(m.sum()))))
        b.loc[m, ["open", "high", "low", "close"]] = b.loc[m, ["open", "high", "low", "close"]].mul(f, axis=0)
        b["high"] = b[["open", "high", "close"]].max(axis=1) * (1 + 1e-7)
        b["low"] = b[["open", "low", "close"]].min(axis=1) * (1 - 1e-7)
        return b
    cfg = _project(tmp_path, ho_override=ho)
    R.run_dev(cfg)
    (tmp_path / cfg.dev_results_doc).write_text("dev\n")
    if mutate_csv:
        p = tmp_path / cfg.exposure_csv
        e = pd.read_csv(p, keep_default_na=False)
        e = mutate_csv(e)
        e.to_csv(p, index=False)
        cfg.pinned[cfg.exposure_csv] = S.sha256_file(p)
    return cfg


def test_o2_cannot_change_the_official_verdict_removed_randomised_altered(tmp_path):
    base = _holdout_variant(tmp_path / "base")
    r0 = R.run_holdout(base)
    v0 = (base.root / base.verdict_txt).read_text()
    assert r0["official"]["official_verdict_phase"] == "INCONCLUSIVE"
    assert r0["o2_secondary"]["caption"] == S.O2_CAPTION
    # (a) O2 prices randomised (different holdout file, different hash, re-pinned)
    rnd = _holdout_variant(tmp_path / "rnd", mutate_prices=True)
    r1 = R.run_holdout(rnd)
    assert (rnd.root / rnd.verdict_txt).read_text() == v0
    assert r1["o2_secondary"]["tests"]["V1"]["o2_estimate"] != r0["o2_secondary"]["tests"]["V1"]["o2_estimate"]
    # (b) O2 removed from the inventory: the run is refused AFTER the verdict was written, which is unchanged
    rem = _holdout_variant(tmp_path / "rem", mutate_csv=lambda e: e.assign(
        category=np.where(e.category == "B_replication_pool", "P_placebo", e.category)))
    with pytest.raises(DataIntegrityError, match="O2 population"):
        R.run_holdout(rem)
    assert (rem.root / rem.verdict_txt).read_text() == v0
    # (c) O2 membership altered (half reassigned) -> refused; verdict unchanged
    def alter(e):
        idx = e.index[e.category == "B_replication_pool"][::2]
        e.loc[idx, "category"] = "P_placebo"
        return e
    alt = _holdout_variant(tmp_path / "alt", mutate_csv=alter)
    with pytest.raises(DataIntegrityError, match="O2 population"):
        R.run_holdout(alt)
    assert (alt.root / alt.verdict_txt).read_text() == v0


def test_holdout_refusals(tmp_path):
    cfg = _project(tmp_path)
    with pytest.raises(R.Refused, match="development results must exist"):
        R.run_holdout(cfg)
    R.run_dev(cfg)
    with pytest.raises(R.Refused, match="committed"):
        R.run_holdout(cfg)
    (tmp_path / cfg.dev_results_doc).write_text("dev\n")
    R.run_holdout(cfg)
    with pytest.raises(R.Refused, match="opened once"):
        R.run_holdout(cfg)


def test_runner_refuses_without_frozen_protocol_or_with_edited_protocol(tmp_path):
    cfg = _project(tmp_path)
    (tmp_path / cfg.prereg).write_text("edited after freezing\n")
    with pytest.raises(R.Refused, match="edited after freezing"):
        R.run_dev(cfg)
    (tmp_path / cfg.prereg).unlink()
    with pytest.raises(R.Refused, match="not frozen"):
        R.run_dev(cfg)


def test_runner_refuses_on_hash_mismatch_and_count_mismatch(tmp_path):
    cfg = _project(tmp_path)
    cfg.pinned["data/train.csv"] = "0" * 64
    with pytest.raises(DataIntegrityError, match="hash mismatch"):
        R.run_dev(cfg)
    cfg2 = _project(tmp_path / "b")
    cfg2.expected_dev = {"eligible_E1_E5": 1308, "primary_E1_E6": 1230}      # the real frozen counts
    with pytest.raises(DataIntegrityError, match="row count"):
        R.run_dev(cfg2)


def test_runner_defaults_pin_the_recorded_hashes():
    c = R.Config()
    assert c.pinned["data/mnq_train.csv"].startswith("a2d8d017")
    assert c.pinned["data/mnq_holdout.csv"].startswith("8b00498f")
    assert c.pinned["runs/rollmap_MNQ.json"].startswith("e1beaeed")
    assert c.pinned["nq_bot/family3.py"].startswith("b97fdfd3")
    assert c.pinned["docs/HOLDOUT_EXPOSURE_SESSIONS.csv"].startswith("a462425b")
    assert c.expected_dev == {"eligible_E1_E5": 1308, "primary_E1_E6": 1230}
    assert c.expected_holdout == {"eligible_E1_E5": 318, "primary_E1_E6": 297} and c.expected_o2 == 185


# =================================================================== E. forbidden quantities cannot enter
@pytest.mark.parametrize("key", ["corr_on_rth", "cov", "ON_RTH_covariance", "var_cc", "regression_beta",
                                 "slope", "hourly_mean_return", "window_mean", "cumulative_return_2am",
                                 "half_hour_return", "first_30_minutes", "sharpe", "net_profit", "pnl", "trades",
                                 "entry_price", "exit", "signal", "position_size", "strategy", "gap_fade",
                                 "rth_given_on_up", "predictive_r2", "r_squared", "oos_r2", "lagged_on", "lead"])
def test_forbidden_guard_catches(key):
    with pytest.raises(S.ForbiddenQuantityError):
        S.assert_no_forbidden({"outer": [{"inner": {key: 1.0}}]})


@pytest.mark.parametrize("key", ["price_limit_flag_count", "overnight_variance_share", "regimes", "holm_reject", "R1", "R2", "R3", "R4",
                                 "p_on_dominant_extreme_pct", "hourly_variance_profile", "rv_globex", "alpha_on"])
def test_forbidden_guard_allows_protocol_quantities(key):
    S.assert_no_forbidden({key: 1.0})


FORBIDDEN_CALLS = {"corrcoef", "cov", "polyfit", "lstsq", "linregress", "OLS", "ols", "pearsonr", "spearmanr", "corr"}


@pytest.mark.parametrize("path", ["nq_bot/sessions.py", "run_sessions_study.py"])
def test_source_never_calls_correlation_or_regression(path):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_CALLS:
            pytest.fail(f"{path}:{node.lineno} uses {node.attr}")
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_CALLS:
            pytest.fail(f"{path}:{node.lineno} uses {node.id}")
        if isinstance(node, ast.FunctionDef):
            assert S.forbidden_reason(node.name) is None, f"{path}: function {node.name}"


def test_hourly_profile_measures_variance_not_mean_returns():
    """A strong positive drift in one hour must NOT appear as a mean; the profile holds mean SQUARES only."""
    idx = pd.date_range("2024-05-07 02:00", "2024-05-07 03:00", freq="1min", inclusive="left", tz=S.TZ).tz_convert("UTC")
    px = 10_000 * np.exp(np.cumsum(np.full(len(idx), 1e-4)))           # monotone drift, zero variance about it
    bars = pd.DataFrame({"open": px, "high": px, "low": px, "close": px, "volume": 1.0}, index=idx)
    prof = S.hourly_variance_profile(bars, [pd.Timestamp("2024-05-07")])
    assert all(v >= 0 for v in prof.values())
    assert prof[2] == pytest.approx((5e-4) ** 2)                      # squared 5-min move, not a signed mean


def test_research_module_is_listed_with_research_modules():
    txt = (ROOT / "tests" / "test_tooling.py").read_text(encoding="utf-8")
    assert '"sessions"' in txt


def test_runner_uses_the_integrity_gate():
    assert "nq_bot.integrity" in (ROOT / "run_sessions_study.py").read_text(encoding="utf-8")


# =================================================================== F. guard branches (coverage follow-up)
@pytest.mark.parametrize("breakage,match", [
    ("naive", "timezone-aware"), ("unsorted", "strictly increasing"), ("nan", "NaN"), ("negative", "non-positive")])
def test_check_bars_rejects_malformed_input(breakage, match):
    spec = sy.Spec("2024-05-06", "2024-05-08", sy.gaussian(0.005), sy.gaussian(0.01), seed=15)
    bars, _ = sy.make(spec)
    if breakage == "naive":
        bars.index = bars.index.tz_localize(None)
    elif breakage == "unsorted":
        bars = bars.iloc[::-1]
    elif breakage == "nan":
        bars.iloc[10, 0] = np.nan
    else:
        bars.iloc[10, 3] = -1.0
    with pytest.raises(DataIntegrityError, match=match):
        S.check_bars(bars)


def test_hill_rejects_nonpositive_threshold_and_bad_k():
    with pytest.raises(ValueError, match="positive"):
        S.hill(np.r_[np.ones(5), -np.ones(20)], 5)
    with pytest.raises(S.InsufficientSample):
        S.hill(np.ones(30), 0)


def test_v42_nonpositive_v1_is_reported_and_the_run_completes(tmp_path):
    """Protocol v4.2 (U9): V1 does not decide whether the pipeline continues. Per-hour RTH variance a quarter of
    per-hour overnight variance gives a negative V1; the development run completes, reports V1 descriptively,
    writes the official verdict with V1's fixed label, and the holdout stage is not refused on V1's account."""
    sd_rth = 0.006 * math.sqrt(0.25 * S.RTH_HOURS / S.ON_HOURS)
    cfg = _project(tmp_path)
    spec_bars, _ = sy.make(sy.Spec("2023-10-02", "2025-12-31", sy.gaussian(0.006), sy.gaussian(sd_rth), seed=31,
                                   holidays=["2023-11-23", "2023-12-25", "2024-01-01", "2024-07-04", "2024-11-28",
                                             "2024-12-25", "2025-01-01", "2025-07-04", "2025-11-27", "2025-12-25"],
                                   half_days=["2023-11-24", "2024-07-03", "2024-11-29", "2024-12-24", "2025-07-03",
                                              "2025-11-28", "2025-12-24"], globex_only=["2024-03-29"]))
    split = pd.Timestamp("2024-11-01 00:00", tz="UTC")
    sy.write_csv(spec_bars[spec_bars.index < split], tmp_path / "data/train.csv")
    cfg.pinned["data/train.csv"] = S.sha256_file(tmp_path / "data/train.csv")
    out = R.run_dev(cfg)
    assert "halted" not in out and "official" in out and out["protocol"] == "v4.2"
    v1 = out["family"]["tests"]["V1"]
    assert v1["theta"] < 0 and v1["classification"] == S.V1_ROLE
    assert out["family"]["v1_point_estimate_positive_reported_only"] is False
    assert set(out["family"]["tests"]) == set(S.TESTS)                       # every claim still reported
    assert out["official"]["official_verdict_per_claim"]["V1"] == S.V1_VERDICT_LABEL
    assert out["official"]["official_verdict_phase"] == "INCONCLUSIVE"
    assert "descriptives" in out and "sensitivities" in out
    txt = (tmp_path / cfg.verdict_txt).read_text()
    assert "Calibration disclosures" in txt and "NOT verified" in txt


def test_v42_no_v1_outcome_halt_exists_in_the_code():
    src = inspect.getsource(R.run_dev) + inspect.getsource(S.run_family)
    assert "pipeline_check" not in src and 'result["halted"]' not in src
    assert '"v1_point_estimate_positive_reported_only"' in inspect.getsource(S.run_family)


def test_v42_p1_and_fwer_disclosures_are_attached():
    fam = S.run_family(_family_inputs(1200, 3.0, np.random.default_rng(53)), B=999)
    assert fam["tests"]["P1"]["calibration_note"] == S.P1_CALIBRATION_NOTE
    assert "NOT established confirmatory evidence" in S.P1_CALIBRATION_NOTE and "not of B" in S.P1_CALIBRATION_NOTE
    assert "NOT verified" in fam["calibration_disclosures"]["family_wise_error"]
    v = S.official_verdict({t: "established" for t in S.TESTS}, {t: True for t in S.TESTS})
    assert v["calibration_disclosures"] == S.CALIBRATION_DISCLOSURES
    assert "P1" in S.render_verdict(v).split("Calibration disclosures")[1]
    assert v["official_verdict_phase"] == "INCONCLUSIVE"
    for t in ("T1", "T2", "L1"):                                                 # disclosure is P1-specific
        assert "calibration_note" not in fam["tests"][t]


def test_git_commit_check_uses_git(tmp_path):
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "doc.md").write_text("a\n")
    assert not R.git_is_committed(tmp_path, "doc.md")                # untracked
    subprocess.run(["git", "add", "doc.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "x"], cwd=tmp_path, check=True)
    assert R.git_is_committed(tmp_path, "doc.md")
    (tmp_path / "doc.md").write_text("changed\n")
    assert not R.git_is_committed(tmp_path, "doc.md")                # uncommitted edit


def test_cli_rejects_unknown_mode_and_default_fomc_comes_from_family3():
    with pytest.raises(SystemExit):
        R.main(["run_sessions_study.py", "everything"])
    f = R.default_fomc()
    assert len(f) == 59 and f[0] == "2019-06-19" and f[-1] == "2026-10-28"


def test_nan_bootstrap_replicates_are_refused_not_silently_counted():
    """Regression: NaN replicates used to count as 'not more extreme', biasing p DOWN."""
    with pytest.raises(ValueError, match="non-finite"):
        S.centered_p(1.0, np.r_[np.random.default_rng(0).normal(size=99), np.nan])
    with pytest.raises(ValueError, match="non-finite"):
        S.percentile_ci(np.r_[np.ones(9), np.inf], 0.99)
    with pytest.raises(S.InsufficientSample, match="k < 1"):
        S._hill_rows_k(np.ones((2, 10)), np.array([1, 0]))


def test_tail_stability_is_refused_when_regime_k_is_below_minimum():
    """Open issue U2: regimes too short for a Hill k of 20 are refused and the claim's stability is
    reported as not assessable (stable=None), with a provisional verdict label."""
    rng = np.random.default_rng(16)
    x = _family_inputs(1600, 3.0, rng, on_tail=3.0)                   # T1 established
    fam = S.run_family(x, B=999, min_sessions=1000)
    assert fam["tests"]["T1"]["classification"] == "established"
    regs = {"R1": ("2020-01-01", "2020-12-31"), "R2": ("2021-01-01", "2021-12-31"),
            "R3": ("2022-01-01", "2022-12-31"), "R4": ("2023-01-01", "2026-12-31")}
    st = S.stability(x, fam, B=999, regimes=regs)
    assert st["T1"]["stable"] is None and "R1" in st["T1"]["not_assessable"]
    assert "V1" not in st                                              # decision U7: V1 is not a claim
    v = S.official_verdict({t: fam["tests"][t]["classification"] for t in S.TESTS},
                           {t: s["stable"] for t, s in st.items()})
    assert "not assessable" in v["official_verdict_per_claim"]["T1"]
    assert v["official_verdict_phase"] == "INCONCLUSIVE"


def test_expected_real_regime_hill_k_from_frozen_counts():
    """Documents U2 from the frozen protocol alone (no data): a regime of n sessions has at most
    floor(0.05*(n - burn-in)) Hill exceedances; 2020-2022 regimes of about 200-230 sessions fall below 20."""
    for n in (200, 230, 250):
        assert math.floor(S.HILL_FRAC * (n - S.EWMA_BURN)) < S.MIN_HILL_K
    assert math.floor(S.HILL_FRAC * 400) == S.MIN_HILL_K                # ~420 sessions needed per regime


def test_hourly_profile_uses_only_analysis_sessions_so_roll_jumps_cannot_enter():
    """Regression: the profile once used every bar, letting E4's roll jump into the 19:00/20:00 ET hour."""
    switch = "2024-03-13 00:00"
    common = dict(start="2024-03-04", end="2024-03-22", on_draw=sy.gaussian(0.004), rth_draw=sy.gaussian(0.008), seed=17)
    _, _, _, clean = build(sy.Spec(**common), switches=[switch])
    bars_j, _ = sy.make(sy.Spec(**common, roll_jumps={switch: 1.03}))
    bars_c, _ = sy.make(sy.Spec(**common))
    keep = S.analysis_set(clean).index
    assert pd.Timestamp("2024-03-13") not in keep
    pj, pc = S.hourly_variance_profile(bars_j, keep), S.hourly_variance_profile(bars_c, keep)
    assert pj == pytest.approx(pc)                                    # the jump is invisible to the profile
    leaky = S.hourly_variance_profile(bars_j, S.session_table(bars_j).index)
    assert leaky[20] > 100 * pc[20]                                   # ...and would dominate hour 20 otherwise


def test_real_data_guard_blocks_the_project_data_folder():
    with pytest.raises(AssertionError, match="must not open real data"):
        open(ROOT / "data" / "mnq_train.csv")                            # noqa: SIM115
    with pytest.raises(AssertionError, match="must not open real data"):
        pd.read_csv(ROOT / "data" / "mnq_holdout.csv")


def test_synthetic_tests_import_no_webhook_or_execution_module():
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not any(("webhook" in m) or ("broker" in m) or ("live" in m) for m in mods)


def test_volatility_groups_depend_only_on_earlier_sessions():
    """U5: changing session d's RV and every later session's leaves session d's group unchanged."""
    rng = np.random.default_rng(18)
    rv = rng.lognormal(-9, 0.6, 400)
    g = S.vol_tercile_membership(rv)
    assert (g[: S.TERCILE_WINDOW + S.TERCILE_MIN_HISTORY] == 0).all()
    assert set(g[S.TERCILE_WINDOW + S.TERCILE_MIN_HISTORY:]) <= {1, 2, 3}
    for d in (90, 150, 250, 399):
        rv2 = rv.copy()
        rv2[d:] = rng.lognormal(-5, 2.0, len(rv) - d)                      # wildly different present and future
        assert S.vol_tercile_membership(rv2)[d] == g[d]


def test_volatility_group_formula_on_a_hand_case():
    rv = np.arange(1.0, 101.0)                                         # increasing RV
    g = S.vol_tercile_membership(rv, window=2, min_history=3)
    # T[d] = mean(rv[d-2], rv[d-1]) = d - 0.5 for d >= 2; first assigned at d = 5 (T[2..4] = 1.5, 2.5, 3.5)
    assert (g[:5] == 0).all()
    assert g[5] == 3                                                   # T=4.5 above the 2/3 quantile of {1.5,2.5,3.5}
    assert (g[5:] == 3).all()                                          # rising series stays in the top group


def test_s7_is_withdrawn_and_never_computed():
    src = (ROOT / "run_sessions_study.py").read_text(encoding="utf-8")
    assert "WITHDRAWN (decision U4" in src
    assert "garch" not in (ROOT / "nq_bot" / "sessions.py").read_text(encoding="utf-8").lower()


def test_ewma_startup_rule_exact():
    """U3: sigma2[20] = mean(r[0..19]^2); sigma2[t] = lam*sigma2[t-1] + (1-lam)*r[t-1]^2."""
    r = np.random.default_rng(19).normal(0, 0.01, 60)
    z = S.ewma_scale(r)
    s2 = np.mean(r[:20] ** 2)
    assert z[20] == pytest.approx(r[20] / math.sqrt(s2), rel=1e-12)
    s2 = 0.94 * s2 + 0.06 * r[20] ** 2
    assert z[21] == pytest.approx(r[21] / math.sqrt(s2), rel=1e-12)


def test_calibration_script_runs_every_scenario_deterministically():
    """Smoke test of scripts/sessions_calibration.py (synthetic only): each scenario's first replicate runs
    and is reproducible from its recorded seed rule."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("calib", ROOT / "scripts" / "sessions_calibration.py")
    calib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(calib)
    for sid in calib.SCENARIOS:
        a, b = calib.one((sid, 0)), calib.one((sid, 0))
        assert a == b and a[0] == sid
    assert calib.wilson(200, 20000)[0] < 0.01 < calib.wilson(200, 20000)[1]


# ================================================================ decision U7: V1 descriptive only
def test_u7_v1_carries_no_inferential_field_and_guard_rejects_one():
    fam = S.run_family(_family_inputs(1200, 3.0, np.random.default_rng(40)), B=999)
    v1 = fam["tests"]["V1"]
    assert v1["classification"] == S.V1_ROLE and "19.4%" in v1["calibration_note"]
    assert {"p_two_sided_descriptive_only", "ci99_descriptive_only", "ci998_descriptive_only"} <= set(v1)
    assert fam["holm_family"] == {"m": 5, "alpha_fwer": 0.01, "descriptive_only_slots_fixed_at_p_1": ["V1"],
                                  "placeholder_note": S.HOLM_PLACEHOLDER_NOTE}
    for k in S.V1_INFERENTIAL_KEYS:
        bad = json.loads(json.dumps(fam))
        bad["tests"]["V1"][k] = 0.0
        with pytest.raises(AssertionError, match="decision U7"):
            S.assert_v1_descriptive_only(bad)
    bad = json.loads(json.dumps(fam))
    bad["tests"]["V1"]["classification"] = "established"
    with pytest.raises(AssertionError, match="decision U7"):
        S.assert_v1_descriptive_only(bad)


def test_u7_other_four_tests_do_not_depend_on_v1(monkeypatch):
    """Shifting V1's point estimate (and so its p-value) leaves every field of T1, T2, P1, L1 unchanged:
    V1 cannot occupy Holm's first slot and relax the other thresholds."""
    x = _family_inputs(1200, 1.0, np.random.default_rng(41), on_tail=3.0)     # V1 null, T1 alive
    base = S.run_family(x, B=999)
    real = S.point_stats

    def shifted(*a, **k):
        out = real(*a, **k)
        if "V1" in out:
            out["V1"] = out["V1"] + 5.0                    # V1 now extreme: its descriptive p reaches 1/(B+1)
        return out
    real_boot = S.bootstrap_family

    def shifted_boot(*a, **k):
        out = real_boot(*a, **k)
        if "V1" in out:
            out["V1"] = out["V1"] + 5.0                    # same shift: the centred null distribution is unchanged
        return out
    monkeypatch.setattr(S, "point_stats", shifted)
    monkeypatch.setattr(S, "bootstrap_family", shifted_boot)
    moved = S.run_family(x, B=999)
    assert moved["tests"]["V1"]["p_two_sided_descriptive_only"] == pytest.approx(1 / 1000)
    assert base["tests"]["V1"]["p_two_sided_descriptive_only"] > 0.01
    for t in S.INFERENTIAL_TESTS:
        assert moved["tests"][t] == base["tests"][t]


def test_u7_holm_uses_m5_with_v1_slot_fixed_at_one():
    """Hand case: the four inferential p-values meet thresholds 0.01/5, 0.01/4, 0.01/3, 0.01/2 exactly as if
    V1 were present and non-significant; with V1 dropped (m = 4) the first threshold would be 0.0025."""
    p = {"V1": 1.0, "T1": 0.0021, "T2": 0.5, "P1": 0.003, "L1": 0.9}
    adj, rej = S.holm(p)
    assert rej == {"T1": False, "P1": False, "T2": False, "L1": False, "V1": False}   # 0.0021 > 0.002
    adj4, rej4 = S.holm({k: v for k, v in p.items() if k != "V1"})
    assert rej4["T1"]                                                               # m = 4 would reject
    assert adj["T1"] == pytest.approx(5 * 0.0021)


@pytest.mark.parametrize("v1_class", ["established", "contradicted", "not established", S.V1_ROLE, "anything"])
@pytest.mark.parametrize("v1_stable", [True, False, None])
def test_u7_official_verdict_ignores_every_v1_input(v1_class, v1_stable):
    cls = {"V1": v1_class, "T1": "established", "T2": "not established", "P1": "contradicted", "L1": "established"}
    stab = {"V1": v1_stable, "T1": None, "L1": True}
    ref = S.official_verdict({**cls, "V1": "not established"}, {k: v for k, v in stab.items() if k != "V1"})
    v = S.official_verdict(cls, stab)
    assert v == ref
    assert v["official_verdict_per_claim"]["V1"] == S.V1_VERDICT_LABEL
    assert v["official_verdict_phase"] == "INCONCLUSIVE"


def test_u7_v1_sign_is_reported_not_inferential():
    """A positive but statistically weak V1 is simply reported; its sign flag reads only the point estimate."""
    x = _family_inputs(1200, 1.05, np.random.default_rng(42))
    fam = S.run_family(x, B=999)
    assert fam["tests"]["V1"]["theta"] > 0
    assert fam["v1_point_estimate_positive_reported_only"] is True
    assert fam["tests"]["V1"]["p_two_sided_descriptive_only"] > 0.01
    src = inspect.getsource(S.run_family)
    assert 'out["v1_point_estimate_positive_reported_only"] = bool(theta["V1"] > 0)' in src


def test_u7_protocol_and_calibration_artifacts_preserved():
    """Decision U7 changes no protocol definition and keeps the calibration evidence intact."""
    import hashlib
    for name, sha in (("DRAFT_PREREG_SESSIONS_awaiting_signoff.md",
                       "716e00037ab4d7e20b9f9a44a0af6a146e646f1f631101470a2c8ceb37506021"),
                      ("SESSIONS_CALIBRATION.json",
                       "e32b7992a48c2fa9718cb4700d36fb838afe2c8459ec24ecfeab2ed55164da27"),
                      ("SESSIONS_CALIBRATION_P1_B9999.json",
                       "3fba6b9d3a44b7a72262befa417874c37b263c1122cd0efb2195442ce6514451"),
                      ("DRAFT_PREREG_SESSIONS_v4.2_awaiting_signoff.md",
                       "99b54fd3571885baae6d58677513dbc43327c6731242914ebd0fe936afecebea")):
        cands = [ROOT / "docs" / name, Path("/mnt/user-data/outputs") / name]
        found = [c for c in cands if c.exists()]
        if not found:
            pytest.skip(f"{name} not present in this checkout")
        assert hashlib.sha256(found[0].read_bytes()).hexdigest() == sha


# ================================================================ decision L4: 60 prior volatility values
def test_l4_constants_frozen():
    assert S.TERCILE_WINDOW == 20 and S.TERCILE_MIN_HISTORY == 60
    sig = inspect.signature(S.vol_tercile_membership)
    assert sig.parameters["window"].default == 20 and sig.parameters["min_history"].default == 60
    assert "vol_tercile_membership(rv_rth)" in inspect.getsource(S.vol_tercile_split)   # defaults, no override


def test_l4_first_eligible_assignment_and_boundaries():
    """Sessions 0-79 unassigned (20 for the first trailing mean + 60 earlier trailing means); session 80 is the
    first assigned, and its cut-offs are the 1/3 and 2/3 quantiles of T[20..79] exactly."""
    rng = np.random.default_rng(43)
    rv = rng.lognormal(-9, 0.6, 300)
    g = S.vol_tercile_membership(rv)
    assert (g[:80] == 0).all() and (g[:60] == 0).all()
    assert g[80] in (1, 2, 3) and (g[80:] > 0).all()
    T = pd.Series(rv).shift(1).rolling(20).mean().to_numpy()
    assert np.isnan(T[:20]).all() and np.isfinite(T[20:]).all()
    c1, c2 = np.quantile(T[20:80], [1 / 3, 2 / 3])
    assert g[80] == (1 if T[80] <= c1 else 2 if T[80] <= c2 else 3)
    for d in (81, 150, 299):                                       # every later session: cut-offs from T[20..d-1]
        c1, c2 = np.quantile(T[20:d], [1 / 3, 2 / 3])
        assert g[d] == (1 if T[d] <= c1 else 2 if T[d] <= c2 else 3)
    # exactly at the boundary: T equal to a cut-off goes to the lower group
    rv_b = np.ones(120)
    assert (S.vol_tercile_membership(rv_b)[80:] == 1).all()


def test_l4_short_samples_and_no_look_ahead_at_the_boundary():
    rng = np.random.default_rng(44)
    for n in (0, 1, 20, 79, 80):
        g = S.vol_tercile_membership(rng.lognormal(-9, 0.6, n))
        assert len(g) == n and (g == 0).all()                   # nothing can be assigned before session 80
    rv = rng.lognormal(-9, 0.6, 200)
    g = S.vol_tercile_membership(rv)
    for d in (79, 80, 81):
        rv2 = rv.copy()
        rv2[d:] *= 50.0                                           # present and future changed
        g2 = S.vol_tercile_membership(rv2)
        assert (g2[: d + 1] == g[: d + 1]).all()                  # sessions up to and including d unchanged
    # first eligible assignment depends on sessions 0..79 only (sessions 0..19 enter T[20..39], etc.)
    rv3 = rv.copy(); rv3[0] *= 50.0                               # earlier data may move later groups...
    assert (S.vol_tercile_membership(rv3)[:80] == 0).all()        # ...but never makes an early session eligible


def test_l4_assigned_count_is_n_minus_80():
    for n in (81, 500, 1230):
        g = S.vol_tercile_membership(np.random.default_rng(n).lognormal(-9, 0.6, n))
        assert int((g == 0).sum()) == 80 and int((g > 0).sum()) == n - 80


# ================================================================ decision U8: five slots, V1 placeholder = 1
def test_u8_v1_cannot_change_holm_adjusted_results_of_the_other_four():
    """For 2,000 random p-vectors of T1, T2, P1, L1 and any observed V1 p-value, the Holm-adjusted p and the
    rejection decisions of the four are identical to Holm with V1's slot at the placeholder 1.0."""
    rng = np.random.default_rng(50)
    v1_values = (1e-9, 1e-4, 0.001, 0.0021, 0.01, 0.5, 1.0)
    for _ in range(2000):
        four = dict(zip(S.INFERENTIAL_TESTS, rng.choice([rng.uniform(0, 0.01), rng.uniform(0, 1)], 4)))
        ref_adj, ref_rej = S.holm({**four, "V1": 1.0})
        for v in v1_values:
            adj, rej, entered = S.holm_with_placeholder({**four, "V1": v})
            assert entered["V1"] == S.HOLM_PLACEHOLDER_P == 1.0          # placeholder, not the observed p
            assert all(entered[t] == four[t] for t in S.INFERENTIAL_TESTS)
            assert all(adj[t] == ref_adj[t] and rej[t] == ref_rej[t] for t in S.INFERENTIAL_TESTS)
            assert rej["V1"] is False and adj["V1"] == 1.0


def test_u8_thresholds_are_the_frozen_five_slot_ones():
    eps = 1e-12
    p = {"V1": 0.0, "T1": 0.002, "T2": 0.0025, "P1": 0.01 / 3, "L1": 0.005}
    _, rej, _ = S.holm_with_placeholder(p)
    assert all(rej[t] for t in S.INFERENTIAL_TESTS) and not rej["V1"]           # 0.01/5, /4, /3, /2 met exactly
    _, rej, _ = S.holm_with_placeholder({**p, "T1": 0.002 + eps})
    assert not any(rej.values())                                               # first step fails -> all stop
    _, rej, _ = S.holm_with_placeholder({**p, "L1": 0.005 + eps})
    assert [rej[t] for t in ("T1", "T2", "P1", "L1")] == [True, True, True, False]
    with pytest.raises(ValueError, match="Holm family"):
        S.holm_with_placeholder({"T1": 0.1, "T2": 0.1, "P1": 0.1, "L1": 0.1})    # V1 slot may not be dropped
    assert S.M_TESTS == 5 and S.ALPHA_FWER == 0.01


def test_u8_run_family_uses_the_placeholder_and_documents_it():
    x = _family_inputs(1200, 3.0, np.random.default_rng(51), on_tail=3.0)
    fam = S.run_family(x, B=999)
    obs = {t: fam["tests"][t]["p_two_sided"] for t in S.INFERENTIAL_TESTS}
    obs["V1"] = fam["tests"]["V1"]["p_two_sided_descriptive_only"]
    adj, rej, _ = S.holm_with_placeholder(obs)
    for t in S.INFERENTIAL_TESTS:
        assert fam["tests"][t]["p_holm"] == adj[t] and fam["tests"][t]["holm_reject"] == rej[t]
    note = fam["holm_family"]["placeholder_note"]
    assert "administrative placeholder" in note and "not an observed V1 p-value" in note
    assert "intentionally conservative" in note and fam["holm_family"]["m"] == 5


def test_l4_one_based_numbering_of_the_warm_up():
    """Decision L4 in one-based session numbers. Session s (1-based) has a 20-session average T_s once s >= 21
    (sessions s-20 .. s-1). Before session s there are s - 21 such averages, so 60 prior averages first exist at
    s = 81. Sessions 1-80 are unassigned; session 81 is the first assigned; session 80 has only 59."""
    rv = np.random.default_rng(52).lognormal(-9, 0.6, 200)
    g = S.vol_tercile_membership(rv)
    one_based = {s: int(g[s - 1]) for s in range(1, 201)}
    assert all(one_based[s] == 0 for s in range(1, 81))
    assert one_based[81] in (1, 2, 3)
    T = pd.Series(rv).shift(1).rolling(20).mean().to_numpy()
    prior_averages = lambda s: int(np.isfinite(T[: s - 1]).sum())          # noqa: E731  T_1 .. T_{s-1}
    assert prior_averages(80) == 59 and prior_averages(81) == 60
    assert np.isnan(T[19]) and np.isfinite(T[20])                           # T first defined at session 21
