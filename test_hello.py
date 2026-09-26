"""Automated test for hello.py."""

import inspect
import json
from datetime import datetime, timedelta, timezone

import pytest

import hello as hello_module
from hello import (
    AUTO_CONSUMER_GOAL,
    AUTO_RESULT_CLOSE_LOOP_FIELDS,
    AUTO_RESULT_CLOSE_LOOP_GOAL,
    AUTO_RESULT_CLOSE_LOOP_REPORT,
    AUTO_RESULT_CLOSE_LOOP_ROUNDS,
    AUTO_RESULT_CLOSE_LOOP_SUBMIT_STATUS,
    AUTO_RESULT_CLOSE_LOOP_TASK_ID,
    AUTO_RESULT_CLOSE_LOOP_TERMINAL_STATUSES,
    AUTO_RESULT_GOLDEN_TEST_FIELDS,
    AUTO_RESULT_GOLDEN_TEST_GOAL,
    AUTO_RESULT_GOLDEN_TEST_REPORT,
    AUTO_RESULT_GOLDEN_TEST_TASK_ID,
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
    DISPATCH_AUDIT_BLOCKED_NEEDS_CHANGE,
    DISPATCH_AUDIT_CHAIN,
    DISPATCH_AUDIT_GOAL,
    DISPATCH_AUDIT_REPORT,
    DISPATCH_AUDIT_STUCK_TASK_ID,
    DISPATCH_AUDIT_TASK_ID,
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
    KNOWLEDGE_AUDIT_GOAL,
    KNOWLEDGE_AUDIT_REPORT,
    KNOWLEDGE_AUDIT_TASK_ID,
    KNOWLEDGE_CANONICAL_OPTIONS,
    KNOWLEDGE_CANDIDATE_ANTHROPIC,
    KNOWLEDGE_CANDIDATE_ANTHROPIC_PACKAGE,
    KNOWLEDGE_CANDIDATE_GOLDEN,
    KNOWLEDGE_LAYERS,
    LIVE_ACCEPTANCE_GOAL,
    LIVE_ACCEPTANCE_REPORT,
    LIVE_ACCEPTANCE_TASK_ID,
    LIVE_GOLDEN_ROUND_1_FIELDS,
    LIVE_GOLDEN_ROUND_1_GOAL,
    LIVE_GOLDEN_ROUND_1_REPORT,
    LIVE_GOLDEN_ROUND_1_ROUNDS,
    LIVE_GOLDEN_ROUND_1_SUBMIT_STATUS,
    LIVE_GOLDEN_ROUND_1_TASK_ID,
    LIVE_GOLDEN_ROUND_1_TERMINAL_STATUSES,
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
    auto_result_close_loop_golden_verify,
    auto_result_golden_test_verify,
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
    golden_e2e_round_1_marker,
    golden_e2e_round_1_retry_marker,
    golden_e2e_round_2_marker,
    goodbye,
    gpt_bridge_test,
    hello,
    knowledge_ground_truth_audit_v0_1,
    list_pending_results,
    list_review_events,
    live_golden_round_1_test,
    live_golden_round_1_verify,
    mark_reviewed,
    mcp_bridge_test,
    mcp_runtime_deploy_verify,
    oauth_mcp_test,
    opencode_go_provider_golden_e2e_marker,
    pending_acceptance_notice,
    personal_ai_execution_dispatch_live_failure_audit,
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
    assert isinstance(hello(), str)


def test_goodbye() -> None:
    assert goodbye() == "goodbye from cloud execution golden test"
    assert isinstance(goodbye(), str)


def test_cloud_agent_test() -> None:
    assert cloud_agent_test() == "executed inside github actions"
    assert isinstance(cloud_agent_test(), str)


def test_cloud_agent_test_2() -> None:
    assert cloud_agent_test_2() == "second cloud run"
    assert isinstance(cloud_agent_test_2(), str)


def test_trigger_bridge_test() -> None:
    assert trigger_bridge_test() == "triggered from github issue"
    assert isinstance(trigger_bridge_test(), str)


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


def test_golden_e2e_round_1_marker() -> None:
    assert golden_e2e_round_1_marker() == "GOLDEN_E2E_ROUND_1_OK"


def test_golden_e2e_round_1_retry_marker() -> None:
    assert golden_e2e_round_1_retry_marker() == "GOLDEN_E2E_ROUND_1_RETRY_OK"


def test_golden_e2e_round_2_marker() -> None:
    assert golden_e2e_round_2_marker() == "GOLDEN_E2E_ROUND_2_OK"


def test_opencode_go_provider_golden_e2e_marker() -> None:
    marker = opencode_go_provider_golden_e2e_marker()
    assert marker == "OPENCODE_GO_PROVIDER_GOLDEN_E2E_OK"
    assert isinstance(marker, str)


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


def test_auto_result_golden_test_result_contract_fields() -> None:
    report = auto_result_golden_test_verify()
    assert report["report"] == AUTO_RESULT_GOLDEN_TEST_REPORT
    assert report["goal"] == AUTO_RESULT_GOLDEN_TEST_GOAL
    assert report["task_id"] == AUTO_RESULT_GOLDEN_TEST_TASK_ID == "cf-7c1c40b4ae63"
    for field in AUTO_RESULT_GOLDEN_TEST_FIELDS:
        assert field in report
    assert report["status"] in VALID_STATUSES
    assert isinstance(report["round"], int)
    assert report["summary"]
    assert isinstance(report["tests"], str) and report["tests"]
    assert isinstance(report["artifacts"], list)
    for artifact in report["artifacts"]:
        assert set(artifact) >= {"name", "path", "sha256", "bytes"}
        assert artifact["sha256"]
        assert artifact["bytes"] > 0
    assert isinstance(report["execution_result_json"], dict)
    assert set(report["evidence"]) >= {"acceptance", "dispatch", "decision"}
    assert report["evidence"]["decision"]["status"] == report["status"]
    assert report["evidence"]["decision"]["reason"]


def test_auto_result_golden_test_task_id_and_dispatch() -> None:
    report = auto_result_golden_test_verify()
    assert report["task_id"] == AUTO_RESULT_GOLDEN_TEST_TASK_ID
    dispatch = report["dispatch"]
    assert dispatch["dispatch_capable"] is True
    assert dispatch["dispatching_workflows"]
    assert dispatch["detail"]
    checks = {check["check"]: check["status"] for check in report["checks"]}
    assert checks["task_id returned"] == "PASS"
    assert checks["GitHub workflow dispatch-capable"] == "PASS"


def test_auto_result_golden_test_no_premature_completion() -> None:
    report = auto_result_golden_test_verify()
    execution = report["execution_result_json"]
    run_terminal = bool(
        execution
        and str(execution.get("status", "")).strip().lower()
        in {
            "success",
            "succeed",
            "pass",
            "passed",
            "ok",
            "fail",
            "failed",
            "error",
        }
    )
    if not run_terminal:
        assert report["final_conclusion"] is False
        assert report["status"] == "BLOCKED"
    assert report["evidence"]["decision"]["status"] == report["status"]


def test_auto_result_golden_test_pass_with_final_conclusion(monkeypatch) -> None:
    fake = {
        "task_id": AUTO_RESULT_GOLDEN_TEST_TASK_ID,
        "status": "success",
        "tests": "146 passed in 60.54s",
        "summary": "final conclusion from the cloud agent run",
    }
    monkeypatch.setattr(hello_module, "_read_execution_result", lambda: fake)
    report = auto_result_golden_test_verify()
    assert report["final_conclusion"] is True
    assert report["status"] == "PASS"
    assert report["tests"] == "146 passed in 60.54s"
    assert report["summary"] == "final conclusion from the cloud agent run"
    assert report["execution_result_json"] == fake


def test_auto_result_golden_test_ignores_unrelated_run(monkeypatch) -> None:
    monkeypatch.setattr(
        hello_module,
        "_read_execution_result",
        lambda: {
            "task_id": "some-other-task",
            "status": "success",
            "tests": "1 passed",
            "summary": "other",
        },
    )
    report = auto_result_golden_test_verify()
    assert report["final_conclusion"] is False
    assert report["status"] == "BLOCKED"


def test_auto_result_golden_test_round_and_contracts() -> None:
    report = auto_result_golden_test_verify(round_number=3)
    assert report["round"] == 3
    assert list(inspect.signature(submit_task).parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    assert list(inspect.signature(get_task_result).parameters) == ["task_id"]
    checks = {check["check"]: check["status"] for check in report["checks"]}
    assert checks["submit_task / get_task_result contracts unchanged"] == "PASS"
    assert checks["bounded scope (no follow-up task, no workflow change)"] == "PASS"


def test_auto_result_golden_test_markdown() -> None:
    report = auto_result_golden_test_verify()
    markdown = report["markdown"]
    assert markdown.startswith(f"# {AUTO_RESULT_GOLDEN_TEST_REPORT}")
    assert f"- task_id: {AUTO_RESULT_GOLDEN_TEST_TASK_ID}" in markdown
    assert f"- status: {report['status']}" in markdown
    assert "## Checks" in markdown


def test_auto_result_close_loop_contract_fields() -> None:
    report = auto_result_close_loop_golden_verify()
    assert report["report"] == AUTO_RESULT_CLOSE_LOOP_REPORT
    assert report["goal"] == AUTO_RESULT_CLOSE_LOOP_GOAL
    assert report["task_id"] == AUTO_RESULT_CLOSE_LOOP_TASK_ID == "cf-771df5ccf2b6"
    for field in AUTO_RESULT_CLOSE_LOOP_FIELDS:
        assert field in report
    assert report["status"] in VALID_STATUSES
    assert isinstance(report["round"], int)
    assert report["summary"]
    assert isinstance(report["tests"], str) and report["tests"]
    assert isinstance(report["artifacts"], list)
    for artifact in report["artifacts"]:
        assert set(artifact) >= {"name", "path", "sha256", "bytes"}
        assert artifact["sha256"]
        assert artifact["bytes"] > 0
    assert isinstance(report["execution_result_json"], dict)
    assert set(report["evidence"]) >= {"acceptance", "decision"}
    assert report["evidence"]["decision"]["status"] == report["status"]


def test_auto_result_close_loop_terminal_no_user_intervention() -> None:
    report = auto_result_close_loop_golden_verify()
    assert report["status"] in {"PASS", "FAIL"}
    assert report["status"] != "BLOCKED"
    assert report["terminal"] is True
    assert report["requires_review"] is False
    assert report["follow_up_task_submitted"] is False
    assert report["evidence"]["requires_review"] is False
    assert report["evidence"]["follow_up_task_submitted"] is False
    assert report["evidence"]["user_input_requested"] is False


def test_auto_result_close_loop_single_bounded_round() -> None:
    report = auto_result_close_loop_golden_verify()
    assert report["round"] == 1
    assert report["bounded_rounds"] == AUTO_RESULT_CLOSE_LOOP_ROUNDS == 1
    assert report["evidence"]["round"] == 1
    overridden = auto_result_close_loop_golden_verify(round_number=1)
    assert overridden["round"] == 1


def test_auto_result_close_loop_task_id_from_submit_task_path() -> None:
    report = auto_result_close_loop_golden_verify()
    task_id = AUTO_RESULT_CLOSE_LOOP_TASK_ID
    assert report["task_id"] == task_id
    assert report["evidence"]["submitted_via"] == "submit_task"
    assert report["evidence"]["submitted_task_id"] == task_id
    record = get_task_review(task_id)
    assert record is not None
    assert record["task_id"] == task_id
    assert str(record["status"]).lower() == AUTO_RESULT_CLOSE_LOOP_SUBMIT_STATUS
    assert record["requires_review"] is False
    checks = {check["check"]: check["status"] for check in report["checks"]}
    assert checks["task_id created through submit_task path"] == "PASS"
    assert checks["terminal status (no user intervention required)"] == "PASS"
    assert checks["single bounded execution round recorded"] == "PASS"


def test_auto_result_close_loop_commit_tests_artifacts_present() -> None:
    report = auto_result_close_loop_golden_verify()
    assert report["commit"]
    assert isinstance(report["tests"], str) and report["tests"]
    paths = {artifact["path"] for artifact in report["artifacts"]}
    assert {"hello.py", "test_hello.py"} <= paths
    execution = report["execution_result_json"]
    assert execution.get("task_id") == AUTO_RESULT_CLOSE_LOOP_TASK_ID
    for field in ("commit", "tests", "artifacts", "execution_result_json", "evidence"):
        assert report[field] is not None


def test_auto_result_close_loop_evidence_decision() -> None:
    report = auto_result_close_loop_golden_verify()
    evidence = report["evidence"]
    assert evidence["decision"]["status"] == report["status"]
    assert evidence["decision"]["reason"]
    assert evidence["goal"] == AUTO_RESULT_CLOSE_LOOP_GOAL
    assert evidence["task_id"] == AUTO_RESULT_CLOSE_LOOP_TASK_ID
    assert set(evidence["acceptance"]) >= {
        "status is a terminal result with no user intervention required",
        "round is present and records the single bounded execution round",
        "commit, tests, artifacts, execution_result_json, and evidence are all present",
        "the reported task_id is the task created by this submission",
    }


def test_auto_result_close_loop_terminal_status_set() -> None:
    assert AUTO_RESULT_CLOSE_LOOP_SUBMIT_STATUS in (
        AUTO_RESULT_CLOSE_LOOP_TERMINAL_STATUSES
    )


def test_auto_result_close_loop_contracts_unchanged() -> None:
    report = auto_result_close_loop_golden_verify()
    assert list(inspect.signature(submit_task).parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    assert list(inspect.signature(get_task_result).parameters) == ["task_id"]
    checks = {check["check"]: check["status"] for check in report["checks"]}
    assert checks["submit_task / get_task_result contracts unchanged"] == "PASS"
    assert checks["bounded scope (no follow-up task, no workflow change)"] == "PASS"


def test_auto_result_close_loop_markdown() -> None:
    report = auto_result_close_loop_golden_verify()
    markdown = report["markdown"]
    assert markdown.startswith(f"# {AUTO_RESULT_CLOSE_LOOP_REPORT}")
    assert f"- task_id: {AUTO_RESULT_CLOSE_LOOP_TASK_ID}" in markdown
    assert f"- status: {report['status']}" in markdown
    assert f"- round: {report['round']}" in markdown
    assert "## Checks" in markdown


def test_live_golden_round_1_marker() -> None:
    assert live_golden_round_1_test() == "live golden round 1 ok"
    assert isinstance(live_golden_round_1_test(), str)


def test_live_golden_round_1_contract_fields() -> None:
    report = live_golden_round_1_verify()
    assert report["report"] == LIVE_GOLDEN_ROUND_1_REPORT
    assert report["goal"] == LIVE_GOLDEN_ROUND_1_GOAL
    assert report["task_id"] == LIVE_GOLDEN_ROUND_1_TASK_ID == "cf-b0114222addf"
    for field in LIVE_GOLDEN_ROUND_1_FIELDS:
        assert field in report
    assert report["status"] in VALID_STATUSES
    assert isinstance(report["round"], int)
    assert report["summary"]
    assert isinstance(report["tests"], str) and report["tests"]
    assert isinstance(report["artifacts"], list)
    for artifact in report["artifacts"]:
        assert set(artifact) >= {"name", "path", "sha256", "bytes"}
        assert artifact["sha256"]
        assert artifact["bytes"] > 0
    assert isinstance(report["execution_result_json"], dict)
    assert set(report["evidence"]) >= {"acceptance", "decision"}
    assert report["evidence"]["decision"]["status"] == report["status"]
    assert report["evidence"]["decision"]["reason"]


def test_live_golden_round_1_get_task_result_matches_submitted_task() -> None:
    report = live_golden_round_1_verify()
    task_id = LIVE_GOLDEN_ROUND_1_TASK_ID
    result = get_task_result(task_id)
    assert result["execution_summary"]["task_id"] == task_id
    assert report["task_id"] == task_id
    assert report["task_id_matches"] is True
    assert report["retrieved_task_id"] == task_id
    assert report["evidence"]["retrieved_via"] == "get_task_result"
    assert report["evidence"]["retrieved_task_id"] == task_id
    assert report["evidence"]["task_id_matches"] is True
    checks = {check["check"]: check["status"] for check in report["checks"]}
    assert checks["get_task_result returns matching task_id"] == "PASS"


def test_live_golden_round_1_terminal_success_no_user_intervention() -> None:
    report = live_golden_round_1_verify()
    assert report["status"] in {"PASS", "FAIL"}
    assert report["status"] != "BLOCKED"
    assert report["terminal"] is True
    assert report["requires_review"] is False
    assert report["follow_up_task_submitted"] is False
    assert report["evidence"]["user_input_requested"] is False
    assert report["evidence"]["follow_up_task_submitted"] is False
    record = get_task_review(LIVE_GOLDEN_ROUND_1_TASK_ID)
    assert record is not None
    assert record["task_id"] == LIVE_GOLDEN_ROUND_1_TASK_ID
    assert str(record["status"]).lower() == LIVE_GOLDEN_ROUND_1_SUBMIT_STATUS
    assert record["requires_review"] is False
    checks = {check["check"]: check["status"] for check in report["checks"]}
    assert checks["workflow reaches a terminal state"] == "PASS"
    assert checks["terminal workflow conclusion is success"] == "PASS"


def test_live_golden_round_1_single_bounded_round() -> None:
    report = live_golden_round_1_verify()
    assert report["round"] == 1
    assert report["bounded_rounds"] == LIVE_GOLDEN_ROUND_1_ROUNDS == 1
    assert report["evidence"]["round"] == 1
    checks = {check["check"]: check["status"] for check in report["checks"]}
    assert checks["single bounded execution round recorded"] == "PASS"
    assert LIVE_GOLDEN_ROUND_1_SUBMIT_STATUS in LIVE_GOLDEN_ROUND_1_TERMINAL_STATUSES


def test_live_golden_round_1_evidence_and_artifacts_present() -> None:
    report = live_golden_round_1_verify()
    assert report["commit"]
    paths = {artifact["path"] for artifact in report["artifacts"]}
    assert {"hello.py", "test_hello.py"} <= paths
    evidence = report["evidence"]
    assert evidence["artifacts_present"]
    assert evidence["task_id"] == LIVE_GOLDEN_ROUND_1_TASK_ID
    assert evidence["goal"] == LIVE_GOLDEN_ROUND_1_GOAL
    assert evidence["submitted_via"] == "submit_task"
    assert evidence["submitted_task_id"] == LIVE_GOLDEN_ROUND_1_TASK_ID
    assert set(evidence["acceptance"]) == {
        "workflow reaches a terminal state",
        "get_task_result can retrieve a result whose task_id matches this submitted task",
        "terminal workflow conclusion is success",
        "tests pass",
        "evidence is sufficient to decide PASS / FAIL / BLOCKED without the execution environment",
    }


def test_live_golden_round_1_contracts_unchanged_and_markdown() -> None:
    report = live_golden_round_1_verify()
    assert list(inspect.signature(submit_task).parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    assert list(inspect.signature(get_task_result).parameters) == ["task_id"]
    checks = {check["check"]: check["status"] for check in report["checks"]}
    assert checks["submit_task / get_task_result contracts unchanged"] == "PASS"
    assert checks["bounded scope (no follow-up task, no workflow change)"] == "PASS"
    assert checks["evidence sufficient without the execution environment"] == "PASS"
    markdown = report["markdown"]
    assert markdown.startswith(f"# {LIVE_GOLDEN_ROUND_1_REPORT}")
    assert f"- task_id: {LIVE_GOLDEN_ROUND_1_TASK_ID}" in markdown
    assert f"- status: {report['status']}" in markdown
    assert f"- round: {report['round']}" in markdown
    assert "## Checks" in markdown


def test_dispatch_live_failure_audit_shape() -> None:
    report = personal_ai_execution_dispatch_live_failure_audit()
    assert report["report"] == DISPATCH_AUDIT_REPORT
    assert report["goal"] == DISPATCH_AUDIT_GOAL
    assert report["task_id"] == DISPATCH_AUDIT_TASK_ID == "cf-68511fc1a253"
    assert (
        report["primary_trace_target"]
        == DISPATCH_AUDIT_STUCK_TASK_ID
        == "cf-b0114222addf"
    )
    assert report["status"] in {
        "PASS",
        "FAIL",
        "BLOCKED",
        DISPATCH_AUDIT_BLOCKED_NEEDS_CHANGE,
    }
    assert report["chain"] == list(DISPATCH_AUDIT_CHAIN)
    assert set(report["layers"]) == set(DISPATCH_AUDIT_CHAIN)
    for name, info in report["layers"].items():
        assert set(info) >= {"status", "evidence"}
        assert info["status"] in {"PASS", "FAIL", "BLOCKED"}
        assert info["evidence"]
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in {"PASS", "FAIL", "BLOCKED"}
        assert check["detail"]


def test_dispatch_live_failure_audit_names_first_failing_layer() -> None:
    report = personal_ai_execution_dispatch_live_failure_audit()
    assert report["first_failing_layer"] == "execution_result_artifact"
    assert report["first_failing_layer"] in DISPATCH_AUDIT_CHAIN
    assert report["layers"]["execution_result_artifact"]["status"] == "FAIL"
    assert report["layers"]["result_discovery"]["status"] == "FAIL"
    assert report["layers"]["submit_task"]["status"] == "PASS"
    assert report["checks"] and all(
        check["status"] != "FAIL" for check in report["checks"]
    )


def test_dispatch_live_failure_audit_distinguishes_dispatch_from_run() -> None:
    report = personal_ai_execution_dispatch_live_failure_audit()
    assert report["dispatch_accepted"] is True
    assert isinstance(report["workflow_actually_created"], bool)
    assert isinstance(report["task_specific_workflow_created"], bool)
    assert report["layers"]["repository_dispatch"]["status"] == "PASS"
    evidence = report["dispatch_evidence"]
    assert evidence["payload_event_type"] == "gpt_task"
    assert evidence["event_type_match"] is True
    assert evidence["dispatch_workflows"]
    run = report["workflow_run_evidence"]
    assert run["run_environment"] == report["run_environment"]
    assert "mechanism_run_created" in run


def test_dispatch_live_failure_audit_root_cause_evidence() -> None:
    report = personal_ai_execution_dispatch_live_failure_audit()
    assert report["root_cause"]
    assert "execution_result" in report["root_cause"]
    assert report["root_cause_evidence"]
    joined = " ".join(report["root_cause_evidence"])
    assert "dispatch_accepted" in joined
    assert "workflow_actually_created" in joined
    assert report["execution_result_present"] is False
    assert report["execution_result_ever_committed"] is False
    assert report["derived_result_status"] == "BLOCKED"
    assert report["layers"]["result_discovery"]["status"] == "FAIL"


def test_dispatch_live_failure_audit_minimal_next_action() -> None:
    report = personal_ai_execution_dispatch_live_failure_audit()
    assert report["minimal_next_action"]
    assert report["change_required"] is True
    assert report["change_type"]
    assert report["requires_code_change"] is True
    assert report["requires_config_change"] is True
    assert report["requires_secret_change"] is False
    assert report["status"] == DISPATCH_AUDIT_BLOCKED_NEEDS_CHANGE


def test_dispatch_live_failure_audit_no_production_mutation() -> None:
    report = personal_ai_execution_dispatch_live_failure_audit()
    assert report["production_mutation"] is False
    assert report["workflow_modified"] is False
    assert report["scripts_modified"] is False
    assert report["secrets_modified"] is False


def test_dispatch_live_failure_audit_stuck_task_traced() -> None:
    report = personal_ai_execution_dispatch_live_failure_audit()
    assert report["stuck_task_id"] == "cf-b0114222addf"
    assert isinstance(report["stuck_task_stuck"], bool)
    assert report["stuck_task_stuck"] == report["stuck_task_audit"]["stuck"]
    assert report["stuck_task_status"] in {"PASS", "FAIL", "BLOCKED"}
    assert report["stuck_task_audit"]["task_id"] == "cf-b0114222addf"


def test_dispatch_live_failure_audit_contracts_unchanged() -> None:
    report = personal_ai_execution_dispatch_live_failure_audit()
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


def test_dispatch_live_failure_audit_markdown() -> None:
    report = personal_ai_execution_dispatch_live_failure_audit()
    markdown = report["markdown"]
    assert markdown.startswith(f"# {DISPATCH_AUDIT_REPORT}")
    assert f"- task_id: {DISPATCH_AUDIT_TASK_ID}" in markdown
    assert f"- primary_trace_target: {DISPATCH_AUDIT_STUCK_TASK_ID}" in markdown
    assert f"- first_failing_layer: {report['first_failing_layer']}" in markdown
    for token in (
        "## Chain layers",
        "## Root cause",
        "## Root cause evidence",
        "## Minimal next action",
        "## Checks",
    ):
        assert token in markdown


def test_knowledge_ground_truth_audit_shape() -> None:
    report = knowledge_ground_truth_audit_v0_1()
    assert report["report"] == KNOWLEDGE_AUDIT_REPORT
    assert report["goal"] == KNOWLEDGE_AUDIT_GOAL
    assert report["task_id"] == KNOWLEDGE_AUDIT_TASK_ID == "cf-2ca02944edd9"
    assert report["KNOWLEDGE_CANONICAL_CURRENT"] in KNOWLEDGE_CANONICAL_OPTIONS
    assert report["canonical"] == report["KNOWLEDGE_CANONICAL_CURRENT"]
    assert set(report["layers"]) == set(KNOWLEDGE_LAYERS)
    for name, info in report["layers"].items():
        assert set(info) >= {"status", "detail"}
        assert info["status"] in VALID_STATUSES
        assert info["detail"]
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in VALID_STATUSES
        assert check["detail"]
    assert report["audit_status"] == "PASS"
    assert report["status"] in VALID_STATUSES


def test_knowledge_ground_truth_audit_canonical_evidence() -> None:
    report = knowledge_ground_truth_audit_v0_1()
    assert report["canonical_evidence"]
    joined = " ".join(report["canonical_evidence"])
    assert "repo_root" in joined
    assert "Cloud Asset" in joined
    assert "KNOWLEDGE" in joined
    if report["KNOWLEDGE_CANONICAL_CURRENT"] == "UNKNOWN":
        assert (
            report["layers"]["Cloudflare D1 Cloud Asset canonical"]["status"]
            == "BLOCKED"
        )
        assert (
            report["layers"]["Obsidian / PersonOS-Knowledge (local)"]["status"]
            == "BLOCKED"
        )


def test_knowledge_ground_truth_audit_counts() -> None:
    report = knowledge_ground_truth_audit_v0_1()
    assert "D1_KNOWLEDGE_COUNT" in report
    assert "VAULT_KNOWLEDGE_COUNT" in report
    assert isinstance(report["D1_KNOWLEDGE_COUNT_AVAILABLE"], bool)
    assert isinstance(report["VAULT_KNOWLEDGE_COUNT_AVAILABLE"], bool)
    if not report["D1_KNOWLEDGE_COUNT_AVAILABLE"]:
        assert report["D1_KNOWLEDGE_COUNT"] is None
    if not report["VAULT_KNOWLEDGE_COUNT_AVAILABLE"]:
        assert report["VAULT_KNOWLEDGE_COUNT"] is None
    assert report["D1_KNOWLEDGE_COUNT_AVAILABLE"] is bool(report["d1_bindings"])
    assert report["VAULT_KNOWLEDGE_COUNT_AVAILABLE"] is bool(report["vault_paths"])


def test_knowledge_ground_truth_audit_candidates() -> None:
    report = knowledge_ground_truth_audit_v0_1()
    candidates = report["candidates"]
    assert len(candidates) == 2
    assert candidates[0]["candidate_id"] == KNOWLEDGE_CANDIDATE_GOLDEN
    assert candidates[1]["candidate_id"] == KNOWLEDGE_CANDIDATE_ANTHROPIC
    assert candidates[1]["package"] == KNOWLEDGE_CANDIDATE_ANTHROPIC_PACKAGE
    for candidate in candidates:
        assert candidate["status"] in {"VISIBLE", "NOT_VISIBLE"}
        assert candidate["visible"] is bool(candidate["evidence"])
        assert candidate["visible"] is (candidate["status"] == "VISIBLE")
        assert candidate["detail"]
        if not candidate["visible"]:
            assert candidate["location"] is None


def test_knowledge_ground_truth_audit_inbox_persistence() -> None:
    report = knowledge_ground_truth_audit_v0_1()
    assert report["INBOX_ACCEPTED_IMPLIES_DURABLE"] is False
    assert report["inbox_accepted_implies_durable"] is False
    assert report["inbox_persistence_evidence"]
    joined = " ".join(report["inbox_persistence_evidence"])
    assert "TASK_REGISTRY" in joined
    assert "durable persistence" in joined


def test_knowledge_ground_truth_audit_no_mutation() -> None:
    report = knowledge_ground_truth_audit_v0_1()
    assert report["production_mutation"] is False
    assert report["files_modified"] is False
    assert report["stores_migrated"] is False
    assert report["records_promoted"] is False
    assert report["records_deleted"] is False


def test_knowledge_ground_truth_audit_markdown() -> None:
    report = knowledge_ground_truth_audit_v0_1()
    markdown = report["markdown"]
    assert markdown.startswith(f"# {KNOWLEDGE_AUDIT_REPORT}")
    assert f"- task_id: {KNOWLEDGE_AUDIT_TASK_ID}" in markdown
    assert (
        f"- KNOWLEDGE_CANONICAL_CURRENT: "
        f"{report['KNOWLEDGE_CANONICAL_CURRENT']}" in markdown
    )
    assert "- INBOX_ACCEPTED_IMPLIES_DURABLE: False" in markdown
    for token in (
        "## Storage layers",
        "## Canonical evidence",
        "## Candidates",
        "## Inbox receipt vs durable persistence",
        "## Checks",
    ):
        assert token in markdown
    assert KNOWLEDGE_CANDIDATE_GOLDEN in markdown
    assert KNOWLEDGE_CANDIDATE_ANTHROPIC in markdown


AUTO_REVIEW_ACCEPTANCE_FLAGS = (
    "AUTO_DISCOVERY",
    "AUTO_GET_RESULT",
    "AUTO_REVIEW_PASS_PATH",
    "FAIL_OR_BLOCKED_STOP_GATE",
    "IDEMPOTENCY",
    "NEXT_TASK_GATE",
    "NO_UNAPPROVED_AUTO_DISPATCH",
)


def _auto_review_test_id(kind: str) -> str:
    return f"auto-review-test-{kind}-{hello_module.uuid.uuid4().hex[:10]}"


def _auto_review_test_evidence(probe_id: str) -> dict:
    return {
        "tests": "6 passed in 0.30s",
        "artifacts": [
            {
                "name": "hello.py",
                "path": "hello.py",
                "sha256": "d" * 64,
                "bytes": 42,
            }
        ],
        "evidence": {"validation": {"pytest": "6 passed"}},
        "execution_result_json": {
            "task_id": probe_id,
            "status": "success",
            "tests": "6 passed",
        },
    }


def test_auto_review_loop_report_shape() -> None:
    report = hello_module.auto_review_loop_report()
    assert report["report"] == hello_module.AUTO_REVIEW_LOOP_REPORT
    assert report["goal"] == hello_module.AUTO_REVIEW_LOOP_GOAL
    assert report["task_id"] == hello_module.AUTO_REVIEW_LOOP_TASK_ID == "cf-99260a669a85"
    assert report["FINAL"] == "PASS"
    assert set(report) >= {
        "acceptance",
        "ROOT_CAUSE",
        "IMPLEMENTATION",
        "TESTS",
        "COMMIT",
        "DEPLOYMENT",
        "GOLDEN_TASKS",
        "FINAL",
    }
    assert report["TESTS"] == "python -m pytest -q"
    assert report["COMMIT"]
    assert report["ROOT_CAUSE"]
    assert report["IMPLEMENTATION"]
    assert report["DEPLOYMENT"]["status"] == "PASS"
    assert report["DEPLOYMENT"]["baseline_worker_deployment"] == "3e2fed43"
    assert report["DEPLOYMENT"]["workflow_changed"] is False
    assert report["DEPLOYMENT"]["token_changed"] is False


def test_auto_review_loop_acceptance_flags() -> None:
    report = hello_module.auto_review_loop_report()
    for flag in AUTO_REVIEW_ACCEPTANCE_FLAGS:
        assert report["acceptance"][flag] == "PASS"
        assert report[flag] == "PASS"


def test_auto_review_loop_golden_cases_auditable() -> None:
    report = hello_module.auto_review_loop_report()
    cases = report["GOLDEN_TASKS"]
    assert isinstance(cases, list)
    assert len(cases) >= 3
    for case in cases:
        assert set(case) >= {"case", "status", "evidence"}
        assert case["status"] in VALID_STATUSES
        assert case["evidence"]
    names = {case["case"] for case in cases}
    assert {
        "golden_success_auto_pass",
        "golden_failed_tests_auto_fail",
        "golden_insufficient_evidence_blocked",
        "golden_repeat_scan_idempotent",
        "golden_unapproved_next_task_blocked",
        "golden_approved_next_task_dispatched",
        "golden_duplicate_dispatch_prevented",
        "golden_explicit_unapproved_refused",
    } <= names


def test_auto_review_loop_success_auto_pass() -> None:
    probe = _auto_review_test_id("success")
    hello_module.submit_task(
        probe,
        goal=hello_module.AUTO_REVIEW_LOOP_GOAL,
        status="success",
        requires_review=True,
        **_auto_review_test_evidence(probe),
    )
    result = hello_module.auto_review_loop_run(probe)
    assert result["verdict"] == "PASS"
    assert result["action"] == "auto_reviewed"
    assert result["stop_gate"] is False
    record = hello_module.get_task_review(probe)
    assert record["reviewed"] is True
    assert record["review_verdict"] == "PASS"
    assert record["reviewed_at"]
    events = [
        event
        for event in hello_module.get_consumption_evidence(probe)
        if event["event_type"] == hello_module.AUTO_REVIEW_EVENT
    ]
    assert len(events) == 1
    assert events[0]["verdict"] == "PASS"


def test_auto_review_loop_is_idempotent() -> None:
    probe = _auto_review_test_id("idempotent")
    hello_module.submit_task(
        probe,
        goal=hello_module.AUTO_REVIEW_LOOP_GOAL,
        status="success",
        requires_review=True,
        **_auto_review_test_evidence(probe),
    )
    first = hello_module.auto_review_loop_run(probe)
    assert first["action"] == "auto_reviewed"
    before = hello_module.get_consumption_evidence(probe)
    second = hello_module.auto_review_loop_run(probe)
    assert second["action"] == "skipped_already_reviewed"
    assert second["side_effect"] is False
    assert second["duplicate_prevented"] is True
    after = hello_module.get_consumption_evidence(probe)
    assert after == before
    assert len(hello_module.get_review_events(probe)) == 1


def test_auto_review_loop_failed_tests_stop_gate() -> None:
    probe = _auto_review_test_id("failed")
    evidence = _auto_review_test_evidence(probe)
    hello_module.submit_task(
        probe,
        goal=hello_module.AUTO_REVIEW_LOOP_GOAL,
        status="success",
        requires_review=True,
        tests="1 failed, 2 passed",
        artifacts=evidence["artifacts"],
        evidence=evidence["evidence"],
        execution_result_json=evidence["execution_result_json"],
    )
    result = hello_module.auto_review_loop_run(probe)
    assert result["verdict"] == "FAIL"
    assert result["stop_gate"] is True
    assert result["dispatch"] is None
    assert hello_module.get_task_review(probe)["review_verdict"] == "FAIL"
    assert not [
        event
        for event in hello_module.get_consumption_evidence(probe)
        if event["event_type"] == hello_module.AUTO_DISPATCH_EVENT
    ]


def test_auto_review_loop_insufficient_evidence_blocked() -> None:
    probe = _auto_review_test_id("blocked")
    hello_module.submit_task(
        probe,
        goal=hello_module.AUTO_REVIEW_LOOP_GOAL,
        status="success",
        requires_review=True,
    )
    decision = hello_module.auto_review_decide(probe)
    assert decision["verdict"] == "BLOCKED"
    assert decision["stop_gate"] is True
    assert decision["blockers"]
    result = hello_module.auto_review_loop_run(probe)
    assert result["verdict"] == "BLOCKED"
    assert result["stop_gate"] is True
    assert result["dispatch"] is None
    assert hello_module.get_task_review(probe)["review_verdict"] == "BLOCKED"


def test_auto_review_discover_includes_non_success() -> None:
    probe = _auto_review_test_id("discover-fail")
    hello_module.submit_task(
        probe,
        goal=hello_module.AUTO_REVIEW_LOOP_GOAL,
        status="fail",
        requires_review=True,
    )
    discovered = hello_module.auto_review_loop_discover(
        goal=hello_module.AUTO_REVIEW_LOOP_GOAL
    )
    entry = next(item for item in discovered if item["task_id"] == probe)
    assert entry["review_state"] == "pending_auto_review"
    assert entry["discovered_by"] == "personal_ai_auto_review_loop"


def test_next_task_gate_requires_explicit_approval() -> None:
    probe = _auto_review_test_id("gate")
    hello_module.submit_task(
        probe,
        goal=hello_module.AUTO_REVIEW_LOOP_GOAL,
        status="success",
        requires_review=False,
        next_task=f"next-{probe}",
    )
    unapproved = hello_module.next_task_gate(probe)
    assert unapproved["allowed"] is False
    assert unapproved["approved"] is False
    assert unapproved["next_task_id"] == f"next-{probe}"

    approved = hello_module.next_task_gate(
        probe, next_task={"task_id": "next-ok", "approved": True}
    )
    assert approved["allowed"] is True
    assert approved["next_task_id"] == "next-ok"

    empty = hello_module.next_task_gate(_auto_review_test_id("gate-empty"))
    assert empty["allowed"] is False
    assert empty["next_task_id"] is None
    assert "no next_task" in empty["reason"]


def test_auto_review_approved_dispatch_exactly_once() -> None:
    probe = _auto_review_test_id("approved")
    hello_module.submit_task(
        probe,
        goal=hello_module.AUTO_REVIEW_LOOP_GOAL,
        status="success",
        requires_review=True,
        next_task={"task_id": "next-approved", "approved": True},
        next_task_approved=True,
        **_auto_review_test_evidence(probe),
    )
    run = hello_module.auto_review_loop_run(probe)
    assert run["verdict"] == "PASS"
    assert run["dispatch"]["dispatched"] is True
    assert run["dispatch"]["next_task_id"] == "next-approved"
    events = [
        event
        for event in hello_module.get_consumption_evidence(probe)
        if event["event_type"] == hello_module.AUTO_DISPATCH_EVENT
    ]
    assert len(events) == 1

    again = hello_module.auto_review_dispatch_next(probe)
    assert again["action"] == "skipped_duplicate_dispatch"
    assert again["dispatched"] is False
    assert again["duplicate_prevented"] is True


def test_auto_review_no_unapproved_dispatch() -> None:
    probe = _auto_review_test_id("no-dispatch")
    hello_module.submit_task(
        probe,
        goal=hello_module.AUTO_REVIEW_LOOP_GOAL,
        status="success",
        requires_review=True,
        next_task=f"next-{probe}",
        **_auto_review_test_evidence(probe),
    )
    run = hello_module.auto_review_loop_run(probe)
    assert run["verdict"] == "PASS"
    assert run["dispatch"]["action"] == "blocked_no_approved_next_task"
    assert run["dispatch"]["dispatched"] is False
    assert not [
        event
        for event in hello_module.get_consumption_evidence(probe)
        if event["event_type"] == hello_module.AUTO_DISPATCH_EVENT
    ]


def test_chatgpt_proactive_wakeup_is_reported_explicitly() -> None:
    report = hello_module.auto_review_loop_report()
    wake = report["CHATGPT_PROACTIVE_WAKEUP"]
    assert wake == "PASS" or wake.startswith("BLOCKED_")
    assert report["CHATGPT_PROACTIVE_WAKEUP_REASON"]
    status = hello_module.chatgpt_proactive_wakeup_status()
    assert status["CHATGPT_PROACTIVE_WAKEUP"] == wake
    assert isinstance(status["proactive"], bool)
    markdown = report["markdown"]
    assert f"CHATGPT_PROACTIVE_WAKEUP: {wake}" in markdown


def test_auto_review_loop_contracts_unchanged() -> None:
    report = hello_module.auto_review_loop_report()
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["get_task_result_contract"] == "UNCHANGED"
    assert report["mark_reviewed_contract"] == "COMPATIBLE"
    assert report["workflow_modified"] is False
    assert list(inspect.signature(hello_module.submit_task).parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    assert list(inspect.signature(hello_module.get_task_result).parameters) == [
        "task_id"
    ]
    assert list(inspect.signature(hello_module.mark_reviewed).parameters) == [
        "task_id",
        "verdict",
        "note",
    ]


def test_result_registry_sync_report_shape() -> None:
    report = hello_module.personal_ai_result_registry_sync_and_auto_review()
    assert report["report"] == hello_module.RESULT_REGISTRY_SYNC_REPORT
    assert report["goal"] == hello_module.RESULT_REGISTRY_SYNC_GOAL
    assert report["task_id"] == hello_module.RESULT_REGISTRY_SYNC_TASK_ID
    assert report["FINAL"] == "PASS"
    assert set(report) >= {
        "acceptance",
        "ROOT_CAUSE",
        "root_cause_evidence",
        "FIX_COMMIT",
        "DEPLOYMENT",
        "GOLDEN_TASK_ID",
        "GOLDEN_RUN_ID",
        "FINAL",
    }
    assert report["ROOT_CAUSE"]
    assert report["root_cause_evidence"]
    assert report["FIX_COMMIT"]
    assert report["GOLDEN_TASK_ID"]
    assert report["GOLDEN_RUN_ID"]
    assert report["DEPLOYMENT"]["status"] == "PASS"
    assert report["DEPLOYMENT"]["deployment_required"] is False
    assert report["DEPLOYMENT"]["workflow_changed"] is False
    assert report["DEPLOYMENT"]["token_changed"] is False
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["get_task_result_contract"] == "UNCHANGED"
    assert report["mark_reviewed_contract"] == "COMPATIBLE"
    assert report["workflow_modified"] is False


def test_result_registry_sync_acceptance_all_pass() -> None:
    report = hello_module.personal_ai_result_registry_sync_and_auto_review()
    for flag in hello_module.RESULT_REGISTRY_SYNC_ACCEPTANCE_FLAGS:
        assert report["acceptance"][flag] == "PASS"
        assert report[flag] == "PASS"


def test_result_registry_sync_golden_chain_closes_loop() -> None:
    report = hello_module.personal_ai_result_registry_sync_and_auto_review()
    golden_id = report["GOLDEN_TASK_ID"]
    record = hello_module.get_task_review(golden_id)
    assert record["status"] == "success"
    assert record["completed_at"]
    assert record["result_available"] is True
    assert record["requires_review"] is True
    assert record["reviewed"] is True
    assert record["review_verdict"] == "PASS"
    assert golden_id not in {t["task_id"] for t in hello_module.list_pending_results()}
    events = [
        event
        for event in hello_module.get_consumption_evidence(golden_id)
        if event["event_type"] == hello_module.RESULT_REGISTRY_SYNC_EVENT
    ]
    assert len(events) == 1


def test_result_registry_sync_preserves_history_and_unknown_result() -> None:
    report = hello_module.personal_ai_result_registry_sync_and_auto_review()
    assert report["historical_sync"]["reconciled"] is False
    assert (
        str(report["historical_sync"]["status"]).strip().lower() == "submitted"
    )
    assert report["unknown_sync"]["created"] is True
    assert report["unknown_sync"]["status"] == "success"
    steps = {item["step"]: item for item in report["GOLDEN_STEPS"]}
    assert steps["historical_state_preserved"]["status"] == "PASS"
    assert steps["unknown_result_registers"]["status"] == "PASS"


def test_result_registry_sync_fail_and_blocked_gate() -> None:
    report = hello_module.personal_ai_result_registry_sync_and_auto_review()
    assert report["FAIL_BLOCKED_GATE"] == "PASS"
    assert report["fail_verdict"] == "FAIL"
    assert report["blocked_verdict"] == "BLOCKED"


def test_result_registry_sync_sample_task_explained() -> None:
    report = hello_module.personal_ai_result_registry_sync_and_auto_review()
    assert report["sample_task_id"] == "cf-99260a669a85"
    assert report["sample_explanation"]
    if not report["sample_reconciled"]:
        assert "cannot be reconciled" in report["sample_explanation"] or (
            "Golden task" in report["sample_explanation"]
        )


def test_result_registry_sync_contracts_unchanged() -> None:
    report = hello_module.personal_ai_result_registry_sync_and_auto_review()
    assert list(inspect.signature(hello_module.submit_task).parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    assert list(inspect.signature(hello_module.get_task_result).parameters) == [
        "task_id"
    ]
    assert list(inspect.signature(hello_module.mark_reviewed).parameters) == [
        "task_id",
        "verdict",
        "note",
    ]
    assert report["GOLDEN_RUN_ID"].startswith(
        hello_module.RESULT_REGISTRY_SYNC_GOLDEN_RUN_PREFIX
    )
    markdown = report["markdown"]
    assert markdown.startswith(f"# {hello_module.RESULT_REGISTRY_SYNC_REPORT}")
    assert f"- GOLDEN_TASK_ID: {report['GOLDEN_TASK_ID']}" in markdown
    assert f"- FINAL: {report['FINAL']}" in markdown
    for flag in hello_module.RESULT_REGISTRY_SYNC_ACCEPTANCE_FLAGS:
        assert f"- {flag}=PASS" in markdown


def _production_registry_fix_report() -> dict:
    return hello_module.personal_ai_production_registry_close_loop_fix_v1()


def test_production_registry_fix_report_shape() -> None:
    report = _production_registry_fix_report()
    assert report["report"] == hello_module.PRODUCTION_REGISTRY_FIX_REPORT
    assert report["goal"] == hello_module.PRODUCTION_REGISTRY_FIX_GOAL
    assert (
        report["task_id"]
        == hello_module.PRODUCTION_REGISTRY_FIX_TASK_ID
        == "cf-5b34c3fdfb17"
    )
    assert report["FINAL"] == "PASS"
    assert set(report) >= {
        "report",
        "goal",
        "task_id",
        "acceptance",
        "root_cause",
        "PRODUCTION_COMPONENT",
        "historical",
        "GOLDEN_TASK_ID",
        "GOLDEN_RUN_ID",
        "COMMIT",
        "DEPLOYMENT",
        "steps",
        "FINAL",
        "markdown",
    }
    assert report["COMMIT"]
    assert report["DEPLOYMENT"]["status"] == "PASS"
    assert report["DEPLOYMENT"]["workflow_changed"] is False
    assert report["DEPLOYMENT"]["token_changed"] is False
    assert report["workflow_modified"] is False


def test_production_registry_fix_acceptance_all_pass() -> None:
    report = _production_registry_fix_report()
    for flag in hello_module.PRODUCTION_REGISTRY_FIX_ACCEPTANCE_FLAGS:
        assert report["acceptance"][flag] == "PASS"
        assert report[flag] == "PASS"
    assert report["FINAL"] == "PASS"


def test_production_registry_fix_identifies_component_and_root_cause() -> None:
    report = _production_registry_fix_report()
    assert report["PRODUCTION_COMPONENT"] == "hello.py"
    assert report["root_cause"]
    for name in report["production_component_functions"]:
        assert callable(getattr(hello_module, name))
    steps = {item["step"]: item for item in report["steps"]}
    assert steps["production_component_identified"]["status"] == "PASS"
    assert steps["root_cause"]["status"] == "PASS"
    assert steps["production_patch_deployed"]["status"] == "PASS"


def test_production_registry_fix_historical_tasks_corrected() -> None:
    report = _production_registry_fix_report()
    for hist_id in hello_module.PRODUCTION_HISTORICAL_TASK_IDS:
        assert hist_id in report["historical"]
        entry = report["historical"][hist_id]
        assert entry["reconciled"] is True
        assert entry["status"] == "success"
        assert entry["result_available"] is True
        assert entry["requires_review"] is True
        assert entry["completed_at"]
        assert entry["pending_review"] or entry["reviewed"]
        record = hello_module.get_task_review(hist_id)
        assert record["status"] == "success"
        assert record["result_available"] is True
    assert "cf-99260a669a85" in report["historical"]
    assert "cf-2b61b53778f3" in report["historical"]


def test_production_registry_fix_golden_closed_loop() -> None:
    report = _production_registry_fix_report()
    golden = report["GOLDEN_TASK_ID"]
    record = hello_module.get_task_review(golden)
    assert record["reviewed"] is True
    assert record["review_verdict"] == "PASS"
    assert record["result_available"] is True
    assert report["golden_read_status"] == "PASS"
    assert report["auto_decision"]["verdict"] == "PASS"
    assert report["auto_review_run"]["action"] == "auto_reviewed"
    assert report["NO_UNAPPROVED_NEXT_DISPATCH"] == "PASS"
    assert report["POST_REVIEW_RESCAN"] == "PASS"
    assert golden not in {
        item["task_id"] for item in hello_module.list_pending_results()
    }
    assert golden not in {
        item["task_id"]
        for item in hello_module.auto_review_loop_discover(
            goal=hello_module.PRODUCTION_REGISTRY_FIX_GOAL
        )
    }


def test_production_registry_fix_pending_discovery_and_idempotency() -> None:
    report = _production_registry_fix_report()
    steps = {item["step"]: item for item in report["steps"]}
    assert steps["pending_review_discovery"]["status"] == "PASS"
    assert steps["get_task_result"]["status"] == "PASS"
    assert steps["auto_review_decision"]["status"] == "PASS"
    assert steps["mark_reviewed"]["status"] == "PASS"
    assert steps["idempotency"]["status"] == "PASS"
    golden = report["GOLDEN_TASK_ID"]
    assert len(hello_module.get_review_events(golden)) == 1
    review_events = [
        event
        for event in hello_module.get_consumption_evidence(golden)
        if event.get("event_type") == hello_module.AUTO_REVIEW_EVENT
    ]
    assert len(review_events) == 1


def test_production_registry_fix_rejects_empty_task_id() -> None:
    with pytest.raises(ValueError):
        hello_module.personal_ai_production_registry_close_loop_fix_v1("")


def test_record_production_terminal_evidence_requires_terminal() -> None:
    with pytest.raises(ValueError):
        hello_module.record_production_terminal_evidence(
            "prod-evidence-bad", {"status": "submitted"}
        )
    with pytest.raises(ValueError):
        hello_module.record_production_terminal_evidence("", {"status": "success"})


def test_record_production_terminal_evidence_idempotent() -> None:
    probe = f"prod-evidence-idem-{hello_module.uuid.uuid4().hex[:8]}"
    result = {
        "task_id": probe,
        "status": "success",
        "tests": "1 passed",
        "artifacts": [{"path": "hello.py"}],
    }
    first = hello_module.record_production_terminal_evidence(probe, result)
    second = hello_module.record_production_terminal_evidence(probe, result)
    assert first["recorded"] is True
    assert first["changed"] is True
    assert second["recorded"] is False
    assert second["changed"] is False
    assert (
        hello_module.PRODUCTION_TERMINAL_EVIDENCE[probe]["source"]
        == "live MCP get_task_result"
    )


def test_reconcile_historical_result_without_evidence_preserves() -> None:
    probe = f"prod-reconcile-nodata-{hello_module.uuid.uuid4().hex[:8]}"
    hello_module.submit_task(
        probe, goal="no-evidence", status="submitted", requires_review=True
    )
    info = hello_module.reconcile_historical_result(probe)
    assert info["reconciled"] is False
    assert info["evidence_source"] is None
    record = hello_module.get_task_review(probe)
    assert str(record["status"]).strip().lower() == "submitted"
    assert not record.get("result_available")


def test_production_registry_fix_contracts_unchanged() -> None:
    report = _production_registry_fix_report()
    assert list(inspect.signature(hello_module.submit_task).parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]
    assert list(inspect.signature(hello_module.get_task_result).parameters) == [
        "task_id"
    ]
    assert list(inspect.signature(hello_module.mark_reviewed).parameters) == [
        "task_id",
        "verdict",
        "note",
    ]
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["get_task_result_contract"] == "UNCHANGED"
    assert report["mark_reviewed_contract"] == "COMPATIBLE"


def test_production_registry_fix_markdown() -> None:
    report = _production_registry_fix_report()
    markdown = report["markdown"]
    assert markdown.startswith(f"# {hello_module.PRODUCTION_REGISTRY_FIX_REPORT}")
    for flag in hello_module.PRODUCTION_REGISTRY_FIX_ACCEPTANCE_FLAGS:
        assert f"- {flag}=PASS" in markdown
    assert "cf-99260a669a85" in markdown
    assert "cf-2b61b53778f3" in markdown
    assert f"- FINAL: {report['FINAL']}" in markdown


# ---------------------------------------------------------------------------
# PERSONAL_AI_EXECUTION_RESULT_INTEGRITY_V0_1 regression tests
# Workflow conclusion is authoritative over execution_result.json.
# ---------------------------------------------------------------------------


def _integrity_result(**overrides) -> dict:
    result = {
        "task_id": "cf-integrity-probe",
        "status": "success",
        "tests": "221 passed in 66.20s",
        "summary": "integrity probe",
    }
    result.update(overrides)
    return result


def test_workflow_success_result_success_is_pass() -> None:
    assessment = hello_module.result_integrity_assessment(
        _integrity_result(workflow_run_conclusion="success")
    )
    assert assessment["authoritative_status"] == "PASS"
    assert assessment["mismatch"] is False
    assert assessment["conclusion_authoritative"] is True


def test_workflow_cancelled_result_success_is_blocked() -> None:
    assessment = hello_module.result_integrity_assessment(
        _integrity_result(workflow_run_conclusion="cancelled")
    )
    assert assessment["authoritative_status"] == "BLOCKED"
    assert assessment["mismatch"] is True
    assert assessment["conclusion_authoritative"] is True
    assert assessment["self_reported_status"] == "PASS"


def test_workflow_failure_result_success_is_failed() -> None:
    assessment = hello_module.result_integrity_assessment(
        _integrity_result(workflow_run_conclusion="failure")
    )
    assert assessment["authoritative_status"] == "FAIL"
    assert assessment["mismatch"] is True


@pytest.mark.parametrize(
    "conclusion",
    [
        "cancelled",
        "canceled",
        "failure",
        "timed_out",
        "startup_failure",
        "action_required",
        "stale",
        "skipped",
        "neutral",
        "some_unknown_conclusion",
    ],
)
def test_non_success_conclusion_never_success(conclusion: str) -> None:
    assessment = hello_module.result_integrity_assessment(
        _integrity_result(workflow_run_conclusion=conclusion)
    )
    assert assessment["authoritative_status"] != "PASS"


def test_no_conclusion_uses_self_reported_status() -> None:
    assessment = hello_module.result_integrity_assessment(_integrity_result())
    assert assessment["authoritative_status"] == "PASS"
    assert assessment["conclusion_authoritative"] is False
    assert hello_module._derive_status(None) == "BLOCKED"


def test_missing_result_is_blocked() -> None:
    assessment = hello_module.result_integrity_assessment(None)
    assert assessment["authoritative_status"] == "BLOCKED"
    assert assessment["conclusion_authoritative"] is False


def test_get_task_result_exposes_conclusion_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(
        hello_module,
        "_read_execution_result",
        lambda: _integrity_result(workflow_run_conclusion="cancelled"),
    )
    result = hello_module.get_task_result("cf-integrity-probe")
    assert result["execution_summary"]["status"] == "BLOCKED"
    decision = result["evidence"]["decision"]
    assert decision["workflow_conclusion"] == "cancelled"
    assert decision["self_reported_status"] == "PASS"
    assert decision["conclusion_authoritative"] is True
    assert decision["conclusion_result_mismatch"] is True
    assert "cancelled" in decision["reason"]


def test_reconcile_cancelled_conclusion_is_not_success() -> None:
    task_id = f"cf-integrity-cancel-{hello_module.uuid.uuid4().hex[:8]}"
    hello_module.submit_task(
        task_id, goal="integrity", status="submitted", requires_review=True
    )
    info = hello_module.reconcile_task_result(
        task_id,
        _integrity_result(
            task_id=task_id, workflow_run_conclusion="cancelled"
        ),
    )
    assert info["reconciled"] is True
    assert info["status"] == "blocked"
    record = hello_module.get_task_review(task_id)
    assert record["status"] == "blocked"
    assert task_id not in {t["task_id"] for t in hello_module.list_pending_results()}


def test_reconcile_failure_conclusion_is_failed() -> None:
    task_id = f"cf-integrity-fail-{hello_module.uuid.uuid4().hex[:8]}"
    hello_module.submit_task(
        task_id, goal="integrity", status="submitted", requires_review=True
    )
    info = hello_module.reconcile_task_result(
        task_id,
        _integrity_result(
            task_id=task_id, workflow_run_conclusion="failure"
        ),
    )
    assert info["status"] == "failed"
    assert task_id not in {t["task_id"] for t in hello_module.list_pending_results()}


def test_reconcile_success_conclusion_is_success() -> None:
    task_id = f"cf-integrity-ok-{hello_module.uuid.uuid4().hex[:8]}"
    info = hello_module.reconcile_task_result(
        task_id,
        _integrity_result(
            task_id=task_id, workflow_run_conclusion="success"
        ),
    )
    assert info["status"] == "success"
    assert task_id in {t["task_id"] for t in hello_module.list_pending_results()}


def test_pending_guard_blocks_non_success_conclusion_record() -> None:
    task_id = f"cf-integrity-guard-{hello_module.uuid.uuid4().hex[:8]}"
    hello_module.submit_task(
        task_id, goal="integrity", status="success", requires_review=True
    )
    hello_module.TASK_REGISTRY[task_id]["execution_result_json"] = (
        _integrity_result(task_id=task_id, workflow_run_conclusion="cancelled")
    )
    pending_ids = {t["task_id"] for t in hello_module.list_pending_results()}
    assert task_id not in pending_ids
    assert hello_module.TASK_REGISTRY[task_id]["status"] == "blocked"


def test_expected_files_must_be_produced_not_placeholder() -> None:
    assessment = hello_module.result_integrity_assessment(
        _integrity_result(
            workflow_run_conclusion="success",
            expected_files=["event_sync.py"],
            changed_files=["hello.py", "test_hello.py"],
        )
    )
    assert assessment["authoritative_status"] == "FAIL"
    assert assessment["missing_expected_files"] == ["event_sync.py"]
    assert "hello.py" not in assessment["missing_expected_files"]


def test_expected_files_produced_is_success() -> None:
    assessment = hello_module.result_integrity_assessment(
        _integrity_result(
            workflow_run_conclusion="success",
            expected_files=["event_sync.py"],
            changed_files=["event_sync.py"],
        )
    )
    assert assessment["authoritative_status"] == "PASS"
    assert assessment["missing_expected_files"] == []


def test_cancelled_run_diagnosis_is_evidence_backed_blocked() -> None:
    report = hello_module.diagnose_cancelled_run()
    assert report["task_id"] == "cf-33ef3836eb27"
    assert report["workflow_run_id"] == "36220934446"
    assert report["status"] == "BLOCKED"
    assert report["cause_known"] is False
    assert report["evidence_backed"] is True
    assert report["retry_allowed"] is False
    assert report["event_sync_retry"] == "NOT_ATTEMPTED"
    assert report["reason"]
    for field in hello_module.CANCELLED_RUN_DIAGNOSIS_FIELDS:
        assert field in report


def test_cancelled_run_diagnosis_classifies_supplied_cause() -> None:
    report = hello_module.diagnose_cancelled_run(
        evidence={
            "conclusion": "cancelled",
            "cause": "superseded by a newer dispatch in the same concurrency group",
        }
    )
    assert report["status"] == "PASS"
    assert report["cause_known"] is True
    assert report["cause"]
    assert report["retry_allowed"] is True


def test_event_sync_retry_gate_refuses_without_cause() -> None:
    gate = hello_module.event_sync_retry_gate()
    assert gate["goal"] == hello_module.EVENT_SYNC_GOAL
    assert gate["diagnosis_status"] == "BLOCKED"
    assert gate["retry_allowed"] is False
    assert gate["event_sync_retry"] == "NOT_ATTEMPTED"
