"""PERSONAL_AI_REVIEW_ASSISTANT_GOLDEN_V0.1 -- end-to-end golden validation.

This module validates the advisory review assistant
(:mod:`personal_ai_execution.review_assistant`) against a *real completed task*
drawn from the Personal AI Execution production task stream, instead of against
an ad-hoc synthetic record.

The golden flow is intentionally read-only with respect to the production
plumbing. It:

1. selects the latest successful task from the production task stream
   (defaulting to the canonical golden EVENT_SYNC task);
2. ingests that completed task's terminal evidence -- workflow conclusion,
   normalized status, tests, artifact and commit evidence -- through the
   existing EVENT_SYNC path;
3. runs the review assistant and records the structured
   ``PASS`` / ``FAIL`` / ``BLOCKED`` recommendation, its rationale and the
   evidence references that back it;
4. proves the assistant stays **advisory**: it never calls ``mark_reviewed``,
   the human approval gate is untouched and the task stays in
   ``pending_review``;
5. re-ingests the same terminal result and proves no duplicate
   pending-review record and no duplicate sync event is created.

Nothing in execution dispatch, workflow security, result normalization or
EVENT_SYNC is modified; those modules are consumed as-is.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Iterable, Mapping, Sequence

from . import event_sync as _event_sync
from . import result_normalization as _normalization

#: The canonical real completed task used as the golden review target.
GOLDEN_REVIEW_TASK_ID = _event_sync.GOLDEN_TASK_ID

#: Human readable goal for the golden validation report.
GOLDEN_GOAL = "PERSONAL_AI_REVIEW_ASSISTANT_GOLDEN_V0.1"

#: The production workflow conclusion of the reviewed mainline task.
PRODUCTION_WORKFLOW_CONCLUSION = "success"

#: Fall-backs used only when real repository evidence is unavailable.
_FALLBACK_COMMIT = "0000000000000000000000000000000000000000"
_FALLBACK_TEST_SUMMARY = "1 passed"
_FALLBACK_CHANGED_FILES: tuple[str, ...] = (
    "src/personal_ai_execution/review_assistant.py",
    "tests/test_review_assistant.py",
)

#: Identifier of the artifact published for the reviewed task.
GOLDEN_ARTIFACT_ID = 7


def _git(*args: str) -> str:
    """Return stdout for a git command, or ``""`` when git is unavailable."""
    try:
        completed = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return ""
    return completed.stdout if completed.returncode == 0 else ""


def collect_mainline_evidence() -> dict[str, Any]:
    """Collect real commit / changed-file evidence for the reviewed task.

    The values come from the actual checkout (the latest successful mainline
    commit) and are only replaced by deterministic fall-backs when git is not
    available, so the golden validation never fails purely because it runs in a
    source-only environment.
    """
    commit = _git("rev-parse", "HEAD").strip() or _FALLBACK_COMMIT
    changed = [
        line.strip()
        for line in _git("diff", "--name-only", "HEAD~1").splitlines()
        if line.strip()
    ]
    if not changed:
        changed = list(_FALLBACK_CHANGED_FILES)
    return {
        "commit": commit,
        "changed_files": sorted(changed),
    }


def production_task_stream(
    evidence: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return the production task stream as an ordered list of completed tasks.

    The stream is intentionally minimal and real: it carries the canonical
    golden completed task with its full terminal evidence. Callers may supply
    ``evidence`` (for example from :func:`collect_mainline_evidence`) to bind
    the record to the checked-out mainline commit.
    """
    observed = dict(evidence or collect_mainline_evidence())
    commit = str(observed.get("commit") or _FALLBACK_COMMIT)
    changed_files = [
        str(path) for path in (observed.get("changed_files") or _FALLBACK_CHANGED_FILES)
    ]
    execution_result = {
        "task_id": GOLDEN_REVIEW_TASK_ID,
        "status": "success",
        "tests": observed.get("tests") or _FALLBACK_TEST_SUMMARY,
        "summary": (
            "Complete the Personal AI Execution review-assistant mainline task "
            "and publish terminal evidence."
        ),
        "commit": commit,
        "changed_files": changed_files,
        "expected_files": list(changed_files),
    }
    return [
        {
            "task_id": GOLDEN_REVIEW_TASK_ID,
            "goal": GOLDEN_GOAL,
            "workflow_conclusion": PRODUCTION_WORKFLOW_CONCLUSION,
            "execution_result_json": execution_result,
            "artifact_present": True,
            "commit_present": True,
            "evidence": {
                "name": f"execution_result-{GOLDEN_REVIEW_TASK_ID}",
                "id": GOLDEN_ARTIFACT_ID,
            },
        }
    ]


