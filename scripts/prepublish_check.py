"""Fail loudly if anything that must not be public is about to be committed.

Run from the repo root after `git add`:
    python scripts/prepublish_check.py
Checks every file git would publish (tracked + staged) for: .env files, market data,
trade logs, risk state, API-key / token patterns, IB paper/live account IDs, emails,
and local Windows user paths. Exit code 1 = do not push.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN_PATHS = [
    (re.compile(r"(^|/)\.env($|\.)(?!example$)"), ".env file (secrets)"),
    (re.compile(r"(^|/)data/"), "market data folder (licensed data)"),
    (re.compile(r"\.(dbn|dbn\.zst|parquet)$"), "raw market data file"),
    (re.compile(r"(^|/)runs/.*\.(csv|jsonl)$"), "trade-level output (derived from licensed data)"),
    (re.compile(r"(^|/)logs/"), "bot logs"),
    (re.compile(r"risk_state\.json$"), "bot risk state"),
]
CONTENT_PATTERNS = [
    (re.compile(r"\bdb-[A-Za-z0-9]{20,}\b"), "Databento API key"),
    (re.compile(r"\b(?:ghp|gho|github_pat)_[A-Za-z0-9_]{20,}\b"), "GitHub token"),
    (re.compile(r"\bsk-[A-Za-z0-9-]{20,}\b"), "API secret key"),
    (re.compile(r"\bDU[A-Z]?\d{5,}\b|\bU\d{7,}\b"), "Interactive Brokers account ID"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "email address"),
    (re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+", re.I), "local Windows user path"),
    (re.compile(r"https://discord(app)?\.com/api/webhooks/\S+"), "alert webhook URL"),
    (re.compile(r'"(?:entry_px|exit_px|entry_price|exit_price)"\s*:'), "per-trade prices (derived from licensed data)"),
]
ALLOWED_EMAILS = {"noreply@anthropic.com"}
TEXT_EXT = {".py", ".md", ".txt", ".yaml", ".yml", ".csv", ".json", ".ini", ".cfg", ".toml", ".example", ""}


def files_to_publish() -> list[str]:
    out = subprocess.run(["git", "ls-files", "--cached"], capture_output=True, text=True, check=True).stdout  # noqa: S607
    return [f for f in out.splitlines() if f]


def scan(paths: list[str]) -> list[str]:
    problems = []
    for p in paths:
        for rx, why in FORBIDDEN_PATHS:
            if rx.search(p):
                problems.append(f"{p}: {why}")
        path = Path(p)
        if path.suffix.lower() not in TEXT_EXT and path.name != ".env.example" or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for rx, why in CONTENT_PATTERNS:
            for m in rx.finditer(text):
                hit = m.group(0)
                if why == "email address" and hit in ALLOWED_EMAILS:
                    continue
                if why.startswith("per-trade prices") and not p.startswith("runs/"):
                    continue  # code and tests may name these fields; only result files are checked
                if why == "Databento API key" and set(hit[3:]) <= {"x"}:
                    continue  # the placeholder in .env.example
                problems.append(f"{p}: {why} -> {hit[:6]}…")
    return problems


def main() -> int:
    try:
        paths = files_to_publish()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Run this inside the git repo after `git add` (git must be installed).")
        return 2
    problems = scan(paths)
    if problems:
        print("DO NOT PUSH. Remove these from the commit (git rm --cached <file>):")
        for p in problems:
            print("  -", p)
        return 1
    print(f"OK: {len(paths)} files checked, nothing secret or licensed found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
