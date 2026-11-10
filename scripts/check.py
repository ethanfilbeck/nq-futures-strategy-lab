"""One command that runs every quality gate. CI runs exactly this; run it before pushing.

    py scripts\\check.py            # everything
    py scripts\\check.py --fast     # skip the dependency audit (needs internet)

Gates (a failure in any required gate makes this exit 1 - nothing is silently ignored):
  1. ruff          lint + security rules (the Bandit rule set) + naive-datetime checks
  2. pytest        unit, regression and mocked-integration tests
  3. prereg        pre-registrations still match their frozen hashes
  4. prepublish    no secrets, account IDs, licensed data or trade prices in tracked files
  5. pip-audit     known vulnerabilities in dependencies
  6. mypy          type check - ADVISORY: reported, does not fail the run (the code base is mostly untyped)
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
GATES = [
    ("ruff", [PY, "-m", "ruff", "check", "."], True, False),
    ("pytest", [PY, "-m", "pytest", "-q"], True, False),
    ("prereg", [PY, "scripts/verify_prereg.py"], True, False),
    ("prepublish", [PY, "scripts/prepublish_check.py"], True, False),
    ("pip-audit", [PY, "-m", "pip_audit", "-r", "requirements.txt", "--progress-spinner", "off"], True, True),
    ("mypy (advisory)", [PY, "-m", "mypy", "nq_bot", "cli.py", "scripts"], False, False),
]


def main() -> int:
    fast = "--fast" in sys.argv
    rows, failed = [], False
    for name, cmd, required, needs_net in GATES:
        if fast and needs_net:
            rows.append((name, "SKIPPED (--fast)", ""))
            continue
        t0 = time.time()
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)  # noqa: S603 (fixed commands above)
        out = (r.stdout + r.stderr).strip()
        last = out.splitlines()[-1] if out else ""
        ok = r.returncode == 0
        if not ok and required:
            print(f"\n===== {name} output =====\n{out}\n")
            failed = True
        rows.append((name, "PASS" if ok else ("FAIL" if required else "ISSUES (advisory)"), f"{last}  [{time.time() - t0:.0f}s]"))
    print("\n== Quality report ==")
    for name, status, last in rows:
        print(f"{status:<18} {name:<16} {last}")
    print("\nRESULT:", "FAILED" if failed else "all required gates passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