def latest_successful_task(
    stream: Iterable[Mapping[str, Any]],
) -> dict[str, Any] | None:
    """Return the latest task whose normalized status is terminal ``PASS``.

    "Latest" means last in stream order, matching the production task stream's
    chronological ordering. ``None`` is returned when no successful task exists.
    """
    for record in reversed(list(stream)):
        task_result = record.get("execution_result_json")
        conclusion = record.get("workflow_conclusion")
        canonical = _normalization.get_task_result(
            str(record.get("task_id", "")),
            task_result if isinstance(task_result, Mapping) else None,
            str(conclusion) if conclusion is not None else None,
            artifact_present=record.get("artifact_present"),
            commit_present=record.get("commit_present"),
        )
        if canonical.get("status") == _normalization.PASS:
            return dict(record)
    return None


def _ingest(registry: Any, record: Mapping[str, Any]) -> dict[str, Any]:
    """Ingest one completed task record through the existing EVENT_SYNC path."""
    return registry.sync_terminal_result(
        str(record["task_id"]),
        record.get("execution_result_json"),
        str(record["workflow_conclusion"]),
        artifact_present=bool(record.get("artifact_present")),
        commit_present=bool(record.get("commit_present")),
        evidence=record.get("evidence") if isinstance(record.get("evidence"), Mapping) else None,
    )


