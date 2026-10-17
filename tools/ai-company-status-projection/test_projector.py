import json
from pathlib import Path

import pytest

from projector import (
    BLOCKED,
    COMPLETED,
    FAILED,
    NOT_APPLICABLE,
    PENDING_REVIEW,
    QUEUED,
    REVIEWED,
    RUNNING,
    UNKNOWN,
    project_tasks,
)

FIXTURE = json.loads(Path(__file__).with_name("fixtures.json").read_text())


def run(records=None, **overrides):
    payload = dict(FIXTURE)
    payload.update(overrides)
    if records is not None:
        payload["records"] = records
    return project_tasks(
        payload["records"],
        source=payload["source"],
        observed_at=payload["observed_at"],
        now=payload["now"],
        ttl_seconds=payload["ttl_seconds"],
        connection_error=payload.get("connection_error"),
    )


def by_id(result):
    return {task["task_id"]: task for task in result["tasks"]}


def test_runtime_and_review_state_semantics():
    tasks = by_id(run())
    assert tasks["cf-completed-unreviewed"]["runtime_state"] == COMPLETED
    assert tasks["cf-completed-unreviewed"]["review_state"] == PENDING_REVIEW
    assert tasks["cf-reviewed"]["runtime_state"] == COMPLETED
    assert tasks["cf-reviewed"]["review_state"] == REVIEWED
    assert tasks["cf-reviewed"]["review_verdict"] == "PASS"
    assert tasks["cf-running"]["runtime_state"] == RUNNING
    assert tasks["cf-running"]["review_state"] == NOT_APPLICABLE
    assert tasks["cf-queued"]["runtime_state"] == QUEUED
    assert tasks["cf-failed"]["runtime_state"] == FAILED
    assert tasks["cf-failed"]["review_state"] == PENDING_REVIEW
    assert tasks["cf-blocked"]["runtime_state"] == BLOCKED
    assert tasks["cf-blocked"]["blocker"] == "workflow_timed_out"


def test_completed_is_not_acceptance_pass():
    task = by_id(run())["cf-completed-unreviewed"]
    assert task["runtime_state"] == COMPLETED
    assert "acceptance" not in task
    assert "status" not in task
    assert task["review_state"] == PENDING_REVIEW


def test_missing_run_evidence_is_unknown():
    task = by_id(run())["cf-unverified-self-report"]
    assert task["runtime_state"] == UNKNOWN
    assert task["blocker"] == "unverified_self_report"
    assert task["review_state"] == NOT_APPLICABLE


def test_duplicate_task_id_is_counted_once_and_authoritative_record_wins():
    result = run()
    tasks = by_id(result)
    duplicate = tasks["cf-duplicate"]
    assert duplicate["runtime_state"] == COMPLETED
    assert duplicate["review_state"] == PENDING_REVIEW
    assert duplicate["duplicate_count"] == 2
    assert result["counts"]["duplicate_records"] == 1
    assert result["counts"]["total_unique_tasks"] == 10
    assert [d["task_id"] for d in result["duplicates"]] == ["cf-duplicate"]


def test_parent_child_does_not_double_count():
    result = run()
    tasks = by_id(result)
    assert tasks["cf-child"]["parent_task_id"] == "cf-parent"
    assert tasks["cf-child"]["runtime_state"] == FAILED
    assert tasks["cf-parent"]["runtime_state"] == COMPLETED
    assert result["counts"]["total_unique_tasks"] == 10
    assert sum(result["counts"]["runtime_state"].values()) == 10


def test_missing_task_id_is_skipped_not_invented():
    result = run()
    assert "record without task_id skipped" in result["warnings"]
    assert result["complete"] is False
    assert result["counts"]["raw_records"] == 12
    assert result["counts"]["total_unique_tasks"] == 10


def test_stale_observation_forces_unknown_but_keeps_last_known():
    result = run(observed_at="2026-10-17T10:00:00Z", now="2026-10-17T12:01:00Z")
    tasks = by_id(result)
    task = tasks["cf-completed-unreviewed"]
    assert result["complete"] is False
    assert result["batch_blocker"] == "stale_observation"
    assert task["runtime_state"] == UNKNOWN
    assert task["last_known_runtime_state"] == COMPLETED
    assert task["freshness"] == "stale"
    assert task["observed_at"] == "2026-10-17T10:00:00Z"
    assert tasks["cf-reviewed"]["review_state"] == REVIEWED
    assert tasks["cf-completed-unreviewed"]["review_state"] == UNKNOWN


