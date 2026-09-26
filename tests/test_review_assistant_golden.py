"""Golden end-to-end validation for the advisory review assistant.

PERSONAL_AI_REVIEW_ASSISTANT_GOLDEN_V0.1 runs the review assistant against a
real completed task taken from the Personal AI Execution production task stream
and asserts the six acceptance criteria: a real task is analysed, the output
carries a recommendation plus evidence-based rationale, no automatic approval
happens, no duplicate pending-review record is created, the produced workflow
concludes success, and the commit / tests / changed files / reviewed task are
reported.
"""

from __future__ import annotations

from personal_ai_execution import (
    BLOCKED,
    GOLDEN_REVIEW_TASK_ID,
    PASS,
    EventSyncRegistry,
    collect_mainline_evidence,
    golden_report_markdown,
    latest_successful_task,
    production_task_stream,
    run_review_assistant_golden,
)

EVIDENCE = {
    "commit": "cafebabe0123456789abcdef0123456789abcdef",
    "changed_files": [
        "src/personal_ai_execution/review_assistant.py",
        "tests/test_review_assistant.py",
    ],
}


def golden_report() -> dict:
    return run_review_assistant_golden(evidence=EVIDENCE)


def refs(report: dict) -> set[tuple]:
    return {
        (ref["source"], ref["field"], ref["value"])
        for ref in report["evidence_refs"]
    }


def test_real_completed_task_is_analyzed_and_recommends_pass() -> None:
    report = golden_report()

    assert report["status"] == PASS
    assert report["verdict"] == PASS
    assert report["reviewed_task_id"] == GOLDEN_REVIEW_TASK_ID
    assert all(check["passed"] for check in report["checks"])


def test_review_output_has_recommendation_and_evidence_based_rationale() -> None:
    report = golden_report()

    assert report["recommendation"]["recommendation"] == PASS
    assert report["rationale"]
    assert report["reasons"]
    assert all(reason.get("code") and reason.get("message") for reason in report["reasons"])

    observed = refs(report)
    assert ("task", "task_id", GOLDEN_REVIEW_TASK_ID) in observed
    assert ("canonical", "workflow_conclusion", "success") in observed
    assert ("canonical", "status", PASS) in observed
    assert ("execution_result", "tests", "1 passed") in observed
    assert ("evidence", "artifact_present", True) in observed
    assert ("evidence", "commit_present", True) in observed
    assert ("evidence", "artifact.id", 7) in observed


def test_no_automatic_approval_is_performed() -> None:
    report = golden_report()

    assert report["advisory"] is True
    assert report["auto_reviewed"] is False
    assert report["auto_mark_reviewed_called"] is False
    assert report["human_gate_intact"] is True
    assert report["review_events"] == 0

    recommendation = report["recommendation"]
    assert recommendation["requires_human_review"] is True
    assert report["pending_after"] == [GOLDEN_REVIEW_TASK_ID]

    registry = EventSyncRegistry()
    report = run_review_assistant_golden(evidence=EVIDENCE, registry=registry)
    entry = registry.list_pending_results()[0]
    assert entry["reviewed"] is False
    assert entry["review_state"] == "pending_review"
    assert registry.get_review_events() == []


def test_no_duplicate_pending_review_records_are_created() -> None:
    report = golden_report()

    assert report["duplicate_pending"] is False
    assert report["idempotent_resync"] is True
    assert report["pending_resync"].count(GOLDEN_REVIEW_TASK_ID) == 1
    assert report["pending_before"] == report["pending_after"] == [GOLDEN_REVIEW_TASK_ID]
    assert report["sync_events"] == 1


def test_production_workflow_conclusion_is_success() -> None:
    report = golden_report()

    assert report["production_workflow_conclusion"] == "success"
    assert report["evidence"]["workflow_conclusion"] == "success"
    assert report["evidence"]["normalized_status"] == PASS


def test_report_returns_commit_tests_changed_files_and_reviewed_task() -> None:
    report = golden_report()

    assert report["reviewed_task_id"] == GOLDEN_REVIEW_TASK_ID
    assert report["evidence"]["commit"] == EVIDENCE["commit"]
    assert report["evidence"]["tests"]
    assert report["evidence"]["changed_files"] == EVIDENCE["changed_files"]
    assert report["evidence"]["artifact"]["name"] == (
        f"execution_result-{GOLDEN_REVIEW_TASK_ID}"
    )

    markdown = golden_report_markdown(report)
    assert GOLDEN_REVIEW_TASK_ID in markdown
    assert EVIDENCE["commit"] in markdown
    assert "PASS" in markdown


def test_latest_successful_task_prefers_latest_pass_and_skips_failure() -> None:
    stream = [
        {
            "task_id": "cf-earlier",
            "workflow_conclusion": "success",
            "execution_result_json": {"task_id": "cf-earlier", "status": "success"},
        },
        {
            "task_id": "cf-later",
            "workflow_conclusion": "failure",
            "execution_result_json": {"task_id": "cf-later", "status": "success"},
        },
    ]

    assert latest_successful_task(stream)["task_id"] == "cf-earlier"


def test_latest_successful_task_returns_none_without_pass() -> None:
    stream = [
        {
            "task_id": "cf-only-fail",
            "workflow_conclusion": "failure",
            "execution_result_json": {"task_id": "cf-only-fail", "status": "success"},
        }
    ]

    assert latest_successful_task(stream) is None


def test_golden_report_is_deterministic() -> None:
    first = run_review_assistant_golden(evidence=EVIDENCE)
    second = run_review_assistant_golden(evidence=EVIDENCE)

    assert first["verdict"] == second["verdict"]
    assert first["rationale"] == second["rationale"]
    assert (
        first["recommendation"]["fingerprint"]
        == second["recommendation"]["fingerprint"]
    )


def test_empty_stream_is_blocked_not_approved() -> None:
    report = run_review_assistant_golden(stream=[])

    assert report["status"] == BLOCKED
    assert report["reviewed_task_id"] is None
    assert report["duplicate_pending"] is False
    assert report["human_gate_intact"] is True


def test_collect_mainline_evidence_and_stream_link_task_and_evidence() -> None:
    stream = production_task_stream(collect_mainline_evidence())

    assert len(stream) == 1
    record = stream[0]
    assert record["task_id"] == GOLDEN_REVIEW_TASK_ID
    assert record["workflow_conclusion"] == "success"
    assert record["execution_result_json"]["commit"]
    assert record["execution_result_json"]["changed_files"]


def test_failed_production_task_is_not_recommended_pass() -> None:
    stream = production_task_stream(EVIDENCE)
    stream[0]["workflow_conclusion"] = "failure"

    report = run_review_assistant_golden(stream=stream)

    assert report["status"] == BLOCKED
    assert report.get("verdict") != PASS
    assert report["reviewed_task_id"] is None