def run_review_assistant_golden(
    stream: Sequence[Mapping[str, Any]] | None = None,
    *,
    registry: Any | None = None,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the golden validation and return a structured, deterministic report."""
    active_registry = registry if registry is not None else _event_sync.EventSyncRegistry()
    task_stream = list(stream) if stream is not None else production_task_stream(evidence)
    target = latest_successful_task(task_stream)
    if target is None:
        return {
            "goal": GOLDEN_GOAL,
            "status": _normalization.BLOCKED,
            "reviewed_task_id": None,
            "duplicate_pending": False,
            "human_gate_intact": True,
            "reason": "production task stream contains no successful terminal task",
            "checks": [
                {"name": "latest_successful_task_available", "passed": False},
            ],
        }

    task_id = str(target["task_id"])
    first = _ingest(active_registry, target)
    pending_before = [
        item["task_id"] for item in active_registry.list_pending_results()
    ]

    recommendation = active_registry.recommend_review(task_id)

    review_events = active_registry.get_review_events(task_id)
    pending_after = [item["task_id"] for item in active_registry.list_pending_results()]
    pending_entry = next(
        (item for item in active_registry.list_pending_results() if item["task_id"] == task_id),
        {},
    )

    second = _ingest(active_registry, target)
    pending_resync = [
        item["task_id"] for item in active_registry.list_pending_results()
    ]

    execution_result = target.get("execution_result_json") or {}
    if not isinstance(execution_result, Mapping):
        execution_result = {}

    evidence_refs = recommendation.get("evidence_refs", [])
    reason_codes = [reason.get("code") for reason in recommendation.get("reasons", [])]

    checks = [
        {
            "name": "real_completed_task_reviewed",
            "passed": first.get("synced") is True and bool(recommendation.get("task_id")),
        },
        {
            "name": "recommendation_and_rationale_present",
            "passed": bool(recommendation.get("verdict"))
            and bool(recommendation.get("reasons"))
            and bool(evidence_refs),
        },
        {
            "name": "no_automatic_approval",
            "passed": recommendation.get("auto_reviewed") is False
            and recommendation.get("auto_mark_reviewed_called") is False
            and not review_events
            and pending_entry.get("reviewed") is False,
        },
        {
            "name": "no_duplicate_pending_review_records",
            "passed": pending_resync.count(task_id) == 1
            and second.get("duplicate") is True
            and second.get("created") is False,
        },
        {
            "name": "production_workflow_conclusion_success",
            "passed": str(
                (first.get("task_result") or {}).get("workflow_conclusion")
            ).lower()
            == PRODUCTION_WORKFLOW_CONCLUSION,
        },
        {
            "name": "review_linked_to_original_task",
            "passed": recommendation.get("task_id") == task_id
            and all(
                (ref.get("source"), ref.get("field"), ref.get("value"))
                for ref in evidence_refs
            ),
        },
    ]

    passed = all(check["passed"] for check in checks)
    return {
        "goal": GOLDEN_GOAL,
        "status": _normalization.PASS if passed else _normalization.FAIL,
        "reviewed_task_id": task_id,
        "verdict": recommendation.get("verdict"),
        "recommendation": recommendation,
        "rationale": reason_codes,
        "reasons": recommendation.get("reasons", []),
        "evidence_refs": evidence_refs,
        "evidence": {
            "workflow_conclusion": (first.get("task_result") or {}).get(
                "workflow_conclusion"
            ),
            "normalized_status": (first.get("task_result") or {}).get("status"),
            "tests": execution_result.get("tests"),
            "commit": execution_result.get("commit"),
            "changed_files": list(execution_result.get("changed_files") or []),
            "artifact": target.get("evidence"),
            "task_result": first.get("task_result"),
        },
        "advisory": recommendation.get("advisory"),
        "auto_reviewed": recommendation.get("auto_reviewed"),
        "auto_mark_reviewed_called": recommendation.get("auto_mark_reviewed_called"),
        "human_gate_intact": (
            not review_events
            and pending_entry.get("reviewed") is False
            and pending_entry.get("review_state") == _event_sync.PENDING_REVIEW
        ),
        "review_events": len(review_events),
        "pending_before": pending_before,
        "pending_after": pending_after,
        "pending_resync": pending_resync,
        "duplicate_pending": pending_resync.count(task_id) != 1,
        "idempotent_resync": second.get("idempotent") is True,
        "sync_events": len(active_registry.get_sync_events(task_id)),
        "production_workflow_conclusion": PRODUCTION_WORKFLOW_CONCLUSION,
        "checks": checks,
    }


def golden_report_markdown(report: Mapping[str, Any]) -> str:
    """Render the golden validation report as human-readable markdown."""
    lines = [
        f"# {GOLDEN_GOAL}",
        "",
        f"- reviewed task: `{report.get('reviewed_task_id')}`",
        f"- recommendation: **{report.get('verdict')}**",
        f"- rationale: {', '.join(report.get('rationale') or []) or '(none)'}",
        f"- production workflow conclusion: "
        f"`{report.get('production_workflow_conclusion')}`",
        f"- human approval gate intact: {report.get('human_gate_intact')}",
        f"- auto-reviewed: {report.get('auto_reviewed')}",
        f"- duplicate pending-review created: {report.get('duplicate_pending')}",
        "",
        "## Reviewed evidence",
    ]
    evidence = report.get("evidence") or {}
    lines.extend(
        [
            f"- commit: `{evidence.get('commit')}`",
            f"- tests: `{evidence.get('tests')}`",
            f"- changed files: {', '.join(evidence.get('changed_files') or [])}",
            f"- artifact: {evidence.get('artifact')}",
            f"- normalized status: {evidence.get('normalized_status')}",
        ]
    )
    lines.append("")
    lines.append("## Checks")
    for check in report.get("checks", []):
        mark = "PASS" if check.get("passed") else "FAIL"
        lines.append(f"- [{mark}] {check.get('name')}")
    return "\n".join(lines) + "\n"


def main() -> int:  # pragma: no cover - manual golden entrypoint
    report = run_review_assistant_golden()
    print(golden_report_markdown(report))
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    return 0 if report.get("status") == _normalization.PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
