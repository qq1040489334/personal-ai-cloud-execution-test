"""Tests for PERSONAL_AI_REVIEW_ASSISTANT_V0.1.

The review assistant is advisory only: it recommends PASS / FAIL / BLOCKED from
pending-review task data plus execution evidence, never calls ``mark_reviewed``,
never mutates the registry, and is deterministic for a given evidence input.
"""

from __future__ import annotations

import pytest

from personal_ai_execution import (
    BLOCKED,
    FAIL,
    PASS,
    EventSyncRegistry,
    build_review_recommendation,
    list_pending_results,
    list_review_recommendations,
    parse_test_evidence,
    recommend_review,
    reset_default_registry,
)


def execution_result(**overrides) -> dict:
    base = {
        "task_id": "cf-review-probe",
        "status": "success",
        "tests": "12 passed in 3.10s",
        "summary": "review assistant probe",
        "commit": "cafebabe",
        "changed_files": ["src/personal_ai_execution/review_assistant.py"],
    }
    base.update(overrides)
    return base


def reason_codes(recommendation: dict) -> list[str]:
    return [reason["code"] for reason in recommendation["reasons"]]


def test_successful_task_recommends_pass_with_evidence_refs() -> None:
    registry = EventSyncRegistry()
    registry.sync_terminal_result(
        "cf-pass",
        execution_result(task_id="cf-pass"),
        "success",
        artifact_present=True,
        commit_present=True,
        evidence={"name": "execution_result-cf-pass", "id": 11},
    )

    recommendation = registry.recommend_review("cf-pass")

    assert recommendation["task_id"] == "cf-pass"
    assert recommendation["verdict"] == PASS
    assert recommendation["recommendation"] == PASS
    assert recommendation["advisory"] is True
    assert recommendation["requires_human_review"] is True
    assert recommendation["auto_reviewed"] is False
    assert recommendation["auto_mark_reviewed_called"] is False
    assert "EVIDENCE_CONSISTENT" in reason_codes(recommendation)

    refs = {(ref["source"], ref["field"], ref["value"]) for ref in recommendation["evidence_refs"]}
    assert ("canonical", "workflow_conclusion", "success") in refs
    assert ("canonical", "status", PASS) in refs
    assert ("evidence", "artifact_present", True) in refs
    assert ("evidence", "commit_present", True) in refs
    assert ("evidence", "artifact.id", 11) in refs


def test_recommendation_never_auto_reviews_or_mutates() -> None:
    registry = EventSyncRegistry()
    registry.sync_terminal_result("cf-noauto", execution_result(), "success")

    registry.recommend_review("cf-noauto")

    assert registry.get_review_events() == []
    pending = registry.list_pending_results()
    assert [item["task_id"] for item in pending] == ["cf-noauto"]
    assert pending[0]["reviewed"] is False
    assert pending[0]["review_state"] == "pending_review"


def test_workflow_failure_recommends_fail_and_flags_conflict() -> None:
    registry = EventSyncRegistry()
    registry.sync_terminal_result(
        "cf-failure", execution_result(), "failure", artifact_present=True
    )

    recommendation = registry.recommend_review("cf-failure")

    assert recommendation["verdict"] == FAIL
    assert "WORKFLOW_FAILURE" in reason_codes(recommendation)
    assert "CONFLICTING_EVIDENCE" in reason_codes(recommendation)
    assert recommendation["inputs"]["conclusion_authoritative"] is True
    assert recommendation["inputs"]["conclusion_result_mismatch"] is True


def test_blocked_workflow_recommends_blocked_and_flags_conflict() -> None:
    recommendation = build_review_recommendation(
        task_id="cf-cancelled",
        execution_result=execution_result(),
        workflow_conclusion="cancelled",
        artifact_present=True,
        commit_present=True,
    )

    assert recommendation["verdict"] == BLOCKED
    assert "WORKFLOW_BLOCKED" in reason_codes(recommendation)
    assert "CONFLICTING_EVIDENCE" in reason_codes(recommendation)


def test_missing_evidence_recommends_blocked() -> None:
    registry = EventSyncRegistry()
    registry.submit_task("cf-missing", goal="no evidence yet", status=PASS)
    registry._tasks["cf-missing"].update(
        {"normalized_status": PASS, "terminal": True, "result_available": True}
    )

    recommendation = registry.recommend_review("cf-missing")

    assert recommendation["verdict"] == BLOCKED
    assert "INSUFFICIENT_EVIDENCE" in reason_codes(recommendation)
    assert recommendation["inputs"]["normalized_status"] == PASS
    assert {
        (ref["source"], ref["field"], ref["value"])
        for ref in recommendation["evidence_refs"]
    } == {
        ("task", "task_id", "cf-missing"),
        ("registry", "normalized_status", PASS),
    }


