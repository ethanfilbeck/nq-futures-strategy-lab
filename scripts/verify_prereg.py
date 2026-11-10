"""Check that no pre-registration was edited after it was frozen.

Every docs/PREREG_*.md has its SHA-256 recorded in docs/PREREG_HASH.txt before its test ran. This recomputes
each hash and fails if any differs, or if a PREREG file has no recorded hash. Run by CI and scripts/check.py.

    py scripts\\verify_prereg.py
"""
import hashlib
import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"


def sha(path: Path) -> str:
    # Hash with LF line endings so a Windows checkout (CRLF) gives the same answer as the frozen file.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def check(docs: Path = DOCS) -> list[str]:
    problems, recorded = [], {}
    for line in (docs / "PREREG_HASH.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"(\S+\.md) sha256=([0-9a-f]{64})\b", line)
        if m:
            recorded[m.group(1)] = m.group(2)
    for name, want in recorded.items():
        f = docs / name
        if not f.exists():
            problems.append(f"{name}: recorded in PREREG_HASH.txt but the file is missing")
        elif sha(f) != want:
            problems.append(f"{name}: CHANGED after it was frozen (hash no longer matches)")
    for f in sorted(docs.glob("PREREG_*.md")):
        if f.name not in recorded:
            problems.append(f"{f.name}: has no hash in PREREG_HASH.txt (freeze it before running its test)")
    return problems


if __name__ == "__main__":
    bad = check()
    for b in bad:
        print("FAIL", b)
    if bad:
        sys.exit(1)
    print(f"OK: {len(list(DOCS.glob('PREREG_*.md')))} pre-registrations match their frozen hashes.")