def test_missing_observed_at_forces_unknown_without_using_now():
    result = run(observed_at=None)
    tasks = by_id(result)
    assert result["complete"] is False
    assert result["batch_blocker"] == "missing_observed_at"
    assert result["observed_at"] is None
    assert all(task["runtime_state"] == UNKNOWN for task in tasks.values())
    assert all(task["observed_at"] is None for task in tasks.values())


def test_connection_failure_is_unknown():
    result = run(connection_error={"code": "CONNECTION_FAILED"})
    assert result["complete"] is False
    assert result["batch_blocker"] == "connection_failure"
    assert all(task["runtime_state"] == UNKNOWN for task in result["tasks"])
    assert all(task["blocker"] == "connection_failure" for task in result["tasks"])
    assert all(task["review_state"] == UNKNOWN for task in result["tasks"])


def test_future_observation_is_invalid():
    result = run(observed_at="2026-10-18T00:00:00Z", now="2026-10-17T12:01:00Z")
    assert result["complete"] is False
    assert result["batch_blocker"] == "observed_at_in_future"
    assert all(task["runtime_state"] == UNKNOWN for task in result["tasks"])


def test_source_event_time_is_never_the_local_now():
    task = by_id(run())["cf-completed-unreviewed"]
    assert task["last_source_event_at"] == "2026-10-17T11:58:00Z"
    assert task["observed_at"] == "2026-10-17T12:00:00Z"
    assert task["observed_at"] != task["last_source_event_at"]


def test_conflicting_parent_in_duplicates_is_omitted():
    records = [
        {
            "task_id": "cf-x",
            "parent_task_id": "cf-a",
            "workflow_conclusion": "success",
            "execution_status": "PASS",
            "updated_at": "2026-10-17T11:58:00Z",
        },
        {
            "task_id": "cf-x",
            "parent_task_id": "cf-b",
            "status": "running",
            "updated_at": "2026-10-17T11:59:00Z",
        },
    ]
    result = run(records=records)
    task = result["tasks"][0]
    assert task["parent_task_id"] is None
    assert any("conflicting parent_task_id" in w for w in result["warnings"])


def test_self_parent_is_not_reported_as_lineage():
    records = [
        {
            "task_id": "cf-self",
            "parent_task_id": "cf-self",
            "status": "queued",
            "updated_at": "2026-10-17T11:59:00Z",
        }
    ]
    task = run(records=records)["tasks"][0]
    assert task["parent_task_id"] is None


def test_empty_fresh_pending_results_is_batch_complete_not_full_idle():
    result = run(records=[])
    assert result["complete"] is True
    assert result["batch_complete"] is True
    assert result["counts"]["total_unique_tasks"] == 0
    assert result["batch_blocker"] is None
    assert result["scope"] == "pending_results_subset"
    assert result["full_task_coverage"] is False
    assert result["coverage"]["batch_complete"] is True
    assert result["coverage"]["full_task_coverage"] is False
    assert result["coverage"]["empty_response_is_full_idle"] is False
    assert any("not proof" in warning for warning in result["warnings"])


def test_declared_full_task_source_can_claim_full_coverage():
    result = run(records=[], source="worker.list_tasks")
    assert result["scope"] == "full_task_set"
    assert result["full_task_coverage"] is True
    assert result["coverage"]["full_task_coverage"] is True
    assert result["coverage"]["empty_response_is_full_idle"] is True
    assert not any("not proof" in warning for warning in result["warnings"])


def test_now_and_ttl_are_required():
    with pytest.raises(ValueError):
        project_tasks([], source="worker.list_pending_results", observed_at="2026-10-17T12:00:00Z", now=None, ttl_seconds=300)
    with pytest.raises(ValueError):
        project_tasks([], source="worker.list_pending_results", observed_at="2026-10-17T12:00:00Z", now="2026-10-17T12:01:00Z", ttl_seconds=None)


def _one(record):
    return run(records=[record])["tasks"][0]


def test_freshness_exactly_at_ttl_is_fresh():
    result = run(
        records=[{"task_id": "cf-b", "status": "queued", "updated_at": "2026-10-17T11:58:00Z"}],
        observed_at="2026-10-17T11:56:00Z",
        now="2026-10-17T12:01:00Z",
    )
    assert result["tasks"][0]["freshness"] == "fresh"
    assert result["batch_blocker"] is None


