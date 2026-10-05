"""Gate 1 (dispatch path) — validate a structured task contract.

Fail-closed. Accepts either a JSON object or a JSON string containing one.
Run: python scripts/task_contract.py <task_json_file>
"""

from __future__ import annotations

import json
import sys

ALLOWED_RISK = {"LOW", "MEDIUM"}
REQUIRED = ("task_id", "goal", "instructions", "risk_level", "expected_files", "acceptance")
FORBIDDEN_PREFIXES = (".github/workflows/",)
FORBIDDEN_SUBSTRINGS = ("secret", "token", "credential", ".env", ".pem", ".key")

READONLY_MODES = {"readonly", "read_only", "read-only"}
WRITE_MODES = {"write", "readwrite", "read_write", "read-write"}


def task_mode(data) -> str | None:
    """Resolve the explicit execution mode; missing/empty defaults to write.

    Returns ``None`` for an unrecognized mode so callers can fail closed.
    """
    raw = data.get("mode", "write") if isinstance(data, dict) else "write"
    if raw is None or str(raw).strip() == "":
        return "write"
    mode = str(raw).strip().lower()
    if mode in READONLY_MODES:
        return "readonly"
    if mode in WRITE_MODES:
        return "write"
    return None


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

    mode = task_mode(data)
    readonly = mode == "readonly"
    if mode is None:
        errors.append(f"mode not acceptable: {data.get('mode')} (allowed: readonly, write)")

    files = data.get("expected_files")
    if not isinstance(files, list):
        errors.append("expected_files must be a list")
    elif not files:
        if not readonly:
            errors.append("expected_files must be a non-empty list for write mode")
    else:
        for path in files:
            low = str(path).lower()
            if low.startswith(FORBIDDEN_PREFIXES) or any(s in low for s in FORBIDDEN_SUBSTRINGS):
                errors.append(f"forbidden expected_file: {path}")
            elif not isinstance(path, str) or not path.strip():
                errors.append("expected_file must be a non-empty string")
            elif path.startswith("/") or path.startswith("\\") or ".." in path.replace("\\", "/").split("/"):
                errors.append(f"unsafe expected_file path: {path}")

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
