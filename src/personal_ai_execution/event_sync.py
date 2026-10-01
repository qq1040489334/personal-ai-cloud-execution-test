"""EVENT_SYNC -- synchronise terminal workflow results into the Task Registry.

EVENT_SYNC turns a completed GitHub Actions workflow result (plus any available
execution artifact / evidence) into a single Task Registry record that becomes
discoverable through :func:`list_pending_results` without an explicit per-task
``get_task_result`` call.

Status normalisation is *not* reimplemented here. The canonical, workflow
authoritative normalisation from
:mod:`personal_ai_execution.result_normalization` is the single source of truth,
so a terminal workflow conclusion always wins over the advisory
``execution_result.json`` self-report.

Synchronisation is idempotent and side-effect free with respect to review:
reprocessing the same terminal task never creates a duplicate pending-review
record and never records a duplicate review event. EVENT_SYNC never calls
``mark_reviewed`` automatically and never invents a follow-up task.

Since PERSONAL_AI_AUTONOMOUS_ADVANCEMENT_V0.2 an *explicit* pre-authorized
``approved_next_task`` may be dispatched exactly once after an authoritative
terminal ``PASS`` review (see :mod:`personal_ai_execution.advancement`). With no
``approved_next_task`` review closure behaves exactly as before and nothing is
dispatched.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from . import advancement as _advancement
from . import reconciliation as _reconciliation
from . import result_normalization as _normalization
from . import review_assistant as _review_assistant
from . import status_contract as _status_contract

REVIEW_ACTION = "review"
REVIEW_VERDICTS = ("PASS", "FAIL", "BLOCKED")
PENDING_REVIEW = "pending_review"
REVIEWED_STATE = "reviewed"
SYNC_EVENT = "event_sync"
RECONCILE_ACTION = "reconcile"

#: Reason code returned by :func:`review_eligibility` for a reviewable task.
ELIGIBLE_REASON_CODE = "ELIGIBLE"

#: Fixed task id used by the golden EVENT_SYNC discovery path.
GOLDEN_TASK_ID = "cf-0564e6c347b8"

#: Optional, additive lineage metadata fields on a canonical registry record.
LINEAGE_PROJECT_FIELD = "project_id"
LINEAGE_ROOT_FIELD = "root_task_id"
LINEAGE_PARENT_FIELD = "parent_task_id"

#: Lineage kind returned by :func:`resolve_lineage`.
LINEAGE_KIND_PROJECT = "project"
LINEAGE_KIND_ROOT = "root"

#: Hard bound on parent-chain walking so a cyclic chain can never loop forever.
MAX_LINEAGE_WALK = 64

#: Process-configurable active-project override for Supervisor consumers. This
#: reuses the existing environment configuration mechanism so the active project
#: is configurable instead of being permanently hard-coded.
ACTIVE_PROJECT_ENV = "PERSONAL_AI_ACTIVE_PROJECT_ID"

#: Default active-project lineage (Cloud Assets Activation) used only when a
#: consumer passes no explicit scope and ``ACTIVE_PROJECT_ENV`` is unset.
DEFAULT_ACTIVE_PROJECT_ID = "cloud-assets-activation"

#: Kind emitted for the single bounded next_action of a Supervisor report.
NEXT_ACTION_REVIEW = "REVIEW_PENDING_RESULT"

#: Optional process config for the live Supervisor/advancement caller. This is
#: the caller-level switch that makes the existing caller request active-project
#: scoped pending results without changing the unscoped compatibility surface
#: used by every other caller. Unset (or truthy) means the live caller requests
#: the configured active-project lineage; a falsey value opts the caller back
#: into the historical unscoped behavior.
SUPERVISOR_ACTIVE_PROJECT_ENV = "PERSONAL_AI_SUPERVISOR_ACTIVE_PROJECT"

#: Truthy/falsey spellings accepted by :func:`supervisor_active_project_enabled`.
_FALSEY_CONFIG = frozenset({"0", "false", "no", "off", ""})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def supervisor_active_project_enabled(
    env: Mapping[str, Any] | None = None,
) -> bool:
    """Return whether the live Supervisor/advancement caller scopes by default.

    The caller is enabled unless ``PERSONAL_AI_SUPERVISOR_ACTIVE_PROJECT`` is set
    to a falsey value, so the existing caller path requests active-project scoped
    pending results by default while an operator can still opt out explicitly.
    """
    environ = env if env is not None else os.environ
    raw = environ.get(SUPERVISOR_ACTIVE_PROJECT_ENV)
    if raw is None:
        return True
    return str(raw).strip().lower() not in _FALSEY_CONFIG


def active_project_scope(
    project_id: Any = None,
    root_task_id: Any = None,
    *,
    env: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Resolve the active-project lineage scope for a Supervisor consumer.

    Precedence is: an explicit ``project_id`` / ``root_task_id`` argument, then
    the ``PERSONAL_AI_ACTIVE_PROJECT_ID`` environment override, then the Cloud
    Assets Activation default. ``None`` is returned only when every source is
    empty, so a caller that intentionally omits scope keeps the historical
    unscoped behavior.
    """
    explicit_project = str(project_id).strip() if project_id else ""
    explicit_root = str(root_task_id).strip() if root_task_id else ""
    if explicit_root and not explicit_project:
        return {LINEAGE_ROOT_FIELD: explicit_root}
    if explicit_project:
        return {LINEAGE_PROJECT_FIELD: explicit_project}
    environ = env if env is not None else os.environ
    configured = str(environ.get(ACTIVE_PROJECT_ENV) or "").strip()
    if configured:
        return {LINEAGE_PROJECT_FIELD: configured}
    default = str(DEFAULT_ACTIVE_PROJECT_ID or "").strip()
    if default:
        return {LINEAGE_PROJECT_FIELD: default}
    return None


