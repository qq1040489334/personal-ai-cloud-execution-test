"""Phase 5 — simulated GPT acceptance (no real GPT API).

Reads `execution_result.json` and judges completion against the task contract's
acceptance criteria. Deterministic stand-in for GPT verification.

Run: python planner/gpt_verify_sim.py <execution_result.json> <task_contract.json> [--out gpt_verification.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def verify(result: dict, contract: dict) -> dict:
    checks: list[dict] = []

    checks.append({
        "check": "status == success",
        "pass": result.get("status") == "success",
        "detail": result.get("status"),
    })
    checks.append({
        "check": "commit present",
        "pass": bool(result.get("commit")),
        "detail": result.get("commit", ""),
    })
    tests = str(result.get("tests", ""))
    checks.append({
        "check": "tests passed",
        "pass": "passed" in tests and "failed" not in tests,
        "detail": tests,
    })
    expected = set(contract.get("expected_files", []))
    changed = set(result.get("changed_files", []))
    checks.append({
        "check": "changed files within expected_files",
        "pass": bool(changed) and changed.issubset(expected),
        "detail": sorted(changed),
    })
    checks.append({
        "check": "task_id matches",
        "pass": result.get("task_id") == contract.get("task_id"),
        "detail": result.get("task_id", ""),
    })

    completed = all(c["pass"] for c in checks)
    failed = [c["check"] for c in checks if not c["pass"]]
    return {
        "verified_by": "GPT_ACCEPTANCE_SIMULATION",
        "task_id": contract.get("task_id", ""),
        "completed": completed,
        "acceptance_satisfied": completed,
        "checks": checks,
        "next_step": (
            "None. Task accepted; evidence archived."
            if completed
            else "Re-plan or escalate: " + "; ".join(failed)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("result")
    parser.add_argument("contract")
    parser.add_argument("--out", default="gpt_verification.json")
    args = parser.parse_args()

    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    verdict = verify(result, contract)
    Path(args.out).write_text(
        json.dumps(verdict, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
    return 0 if verdict["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
