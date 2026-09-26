"""PERSONAL_AI_REVIEW_ASSISTANT_V0.1 -- safe, advisory review recommendations.

This module produces a *recommendation* for a completed Personal AI Execution
task that is awaiting human review. It reads the pending-review task record and
the available execution evidence (workflow conclusion, normalized result status,
``execution_result.json`` fields, test output, artifacts and commit evidence)
and returns a structured ``PASS`` / ``FAIL`` / ``BLOCKED`` recommendation with
explicit reasons and evidence references.

Design constraints (deliberately fail-closed and side-effect free):

* The assistant is strictly **advisory**. It never calls ``mark_reviewed``,
  never mutates the Task Registry, never submits a follow-up task and never
  approves anything. The human reviewer remains the final gate.
* The workflow-authoritative normalization from
  :mod:`personal_ai_execution.result_normalization` is reused as the single
  source of truth. Evidence can only *downgrade* a recommendation, never
  upgrade it to ``PASS``.
* The output is **deterministic** for the same evidence input: no timestamps,
  no randomness, no unordered iteration, and reasons/refs are emitted in a
  fixed order. A stable ``fingerprint`` is included so callers can prove it.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from . import result_normalization as _normalization

PASS = _normalization.PASS
FAIL = _normalization.FAIL
BLOCKED = _normalization.BLOCKED

#: The only verdicts the review assistant may emit.
RECOMMENDATION_VERDICTS = (PASS, FAIL, BLOCKED)

_PASSED_RE = re.compile(r"(\d+)\s+passed", re.IGNORECASE)
_FAILED_RE = re.compile(r"(\d+)\s+(?:failed|errors?|xfailed)", re.IGNORECASE)
_FAILURE_HINT_RE = re.compile(r"\b(failed|failure|error|errors)\b", re.IGNORECASE)


def parse_test_evidence(
    execution_result: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Parse the advisory ``tests`` field into deterministic counts.

    Failure detection is fail-closed: an explicit non-zero failed/error count is
    a failure, and an unparseable string that still contains a failure word is
    treated as a failure rather than silently ignored.
    """
    empty = {
        "present": False,
        "raw": None,
        "passed": None,
        "failed": None,
        "has_failures": False,
    }
    if not isinstance(execution_result, Mapping):
        return empty
    raw = execution_result.get("tests")
    if raw is None or not str(raw).strip():
        return empty
    text = str(raw)
    passed_match = _PASSED_RE.search(text)
    failed_match = _FAILED_RE.search(text)
    passed = int(passed_match.group(1)) if passed_match else None
    failed = int(failed_match.group(1)) if failed_match else None
    if failed is not None:
        has_failures = failed > 0
    else:
        has_failures = bool(_FAILURE_HINT_RE.search(text))
    return {
        "present": True,
        "raw": text,
        "passed": passed,
        "failed": failed,
        "has_failures": has_failures,
    }


