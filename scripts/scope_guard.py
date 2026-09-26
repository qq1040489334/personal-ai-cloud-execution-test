"""Gate 2 — enforce the agent's modification scope.

Compares the working tree (and any agent commit) against a base revision and
blocks: deletions, new files, workflow edits, secret-ish paths, and any change
outside the allowlist.

Run: python scripts/scope_guard.py <base_rev>
"""

from __future__ import annotations

import json
import subprocess
import sys

FORBIDDEN_PREFIXES = (".github/workflows/",)
FORBIDDEN_SUBSTRINGS = ("secret", "token", "credential", ".env", ".pem", ".key")
IGNORED = (".pytest_cache", "__pycache__")


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    return result.stdout


def normalize(path: str) -> str:
    return path.strip().replace("\\", "/")


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
    contract_path = sys.argv[2] if len(sys.argv) > 2 else ""
    violations: list[str] = []
    if not contract_path:
        print("BLOCK: task contract path required")
        return 1
    try:
        contract = json.loads(open(contract_path, encoding="utf-8").read())
        if isinstance(contract, str):
            contract = json.loads(contract)
        allowlist = {normalize(str(p)) for p in contract.get("expected_files", [])}
    except (OSError, ValueError, TypeError) as exc:
        print(f"BLOCK: cannot load task allowlist: {exc}")
        return 1
    if not allowlist:
        print("BLOCK: empty task allowlist")
        return 1

    # Committed + uncommitted content changes relative to base.
    for line in git("diff", "--name-status", base).splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        path = normalize(parts[-1])
        if status.startswith("D"):
            violations.append(f"deletion forbidden: {path}")
            continue
        if any(skip in path for skip in IGNORED):
            continue
        if status.startswith(("A", "C")):
            violations.append(f"new file forbidden: {path}")
            continue
        if path.startswith(FORBIDDEN_PREFIXES) or any(s in path.lower() for s in FORBIDDEN_SUBSTRINGS):
            violations.append(f"forbidden target modified: {path}")
        elif path not in allowlist:
            violations.append(f"modification outside task allowlist: {path}")

    # Untracked, non-ignored files = new files the agent created.
    for path in git("ls-files", "--others", "--exclude-standard").splitlines():
        path = normalize(path)
        if not path or any(skip in path for skip in IGNORED):
            continue
        violations.append(f"new untracked file forbidden: {path}")

    print("=== SCOPE_GUARD RESULT (base=%s) ===" % base)
    print("changed files:")
    print(git("diff", "--name-status", base).strip() or "(none)")
    if violations:
        for v in violations:
            print(f"BLOCK: {v}")
        return 1
    print("PASS: all changes within allowlist, no deletions, no forbidden paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
