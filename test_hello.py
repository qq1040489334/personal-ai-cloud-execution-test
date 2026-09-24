"""Automated test for hello.py."""

import inspect
import json
from datetime import datetime

import pytest

from hello import (
    CLOUDFLARE_AUDIT_GOAL,
    CLOUDFLARE_AUDIT_TASK_ID,
    CLOUDFLARE_AUDIT_TOKENS,
    CLOUDFLARE_WORKER_NAME,
    DEPLOY_VERIFY_COMMIT,
    DEPLOY_VERIFY_TASK_ID,
    REQUIRED_RESULT_FIELDS,
    REVIEW_VERDICTS,
    RUNTIME_AUDIT_GOAL,
    RUNTIME_AUDIT_TASK_ID,
    RUNTIME_CANDIDATE_COMMITS,
    RUNTIME_PROVENANCE_GOAL,
    RUNTIME_PROVENANCE_TASK_ID,
    TASK_REVIEW_GOAL,
    cloud_agent_test,
    cloud_agent_test_2,
    cloud_asset_status,
    cloudflare_mcp_test,
    cloudflare_runtime_audit_report,
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
    personal_ai_task_runtime_audit,
    result_consumer_test,
    result_consumer_test2,
    runtime_provenance_report,
    security_test,
    submit_task,
    task_review_action_report,
    trigger_bridge_test,
)

VALID_STATUSES = {"PASS", "FAIL", "BLOCKED"}


def test_hello() -> None:
    assert hello() == "hello from cloud execution golden test"


def test_goodbye() -> None:
    assert goodbye() == "goodbye from cloud execution golden test"


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
