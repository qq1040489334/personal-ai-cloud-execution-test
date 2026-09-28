"""Build execution_result.json (Phase 4 evidence).

Run: python scripts/build_execution_result.py <task_json> <base_rev> <tests_summary> <out_path> <agent_result_json>
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def build_result(task: dict, agent_result: dict, base: str, tests_summary: str) -> dict:
    """Preserve Agent fields; computed compatibility metadata wins conflicts."""
    changed = [line for line in git("diff", "--name-only", base).splitlines() if line.strip()]
    result = dict(agent_result)
    result["agent_result"] = dict(agent_result)
    result.update(
        {
            "status": "success",
            "task_id": task.get("task_id", ""),
            "commit": git("rev-parse", "HEAD").strip(),
            "tests": tests_summary.strip(),
            "changed_files": changed,
            "summary": task.get("goal", ""),
        }
    )
    return result


def load_agent_result(path: str) -> dict:
    """Load the explicit Agent result file; never infer it from console logs."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Agent result must be a JSON object")
    return value


def main() -> int:
    task_path, base, tests_summary, out_path, agent_result_path = sys.argv[1:6]
    task = json.loads(Path(task_path).read_text(encoding="utf-8"))
    if isinstance(task, str):
        task = json.loads(task)
    if not isinstance(task, dict):
        raise ValueError("Task contract must be a JSON object")

    result = build_result(task, load_agent_result(agent_result_path), base, tests_summary)
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
