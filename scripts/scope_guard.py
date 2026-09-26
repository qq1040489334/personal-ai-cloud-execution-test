"""Gate 2 — enforce the agent's task-scoped modification scope."""

from __future__ import annotations

import fnmatch
import json
import posixpath
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


def unsafe_pattern(path: str) -> bool:
    p = normalize(path)
    return (
        not p
        or p.startswith("/")
        or (len(p) >= 2 and p[1] == ":")
        or any(part == ".." for part in p.split("/"))
    )


def forbidden(path: str) -> bool:
    p = normalize(path)
    low = p.lower()
    return p.startswith(FORBIDDEN_PREFIXES) or any(s in low for s in FORBIDDEN_SUBSTRINGS)


def matches(path: str, patterns: set[str]) -> bool:
    p = normalize(path)
    for raw in patterns:
        pat = normalize(raw)
        if p == pat:
            return True
        if pat.endswith("/**") and (p == pat[:-3] or p.startswith(pat[:-2])):
            return True
        if fnmatch.fnmatchcase(p, pat):
            return True
    return False


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
    contract_path = sys.argv[2] if len(sys.argv) > 2 else ""
    if not contract_path:
        print("BLOCK: task contract path required")
        return 1
    try:
        contract = json.loads(open(contract_path, encoding="utf-8").read())
        if isinstance(contract, str):
            contract = json.loads(contract)
        raw = contract.get("expected_files", [])
        if not isinstance(raw, list) or not raw:
            raise ValueError("expected_files must be a non-empty list")
        allowlist = {normalize(str(p)) for p in raw}
    except (OSError, ValueError, TypeError) as exc:
        print(f"BLOCK: cannot load task allowlist: {exc}")
        return 1

    bad_patterns = [p for p in allowlist if unsafe_pattern(p) or forbidden(p)]
    if bad_patterns:
        for p in bad_patterns:
            print(f"BLOCK: unsafe/forbidden expected_file: {p}")
        return 1

    violations: list[str] = []
    seen: set[str] = set()
    for line in git("diff", "--name-status", base).splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        path = normalize(parts[-1])
        seen.add(path)
        if any(skip in path for skip in IGNORED):
            continue
        if status.startswith("D"):
            violations.append(f"deletion forbidden: {path}")
        elif unsafe_pattern(path):
            violations.append(f"unsafe path modified: {path}")
        elif forbidden(path):
            violations.append(f"forbidden target modified: {path}")
        elif not matches(path, allowlist):
            violations.append(f"modification outside task allowlist: {path}")

    for path in git("ls-files", "--others", "--exclude-standard").splitlines():
        path = normalize(path)
        if not path or path in seen or any(skip in path for skip in IGNORED):
            continue
        if unsafe_pattern(path):
            violations.append(f"unsafe new file: {path}")
        elif forbidden(path):
            violations.append(f"forbidden target modified: {path}")
        elif not matches(path, allowlist):
            violations.append(f"new file outside task allowlist: {path}")

    print(f"=== SCOPE_GUARD RESULT (base={base}) ===")
    print("task allowlist:")
    for p in sorted(allowlist):
        print(f"  {p}")
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
