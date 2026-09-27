"""AUTONOMOUS_ADVANCEMENT -- explicit pre-authorized child dispatch after PASS.

AUTONOMOUS_ADVANCEMENT adds the single missing production edge: after an
authoritative terminal ``PASS`` review, an *explicit* ``approved_next_task``
that was supplied by the reviewer may be dispatched as a child task. The worker
and the registry never invent next work: with no ``approved_next_task`` the
review behaves exactly as before.

The edge is fail-closed and exactly-once:

* only a terminal validated ``PASS`` verdict may dispatch a child;
* ``FAIL`` / ``BLOCKED`` / non-terminal / invalid / missing child dispatch
  nothing;
* an atomic parent/review marker records the dispatch so a replay or an
  idempotent ``mark_reviewed`` can never create a second child;
* the marker preserves the parent task id, child task id, dispatch state,
  timestamps and review linkage for audit.

This module is intentionally transport-agnostic: the caller supplies a
``dispatcher`` callable that performs the real dispatch (the Cloudflare Worker
uses its existing ``gpt_task`` repository_dispatch path). When no dispatcher is
available the edge fails closed instead of inventing a local dispatch.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

PASS_VERDICT = "PASS"

DISPATCH_ACTION = "dispatch"
APPROVED_NEXT_TASK_FIELD = "approved_next_task"

DISPATCH_STATE_PENDING = "PENDING"
DISPATCH_STATE_DISPATCHED = "DISPATCHED"
DISPATCH_STATE_FAILED = "FAILED"
DISPATCH_TERMINAL_STATES = frozenset({DISPATCH_STATE_DISPATCHED, DISPATCH_STATE_FAILED})

DISPATCH_REASON_DISPATCHED = "DISPATCHED"
DISPATCH_REASON_ALREADY = "ALREADY_DISPATCHED"
DISPATCH_REASON_VERDICT = "VERDICT_NOT_PASS"
DISPATCH_REASON_NO_CHILD = "NO_APPROVED_NEXT_TASK"
DISPATCH_REASON_INVALID = "INVALID_APPROVED_NEXT_TASK"
DISPATCH_REASON_UNAVAILABLE = "DISPATCH_GATEWAY_UNAVAILABLE"
DISPATCH_REASON_FAILED = "DISPATCH_FAILED"

FORBIDDEN_EXPECTED_PREFIXES = (".github/workflows/",)
FORBIDDEN_EXPECTED_SUBSTRINGS = ("secret", "token", "credential", ".env", ".pem", ".key")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_child_task_id() -> str:
    """Return a fresh canonical child task id (``cf-`` + 12 hex chars)."""
    return "cf-" + uuid.uuid4().hex[:12]


def normalize_approved_next_task(
    value: Any,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Validate an explicit ``approved_next_task`` fail-closed.

    Returns ``(contract, [])`` when the child is a well-formed task contract and
    ``(None, errors)`` otherwise, so the caller can dispatch nothing.
    """
    errors: list[str] = []
    if not isinstance(value, Mapping):
        return None, ["approved_next_task must be an object"]

    goal = str(value.get("goal") or "").strip()
    if not goal:
        errors.append("approved_next_task.goal must be non-empty")

    instructions = value.get("instructions")
    if not isinstance(instructions, (list, tuple)) or not instructions:
        errors.append("approved_next_task.instructions must be a non-empty list")
        instructions = None

    acceptance = value.get("acceptance")
    if not isinstance(acceptance, (list, tuple)) or not acceptance:
        errors.append("approved_next_task.acceptance must be a non-empty list")
        acceptance = None

    expected = value.get("expected_files")
    normalized_expected: list[str] | None = None
    if expected is not None:
        if not isinstance(expected, (list, tuple)):
            errors.append("approved_next_task.expected_files must be a list")
        else:
            normalized_expected = []
            for path in expected:
                text = str(path).strip()
                if not text:
                    errors.append(
                        "approved_next_task.expected_files entries must be non-empty"
                    )
                    continue
                normalized = text.replace("\\", "/")
                low = text.lower()
                if normalized.startswith("/") or ".." in normalized.split("/"):
                    errors.append(f"unsafe expected_file: {text}")
                elif low.startswith(FORBIDDEN_EXPECTED_PREFIXES) or any(
                    marker in low for marker in FORBIDDEN_EXPECTED_SUBSTRINGS
                ):
                    errors.append(f"forbidden expected_file: {text}")
                else:
                    normalized_expected.append(text)

    if errors:
        return None, errors

    contract: dict[str, Any] = {
        "goal": goal,
        "instructions": [str(item) for item in instructions],
        "acceptance": [str(item) for item in acceptance],
    }
    if normalized_expected is not None:
        contract["expected_files"] = normalized_expected
    return contract, []


