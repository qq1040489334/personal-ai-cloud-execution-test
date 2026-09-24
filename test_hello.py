"""Automated test for hello.py."""

import inspect
import json
from datetime import datetime, timedelta, timezone

import pytest

import hello as hello_module
from hello import (
    AUTO_CONSUMER_GOAL,
    AUTO_CONSUMER_GOLDEN_E2E_GOAL,
    AUTO_CONSUMER_GOLDEN_E2E_REPORT,
    AUTO_CONSUMER_GOLDEN_E2E_STEPS,
    AUTO_CONSUMER_GOLDEN_E2E_TASK_ID,
    AUTO_CONSUMER_REPORT,
    AUTO_CONSUMER_TASK_ID,
    CLOUDFLARE_AUDIT_GOAL,
    CLOUDFLARE_AUDIT_TASK_ID,
    CLOUDFLARE_AUDIT_TOKENS,
    CLOUDFLARE_WORKER_NAME,
    CONSUMER_EVIDENCE_ENV,
    DEPLOY_VERIFY_COMMIT,
    DEPLOY_VERIFY_TASK_ID,
    EXPOSURE_AUDIT_DETAIL_EXPORT_GOAL,
    EXPOSURE_AUDIT_DETAIL_EXPORT_TASK_ID,
    EXPOSURE_AUDIT_FIELD_CLIPPING_LAYERS,
    EXPOSURE_REGRESSION_AUDIT_TASK_ID,
    FINAL_EVIDENCE_AUDIT_GOAL,
    FINAL_EVIDENCE_AUDIT_REPORT,
    FINAL_EVIDENCE_AUDIT_TASK_ID,
    FREEZE_DECISION_GOAL,
    FREEZE_DECISION_REPORT,
    FREEZE_DECISION_TASK_ID,
    FREEZE_DECISIONS,
    GAP_CLOSE_GOAL,
    GAP_CLOSE_LAYERS,
    GAP_CLOSE_REPORT,
    GAP_CLOSE_TASK_ID,
    LIVE_ACCEPTANCE_GOAL,
    LIVE_ACCEPTANCE_REPORT,
    LIVE_ACCEPTANCE_TASK_ID,
    PENDING_TIMEOUT_SECONDS,
    POST_E2E_AUDIT_GOAL,
    POST_E2E_AUDIT_LAYERS,
    POST_E2E_AUDIT_REPORT,
    POST_E2E_AUDIT_TASK_ID,
    PRODUCTION_READINESS_GOAL,
    PRODUCTION_READINESS_REPORT,
    PRODUCTION_READINESS_TASK_ID,
    REQUIRED_RESULT_FIELDS,
    REVIEW_VERDICTS,
    RUNTIME_AUDIT_GOAL,
    RUNTIME_AUDIT_TASK_ID,
    RUNTIME_CANDIDATE_COMMITS,
    RUNTIME_PROVENANCE_GOAL,
    RUNTIME_PROVENANCE_TASK_ID,
    RESULT_DETAIL_GOAL,
    RESULT_DETAIL_TASK_ID,
    RESULT_DETAIL_FIELDS,
    STATUS_MODEL_EXPECTED_FIELDS,
    TASK_REVIEW_GOAL,
    auto_consume_completed_results,
    classify_pending_task,
    cloud_agent_test,
    cloud_agent_test_2,
    cloud_asset_status,
    cloudflare_mcp_test,
    cloudflare_runtime_audit_report,
    consume_task_result,
    consumer_evidence_status,
    consumer_heartbeat,
    discover_completed_results,
    execution_result_detail_exposure_verify,
    expire_stale_pending,
    get_consumer_evidence_path,
    get_consumption_evidence,
    get_review_events,
    get_task_result,
    get_task_review,
    goodbye,
    gpt_bridge_test,
    hello,
    list_pending_results,
    list_review_events,
    mark_reviewed,
    mcp_bridge_test,
    mcp_runtime_deploy_verify,
    oauth_mcp_test,
    pending_acceptance_notice,
    personal_ai_execution_result_exposure_audit_detail_export,
    personal_ai_task_runtime_audit,
    record_consumer_evidence,
    result_consumer_test,
    result_consumer_test2,
    runtime_provenance_report,
    security_test,
    submit_task,
    task_result_auto_consumer_final_evidence_audit,
    task_result_auto_consumer_freeze_decision_report,
    task_result_auto_consumer_gap_close_report,
    task_result_auto_consumer_golden_e2e_verify,
    task_result_auto_consumer_live_acceptance_report,
    task_result_auto_consumer_post_e2e_audit,
    task_result_auto_consumer_production_readiness_report,
    task_result_auto_consumer_report,
    task_review_action_report,
    trigger_bridge_test,
)

VALID_STATUSES = {"PASS", "FAIL", "BLOCKED"}


def test_hello() -> None:
    assert hello() == "hello from cloud execution golden test"


def test_goodbye() -> None:
    assert goodbye() == "goodbye from cloud execution golden test"
    assert isinstance(goodbye(), str)


def test_cloud_agent_test() -> None:
    assert cloud_agent_test() == "executed inside github actions"


def test_cloud_agent_test_2() -> None:
    assert cloud_agent_test_2() == "second cloud run"


def test_trigger_bridge_test() -> None:
    assert trigger_bridge_test() == "triggered from github issue"


def test_security_test() -> None:
    assert security_test() == "security gate ok"


def test_gpt_bridge_test() -> None:
    assert gpt_bridge_test() == "gpt bridge ok"


def test_mcp_bridge_test() -> None:
    assert mcp_bridge_test() == "mcp bridge ok"


def test_cloudflare_mcp_test() -> None:
    assert cloudflare_mcp_test() == "cloudflare mcp ok"


def test_oauth_mcp_test() -> None:
    assert oauth_mcp_test() == "oauth mcp ok"


def test_result_consumer_test() -> None:
    assert result_consumer_test() == "result consumer ok"


def test_result_consumer_test2() -> None:
    assert result_consumer_test2() == "result consumer two ok"


def test_cloud_asset_status_report_shape() -> None:
    report = cloud_asset_status()
    assert set(report) >= {"task_id", "asset", "generated_at", "checks", "overall", "next_steps"}
    assert report["task_id"] == "cf-175495049c41"
    assert report["checks"]
    assert report["overall"] in VALID_STATUSES
    for check in report["checks"]:
        assert set(check) >= {"component", "status", "detail", "evidence"}
        assert check["status"] in VALID_STATUSES
        assert check["detail"]
        assert check["evidence"]


def test_cloud_asset_status_covers_all_components() -> None:
    components = {c["component"] for c in cloud_asset_status()["checks"]}
    assert {
        "Worker",
        "D1",
        "Canonical Asset",
        "Promotion",
        "Governance Audit",
    } <= components


def test_cloud_asset_status_no_fabricated_pass() -> None:
    statuses = {c["component"]: c["status"] for c in cloud_asset_status()["checks"]}
    assert statuses["Worker"] == "BLOCKED"
    assert statuses["D1"] == "BLOCKED"
    assert statuses["Canonical Asset"] == "PASS"


def test_cloud_asset_status_timestamp_and_overall() -> None:
    report = cloud_asset_status()
    assert datetime.fromisoformat(report["generated_at"]).tzinfo is not None
    statuses = [c["status"] for c in report["checks"]]
    if "FAIL" in statuses:
        assert report["overall"] == "FAIL"
    elif "BLOCKED" in statuses:
        assert report["overall"] == "BLOCKED"
    else:
        assert report["overall"] == "PASS"
    expected_next_steps = [
        c["component"] for c in report["checks"] if c["status"] != "PASS"
    ]
    assert len(report["next_steps"]) == len(expected_next_steps)


def test_get_task_result_shape() -> None:
    result = get_task_result("cf-5ce9f24c8aa1")
    assert set(result) == {
        "execution_summary",
        "commit",
        "tests",
        "artifacts",
        "execution_result_json",
        "evidence",
    }
    summary = result["execution_summary"]
    assert set(summary) == {"task_id", "status", "round", "summary"}
    assert summary["task_id"] == "cf-5ce9f24c8aa1"
    assert summary["status"] in VALID_STATUSES
    assert isinstance(summary["round"], int)
    assert summary["summary"]
    assert isinstance(result["tests"], str) and result["tests"]
    assert isinstance(result["artifacts"], list)
    for artifact in result["artifacts"]:
        assert set(artifact) >= {"name", "path", "sha256", "bytes"}
        assert artifact["sha256"]
        assert artifact["bytes"] > 0
    assert isinstance(result["execution_result_json"], dict)
    assert set(result["evidence"]) >= {"acceptance", "logs", "validation", "decision"}
    assert result["evidence"]["decision"]["status"] == summary["status"]


def test_get_task_result_self_contained() -> None:
    result = get_task_result("cf-5ce9f24c8aa1")
    status = result["execution_summary"]["status"]
    assert status in VALID_STATUSES
    assert result["evidence"]["decision"]["status"] == status
    assert result["evidence"]["validation"]["pytest"]
    assert "execution_result_present" in result["evidence"]["validation"]
    assert result["evidence"]["validation"]["artifacts_present"]


def test_get_task_result_artifacts_hashed() -> None:
    paths = {a["path"] for a in get_task_result("cf-5ce9f24c8aa1")["artifacts"]}
    assert "hello.py" in paths
    assert "test_hello.py" in paths
    for artifact in get_task_result("cf-5ce9f24c8aa1")["artifacts"]:
        assert len(artifact["sha256"]) == 64


def test_mcp_runtime_deploy_verify_shape() -> None:
    report = mcp_runtime_deploy_verify()
    assert set(report) >= {
        "task_id",
        "goal",
        "target_commit",
        "head_commit",
        "result_fields",
        "result_fields_complete",
        "target_commit_on_history",
        "worker_asset",
        "deploy_workflows",
        "online_mcp_version",
        "checks",
        "final_status",
        "final_return_markdown",
    }
    assert report["task_id"] == DEPLOY_VERIFY_TASK_ID
    assert report["goal"] == "PERSONAL_AI_EXECUTION_MCP_RUNTIME_DEPLOY_VERIFY_01"
    assert report["final_status"] in {"PASS", "PARTIAL", "FAIL"}
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in {"PASS", "FAIL", "BLOCKED"}
        assert check["detail"]


