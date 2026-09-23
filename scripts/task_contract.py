"""Gate 1 (dispatch path) — validate a structured task contract.

Fail-closed. Accepts either a JSON object or a JSON string containing one.
Run: python scripts/task_contract.py <task_json_file>
"""

from __future__ import annotations

import json
import sys

ALLOWLIST = {"hello.py", "test_hello.py"}
ALLOWED_RISK = {"LOW", "MEDIUM"}
REQUIRED = ("task_id", "goal", "instructions", "risk_level", "expected_files", "acceptance")
FORBIDDEN_PREFIXES = (".github/workflows/",)
FORBIDDEN_SUBSTRINGS = ("secret", "token", "credential", ".env", ".pem", ".key")


def load(path: str):
    data = json.loads(open(path, encoding="utf-8").read())
    if isinstance(data, str):
        data = json.loads(data)
    return data


def evaluate(data) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["task contract is not a JSON object"]
    for field in REQUIRED:
        if field not in data:
            errors.append(f"missing field: {field}")

    risk = str(data.get("risk_level", "")).upper()
    if risk not in ALLOWED_RISK:
        errors.append(f"risk_level not acceptable: {risk} (allowed: LOW, MEDIUM)")

    files = data.get("expected_files")
    if not isinstance(files, list) or not files:
        errors.append("expected_files must be a non-empty list")
    else:
        for path in files:
            low = str(path).lower()
            if low.startswith(FORBIDDEN_PREFIXES) or any(s in low for s in FORBIDDEN_SUBSTRINGS):
                errors.append(f"forbidden expected_file: {path}")
            elif path not in ALLOWLIST:
                errors.append(f"expected_file outside allowlist: {path}")

    for field in ("instructions", "acceptance"):
        value = data.get(field)
        if not isinstance(value, list) or not value:
            errors.append(f"{field} must be a non-empty list")
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: task_contract.py <task_json_file>")
        return 2
    try:
        data = load(sys.argv[1])
    except (OSError, ValueError) as exc:
        print(f"BLOCK: cannot parse task contract: {exc}")
        return 1

    print("=== TASK CONTRACT ===")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("=== TASK_GATE RESULT ===")
    errors = evaluate(data)
    if errors:
        for e in errors:
            print(f"BLOCK: {e}")
        return 1
    print("PASS: structured task contract valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