def test_freshness_just_over_ttl_is_stale():
    result = run(
        records=[{"task_id": "cf-b", "status": "queued", "updated_at": "2026-10-17T11:58:00Z"}],
        observed_at="2026-10-17T11:55:00Z",
        now="2026-10-17T12:01:00Z",
    )
    assert result["tasks"][0]["freshness"] == "stale"
    assert result["batch_blocker"] == "stale_observation"


def test_future_observation_within_clock_skew_is_tolerated():
    result = run(
        records=[{"task_id": "cf-b", "status": "queued", "updated_at": "2026-10-17T11:58:00Z"}],
        observed_at="2026-10-17T12:01:30Z",
        now="2026-10-17T12:01:00Z",
    )
    assert result["tasks"][0]["freshness"] == "fresh"


def test_missing_source_event_time_does_not_invent_a_time():
    task = _one({"task_id": "cf-no-time", "status": "queued"})
    assert task["last_source_event_at"] is None
    assert task["runtime_state"] == QUEUED
    assert task["freshness"] == "fresh"


def test_missing_observed_at_preserves_existing_reviewed_verdict():
    result = run(observed_at=None)
    reviewed = by_id(result)["cf-reviewed"]
    assert reviewed["runtime_state"] == UNKNOWN
    assert reviewed["review_state"] == REVIEWED
    assert reviewed["review_verdict"] == "PASS"


def test_workflow_success_does_not_mask_execution_failure():
    records = [
        {
            "task_id": "cf-contradiction",
            "status": "FAIL",
            "normalized_status": "FAIL",
            "workflow_conclusion": "success",
            "execution_status": "FAIL",
            "result_available": True,
            "updated_at": "2026-10-17T11:58:00Z",
        }
    ]
    task = run(records=records)["tasks"][0]
    assert task["runtime_state"] == FAILED
    assert task["evidence"] == "conflict"
    assert task["blocker"] == "workflow_success_execution_failure"
    assert task["review_state"] == PENDING_REVIEW


def test_newer_execution_failure_is_not_masked_by_older_workflow_success_duplicate():
    records = [
        {
            "task_id": "cf-cross-record-failure",
            "workflow_conclusion": "success",
            "updated_at": "2026-10-17T11:50:00Z",
        },
        {
            "task_id": "cf-cross-record-failure",
            "execution_status": "FAIL",
            "updated_at": "2026-10-17T11:59:00Z",
        },
    ]
    task = run(records=records)["tasks"][0]
    assert task["runtime_state"] == FAILED
    assert task["evidence"] == "execution_status"
    assert task["last_source_event_at"] == "2026-10-17T11:59:00Z"


def test_workflow_success_with_blocked_execution_is_not_green():
    records = [
        {
            "task_id": "cf-blocked-conflict",
            "workflow_conclusion": "success",
            "execution_status": "BLOCKED",
            "updated_at": "2026-10-17T11:58:00Z",
        }
    ]
    task = run(records=records)["tasks"][0]
    assert task["runtime_state"] == BLOCKED
    assert task["evidence"] == "conflict"
    assert task["blocker"] == "workflow_success_execution_blocked"


def test_review_and_runtime_are_independent_dimensions():
    records = [
        {
            "task_id": "cf-reviewed-failure",
            "status": "FAIL",
            "execution_status": "FAIL",
            "workflow_conclusion": "failure",
            "result_available": True,
            "reviewed": True,
            "review_verdict": "FAIL",
            "updated_at": "2026-10-17T11:58:00Z",
        }
    ]
    task = run(records=records)["tasks"][0]
    assert task["runtime_state"] == FAILED
    assert task["review_state"] == REVIEWED
    assert task["review_verdict"] == "FAIL"


def test_review_verdict_does_not_upgrade_unverified_runtime():
    records = [
        {
            "task_id": "cf-reviewed-self-report",
            "status": "success",
            "reviewed": True,
            "review_verdict": "PASS",
            "updated_at": "2026-10-17T11:58:00Z",
        }
    ]
    task = run(records=records)["tasks"][0]
    assert task["runtime_state"] == UNKNOWN
    assert task["blocker"] == "unverified_self_report"
    assert task["review_state"] == REVIEWED
    assert task["review_verdict"] == "PASS"