def test_mcp_runtime_deploy_verify_return_fields() -> None:
    report = mcp_runtime_deploy_verify()
    assert report["result_fields"] == {
        name: True for name in REQUIRED_RESULT_FIELDS
    }
    assert report["result_fields_complete"] is True


def test_mcp_runtime_deploy_verify_target_commit() -> None:
    report = mcp_runtime_deploy_verify()
    assert report["target_commit"] == DEPLOY_VERIFY_COMMIT
    assert report["head_commit"]
    assert report["target_commit_on_history"] is True


def test_mcp_runtime_deploy_verify_no_fabricated_pass() -> None:
    report = mcp_runtime_deploy_verify()
    if not report["worker_asset"]:
        assert report["final_status"] != "PASS"
    if not report["deploy_workflows"]:
        assert report["final_status"] != "PASS"
    assert report["online_mcp_version"] != "PASS"


def test_mcp_runtime_deploy_verify_final_return_markdown() -> None:
    report = mcp_runtime_deploy_verify()
    markdown = report["final_return_markdown"]
    assert markdown.startswith(
        "# FINAL_RETURN_PERSONAL_AI_EXECUTION_MCP_RUNTIME_DEPLOY_VERIFY_01"
    )
    for name in REQUIRED_RESULT_FIELDS:
        assert f"- {name}: returned" in markdown
    assert f"## Final status: {report['final_status']}" in markdown


def test_runtime_provenance_report_shape() -> None:
    report = runtime_provenance_report()
    assert report["report"] == "RUNTIME_PROVENANCE_REPORT"
    assert report["task_id"] == RUNTIME_PROVENANCE_TASK_ID
    assert report["goal"] == RUNTIME_PROVENANCE_GOAL
    assert set(report) >= {
        "report",
        "CURRENT_RUNTIME_COMMIT",
        "DEPLOY_STATUS",
        "NEEDS_DEPLOY",
        "head_commit",
        "origin_main_commit",
        "provenance_source",
        "runtime_verified",
        "candidate_commits",
        "worker_asset",
        "deploy_metadata",
        "deploy_workflows",
        "deploy_history",
        "live_endpoint_checked",
        "assessment",
        "checks",
        "overall",
        "markdown",
    }


def test_runtime_provenance_candidate_commits() -> None:
    report = runtime_provenance_report()
    assert set(report["candidate_commits"]) == set(RUNTIME_CANDIDATE_COMMITS)
    assert report["candidates_present"] is True
    for commit, info in report["candidate_commits"].items():
        assert info["present_locally"] is True
        assert info["on_current_history"] is True
        assert commit in RUNTIME_CANDIDATE_COMMITS


def test_runtime_provenance_markdown_tokens() -> None:
    report = runtime_provenance_report()
    markdown = report["markdown"]
    assert markdown.startswith("# RUNTIME_PROVENANCE_REPORT")
    assert f"CURRENT_RUNTIME_COMMIT={report['CURRENT_RUNTIME_COMMIT']}" in markdown
    assert f"DEPLOY_STATUS={report['DEPLOY_STATUS']}" in markdown
    assert f"NEEDS_DEPLOY={report['NEEDS_DEPLOY']}" in markdown


def test_runtime_provenance_no_fabricated_live_pass() -> None:
    report = runtime_provenance_report()
    assert report["live_endpoint_checked"] is False
    assert report["runtime_verified"] is False
    assert report["overall"] != "PASS"
    if not report["deploy_metadata"]:
        assert report["DEPLOY_STATUS"] != "PASS"
    assert report["NEEDS_DEPLOY"] in {"YES", "NO"}


def test_runtime_provenance_checks_and_status() -> None:
    report = runtime_provenance_report()
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in {"PASS", "FAIL", "BLOCKED"}
        assert check["detail"]
    assert report["DEPLOY_STATUS"] in {"PASS", "FAIL", "BLOCKED", "PARTIAL"}
    assert report["overall"] in {"PASS", "FAIL", "BLOCKED", "PARTIAL"}


def test_cloudflare_runtime_audit_report_shape() -> None:
    report = cloudflare_runtime_audit_report()
    assert report["report"] == "CLOUDFLARE_RUNTIME_AUDIT_REPORT"
    assert report["task_id"] == CLOUDFLARE_AUDIT_TASK_ID
    assert report["goal"] == CLOUDFLARE_AUDIT_GOAL
    assert report["WORKER_NAME"] == CLOUDFLARE_WORKER_NAME
    assert set(report) >= {
        "report",
        "task_id",
        "goal",
        "WORKER_NAME",
        "CURRENT_RUNTIME_COMMIT",
        "WORKER_VERSION_ID",
        "LATEST_DEPLOYMENT_ID",
        "DEPLOY_STATUS",
        "NEEDS_DEPLOY",
        "deployment_timestamp",
        "script_version_hash",
        "head_commit",
        "origin_main_commit",
        "provenance_source",
        "runtime_verified",
        "worker_asset",
        "deploy_metadata",
        "deploy_workflows",
        "deploy_history",
        "live_endpoint_checked",
        "checks",
        "overall",
        "markdown",
    }
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in {"PASS", "FAIL", "BLOCKED"}
        assert check["detail"]


def test_cloudflare_runtime_audit_answers_present() -> None:
    report = cloudflare_runtime_audit_report()
    assert report["CURRENT_RUNTIME_COMMIT"]
    assert report["WORKER_VERSION_ID"]
    assert report["LATEST_DEPLOYMENT_ID"]
    assert report["DEPLOY_STATUS"] in {"PASS", "FAIL", "BLOCKED", "PARTIAL"}
    assert report["NEEDS_DEPLOY"] in {"YES", "NO"}


def test_cloudflare_runtime_audit_markdown_tokens() -> None:
    report = cloudflare_runtime_audit_report()
    markdown = report["markdown"]
    assert markdown.startswith("# CLOUDFLARE_RUNTIME_AUDIT_REPORT")
    for token in CLOUDFLARE_AUDIT_TOKENS:
        assert f"{token}={report[token]}" in markdown


def test_cloudflare_runtime_audit_no_fabricated_live_pass() -> None:
    report = cloudflare_runtime_audit_report()
    assert report["live_endpoint_checked"] is False
    assert report["runtime_verified"] is False
    assert report["overall"] != "PASS"
    if not report["worker_asset"] and not report["deploy_metadata"]:
        assert report["DEPLOY_STATUS"] == "BLOCKED"
    assert report["NEEDS_DEPLOY"] == "YES"
    assert isinstance(report["WORKER_VERSION_ID"], str) and report["WORKER_VERSION_ID"]
    assert isinstance(report["LATEST_DEPLOYMENT_ID"], str) and report["LATEST_DEPLOYMENT_ID"]


def _pending_ids() -> set[str]:
    return {task["task_id"] for task in list_pending_results()}


def test_submit_task_appears_in_pending_review() -> None:
    task_id = "review-flow-001"
    submit_task(task_id, goal="review flow", status="success", requires_review=True)
    pending = {task["task_id"]: task for task in list_pending_results()}
    assert task_id in pending
    assert pending[task_id]["requires_review"] is True
    assert pending[task_id]["review_state"] == "pending_review"


def test_mark_reviewed_removes_task_from_pending_review() -> None:
    task_id = "review-flow-002"
    submit_task(task_id, status="success", requires_review=True)
    assert task_id in _pending_ids()
    result = mark_reviewed(task_id, "PASS", "looks good")
    assert result["reviewed"] is True
    assert result["review_verdict"] == "PASS"
    assert result["reviewed_at"]
    assert result["review_note"] == "looks good"
    assert task_id not in _pending_ids()


def test_mark_reviewed_accepts_json_input() -> None:
    task_id = "review-flow-003"
    submit_task(task_id, status="success", requires_review=True)
    payload = json.dumps({"task_id": task_id, "verdict": "FAIL", "note": "regression"})
    result = mark_reviewed(payload)
    assert result["review_verdict"] == "FAIL"
    assert result["review_note"] == "regression"
    assert task_id not in _pending_ids()


def test_mark_reviewed_accepts_dict_input() -> None:
    task_id = "review-flow-004"
    submit_task(task_id, status="success", requires_review=True)
    result = mark_reviewed({"task_id": task_id, "verdict": "BLOCKED", "note": "wait"})
    assert result["review_verdict"] == "BLOCKED"
    assert task_id not in _pending_ids()


def test_mark_reviewed_rejects_invalid_verdict() -> None:
    task_id = "review-flow-005"
    submit_task(task_id, status="success", requires_review=True)
    with pytest.raises(ValueError):
        mark_reviewed(task_id, "MAYBE")
    assert task_id in _pending_ids()


def test_mark_reviewed_rejects_unknown_task() -> None:
    with pytest.raises(KeyError):
        mark_reviewed("review-flow-unknown", "PASS")


def test_review_events_are_append_only_and_queryable() -> None:
    task_id = "review-flow-006"
    submit_task(task_id, status="success", requires_review=True)
    mark_reviewed(task_id, "PASS", "first")
    mark_reviewed(task_id, "FAIL", "second")
    events = get_review_events(task_id)
    assert [event["verdict"] for event in events] == ["PASS", "FAIL"]
    for event in events:
        assert event["action"] == "review"
        assert event["task_id"] == task_id
        assert event["timestamp"]
    assert get_review_events(task_id) == list_review_events(task_id)


def test_review_registry_fields_present() -> None:
    task_id = "review-flow-007"
    submit_task(task_id, status="success", requires_review=True)
    record = get_task_review(task_id)
    assert record is not None
    for field in ("reviewed", "review_verdict", "reviewed_at", "review_note"):
        assert field in record
    assert record["reviewed"] is False
    assert task_id in _pending_ids()


def test_only_success_tasks_are_pending() -> None:
    task_id = "review-flow-008"
    submit_task(task_id, status="fail", requires_review=True)
    assert task_id not in _pending_ids()


def test_no_auto_review_or_auto_pass() -> None:
    task_id = "review-flow-009"
    submit_task(task_id, status="success", requires_review=True)
    record = get_task_review(task_id)
    assert record["reviewed"] is False
    assert record["review_verdict"] is None
    assert record["reviewed_at"] is None


