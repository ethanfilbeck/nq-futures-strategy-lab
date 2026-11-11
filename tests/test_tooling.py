import hashlib
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate_data  # noqa: E402
import verify_prereg  # noqa: E402

from nq_bot.data import synthetic_bars  # noqa: E402


def test_repo_preregistrations_are_unchanged():
    assert verify_prereg.check() == []


def test_prereg_check_catches_edits_missing_hashes_and_ignores_crlf(tmp_path):
    a = tmp_path / "PREREG_A.md"
    a.write_bytes(b"rule one\nrule two\n")
    h = hashlib.sha256(a.read_bytes()).hexdigest()
    (tmp_path / "PREREG_HASH.txt").write_text(f"PREREG_A.md sha256={h} frozen_at=2026-01-01\n")
    assert verify_prereg.check(tmp_path) == []
    a.write_bytes(b"rule one\r\nrule two\r\n")                 # Windows line endings: same content
    assert verify_prereg.check(tmp_path) == []
    a.write_bytes(b"rule one\nrule two, loosened\n")           # edited after freezing
    assert any("CHANGED" in p for p in verify_prereg.check(tmp_path))
    (tmp_path / "PREREG_B.md").write_text("never frozen")
    assert any("PREREG_B.md" in p and "no hash" in p for p in verify_prereg.check(tmp_path))


def test_clean_bars_pass_validation():
    errors, _ = validate_data.validate(synthetic_bars(days=3))
    assert errors == []


def test_validation_catches_bad_bars():
    bars = synthetic_bars(days=2).copy()
    bars.iloc[5, bars.columns.get_loc("high")] = bars.iloc[5]["low"] - 1        # high below low
    bars.iloc[9, bars.columns.get_loc("close")] = -1.0                           # negative price
    bars.iloc[12, bars.columns.get_loc("volume")] = -5                           # negative volume
    bars = pd.concat([bars, bars.iloc[[20]]])                                    # duplicate + out of order
    errors, _ = validate_data.validate(bars)
    text = " | ".join(errors)
    for expected in ("not sorted", "duplicate", "negative price", "high/low", "negative volume"):
        assert expected in text, (expected, text)


def test_validation_warns_on_off_tick_prices_and_big_moves():
    bars = synthetic_bars(days=2).copy()
    bars.iloc[30, bars.columns.get_loc("close")] += 0.1                          # off the 0.25 grid
    bars.iloc[100:, :4] *= 1.05                                                  # a 5% jump (e.g. a bad roll)
    errors, warnings = validate_data.validate(bars)
    assert any("tick grid" in w for w in warnings) and any("one-bar moves" in w for w in warnings)


# Research code must never be able to reach a broker. Enforced by reading the imports, not by convention.
RESEARCH = ["backtest", "features", "metrics", "regime", "strategy", "momentum", "family2", "family3", "family4",
            "risk", "engine", "events", "contracts", "config", "report", "broker/sim", "broker/base"]
EXECUTION = {"ibkr", "live", "drill", "fomc_paper", "ib_async"}


def test_research_modules_do_not_import_execution_code():
    import ast
    root = Path(__file__).resolve().parent.parent
    files = [root / "nq_bot" / f"{m}.py" for m in RESEARCH] + sorted(root.glob("run_*.py")) \
        + [root / "research_edge.py", root / "wf_edge.py"]
    for f in files:
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [a.name for a in node.names]
            hit = {part for n in names for part in n.split(".")} & EXECUTION
            assert not hit, f"{f.name} imports execution code: {hit}"


def test_roll_detection_finds_an_injected_gap():
    """nq_bot.rolls must find a roll-shaped jump, and adjust_exit must divide it back out.

    Regression test for the November 2026 audit: an unadjusted continuous series jumps at every roll, and
    a strategy holding across one books that gap as profit it never received (docs/AUDIT_2026_11_ROLLS.md).
    """
    import pandas as pd

    from nq_bot import rolls
    from nq_bot.data import synthetic_bars

    bars = synthetic_bars(days=40).copy()
    # a roll is a quiet overnight level shift, so build one: March, 20:00 ET, low volume, +1%.
    # Anchor the block to the last real close so the injected gap is the only discontinuity.
    march = pd.Timestamp("2025-03-12 20:00", tz="America/New_York")
    base = float(bars["close"].iloc[-1])
    overnight = pd.DataFrame({"open": base, "high": base, "low": base, "close": base, "volume": 1.0},
                             index=pd.date_range(march - pd.Timedelta(minutes=5), periods=11, freq="1min"))
    overnight.loc[march:, ["open", "high", "low", "close"]] *= 1.01     # the gap
    bars = pd.concat([bars, overnight]).sort_index()

    found = rolls.detect(bars)
    assert march in found, f"the injected roll at {march} was not detected: {found}"
    assert abs(found[march] - 0.01) < 1e-6

    entry, exit_ts = march - pd.Timedelta(minutes=3), march + pd.Timedelta(minutes=3)
    assert rolls.spans(entry, exit_ts, found), "a hold spanning the roll must report it"
    assert abs(rolls.adjust_exit(base * 1.01, entry, exit_ts, found) - base) < 1e-6
    # a hold that ends before the roll is untouched
    assert rolls.adjust_exit(base, entry, march - pd.Timedelta(minutes=1), found) == base


def test_research_report_requires_roll_exposure():
    """Every backtest summary must state roll exposure, and say so loudly when it was not checked."""
    import pandas as pd

    from nq_bot.family3 import Trade
    from nq_bot.research_report import Costs, render, summarize

    ts = pd.Timestamp("2025-03-11 14:00", tz="America/New_York")
    trades = [Trade(ts + pd.Timedelta(days=i), ts + pd.Timedelta(days=i, hours=23), 1,
                    20000.0, 20000.0 + 10 * (1 if i % 3 else -2), "time") for i in range(12)]
    pnl = [(t.exit - t.entry) * t.side * 2.0 - 1.24 for t in trades]
    costs = Costs(commission_rt=1.24, slippage_rt=1.00)

    unchecked = summarize(trades, pnl, costs, label="no roll map")
    assert unchecked["roll_exposure"]["checked"] is False
    assert "NOT CHECKED" in unchecked["roll_exposure"]["warning"]
    assert "NOT CHECKED" in render(unchecked)

    checked = summarize(trades, pnl, costs, roll_map={}, label="clean")
    assert checked["roll_exposure"]["checked"] is True
    assert checked["roll_exposure"]["holds_spanning_a_roll"] == 0

    # the standard block must carry everything the audit showed was missing
    for key in ("expectancy_per_trade", "mean_ci95_approx", "max_drawdown", "costs",
                "gross_of_all_costs", "double_slippage", "t_dropping_best", "by_year"):
        assert key in checked, key
