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
import math
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
REVIEW_CONFLICT = "conflict"
REVIEW_STATES = (
    PENDING_REVIEW,
    REVIEWED,
    NOT_APPLICABLE,
    "blocked_awaiting_inspection",
    "legacy_orphan",
    REVIEW_UNKNOWN,
    REVIEW_CONFLICT,
)

FRESH = "fresh"
STALE = "stale"
MISSING = "missing"
INVALID = "invalid"
CONNECTION_ERROR = "connection_error"

_SUBJECT_SUBSET = "pending_results_subset"
_SUBJECT_SINGLE = "single_task"
_SUBJECT_FULL = "full_task_set"
_SUBJECT_UNKNOWN = "unknown"

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
    "conflict": 6,
    "workflow_conclusion": 5,
    "execution_status": 4,
    "workflow_run": 3,
    "result_available": 2,
    "advisory_lifecycle": 1,
    "none": 0,
}

_REVIEW_STRENGTH = {
    REVIEWED: 3,
    PENDING_REVIEW: 2,
    "blocked_awaiting_inspection": 1,
    "legacy_orphan": 1,
}

_RUN_ID_FIELDS = (
    "run_id",
    "workflow_run_id",
    "execution_id",
    "run_identity",
    "github_run_id",
)
_SEQUENCE_FIELDS = (
    "sequence",
    "event_sequence",
    "source_sequence",
    "run_sequence",
    "run_attempt",
    "attempt",
    "round",
)


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


def _sequence(record: Mapping[str, Any]) -> float | None:
    for key in _SEQUENCE_FIELDS:
        value = record.get(key)
        if value is None or isinstance(value, bool):
            continue
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed):
            return parsed
    return None


def _run_identity(record: Mapping[str, Any]) -> str | None:
    for key in _RUN_ID_FIELDS:
        value = _text(record.get(key))
        if value:
            return value
    return None


def _safe_event_at(
    record: Mapping[str, Any], boundary: datetime | None
) -> datetime | None:
    parsed = _parse_iso(_source_event_at(record))
    if parsed is None:
        return None
    if (
        boundary is not None
        and (parsed - boundary).total_seconds() > _ALLOWED_CLOCK_SKEW_SECONDS
    ):
        return None
    return parsed


def _event_rank(
    record: Mapping[str, Any], boundary: datetime | None
) -> tuple[float, float]:
    parsed = _safe_event_at(record, boundary)
    stamp = parsed.timestamp() if parsed is not None else float("-inf")
    sequence = _sequence(record)
    return stamp, sequence if sequence is not None else float("-inf")


def _derive_runtime(record: Mapping[str, Any]) -> tuple[str, str, str | None]:
    conclusion = _lower(record.get("workflow_conclusion"))
    execution = _upper(record.get("execution_status"))
    if execution not in _TERMINAL_EXECUTION:
        execution = _upper(record.get("normalized_status"))
    if execution not in _TERMINAL_EXECUTION:
        fallback = _upper(record.get("status"))
        if fallback in {"FAIL", "BLOCKED"}:
            execution = fallback

    if conclusion:
        if conclusion in _SUCCESS_CONCLUSIONS:
            if execution == "FAIL":
                return FAILED, "conflict", "workflow_success_execution_failure"
            if execution == "BLOCKED":
                return BLOCKED, "conflict", "workflow_success_execution_blocked"
            return COMPLETED, "workflow_conclusion", None
        if conclusion in _FAILURE_CONCLUSIONS:
            return FAILED, "workflow_conclusion", None
        return BLOCKED, "workflow_conclusion", f"workflow_{conclusion}"

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


def _has_explicit_review(record: Mapping[str, Any]) -> bool:
    return bool(
        record.get("reviewed") is not None
        or _text(record.get("review_state"))
        or _text(record.get("review_verdict"))
        or record.get("requires_review") is True
        or _lower(record.get("status")) in {"reviewed", PENDING_REVIEW}
    )


