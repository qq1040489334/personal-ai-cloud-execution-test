"""PERSONAL_AI_DECISION_INGESTION_CONTRACT_V0.1 -- canonical DECISION records.

This module defines a single, documented, **read-only** contract that maps the
decision evidence Personal AI Execution already produces into one canonical
DECISION record shape, without writing any production state:

* **review verdict** -- the human verdict owned by ``mark_reviewed``
  (``review_verdict`` / ``verdict``), whose vocabulary is
  :data:`personal_ai_execution.status_contract.REVIEW_VERDICTS`;
* **dispatch outcome** -- the exactly-once dispatch-marker outcome written by
  AUTONOMOUS_ADVANCEMENT (``review_dispatch.dispatch_state`` in the Python
  registry, ``task_dispatch_markers.dispatch_state`` in the Worker);
* **promotion decision** -- the ASSET_PROVENANCE_V0.2 ``promotion.decision`` /
  ``promotion_decision`` (and ``promotion.event_id`` / ``promotion_event``);
* **user choice / user outcome** -- explicit human input, represented here as
  first-class DECISION fields so an agent decision can never be promoted as a
  canonical DECISION without the human choice and its observed outcome.

The contract is *fail-closed*. A record missing the review verdict, the
dispatch outcome, the promotion decision, the user choice or the user outcome
(or carrying an unrecognized verdict/dispatch value) is reported as
``INCOMPLETE``, is **never** reported ``VERIFIED``, and lists the exact missing
fields. No metadata is invented: only fields actually present are echoed back.

The field alias table reuses the existing vocabulary rather than introducing a
second one; the provenance aliases are pulled directly from
:data:`personal_ai_execution.provenance_contract.PROVENANCE_FIELD_ALIASES`.
"""

from __future__ import annotations

from typing import Any, Mapping

from . import advancement as _advancement
from . import provenance_contract as _provenance
from .status_contract import REVIEW_VERDICTS as _REVIEW_VERDICTS

#: Version tag of the read-only decision ingestion contract.
DECISION_CONTRACT_VERSION = "PERSONAL_AI_DECISION_INGESTION_V0.1"

#: Canonical DECISION verification states.
STATUS_VERIFIED = "VERIFIED"
STATUS_INCOMPLETE = "INCOMPLETE"
DECISION_STATUSES = (STATUS_VERIFIED, STATUS_INCOMPLETE)

#: Every field the canonical DECISION record can carry, in contract order.
DECISION_FIELDS = (
    "decision_id",
    "task_id",
    "review_verdict",
    "dispatch_outcome",
    "promotion_decision",
    "promotion_event",
    "user_choice",
    "user_outcome",
    "decided_at",
)

#: Fields that must be present for a DECISION to be considered complete.
#: These are the existing review / dispatch / promotion fields plus the
#: explicit user choice and user outcome.
REQUIRED_DECISION_FIELDS = (
    "review_verdict",
    "dispatch_outcome",
    "promotion_decision",
    "user_choice",
    "user_outcome",
)

#: Fields that are only required "where applicable" (identity / timestamps).
OPTIONAL_DECISION_FIELDS = (
    "decision_id",
    "task_id",
    "promotion_event",
    "decided_at",
)

#: Known exactly-once dispatch-marker states (reused from AUTONOMOUS_ADVANCEMENT).
DISPATCH_OUTCOMES = (
    _advancement.DISPATCH_STATE_PENDING,
    _advancement.DISPATCH_STATE_DISPATCHED,
    _advancement.DISPATCH_STATE_FAILED,
)

#: Accepted locations for each canonical field. The first meaningful alias wins,
#: which lets a DECISION be assembled from the existing review verdict record,
#: the dispatch marker, the provenance promotion block or a combined input
#: without inventing duplicate metadata.
DECISION_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "decision_id": ("decision_id", "decision.id"),
    "task_id": ("task_id", "decision.task_id", "task.id"),
    "review_verdict": (
        "review_verdict",
        "review.verdict",
        "review_event.verdict",
        "verdict",
    ),
    "dispatch_outcome": (
        "review_dispatch.dispatch_state",
        "review_dispatch.state",
        "task_dispatch_marker.dispatch_state",
        "dispatch_marker.dispatch_state",
        "dispatch_outcome",
        "dispatch.state",
        "dispatch_state",
    ),
    "promotion_decision": (
        "promotion_decision",
        "promotion.decision",
        "provenance.promotion.decision",
    )
    + tuple(_provenance.PROVENANCE_FIELD_ALIASES["promotion_decision"]),
    "promotion_event": (
        "promotion_event",
        "promotion.event_id",
        "provenance.promotion.event_id",
    )
    + tuple(_provenance.PROVENANCE_FIELD_ALIASES["promotion_event"]),
    "user_choice": (
        "user_choice",
        "user.choice",
        "decision.user_choice",
        "reviewer_choice",
    ),
    "user_outcome": (
        "user_outcome",
        "user.outcome",
        "decision.user_outcome",
        "reviewer_outcome",
    ),
    "decided_at": (
        "decided_at",
        "decision.decided_at",
        "reviewed_at",
        "dispatch.dispatched_at",
        "promotion.decided_at",
    ),
}

