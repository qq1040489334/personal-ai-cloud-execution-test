"""Canonical Personal AI Execution V2 result normalization.

The GitHub Actions workflow conclusion is the authoritative terminal state.
``execution_result.json`` is advisory only: a self-reported success, the
presence of an artifact, or the presence of a commit can never upgrade a
non-success workflow run. EVENT_SYNC must retry only against the normalized
terminal status produced here.

Mapping (fail-closed):

* ``success``     -> use the execution_result self-reported status.
* ``failure``     -> ``FAIL``.
* ``cancelled``   -> ``BLOCKED``.
* ``timed_out``   -> ``BLOCKED``.
* anything else   -> ``BLOCKED``.
"""

from __future__ import annotations

from typing import Any, Mapping

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
PENDING = "PENDING"

TERMINAL_STATUSES = frozenset({PASS, FAIL, BLOCKED})

WORKFLOW_SUCCESS_CONCLUSIONS = frozenset({"success"})
WORKFLOW_FAILURE_CONCLUSIONS = frozenset({"failure", "startup_failure", "error"})
WORKFLOW_BLOCKED_CONCLUSIONS = frozenset(
    {
        "cancelled",
        "canceled",
        "timed_out",
        "action_required",
        "stale",
        "neutral",
        "skipped",
    }
)

CONCLUSION_FIELDS = (
    "workflow_run_conclusion",
    "workflow_conclusion",
    "conclusion",
    "github_workflow_conclusion",
    "run_conclusion",
)

SUCCESS_STATUSES = frozenset(
    {"success", "succeeded", "pass", "passed", "ok", "complete", "completed"}
)
FAILURE_STATUSES = frozenset(
    {"failure", "failed", "fail", "error", "errored", "timed_out"}
)


def workflow_conclusion(execution_result: Mapping[str, Any] | None) -> str | None:
    """Return the recorded GitHub Actions workflow conclusion, if any."""
    if not isinstance(execution_result, Mapping):
        return None
    for field in CONCLUSION_FIELDS:
        value = execution_result.get(field)
        if value is None:
            continue
        text = str(value).strip().lower()
        if text:
            return text
    return None


def normalize_conclusion(conclusion: str | None) -> str:
    """Map a workflow conclusion to a terminal status, fail-closed."""
    text = str(conclusion).strip().lower() if conclusion is not None else ""
    if text in WORKFLOW_SUCCESS_CONCLUSIONS:
        return PASS
    if text in WORKFLOW_FAILURE_CONCLUSIONS:
        return FAIL
    if text in WORKFLOW_BLOCKED_CONCLUSIONS:
        return BLOCKED
    return BLOCKED


def normalize_self_reported_status(
    execution_result: Mapping[str, Any] | None,
) -> str:
    """Normalize the advisory execution_result self-report to a status."""
    if not isinstance(execution_result, Mapping):
        return BLOCKED
    status = str(execution_result.get("status", "")).strip().lower()
    tests = str(execution_result.get("tests", "")).strip().lower()
    if status in FAILURE_STATUSES or "fail" in tests:
        return FAIL
    if status in SUCCESS_STATUSES or "passed" in tests:
        return PASS
    return BLOCKED


def _missing_expected_files(
    execution_result: Mapping[str, Any] | None,
) -> list[str]:
    """Return declared expected files the run did not actually change."""
    if not isinstance(execution_result, Mapping):
        return []
    expected = execution_result.get("expected_files")
    if not isinstance(expected, list) or not expected:
        return []
    changed = execution_result.get("changed_files")
    if not isinstance(changed, list):
        return [str(path) for path in expected]
    changed_set = {str(path) for path in changed}
    return [str(path) for path in expected if str(path) not in changed_set]


def normalize_result(
    execution_result: Mapping[str, Any] | None,
    workflow_conclusion_value: str | None = None,
    *,
    artifact_present: bool | None = None,
    commit_present: bool | None = None,
) -> dict[str, Any]:
    """Return the authoritative normalization of an execution result.

    ``artifact_present`` / ``commit_present`` are recorded as evidence but are
    never allowed to override a non-success workflow conclusion.
    """
    self_status = normalize_self_reported_status(execution_result)
    conclusion = workflow_conclusion_value
    if conclusion is None:
        conclusion = workflow_conclusion(execution_result)
    missing_expected = _missing_expected_files(execution_result)

    if conclusion is None:
        authoritative = self_status
        source = "self_report"
        authoritative_conclusion = False
        mismatch = False
        reason = (
            "no workflow conclusion recorded; execution_result.json "
            f"status used as-is -> {self_status}"
        )
    else:
        conclusion_status = normalize_conclusion(conclusion)
        authoritative_conclusion = True
        if conclusion_status == PASS:
            authoritative = self_status
            source = "workflow_success+self_report"
            mismatch = False
            reason = (
                "workflow conclusion 'success' agrees with "
                f"execution_result.json -> {self_status}"
            )
        else:
            authoritative = conclusion_status
            source = "workflow_conclusion"
            mismatch = self_status == PASS
            reason = (
                f"workflow conclusion {conclusion!r} is authoritative and "
                f"overrides execution_result.json self-reported {self_status}"
                + (" (CONCLUSION/RESULT MISMATCH)" if mismatch else "")
            )

    if authoritative == PASS and missing_expected:
        authoritative = FAIL
        mismatch = True
        reason = (
            reason
            + "; expected files not produced by the run: "
            + ", ".join(missing_expected)
        )

    return {
        "status": authoritative,
        "terminal": authoritative in TERMINAL_STATUSES,
        "authoritative_status": authoritative,
        "authoritative_source": source,
        "self_reported_status": self_status,
        "workflow_conclusion": conclusion,
        "conclusion_authoritative": authoritative_conclusion,
        "mismatch": mismatch,
        "missing_expected_files": missing_expected,
        "artifact_present": artifact_present,
        "commit_present": commit_present,
        "reason": reason,
    }


def get_task_result(
    task_id: str,
    execution_result: Mapping[str, Any] | None = None,
    workflow_conclusion_value: str | None = None,
    *,
    artifact_present: bool | None = None,
    commit_present: bool | None = None,
) -> dict[str, Any]:
    """Return a result payload whose ``status`` is the normalized terminal state.

    The top-level ``status`` is never the contradictory self-report; the raw
    self-report is exposed separately as ``execution_result_status``.
    """
    assessment = normalize_result(
        execution_result,
        workflow_conclusion_value,
        artifact_present=artifact_present,
        commit_present=commit_present,
    )
    return {
        "task_id": task_id,
        "status": assessment["status"],
        "execution_result_status": assessment["self_reported_status"],
        "workflow_conclusion": assessment["workflow_conclusion"],
        "conclusion_authoritative": assessment["conclusion_authoritative"],
        "conclusion_result_mismatch": assessment["mismatch"],
        "missing_expected_files": assessment["missing_expected_files"],
        "terminal": assessment["terminal"],
        "reason": assessment["reason"],
    }


def event_sync_retry_allowed(status: str) -> bool:
    """EVENT_SYNC may retry only once normalization yields terminal success."""
    return str(status).strip().upper() == PASS