def resolve_lineage(
    record: Mapping[str, Any], index: Mapping[str, Any]
) -> tuple[str, str]:
    """Resolve a record to a single deterministic lineage key, fail-closed.

    Resolution precedence is ``project_id`` -> ``root_task_id`` -> walk the
    ``parent_task_id`` chain -> singleton lineage of the record's own task id.
    The walk is bounded and cycle-aware, and an unknown parent stops the walk so
    a record can never be cross-associated with an unrelated project.
    """
    task_id = str(record.get("task_id") or "")
    project_id = record.get(LINEAGE_PROJECT_FIELD)
    if project_id:
        return LINEAGE_KIND_PROJECT, str(project_id)
    root = record.get(LINEAGE_ROOT_FIELD)
    if root:
        return LINEAGE_KIND_ROOT, str(root)

    parent = record.get(LINEAGE_PARENT_FIELD)
    seen: set[str] = set()
    while parent and str(parent) not in seen and len(seen) < MAX_LINEAGE_WALK:
        seen.add(str(parent))
        ancestor = index.get(str(parent))
        if not isinstance(ancestor, Mapping):
            break  # unknown parent -> stop, fail closed
        ancestor_root = ancestor.get(LINEAGE_ROOT_FIELD)
        if ancestor_root:
            return LINEAGE_KIND_ROOT, str(ancestor_root)
        ancestor_project = ancestor.get(LINEAGE_PROJECT_FIELD)
        if ancestor_project:
            return LINEAGE_KIND_PROJECT, str(ancestor_project)
        parent = ancestor.get(LINEAGE_PARENT_FIELD)
    return LINEAGE_KIND_ROOT, task_id


def lineage_in_scope(
    record: Mapping[str, Any],
    scope: Mapping[str, Any] | None,
    index: Mapping[str, Any],
) -> bool:
    """Return ``True`` when ``record`` belongs to the requested lineage scope.

    ``scope is None`` (or an empty scope) selects everything, preserving the
    historical unscoped behavior. A scope with ``project_id`` or
    ``root_task_id`` selects exactly the records whose resolved lineage key
    matches; everything else is excluded without mutation.
    """
    if not scope:
        return True
    project_id = scope.get(LINEAGE_PROJECT_FIELD)
    root_task_id = scope.get(LINEAGE_ROOT_FIELD)
    if not project_id and not root_task_id:
        return True
    kind, key = resolve_lineage(record, index)
    if project_id:
        return kind == LINEAGE_KIND_PROJECT and key == str(project_id)
    return kind == LINEAGE_KIND_ROOT and key == str(root_task_id)


def _normalized_status(value: Any) -> str:
    return str(value).strip().upper() if value is not None else ""