def test_mark_reviewed_verdict_allowlist() -> None:
    assert set(REVIEW_VERDICTS) == {"PASS", "FAIL", "BLOCKED"}


def test_task_review_action_report_contract() -> None:
    report = task_review_action_report()
    assert report["goal"] == TASK_REVIEW_GOAL
    assert report["STATUS"] == "PASS"
    assert report["新增项"]
    assert "Tests" in report
    assert report["Compatibility"] == {
        "submit_task": "UNCHANGED",
        "get_task_result": "UNCHANGED",
        "github_workflows": "UNCHANGED",
    }


GOLDEN_E2E_TASK_ID = "review-golden-e2e-001"


def test_golden_e2e_list_pending_returns_success_review_task() -> None:
    submit_task(
        GOLDEN_E2E_TASK_ID,
        goal="PERSONAL_AI_TASK_REVIEW_GOLDEN_E2E_VERIFY_V0.1",
        status="success",
        requires_review=True,
    )
    pending = {task["task_id"]: task for task in list_pending_results()}
    assert GOLDEN_E2E_TASK_ID in pending
    record = pending[GOLDEN_E2E_TASK_ID]
    assert record["requires_review"] is True
    assert record["status"] == "success"
    assert record["review_state"] == "pending_review"


def test_golden_e2e_get_task_result_returns_execution_result() -> None:
    result = get_task_result(GOLDEN_E2E_TASK_ID)
    assert set(result) == {
        "execution_summary",
        "commit",
        "tests",
        "artifacts",
        "execution_result_json",
        "evidence",
    }
    assert result["execution_summary"]["task_id"] == GOLDEN_E2E_TASK_ID
    assert set(result["evidence"]) >= {"acceptance", "logs", "validation", "decision"}


def test_golden_e2e_full_closed_loop() -> None:
    submit_task(
        GOLDEN_E2E_TASK_ID,
        goal="PERSONAL_AI_TASK_REVIEW_GOLDEN_E2E_VERIFY_V0.1",
        status="success",
        requires_review=True,
    )

    assert GOLDEN_E2E_TASK_ID in _pending_ids()

    result_before = get_task_result(GOLDEN_E2E_TASK_ID)
    snapshot_before = json.dumps(result_before, sort_keys=True)

    reviewed = mark_reviewed(GOLDEN_E2E_TASK_ID, "PASS", "golden e2e")
    assert reviewed["reviewed"] is True
    assert reviewed["review_verdict"] == "PASS"
    assert reviewed["reviewed_at"]

    assert GOLDEN_E2E_TASK_ID not in _pending_ids()

    events = get_review_events(GOLDEN_E2E_TASK_ID)
    assert len(events) == 1
    event = events[0]
    assert event["task_id"] == GOLDEN_E2E_TASK_ID
    assert event["action"] == "review"
    assert event["verdict"] == "PASS"
    assert event["timestamp"]

    snapshot_after = json.dumps(get_task_result(GOLDEN_E2E_TASK_ID), sort_keys=True)
    assert snapshot_after == snapshot_before


def test_golden_e2e_review_preserves_audit_history() -> None:
    record = get_task_review(GOLDEN_E2E_TASK_ID)
    assert record is not None
    assert record["reviewed"] is True
    assert record["review_verdict"] == "PASS"
    assert get_review_events(GOLDEN_E2E_TASK_ID) == get_review_events(GOLDEN_E2E_TASK_ID)
    events = [e for e in get_review_events() if e["task_id"] == GOLDEN_E2E_TASK_ID]
    assert len(events) == 1


