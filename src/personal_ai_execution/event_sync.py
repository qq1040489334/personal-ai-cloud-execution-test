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
``mark_reviewed`` automatically and never submits a follow-up task.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from . import reconciliation as _reconciliation
from . import result_normalization as _normalization

REVIEW_ACTION = "review"
REVIEW_VERDICTS = ("PASS", "FAIL", "BLOCKED")
PENDING_REVIEW = "pending_review"
REVIEWED_STATE = "reviewed"
SYNC_EVENT = "event_sync"
RECONCILE_ACTION = "reconcile"

#: Fixed task id used by the golden EVENT_SYNC discovery path.
GOLDEN_TASK_ID = "cf-0564e6c347b8"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventSyncRegistry:
    """Task Registry that ingests terminal workflow results via EVENT_SYNC.

    The registry preserves the ``submit_task`` / ``get_task_result`` /
    ``list_pending_results`` / ``mark_reviewed`` contracts: it never infers a
    verdict, never auto-reviews and never auto-submits a next task.
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

    def get_task_result(self, task_id: str) -> dict[str, Any]:
        """Return the stored workflow-authoritative task result payload."""
        record = self._tasks.get(str(task_id))
        if record is None:
            raise KeyError(f"unknown task_id: {task_id}")
        payload = (record.get("evidence") or {}).get("task_result")
        if isinstance(payload, Mapping):
            return dict(payload)
        return _normalization.get_task_result(
            str(task_id),
            record.get("execution_result_json"),
            record.get("workflow_conclusion"),
        )

    def list_pending_results(self) -> list[dict[str, Any]]:
        """Return every terminal, unreviewed task awaiting human review.

        Discovery needs no manual ``get_task_result`` call: EVENT_SYNC stores the
        normalized status on the registry record itself.
        """
        pending: list[dict[str, Any]] = []
        for record in self._tasks.values():
            if not record.get("terminal") or not record.get("result_available"):
                continue
            if not record.get("requires_review"):
                continue
            if record.get("reviewed"):
                continue
            item = dict(record)
            item["review_state"] = PENDING_REVIEW
            pending.append(item)
        pending.sort(key=lambda item: item["task_id"])
        return pending

    def mark_reviewed(
        self, task_id: Any = None, verdict: str | None = None, note: str | None = None
    ) -> dict[str, Any]:
        """Record an explicit human review verdict; idempotent per verdict."""
        if isinstance(task_id, Mapping):
            payload = dict(task_id)
            task_id = payload.get("task_id", task_id)
            verdict = payload.get("verdict", verdict)
            note = payload.get("note", note)
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
                result = dict(record)
                result["idempotent"] = True
                return result
            raise ValueError(
                f"review already recorded: {record.get('review_verdict')}"
            )
        timestamp = _utc_now()
        event = {
            "task_id": str(task_id),
            "action": REVIEW_ACTION,
            "verdict": normalized,
            "timestamp": timestamp,
            "note": note,
        }
        record["reviewed"] = True
        record["review_verdict"] = normalized
        record["reviewed_at"] = timestamp
        record["review_note"] = note
        record["review_state"] = REVIEWED_STATE
        record.setdefault("review_events", []).append(event)
        self._review_events.append(event)
        result = dict(record)
        result["idempotent"] = False
        return result

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
            if isinstance(execution_result, Mapping):
                base_goal = str(execution_result.get("summary", "")).strip()
            self.submit_task(
                task_id,
                goal=base_goal,
                status=canonical["status"],
                requires_review=True,
            )
            record = self._tasks[task_id]

        already = bool(
            record.get("synced") and record.get("sync_fingerprint") == fingerprint
        )

        record["status"] = canonical["status"]
        record["normalized_status"] = canonical["status"]
        record["workflow_conclusion"] = canonical["workflow_conclusion"]
        record["terminal"] = True
        record["result_available"] = True
        record["requires_review"] = True
        record["synced"] = True
        record["sync_fingerprint"] = fingerprint
        if isinstance(execution_result, Mapping) and record.get(
            "execution_result_json"
        ) is None:
            record["execution_result_json"] = dict(execution_result)
        if record.get("reviewed"):
            record["review_state"] = REVIEWED_STATE
        else:
            record["review_state"] = PENDING_REVIEW

        stored_evidence = dict(record.get("evidence") or {})
        stored_evidence.update(
            {
                "artifact_present": bool(artifact_present),
                "commit_present": bool(commit_present),
                "workflow_conclusion": canonical["workflow_conclusion"],
                "normalized_status": canonical["status"],
                "conclusion_authoritative": canonical["conclusion_authoritative"],
                "conclusion_result_mismatch": canonical["conclusion_result_mismatch"],
                "task_result": canonical,
                "reason": canonical["reason"],
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
            "workflow_conclusion": canonical["workflow_conclusion"],
            "terminal": True,
            "review_state": record["review_state"],
            "requires_review": record["requires_review"],
            "reviewed": record["reviewed"],
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


def list_pending_results() -> list[dict[str, Any]]:
    return _DEFAULT_REGISTRY.list_pending_results()


def mark_reviewed(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _DEFAULT_REGISTRY.mark_reviewed(*args, **kwargs)


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
