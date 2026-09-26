"""PERSONAL_AI_TASK_REGISTRY_CLEANUP_V0.1 -- historical Task Registry reconciliation.

Tasks submitted *before* EVENT_SYNC existed could remain stuck in advisory states
such as ``submitted`` / ``blocked`` / ``unknown`` with no terminal normalization.
This module classifies those historical records without mutating or deleting any
audit data. Reconciliation only *adds* derived terminal metadata; it never
removes records, execution evidence, review events, or commits.

Four legacy destinations are distinguished:

``completed_with_result``
    A historical task that has an authoritative result whose normalized status is
    ``PASS``. It becomes discoverable through ``list_pending_results``.
``failed_with_result``
    A historical task that has an authoritative result whose normalized status is
    ``FAIL``. It becomes discoverable through ``list_pending_results``.
``blocked_awaiting_inspection``
    A historical task that is explicitly blocked (or whose normalized result is
    ``BLOCKED``). Records with a result are discoverable for review; result-less
    records remain discoverable only as an inspection item.
``legacy_orphan``
    A historical task with no result that is older than the orphan threshold. It
    is preserved for manual inspection and is never promoted to a pending result.

Records that are already EVENT_SYNC owned (``synced``), already reviewed, or too
recent to judge are reported but left untouched.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from . import result_normalization as _normalization

COMPLETED_WITH_RESULT = "completed_with_result"
FAILED_WITH_RESULT = "failed_with_result"
BLOCKED_AWAITING_INSPECTION = "blocked_awaiting_inspection"
LEGACY_ORPHAN = "legacy_orphan"
ALREADY_SYNCED = "already_synced"
REVIEWED = "reviewed"
IN_PROGRESS = "in_progress"

#: Classes the reconciler may rewrite legacy metadata for.
RECONCILABLE_CLASSES = (
    COMPLETED_WITH_RESULT,
    FAILED_WITH_RESULT,
    BLOCKED_AWAITING_INSPECTION,
    LEGACY_ORPHAN,
)

#: Every class a record can be reported under.
ALL_CLASSES = (
    COMPLETED_WITH_RESULT,
    FAILED_WITH_RESULT,
    BLOCKED_AWAITING_INSPECTION,
    LEGACY_ORPHAN,
    ALREADY_SYNCED,
    REVIEWED,
    IN_PROGRESS,
)

#: Advisory statuses that indicate a pre-EVENT_SYNC record.
LEGACY_STATUSES = frozenset(
    {
        "submitted",
        "pending",
        "queued",
        "in_progress",
        "running",
        "unknown",
        "blocked",
    }
)

#: Advisory statuses that should be surfaced for inspection rather than review.
BLOCKED_HINTS = frozenset(
    {
        "blocked",
        "cancelled",
        "canceled",
        "timed_out",
        "action_required",
        "stale",
    }
)

#: A result-less legacy record older than this is treated as an orphan (15 min).
DEFAULT_ORPHAN_AFTER_SECONDS = 15 * 60


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(value: Any) -> datetime | None:
    """Parse an ISO-8601 timestamp, assuming UTC when no offset is supplied."""
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


def age_seconds(record: Mapping[str, Any], now: datetime | None = None) -> float | None:
    """Return the age of a record, or ``None`` when it has no usable timestamp."""
    created = parse_timestamp(record.get("created_at"))
    if created is None:
        created = parse_timestamp(record.get("updated_at"))
    if created is None:
        return None
    return ((now or utc_now()) - created).total_seconds()


def _class_for_status(status: str | None) -> str:
    normalized = str(status or "").strip().upper()
    if normalized == _normalization.PASS:
        return COMPLETED_WITH_RESULT
    if normalized == _normalization.FAIL:
        return FAILED_WITH_RESULT
    return BLOCKED_AWAITING_INSPECTION


def classify_record(
    record: Mapping[str, Any],
    *,
    execution_result: Mapping[str, Any] | None = None,
    conclusion: str | None = None,
    now: datetime | None = None,
    orphan_after_seconds: int = DEFAULT_ORPHAN_AFTER_SECONDS,
) -> dict[str, Any]:
    """Classify one registry record without mutating it.

    ``execution_result`` / ``conclusion`` let a caller supply freshly discovered
    artifact evidence for a legacy record. When omitted the record's own stored
    evidence is used.
    """
    now = now or utc_now()
    if record.get("synced"):
        return {"classification": ALREADY_SYNCED, "has_result": True, "terminal": True}
    if record.get("reviewed"):
        return {
            "classification": REVIEWED,
            "has_result": bool(record.get("result_available")),
            "terminal": bool(record.get("terminal")),
        }

    result = execution_result
    if result is None:
        result = record.get("execution_result_json")
    resolved_conclusion = conclusion
    if resolved_conclusion is None:
        resolved_conclusion = record.get("workflow_conclusion")

    if result is not None or resolved_conclusion is not None:
        task_result = _normalization.get_task_result(
            str(record.get("task_id")), result, resolved_conclusion
        )
        classification = _class_for_status(task_result["status"])
        return {
            "classification": classification,
            "has_result": True,
            "terminal": True,
            "status": task_result["status"],
            "workflow_conclusion": task_result["workflow_conclusion"],
            "task_result": task_result,
            "execution_result": result,
        }

    if record.get("normalized_status"):
        classification = _class_for_status(record.get("normalized_status"))
        return {
            "classification": classification,
            "has_result": bool(record.get("result_available")),
            "terminal": bool(record.get("terminal")),
            "status": record.get("normalized_status"),
        }

    advisory = str(record.get("status") or "").strip().lower()
    if advisory in BLOCKED_HINTS:
        return {
            "classification": BLOCKED_AWAITING_INSPECTION,
            "has_result": False,
            "terminal": False,
            "status": _normalization.BLOCKED,
        }

    age = age_seconds(record, now)
    if age is not None and age > orphan_after_seconds:
        return {
            "classification": LEGACY_ORPHAN,
            "has_result": False,
            "terminal": False,
            "status": record.get("status"),
        }

    return {
        "classification": IN_PROGRESS,
        "has_result": False,
        "terminal": False,
        "status": record.get("status"),
    }
