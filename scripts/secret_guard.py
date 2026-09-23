"""Gate 3 — secret leak check.

Fails if the model secret value (env MODEL_API_KEY) or any api-key-like string
appears in the change set or in any changed file.

Run: MODEL_API_KEY=... python scripts/secret_guard.py <base_rev>
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9]{10,}")
IGNORED = (".pytest_cache", "__pycache__")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
    secret = os.environ.get("MODEL_API_KEY", "")
    findings: list[str] = []

    diff = git("diff", base)
    if secret and secret in diff:
        findings.append("secret value present in diff")
    for m in KEY_PATTERN.finditer(diff):
        findings.append(f"api-key-like string in diff: {m.group(0)[:8]}...")

    changed = [l.split("\t")[-1] for l in git("diff", "--name-only", base).splitlines() if l.strip()]
    for name in changed:
        if any(skip in name for skip in IGNORED):
            continue
        p = Path(name)
        if not p.is_file():
            continue
        try:
            data = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if secret and secret in data:
            findings.append(f"secret value present in file: {name}")
        for m in KEY_PATTERN.finditer(data):
            findings.append(f"api-key-like string in {name}: {m.group(0)[:8]}...")

    print("=== SECRET_GUARD RESULT ===")
    if findings:
        for f in findings:
            print(f"BLOCK: {f}")
        return 1
    print("PASS: no secret value and no api-key-like string in the change set")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
