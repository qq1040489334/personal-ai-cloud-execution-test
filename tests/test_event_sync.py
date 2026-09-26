"""Tests for the canonical EVENT_SYNC terminal-result synchronization.

EVENT_SYNC ingests a terminal GitHub workflow result and makes it discoverable
through ``list_pending_results`` exactly once, preserving the workflow
authoritative normalized status. It never auto-reviews and never auto-submits.
"""

from __future__ import annotations

import pytest

from personal_ai_execution import (
    BLOCKED,
    FAIL,
    GOLDEN_TASK_ID,
    PASS,
    EventSyncRegistry,
    event_sync,
    list_pending_results,
    reset_default_registry,
)


def terminal_result(**overrides) -> dict:
    base = {
        "task_id": "cf-event-sync-probe",
        "status": "success",
        "tests": "12 passed in 3.10s",
        "summary": "event sync probe",
        "commit": "cafebabe",
        "changed_files": ["src/personal_ai_execution/event_sync.py"],
    }
    base.update(overrides)
    return base


def pending_ids(registry: EventSyncRegistry) -> list[str]:
    return [item["task_id"] for item in registry.list_pending_results()]


def test_terminal_success_discovered_without_get_task_result() -> None:
    registry = EventSyncRegistry()

    info = registry.sync_terminal_result(
        "cf-success",
        terminal_result(),
        "success",
        artifact_present=True,
        commit_present=True,
        evidence={"name": "execution_result-cf-success", "id": 42},
    )

    assert info["synced"] is True
    assert info["status"] == PASS
    assert info["created"] is True

    pending = registry.list_pending_results()
    assert pending_ids(registry) == ["cf-success"]
    entry = pending[0]
    assert entry["status"] == PASS
    assert entry["normalized_status"] == PASS
    assert entry["review_state"] == "pending_review"
    assert entry["terminal"] is True
    assert entry["requires_review"] is True
    assert entry["reviewed"] is False


def test_workflow_failure_propagates_over_self_reported_success() -> None:
    registry = EventSyncRegistry()
    info = registry.sync_terminal_result(
        "cf-failure", terminal_result(), "failure"
    )

    assert info["status"] == FAIL
    assert info["task_result"]["execution_result_status"] == PASS
    assert info["task_result"]["conclusion_result_mismatch"] is True
    assert info["task_result"]["conclusion_authoritative"] is True

    entry = registry.list_pending_results()[0]
    assert entry["task_id"] == "cf-failure"
    assert entry["status"] == FAIL
    assert entry["workflow_conclusion"] == "failure"


@pytest.mark.parametrize("conclusion", ["cancelled", "timed_out", "skipped"])
def test_cancelled_and_blocked_propagate(conclusion: str) -> None:
    registry = EventSyncRegistry()
    info = registry.sync_terminal_result(
        f"cf-{conclusion}", terminal_result(), conclusion
    )

    assert info["status"] == BLOCKED
    assert info["workflow_conclusion"] == conclusion

    entry = registry.list_pending_results()[0]
    assert entry["status"] == BLOCKED
    assert entry["normalized_status"] == BLOCKED


def test_repeated_sync_is_idempotent_and_never_duplicates_pending() -> None:
    registry = EventSyncRegistry()
    first = registry.sync_terminal_result("cf-idem", terminal_result(), "success")
    second = registry.sync_terminal_result("cf-idem", terminal_result(), "success")

    assert first["idempotent"] is False
    assert second["idempotent"] is True
    assert second["duplicate"] is True
    assert second["created"] is False

    assert pending_ids(registry).count("cf-idem") == 1
    assert len(registry.get_sync_events("cf-idem")) == 1


def test_repeated_sync_does_not_duplicate_review_events() -> None:
    registry = EventSyncRegistry()
    registry.sync_terminal_result("cf-review", terminal_result(), "success")
    registry.sync_terminal_result("cf-review", terminal_result(), "success")

    first = registry.mark_reviewed("cf-review", "PASS", "golden review")
    second = registry.mark_reviewed("cf-review", "PASS", "golden review")

    assert first["idempotent"] is False
    assert second["idempotent"] is True
    assert len(registry.get_review_events("cf-review")) == 1
    assert registry.list_pending_results() == []


def test_mark_reviewed_does_not_auto_submit_or_auto_review() -> None:
    registry = EventSyncRegistry()
    registry.sync_terminal_result("cf-manual", terminal_result(), "success")

    assert registry.list_pending_results()[0]["reviewed"] is False
    assert len(registry.get_review_events()) == 0

    registry.mark_reviewed("cf-manual", "PASS")
    assert [item["task_id"] for item in registry._tasks.values()] == ["cf-manual"]


def test_non_terminal_event_is_not_synchronized() -> None:
    registry = EventSyncRegistry()
    info = registry.sync_terminal_result("cf-inflight", {"status": "running"}, None)

    assert info["synced"] is False
    assert info["status"] is None
    assert "no workflow conclusion" in info["reason"]
    assert registry.list_pending_results() == []


def test_missing_expected_files_downgrades_success() -> None:
    registry = EventSyncRegistry()
    info = registry.sync_terminal_result(
        "cf-missing",
        terminal_result(
            expected_files=["src/personal_ai_execution/event_sync.py"],
            changed_files=["hello.py"],
        ),
        "success",
    )

    assert info["status"] == FAIL
    assert info["task_result"]["missing_expected_files"] == [
        "src/personal_ai_execution/event_sync.py"
    ]
    assert registry.list_pending_results()[0]["status"] == FAIL


def test_golden_task_is_discoverable_and_verifiable() -> None:
    registry = EventSyncRegistry()
    registry.sync_terminal_result(
        GOLDEN_TASK_ID,
        terminal_result(task_id=GOLDEN_TASK_ID),
        "success",
        artifact_present=True,
        commit_present=True,
        evidence={"name": f"execution_result-{GOLDEN_TASK_ID}", "id": 7},
    )

    pending = registry.list_pending_results()
    assert [item["task_id"] for item in pending] == [GOLDEN_TASK_ID]
    assert pending[0]["status"] == PASS
    assert pending[0]["evidence"]["artifact"]["id"] == 7
    assert pending[0]["evidence"]["task_result"]["task_id"] == GOLDEN_TASK_ID

    payload = registry.get_task_result(GOLDEN_TASK_ID)
    assert payload["status"] == PASS
    assert payload["task_id"] == GOLDEN_TASK_ID


def test_default_registry_module_level_flow() -> None:
    reset_default_registry()
    info = event_sync.sync_terminal_result(
        GOLDEN_TASK_ID,
        terminal_result(task_id=GOLDEN_TASK_ID),
        "success",
    )
    assert info["status"] == PASS
    assert [item["task_id"] for item in list_pending_results()] == [GOLDEN_TASK_ID]

    event_sync.mark_reviewed(GOLDEN_TASK_ID, "PASS")
    assert list_pending_results() == []


def test_package_level_get_task_result_stays_normalization_contract() -> None:
    from personal_ai_execution import get_task_result as package_get_task_result

    payload = package_get_task_result(
        "cf-contract", terminal_result(), "cancelled"
    )
    assert payload["status"] == BLOCKED
    assert payload["execution_result_status"] == PASS
