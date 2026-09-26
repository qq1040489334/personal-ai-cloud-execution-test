"""Tests for TASK_REGISTRY_CLEANUP_V0.1 historical reconciliation.

Reconciliation classifies pre-EVENT_SYNC Task Registry records into
completed-with-result / failed-with-result / blocked-awaiting-inspection /
legacy-orphan without deleting audit history, and stays idempotent. Records that
already flow through EVENT_SYNC are never touched.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from personal_ai_execution import (
    ALREADY_SYNCED,
    BLOCKED,
    BLOCKED_AWAITING_INSPECTION,
    COMPLETED_WITH_RESULT,
    FAIL,
    FAILED_WITH_RESULT,
    IN_PROGRESS,
    LEGACY_ORPHAN,
    PASS,
    REVIEWED,
    EventSyncRegistry,
    classify_record,
    get_reconciliation_events,
    reconcile_historical_tasks,
    reset_default_registry,
)


def backdate(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


def legacy_task(
    registry: EventSyncRegistry,
    task_id: str,
    *,
    status: str = "submitted",
    created_at: str | None = None,
) -> None:
    registry.submit_task(
        task_id,
        goal=f"legacy {task_id}",
        status=status,
        created_at=created_at,
    )


def pending_ids(registry: EventSyncRegistry) -> list[str]:
    return [item["task_id"] for item in registry.list_pending_results()]


def test_legacy_submitted_with_discovered_result_is_completed_with_result() -> None:
    registry = EventSyncRegistry()
    legacy_task(registry, "cf-legacy-pass")

    report = registry.reconcile_historical_tasks(
        discovered_results={
            "cf-legacy-pass": {"status": "passed", "tests": "3 passed"}
        }
    )

    assert report["counts"][COMPLETED_WITH_RESULT] == 1
    assert report["idempotent"] is False
    assert pending_ids(registry) == ["cf-legacy-pass"]
    entry = registry.list_pending_results()[0]
    assert entry["status"] == PASS
    assert entry["normalized_status"] == PASS
    assert entry["review_state"] == "pending_review"
    assert entry["reconciliation_class"] == COMPLETED_WITH_RESULT
    assert entry["legacy"] is True
    assert entry["legacy_original_status"] == "submitted"
    assert registry.get_task_result("cf-legacy-pass")["status"] == PASS


def test_legacy_failure_conclusion_is_failed_with_result() -> None:
    registry = EventSyncRegistry()
    legacy_task(registry, "cf-legacy-fail")

    registry.reconcile_historical_tasks(
        discovered_results={
            "cf-legacy-fail": {"status": "success", "tests": "9 passed"}
        },
        conclusions={"cf-legacy-fail": "failure"},
    )

    entry = registry.list_pending_results()[0]
    assert entry["task_id"] == "cf-legacy-fail"
    assert entry["status"] == FAIL
    assert entry["reconciliation_class"] == FAILED_WITH_RESULT
    assert entry["workflow_conclusion"] == "failure"
    assert entry["evidence"]["task_result"]["conclusion_result_mismatch"] is True


def test_legacy_blocked_without_result_awaits_inspection_not_pending() -> None:
    registry = EventSyncRegistry()
    legacy_task(registry, "cf-legacy-blocked", status="blocked")

    report = registry.reconcile_historical_tasks()

    assert report["counts"][BLOCKED_AWAITING_INSPECTION] == 1
    assert registry.list_pending_results() == []
    record = registry._tasks["cf-legacy-blocked"]
    assert record["reconciliation_class"] == BLOCKED_AWAITING_INSPECTION
    assert record["review_state"] == BLOCKED_AWAITING_INSPECTION
    assert record["requires_inspection"] is True
    assert record["terminal"] is False
    assert record["result_available"] is False
    assert record["status"] == "blocked"


def test_legacy_blocked_with_result_is_discoverable_as_blocked() -> None:
    registry = EventSyncRegistry()
    legacy_task(registry, "cf-legacy-cancelled")

    registry.reconcile_historical_tasks(
        discovered_results={"cf-legacy-cancelled": {"status": "success"}},
        conclusions={"cf-legacy-cancelled": "cancelled"},
    )

    entry = registry.list_pending_results()[0]
    assert entry["status"] == BLOCKED
    assert entry["reconciliation_class"] == BLOCKED_AWAITING_INSPECTION


def test_stale_result_less_record_is_legacy_orphan() -> None:
    registry = EventSyncRegistry()
    legacy_task(registry, "cf-legacy-orphan", created_at=backdate(3600))

    report = registry.reconcile_historical_tasks()

    assert report["counts"][LEGACY_ORPHAN] == 1
    assert registry.list_pending_results() == []
    record = registry._tasks["cf-legacy-orphan"]
    assert record["reconciliation_class"] == LEGACY_ORPHAN
    assert record["orphaned"] is True
    assert record["requires_inspection"] is True
    assert record["status"] == "submitted"
    # the record and its original metadata are preserved for audit
    assert record["goal"] == "legacy cf-legacy-orphan"
    assert record["legacy_original_status"] == "submitted"


def test_fresh_submitted_record_is_left_in_progress() -> None:
    registry = EventSyncRegistry()
    legacy_task(registry, "cf-fresh")

    report = registry.reconcile_historical_tasks()

    assert report["counts"][IN_PROGRESS] == 1
    assert report["skipped"][0]["task_id"] == "cf-fresh"
    assert registry.list_pending_results() == []
    assert registry.get_reconciliation_events("cf-fresh") == []


def test_already_synced_event_sync_record_is_untouched() -> None:
    registry = EventSyncRegistry()
    registry.sync_terminal_result(
        "cf-synced",
        {"task_id": "cf-synced", "status": "success", "tests": "1 passed"},
        "success",
        artifact_present=True,
        evidence={"id": 99},
    )
    before = dict(registry._tasks["cf-synced"])

    report = registry.reconcile_historical_tasks()

    assert report["counts"][ALREADY_SYNCED] == 1
    assert report["skipped"][0]["classification"] == ALREADY_SYNCED
    assert registry.get_reconciliation_events() == []
    after = registry._tasks["cf-synced"]
    assert after["reconciled"] is False
    assert after["evidence"] == before["evidence"]
    assert after["sync_fingerprint"] == before["sync_fingerprint"]
    assert pending_ids(registry) == ["cf-synced"]


def test_reconciliation_is_idempotent_and_no_duplicate_pending_entries() -> None:
    registry = EventSyncRegistry()
    legacy_task(registry, "cf-idem")
    discovered = {"cf-idem": {"status": "passed", "tests": "1 passed"}}

    first = registry.reconcile_historical_tasks(discovered_results=discovered)
    second = registry.reconcile_historical_tasks(discovered_results=discovered)
    third = registry.reconcile_historical_tasks(discovered_results=discovered)

    assert first["idempotent"] is False
    assert second["idempotent"] is True
    assert third["idempotent"] is True
    assert all(item["changed"] is False for item in second["reconciled"])
    assert len(registry.get_reconciliation_events("cf-idem")) == 1
    assert pending_ids(registry) == ["cf-idem"]


def test_multiple_reconciliations_never_duplicate_pending_review() -> None:
    registry = EventSyncRegistry()
    legacy_task(registry, "cf-a", status="blocked")
    legacy_task(registry, "cf-b", created_at=backdate(7200))
    legacy_task(registry, "cf-c")
    registry.sync_terminal_result(
        "cf-synced",
        {"task_id": "cf-synced", "status": "success"},
        "success",
    )
    discovered = {"cf-c": {"status": "passed", "tests": "2 passed"}}

    for _ in range(3):
        registry.reconcile_historical_tasks(discovered_results=discovered)

    ids = pending_ids(registry)
    assert ids == sorted(ids)
    assert ids == ["cf-c", "cf-synced"]
    assert len(ids) == len(set(ids))


def test_reconciliation_preserves_review_events_and_does_not_rereview() -> None:
    registry = EventSyncRegistry()
    legacy_task(registry, "cf-reviewed")
    registry.reconcile_historical_tasks(
        discovered_results={"cf-reviewed": {"status": "passed"}}
    )
    registry.mark_reviewed("cf-reviewed", "PASS", "human verified")

    report = registry.reconcile_historical_tasks(
        discovered_results={"cf-reviewed": {"status": "passed"}}
    )

    assert report["counts"][REVIEWED] == 1
    assert report["skipped"][0]["classification"] == REVIEWED
    assert registry.list_pending_results() == []
    events = registry.get_review_events("cf-reviewed")
    assert len(events) == 1
    assert events[0]["verdict"] == "PASS"
    record = registry._tasks["cf-reviewed"]
    assert record["reviewed"] is True
    assert record["review_verdict"] == "PASS"


def test_reconciliation_preserves_original_evidence_and_commits() -> None:
    registry = EventSyncRegistry()
    legacy_task(registry, "cf-evidence")
    registry._tasks["cf-evidence"]["evidence"] = {"commit": "deadbeef"}
    registry._tasks["cf-evidence"]["execution_result_json"] = {
        "status": "passed",
        "commit": "deadbeef",
    }

    registry.reconcile_historical_tasks()

    record = registry._tasks["cf-evidence"]
    assert record["evidence"]["commit"] == "deadbeef"
    assert record["execution_result_json"]["commit"] == "deadbeef"
    assert record["evidence"]["task_result"]["status"] == PASS
    assert record["reconciled"] is True


def test_reconciled_record_keeps_contract_operations() -> None:
    registry = EventSyncRegistry()
    legacy_task(registry, "cf-contract")
    registry.reconcile_historical_tasks(
        discovered_results={"cf-contract": {"status": "passed"}}
    )

    assert registry.get_task_result("cf-contract")["status"] == PASS
    assert pending_ids(registry) == ["cf-contract"]

    reviewed = registry.mark_reviewed("cf-contract", "PASS")
    assert reviewed["reviewed"] is True
    assert reviewed["idempotent"] is False
    assert pending_ids(registry) == []
    assert registry.list_pending_results() == []


def test_audit_is_dry_run_and_does_not_mutate() -> None:
    registry = EventSyncRegistry()
    legacy_task(registry, "cf-audit", created_at=backdate(3600))

    report = registry.audit_historical_tasks()

    assert report["dry_run"] is True
    assert report["counts"][LEGACY_ORPHAN] == 1
    assert registry._tasks["cf-audit"]["reconciled"] is False
    assert registry.get_reconciliation_events() == []


def test_classify_record_distinguishes_all_legacy_states() -> None:
    now = datetime.now(timezone.utc)
    assert (
        classify_record(
            {"task_id": "a", "synced": True}, now=now
        )["classification"]
        == ALREADY_SYNCED
    )
    assert (
        classify_record(
            {"task_id": "b", "reviewed": True}, now=now
        )["classification"]
        == REVIEWED
    )
    assert (
        classify_record(
            {"task_id": "c", "status": "submitted"}, now=now
        )["classification"]
        == IN_PROGRESS
    )
    assert (
        classify_record(
            {"task_id": "d", "status": "blocked"}, now=now
        )["classification"]
        == BLOCKED_AWAITING_INSPECTION
    )
    assert (
        classify_record(
            {
                "task_id": "e",
                "status": "submitted",
                "created_at": (now - timedelta(hours=1)).isoformat(),
            },
            now=now,
        )["classification"]
        == LEGACY_ORPHAN
    )
    assert (
        classify_record(
            {"task_id": "f", "status": "submitted"},
            execution_result={"status": "passed"},
            now=now,
        )["classification"]
        == COMPLETED_WITH_RESULT
    )


def test_module_level_reconciliation_flow() -> None:
    reset_default_registry()
    from personal_ai_execution import submit_task

    submit_task("cf-module", goal="module", status="submitted")
    report = reconcile_historical_tasks(
        discovered_results={"cf-module": {"status": "passed"}}
    )

    assert report["counts"][COMPLETED_WITH_RESULT] == 1
    assert len(get_reconciliation_events("cf-module")) == 1