#: Documented DECISION decision matrix (also rendered in the contract doc).
DECISION_MATRIX = (
    {
        "scenario": "complete decision evidence",
        "required_fields": (
            "review_verdict + dispatch_outcome + promotion_decision + "
            "user_choice + user_outcome present"
        ),
        "status": STATUS_VERIFIED,
        "complete": True,
        "verified": True,
    },
    {
        "scenario": "review verdict never recorded",
        "required_fields": "review_verdict absent",
        "status": STATUS_INCOMPLETE,
        "complete": False,
        "verified": False,
    },
    {
        "scenario": "dispatch outcome never recorded",
        "required_fields": "dispatch_outcome absent",
        "status": STATUS_INCOMPLETE,
        "complete": False,
        "verified": False,
    },
    {
        "scenario": "promotion decision never recorded",
        "required_fields": "promotion_decision absent",
        "status": STATUS_INCOMPLETE,
        "complete": False,
        "verified": False,
    },
    {
        "scenario": "user choice never captured",
        "required_fields": "user_choice absent",
        "status": STATUS_INCOMPLETE,
        "complete": False,
        "verified": False,
    },
    {
        "scenario": "user outcome never captured",
        "required_fields": "user_outcome absent",
        "status": STATUS_INCOMPLETE,
        "complete": False,
        "verified": False,
    },
    {
        "scenario": "unrecognized verdict or dispatch value",
        "required_fields": "present but not a known vocabulary value",
        "status": STATUS_INCOMPLETE,
        "complete": False,
        "verified": False,
    },
)


def _lookup(mapping: Any, path: str) -> Any:
    current = mapping
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _resolve(record: Mapping[str, Any], field: str) -> Any:
    for alias in DECISION_FIELD_ALIASES[field]:
        value = _lookup(record, alias)
        if _meaningful(value):
            return value
    return None


def normalize_decision(record: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize decision evidence into one canonical DECISION record.

    ``record`` may be a Task Registry record, an append-only review event, a
    dispatch marker, an ASSET_PROVENANCE_V0.2 provenance record, or a combined
    mapping whose keys overlap any of them. The result is fail-closed: only a
    record carrying a recognized review verdict, a known dispatch outcome, a
    promotion decision, a user choice and a user outcome is ``VERIFIED``.

    The input mapping is never mutated and no production state is written.
    """
    source = record if isinstance(record, Mapping) else {}

    fields: dict[str, Any] = {}
    for field in DECISION_FIELDS:
        fields[field] = _resolve(source, field)

    decision_id = fields["decision_id"]
    if decision_id is None and fields["task_id"] is not None:
        decision_id = str(fields["task_id"])
    fields["decision_id"] = decision_id

    missing = [field for field in REQUIRED_DECISION_FIELDS if fields[field] is None]

    invalid: list[str] = []
    verdict = fields["review_verdict"]
    normalized_verdict = _text(verdict).upper() if verdict is not None else None
    if verdict is not None and normalized_verdict not in _REVIEW_VERDICTS:
        invalid.append("review_verdict")

    dispatch = fields["dispatch_outcome"]
    normalized_dispatch = _text(dispatch).upper() if dispatch is not None else None
    if dispatch is not None and normalized_dispatch not in DISPATCH_OUTCOMES:
        invalid.append("dispatch_outcome")

    complete = not missing and not invalid
    verified = complete

    canonical = {
        "decision_id": decision_id,
        "task_id": fields["task_id"],
        "review_verdict": normalized_verdict,
        "dispatch_outcome": normalized_dispatch,
        "promotion_decision": fields["promotion_decision"],
        "promotion_event": fields["promotion_event"],
        "user_choice": fields["user_choice"],
        "user_outcome": fields["user_outcome"],
        "decided_at": fields["decided_at"],
    }

    if verified:
        status = STATUS_VERIFIED
        reason = (
            "decision complete: review verdict, dispatch outcome, promotion "
            "decision, user choice and user outcome are all recorded"
        )
    else:
        status = STATUS_INCOMPLETE
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if invalid:
            details.append("unrecognized " + ", ".join(invalid))
        reason = "decision incomplete: " + "; ".join(details)

    return {
        "contract": DECISION_CONTRACT_VERSION,
        "status": status,
        "complete": complete,
        "verified": verified,
        "missing": missing,
        "invalid": invalid,
        "fields": fields,
        "record": canonical,
        "reason": reason,
    }


def build_decision(
    *,
    task_id: str | None = None,
    review_verdict: str,
    dispatch_outcome: str,
    promotion_decision: str,
    user_choice: Any,
    user_outcome: Any,
    promotion_event: str | None = None,
    decided_at: str | None = None,
    decision_id: str | None = None,
) -> dict[str, Any]:
    """Build a canonical, structurally complete DECISION input record.

    The returned mapping uses the existing nested shapes (``review_dispatch`` for
    the dispatch marker, ``promotion`` for the provenance block) and
    round-trips through :func:`normalize_decision` to ``VERIFIED``.
    """
    record: dict[str, Any] = {
        "decision_id": decision_id or task_id,
        "task_id": task_id,
        "review_verdict": review_verdict,
        "review_dispatch": {"dispatch_state": dispatch_outcome},
        "promotion": {
            "decision": promotion_decision,
            "event_id": promotion_event,
        },
        "user_choice": user_choice,
        "user_outcome": user_outcome,
        "decided_at": decided_at,
    }
    return record


def decision_matrix() -> tuple[dict[str, Any], ...]:
    """Return the documented DECISION matrix (a defensive copy)."""
    return tuple(dict(row) for row in DECISION_MATRIX)
