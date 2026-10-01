"""Tests for CLOUD_AGENT_QUEUED_RUN_CANCELLATION_FIX_V0.1.

An accepted Cloud Agent task becomes permanently ``PENDING`` when a queued
``repository_dispatch`` run is cancelled by the single-writer concurrency group
before any job starts. The fix models an accepted dispatch as a *bounded lease*
and truthfully classifies an unconfirmed lease as retryable / inspectable, while
preserving single-writer safety (retries reuse the same ``task_id`` and carry a
deterministic dedupe key).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from personal_ai_execution import (
    ACTION_INSPECT,
    ACTION_NONE,
    ACTION_RETRY,
    ACTION_WAIT,
    DEFAULT_DISPATCH_CONFIRM_GRACE_SECONDS,
    TASK_DISPATCH_STATE_ACCEPTED,
    TASK_DISPATCH_STATE_CONFIRMED,
    TASK_DISPATCH_STATE_EXHAUSTED,
    TASK_DISPATCH_STATE_FAILED,
    TASK_DISPATCH_STATE_PENDING,
    TASK_DISPATCH_STATE_RETRY,
    TASK_DISPATCH_STATE_UNCONFIRMED,
    MAX_DISPATCH_ATTEMPTS,
    EventSyncRegistry,
    classify_dispatch_liveness,
    dispatch_confirmed,
    is_permanently_pending,
    plan_dispatch_retry,
)

NOW = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)


def accepted_record(
    task_id: str = "cf-queued",
    *,
    accepted_seconds_ago: int = 0,
    attempt: int = 1,
    state: str | None = None,
    **extra: object,
) -> dict[str, object]:
    accepted = NOW - timedelta(seconds=accepted_seconds_ago)
    record: dict[str, object] = {
        "task_id": task_id,
        "status": "PENDING",
        "terminal": False,
        "result_available": False,
        "reviewed": False,
        "dispatch_state": state or TASK_DISPATCH_STATE_ACCEPTED,
        "dispatch_attempt": attempt,
        "dispatch_accepted_at": accepted.isoformat(),
    }
    record.update(extra)
    return record


# -- queue/run status truthfulness -------------------------------------------


def test_queued_run_status_is_not_confirmation() -> None:
    # A run that is merely ``queued`` has not started a job; that is exactly the
    # cancelled-before-job-start case and must not count as confirmation.
    assert dispatch_confirmed({}, has_artifact=False, run_status="queued") is False
    assert dispatch_confirmed({}, has_artifact=False, run_status="waiting") is False
    assert dispatch_confirmed({}, has_artifact=False, run_status=None) is False


def test_job_start_evidence_is_confirmation() -> None:
    assert dispatch_confirmed({}, has_artifact=True) is True
    assert dispatch_confirmed({}, run_status="in_progress") is True
    assert dispatch_confirmed({}, run_status="completed") is True
    assert dispatch_confirmed({}, run_conclusion="cancelled") is True


# -- the primary regression: no permanent PENDING ----------------------------


def test_cancelled_before_job_start_becomes_retryable_not_permanent_pending() -> None:
    record = accepted_record(accepted_seconds_ago=16 * 60)
    report = classify_dispatch_liveness(
        record, has_artifact=False, run_status="queued", now=NOW
    )

    assert report["dispatch_state"] == TASK_DISPATCH_STATE_UNCONFIRMED
    assert report["recommended_action"] == ACTION_RETRY
    assert report["retryable"] is True
    assert report["lease_expired"] is True
    assert report["confirmed"] is False
    assert is_permanently_pending(report) is False


def test_fresh_accepted_lease_reports_bounded_wait_with_deadline() -> None:
    record = accepted_record(accepted_seconds_ago=60)
    report = classify_dispatch_liveness(record, now=NOW)

    assert report["dispatch_state"] == TASK_DISPATCH_STATE_ACCEPTED
    assert report["recommended_action"] == ACTION_WAIT
    assert report["lease_expired"] is False
    assert report["dispatch_confirm_deadline"] is not None
    assert is_permanently_pending(report) is False


def test_classifier_never_reports_permanent_pending_across_ages() -> None:
    for age in (0, 60, 900, 901, 3000, 100000):
        record = accepted_record(accepted_seconds_ago=age)
        report = classify_dispatch_liveness(record, now=NOW)
        assert is_permanently_pending(report) is False
        assert report["recommended_action"] in {
            ACTION_WAIT,
            ACTION_RETRY,
            ACTION_INSPECT,
            ACTION_NONE,
        }


def test_explicit_deadline_is_honoured_over_created_at() -> None:
    record = accepted_record(accepted_seconds_ago=10)
    record["dispatch_confirm_deadline"] = (NOW - timedelta(seconds=1)).isoformat()
    report = classify_dispatch_liveness(record, has_artifact=False, now=NOW)

    assert report["lease_expired"] is True
    assert report["recommended_action"] == ACTION_RETRY


# -- exhaustion is bounded, never an infinite retry loop ---------------------


def test_unconfirmed_at_max_attempts_is_exhausted_for_inspection() -> None:
    record = accepted_record(
        accepted_seconds_ago=3600, attempt=MAX_DISPATCH_ATTEMPTS
    )
    report = classify_dispatch_liveness(record, now=NOW)

    assert report["dispatch_state"] == TASK_DISPATCH_STATE_EXHAUSTED
    assert report["recommended_action"] == ACTION_INSPECT
    assert report["retryable"] is False


def test_confirmed_job_start_wins_over_expired_lease() -> None:
    record = accepted_record(accepted_seconds_ago=3600)
    report = classify_dispatch_liveness(
        record, run_status="in_progress", now=NOW
    )

    assert report["dispatch_state"] == TASK_DISPATCH_STATE_CONFIRMED
    assert report["recommended_action"] == ACTION_WAIT
    assert report["retryable"] is False


def test_authoritative_result_closes_liveness() -> None:
    record = accepted_record(accepted_seconds_ago=3600, terminal=True, result_available=True)
    report = classify_dispatch_liveness(record, now=NOW)

    assert report["dispatch_state"] == TASK_DISPATCH_STATE_CONFIRMED
    assert report["recommended_action"] == ACTION_NONE
    assert is_permanently_pending(report) is False


def test_failed_dispatch_http_is_retryable_then_inspectable() -> None:
    retryable = classify_dispatch_liveness(
        accepted_record(attempt=1, state=TASK_DISPATCH_STATE_FAILED), now=NOW
    )
    exhausted = classify_dispatch_liveness(
        accepted_record(attempt=MAX_DISPATCH_ATTEMPTS, state=TASK_DISPATCH_STATE_FAILED),
        now=NOW,
    )

    assert retryable["dispatch_state"] == TASK_DISPATCH_STATE_FAILED
    assert retryable["recommended_action"] == ACTION_RETRY
    assert exhausted["recommended_action"] == ACTION_INSPECT


# -- idempotency / dedupe ----------------------------------------------------


def test_retry_plan_reuses_same_task_id_and_dedupes() -> None:
    record = accepted_record("cf-dedupe", accepted_seconds_ago=16 * 60)
    plan = plan_dispatch_retry(record, now=NOW)

    assert plan["should_retry"] is True
    assert plan["same_task_id"] is True
    assert plan["task_id"] == "cf-dedupe"
    assert plan["next_attempt"] == 2
    assert plan["idempotency_key"] == "retry:cf-dedupe:2"
    assert plan["retry_claim_scope"] == "task_dispatch_markers"


def test_two_planners_converge_on_one_idempotency_key() -> None:
    record = accepted_record("cf-converge", accepted_seconds_ago=16 * 60)
    first = plan_dispatch_retry(record, now=NOW)
    second = plan_dispatch_retry(record, now=NOW)

    assert first["idempotency_key"] == second["idempotency_key"]
    assert first["next_attempt"] == second["next_attempt"] == 2


def test_confirmed_task_has_no_retry_plan() -> None:
    record = accepted_record("cf-ok")
    plan = plan_dispatch_retry(record, run_status="in_progress", now=NOW)

    assert plan["should_retry"] is False
    assert plan["idempotency_key"] is None
    assert plan["retry_claim_scope"] is None


# -- registry integration: read-only, idempotent, truthful -------------------


def test_registry_liveness_report_is_read_only_and_surfaces_unconfirmed() -> None:
    registry = EventSyncRegistry()
    registry.submit_task(
        "cf-stuck",
        goal="queued dispatch cancelled",
        status="PENDING",
        dispatch_state=TASK_DISPATCH_STATE_ACCEPTED,
        dispatch_attempt=1,
        dispatch_accepted_at=(NOW - timedelta(seconds=16 * 60)).isoformat(),
    )
    before = dict(registry._tasks["cf-stuck"])

    report = registry.dispatch_liveness_report(
        {"cf-stuck": {"has_artifact": False, "run_status": "queued"}}, now=NOW
    )

    assert report["counts"]["unconfirmed"] == 1
    assert report["retryable"][0]["task_id"] == "cf-stuck"
    assert report["retryable"][0]["permanently_pending"] is False
    # read-only: no mutation from merely reporting
    assert registry._tasks["cf-stuck"] == before


def test_registry_retry_updates_metadata_only_never_status_or_review() -> None:
    registry = EventSyncRegistry()
    registry.submit_task(
        "cf-retry",
        goal="queued dispatch cancelled",
        status="PENDING",
        dispatch_state=TASK_DISPATCH_STATE_ACCEPTED,
        dispatch_attempt=1,
        dispatch_accepted_at=(NOW - timedelta(seconds=16 * 60)).isoformat(),
    )

    update = registry.mark_dispatch_retried("cf-retry", timestamp=NOW)
    record = registry._tasks["cf-retry"]

    assert update["dispatch_attempt"] == 2
    assert update["dispatch_state"] == TASK_DISPATCH_STATE_RETRY
    assert record["status"] == "PENDING"
    assert record["terminal"] is False
    assert record["result_available"] is False
    assert record["reviewed"] is False
    # the retry audit is append-only and idempotent to read
    assert len(registry.get_dispatch_events("cf-retry")) == 1
    assert registry.get_dispatch_events("cf-retry")[0]["action"] == "dispatch_retry"


def test_registry_plan_redispatch_matches_module_plan() -> None:
    registry = EventSyncRegistry()
    registry.submit_task(
        "cf-plan",
        goal="queued dispatch cancelled",
        status="PENDING",
        dispatch_state=TASK_DISPATCH_STATE_ACCEPTED,
        dispatch_attempt=1,
        dispatch_accepted_at=(NOW - timedelta(seconds=16 * 60)).isoformat(),
    )

    plan = registry.plan_task_redispatch("cf-plan", now=NOW)
    direct = plan_dispatch_retry(
        registry._tasks["cf-plan"], now=NOW
    )

    assert plan["idempotency_key"] == direct["idempotency_key"]
    assert plan["should_retry"] is True


def test_registry_plan_redispatch_unknown_task_fails_closed() -> None:
    registry = EventSyncRegistry()
    with pytest.raises(KeyError):
        registry.plan_task_redispatch("cf-missing")


# -- no regression to default behavior ---------------------------------------


def test_default_grace_seconds_is_fifteen_minutes() -> None:
    assert DEFAULT_DISPATCH_CONFIRM_GRACE_SECONDS == 15 * 60


def test_pending_and_retry_recorded_states_still_report_bounded_wait() -> None:
    # Whether a record was written pre-dispatch or by a retry, a fresh lease is
    # always a bounded ``wait`` (never a silent permanent ``PENDING``).
    for state in (TASK_DISPATCH_STATE_PENDING, TASK_DISPATCH_STATE_RETRY):
        report = classify_dispatch_liveness(
            accepted_record(accepted_seconds_ago=30, state=state), now=NOW
        )
        assert report["dispatch_state"] == TASK_DISPATCH_STATE_ACCEPTED
        assert report["recommended_action"] == ACTION_WAIT
        assert report["dispatch_confirm_deadline"] is not None
        assert is_permanently_pending(report) is False