def test_duplicate_equal_evidence_prefers_newer_source_event():
    records = [
        {"task_id": "cf-order", "status": "running", "updated_at": "2026-10-17T11:53:00Z"},
        {"task_id": "cf-order", "status": "queued", "updated_at": "2026-10-17T11:59:00Z"},
    ]
    result = run(records=records)
    task = result["tasks"][0]
    assert task["runtime_state"] == QUEUED
    assert task["duplicate_count"] == 2
    assert task["last_source_event_at"] == "2026-10-17T11:59:00Z"


def test_duplicate_merges_newer_review_verdict_independently_of_runtime_evidence():
    records = [
        {
            "task_id": "cf-merge",
            "workflow_conclusion": "success",
            "execution_status": "PASS",
            "result_available": True,
            "reviewed": False,
            "review_state": "pending_review",
            "updated_at": "2026-10-17T11:50:00Z",
        },
        {
            "task_id": "cf-merge",
            "execution_status": "PASS",
            "result_available": True,
            "reviewed": True,
            "review_verdict": "FAIL",
            "review_state": "reviewed",
            "updated_at": "2026-10-17T11:59:00Z",
        },
    ]
    task = run(records=records)["tasks"][0]
    assert task["runtime_state"] == COMPLETED
    assert task["evidence"] == "workflow_conclusion"
    assert task["review_state"] == REVIEWED
    assert task["review_verdict"] == "FAIL"
    assert task["last_source_event_at"] == "2026-10-17T11:59:00Z"
    assert task["duplicate_count"] == 2


def test_conflicting_review_verdicts_without_ordering_evidence_are_conflict():
    records = [
        {
            "task_id": "cf-review-tie",
            "execution_status": "PASS",
            "reviewed": True,
            "review_verdict": "PASS",
        },
        {
            "task_id": "cf-review-tie",
            "execution_status": "PASS",
            "reviewed": True,
            "review_verdict": "FAIL",
        },
    ]
    task = run(records=records)["tasks"][0]
    assert task["runtime_state"] == COMPLETED
    assert task["review_state"] == "conflict"
    assert task["review_blocker"] == "conflicting_review_evidence"
    assert "review_verdict" not in task
    assert any(conflict.startswith("review:") for conflict in task["conflicts"])


def test_same_rank_and_time_success_failure_duplicates_are_conflict():
    records = [
        {
            "task_id": "cf-runtime-tie",
            "execution_status": "PASS",
            "run_id": "run-a",
            "updated_at": "2026-10-17T11:58:00Z",
        },
        {
            "task_id": "cf-runtime-tie",
            "execution_status": "FAIL",
            "run_id": "run-b",
            "updated_at": "2026-10-17T11:58:00Z",
        },
    ]
    task = run(records=records)["tasks"][0]
    assert task["runtime_state"] == UNKNOWN
    assert task["evidence"] == "conflict"
    assert task["blocker"] == "conflicting_runtime_evidence"
    assert any(conflict.startswith("runtime:") for conflict in task["conflicts"])


def test_sequence_evidence_resolves_same_time_duplicate_without_lexical_tiebreak():
    records = [
        {
            "task_id": "cf-sequence",
            "execution_status": "PASS",
            "run_sequence": 1,
            "updated_at": "2026-10-17T11:58:00Z",
        },
        {
            "task_id": "cf-sequence",
            "execution_status": "FAIL",
            "run_sequence": 2,
            "updated_at": "2026-10-17T11:58:00Z",
        },
    ]
    task = run(records=records)["tasks"][0]
    assert task["runtime_state"] == FAILED
    assert task["blocker"] is None


def test_future_source_event_cannot_win_duplicate_selection():
    records = [
        {
            "task_id": "cf-future-event",
            "execution_status": "FAIL",
            "updated_at": "2026-10-17T11:50:00Z",
        },
        {
            "task_id": "cf-future-event",
            "execution_status": "PASS",
            "updated_at": "2026-10-18T00:00:00Z",
        },
    ]
    task = run(records=records)["tasks"][0]
    assert task["runtime_state"] == FAILED
    assert task["last_source_event_at"] == "2026-10-17T11:50:00Z"


@pytest.mark.parametrize(
    "ttl",
    [float("nan"), float("inf"), float("-inf"), -1, -0.5],
)
def test_invalid_ttl_is_rejected(ttl):
    with pytest.raises(ValueError):
        project_tasks(
            [],
            source="worker.list_pending_results",
            observed_at="2026-10-17T12:00:00Z",
            now="2026-10-17T12:01:00Z",
            ttl_seconds=ttl,
        )
