"""POST_TIMEOUT_FIX_GOLDEN_V0.1 production-path verification.

Bounded, no-feature-change regression coverage for the workflow
timeout/truthfulness repair (commit ed3ca64):

* the dispatching job budget must not regress to the 10-minute forced
  cancellation;
* a non-success job must never publish the stale self-reported
  ``execution_result.json`` -- the embedded fallback result is truthful
  (``status == "failure"``);
* the canonical ``get_task_result`` status must always agree with the
  GitHub workflow conclusion and can never be upgraded to PASS by a
  self-report, artifact or commit.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import textwrap
from pathlib import Path
from types import ModuleType

import pytest

from personal_ai_execution import (
    BLOCKED,
    FAIL,
    PASS,
    get_task_result,
    normalize_conclusion,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "agent-dispatch.yml"

OLD_FORCED_CANCELLATION_MINUTES = 10
MINIMUM_ACCEPTABLE_BUDGET_MINUTES = 30

REQUIRED_STEPS_IN_ORDER = (
    "Gate 1 - validate task contract (fail-closed)",
    "Run OpenCode agent (execute task contract)",
    "Gate 2 - scope guard (fail-closed)",
    "Verify tests (independent)",
    "Gate 3 - secret leak check (fail-closed)",
    "Build execution_result.json",
    "Upload execution_result artifact",
)


def workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def job_timeout_minutes() -> int:
    """Return the timeout budget of the dispatching job (before its steps)."""
    before_steps = workflow_text().split("    steps:", 1)[0]
    match = re.search(r"timeout-minutes:\s*(\d+)", before_steps)
    assert match, "agent job has no timeout-minutes budget"
    return int(match.group(1))


def embedded_fallback_source() -> str:
    """Extract the real Python fallback heredoc from the workflow file."""
    lines = workflow_text().splitlines()
    start = next(i for i, line in enumerate(lines) if "<<'PY'" in line)
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip() == "PY":
            break
        body.append(line)
    assert body, "embedded fallback python heredoc not found"
    return textwrap.dedent("\n".join(body))


def run_embedded_fallback(tmp_path: Path, job_status: str, push_outcome: str) -> dict:
    """Execute the workflow's real fallback publisher and return its output."""
    src = tmp_path / "task.json"
    src.write_text(
        json.dumps({"task_id": "cf-post-timeout-fix"}), encoding="utf-8"
    )
    out = tmp_path / "execution_result.json"
    source = embedded_fallback_source()
    argv_backup = list(sys.argv)
    try:
        sys.argv = ["-", str(src), str(out), job_status, push_outcome]
        exec(compile(source, "<workflow-fallback>", "exec"), {"__name__": "__main__"})
    finally:
        sys.argv = argv_backup
    return json.loads(out.read_text(encoding="utf-8"))


def load_build_execution_result() -> ModuleType:
    path = REPO_ROOT / "scripts" / "build_execution_result.py"
    spec = importlib.util.spec_from_file_location("build_execution_result", path)
    assert spec and spec.loader, "cannot load scripts/build_execution_result.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def terminal_result(**overrides) -> dict:
    base = {
        "task_id": "cf-post-timeout-fix",
        "status": "success",
        "tests": "336 passed in 43.70s",
        "commit": "ed3ca64977a1d1a6e562ba3640820730b71a8447",
        "summary": "post-timeout-fix golden verification",
        "changed_files": ["tests/test_post_timeout_fix_golden.py"],
        "expected_files": ["tests/test_post_timeout_fix_golden.py"],
    }
    base.update(overrides)
    return base


# --- workflow budget / truthfulness repair --------------------------------


def test_dispatch_job_budget_is_not_the_old_forced_cancellation() -> None:
    budget = job_timeout_minutes()
    assert budget >= MINIMUM_ACCEPTABLE_BUDGET_MINUTES
    assert budget != OLD_FORCED_CANCELLATION_MINUTES


def test_truthfulness_guard_removes_stale_self_report_before_fallback() -> None:
    text = workflow_text()
    assert 'if [ "$JOB_STATUS" != "success" ]; then' in text
    assert 'rm -f "$RUNNER_TEMP/execution_result.json"' in text


@pytest.mark.parametrize("job_status", ["cancelled", "timed_out", "failure"])
def test_non_success_job_fallback_result_is_truthful(tmp_path, job_status) -> None:
    result = run_embedded_fallback(tmp_path, job_status, "success")
    assert result["status"] == "failure"
    assert result["job_status"] == job_status
    assert result["failure_stage"] == "workflow"
    assert result["task_id"] == "cf-post-timeout-fix"


def test_push_failure_is_attributed_to_the_push_stage(tmp_path) -> None:
    result = run_embedded_fallback(tmp_path, "failure", "failure")
    assert result["status"] == "failure"
    assert result["failure_stage"] == "push"
    assert result["push_outcome"] == "failure"


def test_required_gates_run_in_order() -> None:
    text = workflow_text()
    positions = [text.index(f"name: {step}") for step in REQUIRED_STEPS_IN_ORDER]
    assert positions == sorted(positions)
    assert len(set(positions)) == len(positions)


def test_build_execution_result_is_advisory_self_report_only() -> None:
    source = (REPO_ROOT / "scripts" / "build_execution_result.py").read_text(
        encoding="utf-8"
    )
    assert '"status": "success"' in source
    assert load_build_execution_result() is not None


# --- get_task_result agrees with the workflow conclusion ------------------


@pytest.mark.parametrize(
    ("conclusion", "expected"),
    [
        ("success", PASS),
        ("failure", FAIL),
        ("cancelled", BLOCKED),
        ("canceled", BLOCKED),
        ("timed_out", BLOCKED),
    ],
)
def test_get_task_result_status_agrees_with_workflow_conclusion(
    conclusion: str, expected: str
) -> None:
    payload = get_task_result("cf-post-timeout-fix", terminal_result(), conclusion)
    assert payload["status"] == expected
    assert payload["status"] == normalize_conclusion(conclusion)
    assert payload["workflow_conclusion"] == conclusion
    assert payload["terminal"] is True


def test_self_report_artifact_and_commit_cannot_upgrade_cancelled() -> None:
    payload = get_task_result(
        "cf-post-timeout-fix",
        terminal_result(workflow_run_conclusion="cancelled"),
        artifact_present=True,
        commit_present=True,
    )
    assert payload["execution_result_status"] == PASS
    assert payload["status"] == BLOCKED
    assert payload["conclusion_authoritative"] is True
    assert payload["conclusion_result_mismatch"] is True


def test_post_fix_publication_path_status_agrees_with_conclusion(tmp_path) -> None:
    fallback = run_embedded_fallback(tmp_path, "cancelled", "success")
    fallback["task_id"] = "cf-post-timeout-fix"

    payload = get_task_result("cf-post-timeout-fix", fallback, "cancelled")

    assert payload["execution_result_status"] == FAIL
    assert payload["status"] == BLOCKED
    assert payload["status"] == normalize_conclusion("cancelled")
    assert payload["conclusion_authoritative"] is True


def test_produced_expected_files_keep_success() -> None:
    payload = get_task_result("cf-post-timeout-fix", terminal_result(), "success")
    assert payload["status"] == PASS
    assert payload["missing_expected_files"] == []