def test_no_input_at_all_recommends_blocked() -> None:
    recommendation = build_review_recommendation(None)

    assert recommendation["verdict"] == BLOCKED
    assert "NO_NORMALIZED_STATUS" in reason_codes(recommendation)
    assert recommendation["task_id"] is None


def test_tests_failure_evidence_downgrades_pass_to_fail() -> None:
    recommendation = build_review_recommendation(
        task_id="cf-tests-fail",
        execution_result=execution_result(tests="1 error during teardown"),
        workflow_conclusion="success",
    )

    assert recommendation["verdict"] == FAIL
    assert "TEST_FAILURES" in reason_codes(recommendation)
    assert recommendation["inputs"]["tests"]["has_failures"] is True


def test_missing_expected_files_is_surfaced_and_fails() -> None:
    recommendation = build_review_recommendation(
        task_id="cf-missing-files",
        execution_result=execution_result(
            expected_files=["src/personal_ai_execution/review_assistant.py"],
            changed_files=["hello.py"],
        ),
        workflow_conclusion="success",
    )

    assert recommendation["verdict"] == FAIL
    assert recommendation["inputs"]["missing_expected_files"] == [
        "src/personal_ai_execution/review_assistant.py"
    ]
    assert any(
        ref["source"] == "canonical"
        and ref["field"] == "missing_expected_files"
        and ref["value"] == ["src/personal_ai_execution/review_assistant.py"]
        for ref in recommendation["evidence_refs"]
    )


def test_recommendation_is_deterministic() -> None:
    task = {
        "task_id": "cf-deterministic",
        "status": PASS,
        "normalized_status": PASS,
        "terminal": True,
        "workflow_conclusion": "success",
        "execution_result_json": execution_result(task_id="cf-deterministic"),
        "evidence": {
            "artifact_present": True,
            "commit_present": True,
            "artifact": {"name": "execution_result-cf-deterministic", "id": 5},
        },
    }

    first = build_review_recommendation(task)
    second = build_review_recommendation(task)

    assert first == second
    assert first["fingerprint"] == second["fingerprint"]


def test_unknown_task_raises_key_error() -> None:
    registry = EventSyncRegistry()
    with pytest.raises(KeyError):
        registry.recommend_review("cf-does-not-exist")


def test_list_review_recommendations_covers_pending_tasks() -> None:
    registry = EventSyncRegistry()
    registry.sync_terminal_result("cf-a", execution_result(task_id="cf-a"), "success")
    registry.sync_terminal_result("cf-b", execution_result(task_id="cf-b"), "failure")

    recommendations = registry.list_review_recommendations()

    assert [item["task_id"] for item in recommendations] == ["cf-a", "cf-b"]
    assert [item["verdict"] for item in recommendations] == [PASS, FAIL]


def test_module_level_default_registry_flow() -> None:
    reset_default_registry()
    from personal_ai_execution import event_sync

    event_sync.sync_terminal_result("cf-default", execution_result(), "success")

    recommendation = recommend_review("cf-default")
    assert recommendation["verdict"] == PASS
    assert [item["task_id"] for item in list_review_recommendations()] == [
        "cf-default"
    ]
    assert [item["task_id"] for item in list_pending_results()] == ["cf-default"]


def test_mark_reviewed_contract_still_honoured_after_recommendation() -> None:
    registry = EventSyncRegistry()
    registry.sync_terminal_result("cf-contract", execution_result(), "success")
    registry.recommend_review("cf-contract")

    result = registry.mark_reviewed("cf-contract", "PASS", "human approved")
    assert result["reviewed"] is True
    assert result["review_verdict"] == PASS
    assert registry.list_pending_results() == []


@pytest.mark.parametrize(
    "tests_field,has_failures",
    [
        ("12 passed in 3.10s", False),
        ("3 passed, 0 failed", False),
        ("1 failed, 3 passed", True),
        ("2 errors", True),
        ("failed to collect", True),
    ],
)
def test_parse_test_evidence(tests_field: str, has_failures: bool) -> None:
    parsed = parse_test_evidence({"tests": tests_field})
    assert parsed["present"] is True
    assert parsed["has_failures"] is has_failures


def test_parse_test_evidence_absent() -> None:
    parsed = parse_test_evidence(None)
    assert parsed["present"] is False
    assert parsed["has_failures"] is False
