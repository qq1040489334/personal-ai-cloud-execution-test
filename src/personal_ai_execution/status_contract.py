"""PERSONAL_AI_STATUS_CONTRACT_V0.2 -- one authoritative task-status contract.

This module is the single documented source of truth for how a Personal AI
Execution task is represented across GitHub workflow truth, Python result
normalization, Worker responses, EVENT_SYNC and the Task Registry.

Two independent concepts are deliberately never conflated:

* **execution status** -- the machine truth about whether the task ran.
  Values: ``PENDING`` (non-terminal) and ``PASS`` / ``FAIL`` / ``BLOCKED``
  (terminal).
* **review verdict** -- the human decision owned by ``mark_reviewed``.
  Values: ``PASS`` / ``FAIL`` / ``BLOCKED``.

The GitHub Actions workflow conclusion is authoritative whenever it is
available. Self-reported status, artifact presence and commit presence can
never upgrade a non-success conclusion. The normative terminal mapping lives in
:mod:`personal_ai_execution.result_normalization`; this module is the umbrella
lifecycle contract that re-exports it, adds the non-terminal lifecycle status,
and keeps execution status and review verdict explicitly separate.
"""

from __future__ import annotations

from typing import Any, Mapping

from . import result_normalization as _normalization

PENDING = _normalization.PENDING
PASS = _normalization.PASS
FAIL = _normalization.FAIL
BLOCKED = _normalization.BLOCKED

#: Every execution status the contract can emit, in lifecycle order.
EXECUTION_STATUSES = (PENDING, PASS, FAIL, BLOCKED)

#: Terminal execution statuses. Only these may be reviewed.
TERMINAL_STATUSES = frozenset(_normalization.TERMINAL_STATUSES)

#: Non-terminal execution statuses (still in flight / not yet synchronized).
NON_TERMINAL_STATUSES = frozenset({PENDING})

#: Human review verdicts. These are *not* execution statuses.
REVIEW_VERDICTS = (PASS, FAIL, BLOCKED)

#: Review lifecycle states surfaced on registry records.
REVIEW_PENDING = "pending_review"
REVIEW_COMPLETE = "reviewed"
REVIEW_BLOCKED_INSPECTION = "blocked_awaiting_inspection"
REVIEW_LEGACY_ORPHAN = "legacy_orphan"
REVIEW_STATES = frozenset(
    {
        REVIEW_PENDING,
        REVIEW_COMPLETE,
        REVIEW_BLOCKED_INSPECTION,
        REVIEW_LEGACY_ORPHAN,
    }
)

#: Advisory registry statuses: non-authoritative lifecycle values that must be
#: normalized to the non-terminal ``PENDING`` execution status, never to a
#: terminal success.
ADVISORY_LIFECYCLE_STATUSES = frozenset(
    {
        "submitted",
        "pending",
        "queued",
        "created",
        "dispatched",
        "started",
        "in_progress",
        "in-progress",
        "running",
        "unknown",
    }
)

#: Authoritative GitHub workflow conclusion -> canonical execution status.
WORKFLOW_CONCLUSION_TO_STATUS = {
    "success": PASS,
    "failure": FAIL,
    "startup_failure": FAIL,
    "error": FAIL,
    "cancelled": BLOCKED,
    "canceled": BLOCKED,
    "timed_out": BLOCKED,
    "action_required": BLOCKED,
    "stale": BLOCKED,
    "neutral": BLOCKED,
    "skipped": BLOCKED,
}