def validated_review_result(record: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return the validated, task-id-matching result for ``record``.

    A result qualifies for review only when it is a stored ``task_result``
    mapping that (a) carries a ``task_id`` equal to the record's ``task_id`` and
    (b) has a terminal status. Anything missing, malformed, non-terminal or
    mismatched returns ``None`` so the caller fails closed.
    """
    task_id = str(record.get("task_id") or "")
    if not task_id:
        return None
    evidence = record.get("evidence")
    result = evidence.get("task_result") if isinstance(evidence, Mapping) else None
    if not isinstance(result, Mapping):
        return None
    result_task_id = result.get("task_id")
    if result_task_id is None or str(result_task_id) != task_id:
        return None
    if _normalized_status(result.get("status")) not in _normalization.TERMINAL_STATUSES:
        return None
    if result.get("terminal") is False:
        return None
    return dict(result)


def review_eligibility(record: Mapping[str, Any]) -> dict[str, Any]:
    """Assess, fail-closed, whether a task record may be marked reviewed.

    Review closure requires an *authoritative terminal execution state* plus a
    *validated result whose ``task_id`` matches* the task. Every rejection is
    returned as a structured ``reason_code`` + human ``reason`` so the mark
    reviewed audit event can preserve why the gate opened or closed.
    """
    task_id = str(record.get("task_id") or "")
    assessment: dict[str, Any] = {
        "task_id": task_id or None,
        "eligible": False,
        "reason_code": None,
        "reason": None,
        "status": None,
        "result_task_id": None,
    }

    def reject(code: str, reason: str) -> dict[str, Any]:
        assessment["reason_code"] = code
        assessment["reason"] = reason
        return assessment

    if not task_id:
        return reject("MISSING_TASK_ID", "task record has no task_id")

    normalized_status = _normalized_status(record.get("normalized_status"))
    if not record.get("terminal"):
        return reject(
            "NON_TERMINAL",
            "task has no authoritative terminal execution state",
        )
    if normalized_status not in _normalization.TERMINAL_STATUSES:
        return reject(
            "NON_TERMINAL_STATUS",
            f"normalized status {normalized_status or None!r} is not terminal; "
            f"allowed: {', '.join(sorted(_normalization.TERMINAL_STATUSES))}",
        )
    if not record.get("result_available"):
        return reject(
            "RESULT_UNAVAILABLE",
            "task has no validated result available for review",
        )

    evidence = record.get("evidence")
    stored = evidence.get("task_result") if isinstance(evidence, Mapping) else None
    if not isinstance(stored, Mapping):
        return reject("MISSING_RESULT", "task has no stored task_result to validate")
    stored_task_id = stored.get("task_id")
    if stored_task_id is None or str(stored_task_id) != task_id:
        return reject(
            "RESULT_TASK_ID_MISMATCH",
            f"result task_id {stored_task_id!r} does not match task {task_id}",
        )
    stored_status = _normalized_status(stored.get("status"))
    if stored_status not in _normalization.TERMINAL_STATUSES:
        return reject(
            "NON_TERMINAL_RESULT",
            f"validated result status {stored_status or None!r} is not terminal",
        )
    if stored.get("terminal") is False:
        return reject(
            "NON_TERMINAL_RESULT",
            "validated result reports terminal=False",
        )
    if stored_status != normalized_status:
        return reject(
            "RESULT_STATUS_MISMATCH",
            f"result status {stored_status} disagrees with registry status "
            f"{normalized_status}",
        )

    assessment["eligible"] = True
    assessment["reason_code"] = ELIGIBLE_REASON_CODE
    assessment["status"] = normalized_status
    assessment["result_task_id"] = str(stored_task_id)
    assessment["reason"] = (
        f"task {task_id} has terminal status {normalized_status} and a "
        f"validated result whose task_id matches"
    )
    return assessment


class EventSyncRegistry:
    """Task Registry that ingests terminal workflow results via EVENT_SYNC.

    The registry preserves the ``submit_task`` / ``get_task_result`` /
    ``list_pending_results`` / ``mark_reviewed`` contracts: it never infers a
    verdict and never auto-reviews. It never invents a next task; it only
    dispatches an explicit pre-authorized ``approved_next_task`` exactly once
    after an authoritative terminal ``PASS`` review.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}
        self._review_events: list[dict[str, Any]] = []
        self._sync_events: list[dict[str, Any]] = []
        self._reconciliation_events: list[dict[str, Any]] = []

    # -- contract-preserved surface -------------------------------------
    def submit_task(
        self,
        task_id: Any = None,
        goal: str = "",
        status: str = _normalization.PENDING,
        requires_review: bool = True,
        **extra: Any,
    ) -> dict[str, Any]:
        """Register a task without judging or reviewing it."""
        if isinstance(task_id, Mapping):
            payload = dict(task_id)
            task_id = payload.get("task_id", task_id)
            goal = payload.get("goal", goal)
            status = payload.get("status", status)
            requires_review = payload.get("requires_review", requires_review)
            extra = {
                **{
                    key: value
                    for key, value in payload.items()
                    if key
                    not in ("task_id", "goal", "status", "requires_review")
                },
                **extra,
            }
        if not task_id:
            raise ValueError("submit_task requires a task_id")
        record = self._tasks.get(str(task_id))
        if record is None:
            timestamp = _utc_now()
            record = {
                "task_id": str(task_id),
                "goal": goal,
                "status": status,
                "created_at": timestamp,
                "updated_at": timestamp,
                "requires_review": bool(requires_review),
                "reviewed": False,
                "review_verdict": None,
                "reviewed_at": None,
                "review_note": None,
                "review_reason": None,
                "review_reason_code": None,
                "result_available": False,
                "terminal": False,
                "normalized_status": None,
                "workflow_conclusion": None,
                "review_state": None,
                "synced": False,
                "sync_fingerprint": None,
                "legacy": False,
                "reconciled": False,
                "reconciliation_class": None,
                "reconciliation_fingerprint": None,
                "reconciled_at": None,
                "legacy_original_status": None,
                "execution_result_json": None,
                "evidence": {},
                "review_events": [],
                "reconciliation_events": [],
                "review_dispatch": None,
                "review_dispatches": [],
            }
            self._tasks[str(task_id)] = record
        else:
            record["goal"] = goal or record["goal"]
            record["status"] = status or record["status"]
            record["requires_review"] = bool(requires_review)
        for key, value in extra.items():
            if key in ("created_at", "updated_at") and value is not None:
                record[key] = value
            else:
                record.setdefault(key, value)
        return dict(record)

    def _result_payload(
        self, record: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Return a payload that keeps execution status and review separate.

        ``status`` / ``normalized_status`` / ``execution_status`` always carry
        the execution state; ``review_verdict`` carries the human verdict (or
        ``None``). The two are never merged.
        """
        result = dict(payload)
        result.setdefault("normalized_status", result.get("status"))
        result["execution_status"] = result.get("status")
        result["task_id"] = record.get("task_id")
        result["review_verdict"] = record.get("review_verdict")
        result["review_state"] = record.get("review_state")
        return result

    def _store_canonical_result(
        self, record: dict[str, Any], canonical: Mapping[str, Any]
    ) -> None:
        """Write an authoritative terminal execution state back to ``record``.

        This is the single write-back used by EVENT_SYNC and by result discovery
        so the Task Registry can never stay stale as ``submitted`` after a
        terminal workflow result is known. It never touches review state other
        than to keep an already-recorded verdict.
        """
        record["status"] = canonical["status"]
        record["normalized_status"] = canonical["status"]
        record["workflow_conclusion"] = canonical["workflow_conclusion"]
        record["terminal"] = bool(canonical["terminal"])
        record["result_available"] = True
        record["requires_review"] = True
        record["synced"] = True
        record["sync_fingerprint"] = "|".join(
            (str(canonical["status"]), str(canonical["workflow_conclusion"]))
        )
        if record.get("reviewed"):
            record["review_state"] = REVIEWED_STATE
        else:
            record["review_state"] = PENDING_REVIEW
        evidence = dict(record.get("evidence") or {})
        evidence.update(
            {
                "workflow_conclusion": canonical["workflow_conclusion"],
                "normalized_status": canonical["status"],
                "conclusion_authoritative": canonical["conclusion_authoritative"],
                "conclusion_result_mismatch": canonical["conclusion_result_mismatch"],
                "task_result": dict(canonical),
                "reason": canonical["reason"],
            }
        )
        record["evidence"] = evidence

    def get_task_result(self, task_id: str) -> dict[str, Any]:
        """Return the stored workflow-authoritative task result payload.

        Reading a task whose workflow conclusion is known also writes the
        synchronized terminal execution state back onto the registry record, so
        discovery through :meth:`get_task_result` cannot leave the registry stale
        as ``submitted``. A task with no authoritative conclusion yet is reported
        as the non-terminal ``PENDING`` execution status.
        """
        record = self._tasks.get(str(task_id))
        if record is None:
            raise KeyError(f"unknown task_id: {task_id}")
        execution_result = record.get("execution_result_json")
        conclusion = record.get("workflow_conclusion")
        if conclusion is None:
            conclusion = _normalization.workflow_conclusion(execution_result)
        if conclusion is not None:
            # Re-derive from the authoritative conclusion so the overall status
            # can never disagree with a (possibly updated) workflow conclusion.
            canonical = _normalization.get_task_result(
                str(task_id), execution_result, conclusion
            )
            self._store_canonical_result(record, canonical)
            return self._result_payload(record, canonical)
        payload = (record.get("evidence") or {}).get("task_result")
        if isinstance(payload, Mapping):
            # Discovered / reconciled result that carries no workflow
            # conclusion of its own.
            return self._result_payload(record, payload)
        lifecycle = _status_contract.normalize_lifecycle_status(record.get("status"))
        return self._result_payload(
            record,
            {
                "task_id": str(task_id),
                "status": lifecycle,
                "workflow_conclusion": None,
                "conclusion_authoritative": False,
                "conclusion_result_mismatch": False,
                "missing_expected_files": [],
                "terminal": False,
                "reason": (
                    "no authoritative workflow conclusion recorded; task is "
                    "not terminal"
                ),
            },
        )

    def list_pending_results(
        self, scope: Mapping[str, Any] | None = None
    ) -> Any:
        """Return every terminal, unreviewed task awaiting human review.

        Discovery needs no manual ``get_task_result`` call: EVENT_SYNC stores the
        normalized status on the registry record itself.

        With no ``scope`` the return value is the historical list, unchanged.
        With an explicit lineage ``scope`` (``{"project_id": ...}`` or
        ``{"root_task_id": ...}``) the return value is a report mapping whose
        ``pending``/``pending_review`` entries are restricted to the requested
        lineage and whose ``excluded_by_lineage`` count proves that unrelated
        historical backlog was excluded, never mutated or hidden.
        """
        index = {
            str(record.get("task_id")): record
            for record in self._tasks.values()
            if record.get("task_id")
        }
        pending: list[dict[str, Any]] = []
        excluded = 0
        for record in self._tasks.values():
            if not record.get("terminal") or not record.get("result_available"):
                continue
            if not record.get("requires_review"):
                continue
            if record.get("reviewed"):
                continue
            if not lineage_in_scope(record, scope, index):
                excluded += 1
                continue
            item = dict(record)
            item["review_state"] = PENDING_REVIEW
            kind, key = resolve_lineage(record, index)
            item["lineage"] = {"kind": kind, "key": key}
            pending.append(item)
        pending.sort(key=lambda item: item["task_id"])
        if not scope:
            return pending
        return {
            "pending": pending,
            "pending_review": pending,
            "scope": dict(scope),
            "excluded_by_lineage": excluded,
            "counts": {"pending_review": len(pending), "excluded_by_lineage": excluded},
        }

    def mark_reviewed(
        self,
        task_id: Any = None,
        verdict: str | None = None,
        note: str | None = None,
        approved_next_task: Any = None,
        dispatcher: Callable[[Mapping[str, Any]], Any] | None = None,
    ) -> dict[str, Any]:
        """Record an explicit human review verdict for an eligible task.

        Fail-closed: review closure is allowed only when the task has an
        authoritative terminal execution state and a validated result whose
        ``task_id`` matches. Eligible completed tasks accept ``PASS`` / ``FAIL``
        / ``BLOCKED``. An identical repeated verdict is idempotent; a conflicting
        second verdict is rejected.

        When an explicit ``approved_next_task`` is supplied and ``verdict`` is
        ``PASS``, it is dispatched as a child through ``dispatcher`` exactly once
        (guarded by a persisted review/dispatch marker). With no
        ``approved_next_task`` nothing is dispatched and the review is unchanged.
        """
        if isinstance(task_id, Mapping):
            payload = dict(task_id)
            task_id = payload.get("task_id", task_id)
            verdict = payload.get("verdict", verdict)
            note = payload.get("note", note)
            if approved_next_task is None:
                approved_next_task = payload.get(_advancement.APPROVED_NEXT_TASK_FIELD)
            if dispatcher is None:
                dispatcher = payload.get("dispatcher")
        if not task_id:
            raise ValueError("mark_reviewed requires a task_id")
        normalized = str(verdict).strip().upper() if verdict is not None else ""
        if normalized not in REVIEW_VERDICTS:
            raise ValueError(
                f"invalid verdict: {verdict!r} (allowed: {', '.join(REVIEW_VERDICTS)})"
            )
        record = self._tasks.get(str(task_id))
        if record is None:
            raise KeyError(f"unknown task_id: {task_id}")
        if record.get("reviewed"):
            if record.get("review_verdict") == normalized:
                dispatch = _advancement.dispatch_approved_child(
                    record,
                    str(task_id),
                    normalized,
                    approved_next_task,
                    dispatcher,
                    review_timestamp=record.get("reviewed_at"),
                    review_note=record.get("review_note"),
                )
                result = dict(record)
                result["idempotent"] = True
                result["child_dispatch"] = dispatch
                return result
            raise ValueError(
                f"review already recorded: {record.get('review_verdict')}; "
                f"conflicting verdict {normalized} rejected"
            )
        eligibility = review_eligibility(record)
        if not eligibility["eligible"]:
            raise ValueError(
                f"task {task_id} is not reviewable "
                f"({eligibility['reason_code']}): {eligibility['reason']}"
            )
        timestamp = _utc_now()
        event = {
            "task_id": str(task_id),
            "action": REVIEW_ACTION,
            "verdict": normalized,
            "timestamp": timestamp,
            "note": note,
            "reason": eligibility["reason"],
            "reason_code": eligibility["reason_code"],
            "reviewed_status": eligibility["status"],
            "result_task_id": eligibility["result_task_id"],
        }
        record["reviewed"] = True
        record["review_verdict"] = normalized
        record["reviewed_at"] = timestamp
        record["review_note"] = note
        record["review_reason"] = eligibility["reason"]
        record["review_reason_code"] = eligibility["reason_code"]
        record["review_state"] = REVIEWED_STATE
        record.setdefault("review_events", []).append(event)
        self._review_events.append(event)
        dispatch = _advancement.dispatch_approved_child(
            record,
            str(task_id),
            normalized,
            approved_next_task,
            dispatcher,
            review_timestamp=timestamp,
            review_note=note,
        )
        result = dict(record)
        result["review_event"] = event
        result["child_dispatch"] = dispatch
        result["idempotent"] = False
        return result

    def recommend_review(self, task_id: str) -> dict[str, Any]:
        """Return an advisory review recommendation without mutating state.

        This is read-only: it never calls ``mark_reviewed`` and never changes the
        record. Human review remains the final gate.
        """
        record = self._tasks.get(str(task_id))
        if record is None:
            raise KeyError(f"unknown task_id: {task_id}")
        return _review_assistant.build_review_recommendation(record)

    def list_review_recommendations(
        self, scope: Mapping[str, Any] | None = None
    ) -> Any:
        """Return recommendations for pending-review tasks, in order.

        With no ``scope`` the return value is the historical list of advisory
        recommendations, unchanged. With an explicit lineage ``scope`` the return
        value is an audit report whose ``recommendations`` are restricted to the
        requested lineage and whose ``excluded_by_lineage`` count proves the
        unrelated historical backlog was excluded, never mutated.
        """
        pending_report = self.list_pending_results(scope)
        if not scope:
            return [
                _review_assistant.build_review_recommendation(record)
                for record in pending_report
            ]
        records = pending_report["pending"]
        return {
            "recommendations": [
                _review_assistant.build_review_recommendation(record)
                for record in records
            ],
            "pending": records,
            "pending_review": records,
            "scope": dict(scope),
            "excluded_by_lineage": pending_report["excluded_by_lineage"],
            "counts": dict(pending_report["counts"]),
        }

    def supervisor_pending_review_report(
        self,
        project_id: Any = None,
        root_task_id: Any = None,
        *,
        active_project: bool | None = None,
        env: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Deterministically select the active-project pending-review backlog.

        This is the Supervisor/advancement consumer entry point, and the live
        caller path requests active-project scope through ``active_project`` or
        the ``PERSONAL_AI_SUPERVISOR_ACTIVE_PROJECT`` caller config. It resolves
        the active Cloud Assets Activation lineage (overridable with an explicit
        ``project_id`` / ``root_task_id`` or the ``PERSONAL_AI_ACTIVE_PROJECT_ID``
        environment variable), reads only that lineage's pending results, builds
        advisory recommendations, reports the ``excluded_by_lineage`` audit count
        and returns exactly one bounded ``next_action``. Historical singletons
        are never selected and never mutated. Passing ``active_project=False``
        (or a falsey caller config) preserves the historical unscoped behavior
        for callers that intentionally omit scope.
        """
        explicit_scope = bool(
            (str(project_id).strip() if project_id else "")
            or (str(root_task_id).strip() if root_task_id else "")
        )
        if explicit_scope:
            scope = active_project_scope(project_id, root_task_id, env=env)
        else:
            enabled = (
                supervisor_active_project_enabled(env)
                if active_project is None
                else bool(active_project)
            )
            scope = active_project_scope(env=env) if enabled else None
        if scope:
            report = self.list_review_recommendations(scope)
        else:
            pending = self.list_pending_results()
            report = {
                "recommendations": [
                    _review_assistant.build_review_recommendation(record)
                    for record in pending
                ],
                "pending": pending,
                "pending_review": pending,
                "scope": None,
                "excluded_by_lineage": 0,
                "counts": {
                    "pending_review": len(pending),
                    "excluded_by_lineage": 0,
                },
            }
        recommendations = report["recommendations"]
        selected = recommendations[0] if recommendations else None
        report["next_action"] = (
            {
                "kind": NEXT_ACTION_REVIEW,
                "task_id": selected["task_id"],
                "recommendation": selected["verdict"],
                "requires_human_review": selected["requires_human_review"],
            }
            if selected
            else None
        )
        return report

    def get_review_events(self, task_id: str | None = None) -> list[dict[str, Any]]:
        if task_id is None:
            return [dict(event) for event in self._review_events]
        return [
            dict(event)
            for event in self._review_events
            if event.get("task_id") == str(task_id)
        ]

    def get_sync_events(self, task_id: str | None = None) -> list[dict[str, Any]]:
        if task_id is None:
            return [dict(event) for event in self._sync_events]
        return [
            dict(event)
            for event in self._sync_events
            if event.get("task_id") == str(task_id)
        ]

    def get_reconciliation_events(
        self, task_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Return the append-only reconciliation audit trail."""
        if task_id is None:
            return [dict(event) for event in self._reconciliation_events]
        return [
            dict(event)
            for event in self._reconciliation_events
            if event.get("task_id") == str(task_id)
        ]

    # -- TASK_REGISTRY_CLEANUP_V0.1 --------------------------------------
    def audit_historical_tasks(
        self,
        *,
        discovered_results: Mapping[str, Mapping[str, Any]] | None = None,
        conclusions: Mapping[str, str] | None = None,
        now: datetime | None = None,
        orphan_after_seconds: int = _reconciliation.DEFAULT_ORPHAN_AFTER_SECONDS,
    ) -> dict[str, Any]:
        """Classify every historical record without mutating the registry."""
        return self.reconcile_historical_tasks(
            discovered_results=discovered_results,
            conclusions=conclusions,
            now=now,
            orphan_after_seconds=orphan_after_seconds,
            dry_run=True,
        )

    def reconcile_historical_tasks(
        self,
        *,
        discovered_results: Mapping[str, Mapping[str, Any]] | None = None,
        conclusions: Mapping[str, str] | None = None,
        now: datetime | None = None,
        orphan_after_seconds: int = _reconciliation.DEFAULT_ORPHAN_AFTER_SECONDS,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Reconcile pre-EVENT_SYNC task states without deleting any history.

        Only records that predate EVENT_SYNC are touched. Already-synced records
        keep using the EVENT_SYNC path and are reported as ``already_synced``.
        The operation is idempotent: re-running it never duplicates pending-review
        entries or reconciliation events, and it never deletes evidence, review
        events, or commits.
        """
        discovered = dict(discovered_results or {})
        discovered_conclusions = dict(conclusions or {})
        report: dict[str, Any] = {
            "dry_run": bool(dry_run),
            "idempotent": True,
            "total": len(self._tasks),
            "reconciled": [],
            "skipped": [],
            "counts": {name: 0 for name in _reconciliation.ALL_CLASSES},
        }
        for record in list(self._tasks.values()):
            task_id = str(record["task_id"])
            assessment = _reconciliation.classify_record(
                record,
                execution_result=discovered.get(task_id),
                conclusion=discovered_conclusions.get(task_id),
                now=now,
                orphan_after_seconds=orphan_after_seconds,
            )
            classification = assessment["classification"]
            report["counts"][classification] += 1
            if classification in (
                _reconciliation.ALREADY_SYNCED,
                _reconciliation.REVIEWED,
                _reconciliation.IN_PROGRESS,
            ):
                report["skipped"].append(
                    {
                        "task_id": task_id,
                        "classification": classification,
                        "reason": "event-sync owned / reviewed / still in flight",
                    }
                )
                continue
            entry = {
                "task_id": task_id,
                "classification": classification,
                "previous_status": (
                    record.get("legacy_original_status") or record.get("status")
                ),
                "status": assessment.get("status"),
                "has_result": bool(assessment.get("has_result")),
            }
            if not dry_run:
                changed = self._apply_reconciliation(
                    record, assessment, task_id, now=now
                )
                entry["changed"] = changed
                if changed:
                    report["idempotent"] = False
            report["reconciled"].append(entry)
        report["counts"]["total"] = len(self._tasks)
        return report

    def _apply_reconciliation(
        self,
        record: dict[str, Any],
        assessment: Mapping[str, Any],
        task_id: str,
        *,
        now: datetime | None = None,
    ) -> bool:
        classification = str(assessment["classification"])
        timestamp = (now or _reconciliation.utc_now()).isoformat()
        record["legacy"] = True
        if record.get("legacy_original_status") is None:
            record["legacy_original_status"] = record.get("status")
        if record.get("reconciled_at") is None:
            record["reconciled_at"] = timestamp

        task_result = assessment.get("task_result")
        if task_result is not None:
            record["status"] = task_result["status"]
            record["normalized_status"] = task_result["status"]
            record["workflow_conclusion"] = task_result["workflow_conclusion"]
            evidence = dict(record.get("evidence") or {})
            evidence.setdefault("task_result", dict(task_result))
            evidence["reconciliation_class"] = classification
            evidence["conclusion_authoritative"] = task_result[
                "conclusion_authoritative"
            ]
            evidence["conclusion_result_mismatch"] = task_result[
                "conclusion_result_mismatch"
            ]
            record["evidence"] = evidence
            execution_result = assessment.get("execution_result")
            if isinstance(execution_result, Mapping) and record.get(
                "execution_result_json"
            ) is None:
                record["execution_result_json"] = dict(execution_result)

        if assessment.get("has_result"):
            record["terminal"] = True
            record["result_available"] = True
            record["requires_review"] = True
            if not record.get("reviewed"):
                record["review_state"] = PENDING_REVIEW
        elif classification == _reconciliation.BLOCKED_AWAITING_INSPECTION:
            record["requires_inspection"] = True
            record["review_state"] = _reconciliation.BLOCKED_AWAITING_INSPECTION
            if assessment.get("ambiguous"):
                record["ambiguous"] = True
                ambiguous_result = assessment.get("execution_result")
                if isinstance(ambiguous_result, Mapping) and record.get(
                    "execution_result_json"
                ) is None:
                    record["execution_result_json"] = dict(ambiguous_result)
        elif classification == _reconciliation.LEGACY_ORPHAN:
            record["requires_inspection"] = True
            record["orphaned"] = True
            record["review_state"] = _reconciliation.LEGACY_ORPHAN

        fingerprint = "|".join(
            (
                classification,
                str(assessment.get("status")),
                str(assessment.get("workflow_conclusion")),
            )
        )
        already = bool(
            record.get("reconciled")
            and record.get("reconciliation_fingerprint") == fingerprint
        )
        record["reconciled"] = True
        record["reconciliation_class"] = classification
        record["reconciliation_fingerprint"] = fingerprint
        if already:
            return False
        event = {
            "task_id": task_id,
            "action": RECONCILE_ACTION,
            "classification": classification,
            "from_status": record.get("legacy_original_status"),
            "to_status": record.get("normalized_status") or record.get("status"),
            "timestamp": timestamp,
        }
        record.setdefault("reconciliation_events", []).append(event)
        self._reconciliation_events.append(event)
        return True

    # -- EVENT_SYNC ------------------------------------------------------
    def sync_terminal_result(
        self,
        task_id: str,
        execution_result: Mapping[str, Any] | None = None,
        workflow_conclusion_value: str | None = None,
        *,
        artifact_present: bool | None = None,
        commit_present: bool | None = None,
        evidence: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Synchronise one terminal workflow result into the registry.

        Only results carrying a workflow conclusion are accepted: EVENT_SYNC
        exists to ingest *completed* workflow runs, not to guess at in-flight
        ones. The returned ``status`` is always the canonical normalized status.
        """
        if not task_id:
            raise ValueError("sync_terminal_result requires a task_id")
        task_id = str(task_id)
        conclusion = workflow_conclusion_value
        if conclusion is None:
            conclusion = _normalization.workflow_conclusion(execution_result)
        if conclusion is None:
            return {
                "task_id": task_id,
                "synced": False,
                "idempotent": False,
                "created": False,
                "duplicate": False,
                "status": None,
                "reason": (
                    "no workflow conclusion recorded; EVENT_SYNC only "
                    "synchronises terminal workflow results"
                ),
            }

        canonical = _normalization.get_task_result(
            task_id,
            execution_result,
            conclusion,
            artifact_present=artifact_present,
            commit_present=commit_present,
        )
        fingerprint = "|".join(
            (str(canonical["status"]), str(canonical["workflow_conclusion"]))
        )

        record = self._tasks.get(task_id)
        created = record is None
        if record is None:
            base_goal = ""
            lineage: dict[str, Any] = {}
            if isinstance(execution_result, Mapping):
                base_goal = str(execution_result.get("summary", "")).strip()
                for field in (
                    LINEAGE_PROJECT_FIELD,
                    LINEAGE_ROOT_FIELD,
                    LINEAGE_PARENT_FIELD,
                ):
                    value = execution_result.get(field)
                    if value:
                        lineage[field] = value
            self.submit_task(
                task_id,
                goal=base_goal,
                status=canonical["status"],
                requires_review=True,
                **lineage,
            )
            record = self._tasks[task_id]

        already = bool(
            record.get("synced") and record.get("sync_fingerprint") == fingerprint
        )

        self._store_canonical_result(record, canonical)
        if isinstance(execution_result, Mapping) and record.get(
            "execution_result_json"
        ) is None:
            record["execution_result_json"] = dict(execution_result)

        stored_evidence = dict(record.get("evidence") or {})
        stored_evidence.update(
            {
                "artifact_present": bool(artifact_present),
                "commit_present": bool(commit_present),
            }
        )
        if isinstance(evidence, Mapping):
            stored_evidence["artifact"] = dict(evidence)
        record["evidence"] = stored_evidence

        event = None
        if not already:
            event = {
                "task_id": task_id,
                "action": SYNC_EVENT,
                "status": canonical["status"],
                "workflow_conclusion": canonical["workflow_conclusion"],
                "created": created,
            }
            self._sync_events.append(event)

        return {
            "task_id": task_id,
            "synced": True,
            "idempotent": already,
            "created": created,
            "duplicate": already,
            "status": canonical["status"],
            "normalized_status": canonical["status"],
            "execution_status": canonical["status"],
            "workflow_conclusion": canonical["workflow_conclusion"],
            "terminal": True,
            "review_state": record["review_state"],
            "requires_review": record["requires_review"],
            "reviewed": record["reviewed"],
            "review_verdict": record.get("review_verdict"),
            "sync_event": event,
            "task_result": canonical,
            "reason": canonical["reason"],
        }


_DEFAULT_REGISTRY = EventSyncRegistry()


def default_registry() -> EventSyncRegistry:
    """Return the process-wide default EVENT_SYNC registry."""
    return _DEFAULT_REGISTRY


def reset_default_registry() -> EventSyncRegistry:
    """Replace the process-wide registry (used by tests for isolation)."""
    global _DEFAULT_REGISTRY
    _DEFAULT_REGISTRY = EventSyncRegistry()
    return _DEFAULT_REGISTRY


def submit_task(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _DEFAULT_REGISTRY.submit_task(*args, **kwargs)


def get_task_result(task_id: str) -> dict[str, Any]:
    return _DEFAULT_REGISTRY.get_task_result(task_id)


def list_pending_results(
    scope: Mapping[str, Any] | None = None,
) -> Any:
    return _DEFAULT_REGISTRY.list_pending_results(scope)


def mark_reviewed(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _DEFAULT_REGISTRY.mark_reviewed(*args, **kwargs)


def recommend_review(task_id: str) -> dict[str, Any]:
    return _DEFAULT_REGISTRY.recommend_review(task_id)


def list_review_recommendations(
    scope: Mapping[str, Any] | None = None,
) -> Any:
    return _DEFAULT_REGISTRY.list_review_recommendations(scope)


def supervisor_pending_review_report(
    project_id: Any = None,
    root_task_id: Any = None,
    *,
    active_project: bool | None = None,
    env: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return _DEFAULT_REGISTRY.supervisor_pending_review_report(
        project_id,
        root_task_id,
        active_project=active_project,
        env=env,
    )


def get_review_events(task_id: str | None = None) -> list[dict[str, Any]]:
    return _DEFAULT_REGISTRY.get_review_events(task_id)


def get_sync_events(task_id: str | None = None) -> list[dict[str, Any]]:
    return _DEFAULT_REGISTRY.get_sync_events(task_id)


def get_reconciliation_events(task_id: str | None = None) -> list[dict[str, Any]]:
    return _DEFAULT_REGISTRY.get_reconciliation_events(task_id)


def audit_historical_tasks(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _DEFAULT_REGISTRY.audit_historical_tasks(*args, **kwargs)


def reconcile_historical_tasks(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _DEFAULT_REGISTRY.reconcile_historical_tasks(*args, **kwargs)


def sync_terminal_result(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _DEFAULT_REGISTRY.sync_terminal_result(*args, **kwargs)