def test_submit_task_signature_unchanged() -> None:
    signature = inspect.signature(submit_task)
    assert list(signature.parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    assert signature.parameters["goal"].default == ""
    assert signature.parameters["status"].default == "success"
    assert signature.parameters["requires_review"].default is True
    assert signature.parameters["extra"].kind is inspect.Parameter.VAR_KEYWORD


def test_get_task_result_signature_unchanged() -> None:
    signature = inspect.signature(get_task_result)
    assert list(signature.parameters) == ["task_id"]
    result = get_task_result("cf-compat-check")
    assert set(result) == {
        "execution_summary",
        "commit",
        "tests",
        "artifacts",
        "execution_result_json",
        "evidence",
    }
    assert result["execution_summary"]["task_id"] == "cf-compat-check"


def test_golden_e2e_report_outputs_status_tests_compatibility() -> None:
    report = task_review_action_report()
    assert report["STATUS"] == "PASS"
    assert report["Tests"] == "python -m pytest -q"
    assert report["Compatibility"]["submit_task"] == "UNCHANGED"
    assert report["Compatibility"]["get_task_result"] == "UNCHANGED"
    assert report["Compatibility"]["github_workflows"] == "UNCHANGED"


def test_runtime_audit_targets_requested_task() -> None:
    report = personal_ai_task_runtime_audit()
    assert report["report"] == "PERSONAL_AI_EXECUTION_TASK_RUNTIME_AUDIT_REPORT"
    assert report["task_id"] == RUNTIME_AUDIT_TASK_ID == "cf-62e0f30e0d02"
    assert report["goal"] == RUNTIME_AUDIT_GOAL


def test_runtime_audit_outputs_status_evidence_conclusion() -> None:
    report = personal_ai_task_runtime_audit()
    assert report["STATUS"] in {"PASS", "FAIL", "BLOCKED", "PARTIAL"}
    assert report["Evidence"]
    assert all(isinstance(item, str) and item for item in report["Evidence"])
    assert report["Conclusion"]
    assert report["status_source"]


def test_runtime_audit_reports_trigger_and_log_state() -> None:
    report = personal_ai_task_runtime_audit()
    assert isinstance(report["github_workflow_triggered"], bool)
    assert isinstance(report["execution_log_present"], bool)
    assert report["workflow_trigger_source"]
    assert isinstance(report["execution_log_evidence"], list)


def test_runtime_audit_gives_stuck_judgment() -> None:
    report = personal_ai_task_runtime_audit()
    assert isinstance(report["stuck"], bool)
    assert report["stuck_reason"]
    if not report["github_workflow_triggered"] and not report["execution_log_present"]:
        assert report["stuck"] is True
        assert report["STATUS"] != "PASS"


def test_runtime_audit_checks_and_markdown() -> None:
    report = personal_ai_task_runtime_audit()
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in {"PASS", "FAIL", "BLOCKED"}
        assert check["detail"]
    markdown = report["markdown"]
    assert markdown.startswith("# PERSONAL_AI_EXECUTION_TASK_RUNTIME_AUDIT_REPORT")
    for token in ("STATUS", "Evidence", "Conclusion", "Stuck judgment"):
        assert token in markdown


def test_runtime_audit_never_fabricates_runtime_state() -> None:
    report = personal_ai_task_runtime_audit()
    if report["registry_record"] is None:
        assert report["started_at"] is None
        assert report["heartbeat"] is None
        assert report["runner_status"] is None
    assert report["STATUS"] != "PASS" or report["registry_record"] is not None


def test_detail_exposure_report_shape() -> None:
    report = execution_result_detail_exposure_verify()
    assert report["report"] == "EXECUTION_RESULT_DETAIL_EXPOSURE_REPORT"
    assert report["goal"] == RESULT_DETAIL_GOAL
    assert report["task_id"] == RESULT_DETAIL_TASK_ID == "cf-3191b5302202"
    assert set(report) >= {
        "report",
        "goal",
        "task_id",
        "overall",
        "get_task_result_fields",
        "detail_exposure",
        "execution_result_json_obtained",
        "evidence_obtained",
        "artifacts_obtained",
        "submit_task_contract",
        "submit_task_signature_unchanged",
        "workflow_modified",
        "checks",
        "next_minimal_improvement",
        "markdown",
    }
    assert set(report["detail_exposure"]) == set(RESULT_DETAIL_FIELDS)
    for field in RESULT_DETAIL_FIELDS:
        info = report["detail_exposure"][field]
        assert set(info) >= {"returned", "obtained", "source", "reason"}
        assert isinstance(info["returned"], bool)
        assert isinstance(info["obtained"], bool)
        assert info["source"]
        assert info["reason"]


def test_detail_exposure_covers_contract_fields() -> None:
    report = execution_result_detail_exposure_verify()
    assert set(report["get_task_result_fields"]) == {
        "execution_summary",
        "commit",
        "tests",
        "artifacts",
        "execution_result_json",
        "evidence",
    }


def test_detail_exposure_flags_match_values() -> None:
    report = execution_result_detail_exposure_verify()
    exposure = report["detail_exposure"]
    assert report["execution_result_json_obtained"] == bool(
        exposure["execution_result_json"]["value"]
    )
    assert report["execution_result_json_obtained"] == exposure[
        "execution_result_json"
    ]["obtained"]
    assert report["evidence_obtained"] == exposure["evidence"]["obtained"]
    assert report["artifacts_obtained"] == exposure["artifacts"]["obtained"]


def test_detail_exposure_evidence_and_artifacts_available() -> None:
    report = execution_result_detail_exposure_verify()
    assert report["evidence_obtained"] is True
    assert report["artifacts_obtained"] is True
    paths = {a["path"] for a in get_task_result(RESULT_DETAIL_TASK_ID)["artifacts"]}
    assert {"hello.py", "test_hello.py"} <= paths


def test_detail_exposure_overall_status_logic() -> None:
    report = execution_result_detail_exposure_verify()
    flags = (
        report["execution_result_json_obtained"],
        report["evidence_obtained"],
        report["artifacts_obtained"],
    )
    if all(flags):
        assert report["overall"] == "PASS"
    elif not any(flags):
        assert report["overall"] == "BLOCKED"
    else:
        assert report["overall"] == "PARTIAL"


def test_detail_exposure_does_not_change_contract_or_workflows() -> None:
    report = execution_result_detail_exposure_verify()
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["submit_task_signature_unchanged"] is True
    assert report["workflow_modified"] is False
    assert report["next_minimal_improvement"]


def test_detail_exposure_checks_and_markdown() -> None:
    report = execution_result_detail_exposure_verify()
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in {"PASS", "FAIL", "BLOCKED"}
        assert check["detail"]
    markdown = report["markdown"]
    assert markdown.startswith("# EXECUTION_RESULT_DETAIL_EXPOSURE_REPORT")
    assert f"- task_id: {RESULT_DETAIL_TASK_ID}" in markdown
    for field in RESULT_DETAIL_FIELDS:
        assert field in markdown


def test_detail_exposure_submit_task_still_unchanged() -> None:
    signature = inspect.signature(submit_task)
    assert list(signature.parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]


def _auto_task(
    task_id: str, status: str = "success", requires_review: bool = True
) -> None:
    submit_task(
        task_id,
        goal=AUTO_CONSUMER_GOAL,
        status=status,
        requires_review=requires_review,
    )


def test_auto_consumer_report_shape() -> None:
    report = task_result_auto_consumer_report()
    assert report["report"] == AUTO_CONSUMER_REPORT
    assert report["goal"] == AUTO_CONSUMER_GOAL
    assert report["task_id"] == AUTO_CONSUMER_TASK_ID == "cf-21d939a5569c"
    assert report["STATUS"] in {"PASS", "FAIL"}
    assert report["新增项"]
    assert report["Tests"] == "python -m pytest -q"
    assert report["Compatibility"] == {
        "submit_task": "UNCHANGED",
        "get_task_result": "COMPATIBLE",
        "github_workflows": "UNCHANGED",
    }
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in {"PASS", "FAIL", "BLOCKED"}
        assert check["detail"]
    markdown = report["markdown"]
    assert markdown.startswith(f"# {AUTO_CONSUMER_REPORT}")
    assert f"- task_id: {AUTO_CONSUMER_TASK_ID}" in markdown
    assert "## Compatibility" in markdown


def test_auto_consumer_discovers_success_only() -> None:
    success_id = "auto-consumer-discover-ok"
    fail_id = "auto-consumer-discover-fail"
    _auto_task(success_id, status="success")
    _auto_task(fail_id, status="fail")
    discovered = {item["task_id"]: item for item in discover_completed_results()}
    assert success_id in discovered
    assert fail_id not in discovered
    entry = discovered[success_id]
    assert entry["status"] == "success"
    assert entry["review_state"] == "pending_review"
    assert entry["discovered_by"] == "task_result_auto_consumer"


def test_auto_consumer_identifies_success_and_reads_result() -> None:
    task_id = "auto-consumer-read-ok"
    _auto_task(task_id)
    consumed = consume_task_result(task_id)
    assert consumed["identified_success"] is True
    assert consumed["identified_status"] == "success"
    assert consumed["result_status"] in VALID_STATUSES
    assert isinstance(consumed["result"], dict)
    assert set(consumed["result"]) == {
        "execution_summary",
        "commit",
        "tests",
        "artifacts",
        "execution_result_json",
        "evidence",
    }
    assert consumed["result"]["execution_summary"]["task_id"] == task_id
    assert consumed["status_source"]


def test_auto_consumer_generates_requires_review_entry() -> None:
    task_id = "auto-consumer-requires-review"
    _auto_task(task_id, requires_review=False)
    consumed = consume_task_result(task_id)
    assert consumed["identified_success"] is True
    assert consumed["requires_review"] is True
    assert consumed["review_state"] == "pending_review"
    assert consumed["human_review_gate"] is True
    assert task_id in {t["task_id"] for t in list_pending_results()}


def test_auto_consumer_does_not_auto_review_or_trigger_next() -> None:
    task_id = "auto-consumer-no-auto"
    _auto_task(task_id)
    consume_task_result(task_id)
    record = get_task_review(task_id)
    assert record["reviewed"] is False
    assert record["review_verdict"] is None
    assert record["reviewed_at"] is None


def test_auto_consumer_preserves_human_review_flow() -> None:
    task_id = "auto-consumer-human-review"
    _auto_task(task_id)
    consume_task_result(task_id)
    assert task_id in _pending_ids()
    reviewed = mark_reviewed(task_id, "PASS", "human consumes result")
    assert reviewed["review_verdict"] == "PASS"
    assert task_id not in _pending_ids()
    again = consume_task_result(task_id)
    assert again["reviewed"] is True
    assert again["review_state"] == "reviewed"


def test_auto_consumer_non_success_is_not_pending() -> None:
    task_id = "auto-consumer-blocked"
    submit_task(
        task_id, goal=AUTO_CONSUMER_GOAL, status="fail", requires_review=True
    )
    consumed = consume_task_result(task_id)
    assert consumed["identified_success"] is False
    assert consumed["review_state"] == "not_applicable"
    assert task_id not in _pending_ids()


def test_auto_consumer_rejects_empty_task_id() -> None:
    with pytest.raises(ValueError):
        consume_task_result("")


def test_auto_consumer_contracts_unchanged() -> None:
    signature = inspect.signature(submit_task)
    assert list(signature.parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    result_signature = inspect.signature(get_task_result)
    assert list(result_signature.parameters) == ["task_id"]
    report = task_result_auto_consumer_report()
    assert report["Compatibility"]["submit_task"] == "UNCHANGED"
    assert report["Compatibility"]["get_task_result"] == "COMPATIBLE"


def test_auto_consumer_report_consumes_discovered() -> None:
    task_id = "auto-consumer-report"
    _auto_task(task_id)
    report = task_result_auto_consumer_report()
    assert task_id in report["discovered_task_ids"]
    assert task_id in report["requires_review_ids"]
    assert task_id in report["identified_success"]
    entries = {c["task_id"]: c for c in report["consumed"]}
    assert entries[task_id]["review_state"] == "pending_review"
    assert report["STATUS"] == "PASS"


def test_auto_consumer_golden_e2e_report_shape() -> None:
    report = task_result_auto_consumer_golden_e2e_verify()
    assert report["report"] == AUTO_CONSUMER_GOLDEN_E2E_REPORT
    assert report["goal"] == AUTO_CONSUMER_GOLDEN_E2E_GOAL
    assert report["task_id"] == AUTO_CONSUMER_GOLDEN_E2E_TASK_ID == "cf-24192a013493"
    assert report["STATUS"] in {"PASS", "FAIL"}
    assert report["Tests"] == "python -m pytest -q"
    assert report["Compatibility"] == {
        "submit_task": "UNCHANGED",
        "get_task_result": "UNCHANGED",
        "github_workflows": "UNCHANGED",
    }
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    assert report["验证步骤"] == report["steps"]
    assert report["pending_review"]
    markdown = report["markdown"]
    assert markdown.startswith(f"# {AUTO_CONSUMER_GOLDEN_E2E_REPORT}")
    assert f"- task_id: {AUTO_CONSUMER_GOLDEN_E2E_TASK_ID}" in markdown
    assert "## 验证步骤" in markdown
    assert "## Compatibility" in markdown
    assert "python -m pytest -q" in markdown


def test_auto_consumer_golden_e2e_steps_cover_required_checks() -> None:
    report = task_result_auto_consumer_golden_e2e_verify()
    step_names = [step["step"] for step in report["steps"]]
    assert step_names == list(AUTO_CONSUMER_GOLDEN_E2E_STEPS)
    for step in report["steps"]:
        assert set(step) >= {"step", "status", "detail"}
        assert step["status"] in {"PASS", "FAIL", "BLOCKED"}
        assert step["detail"]
    assert report["STATUS"] == "PASS"


def test_auto_consumer_golden_e2e_real_task_enters_human_review() -> None:
    report = task_result_auto_consumer_golden_e2e_verify()
    task_id = AUTO_CONSUMER_GOLDEN_E2E_TASK_ID
    assert report["consumed"]["task_id"] == task_id
    assert report["consumed"]["identified_success"] is True
    assert report["consumed"]["requires_review"] is True
    assert report["consumed"]["review_state"] == "pending_review"
    assert task_id in report["pending_review"]
    assert task_id in _pending_ids()


def test_auto_consumer_golden_e2e_never_auto_reviews_real_task() -> None:
    task_result_auto_consumer_golden_e2e_verify()
    record = get_task_review(AUTO_CONSUMER_GOLDEN_E2E_TASK_ID)
    assert record["reviewed"] is False
    assert record["review_verdict"] is None
    assert record["reviewed_at"] is None


def test_auto_consumer_golden_e2e_mark_reviewed_flow_compatible() -> None:
    report = task_result_auto_consumer_golden_e2e_verify()
    probe_id = report["review_flow_probe"]
    probe = get_task_review(probe_id)
    assert probe["reviewed"] is True
    assert probe["review_verdict"] == "PASS"
    assert probe_id not in _pending_ids()
    events = get_review_events(probe_id)
    assert events
    assert events[-1]["action"] == "review"
    assert events[-1]["verdict"] == "PASS"
    assert AUTO_CONSUMER_GOLDEN_E2E_TASK_ID in _pending_ids()


def test_auto_consumer_golden_e2e_contracts_unchanged() -> None:
    task_result_auto_consumer_golden_e2e_verify()
    signature = inspect.signature(submit_task)
    assert list(signature.parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    result_signature = inspect.signature(get_task_result)
    assert list(result_signature.parameters) == ["task_id"]
    result = get_task_result(AUTO_CONSUMER_GOLDEN_E2E_TASK_ID)
    assert set(result) == {
        "execution_summary",
        "commit",
        "tests",
        "artifacts",
        "execution_result_json",
        "evidence",
    }


def test_auto_consumer_golden_e2e_rejects_empty_task_id() -> None:
    with pytest.raises(ValueError):
        task_result_auto_consumer_golden_e2e_verify("")


def test_post_e2e_audit_report_shape() -> None:
    report = task_result_auto_consumer_post_e2e_audit()
    assert report["report"] == POST_E2E_AUDIT_REPORT
    assert report["goal"] == POST_E2E_AUDIT_GOAL
    assert report["task_id"] == POST_E2E_AUDIT_TASK_ID == "cf-e114822ee2ae"
    assert report["STATUS"] in VALID_STATUSES
    assert report["report_status"] in VALID_STATUSES
    assert set(report) >= {
        "report",
        "goal",
        "task_id",
        "STATUS",
        "report_status",
        "auto_consumer_reached",
        "primary_gap",
        "gap_layers",
        "layers",
        "evidence",
        "golden_e2e_status",
        "golden_e2e_steps",
        "consumed",
        "consumed_task_ids",
        "pending_review",
        "discovered_task_ids",
        "review_event_count",
        "target_task_id",
        "target_task_status",
        "target_task_stuck",
        "target_task_stuck_reason",
        "status_model_expected_fields",
        "status_model_missing_fields",
        "status_model_gap",
        "minimal_fix_suggestions",
        "human_review_gate",
        "auto_pass",
        "auto_trigger_next",
        "compatibility",
        "checks",
        "markdown",
    }


def test_post_e2e_audit_captures_real_consumer_evidence() -> None:
    report = task_result_auto_consumer_post_e2e_audit()
    assert report["golden_e2e_status"] == "PASS"
    assert report["golden_e2e_steps"]
    consumed = report["consumed"]
    assert consumed["identified_success"] is True
    assert consumed["requires_review"] is True
    assert consumed["review_state"] == "pending_review"
    assert consumed["task_id"] in report["pending_review"]
    assert report["review_event_count"] >= 1
    assert report["discovered_task_ids"]
    evidence = report["evidence"]
    assert evidence["golden_e2e_status"] == "PASS"
    assert evidence["consumed_records"][0]["task_id"] == consumed["task_id"]


def test_post_e2e_audit_layer_assessment() -> None:
    report = task_result_auto_consumer_post_e2e_audit()
    assert set(report["layers"]) == set(POST_E2E_AUDIT_LAYERS)
    for name, info in report["layers"].items():
        assert set(info) >= {"present", "detail"}
        assert isinstance(info["present"], bool)
        assert info["detail"]
    assert report["layers"]["read"]["present"] is True
    assert report["gap_layers"] == [
        name
        for name in POST_E2E_AUDIT_LAYERS
        if not report["layers"][name]["present"]
    ]
    assert report["auto_consumer_reached"] is (not report["gap_layers"])


def test_post_e2e_audit_not_reached_without_manual_follow_up() -> None:
    report = task_result_auto_consumer_post_e2e_audit()
    assert report["auto_consumer_reached"] is False
    assert report["STATUS"] != "PASS"
    assert report["primary_gap"] in POST_E2E_AUDIT_LAYERS
    assert report["gap_layers"]
    assert report["layers"]["trigger"]["present"] is False
    assert report["layers"]["notification"]["present"] is False


def test_post_e2e_audit_reports_cf62_state_and_root_cause() -> None:
    report = task_result_auto_consumer_post_e2e_audit()
    assert report["target_task_id"] == RUNTIME_AUDIT_TASK_ID == "cf-62e0f30e0d02"
    assert report["target_task_status"] in {"PASS", "FAIL", "BLOCKED", "PARTIAL"}
    assert report["target_task_status"] != "PASS"
    assert report["target_task_stuck"] is True
    assert report["target_task_stuck_reason"]
    assert report["target_task_conclusion"]
    assert "cf-62e0f30e0d02" in report["markdown"]


def test_post_e2e_audit_status_model_gap_and_fixes() -> None:
    report = task_result_auto_consumer_post_e2e_audit()
    assert report["status_model_expected_fields"] == list(
        STATUS_MODEL_EXPECTED_FIELDS
    )
    missing = set(report["status_model_missing_fields"])
    assert {"last_update_at", "timeout", "stuck"} <= missing
    assert report["status_model_gap"]
    assert len(report["minimal_fix_suggestions"]) >= 3
    for suggestion in report["minimal_fix_suggestions"]:
        assert suggestion


def test_post_e2e_audit_never_auto_pass_or_trigger() -> None:
    report = task_result_auto_consumer_post_e2e_audit()
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    record = get_task_review(AUTO_CONSUMER_GOLDEN_E2E_TASK_ID)
    assert record["reviewed"] is False
    assert record["review_verdict"] is None


def test_post_e2e_audit_contracts_unchanged() -> None:
    report = task_result_auto_consumer_post_e2e_audit()
    assert report["compatibility"] == {
        "submit_task": "UNCHANGED",
        "get_task_result": "UNCHANGED",
        "github_workflows": "UNCHANGED",
    }
    assert list(inspect.signature(submit_task).parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    assert list(inspect.signature(get_task_result).parameters) == ["task_id"]


def test_post_e2e_audit_checks_and_markdown() -> None:
    report = task_result_auto_consumer_post_e2e_audit()
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in {"PASS", "FAIL", "BLOCKED"}
        assert check["detail"]
    markdown = report["markdown"]
    assert markdown.startswith(f"# {POST_E2E_AUDIT_REPORT}")
    assert f"- task_id: {POST_E2E_AUDIT_TASK_ID}" in markdown
    assert "## Golden E2E consumer evidence" in markdown
    assert "## Layer gap assessment" in markdown
    assert "## Status model gap" in markdown
    assert "## Minimal fix suggestions" in markdown


def test_gap_close_report_shape() -> None:
    report = task_result_auto_consumer_gap_close_report()
    assert report["report"] == GAP_CLOSE_REPORT
    assert report["goal"] == GAP_CLOSE_GOAL
    assert report["task_id"] == GAP_CLOSE_TASK_ID == "cf-95b618168963"
    assert report["STATUS"] in {"PASS", "FAIL", "BLOCKED", "PARTIAL"}
    assert report["变更项"]
    assert report["Tests"] == "python -m pytest -q"
    assert report["Compatibility"] == {
        "submit_task": "UNCHANGED",
        "get_task_result": "UNCHANGED",
        "mark_reviewed": "COMPATIBLE",
        "list_pending_results": "COMPATIBLE",
        "review_event": "COMPATIBLE",
        "github_workflows": "UNCHANGED",
    }
    assert isinstance(report["Remaining Gaps"], list)
    assert report["Remaining Gaps"]
    assert set(report["layers"]) == set(GAP_CLOSE_LAYERS)
    for name, info in report["layers"].items():
        assert set(info) >= {"present", "detail"}
        assert isinstance(info["present"], bool)
        assert info["detail"]
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in {"PASS", "FAIL", "BLOCKED"}
        assert check["detail"]
    markdown = report["markdown"]
    assert markdown.startswith(f"# {GAP_CLOSE_REPORT}")
    for token in ("## 变更项", "## Tests", "## Compatibility", "## Remaining Gaps"):
        assert token in markdown


def test_gap_close_layers_equivalents_present() -> None:
    report = task_result_auto_consumer_gap_close_report()
    for name in GAP_CLOSE_LAYERS:
        assert report["layers"][name]["present"] is True
    assert report["gap_layers"] == []
    assert report["STATUS"] == "PASS"
    assert report["consumer_evidence"]["persisted"] is True
    assert report["consumer_evidence"]["queryable"] is True
    assert report["consumer_evidence"]["event_count"] >= 1


def test_gap_close_target_long_pending_is_terminal() -> None:
    report = task_result_auto_consumer_gap_close_report()
    assert report["target_task_id"] == RUNTIME_AUDIT_TASK_ID == "cf-62e0f30e0d02"
    assert report["target_task_state"] in {"stuck", "timed_out", "failed"}
    assert report["target_task_terminal"] is True
    assert report["target_task_state_reason"]
    evidence = [
        event
        for event in report["consumption_evidence"]
        if event["task_id"] == RUNTIME_AUDIT_TASK_ID
    ]
    assert evidence


def test_gap_close_evidence_persisted_and_queryable(tmp_path, monkeypatch) -> None:
    state = tmp_path / "consumer_state.json"
    monkeypatch.setenv(CONSUMER_EVIDENCE_ENV, str(state))
    event = record_consumer_evidence(
        "consumed", "gap-close-evidence-001", detail="probe"
    )
    assert event["task_id"] == "gap-close-evidence-001"
    assert event["event_type"] == "consumed"
    assert event["consumed"] is True
    assert state.is_file()
    saved = json.loads(state.read_text(encoding="utf-8"))
    assert saved["kind"]
    assert any(
        e["task_id"] == "gap-close-evidence-001" for e in saved["events"]
    )
    queried = get_consumption_evidence("gap-close-evidence-001")
    assert queried
    assert queried[-1]["event_type"] == "consumed"
    assert get_consumer_evidence_path() == state
    status = consumer_evidence_status()
    assert status["persisted"] is True
    assert status["queryable"] is True
    assert status["event_count"] >= 1


def test_record_consumer_evidence_requires_args() -> None:
    with pytest.raises(ValueError):
        record_consumer_evidence("", "gap-close-bad")
    with pytest.raises(ValueError):
        record_consumer_evidence("consumed", "")


def test_consumer_heartbeat_auto_consumes_and_records() -> None:
    task_id = "gap-close-heartbeat-001"
    submit_task(
        task_id, goal=GAP_CLOSE_GOAL, status="success", requires_review=False
    )
    heartbeat = consumer_heartbeat(force=True)
    assert heartbeat["ran"] is True
    assert heartbeat["wired"] is True
    assert task_id in heartbeat["discovered"]
    consumed_ids = {item["task_id"] for item in heartbeat["result"]["consumed"]}
    assert task_id in consumed_ids
    assert heartbeat["result"]["auto_pass"] is False
    assert heartbeat["result"]["auto_trigger_next"] is False
    evidence = get_consumption_evidence(task_id)
    assert any(e["event_type"] == "discovered" for e in evidence)
    assert any(e["event_type"] == "consumed" for e in evidence)
    record = get_task_review(task_id)
    assert record["reviewed"] is False
    assert record["review_verdict"] is None
    assert task_id in {item["task_id"] for item in list_pending_results()}


def test_auto_consume_entrypoint_returns_evidence() -> None:
    task_id = "gap-close-entrypoint-001"
    submit_task(task_id, goal=GAP_CLOSE_GOAL, status="success")
    result = auto_consume_completed_results()
    assert task_id in result["discovered"]
    assert result["consumption_record_count"] == len(result["consumed"])
    assert result["human_review_gate"] is True
    assert get_task_review(task_id)["reviewed"] is False


def test_pending_acceptance_notice_exposes_pending() -> None:
    task_id = "gap-close-notice-001"
    submit_task(task_id, goal=GAP_CLOSE_GOAL, status="success", requires_review=True)
    notice = pending_acceptance_notice()
    assert notice["present"] is True
    assert notice["count"] >= 1
    assert "PENDING ACCEPTANCE" in notice["notice"]
    assert task_id in notice["task_ids"]
    entry = next(item for item in notice["items"] if item["task_id"] == task_id)
    assert entry["state"] == "pending_review"
    assert entry["terminal"] is False
    assert entry["requires_review"] is True


def test_classify_pending_task_non_success_not_pending() -> None:
    task_id = "gap-close-failed-001"
    submit_task(task_id, goal=GAP_CLOSE_GOAL, status="fail")
    info = classify_pending_task(task_id)
    assert info["state"] == "failed"
    assert info["terminal"] is True


def test_gap_close_mark_reviewed_compatibility() -> None:
    report = task_result_auto_consumer_gap_close_report()
    probe = report["review_probe"]
    assert probe["ok"] is True
    assert probe["pending_before"] is True
    assert probe["pending_after"] is False
    record = get_task_review(probe["probe_id"])
    assert record["reviewed"] is True
    assert record["review_verdict"] == "PASS"
    events = get_review_events(probe["probe_id"])
    assert events
    assert events[-1]["action"] == "review"
    assert events[-1]["verdict"] == "PASS"


def test_gap_close_contracts_unchanged() -> None:
    assert list(inspect.signature(submit_task).parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    assert list(inspect.signature(get_task_result).parameters) == ["task_id"]
    assert list(inspect.signature(consume_task_result).parameters) == ["task_id"]
    assert list(inspect.signature(mark_reviewed).parameters) == [
        "task_id",
        "verdict",
        "note",
    ]


def test_expire_stale_pending_marks_timed_out() -> None:
    task_id = "gap-close-timeout-001"
    submit_task(
        task_id, goal=GAP_CLOSE_GOAL, status="success", requires_review=True
    )
    assert task_id in {item["task_id"] for item in list_pending_results()}
    future = datetime.now(timezone.utc) + timedelta(
        seconds=PENDING_TIMEOUT_SECONDS + 10
    )
    info = classify_pending_task(task_id, now=future)
    assert info["state"] == "timed_out"
    assert info["terminal"] is True
    expired = expire_stale_pending(now=future)
    assert any(item["task_id"] == task_id for item in expired)
    assert task_id not in {item["task_id"] for item in list_pending_results()}
    record = get_task_review(task_id)
    assert record["timed_out"] is True
    assert record["terminal_state"] == "timed_out"
    assert record["timeout_reason"]
    assert any(
        event["event_type"] == "timed_out"
        for event in get_consumption_evidence(task_id)
    )


def test_live_acceptance_report_shape() -> None:
    report = task_result_auto_consumer_live_acceptance_report()
    assert report["report"] == LIVE_ACCEPTANCE_REPORT
    assert report["goal"] == LIVE_ACCEPTANCE_GOAL
    assert report["task_id"] == LIVE_ACCEPTANCE_TASK_ID == "cf-87e0bd844e84"
    assert report["LIVE_ACCEPTANCE"] == report["STATUS"]
    assert report["LIVE_ACCEPTANCE"] in VALID_STATUSES
    assert report["Tests"] == "python -m pytest -q"
    assert report["Evidence"]
    assert report["Remaining Gaps"]
    assert set(report["Compatibility"]) == {
        "submit_task",
        "get_task_result",
        "mark_reviewed",
        "list_pending_results",
        "review_event",
        "github_workflows",
    }
    assert report["probe_task_id"]
    markdown = report["markdown"]
    assert markdown.startswith(f"# {LIVE_ACCEPTANCE_REPORT}")
    assert f"- task_id: {LIVE_ACCEPTANCE_TASK_ID}" in markdown
    for token in (
        "## Live acceptance steps",
        "## Evidence",
        "## Tests",
        "## Compatibility",
        "## Remaining Gaps",
    ):
        assert token in markdown


def test_live_acceptance_steps_and_status() -> None:
    report = task_result_auto_consumer_live_acceptance_report()
    assert report["steps"]
    for step in report["steps"]:
        assert set(step) >= {"step", "status", "detail"}
        assert step["status"] in VALID_STATUSES
        assert step["detail"]
    assert report["LIVE_ACCEPTANCE"] == "PASS"


def test_live_acceptance_auto_discovery_without_manual_query() -> None:
    report = task_result_auto_consumer_live_acceptance_report()
    assert report["automatic_discovery_without_manual_query"] is True
    probe = report["live_probe"]
    assert probe["manual_get_task_result_calls"] == 0
    assert probe["auto_discovered"] is True
    assert probe["requires_review"] is True
    assert probe["pending_state"] == "pending_review"
    assert report["pending_acceptance_visible"] is True


def test_live_acceptance_consumption_evidence_persisted() -> None:
    report = task_result_auto_consumer_live_acceptance_report()
    assert report["consumption_evidence_persisted"] is True
    probe = report["live_probe"]
    assert probe["evidence_discovered"] is True
    assert probe["evidence_consumed"] is True
    storage = report["consumer_evidence"]
    assert storage["persisted"] is True
    assert storage["queryable"] is True
    queried = get_consumption_evidence(probe["task_id"])
    assert any(e["event_type"] == "discovered" for e in queried)
    assert any(e["event_type"] == "consumed" for e in queried)


def test_live_acceptance_mark_reviewed_closes_pending_and_traces_event() -> None:
    report = task_result_auto_consumer_live_acceptance_report()
    assert report["mark_reviewed_closes_pending"] is True
    assert report["review_event_traceable"] is True
    probe = report["live_probe"]
    assert probe["reviewed"] is True
    assert probe["review_verdict"] == "PASS"
    assert probe["pending_after_review"] is False
    assert probe["review_event_count"] >= 1
    assert probe["review_event_verdict"] == "PASS"
    events = get_review_events(probe["task_id"])
    assert events
    assert events[-1]["action"] == "review"
    assert events[-1]["verdict"] == "PASS"
    assert events[-1]["timestamp"]
    assert probe["task_id"] not in {
        t["task_id"] for t in list_pending_results()
    }


def test_live_acceptance_target_task_terminal_not_pending() -> None:
    report = task_result_auto_consumer_live_acceptance_report()
    assert report["target_task_id"] == RUNTIME_AUDIT_TASK_ID == "cf-62e0f30e0d02"
    assert report["target_task_terminal"] is True
    assert report["target_task_state"] in {"stuck", "timed_out", "failed"}
    assert report["target_task_pending"] is False
    assert report["target_task_state_reason"]
    assert report["target_task_terminal_evidence"]
    assert "cf-62e0f30e0d02" in report["markdown"]


def test_live_acceptance_contracts_unchanged() -> None:
    report = task_result_auto_consumer_live_acceptance_report()
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["get_task_result_contract"] == "UNCHANGED"
    assert list(inspect.signature(submit_task).parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    assert list(inspect.signature(get_task_result).parameters) == ["task_id"]


def test_live_acceptance_no_auto_pass_or_trigger() -> None:
    report = task_result_auto_consumer_live_acceptance_report()
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    probe = report["live_probe"]
    assert probe["manual_get_task_result_calls"] == 0
    record = get_task_review(probe["task_id"])
    assert record["reviewed"] is True
    assert record["review_verdict"] == "PASS"


def test_production_readiness_report_shape() -> None:
    report = task_result_auto_consumer_production_readiness_report()
    assert report["report"] == PRODUCTION_READINESS_REPORT
    assert report["goal"] == PRODUCTION_READINESS_GOAL
    assert report["task_id"] == PRODUCTION_READINESS_TASK_ID == "cf-c6f00c4926eb"
    assert report["PRODUCTION_READINESS"] == report["STATUS"]
    assert report["PRODUCTION_READINESS"] in VALID_STATUSES
    assert report["Tests"] == "python -m pytest -q"
    assert report["Evidence"]
    assert report["Known Limitations"]
    assert report["Remaining Gaps"]
    assert set(report["Compatibility"]) == {
        "submit_task",
        "get_task_result",
        "mark_reviewed",
        "list_pending_results",
        "review_event",
        "github_workflows",
    }
    markdown = report["markdown"]
    assert markdown.startswith(f"# {PRODUCTION_READINESS_REPORT}")
    assert f"- task_id: {PRODUCTION_READINESS_TASK_ID}" in markdown
    for token in (
        "## Production readiness steps",
        "## Evidence",
        "## Tests",
        "## Known Limitations",
        "## Compatibility",
        "## Remaining Gaps",
    ):
        assert token in markdown


def test_production_readiness_steps_and_status() -> None:
    report = task_result_auto_consumer_production_readiness_report()
    assert report["steps"]
    for step in report["steps"]:
        assert set(step) >= {"step", "status", "detail"}
        assert step["status"] in VALID_STATUSES
        assert step["detail"]
    assert report["PRODUCTION_READINESS"] == "PASS"


def test_production_readiness_batch_no_missed_or_duplicate_consumption() -> None:
    report = task_result_auto_consumer_production_readiness_report()
    assert report["batch_size"] == 3
    assert report["missed_consumption"] == []
    assert report["duplicate_consumption"] == []
    assert set(report["batch_task_ids"]) <= set(report["first_scan_newly_consumed"])
    for task_id in report["batch_task_ids"]:
        events = get_consumption_evidence(task_id)
        assert sum(1 for e in events if e["event_type"] == "discovered") == 1
        assert sum(1 for e in events if e["event_type"] == "consumed") == 1


def test_production_readiness_repeated_and_restart_scan_idempotent() -> None:
    report = task_result_auto_consumer_production_readiness_report()
    assert report["repeated_scan_idempotent"] is True
    assert report["restart_scan_idempotent"] is True
    assert report["restart_scan_reconsumed"] == []
    assert not (
        set(report["repeated_scan_newly_consumed"])
        & set(report["batch_task_ids"])
    )
    assert report["batch_task_ids"][0] in report["durable_consumed_task_ids"]


def test_production_readiness_review_gate_and_event_traceable() -> None:
    report = task_result_auto_consumer_production_readiness_report()
    assert report["human_review_gate"] is True
    assert report["review_event_traceable"] is True
    assert report["review_gate_not_reopened"] is True
    reviewed_id = report["reviewed_task_id"]
    events = get_review_events(reviewed_id)
    assert events
    assert events[-1]["action"] == "review"
    assert events[-1]["verdict"] == "PASS"
    assert events[-1]["timestamp"]
    record = get_task_review(reviewed_id)
    assert record["reviewed"] is True
    assert reviewed_id not in {
        item["task_id"] for item in list_pending_results()
    }


def test_production_readiness_permanent_pending_disposition() -> None:
    report = task_result_auto_consumer_production_readiness_report()
    assert report["permanent_pending_disposition"] is True
    assert report["stale_task_terminal"] is True
    assert report["stale_task_state"] == "timed_out"
    record = get_task_review(report["stale_task_id"])
    assert record["timed_out"] is True
    assert record["terminal_state"] == "timed_out"
    assert any(
        event["event_type"] == "timed_out"
        for event in get_consumption_evidence(report["stale_task_id"])
    )


def test_production_readiness_target_task_terminal() -> None:
    report = task_result_auto_consumer_production_readiness_report()
    assert report["target_task_id"] == RUNTIME_AUDIT_TASK_ID == "cf-62e0f30e0d02"
    assert report["target_task_terminal"] is True
    assert report["target_task_state"] in {"stuck", "timed_out", "failed"}
    assert report["target_task_pending"] is False
    assert report["target_task_state_reason"]
    assert report["target_task_terminal_evidence"]
    assert "cf-62e0f30e0d02" in report["markdown"]


def test_production_readiness_contracts_unchanged() -> None:
    report = task_result_auto_consumer_production_readiness_report()
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["get_task_result_contract"] == "UNCHANGED"
    assert list(inspect.signature(submit_task).parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    assert list(inspect.signature(get_task_result).parameters) == ["task_id"]


def test_production_readiness_outputs_tests_evidence_limitations_gaps() -> None:
    report = task_result_auto_consumer_production_readiness_report()
    assert report["Tests"] == "python -m pytest -q"
    assert isinstance(report["Evidence"], list) and report["Evidence"]
    assert isinstance(report["Known Limitations"], list) and report["Known Limitations"]
    assert isinstance(report["Remaining Gaps"], list) and report["Remaining Gaps"]
    assert report["known_limitations"] == report["Known Limitations"]
    assert report["remaining_gaps"] == report["Remaining Gaps"]


def test_production_readiness_no_auto_pass_or_trigger() -> None:
    report = task_result_auto_consumer_production_readiness_report()
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    assert report["human_review_gate"] is True


def test_consumer_evidence_ledger_survives_restart(tmp_path, monkeypatch) -> None:
    ledger = tmp_path / "consumer_evidence.json"
    monkeypatch.setenv(CONSUMER_EVIDENCE_ENV, str(ledger))
    saved = list(hello_module.CONSUMPTION_EVIDENCE)
    hello_module.CONSUMPTION_EVIDENCE.clear()
    try:
        record_consumer_evidence("discovered", "restart-probe-a", detail="first")
        record_consumer_evidence("consumed", "restart-probe-a", detail="first")
        hello_module.CONSUMPTION_EVIDENCE.clear()
        record_consumer_evidence("discovered", "restart-probe-b", detail="second")
        persisted = {
            event["task_id"]
            for event in json.loads(ledger.read_text(encoding="utf-8"))["events"]
        }
        assert {"restart-probe-a", "restart-probe-b"} <= persisted
    finally:
        hello_module.CONSUMPTION_EVIDENCE.clear()
        hello_module.CONSUMPTION_EVIDENCE.extend(saved)


def test_final_evidence_audit_report_shape() -> None:
    report = task_result_auto_consumer_final_evidence_audit()
    assert report["report"] == FINAL_EVIDENCE_AUDIT_REPORT
    assert report["goal"] == FINAL_EVIDENCE_AUDIT_GOAL
    assert report["task_id"] == FINAL_EVIDENCE_AUDIT_TASK_ID == "cf-55462c30f4f9"
    assert report["FINAL_EVIDENCE_AUDIT"] == report["STATUS"]
    assert report["FINAL_EVIDENCE_AUDIT"] in VALID_STATUSES
    assert report["Tests"] == "python -m pytest -q"
    assert report["Evidence"]
    assert report["Known Limitations"]
    assert report["Remaining Gaps"]
    assert set(report["Compatibility"]) == {
        "submit_task",
        "get_task_result",
        "mark_reviewed",
        "list_pending_results",
        "review_event",
        "github_workflows",
    }
    assert report["steps"]
    assert report["checks"]
    markdown = report["markdown"]
    assert markdown.startswith(f"# {FINAL_EVIDENCE_AUDIT_REPORT}")
    assert f"- task_id: {FINAL_EVIDENCE_AUDIT_TASK_ID}" in markdown
    assert f"FINAL_EVIDENCE_AUDIT: {report['FINAL_EVIDENCE_AUDIT']}" in markdown


def test_final_evidence_audit_consumer_idempotency_evidence() -> None:
    report = task_result_auto_consumer_final_evidence_audit()
    assert report["missed_consumption"] == []
    assert report["duplicate_consumption"] == []
    assert report["repeated_scan_idempotent"] is True
    assert report["restart_scan_idempotent"] is True
    assert report["restart_scan_reconsumed"] == []
    assert report["durable_consumed_task_ids"]
    idempotency = report["consumer_idempotency"]
    assert idempotency["evidence_persisted"] is True
    assert idempotency["evidence_queryable"] is True
    assert idempotency["batch_size"] == 3
    assert set(idempotency["batch_task_ids"]) <= set(
        idempotency["durable_consumed_task_ids"]
    )


def test_final_evidence_audit_review_event_audit() -> None:
    report = task_result_auto_consumer_final_evidence_audit()
    audit = report["review_event_audit"]
    assert audit["mark_reviewed_only_close_action"] is True
    assert audit["auto_pass"] is False
    assert audit["auto_trigger_next"] is False
    assert audit["review_event_traceable"] is True
    assert audit["review_event_count"] >= 1
    events = audit["review_events"]
    assert events
    last = events[-1]
    assert last["task_id"] == audit["reviewed_task_id"] == report["reviewed_task_id"]
    assert last["action"] == "review"
    assert last["verdict"] == "PASS"
    assert last["timestamp"]
    assert get_review_events(audit["reviewed_task_id"]) == events


def test_final_evidence_audit_target_task_terminal() -> None:
    report = task_result_auto_consumer_final_evidence_audit()
    assert report["target_task_id"] == RUNTIME_AUDIT_TASK_ID == "cf-62e0f30e0d02"
    assert report["target_task_terminal"] is True
    assert report["target_task_pending"] is False
    assert report["target_task_state"] in {"stuck", "timed_out", "failed"}
    assert report["target_task_state_reason"]
    assert report["target_task_terminal_evidence"]
    disposition = report["target_task_disposition"]
    assert disposition["permanently_pending_possible"] is False
    assert "cf-62e0f30e0d02" in report["markdown"]


def test_final_evidence_audit_discoverable_without_manual_query() -> None:
    report = task_result_auto_consumer_final_evidence_audit()
    assert report["auto_discovery_without_manual_query"] is True
    probe = report["discoverability"]
    assert probe["manual_get_task_result_calls"] == 0
    assert probe["auto_discovered_without_manual_query"] is True
    assert probe["pending_review"] is True
    assert probe["not_auto_reviewed"] is True
    assert report["probe_task_id"] in {
        item["task_id"] for item in list_pending_results()
    }


def test_final_evidence_audit_freeze_recommendation() -> None:
    report = task_result_auto_consumer_final_evidence_audit()
    assert report["FINAL_EVIDENCE_AUDIT"] == "PASS"
    assert report["can_freeze_mainline"] is True
    assert "FREEZE" in report["freeze_recommendation"]
    assert "FREEZE" in report["markdown"]


def test_final_evidence_audit_known_limitations_and_gaps() -> None:
    report = task_result_auto_consumer_final_evidence_audit()
    assert report["known_limitations"] == report["Known Limitations"]
    assert report["remaining_gaps"] == report["Remaining Gaps"]
    assert isinstance(report["Known Limitations"], list)
    assert report["Known Limitations"]
    assert isinstance(report["Remaining Gaps"], list)
    assert report["Remaining Gaps"]


def test_final_evidence_audit_contracts_unchanged() -> None:
    report = task_result_auto_consumer_final_evidence_audit()
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["get_task_result_contract"] == "UNCHANGED"
    assert report["Compatibility"]["submit_task"] == "UNCHANGED"
    assert report["Compatibility"]["get_task_result"] == "UNCHANGED"
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    assert list(inspect.signature(submit_task).parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    assert list(inspect.signature(get_task_result).parameters) == ["task_id"]


def test_final_evidence_audit_checks_and_markdown() -> None:
    report = task_result_auto_consumer_final_evidence_audit()
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in VALID_STATUSES
        assert check["detail"]
    assert all(check["status"] != "FAIL" for check in report["checks"])
    markdown = report["markdown"]
    for token in (
        "## Consumer idempotency / recovery / duplicate-missed protection",
        "## review_event / mark_reviewed audit evidence",
        "## Checks",
        "## Freeze recommendation",
        "## Known Limitations",
        "## Compatibility",
        "## Remaining Gaps",
    ):
        assert token in markdown


def test_freeze_decision_report_shape() -> None:
    report = task_result_auto_consumer_freeze_decision_report()
    assert report["report"] == FREEZE_DECISION_REPORT
    assert report["goal"] == FREEZE_DECISION_GOAL
    assert report["task_id"] == FREEZE_DECISION_TASK_ID == "cf-a91f8e558e59"
    assert report["FREEZE_DECISION"] in FREEZE_DECISIONS
    assert report["FREEZE_DECISION"] == report["freeze_decision"]
    assert report["Tests"] == "python -m pytest -q"
    assert set(report) >= {
        "report",
        "goal",
        "task_id",
        "FREEZE_DECISION",
        "STATUS",
        "can_freeze_daily_use",
        "source_audit",
        "verified_capabilities",
        "capability_summary",
        "Known Limitations",
        "known_limitations",
        "Remaining Gaps",
        "remaining_gaps",
        "must_fix_items",
        "blocking_issues",
        "deferrable_items",
        "non_blocking_issues",
        "blocking_daily_use",
        "non_blocking_daily_use",
        "recommended_freeze_scope",
        "human_review_gate",
        "auto_pass",
        "auto_trigger_next",
        "target_task_id",
        "target_task_blocking",
        "target_task_rationale",
        "permanent_pending_blocking",
        "permanent_pending_rationale",
        "submit_task_contract",
        "get_task_result_contract",
        "Compatibility",
        "checks",
        "markdown",
    }
    assert report["source_audit"]["status"] == "PASS"
    assert report["source_audit"]["can_freeze_mainline"] is True


def test_freeze_decision_is_freeze() -> None:
    report = task_result_auto_consumer_freeze_decision_report()
    assert report["FREEZE_DECISION"] == "FREEZE"
    assert report["can_freeze_daily_use"] is True
    assert report["must_fix_items"] == []
    assert report["blocking_issues"] == []
    assert report["blocking_daily_use"] == []


def test_freeze_decision_lists_verified_capabilities_and_evidence() -> None:
    report = task_result_auto_consumer_freeze_decision_report()
    capabilities = report["verified_capabilities"]
    assert capabilities
    names = {item["capability"] for item in capabilities}
    assert set(hello_module.FREEZE_DECISIONS) == {"FREEZE", "DO_NOT_FREEZE", "BLOCKED"}
    assert {
        "auto_discovery_without_manual_query",
        "no_missed_or_duplicate_consumption",
        "repeated_and_restart_scan_idempotent",
        "durable_queryable_consumption_evidence",
        "human_review_gate_only_close_action",
        "long_pending_task_terminal_disposition",
        "submit_task_get_task_result_contracts_unchanged",
    } <= names
    for item in capabilities:
        assert set(item) >= {"capability", "status", "evidence"}
        assert item["status"] in VALID_STATUSES
        assert item["evidence"]
    assert report["capability_summary"]
    assert all(
        item["status"] != "FAIL" for item in report["verified_capabilities"]
    )


def test_freeze_decision_known_limitations_and_remaining_gaps() -> None:
    report = task_result_auto_consumer_freeze_decision_report()
    assert isinstance(report["Known Limitations"], list)
    assert report["Known Limitations"]
    assert isinstance(report["Remaining Gaps"], list)
    assert report["Remaining Gaps"]
    assert report["known_limitations"] == report["Known Limitations"]
    assert report["remaining_gaps"] == report["Remaining Gaps"]
    assert report["deferrable_items"] == report["non_blocking_issues"]
    assert len(report["deferrable_items"]) == len(
        report["Known Limitations"]
    ) + len(report["Remaining Gaps"])
    assert report["non_blocking_daily_use"]
    assert report["recommended_freeze_scope"]


def test_freeze_decision_human_review_gate_and_contracts() -> None:
    report = task_result_auto_consumer_freeze_decision_report()
    assert report["human_review_gate"] is True
    assert report["human_review_gate_effective"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["get_task_result_contract"] == "UNCHANGED"
    assert report["Compatibility"]["submit_task"] == "UNCHANGED"
    assert report["Compatibility"]["get_task_result"] == "UNCHANGED"
    assert list(inspect.signature(submit_task).parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    assert list(inspect.signature(get_task_result).parameters) == ["task_id"]


def test_freeze_decision_target_task_and_permanent_pending_rationale() -> None:
    report = task_result_auto_consumer_freeze_decision_report()
    assert report["target_task_id"] == RUNTIME_AUDIT_TASK_ID == "cf-62e0f30e0d02"
    assert report["target_task_blocking"] is False
    assert report["target_task_rationale"]
    assert "NON-BLOCKING" in report["target_task_rationale"]
    assert report["permanent_pending_disposition"] is True
    assert report["permanent_pending_blocking"] is False
    assert report["permanent_pending_rationale"]
    assert "NON-BLOCKING" in report["permanent_pending_rationale"]
    assert any(
        "cf-62e0f30e0d02" in item for item in report["non_blocking_daily_use"]
    )


def test_freeze_decision_checks_and_markdown() -> None:
    report = task_result_auto_consumer_freeze_decision_report()
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in VALID_STATUSES
        assert check["detail"]
    assert all(check["status"] != "FAIL" for check in report["checks"])
    markdown = report["markdown"]
    assert markdown.startswith(f"# {FREEZE_DECISION_REPORT}")
    assert f"- task_id: {FREEZE_DECISION_TASK_ID}" in markdown
    assert f"FREEZE_DECISION: {report['FREEZE_DECISION']}" in markdown
    for token in (
        "## Verified capabilities and evidence",
        "## Must-fix / blocking items",
        "## Deferrable / non-blocking items",
        "## Known Limitations",
        "## Remaining Gaps",
        "## Blocking vs non-blocking for daily use",
        "## Recommended freeze scope",
        "## Human review gate",
        "## Checks",
        "## Compatibility",
    ):
        assert token in markdown


def test_exposure_audit_detail_export_shape() -> None:
    report = personal_ai_execution_result_exposure_audit_detail_export()
    assert report["report"] == "EXECUTION_RESULT_EXPOSURE_AUDIT_DETAIL_EXPORT"
    assert report["goal"] == EXPOSURE_AUDIT_DETAIL_EXPORT_GOAL
    assert report["task_id"] == EXPOSURE_AUDIT_DETAIL_EXPORT_TASK_ID == "cf-5f36864952d6"
    assert report["previous_task_id"] == EXPOSURE_REGRESSION_AUDIT_TASK_ID
    assert report["previous_task_id"] == "cf-331c3ad2d35c"
    assert set(report) >= {
        "report",
        "goal",
        "task_id",
        "previous_task_id",
        "summary",
        "execution_summary",
        "regression_audit_verdict",
        "field_clipping_layer",
        "current_worker_version",
        "root_cause",
        "minimal_fix",
        "local_action_required",
        "artifact_available",
        "blocked",
        "reason",
    }
    assert isinstance(report["summary"], str) and report["summary"]
    assert isinstance(report["execution_summary"], dict)
    assert report["execution_summary"]["summary"] == report["summary"]
    assert report["execution_summary"]["task_id"] == report["task_id"]


def test_exposure_audit_detail_export_summary_self_contained() -> None:
    report = personal_ai_execution_result_exposure_audit_detail_export()
    summary = report["summary"]
    assert summary != EXPOSURE_AUDIT_DETAIL_EXPORT_GOAL
    assert report["goal"] in summary
    for token in (
        "REGRESSION_AUDIT",
        "WORKER",
        "MCP_TRANSPORT",
        "CONNECTOR_SCHEMA",
        "CHATGPT_ENTRY",
        "UNKNOWN",
        "CURRENT_WORKER_VERSION",
        "ROOT_CAUSE",
        "MINIMAL_FIX",
        "LOCAL_ACTION_REQUIRED",
    ):
        assert token in summary
    assert f"LOCAL_ACTION_REQUIRED={'true' if report['local_action_required'] else 'false'}" in summary
    assert report["regression_audit_verdict"] in {
        "BLOCKED",
        "PASS",
        "FAIL",
        "UNKNOWN",
    }
    assert report["regression_audit_verdict"] in summary


def test_exposure_audit_detail_export_blocked_when_artifact_unreadable() -> None:
    report = personal_ai_execution_result_exposure_audit_detail_export()
    assert report["artifact_available"] is False
    assert report["blocked"] is True
    assert report["regression_audit_verdict"] == "BLOCKED"
    assert report["field_clipping_layer"] == "UNKNOWN"
    assert report["current_worker_version"] == "UNKNOWN"
    assert report["local_action_required"] is True
    assert report["reason"]
    assert "BLOCKED" in report["summary"]
    assert "reason=" in report["summary"]
    assert report["root_cause"] and report["minimal_fix"]


def test_exposure_audit_detail_export_requires_no_fabrication() -> None:
    report = personal_ai_execution_result_exposure_audit_detail_export()
    for key in (
        "regression_audit_verdict",
        "field_clipping_layer",
        "current_worker_version",
        "root_cause",
        "minimal_fix",
    ):
        assert isinstance(report[key], str) and report[key]
    assert report["field_clipping_layer"] in EXPOSURE_AUDIT_FIELD_CLIPPING_LAYERS
    assert set(report["field_clipping_layer_candidates"]) == set(
        EXPOSURE_AUDIT_FIELD_CLIPPING_LAYERS
    )
    assert report["workflow_modified"] is False


def test_exposure_audit_detail_export_reads_supplied_artifact() -> None:
    artifact = {
        "task_id": EXPOSURE_REGRESSION_AUDIT_TASK_ID,
        "REGRESSION_AUDIT": "PASS",
        "field_clipping_layer": "MCP_TRANSPORT",
        "CURRENT_WORKER_VERSION": "v42",
        "ROOT_CAUSE": "connector schema clipped detail fields",
        "MINIMAL_FIX": "surface the audit summary through the existing field",
        "LOCAL_ACTION_REQUIRED": "false",
    }
    report = personal_ai_execution_result_exposure_audit_detail_export(artifact)
    assert report["artifact_available"] is True
    assert report["blocked"] is False
    assert report["regression_audit_verdict"] == "PASS"
    assert report["field_clipping_layer"] == "MCP_TRANSPORT"
    assert report["current_worker_version"] == "v42"
    assert report["root_cause"] == "connector schema clipped detail fields"
    assert report["minimal_fix"] == "surface the audit summary through the existing field"
    assert report["local_action_required"] is False
    assert "MCP_TRANSPORT" in report["summary"]
    assert "LOCAL_ACTION_REQUIRED=false" in report["summary"]
    assert "status=EXPORTED" in report["summary"]


def test_exposure_audit_detail_export_unknown_layer_falls_back() -> None:
    artifact = {
        "task_id": EXPOSURE_REGRESSION_AUDIT_TASK_ID,
        "verdict": "FAIL",
        "layer": "SOME_UNKNOWN_LAYER",
    }
    report = personal_ai_execution_result_exposure_audit_detail_export(artifact)
    assert report["blocked"] is False
    assert report["field_clipping_layer"] == "UNKNOWN"
    assert report["current_worker_version"] == "UNKNOWN"
    assert report["local_action_required"] is True


def test_exposure_audit_detail_export_contracts_unchanged() -> None:
    report = personal_ai_execution_result_exposure_audit_detail_export()
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["get_task_result_contract"] == "UNCHANGED"
    assert list(inspect.signature(submit_task).parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    assert list(inspect.signature(get_task_result).parameters) == ["task_id"]
    assert set(get_task_result(EXPOSURE_AUDIT_DETAIL_EXPORT_TASK_ID)) == {
        "execution_summary",
        "commit",
        "tests",
        "artifacts",
        "execution_result_json",
        "evidence",
    }