#: The documented status matrix (also rendered in STATUS_CONTRACT_V0.2.md).
STATUS_MATRIX = (
    {
        "scenario": "workflow success + matching result",
        "workflow_conclusion": "success",
        "execution_status": PASS,
        "terminal": True,
        "authoritative": True,
        "review_verdict_separate": True,
    },
    {
        "scenario": "workflow failure (any self-report)",
        "workflow_conclusion": "failure",
        "execution_status": FAIL,
        "terminal": True,
        "authoritative": True,
        "review_verdict_separate": True,
    },
    {
        "scenario": "workflow cancelled / canceled",
        "workflow_conclusion": "cancelled",
        "execution_status": BLOCKED,
        "terminal": True,
        "authoritative": True,
        "review_verdict_separate": True,
    },
    {
        "scenario": "workflow timed_out / action_required / stale / neutral / skipped",
        "workflow_conclusion": "timed_out",
        "execution_status": BLOCKED,
        "terminal": True,
        "authoritative": True,
        "review_verdict_separate": True,
    },
    {
        "scenario": "success conclusion but expected files missing",
        "workflow_conclusion": "success",
        "execution_status": FAIL,
        "terminal": True,
        "authoritative": True,
        "review_verdict_separate": True,
    },
    {
        "scenario": "unknown / unrecognized conclusion",
        "workflow_conclusion": "unrecognized",
        "execution_status": BLOCKED,
        "terminal": True,
        "authoritative": True,
        "review_verdict_separate": True,
    },
    {
        "scenario": "no conclusion recorded (task still in flight)",
        "workflow_conclusion": None,
        "execution_status": PENDING,
        "terminal": False,
        "authoritative": False,
        "review_verdict_separate": True,
    },
)


def _text(value: Any) -> str:
    return str(value).strip().upper() if value is not None else ""


def canonical_conclusion_status(conclusion: str | None) -> str:
    """Map a GitHub workflow conclusion to its canonical execution status.

    Fail-closed: anything that is not an explicit success is never ``PASS``;
    unrecognized or missing conclusions become ``BLOCKED``.
    """
    return _normalization.normalize_conclusion(conclusion)


def is_execution_status(value: Any) -> bool:
    """Return True when ``value`` is one of the four canonical statuses."""
    return _text(value) in EXECUTION_STATUSES


def is_terminal_status(value: Any) -> bool:
    """Return True when ``value`` is a terminal execution status."""
    return _text(value) in TERMINAL_STATUSES


def normalize_lifecycle_status(
    value: Any, *, conclusion: str | None = None
) -> str:
    """Normalize an advisory registry status to a canonical execution status.

    When an authoritative ``conclusion`` is supplied it always wins. Otherwise a
    terminal value is preserved and every advisory or unknown value collapses to
    the non-terminal ``PENDING`` -- unknown work is never reported as success.
    """
    if conclusion is not None:
        return canonical_conclusion_status(conclusion)
    text = _text(value)
    if text in TERMINAL_STATUSES:
        return text
    return PENDING


def execution_status_for_record(record: Mapping[str, Any]) -> str:
    """Return the canonical execution status for a registry record.

    Preference order: the authoritative workflow conclusion, then the stored
    normalized status, then the advisory lifecycle status.
    """
    if not isinstance(record, Mapping):
        return PENDING
    conclusion = record.get("workflow_conclusion")
    if conclusion is not None:
        return canonical_conclusion_status(conclusion)
    normalized = record.get("normalized_status")
    if _text(normalized) in TERMINAL_STATUSES:
        return _text(normalized)
    return normalize_lifecycle_status(record.get("status"))


def review_verdict_for_record(record: Mapping[str, Any]) -> str | None:
    """Return only the human review verdict, never the execution status."""
    if not isinstance(record, Mapping):
        return None
    verdict = _text(record.get("review_verdict"))
    return verdict or None


def separate_review_fields(record: Mapping[str, Any]) -> dict[str, Any]:
    """Project a record into execution-status and review-verdict fields.

    Returned mapping keeps the two concepts on separate keys so a caller can
    never accidentally read a review verdict as an execution status (or vice
    versa).
    """
    execution_status = execution_status_for_record(record)
    return {
        "execution_status": execution_status,
        "normalized_status": _text(record.get("normalized_status")) or None,
        "terminal": bool(record.get("terminal")),
        "review_verdict": review_verdict_for_record(record),
        "review_state": record.get("review_state"),
        "reviewed": bool(record.get("reviewed")),
    }


def status_matrix() -> tuple[dict[str, Any], ...]:
    """Return the documented status matrix (a defensive copy)."""
    return tuple(dict(row) for row in STATUS_MATRIX)
