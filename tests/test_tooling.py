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
