"""CSCV must give the right answer on cases whose answer is known in advance."""
import numpy as np
import pandas as pd
import pytest

from nq_bot.pbo import cscv, daily_matrix

T, N, SEED = 1600, 12, 7


def _noise(rng):
    return pd.DataFrame(rng.normal(0, 1, (T, N)), columns=[f"s{i}" for i in range(N)])


def test_pure_noise_gives_pbo_near_one_half():
    """With no real edge anywhere, the in-sample winner is a coin flip out of sample."""
    res = cscv(_noise(np.random.default_rng(SEED)), 16)
    assert 0.40 <= res["pbo"] <= 0.60, res["pbo"]


def test_a_genuine_persistent_edge_gives_pbo_near_zero():
    rng = np.random.default_rng(SEED)
    m = _noise(rng)
    m["s0"] = rng.normal(0.25, 1, T)
    res = cscv(m, 16)
    assert res["pbo"] < 0.05, res["pbo"]
    assert max(res["selected_in_sample_counts"], key=res["selected_in_sample_counts"].get) == "s0"


def test_an_edge_that_reverses_halfway_gives_high_pbo():
    """The classic overfit: great in the first half, bad in the second."""
    rng = np.random.default_rng(SEED)
    m = _noise(rng)
    m.loc[: T // 2, "s1"] = rng.normal(0.45, 1, len(m.loc[: T // 2]))
    m.loc[T // 2 :, "s1"] = rng.normal(-0.45, 1, len(m.loc[T // 2 :]))
    res = cscv(m, 16)
    assert res["pbo"] > 0.5, res["pbo"]


def test_block_count_must_be_even_and_feasible():
    m = _noise(np.random.default_rng(SEED))
    with pytest.raises(ValueError, match="even"):
        cscv(m, 15)
    with pytest.raises(ValueError, match="at least 2"):
        cscv(m[["s0"]], 16)
    with pytest.raises(ValueError, match="too few"):
        cscv(m.head(10), 16)


def test_daily_matrix_zero_fills_non_trading_days_and_keeps_totals():
    """A day with no position is a real zero, not a missing value; totals must survive alignment."""
    import datetime as dt

    cal = [dt.date(2025, 1, d) for d in range(1, 11)]
    a = pd.Series({dt.date(2025, 1, 2): 100.0, dt.date(2025, 1, 5): -40.0})
    b = pd.Series({dt.date(2025, 1, 3): 7.0})
    m = daily_matrix({"a": a, "b": b}, cal)
    assert list(m.index) == cal
    assert m["a"].sum() == pytest.approx(60.0)
    assert m["b"].sum() == pytest.approx(7.0)
    assert int((m["a"] != 0).sum()) == 2
    assert not m.isna().any().any()


def test_reported_counts_are_internally_consistent():
    res = cscv(_noise(np.random.default_rng(SEED)), 10)
    assert res["n_combinations"] == 252                     # C(10,5)
    assert res["rows_used"] == res["s_blocks"] * res["block_size"]
    assert res["rows_used"] + res["rows_dropped"] == T
    assert res["winner_oos_below_median_count"] == pytest.approx(res["pbo"] * res["n_combinations"], abs=1)


def test_daily_matrix_refuses_to_drop_off_calendar_pnl():
    """Regression test for the independent audit: reindexing used to discard P&L dated outside the
    calendar, losing $322.70 across ORB/H3/H4/H5 on exchange half-days. It must refuse instead."""
    import datetime as dt

    cal = [dt.date(2025, 1, d) for d in range(1, 6)]
    traded_off_calendar = pd.Series({dt.date(2025, 1, 2): 10.0, dt.date(2025, 1, 9): -250.0})

    with pytest.raises(ValueError, match="outside the calendar"):
        daily_matrix({"a": traded_off_calendar}, cal)

    # an explicit opt-out still records exactly what was left out
    m = daily_matrix({"a": traded_off_calendar}, cal, on_off_calendar="report")
    assert m["a"].sum() == pytest.approx(10.0)
    assert m.attrs["off_calendar"]["a"] == {"sessions": 1, "pnl": -250.0}

    # and a series wholly inside the calendar passes untouched
    inside = pd.Series({dt.date(2025, 1, 3): 5.0})
    assert daily_matrix({"b": inside}, cal)["b"].sum() == pytest.approx(5.0)
