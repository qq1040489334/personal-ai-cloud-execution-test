"""Gate 1b — validate the agent's EXECUTION_PLAN before allowing execution.

Fail-closed: anything unparsable or outside the allowlist blocks the run.
Run: python scripts/plan_gate.py <plan_file>
"""

from __future__ import annotations

import re
import sys

ALLOWLIST = {"hello.py", "test_hello.py"}
ALLOWED_RISK = {"LOW", "MEDIUM"}
FORBIDDEN_PREFIXES = (".github/workflows/",)
FORBIDDEN_SUBSTRINGS = ("secret", "token", "credential", ".env", ".pem", ".key")


def parse_files(text: str) -> list[str]:
    match = re.search(r"files to modify\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if not match:
        return []
    raw = match.group(1).strip()
    raw = raw.split("\n")[0]
    items = re.split(r"[,\s]+", raw)
    return [i.strip().strip("`\"'[]") for i in items if i.strip()]


def parse_risk(text: str) -> str:
    match = re.search(r"risk level\s*[:\-]\s*([A-Za-z]+)", text, re.IGNORECASE)
    return match.group(1).upper() if match else "UNKNOWN"


def evaluate(text: str) -> list[str]:
    errors: list[str] = []
    if "EXECUTION_PLAN" not in text.upper():
        errors.append("missing EXECUTION_PLAN block")

    risk = parse_risk(text)
    if risk not in ALLOWED_RISK:
        errors.append(f"risk level not acceptable: {risk} (allowed: LOW, MEDIUM)")

    files = parse_files(text)
    if not files:
        errors.append("no 'Files to modify:' entry parsed")
    for path in files:
        low = path.lower()
        if low.startswith(FORBIDDEN_PREFIXES) or any(s in low for s in FORBIDDEN_SUBSTRINGS):
            errors.append(f"forbidden target: {path}")
        elif path not in ALLOWLIST:
            errors.append(f"outside allowlist: {path} (allowed: {sorted(ALLOWLIST)})")
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: plan_gate.py <plan_file>")
        return 2
    try:
        text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
    except OSError as exc:
        print(f"PLAN_GATE BLOCK: cannot read plan: {exc}")
        return 1

    errors = evaluate(text)
    print("=== EXECUTION_PLAN (agent output) ===")
    print(text.strip())
    print("=== PLAN_GATE RESULT ===")
    if errors:
        for e in errors:
            print(f"BLOCK: {e}")
        return 1
    print("PASS: plan within scope and acceptable risk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