def _fingerprint(recommendation: Mapping[str, Any]) -> str:
    """Return a stable sha256 over the recommendation's decision content."""
    core = {
        "task_id": recommendation.get("task_id"),
        "verdict": recommendation.get("verdict"),
        "reasons": recommendation.get("reasons"),
        "evidence_refs": recommendation.get("evidence_refs"),
    }
    blob = json.dumps(core, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_review_recommendation(
    task: Mapping[str, Any] | None = None,
    *,
    task_id: str | None = None,
    task_result: Mapping[str, Any] | None = None,
    execution_result: Mapping[str, Any] | None = None,
    evidence: Mapping[str, Any] | None = None,
    artifact_present: bool | None = None,
    commit_present: bool | None = None,
    workflow_conclusion: str | None = None,
) -> dict[str, Any]:
    """Build an advisory review recommendation without touching any state.

    ``task`` is a pending-review task record (for example an entry returned by
    ``list_pending_results``). Explicit keyword arguments override values read
    from the record, which is useful for evidence discovered out-of-band.
    """
    record = dict(task) if isinstance(task, Mapping) else {}
    record_evidence = record.get("evidence")
    if not isinstance(record_evidence, Mapping):
        record_evidence = {}

    if task_result is None:
        stored_result = record_evidence.get("task_result")
        if isinstance(stored_result, Mapping):
            task_result = stored_result
    if execution_result is None:
        execution_result = record.get("execution_result_json")
    if evidence is None:
        evidence = record_evidence or None
    if workflow_conclusion is None:
        workflow_conclusion = record.get("workflow_conclusion")
    if artifact_present is None:
        artifact_present = record.get("artifact_present")
        if artifact_present is None and "artifact_present" in record_evidence:
            artifact_present = record_evidence.get("artifact_present")
    if commit_present is None:
        commit_present = record.get("commit_present")
        if commit_present is None and "commit_present" in record_evidence:
            commit_present = record_evidence.get("commit_present")

    resolved_task_id: str | None = None
    if task_id:
        resolved_task_id = str(task_id)
    elif record.get("task_id"):
        resolved_task_id = str(record.get("task_id"))
    elif isinstance(task_result, Mapping) and task_result.get("task_id"):
        resolved_task_id = str(task_result.get("task_id"))

    canonical: dict[str, Any] | None = None
    if isinstance(task_result, Mapping):
        canonical = dict(task_result)
    elif execution_result is not None or workflow_conclusion is not None:
        canonical = _normalization.get_task_result(
            resolved_task_id or "",
            execution_result,
            workflow_conclusion,
            artifact_present=artifact_present,
            commit_present=commit_present,
        )

    if canonical is not None:
        raw_status = canonical.get("status")
    else:
        raw_status = record.get("normalized_status") or record.get("status")
    normalized_status = (
        str(raw_status).strip().upper() if raw_status is not None else None
    )

    resolved_conclusion = (
        canonical.get("workflow_conclusion")
        if canonical is not None
        else workflow_conclusion
    )
    conflict = bool(canonical and canonical.get("conclusion_result_mismatch"))
    missing_files = (
        sorted(str(path) for path in (canonical.get("missing_expected_files") or []))
        if canonical is not None
        else []
    )
    test_evidence = parse_test_evidence(execution_result)

    #: True when at least one piece of corroborating evidence was supplied.
    has_evidence = any(
        value is not None
        for value in (
            execution_result,
            task_result,
            evidence,
            artifact_present,
            commit_present,
            workflow_conclusion,
        )
    ) or bool(record_evidence)

    reasons: list[dict[str, str]] = []
    refs: list[dict[str, Any]] = []

    def add_reason(code: str, message: str) -> None:
        reasons.append({"code": code, "message": message})

    def add_ref(source: str, field: str, value: Any) -> None:
        refs.append({"source": source, "field": field, "value": value})

    if resolved_task_id:
        add_ref("task", "task_id", resolved_task_id)
    if resolved_conclusion is not None:
        add_ref("canonical", "workflow_conclusion", resolved_conclusion)
    if canonical is not None:
        add_ref("canonical", "status", canonical.get("status"))
        add_ref(
            "canonical",
            "self_reported_status",
            canonical.get("self_reported_status"),
        )
        add_ref(
            "canonical",
            "conclusion_authoritative",
            bool(canonical.get("conclusion_authoritative")),
        )
        add_ref(
            "canonical",
            "conclusion_result_mismatch",
            conflict,
        )
        if missing_files:
            add_ref("canonical", "missing_expected_files", missing_files)
    elif normalized_status is not None:
        add_ref("registry", "normalized_status", normalized_status)
    if isinstance(execution_result, Mapping):
        add_ref("execution_result", "status", execution_result.get("status"))
    if test_evidence["present"]:
        add_ref("execution_result", "tests", test_evidence["raw"])
        if test_evidence["passed"] is not None:
            add_ref("execution_result", "tests_passed", test_evidence["passed"])
        if test_evidence["failed"] is not None:
            add_ref("execution_result", "tests_failed", test_evidence["failed"])
    if artifact_present is not None:
        add_ref("evidence", "artifact_present", bool(artifact_present))
    if commit_present is not None:
        add_ref("evidence", "commit_present", bool(commit_present))
    if isinstance(evidence, Mapping) and isinstance(evidence.get("artifact"), Mapping):
        artifact = evidence["artifact"]
        for name in ("name", "id"):
            if artifact.get(name) is not None:
                add_ref("evidence", f"artifact.{name}", artifact.get(name))

    verdict: str
    if normalized_status is None:
        verdict = BLOCKED
        add_reason(
            "NO_NORMALIZED_STATUS",
            "no normalized result status or workflow conclusion is available",
        )
    elif normalized_status not in _normalization.TERMINAL_STATUSES:
        verdict = BLOCKED
        add_reason(
            "NON_TERMINAL_STATUS",
            f"normalized status {normalized_status!r} is not terminal",
        )
    elif normalized_status == FAIL:
        verdict = FAIL
        if conflict:
            add_reason(
                "CONFLICTING_EVIDENCE",
                "workflow conclusion and execution_result self-report disagree; "
                "the workflow conclusion is authoritative",
            )
        add_reason(
            "WORKFLOW_FAILURE",
            "normalized terminal status is FAIL",
        )
    elif normalized_status == BLOCKED:
        verdict = BLOCKED
        if conflict:
            add_reason(
                "CONFLICTING_EVIDENCE",
                "workflow conclusion and execution_result self-report disagree; "
                "the workflow conclusion is authoritative",
            )
        add_reason(
            "WORKFLOW_BLOCKED",
            "normalized terminal status is BLOCKED "
            "(cancelled/timed_out/unknown conclusion)",
        )
    elif conflict:
        verdict = BLOCKED
        add_reason(
            "CONFLICTING_EVIDENCE",
            "workflow conclusion and execution_result self-report disagree; "
            "the workflow conclusion is authoritative",
        )
    elif test_evidence["has_failures"]:
        verdict = FAIL
        add_reason(
            "TEST_FAILURES",
            "execution_result tests report failures",
        )
    elif missing_files:
        verdict = FAIL
        add_reason(
            "MISSING_EXPECTED_FILES",
            "declared expected files were not produced: " + ", ".join(missing_files),
        )
    elif not has_evidence:
        verdict = BLOCKED
        add_reason(
            "INSUFFICIENT_EVIDENCE",
            "normalized PASS has no execution result, artifact, commit, or "
            "review evidence to corroborate it",
        )
    else:
        verdict = PASS
        add_reason(
            "EVIDENCE_CONSISTENT",
            "workflow conclusion and available evidence agree on terminal success",
        )

    recommendation: dict[str, Any] = {
        "task_id": resolved_task_id,
        "verdict": verdict,
        "recommendation": verdict,
        "advisory": True,
        "requires_human_review": True,
        "auto_reviewed": False,
        "auto_mark_reviewed_called": False,
        "reasons": reasons,
        "evidence_refs": refs,
        "inputs": {
            "normalized_status": normalized_status,
            "workflow_conclusion": resolved_conclusion,
            "conclusion_authoritative": (
                bool(canonical.get("conclusion_authoritative"))
                if canonical is not None
                else False
            ),
            "conclusion_result_mismatch": conflict,
            "missing_expected_files": missing_files,
            "tests": test_evidence,
            "artifact_present": artifact_present,
            "commit_present": commit_present,
        },
    }
    recommendation["fingerprint"] = _fingerprint(recommendation)
    return recommendation


def recommend_pending_reviews(
    records: Any,
) -> list[dict[str, Any]]:
    """Return one deterministic recommendation per pending-review record."""
    if not isinstance(records, (list, tuple)):
        records = list(records)
    return [build_review_recommendation(record) for record in records]