def _dispatch_accepted(outcome: Any) -> bool:
    if isinstance(outcome, Mapping):
        for key in ("accepted", "ok", "dispatched"):
            if key in outcome:
                return bool(outcome[key])
        return False
    return bool(outcome)


def dispatch_approved_child(
    record: dict[str, Any],
    task_id: str,
    verdict: str,
    approved_next_task: Any,
    dispatcher: Callable[[Mapping[str, Any]], Any] | None,
    *,
    review_timestamp: str | None = None,
    review_note: str | None = None,
) -> dict[str, Any]:
    """Dispatch an explicit pre-authorized child exactly once, fail-closed.

    Mutates ``record`` (``review_dispatch`` marker + ``review_dispatches`` audit
    trail) and returns a structured dispatch assessment. A ``PASS`` verdict plus
    a valid ``approved_next_task`` plus a dispatcher is the *only* path that
    reaches the dispatcher; every other path dispatches nothing.
    """
    base: dict[str, Any] = {
        "parent_task_id": str(task_id),
        "attempted": False,
        "dispatched": False,
        "idempotent": False,
        "child_task_id": None,
        "dispatch_state": None,
        "reason": None,
    }

    if str(verdict).strip().upper() != PASS_VERDICT:
        return {**base, "reason": DISPATCH_REASON_VERDICT}
    if approved_next_task is None:
        return {**base, "reason": DISPATCH_REASON_NO_CHILD}

    existing = record.get("review_dispatch")
    if isinstance(existing, Mapping) and existing.get("child_task_id"):
        return {
            **base,
            "idempotent": True,
            "child_task_id": existing.get("child_task_id"),
            "dispatch_state": existing.get("dispatch_state"),
            "reason": DISPATCH_REASON_ALREADY,
        }

    contract, errors = normalize_approved_next_task(approved_next_task)
    if errors:
        return {
            **base,
            "attempted": True,
            "reason": DISPATCH_REASON_INVALID,
            "errors": errors,
        }
    if not callable(dispatcher):
        return {**base, "attempted": True, "reason": DISPATCH_REASON_UNAVAILABLE}

    child_task_id = new_child_task_id()
    audit: dict[str, Any] = {
        "parent_task_id": str(task_id),
        "child_task_id": child_task_id,
        "review_verdict": PASS_VERDICT,
        "review_timestamp": review_timestamp,
        "review_note": review_note,
        "dispatch_state": DISPATCH_STATE_PENDING,
        "created_at": _utc_now(),
    }
    record["review_dispatch"] = audit

    child = {**contract, "task_id": child_task_id, "parent_task_id": str(task_id)}
    try:
        outcome = dispatcher(child)
    except Exception as exc:  # noqa: BLE001 - fail closed on any dispatcher error
        audit["dispatch_state"] = DISPATCH_STATE_FAILED
        audit["reason"] = DISPATCH_REASON_FAILED
        audit["error"] = f"{type(exc).__name__}: {exc}"
        record.setdefault("review_dispatches", []).append(dict(audit))
        return {
            **base,
            "attempted": True,
            "child_task_id": child_task_id,
            "dispatch_state": DISPATCH_STATE_FAILED,
            "reason": DISPATCH_REASON_FAILED,
        }

    if not _dispatch_accepted(outcome):
        audit["dispatch_state"] = DISPATCH_STATE_FAILED
        audit["reason"] = DISPATCH_REASON_FAILED
        if isinstance(outcome, Mapping):
            audit["dispatch_status"] = outcome.get("dispatch_status")
        record.setdefault("review_dispatches", []).append(dict(audit))
        return {
            **base,
            "attempted": True,
            "child_task_id": child_task_id,
            "dispatch_state": DISPATCH_STATE_FAILED,
            "reason": DISPATCH_REASON_FAILED,
        }

    dispatched_at = _utc_now()
    audit["dispatch_state"] = DISPATCH_STATE_DISPATCHED
    audit["dispatch_status"] = "accepted"
    audit["dispatched_at"] = dispatched_at
    audit["reason"] = DISPATCH_REASON_DISPATCHED
    record.setdefault("review_dispatches", []).append(dict(audit))
    return {
        **base,
        "attempted": True,
        "dispatched": True,
        "child_task_id": child_task_id,
        "dispatch_state": DISPATCH_STATE_DISPATCHED,
        "reason": DISPATCH_REASON_DISPATCHED,
        "dispatched_at": dispatched_at,
    }
