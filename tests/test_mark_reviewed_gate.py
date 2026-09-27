"""Tests for PERSONAL_AI_MARK_REVIEWED_GATE_V0.2.

``mark_reviewed`` must not be able to bypass task completion: review closure is
allowed only for a task with an authoritative terminal execution state and a
validated result whose ``task_id`` matches. Submitted / pending / in-progress /
unknown / missing-result / mismatched-result tasks are rejected fail-closed, the
review event and its reason are preserved, an identical retry is idempotent and a
conflicting retry is rejected.
"""

from __future__ import annotations

import pytest

from personal_ai_execution import (
    BLOCKED,
    ELIGIBLE_REASON_CODE,
    FAIL,
    PASS,
    EventSyncRegistry,
    reset_default_registry,
    review_eligibility,
    validated_review_result,
)

TASK_ID = "cf-mark-gate"


def execution_result(task_id: str = TASK_ID, **overrides) -> dict:
    base = {
        "task_id": task_id,
        "status": "success",
        "tests": "5 passed in 1.20s",
        "summary": "mark-reviewed gate probe",
        "commit": "cafebabe",
        "changed_files": ["src/personal_ai_execution/event_sync.py"],
    }
    base.update(overrides)
    return base


def synced(conclusion: str = "success", task_id: str = TASK_ID) -> EventSyncRegistry:
    registry = EventSyncRegistry()
    registry.sync_terminal_result(
        task_id,
        execution_result(task_id),
        conclusion,
        artifact_present=True,
        commit_present=True,
    )
    return registry


# -- rejection paths --------------------------------------------------------
@pytest.mark.parametrize(
    "status", ["submitted", "pending", "in_progress", "queued", "running", "unknown"]
)
def test_non_terminal_submitted_tasks_cannot_be_reviewed(status: str) -> None:
    registry = EventSyncRegistry()
    registry.submit_task(TASK_ID, goal="not done", status=status)

    with pytest.raises(ValueError) as excinfo:
        registry.mark_reviewed(TASK_ID, "PASS")

    assert "NON_TERMINAL" in str(excinfo.value)
    record = registry._tasks[TASK_ID]
    assert record["reviewed"] is False
    assert record["review_verdict"] is None
    assert registry.get_review_events(TASK_ID) == []


def test_non_terminal_sync_is_not_created_or_reviewable() -> None:
    registry = EventSyncRegistry()
    info = registry.sync_terminal_result(TASK_ID, {"status": "running"}, None)

    assert info["synced"] is False
    assert TASK_ID not in registry._tasks
    with pytest.raises(KeyError):
        registry.mark_reviewed(TASK_ID, "PASS")


def test_missing_result_cannot_be_reviewed_even_if_terminal() -> None:
    registry = synced()
    record = registry._tasks[TASK_ID]
    record["evidence"].pop("task_result")

    assessment = review_eligibility(record)

    assert assessment["eligible"] is False
    assert assessment["reason_code"] == "MISSING_RESULT"
    with pytest.raises(ValueError) as excinfo:
        registry.mark_reviewed(TASK_ID, "PASS")
    assert "MISSING_RESULT" in str(excinfo.value)


def test_unvalidated_result_available_flag_cannot_bypass() -> None:
    registry = synced()
    registry._tasks[TASK_ID]["result_available"] = False

    with pytest.raises(ValueError) as excinfo:
        registry.mark_reviewed(TASK_ID, "PASS")
    assert "RESULT_UNAVAILABLE" in str(excinfo.value)


def test_mismatched_result_task_id_is_rejected() -> None:
    registry = synced()
    registry._tasks[TASK_ID]["evidence"]["task_result"]["task_id"] = "cf-someone-else"

    assessment = review_eligibility(registry._tasks[TASK_ID])

    assert assessment["eligible"] is False
    assert assessment["reason_code"] == "RESULT_TASK_ID_MISMATCH"
    assert validated_review_result(registry._tasks[TASK_ID]) is None
    with pytest.raises(ValueError) as excinfo:
        registry.mark_reviewed(TASK_ID, "PASS")
    assert "RESULT_TASK_ID_MISMATCH" in str(excinfo.value)


def test_result_status_mismatch_is_rejected() -> None:
    registry = synced()
    registry._tasks[TASK_ID]["normalized_status"] = FAIL

    with pytest.raises(ValueError) as excinfo:
        registry.mark_reviewed(TASK_ID, "PASS")
    assert "RESULT_STATUS_MISMATCH" in str(excinfo.value)


def test_non_terminal_result_status_is_rejected() -> None:
    registry = synced()
    result = registry._tasks[TASK_ID]["evidence"]["task_result"]
    result["status"] = "PENDING"

    with pytest.raises(ValueError) as excinfo:
        registry.mark_reviewed(TASK_ID, "PASS")
    assert "NON_TERMINAL_RESULT" in str(excinfo.value)


