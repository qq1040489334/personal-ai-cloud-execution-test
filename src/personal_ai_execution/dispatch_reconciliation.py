"""CLOUD_AGENT_QUEUED_RUN_CANCELLATION_FIX_V0.1 -- dispatch liveness lease.

Accepted Cloud Agent tasks become *permanently* ``PENDING`` when a queued
``repository_dispatch`` run is cancelled before any job step starts. The single
global concurrency group in ``.github/workflows/agent-dispatch.yml``
(``cloud-agent-dispatch-main-writer`` with ``cancel-in-progress: false``) keeps
at most one running plus one pending run; a burst of dispatches cancels the
previously-queued run with zero jobs. Such a run writes no ``execution_result``
artifact, so the Worker registry (``worker/index.js`` ``recordTask`` /
``listPendingResults``) never observes a conclusion and the record stays
``PENDING`` forever.

This module defines the *smallest safe, pure* liveness contract that removes the
silent permanent ``PENDING`` without touching the single-writer safety property:

* An accepted dispatch is a **lease**, not a terminal state. Every accepted task
  carries ``dispatch_state`` / ``dispatch_attempt`` / ``dispatch_accepted_at`` /
  ``dispatch_confirm_deadline``.
* **Confirmation** is positive evidence that a job actually started: an
  ``execution_result-<task_id>`` artifact exists, a workflow conclusion is
  present, or the run status is ``in_progress`` / ``completed``. A run that is
  merely ``queued`` is explicitly *not* confirmation -- that is exactly the
  cancelled-before-job-start case.
* Past the confirmation deadline with no job-start evidence, the task is
  truthfully classified ``UNCONFIRMED`` (retryable) or ``EXHAUSTED``
  (inspect) instead of remaining silently ``PENDING``.
* A retry is **idempotent and deduplicated**: it reuses the same ``task_id`` and
  carries a deterministic ``retry:<task_id>:<attempt>`` idempotency key so two
  concurrent planners converge on exactly one re-dispatch.

The module is deliberately side-effect free. Applying a retry to registry
metadata lives in :meth:`personal_ai_execution.event_sync.EventSyncRegistry.
plan_task_redispatch` / ``mark_dispatch_retried`` and, in production, in the
Cloudflare Worker. The dispatch itself remains an authorized, separately gated
action.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

#: Written *before* the repository_dispatch HTTP call so a Worker crash between
#: acceptance and ``recordTask`` still leaves a bounded, recoverable record.
TASK_DISPATCH_STATE_PENDING = "PENDING_DISPATCH"
#: The dispatch HTTP call returned 2xx and a lease is active.
TASK_DISPATCH_STATE_ACCEPTED = "ACCEPTED"
#: Positive job-start evidence (artifact / conclusion / in_progress run).
TASK_DISPATCH_STATE_CONFIRMED = "CONFIRMED"
#: Lease expired with no job-start evidence: retryable.
TASK_DISPATCH_STATE_UNCONFIRMED = "UNCONFIRMED"
#: A retry lease is currently active.
TASK_DISPATCH_STATE_RETRY = "RETRY_DISPATCHED"
#: The dispatch HTTP call failed (network error / GitHub rejection).
TASK_DISPATCH_STATE_FAILED = "DISPATCH_FAILED"
#: ``MAX_DISPATCH_ATTEMPTS`` reached with no confirmation: inspect, do not loop.
TASK_DISPATCH_STATE_EXHAUSTED = "EXHAUSTED"

#: Truthful next actions surfaced to a Supervisor consumer.
ACTION_WAIT = "wait"
ACTION_RETRY = "retry"
ACTION_INSPECT = "inspect"
ACTION_NONE = "none"

#: States that are liveness-terminal (no further automatic retry).
TERMINAL_DISPATCH_STATES = frozenset(
    {TASK_DISPATCH_STATE_CONFIRMED, TASK_DISPATCH_STATE_EXHAUSTED}
)

#: Confirmation grace period, aligned with the Worker ``BLOCKED_AFTER_MS``.
DEFAULT_DISPATCH_CONFIRM_GRACE_SECONDS = 15 * 60

#: Bounded attempts. On exhaustion the task is surfaced for human inspection
#: instead of re-dispatching forever.
MAX_DISPATCH_ATTEMPTS = 3

#: Workflow run statuses that prove a job actually started. ``queued`` is
#: deliberately excluded.
_CONFIRMING_RUN_STATUSES = frozenset({"in_progress", "completed"})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def dispatch_confirmed(
    record: Mapping[str, Any],
    *,
    has_artifact: bool = False,
    run_status: str | None = None,
    run_conclusion: str | None = None,
) -> bool:
    """Return ``True`` only on positive evidence that a job actually started.

    A run that is merely ``queued`` is *not* confirmed: a queued run that is
    cancelled by the single-writer concurrency group never starts a job and
    never produces an artifact. Only an artifact, a recorded conclusion, or an
    ``in_progress`` / ``completed`` run count as confirmation.
    """
    if has_artifact:
        return True
    if run_conclusion is not None and str(run_conclusion).strip():
        return True
    status = str(run_status).strip().lower() if run_status is not None else ""
    return status in _CONFIRMING_RUN_STATUSES


def classify_dispatch_liveness(
    record: Mapping[str, Any],
    *,
    has_artifact: bool = False,
    run_status: str | None = None,
    run_conclusion: str | None = None,
    now: datetime | None = None,
    grace_seconds: int = DEFAULT_DISPATCH_CONFIRM_GRACE_SECONDS,
    max_attempts: int = MAX_DISPATCH_ATTEMPTS,
) -> dict[str, Any]:
    """Classify a registry record into a truthful, bounded dispatch liveness state.

    The returned ``recommended_action`` is one of ``wait`` / ``retry`` /
    ``inspect`` / ``none``. A record with a fresh lease reports ``wait`` and
    carries an explicit ``dispatch_confirm_deadline``; once that deadline passes
    without job-start evidence the record reports ``retry`` (or ``inspect`` when
    attempts are exhausted). By construction a record can therefore never be
    reported as permanently-``PENDING`` with no action.
    """
    current = now or _utc_now()
    task_id = str(record.get("task_id") or "")
    try:
        attempt = max(1, int(record.get("dispatch_attempt") or 1))
    except (TypeError, ValueError):
        attempt = 1
    max_attempts = max(1, int(max_attempts))

    accepted_at = _parse_timestamp(
        record.get("dispatch_accepted_at")
        or record.get("dispatch_at")
        or record.get("created_at")
        or record.get("updated_at")
    )
    deadline = _parse_timestamp(record.get("dispatch_confirm_deadline"))
    if deadline is None and accepted_at is not None:
        deadline = accepted_at + timedelta(seconds=max(0, int(grace_seconds)))
    lease_expired = bool(deadline is not None and current > deadline)

    confirmed = dispatch_confirmed(
        record,
        has_artifact=has_artifact,
        run_status=run_status,
        run_conclusion=run_conclusion,
    )
    authoritative = bool(
        record.get("reviewed")
        or record.get("terminal")
        or record.get("result_available")
    )
    recorded_state = str(record.get("dispatch_state") or "").strip().upper()

    if authoritative:
        state = TASK_DISPATCH_STATE_CONFIRMED
        action = ACTION_NONE
        retryable = False
        reason = "authoritative result or review already recorded"
    elif recorded_state == TASK_DISPATCH_STATE_FAILED:
        retryable = attempt < max_attempts
        state = TASK_DISPATCH_STATE_FAILED
        action = ACTION_RETRY if retryable else ACTION_INSPECT
        reason = (
            "dispatch HTTP call failed; "
            + ("retryable" if retryable else "attempts exhausted")
        )
    elif confirmed:
        state = TASK_DISPATCH_STATE_CONFIRMED
        action = (
            ACTION_WAIT
            if str(run_status or "").strip().lower() == "in_progress"
            else ACTION_NONE
        )
        retryable = False
        reason = "job-start evidence observed; awaiting authoritative result"
    elif not lease_expired:
        # A fresh lease reports ``wait`` regardless of whether the dispatch call
        # has already been accepted, so the state always carries a deadline and
        # can never be a silent permanent ``PENDING``.
        state = TASK_DISPATCH_STATE_ACCEPTED
        action = ACTION_WAIT
        retryable = False
        reason = "dispatch lease active; awaiting job start"
    elif attempt >= max_attempts:
        state = TASK_DISPATCH_STATE_EXHAUSTED
        action = ACTION_INSPECT
        retryable = False
        reason = (
            "dispatch accepted but no job started before the deadline and "
            "attempts are exhausted"
        )
    else:
        state = TASK_DISPATCH_STATE_UNCONFIRMED
        action = ACTION_RETRY
        retryable = True
        reason = (
            "dispatch accepted but no job started before the deadline "
            "(queued run cancelled before job start)"
        )

    return {
        "task_id": task_id,
        "dispatch_state": state,
        "recommended_action": action,
        "retryable": retryable,
        "confirmed": confirmed,
        "lease_expired": lease_expired,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "dispatch_accepted_at": accepted_at.isoformat() if accepted_at else None,
        "dispatch_confirm_deadline": deadline.isoformat() if deadline else None,
        "reason": reason,
    }


def is_permanently_pending(report: Mapping[str, Any]) -> bool:
    """Return ``True`` only if a report is silently stuck ``PENDING``.

    A bounded ``wait`` on a *fresh* lease is not permanent-``PENDING`` because it
    carries a deadline. This predicate exists as an executable invariant: the
    classifier must never produce a report that satisfies it.
    """
    return (
        str(report.get("recommended_action")) == ACTION_WAIT
        and bool(report.get("lease_expired"))
    )


def plan_dispatch_retry(
    record: Mapping[str, Any],
    *,
    has_artifact: bool = False,
    run_status: str | None = None,
    run_conclusion: str | None = None,
    now: datetime | None = None,
    grace_seconds: int = DEFAULT_DISPATCH_CONFIRM_GRACE_SECONDS,
    max_attempts: int = MAX_DISPATCH_ATTEMPTS,
) -> dict[str, Any]:
    """Return an idempotent, deduplicated re-dispatch plan for ``record``.

    The retry intentionally reuses the *same* ``task_id`` so no duplicate
    registry or review record can be created. The deterministic
    ``retry:<task_id>:<attempt>`` idempotency key lets a caller claim the retry
    exactly once (for example with the existing D1
    ``INSERT OR IGNORE`` marker pattern) so two concurrent planners converge on
    one dispatch.
    """
    report = classify_dispatch_liveness(
        record,
        has_artifact=has_artifact,
        run_status=run_status,
        run_conclusion=run_conclusion,
        now=now,
        grace_seconds=grace_seconds,
        max_attempts=max_attempts,
    )
    task_id = str(record.get("task_id") or "")
    attempt = int(report["attempt"])
    should_retry = report["recommended_action"] == ACTION_RETRY
    next_attempt = attempt + 1 if should_retry else attempt
    idempotency_key = (
        f"retry:{task_id}:{next_attempt}" if should_retry and task_id else None
    )
    return {
        "task_id": task_id,
        "should_retry": should_retry,
        "same_task_id": True,
        "next_attempt": next_attempt,
        "idempotency_key": idempotency_key,
        "retry_claim_scope": "task_dispatch_markers" if should_retry else None,
        "dispatch_state": report["dispatch_state"],
        "recommended_action": report["recommended_action"],
        "retryable": report["retryable"],
        "confirmed": report["confirmed"],
        "lease_expired": report["lease_expired"],
        "reason": report["reason"],
    }
