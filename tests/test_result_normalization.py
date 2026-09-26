"""Regression tests for canonical Personal AI Execution V2 normalization.

Workflow conclusion is the authoritative terminal state; execution_result.json
self-reports, artifact presence, and commit presence can never override it.
"""

from __future__ import annotations

import pytest

from personal_ai_execution import (
    BLOCKED,
    FAIL,
    PASS,
    event_sync_retry_allowed,
    get_task_result,
    normalize_conclusion,
    normalize_result,
)


def result(**overrides) -> dict:
    base = {
        "task_id": "cf-normalization-probe",
        "status": "success",
        "tests": "221 passed in 66.20s",
        "commit": "deadbeef",
        "summary": "normalization probe",
    }
    base.update(overrides)
    return base


def test_workflow_failure_overrides_result_success() -> None:
    assessment = normalize_result(
        result(workflow_run_conclusion="failure")
    )
    assert assessment["status"] == FAIL
    assert assessment["self_reported_status"] == PASS
    assert assessment["conclusion_authoritative"] is True
    assert assessment["mismatch"] is True
    assert assessment["authoritative_source"] == "workflow_conclusion"


def test_workflow_cancelled_overrides_result_success() -> None:
    assessment = normalize_result(
        result(workflow_run_conclusion="cancelled")
    )
    assert assessment["status"] == BLOCKED
    assert assessment["self_reported_status"] == PASS
    assert assessment["conclusion_authoritative"] is True
    assert assessment["mismatch"] is True


def test_workflow_timed_out_overrides_result_success() -> None:
    assessment = normalize_result(
        result(workflow_run_conclusion="timed_out")
    )
    assert assessment["status"] == BLOCKED
    assert assessment["self_reported_status"] == PASS
    assert assessment["conclusion_authoritative"] is True
    assert assessment["mismatch"] is True


def test_workflow_success_uses_result_success() -> None:
    assessment = normalize_result(
        result(workflow_run_conclusion="success")
    )
    assert assessment["status"] == PASS
    assert assessment["self_reported_status"] == PASS
    assert assessment["conclusion_authoritative"] is True
    assert assessment["mismatch"] is False


@pytest.mark.parametrize(
    "conclusion",
    [
        "cancelled",
        "canceled",
        "timed_out",
        "failure",
        "startup_failure",
        "action_required",
        "stale",
        "skipped",
        "neutral",
        "some_unknown_conclusion",
    ],
)
def test_non_success_conclusion_never_success(conclusion: str) -> None:
    assert normalize_result(
        result(workflow_run_conclusion=conclusion)
    )["status"] != PASS


def test_artifact_and_commit_presence_do_not_override_conclusion() -> None:
    assessment = normalize_result(
        result(workflow_run_conclusion="failure"),
        artifact_present=True,
        commit_present=True,
    )
    assert assessment["status"] == FAIL
    assert assessment["artifact_present"] is True
    assert assessment["commit_present"] is True


def test_cancelled_is_blocked_even_with_artifact_and_commit() -> None:
    assessment = normalize_result(
        result(workflow_run_conclusion="cancelled"),
        artifact_present=True,
        commit_present=True,
    )
    assert assessment["status"] == BLOCKED


def test_missing_expected_files_downgrade_success_to_fail() -> None:
    assessment = normalize_result(
        result(
            workflow_run_conclusion="success",
            expected_files=["event_sync.py"],
            changed_files=["hello.py", "test_hello.py"],
        )
    )
    assert assessment["status"] == FAIL
    assert assessment["missing_expected_files"] == ["event_sync.py"]


def test_expected_files_produced_stays_success() -> None:
    assessment = normalize_result(
        result(
            workflow_run_conclusion="success",
            expected_files=["event_sync.py"],
            changed_files=["event_sync.py"],
        )
    )
    assert assessment["status"] == PASS
    assert assessment["missing_expected_files"] == []


def test_normalize_conclusion_mapping() -> None:
    assert normalize_conclusion("success") == PASS
    assert normalize_conclusion("failure") == FAIL
    assert normalize_conclusion("cancelled") == BLOCKED
    assert normalize_conclusion("timed_out") == BLOCKED
    assert normalize_conclusion(None) == BLOCKED


def test_no_conclusion_uses_self_report() -> None:
    assessment = normalize_result(result())
    assert assessment["status"] == PASS
    assert assessment["conclusion_authoritative"] is False


def test_missing_result_is_blocked() -> None:
    assessment = normalize_result(None)
    assert assessment["status"] == BLOCKED
    assert assessment["conclusion_authoritative"] is False


def test_get_task_result_exposes_normalized_status() -> None:
    payload = get_task_result(
        "cf-normalization-probe",
        result(workflow_run_conclusion="cancelled"),
    )
    assert payload["status"] == BLOCKED
    assert payload["execution_result_status"] == PASS
    assert payload["workflow_conclusion"] == "cancelled"
    assert payload["conclusion_result_mismatch"] is True
    assert payload["terminal"] is True
    assert "cancelled" in payload["reason"]


def test_get_task_result_success_matches_self_report() -> None:
    payload = get_task_result(
        "cf-normalization-probe",
        result(workflow_run_conclusion="success"),
    )
    assert payload["status"] == PASS
    assert payload["execution_result_status"] == PASS
    assert payload["conclusion_result_mismatch"] is False


def test_event_sync_retry_only_after_terminal_success() -> None:
    assert event_sync_retry_allowed(PASS) is True
    assert event_sync_retry_allowed(FAIL) is False
    assert event_sync_retry_allowed(BLOCKED) is False
