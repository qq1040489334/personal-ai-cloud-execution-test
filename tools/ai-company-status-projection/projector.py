"""Read-only projection of existing AI Company task responses.

Pure functions only. This module performs no network I/O, reads no
credentials, touches no filesystem state and never reads the local clock.
The caller must supply:

* ``observed_at`` -- when the source API response was observed;
* ``now`` -- the caller's evaluation time;
* ``ttl_seconds`` -- the caller's freshness budget.

It never writes a second state store and never derives an acceptance verdict.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

QUEUED = "queued"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
BLOCKED = "blocked"
UNKNOWN = "unknown"
RUNTIME_STATES = (QUEUED, RUNNING, COMPLETED, FAILED, BLOCKED, UNKNOWN)

PENDING_REVIEW = "pending_review"
REVIEWED = "reviewed"
NOT_APPLICABLE = "not_applicable"
REVIEW_UNKNOWN = "unknown"
REVIEW_STATES = (
    PENDING_REVIEW,
    REVIEWED,
    NOT_APPLICABLE,
    "blocked_awaiting_inspection",
    "legacy_orphan",
    REVIEW_UNKNOWN,
)

FRESH = "fresh"
STALE = "stale"
MISSING = "missing"
INVALID = "invalid"
CONNECTION_ERROR = "connection_error"

_SUCCESS_CONCLUSIONS = frozenset({"success"})
_FAILURE_CONCLUSIONS = frozenset({"failure", "startup_failure", "error"})
_QUEUED_STATUSES = frozenset(
    {
        "queued",
        "pending",
        "submitted",
        "created",
        "dispatched",
        "accepted",
        "pending_dispatch",
        "requested",
        "waiting",
    }
)
_RUNNING_STATUSES = frozenset({"running", "in_progress", "in-progress", "started", "start"})
_TERMINAL_EXECUTION = {"PASS": COMPLETED, "FAIL": FAILED, "BLOCKED": BLOCKED}
_RESULT_STATES = frozenset({COMPLETED, FAILED, BLOCKED})
_DISPATCH_BLOCKERS = {
    "DISPATCH_FAILED": "dispatch_failed",
    "EXHAUSTED": "dispatch_exhausted",
}
_SELF_REPORTED_SUCCESS = frozenset(
    {"completed", "complete", "success", "succeeded", "pass", "passed", "ok"}
)
_SELF_REPORTED_FAILURE = frozenset(
    {"failure", "failed", "fail", "error", "errored", "blocked", "timed_out"}
)
_ALLOWED_CLOCK_SKEW_SECONDS = 60

_EVIDENCE_RANK = {
    "workflow_conclusion": 5,
    "execution_status": 4,
    "workflow_run": 3,
    "result_available": 2,
    "advisory_lifecycle": 1,
    "none": 0,
}


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _lower(value: Any) -> str:
    return _text(value).lower()


def _upper(value: Any) -> str:
    return _text(value).upper()


def _parse_iso(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_now(now: Any) -> datetime | None:
    if isinstance(now, datetime):
        parsed = now
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return _parse_iso(now)


def _source_event_at(record: Mapping[str, Any]) -> str | None:
    for key in ("updated_at", "last_update_at", "completed_at", "created_at"):
        parsed = _parse_iso(record.get(key))
        if parsed is not None:
            return _iso(parsed)
    return None


def _evidence(record: Mapping[str, Any]) -> str:
    if _text(record.get("workflow_conclusion")):
        return "workflow_conclusion"
    if _upper(record.get("execution_status")) in _TERMINAL_EXECUTION:
        return "execution_status"
    if _upper(record.get("normalized_status")) in _TERMINAL_EXECUTION:
        return "execution_status"
    if _text(record.get("run_status")) or _text(record.get("run_conclusion")):
        return "workflow_run"
    if record.get("result_available") is True:
        return "result_available"
    status = _lower(record.get("status"))
    if (
        status in _QUEUED_STATUSES
        or status in _RUNNING_STATUSES
        or _text(record.get("dispatch_state"))
    ):
        return "advisory_lifecycle"
    return "none"


def _derive_runtime(record: Mapping[str, Any]) -> tuple[str, str, str | None]:
    conclusion = _lower(record.get("workflow_conclusion"))
    if conclusion:
        if conclusion in _SUCCESS_CONCLUSIONS:
            return COMPLETED, "workflow_conclusion", None
        if conclusion in _FAILURE_CONCLUSIONS:
            return FAILED, "workflow_conclusion", None
        return BLOCKED, "workflow_conclusion", f"workflow_{conclusion}"

    execution = _upper(record.get("execution_status"))
    if execution not in _TERMINAL_EXECUTION:
        execution = _upper(record.get("normalized_status"))
    if execution in _TERMINAL_EXECUTION:
        state = _TERMINAL_EXECUTION[execution]
        blocker = "execution_blocked" if state == BLOCKED else None
        return state, "execution_status", blocker

    run_status = _lower(record.get("run_status"))
    run_conclusion = _lower(record.get("run_conclusion"))
    if run_conclusion:
        if run_conclusion in _SUCCESS_CONCLUSIONS:
            return COMPLETED, "workflow_run", None
        if run_conclusion in _FAILURE_CONCLUSIONS:
            return FAILED, "workflow_run", None
        return BLOCKED, "workflow_run", f"workflow_{run_conclusion}"
    if run_status in {"completed", "complete"}:
        return BLOCKED, "workflow_run", "workflow_conclusion_missing"
    if run_status in _RUNNING_STATUSES:
        return RUNNING, "workflow_run", None
    if run_status in _QUEUED_STATUSES:
        return QUEUED, "workflow_run", None

    if record.get("result_available") is True:
        return COMPLETED, "result_available", None

    dispatch = _upper(record.get("dispatch_state"))
    if dispatch in _DISPATCH_BLOCKERS:
        return BLOCKED, "advisory_lifecycle", _DISPATCH_BLOCKERS[dispatch]
    if _lower(record.get("recommended_action")) == "inspect":
        return BLOCKED, "advisory_lifecycle", "inspect_required"

    status = _lower(record.get("status"))
    if status in _QUEUED_STATUSES:
        return QUEUED, "advisory_lifecycle", None
    if status in _RUNNING_STATUSES:
        return RUNNING, "advisory_lifecycle", None
    if status in _SELF_REPORTED_SUCCESS or status in _SELF_REPORTED_FAILURE:
        return UNKNOWN, "none", "unverified_self_report"
    return UNKNOWN, "none", "no_run_evidence"


def _derive_review(
    record: Mapping[str, Any], runtime: str
) -> tuple[str, str | None]:
    verdict = _upper(record.get("review_verdict")) or None
    if record.get("reviewed") is True or (verdict in {"PASS", "FAIL", "BLOCKED"}):
        return REVIEWED, verdict
    raw_review = _lower(record.get("review_state"))
    if raw_review in {
        "reviewed",
        PENDING_REVIEW,
        "blocked_awaiting_inspection",
        "legacy_orphan",
    }:
        return raw_review, verdict
    status = _lower(record.get("status"))
    if status == "reviewed":
        return REVIEWED, verdict
    if status == PENDING_REVIEW:
        return PENDING_REVIEW, verdict
    if (
        runtime in _RESULT_STATES
        and record.get("result_available") is True
    ) or (
        runtime in _RESULT_STATES
        and record.get("requires_review") is True
    ):
        return PENDING_REVIEW, verdict
    return NOT_APPLICABLE, verdict


def _stable(record: Mapping[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, default=str, ensure_ascii=False)


def _rank(record: Mapping[str, Any]) -> tuple[int, float, str]:
    parsed = _parse_iso(_source_event_at(record))
    stamp = parsed.timestamp() if parsed is not None else float("-inf")
    return (_EVIDENCE_RANK.get(_evidence(record), 0), stamp, _stable(record))


def _merge_duplicates(
    task_id: str, records: list[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
    merged = dict(max(records, key=_rank))
    warnings: list[str] = []
    for field in ("parent_task_id", "project_id", "root_task_id"):
        values = {
            _text(record.get(field))
            for record in records
            if _text(record.get(field))
        }
        chosen = _text(merged.get(field))
        if len(values) > 1:
            merged[field] = None
            warnings.append(f"{task_id}: conflicting {field}; omitted")
        elif not chosen and len(values) == 1:
            merged[field] = next(iter(values))
    return merged, warnings


def _freshness(
    observed_at: Any, now_dt: datetime, ttl: float
) -> tuple[str, str | None, str | None, float | None]:
    if observed_at is None or not _text(observed_at):
        return MISSING, None, "missing_observed_at", None
    observed = _parse_iso(observed_at)
    if observed is None:
        return INVALID, None, "invalid_observed_at", None
    age = (now_dt - observed).total_seconds()
    if age < -_ALLOWED_CLOCK_SKEW_SECONDS:
        return INVALID, _iso(observed), "observed_at_in_future", age
    if age > ttl:
        return STALE, _iso(observed), "stale_observation", age
    return FRESH, _iso(observed), None, max(0.0, age)


def _project_one(
    task_id: str,
    record: Mapping[str, Any],
    *,
    source: str,
    observed_iso: str | None,
    freshness: str,
    freshness_blocker: str | None,
    age_seconds: float | None,
    connection_error: bool,
    duplicate_count: int,
) -> dict[str, Any]:
    runtime, evidence, blocker = _derive_runtime(record)
    review, verdict = _derive_review(record, runtime)
    last_known = None
    if connection_error:
        runtime, blocker, evidence = UNKNOWN, "connection_failure", "none"
        review = REVIEW_UNKNOWN
    elif freshness != FRESH:
        if runtime != UNKNOWN:
            last_known = runtime
        runtime = UNKNOWN
        blocker = freshness_blocker
        if review != REVIEWED:
            review = REVIEW_UNKNOWN

    parent = _text(record.get("parent_task_id")) or None
    if parent == task_id:
        parent = None

    projected: dict[str, Any] = {
        "task_id": task_id,
        "source": source,
        "observed_at": observed_iso,
        "runtime_state": runtime,
        "review_state": review,
        "blocker": blocker,
        "parent_task_id": parent,
        "last_source_event_at": _source_event_at(record),
        "evidence": evidence,
        "freshness": freshness,
        "duplicate_count": duplicate_count,
    }
    if last_known is not None:
        projected["last_known_runtime_state"] = last_known
    if verdict is not None:
        projected["review_verdict"] = verdict
    for field in ("project_id", "root_task_id"):
        value = _text(record.get(field))
        if value:
            projected[field] = value
    if age_seconds is not None:
        projected["observed_age_seconds"] = round(age_seconds, 3)
    return projected


def project_tasks(
    records: Iterable[Mapping[str, Any]],
    *,
    source: str,
    observed_at: Any,
    now: Any,
    ttl_seconds: Any,
    connection_error: Any = None,
) -> dict[str, Any]:
    """Project an existing task-API response into read-only status metadata.

    ``records`` is the raw response list. ``source`` names the verified
    interface that produced it. ``observed_at`` is the explicit source
    observation time; ``now`` and ``ttl_seconds`` are supplied by the caller.
    ``connection_error`` is truthy when the transport failed.
    """
    record_list = list(records or [])
    source_name = _text(source) or "unknown"
    warnings: list[str] = []
    if source_name == "unknown":
        warnings.append("source missing; reported as unknown")
    connection_failed = bool(connection_error)
    now_dt = _coerce_now(now)
    if now_dt is None:
        raise ValueError("now must be a datetime or ISO-8601 string")
    if ttl_seconds is None:
        raise ValueError("ttl_seconds is required and must be caller-supplied")
    ttl = float(ttl_seconds)
    if ttl < 0:
        raise ValueError("ttl_seconds must be >= 0")
    freshness, observed_iso, freshness_blocker, age_seconds = _freshness(
        observed_at, now_dt, ttl
    )

    groups: dict[str, list[Mapping[str, Any]]] = {}
    for record in record_list:
        if not isinstance(record, Mapping):
            warnings.append("non-object record skipped")
            continue
        task_id = _text(record.get("task_id"))
        if not task_id:
            warnings.append("record without task_id skipped")
            continue
        groups.setdefault(task_id, []).append(record)

    tasks: list[dict[str, Any]] = []
    duplicate_notes: list[dict[str, Any]] = []
    for task_id, group in groups.items():
        merged, merge_warnings = _merge_duplicates(task_id, group)
        warnings.extend(merge_warnings)
        if len(group) > 1:
            duplicate_notes.append(
                {"task_id": task_id, "records": len(group)}
            )
        record_source = _text(merged.get("source")) or source_name
        tasks.append(
            _project_one(
                task_id,
                merged,
                source=record_source,
                observed_iso=observed_iso,
                freshness=freshness,
                freshness_blocker=freshness_blocker,
                age_seconds=age_seconds,
                connection_error=connection_failed,
                duplicate_count=len(group),
            )
        )

    runtime_counts = {state: 0 for state in RUNTIME_STATES}
    review_counts = {state: 0 for state in REVIEW_STATES}
    for task in tasks:
        runtime_counts[task["runtime_state"]] += 1
        review_counts[task["review_state"]] += 1

    complete = (
        freshness == FRESH
        and not connection_failed
        and not any(
            warning.startswith(("record without task_id", "non-object record"))
            for warning in warnings
        )
    )
    batch_blocker = None
    if connection_failed:
        batch_blocker = "connection_failure"
    elif freshness != FRESH:
        batch_blocker = freshness_blocker

    return {
        "source": source_name,
        "observed_at": observed_iso,
        "projected_at": _iso(now_dt),
        "ttl_seconds": ttl,
        "complete": complete,
        "batch_blocker": batch_blocker,
        "tasks": sorted(tasks, key=lambda item: item["task_id"]),
        "counts": {
            "raw_records": len(record_list),
            "total_unique_tasks": len(tasks),
            "duplicate_records": sum(
                note["records"] - 1 for note in duplicate_notes
            ),
            "runtime_state": runtime_counts,
            "review_state": review_counts,
        },
        "duplicates": duplicate_notes,
        "warnings": warnings,
    }