def _stable(record: Mapping[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, default=str, ensure_ascii=False)


def _select_runtime(
    records: list[Mapping[str, Any]], boundary: datetime | None
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for record in records:
        state, evidence, blocker = _derive_runtime(record)
        stamp, sequence = _event_rank(record, boundary)
        rank = _EVIDENCE_RANK.get(evidence, 0)
        candidates.append(
            {
                "key": (rank, stamp, sequence),
                "state": state,
                "evidence": evidence,
                "blocker": blocker,
                "record": record,
            }
        )
    best_key = max(candidate["key"] for candidate in candidates)
    top = [candidate for candidate in candidates if candidate["key"] == best_key]
    chosen = max(top, key=lambda candidate: _stable(candidate["record"]))
    states = {candidate["state"] for candidate in top}
    if len(states) == 1 and chosen["state"] == COMPLETED:
        best_event = best_key[1:]
        tied_failures: list[dict[str, Any]] = []
        newer_failures: list[dict[str, Any]] = []
        for candidate in candidates:
            if candidate["state"] not in {FAILED, BLOCKED}:
                continue
            if candidate["evidence"] not in {"execution_status", "conflict"}:
                continue
            candidate_event = candidate["key"][1:]
            if candidate_event == best_event:
                tied_failures.append(candidate)
            elif candidate_event > best_event:
                newer_failures.append(candidate)
        if tied_failures:
            return {
                "state": UNKNOWN,
                "evidence": "conflict",
                "blocker": "conflicting_runtime_evidence",
                "record": chosen["record"],
                "conflicts": [
                    "runtime: completion and execution failure share the "
                    "same time/sequence evidence"
                ],
            }
        if newer_failures:
            candidate = max(
                newer_failures,
                key=lambda item: (
                    item["key"][1],
                    item["key"][2],
                    item["key"][0],
                    _stable(item["record"]),
                ),
            )
            return {
                "state": candidate["state"],
                "evidence": candidate["evidence"],
                "blocker": candidate["blocker"],
                "record": candidate["record"],
                "conflicts": [
                    "runtime: newer execution evidence contradicts "
                    "workflow-success completion"
                ],
            }
    if len(states) > 1:
        identities = {_run_identity(candidate["record"]) for candidate in top}
        if len(identities) > 1:
            detail = (
                "runtime: same evidence rank/time but differing run identities; "
                "association insufficient"
            )
        elif None in identities:
            detail = (
                "runtime: same evidence rank/time but run identity missing; "
                "association insufficient"
            )
        else:
            detail = (
                "runtime: same evidence rank/time but contradictory execution "
                "states for the same run identity"
            )
        return {
            "state": UNKNOWN,
            "evidence": "conflict",
            "blocker": "conflicting_runtime_evidence",
            "record": chosen["record"],
            "conflicts": [detail],
        }
    return {
        "state": chosen["state"],
        "evidence": chosen["evidence"],
        "blocker": chosen["blocker"],
        "record": chosen["record"],
        "conflicts": [],
    }


def _select_review(
    records: list[Mapping[str, Any]], boundary: datetime | None
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for record in records:
        runtime, _, _ = _derive_runtime(record)
        state, verdict = _derive_review(record, runtime)
        strength = _REVIEW_STRENGTH.get(state)
        if not strength:
            continue
        stamp, sequence = _event_rank(record, boundary)
        candidates.append(
            {
                "key": (stamp, sequence, strength),
                "state": state,
                "verdict": verdict,
                "explicit": _has_explicit_review(record),
                "record": record,
            }
        )
    if not candidates:
        return None
    explicit = [candidate for candidate in candidates if candidate["explicit"]]
    pool = explicit or candidates
    best_key = max(candidate["key"] for candidate in pool)
    top = [candidate for candidate in pool if candidate["key"] == best_key]
    chosen = max(top, key=lambda candidate: _stable(candidate["record"]))
    outcomes = {(candidate["state"], candidate["verdict"]) for candidate in top}
    if len(outcomes) > 1:
        verdicts = {
            candidate["verdict"] for candidate in top if candidate["verdict"] is not None
        }
        if len(verdicts) > 1:
            detail = (
                "review: same time/sequence evidence carries conflicting "
                "verdicts; no ordering evidence"
            )
        else:
            detail = (
                "review: same time/sequence evidence carries conflicting review "
                "states; no ordering evidence"
            )
        return {
            "state": REVIEW_CONFLICT,
            "verdict": None,
            "record": chosen["record"],
            "conflicts": [detail],
        }
    return {
        "state": chosen["state"],
        "verdict": chosen["verdict"],
        "record": chosen["record"],
        "conflicts": [],
    }


def _merge_duplicates(
    task_id: str,
    records: list[Mapping[str, Any]],
    boundary: datetime | None,
) -> tuple[
    dict[str, Any],
    list[str],
    dict[str, Any],
    dict[str, Any] | None,
    str | None,
    list[str],
]:
    runtime_selection = _select_runtime(records, boundary)
    review_selection = _select_review(records, boundary)
    merged = dict(runtime_selection["record"])
    warnings: list[str] = []
    conflicts = list(runtime_selection.get("conflicts", []))
    if review_selection is not None:
        conflicts.extend(review_selection.get("conflicts", []))

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

    last_event: datetime | None = None
    for record in records:
        parsed = _safe_event_at(record, boundary)
        if parsed is not None and (last_event is None or parsed > last_event):
            last_event = parsed
    return (
        merged,
        warnings,
        runtime_selection,
        review_selection,
        _iso(last_event) if last_event is not None else None,
        conflicts,
    )


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


def _coverage(
    source_name: str, batch_complete: bool, task_count: int
) -> dict[str, Any]:
    lowered = source_name.lower()
    if "list_pending_results" in lowered:
        scope = _SUBJECT_SUBSET
        full = False
        reason = (
            "list_pending_results returns only pending/failed/blocked buckets, "
            "not the full active-task set"
        )
    elif "get_task_result" in lowered:
        scope = _SUBJECT_SINGLE
        full = False
        reason = "get_task_result covers only the requested task"
    elif any(
        token in lowered
        for token in ("list_tasks", "list_all_tasks", "full_task_list")
    ):
        scope = _SUBJECT_FULL
        full = True
        reason = "caller declared a full task-list source"
    else:
        scope = _SUBJECT_UNKNOWN
        full = False
        reason = "source scope is not declared; full task coverage cannot be claimed"
    return {
        "scope": scope,
        "full_task_coverage": full,
        "batch_complete": batch_complete,
        "task_count": task_count,
        "empty_response_is_full_idle": bool(
            full and batch_complete and task_count == 0
        ),
        "reason": reason,
    }


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
    runtime_selection: Mapping[str, Any] | None = None,
    review_selection: Mapping[str, Any] | None = None,
    last_source_event_at: str | None = None,
    conflicts: list[str] | None = None,
) -> dict[str, Any]:
    if runtime_selection is None:
        runtime, evidence, blocker = _derive_runtime(record)
    else:
        runtime = runtime_selection["state"]
        evidence = runtime_selection["evidence"]
        blocker = runtime_selection["blocker"]

    if review_selection is None:
        review, verdict = _derive_review(record, runtime)
    else:
        review = review_selection["state"]
        verdict = review_selection["verdict"]

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
        "last_source_event_at": last_source_event_at,
        "evidence": evidence,
        "freshness": freshness,
        "duplicate_count": duplicate_count,
    }
    if last_known is not None:
        projected["last_known_runtime_state"] = last_known
    if verdict is not None:
        projected["review_verdict"] = verdict
    if review == REVIEW_CONFLICT:
        projected["review_blocker"] = "conflicting_review_evidence"
    if conflicts:
        projected["conflicts"] = list(conflicts)
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
    try:
        ttl = float(ttl_seconds)
    except (TypeError, ValueError):
        raise ValueError("ttl_seconds must be a finite number >= 0") from None
    if not math.isfinite(ttl) or ttl < 0:
        raise ValueError("ttl_seconds must be a finite number >= 0")
    freshness, observed_iso, freshness_blocker, age_seconds = _freshness(
        observed_at, now_dt, ttl
    )
    observed_dt = _parse_iso(observed_at)

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
        (
            merged,
            merge_warnings,
            runtime_selection,
            review_selection,
            last_event,
            conflicts,
        ) = _merge_duplicates(task_id, group, observed_dt)
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
                runtime_selection=runtime_selection,
                review_selection=review_selection,
                last_source_event_at=last_event,
                conflicts=conflicts,
            )
        )

    runtime_counts = {state: 0 for state in RUNTIME_STATES}
    review_counts = {state: 0 for state in REVIEW_STATES}
    for task in tasks:
        runtime_counts[task["runtime_state"]] += 1
        review_counts[task["review_state"]] += 1

    batch_complete = (
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

    coverage = _coverage(source_name, batch_complete, len(tasks))
    if not tasks and not coverage["full_task_coverage"]:
        warnings.append(
            "empty response from a partial source is not proof that all tasks are idle"
        )

    return {
        "source": source_name,
        "observed_at": observed_iso,
        "projected_at": _iso(now_dt),
        "ttl_seconds": ttl,
        "complete": batch_complete,
        "batch_complete": batch_complete,
        "scope": coverage["scope"],
        "full_task_coverage": coverage["full_task_coverage"],
        "coverage": coverage,
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
