"""Build execution_result.json (Phase 4 evidence).

Run: python scripts/build_execution_result.py <task_json> <base_rev> <tests_summary> <out_path>
"""

from __future__ import annotations

import json
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def main() -> int:
    task_path, base, tests_summary, out_path = sys.argv[1:5]
    task = json.loads(open(task_path, encoding="utf-8").read())
    if isinstance(task, str):
        task = json.loads(task)

    changed = [line for line in git("diff", "--name-only", base).splitlines() if line.strip()]
    result = {
        "status": "success",
        "task_id": task.get("task_id", ""),
        "commit": git("rev-parse", "HEAD").strip(),
        "tests": tests_summary.strip(),
        "changed_files": changed,
        "summary": task.get("goal", ""),
    }
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