def test_unknown_task_and_invalid_verdict_rejected() -> None:
    registry = synced()
    with pytest.raises(KeyError):
        registry.mark_reviewed("cf-absent", "PASS")
    with pytest.raises(ValueError):
        registry.mark_reviewed(TASK_ID, "MAYBE")


# -- eligible paths ---------------------------------------------------------
@pytest.mark.parametrize(
    "conclusion,expected_status",
    [("success", PASS), ("failure", FAIL), ("cancelled", BLOCKED)],
)
@pytest.mark.parametrize("verdict", [PASS, FAIL, BLOCKED])
def test_eligible_terminal_validated_task_accepts_each_verdict(
    conclusion: str, expected_status: str, verdict: str
) -> None:
    registry = synced(conclusion)

    result = registry.mark_reviewed(TASK_ID, verdict, "human reviewed")

    assert result["reviewed"] is True
    assert result["review_verdict"] == verdict
    assert result["reviewed_at"]
    assert result["review_note"] == "human reviewed"
    assert result["idempotent"] is False
    assert registry.list_pending_results() == []

    events = registry.get_review_events(TASK_ID)
    assert len(events) == 1
    assert events[0]["verdict"] == verdict
    assert events[0]["action"] == "review"
    assert events[0]["note"] == "human reviewed"
    assert events[0]["reviewed_status"] == expected_status
    assert events[0]["reason_code"] == ELIGIBLE_REASON_CODE
    assert events[0]["result_task_id"] == TASK_ID


def test_review_event_and_reason_are_preserved() -> None:
    registry = synced("failure")

    result = registry.mark_reviewed(TASK_ID, FAIL, "regression")

    record = registry._tasks[TASK_ID]
    assert record["review_reason_code"] == ELIGIBLE_REASON_CODE
    assert record["review_reason"] == (
        f"task {TASK_ID} has terminal status FAIL and a validated result whose "
        "task_id matches"
    )
    event = result["review_event"]
    assert event["reason"] == record["review_reason"]
    assert event["reason_code"] == ELIGIBLE_REASON_CODE
    assert registry.get_review_events(TASK_ID)[0] == event


def test_identical_retry_is_idempotent_and_single_event() -> None:
    registry = synced()

    first = registry.mark_reviewed(TASK_ID, PASS, "same")
    second = registry.mark_reviewed(TASK_ID, PASS, "same")

    assert first["idempotent"] is False
    assert second["idempotent"] is True
    assert second["review_verdict"] == PASS
    assert len(registry.get_review_events(TASK_ID)) == 1


def test_conflicting_retry_is_fail_closed() -> None:
    registry = synced()
    registry.mark_reviewed(TASK_ID, PASS, "approved")

    with pytest.raises(ValueError) as excinfo:
        registry.mark_reviewed(TASK_ID, FAIL, "changed mind")

    assert "conflicting" in str(excinfo.value).lower()
    record = registry._tasks[TASK_ID]
    assert record["review_verdict"] == PASS
    assert record["review_note"] == "approved"
    events = registry.get_review_events(TASK_ID)
    assert len(events) == 1
    assert events[0]["verdict"] == PASS


def test_rejected_review_does_not_mutate_or_close_pending() -> None:
    registry = EventSyncRegistry()
    registry.submit_task(TASK_ID, goal="in flight", status="in_progress")

    with pytest.raises(ValueError):
        registry.mark_reviewed(TASK_ID, PASS)

    record = registry._tasks[TASK_ID]
    assert record["reviewed"] is False
    assert record["review_state"] is None
    assert registry.get_review_events() == []
    assert [item["task_id"] for item in registry.list_pending_results()] == []


def test_review_eligibility_helper_is_structured() -> None:
    registry = synced("cancelled")
    eligible = review_eligibility(registry._tasks[TASK_ID])
    assert eligible["eligible"] is True
    assert eligible["reason_code"] == ELIGIBLE_REASON_CODE
    assert eligible["status"] == BLOCKED
    assert eligible["result_task_id"] == TASK_ID

    submitted = EventSyncRegistry()
    submitted.submit_task("cf-x", status="submitted")
    ineligible = review_eligibility(submitted._tasks["cf-x"])
    assert ineligible["eligible"] is False
    assert ineligible["reason_code"] == "NON_TERMINAL"


def test_module_level_default_registry_flow() -> None:
    reset_default_registry()
    from personal_ai_execution import event_sync, list_pending_results

    event_sync.sync_terminal_result(TASK_ID, execution_result(), "success")
    assert [item["task_id"] for item in list_pending_results()] == [TASK_ID]

    reviewed = event_sync.mark_reviewed(TASK_ID, PASS, "module flow")
    assert reviewed["reviewed"] is True
    assert list_pending_results() == []
