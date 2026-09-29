"""Automated test for hello.py."""

import inspect
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import uuid
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
    RESULT_SCHEMA_PRESERVATION_GOAL,
    RESULT_SCHEMA_PRESERVATION_REPORT,
    RESULT_SCHEMA_PRESERVATION_TASK_ID,
    RESULT_SCHEMA_PRESERVATION_UNKNOWN_FIELD,
    STATUS_MODEL_EXPECTED_FIELDS,
    TASK_REVIEW_GOAL,
    VERIFY_TESTS_TIMEOUT_POLICY_MAX_MINUTES,
    VERIFY_TESTS_TIMEOUT_POLICY_MIN_MINUTES,
    AUTONOMOUS_ADVANCEMENT_EVIDENCE_ENV,
    AUTONOMOUS_ADVANCEMENT_EVIDENCE_PATH_ENV,
    AUTONOMOUS_ADVANCEMENT_FINAL_BLOCKED_EVIDENCE,
    AUTONOMOUS_ADVANCEMENT_FINAL_FAIL,
    AUTONOMOUS_ADVANCEMENT_FINAL_GOLDEN_PASS,
    AUTONOMOUS_ADVANCEMENT_PRODUCTION_EVIDENCE_AUDIT_GOAL,
    AUTONOMOUS_ADVANCEMENT_PRODUCTION_EVIDENCE_AUDIT_REPORT,
    AUTONOMOUS_ADVANCEMENT_PRODUCTION_EVIDENCE_AUDIT_TASK_ID,
    auto_consume_completed_results,
    auto_result_close_loop_golden_verify,
    auto_result_golden_test_verify,
    autonomous_advancement_production_evidence_audit,
    build_result_schema_preservation_agent_result,
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
    personal_ai_autonomous_advancement_production_evidence_audit_v0_1,
    personal_ai_execution_dispatch_live_failure_audit,
    personal_ai_execution_result_exposure_audit_detail_export,
    personal_ai_task_runtime_audit,
    PRODUCTION_GOLDEN_RUNTIME_DUPLICATE_CALLS,
    PRODUCTION_GOLDEN_RUNTIME_PARENT_TASK_ID,
    PRODUCTION_GOLDEN_RUNTIME_REPORT,
    PRODUCTION_GOLDEN_RUNTIME_VERIFY_GOAL,
    PRODUCTION_GOLDEN_RUNTIME_VERIFY_TASK_ID,
    production_golden_runtime_verification,
    record_consumer_evidence,
    result_consumer_test,
    result_consumer_test2,
    result_schema_preservation_golden_verify,
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
    VERIFY_TESTS_FAILURE_ROOT_CAUSE,
    VERIFY_TESTS_FAILURE_STAGE,
    VERIFY_TESTS_STEP_NAME,
    VERIFY_TESTS_TIMEOUT_ACTION_CODE_FIX,
    VERIFY_TESTS_TIMEOUT_ACTION_CONFIG_FIX,
    VERIFY_TESTS_TIMEOUT_ACTION_RETRY_ONLY,
    classify_verify_tests_timeout_failure,
    verify_tests_timeout_is_within_policy,
    verify_tests_timeout_next_action,
    write_production_golden_runtime_execution_result,
    REAL_PUSH_BLOCKED_CREDENTIAL,
    REAL_PUSH_FAILED,
    REAL_PUSH_PASS,
    SERVERCHAN_REAL_PUSH_02_EVENT,
    SERVERCHAN_REAL_PUSH_02_GOAL,
    SERVERCHAN_REAL_PUSH_02_MARKER,
    SERVERCHAN_REAL_PUSH_02_REPORT,
    SERVERCHAN_REAL_PUSH_02_TASK_ID,
    SERVERCHAN_REAL_PUSH_02_TITLE,
    SERVERCHAN_REAL_PUSH_EVENT,
    SERVERCHAN_REAL_PUSH_GOAL,
    SERVERCHAN_REAL_PUSH_MARKER,
    SERVERCHAN_REAL_PUSH_REPORT,
    SERVERCHAN_REAL_PUSH_TASK_ID,
    SERVERCHAN_REAL_PUSH_TITLE,
    build_serverchan_golden_02_payload,
    build_serverchan_golden_payload,
    serverchan_real_push_golden,
    serverchan_real_push_golden_02,
)

VALID_STATUSES = {"PASS", "FAIL", "BLOCKED"}

# TEST ISOLATION (task cf-2f2b71c331da): the runner-process SendKey is
# deliberately NOT snapshotted. Every pytest path must inject a fake transport
# (or be stopped by hello's in-process test-isolation guard), so a present
# SERVERCHAN_SENDKEY can never cause a real ServerChan HTTPS call during pytest.

# Residual root cause of cloud-agent-dispatch run 36401601530: the checked-out
# workflow already declared `timeout-minutes: 15` for `Verify tests
# (independent)` (check-run annotation "timed out after 15 minutes"), yet the
# independent pytest suite still overran the budget because process-global state
# accumulated across tests and made later report builders scan ever-growing
# registries/ledgers. This autouse fixture resets that state before every test
# so the suite runtime stays bounded and remains inside the policy band.
_RESETTABLE_HELLO_STATE = (
    "TASK_REGISTRY",
    "REVIEW_EVENTS",
    "CONSUMPTION_EVIDENCE",
    "PRODUCTION_TERMINAL_EVIDENCE",
    "NOTIFICATION_LEDGER",
    "NOTIFICATION_DELIVERIES",
    "PUSH_OUTBOX",
)


@pytest.fixture(autouse=True)
def isolate_hello_state(monkeypatch, tmp_path):
    state_dir = tmp_path / "hello_state"
    state_dir.mkdir()
    monkeypatch.setenv(
        hello_module.EVENT_NOTIFICATION_STATE_ENV,
        str(state_dir / "notifications.json"),
    )
    monkeypatch.setenv(
        hello_module.NOTIFICATION_DELIVERY_STATE_ENV,
        str(state_dir / "deliveries.json"),
    )
    monkeypatch.setenv(
        hello_module.CONSUMER_EVIDENCE_ENV,
        str(state_dir / "consumer_evidence.json"),
    )
    monkeypatch.setenv(
        hello_module.PUSH_OUTBOX_STATE_ENV,
        str(state_dir / "push_outbox.json"),
    )
    # Durable ServerChan delivery ledger: always redirected to the test tmp dir so
    # the canonical repo-root ledger is never written by a test.
    monkeypatch.setenv(
        hello_module.DELIVERY_LEDGER_STATE_ENV,
        str(state_dir / "delivery_ledger.json"),
    )
    # Hard test-isolation marker: the real HTTP transport refuses to run while
    # this is set (and while pytest is imported / PYTEST_CURRENT_TEST is set).
    monkeypatch.setenv(hello_module.SERVERCHAN_TEST_ISOLATION_ENV, "1")
    monkeypatch.delenv(hello_module.PUSH_EXTERNAL_ENDPOINT_ENV, raising=False)
    monkeypatch.delenv(hello_module.SERVERCHAN_SENDKEY_ENV, raising=False)
    for name in _RESETTABLE_HELLO_STATE:
        container = getattr(hello_module, name, None)
        if container is not None:
            container.clear()
    hello_module._AUTO_CONSUMER_RAN = False
    hello_module._AUTO_CONSUMER_GUARD = False
    hello_module.reset_serverchan_test_isolation_counters()
    yield


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
    submit_task(
        GOLDEN_E2E_TASK_ID,
        goal="PERSONAL_AI_TASK_REVIEW_GOLDEN_E2E_VERIFY_V0.1",
        status="success",
        requires_review=True,
    )
    mark_reviewed(GOLDEN_E2E_TASK_ID, "PASS", "golden e2e")
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


def test_runtime_provenance_v0_1_report_shape() -> None:
    report = hello_module.runtime_provenance_v0_1_report()
    assert report["report"] == hello_module.RUNTIME_PROVENANCE_V01_REPORT
    assert report["goal"] == hello_module.RUNTIME_PROVENANCE_V01_GOAL
    assert report["goal"] == "PERSONAL_AI_RUNTIME_PROVENANCE_V0.1"
    assert report["task_id"] == hello_module.RUNTIME_PROVENANCE_V01_TASK_ID
    assert report["task_id"] == "cf-fc30ce98400d"
    assert set(hello_module.RUNTIME_PROVENANCE_V01_FIELDS) <= set(report)
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in {"PASS", "FAIL", "BLOCKED"}
        assert check["detail"]
    assert report["overall"] in {"PASS", "FAIL", "BLOCKED", "PARTIAL"}


def test_runtime_provenance_v0_1_identifies_deployed_version() -> None:
    report = hello_module.runtime_provenance_v0_1_report()
    assert isinstance(report["deployed_version"], str)
    assert report["deployed_version"]
    assert report["version_source"]
    assert report["version_evidence"]
    baseline = hello_module._load_repo_json(
        hello_module.RUNTIME_PROVENANCE_BASELINE_PATH
    )
    if baseline and baseline.get("production_version"):
        assert report["deployed_version"] == baseline["production_version"]
        assert report["deployment_metadata_present"] is True
        assert report["deployed_service"] == baseline["service"]


def test_runtime_provenance_v0_1_verifies_source_commit_relationship() -> None:
    report = hello_module.runtime_provenance_v0_1_report()
    assert isinstance(report["relationship_verified"], bool)
    assert isinstance(report["runtime_verified"], bool)
    assert report["source_tracked"] is True
    assert report["source_commit_on_history"] is True
    assert report["source_last_commit"]
    expected = bool(
        report["deployment_metadata_present"]
        and report["canonical_source_present"]
        and report["source_tracked"]
        and report["source_commit_on_history"]
        and report["source_hash_matches"]
        and report["source_size_matches"]
        and report["source_lines_matches"]
    )
    assert report["relationship_verified"] is expected
    if report["relationship_verified"]:
        assert report["runtime_verified"] is True
    else:
        assert report["runtime_verified"] is False


def test_runtime_provenance_v0_1_reports_metadata_source_mismatch() -> None:
    report = hello_module.runtime_provenance_v0_1_report()
    if report["recorded_source_hash"] and report["canonical_source_hash"]:
        matches = (
            report["recorded_source_hash"].lower()
            == report["canonical_source_hash"].lower()
        )
        assert report["source_hash_matches"] is matches
        check = next(
            c
            for c in report["checks"]
            if c["check"] == "deployment metadata source matches canonical source"
        )
        if not matches:
            assert check["status"] == "BLOCKED"
            assert report["relationship_verified"] is False
            assert report["runtime_verified"] is False


def test_runtime_provenance_v0_1_no_production_mutation() -> None:
    report = hello_module.runtime_provenance_v0_1_report()
    assert report["production_mutated"] is False
    assert report["read_only"] is True
    assert report["live_endpoint_checked"] is False
    check = next(
        c for c in report["checks"] if c["check"] == "no production mutation"
    )
    assert check["status"] == "PASS"


def test_runtime_provenance_v0_1_no_fabricated_pass() -> None:
    report = hello_module.runtime_provenance_v0_1_report()
    if not report["runtime_verified"]:
        assert report["overall"] != "PASS"
    if report["overall"] == "PASS":
        assert report["runtime_verified"] is True
        assert all(c["status"] == "PASS" for c in report["checks"])


def test_runtime_provenance_v0_1_markdown_tokens() -> None:
    report = hello_module.runtime_provenance_v0_1_report()
    markdown = report["markdown"]
    assert markdown.startswith("# PERSONAL_AI_RUNTIME_PROVENANCE_REPORT")
    assert f"- task_id: {report['task_id']}" in markdown
    assert f"DEPLOYED_VERSION={report['deployed_version']}" in markdown
    assert f"RELATIONSHIP_VERIFIED={report['relationship_verified']}" in markdown
    assert f"RUNTIME_VERIFIED={report['runtime_verified']}" in markdown
    assert "PRODUCTION_MUTATED=False" in markdown


POST_CANONICAL_DEPLOY_GOLDEN_TASK_ID = "cf-e4a3dd8b4989"


def _import_personal_ai_execution():
    import sys
    from pathlib import Path

    src = Path(__file__).resolve().parent / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import personal_ai_execution

    return personal_ai_execution


def test_post_canonical_deploy_live_golden_success_path() -> None:
    """Bounded no-mutation check of submit -> result -> discovery -> review gate."""
    pkg = _import_personal_ai_execution()
    PASS = pkg.PASS
    EventSyncRegistry = pkg.EventSyncRegistry
    from personal_ai_execution import status_contract as sc

    registry = EventSyncRegistry()
    task_id = POST_CANONICAL_DEPLOY_GOLDEN_TASK_ID
    registry.submit_task(task_id, goal="no-change production execution golden")

    fresh = registry.get_task_result(task_id)
    assert fresh["status"] == sc.PENDING
    assert fresh["terminal"] is False
    assert registry.list_pending_results() == []

    with pytest.raises(ValueError):
        registry.mark_reviewed(task_id, "PASS", note="too early")

    sync = registry.sync_terminal_result(
        task_id,
        execution_result={"task_id": task_id, "status": "success"},
        workflow_conclusion_value="success",
    )
    assert sync["status"] == PASS
    assert sync["terminal"] is True

    result = registry.get_task_result(task_id)
    assert result["task_id"] == task_id
    assert result["status"] == PASS
    assert result["workflow_conclusion"] == "success"
    assert result["terminal"] is True

    pending = registry.list_pending_results()
    assert [record["task_id"] for record in pending] == [task_id]
    assert pending[0]["normalized_status"] == PASS
    assert pending[0]["review_state"] == "pending_review"

    reviewed = registry.mark_reviewed(task_id, "PASS", note="golden verified")
    assert reviewed["review_verdict"] == PASS
    assert reviewed["status"] == PASS
    assert reviewed["normalized_status"] == PASS
    assert registry.list_pending_results() == []


def test_post_canonical_deploy_live_golden_failure_bucket() -> None:
    """A non-success conclusion lands in the failure bucket, never upgraded."""
    pkg = _import_personal_ai_execution()
    BLOCKED = pkg.BLOCKED
    FAIL = pkg.FAIL
    PASS = pkg.PASS
    EventSyncRegistry = pkg.EventSyncRegistry

    registry = EventSyncRegistry()
    task_id = f"{POST_CANONICAL_DEPLOY_GOLDEN_TASK_ID}-failure"
    registry.submit_task(task_id, goal="no-change production execution golden")

    sync = registry.sync_terminal_result(
        task_id,
        execution_result={"task_id": task_id, "status": "success"},
        workflow_conclusion_value="failure",
    )
    assert sync["status"] == FAIL

    result = registry.get_task_result(task_id)
    assert result["status"] == FAIL
    assert result["execution_result_status"] == PASS
    assert result["conclusion_result_mismatch"] is True

    pending = registry.list_pending_results()
    assert [record["task_id"] for record in pending] == [task_id]

    blocked = registry.sync_terminal_result(
        task_id,
        execution_result={"task_id": task_id, "status": "success"},
        workflow_conclusion_value="cancelled",
    )
    assert blocked["status"] == BLOCKED
    assert registry.get_task_result(task_id)["status"] == BLOCKED


# -- PERSONAL_AI_AUTONOMOUS_ADVANCEMENT_GOLDEN_RUNTIME_VERIFY_V0.1 ----------
#
# Golden runtime verification of the canonical production Worker
# ``mark_reviewed(verdict, approved_next_task)`` behaviour. The production
# source runs read-only under node against an in-memory D1/KV/fetch double.

NODE_AVAILABLE = shutil.which("node") is not None
requires_node = pytest.mark.skipif(
    not NODE_AVAILABLE, reason="node runtime is required to execute the worker source"
)


@pytest.fixture(scope="module")
def golden_runtime_report() -> dict:
    return production_golden_runtime_verification()


@requires_node
def test_production_golden_runtime_verify_goal_and_task_id(
    golden_runtime_report: dict,
) -> None:
    assert golden_runtime_report["goal"] == PRODUCTION_GOLDEN_RUNTIME_VERIFY_GOAL
    assert (
        golden_runtime_report["task_id"] == PRODUCTION_GOLDEN_RUNTIME_VERIFY_TASK_ID
    )
    assert golden_runtime_report["report"] == PRODUCTION_GOLDEN_RUNTIME_REPORT


@requires_node
def test_production_golden_runtime_status_is_pass(golden_runtime_report: dict) -> None:
    assert (
        golden_runtime_report["PRODUCTION_GOLDEN_RUNTIME_STATUS"] == "PASS"
    )
    assert golden_runtime_report["production_mutated"] is False
    assert golden_runtime_report["read_only"] is True
    assert all(check["status"] == "PASS" for check in golden_runtime_report["checks"])


@requires_node
def test_production_golden_runtime_parent_child_dispatch_evidence(
    golden_runtime_report: dict,
) -> None:
    parent_task_id = golden_runtime_report["parent_task_id"]
    child_task_id = golden_runtime_report["child_task_id"]
    assert parent_task_id == PRODUCTION_GOLDEN_RUNTIME_PARENT_TASK_ID
    assert parent_task_id
    assert child_task_id
    assert child_task_id.startswith("cf-")
    assert child_task_id != parent_task_id
    assert (
        golden_runtime_report["exactly_once"]["parent_task_id"] == parent_task_id
    )
    assert golden_runtime_report["exactly_once"]["child_task_id"] == child_task_id


@requires_node
def test_production_golden_runtime_exactly_once(golden_runtime_report: dict) -> None:
    exactly_once = golden_runtime_report["exactly_once"]
    assert exactly_once["verified"] is True
    assert exactly_once["duplicate_calls"] == PRODUCTION_GOLDEN_RUNTIME_DUPLICATE_CALLS
    assert exactly_once["dispatch_calls"] == 1
    assert exactly_once["reason"] == "ALREADY_DISPATCHED"
    assert exactly_once["child_task_ids"] == [golden_runtime_report["child_task_id"]]


@requires_node
def test_production_golden_runtime_fail_closed(golden_runtime_report: dict) -> None:
    fail_closed = golden_runtime_report["fail_closed"]
    assert fail_closed["verified"] is True
    scenarios = fail_closed["scenarios"]
    for name in (
        "FAIL",
        "BLOCKED",
        "missing_approved_next_task",
        "invalid_approved_next_task",
        "dispatch_marker_unavailable",
        "github_rejected",
    ):
        assert scenarios[name]["status"] == "PASS", name
    assert scenarios["FAIL"]["reason"] == "VERDICT_NOT_PASS"
    assert scenarios["FAIL"]["dispatch_calls"] == 0
    assert scenarios["BLOCKED"]["reason"] == "VERDICT_NOT_PASS"
    assert scenarios["BLOCKED"]["dispatch_calls"] == 0
    assert scenarios["missing_approved_next_task"]["reason"] == "NO_APPROVED_NEXT_TASK"
    assert scenarios["missing_approved_next_task"]["dispatch_calls"] == 0
    assert scenarios["invalid_approved_next_task"]["reason"] == (
        "INVALID_APPROVED_NEXT_TASK"
    )
    assert scenarios["github_rejected"]["dispatch_calls"] == 1


@requires_node
def test_production_golden_runtime_markdown_tokens(golden_runtime_report: dict) -> None:
    markdown = golden_runtime_report["markdown"]
    assert f"PRODUCTION_GOLDEN_RUNTIME_STATUS={golden_runtime_report['PRODUCTION_GOLDEN_RUNTIME_STATUS']}" in markdown
    assert (
        f"parent_task_id={golden_runtime_report['parent_task_id']}" in markdown
    )
    assert f"child_task_id={golden_runtime_report['child_task_id']}" in markdown
    assert "exactly_once_verified=True" in markdown
    assert "fail_closed_verified=True" in markdown


@requires_node
def test_write_production_golden_runtime_execution_result(tmp_path) -> None:
    target = tmp_path / "execution_result.json"
    written = write_production_golden_runtime_execution_result(output_path=target)
    assert written["path"] == str(target)
    assert target.is_file()

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["status"] == "success"
    assert payload["task_id"] == PRODUCTION_GOLDEN_RUNTIME_VERIFY_TASK_ID
    assert payload["goal"] == PRODUCTION_GOLDEN_RUNTIME_VERIFY_GOAL
    assert payload["PRODUCTION_GOLDEN_RUNTIME_STATUS"] == "PASS"
    assert payload["parent_task_id"] == PRODUCTION_GOLDEN_RUNTIME_PARENT_TASK_ID
    assert payload["child_task_id"]
    assert payload["exactly_once_verified"] is True
    assert payload["fail_closed_verified"] is True
    assert payload["production_mutated"] is False


def test_production_golden_runtime_missing_node_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hello_module, "_node_executable", lambda: None)
    report = production_golden_runtime_verification()
    assert report["PRODUCTION_GOLDEN_RUNTIME_STATUS"] == "BLOCKED"
    assert report["probe_available"] is False
    assert report["parent_task_id"] is None
    assert report["child_task_id"] is None


def test_production_golden_runtime_missing_source_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(
        hello_module, "_production_worker_source_path", lambda: tmp_path / "missing.js"
    )
    report = production_golden_runtime_verification()
    assert report["PRODUCTION_GOLDEN_RUNTIME_STATUS"] == "BLOCKED"
    assert report["probe_available"] is False


# -- PERSONAL_AI_AUTONOMOUS_ADVANCEMENT_PRODUCTION_EVIDENCE_AUDIT_V0.1 ------
#
# Final read-only production evidence audit of the PASS-review -> child-dispatch
# edge. The default environment has no authoritative Cloudflare D1 read, so the
# audit must fail closed (BLOCKED_EVIDENCE_MISSING), never invent GOLDEN_PASS.


def captured_production_evidence() -> dict:
    """A syntactically complete authoritative capture, used to exercise the
    GOLDEN_PASS / FAIL evaluation branches without touching production."""
    return {
        "available": True,
        "source": "test-capture:cloudflare-d1-readonly",
        "captured_at": "2026-09-27T00:00:00Z",
        "d1": {
            "table_present": True,
            "indexes_satisfied": True,
            "remote_applied": True,
        },
        "pass_dispatch": {
            "parent_task_id": "cf-golden-parent-1",
            "child_task_id": "cf-golden-child-1",
            "dispatch_state": "DISPATCHED",
            "created_at": "2026-09-27T00:00:01Z",
        },
        "exactly_once": {
            "parent_task_id": "cf-golden-parent-1",
            "child_task_id": "cf-golden-child-1",
            "child_dispatch_count": 1,
            "replay_reason": "ALREADY_DISPATCHED",
        },
        "fail_closed": {
            "FAIL": {"child_dispatch_count": 0},
            "BLOCKED": {"child_dispatch_count": 0},
            "missing_approved_next_task": {"child_dispatch_count": 0},
        },
        "cloudflare": {
            "version_id": "ver-golden-1",
            "deployment_id": "dep-golden-1",
        },
    }


@pytest.fixture(scope="module")
def production_evidence_audit_report() -> dict:
    return autonomous_advancement_production_evidence_audit()


def test_production_evidence_audit_goal_and_task_id(
    production_evidence_audit_report: dict,
) -> None:
    assert (
        production_evidence_audit_report["goal"]
        == AUTONOMOUS_ADVANCEMENT_PRODUCTION_EVIDENCE_AUDIT_GOAL
    )
    assert (
        production_evidence_audit_report["task_id"]
        == AUTONOMOUS_ADVANCEMENT_PRODUCTION_EVIDENCE_AUDIT_TASK_ID
    )
    assert (
        production_evidence_audit_report["report"]
        == AUTONOMOUS_ADVANCEMENT_PRODUCTION_EVIDENCE_AUDIT_REPORT
    )


def test_production_evidence_audit_default_is_blocked(
    production_evidence_audit_report: dict,
) -> None:
    report = production_evidence_audit_report
    assert report["FINAL_STATUS"] == AUTONOMOUS_ADVANCEMENT_FINAL_BLOCKED_EVIDENCE
    assert report["authoritative_evidence"] is False
    assert report["read_only"] is True
    assert report["production_mutated"] is False
    assert report["remote_mutations"] == 0
    assert report["deployments"] == 0
    assert report["d1_mutations"] == 0


def test_production_evidence_audit_d1_schema_table_and_three_indexes(
    production_evidence_audit_report: dict,
) -> None:
    d1 = production_evidence_audit_report["d1_schema"]
    assert d1["table"] == "task_dispatch_markers"
    assert d1["table_present"] is True
    indexes = d1["indexes"]
    assert set(indexes) == {
        "idx_task_dispatch_markers_parent",
        "idx_task_dispatch_markers_child",
        "idx_task_dispatch_markers_state",
    }
    assert indexes["idx_task_dispatch_markers_parent"]["column"] == "parent_task_id"
    assert indexes["idx_task_dispatch_markers_parent"]["required_unique"] is True
    assert indexes["idx_task_dispatch_markers_parent"]["unique"] is True
    assert indexes["idx_task_dispatch_markers_child"]["column"] == "child_task_id"
    assert indexes["idx_task_dispatch_markers_child"]["required_unique"] is False
    assert indexes["idx_task_dispatch_markers_state"]["column"] == "dispatch_state"
    assert indexes["idx_task_dispatch_markers_state"]["required_unique"] is False
    assert all(item["satisfied"] for item in indexes.values())
    assert d1["indexes_satisfied"] is True
    # In-repo schema only: production D1 remains non-authoritative/blocked.
    assert d1["production_authoritative"] is False
    assert d1["status"] == AUTONOMOUS_ADVANCEMENT_FINAL_BLOCKED_EVIDENCE
    assert d1["remote_applied"] is False


def test_production_evidence_audit_default_pass_dispatch_is_missing(
    production_evidence_audit_report: dict,
) -> None:
    dispatch = production_evidence_audit_report["pass_dispatch"]
    assert dispatch["parent_task_id"] is None
    assert dispatch["child_task_id"] is None
    assert dispatch["status"] == AUTONOMOUS_ADVANCEMENT_FINAL_BLOCKED_EVIDENCE
    assert dispatch["missing_reason"]


def test_production_evidence_audit_default_exactly_once_is_missing(
    production_evidence_audit_report: dict,
) -> None:
    exactly_once = production_evidence_audit_report["exactly_once"]
    assert exactly_once["child_dispatch_count"] is None
    assert exactly_once["status"] == AUTONOMOUS_ADVANCEMENT_FINAL_BLOCKED_EVIDENCE


def test_production_evidence_audit_default_fail_closed_is_missing(
    production_evidence_audit_report: dict,
) -> None:
    fail_closed = production_evidence_audit_report["fail_closed"]
    assert fail_closed["status"] == AUTONOMOUS_ADVANCEMENT_FINAL_BLOCKED_EVIDENCE
    for name in ("FAIL", "BLOCKED", "missing_approved_next_task"):
        assert fail_closed["scenarios"][name]["child_dispatch_count"] is None
        assert (
            fail_closed["scenarios"][name]["status"]
            == AUTONOMOUS_ADVANCEMENT_FINAL_BLOCKED_EVIDENCE
        )


def test_production_evidence_audit_cloudflare_version_missing_reason(
    production_evidence_audit_report: dict,
) -> None:
    cloudflare = production_evidence_audit_report["cloudflare"]
    assert cloudflare["version_id"] is None
    assert cloudflare["deployment_id"] is None
    assert cloudflare["status"] == AUTONOMOUS_ADVANCEMENT_FINAL_BLOCKED_EVIDENCE
    assert cloudflare["missing_reason"]
    assert cloudflare["declared_production_version"]


def test_production_evidence_audit_golden_pass_with_captured_evidence() -> None:
    report = autonomous_advancement_production_evidence_audit(
        captured_production_evidence()
    )
    assert report["FINAL_STATUS"] == AUTONOMOUS_ADVANCEMENT_FINAL_GOLDEN_PASS
    assert all(status == "PASS" for status in report["section_statuses"].values())
    assert report["pass_dispatch"]["parent_task_id"] == "cf-golden-parent-1"
    assert report["pass_dispatch"]["child_task_id"] == "cf-golden-child-1"
    assert report["cloudflare"]["version_id"] == "ver-golden-1"
    assert report["cloudflare"]["deployment_id"] == "dep-golden-1"
    assert report["remote_mutations"] == 0
    assert report["deployments"] == 0
    assert report["d1_mutations"] == 0


def test_production_evidence_audit_exactly_once_count_is_one() -> None:
    report = autonomous_advancement_production_evidence_audit(
        captured_production_evidence()
    )
    exactly_once = report["exactly_once"]
    assert exactly_once["child_dispatch_count"] == 1
    assert exactly_once["replay_reason"] == "ALREADY_DISPATCHED"
    assert exactly_once["status"] == "PASS"


def test_production_evidence_audit_fail_closed_all_zero() -> None:
    report = autonomous_advancement_production_evidence_audit(
        captured_production_evidence()
    )
    assert report["fail_closed"]["status"] == "PASS"
    for name in ("FAIL", "BLOCKED", "missing_approved_next_task"):
        assert report["fail_closed"]["scenarios"][name]["child_dispatch_count"] == 0


def test_production_evidence_audit_fails_on_second_child() -> None:
    evidence = captured_production_evidence()
    evidence["exactly_once"]["child_dispatch_count"] = 2
    report = autonomous_advancement_production_evidence_audit(evidence)
    assert report["exactly_once"]["status"] == "FAIL"
    assert report["FINAL_STATUS"] == AUTONOMOUS_ADVANCEMENT_FINAL_FAIL


def test_production_evidence_audit_fails_on_fail_closed_leak() -> None:
    evidence = captured_production_evidence()
    evidence["fail_closed"]["BLOCKED"]["child_dispatch_count"] = 1
    report = autonomous_advancement_production_evidence_audit(evidence)
    assert report["fail_closed"]["scenarios"]["BLOCKED"]["status"] == "FAIL"
    assert report["FINAL_STATUS"] == AUTONOMOUS_ADVANCEMENT_FINAL_FAIL


def test_production_evidence_audit_missing_parent_child_is_blocked() -> None:
    evidence = captured_production_evidence()
    evidence["pass_dispatch"] = {}
    report = autonomous_advancement_production_evidence_audit(evidence)
    assert report["pass_dispatch"]["status"] == (
        AUTONOMOUS_ADVANCEMENT_FINAL_BLOCKED_EVIDENCE
    )
    assert report["FINAL_STATUS"] == AUTONOMOUS_ADVANCEMENT_FINAL_BLOCKED_EVIDENCE


def test_production_evidence_audit_capture_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        AUTONOMOUS_ADVANCEMENT_EVIDENCE_ENV,
        json.dumps(captured_production_evidence()),
    )
    report = autonomous_advancement_production_evidence_audit()
    assert report["authoritative_evidence"] is True
    assert report["FINAL_STATUS"] == AUTONOMOUS_ADVANCEMENT_FINAL_GOLDEN_PASS


def test_production_evidence_audit_invalid_env_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(AUTONOMOUS_ADVANCEMENT_EVIDENCE_ENV, "not-json")
    report = autonomous_advancement_production_evidence_audit()
    assert report["authoritative_evidence"] is False
    assert report["FINAL_STATUS"] == AUTONOMOUS_ADVANCEMENT_FINAL_BLOCKED_EVIDENCE


def test_production_evidence_audit_markdown_tokens() -> None:
    report = autonomous_advancement_production_evidence_audit(
        captured_production_evidence()
    )
    markdown = report["markdown"]
    for token in (
        "D1_SCHEMA_EVIDENCE",
        "PASS_DISPATCH_EVIDENCE",
        "EXACTLY_ONCE_EVIDENCE",
        "FAIL_CLOSED_EVIDENCE",
        "remote_mutations=0",
        "deployments=0",
        "d1_mutations=0",
    ):
        assert token in markdown
    assert f"FINAL_STATUS={report['FINAL_STATUS']}" in markdown
    assert "parent_task_id=cf-golden-parent-1" in markdown
    assert "child_task_id=cf-golden-child-1" in markdown
    assert "child_dispatch_count=1" in markdown

    blocked = autonomous_advancement_production_evidence_audit()
    assert "FINAL_STATUS=BLOCKED_EVIDENCE_MISSING" in blocked["markdown"]


def test_personal_ai_autonomous_advancement_alias() -> None:
    report = personal_ai_autonomous_advancement_production_evidence_audit_v0_1(
        captured_production_evidence()
    )
    assert report["FINAL_STATUS"] == AUTONOMOUS_ADVANCEMENT_FINAL_GOLDEN_PASS


# -- PERSONAL_AI_EXECUTION_RUNTIME_GOLDEN_VERIFY_V0.1 -----------------------
# Golden verification that a structured Agent result survives the production
# chain (agent_result.json -> build_execution_result.py -> execution_result.json
# -> get_task_result) with RESULT_SCHEMA_PRESERVATION intact.


@pytest.fixture(scope="module")
def result_schema_preservation_golden_report() -> dict:
    return result_schema_preservation_golden_verify()


def test_result_schema_preservation_report_contract(
    result_schema_preservation_golden_report: dict,
) -> None:
    report = result_schema_preservation_golden_report
    assert report["report"] == RESULT_SCHEMA_PRESERVATION_REPORT
    assert report["goal"] == RESULT_SCHEMA_PRESERVATION_GOAL
    assert report["task_id"] == RESULT_SCHEMA_PRESERVATION_TASK_ID
    assert report["status"] == "PASS"
    assert report["final_status"] == "PASS"
    assert report["production_mutated"] is False
    assert report["read_only"] is True
    assert report["generator_error"] is None


def test_result_schema_preservation_unknown_field_survives_generator(
    result_schema_preservation_golden_report: dict,
) -> None:
    report = result_schema_preservation_golden_report
    artifact = report["execution_result_json"]
    fixture = report["agent_result"]
    unknown = RESULT_SCHEMA_PRESERVATION_UNKNOWN_FIELD

    assert artifact[unknown] == fixture[unknown]
    assert artifact["evidence"] == fixture["evidence"]
    assert artifact["artifacts"] == fixture["artifacts"]
    assert artifact["agent_result"] == fixture
    assert artifact["final_status"] == fixture["final_status"]


def test_result_schema_preservation_keeps_business_and_workflow_status_separate(
    result_schema_preservation_golden_report: dict,
) -> None:
    artifact = result_schema_preservation_golden_report["execution_result_json"]
    assert artifact["status"] == "success"
    assert artifact["final_status"] == "PASS"
    assert artifact["task_id"] == RESULT_SCHEMA_PRESERVATION_TASK_ID


def test_result_schema_preservation_get_task_result_exposes_unknown_field(
    result_schema_preservation_golden_report: dict,
) -> None:
    report = result_schema_preservation_golden_report
    exposed = report["get_task_result_exposed"]
    raw = exposed["execution_result_json"]
    fixture = report["agent_result"]
    unknown = RESULT_SCHEMA_PRESERVATION_UNKNOWN_FIELD

    assert raw[unknown] == fixture[unknown]
    assert raw["evidence"] == fixture["evidence"]
    assert raw["artifacts"] == fixture["artifacts"]
    assert raw["agent_result"] == fixture


def test_get_task_result_preserves_agent_unknown_field_via_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = result_schema_preservation_golden_verify()
    artifact = report["execution_result_json"]
    monkeypatch.setattr(hello_module, "_read_execution_result", lambda: artifact)

    result = get_task_result(RESULT_SCHEMA_PRESERVATION_TASK_ID)
    raw = result["execution_result_json"]
    unknown = RESULT_SCHEMA_PRESERVATION_UNKNOWN_FIELD

    assert raw[unknown] == report["agent_result"][unknown]
    assert raw["evidence"]
    assert raw["artifacts"]
    assert raw["agent_result"]
    assert result["artifacts"]


def test_result_schema_preservation_missing_unknown_field_fails() -> None:
    fixture = build_result_schema_preservation_agent_result()
    fixture.pop(RESULT_SCHEMA_PRESERVATION_UNKNOWN_FIELD)

    report = result_schema_preservation_golden_verify(fixture)

    assert report["final_status"] == "FAIL"
    assert any(
        item["status"] == "FAIL"
        and RESULT_SCHEMA_PRESERVATION_UNKNOWN_FIELD in item["check"]
        for item in report["checks"]
    )



# -- PERSONAL_AI_AUTO_REVIEW_GATE_V0.1 -------------------------------------
# Minimal closed loop: read a completed get_task_result payload -> decide
# PASS/FAIL/BLOCKED -> apply (or simulate) mark_reviewed. No Router, no
# multi-agent scheduling, no workflow/token change.

AUTO_REVIEW_GATE_ACCEPTANCE_FIELDS = (
    "auto decision logic exposed",
    "PASS/FAIL/BLOCKED mapping",
    "mark_reviewed applied",
    "dry-run has no side effect",
    "execution_result return structure preserved",
    "contracts unchanged",
)


def _auto_review_gate_test_id(kind: str) -> str:
    return f"auto-review-gate-test-{kind}-{hello_module.uuid.uuid4().hex[:10]}"


def _auto_review_gate_test_evidence(probe_id: str) -> dict:
    return {
        "tests": "5 passed in 0.20s",
        "artifacts": [
            {
                "name": "hello.py",
                "path": "hello.py",
                "sha256": "f" * 64,
                "bytes": 42,
            }
        ],
        "evidence": {"validation": {"pytest": "5 passed"}},
        "execution_result_json": {
            "task_id": probe_id,
            "status": "success",
            "tests": "5 passed",
        },
    }


@pytest.fixture(scope="module")
def auto_review_gate_report() -> dict:
    return hello_module.personal_ai_auto_review_gate_v0_1()


def test_auto_review_gate_report_contract(auto_review_gate_report: dict) -> None:
    report = auto_review_gate_report
    assert report["report"] == "PERSONAL_AI_AUTO_REVIEW_GATE_REPORT"
    assert report["goal"] == "PERSONAL_AI_AUTO_REVIEW_GATE_V0.1"
    assert report["task_id"] == "cf-cdcf9d65ec42"
    assert report["status"] == "PASS"
    assert report["final_status"] == "PASS"
    assert report["decision_logic"]
    assert report["markdown"].startswith("# PERSONAL_AI_AUTO_REVIEW_GATE_REPORT")
    assert "FINAL_STATUS=PASS" in report["markdown"]


def test_auto_review_gate_checks_all_pass(auto_review_gate_report: dict) -> None:
    report = auto_review_gate_report
    checks = {check["check"]: check for check in report["checks"]}
    assert set(checks) == set(AUTO_REVIEW_GATE_ACCEPTANCE_FIELDS)
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] == "PASS"
        assert check["detail"]


def test_auto_review_gate_state_mapping_exposes_three_states(
    auto_review_gate_report: dict,
) -> None:
    report = auto_review_gate_report
    assert set(report["states"]) == {"PASS", "FAIL", "BLOCKED"}
    assert set(report["state_mapping"]) == {"PASS", "FAIL", "BLOCKED"}
    for state, rule in report["state_mapping"].items():
        assert rule
    assert report["state_mapping_ok"] is True

    actuals = {scenario["scenario"]: scenario["actual"] for scenario in report["scenarios"]}
    assert actuals["success_maps_to_pass"] == "PASS"
    assert actuals["failing_tests_map_to_fail"] == "FAIL"
    assert actuals["insufficient_evidence_maps_to_blocked"] == "BLOCKED"
    assert set(actuals.values()) >= {"PASS", "FAIL", "BLOCKED"}


def test_auto_review_gate_scenarios_are_auditable(
    auto_review_gate_report: dict,
) -> None:
    for scenario in auto_review_gate_report["scenarios"]:
        assert set(scenario) >= {
            "scenario",
            "expected",
            "actual",
            "status",
            "applied",
            "evidence",
        }
        assert scenario["status"] == "PASS"
        assert scenario["expected"] == scenario["actual"]
        assert scenario["evidence"]


def test_auto_review_gate_applies_mark_reviewed() -> None:
    probe = _auto_review_gate_test_id("apply")
    hello_module.submit_task(
        probe,
        goal="PERSONAL_AI_AUTO_REVIEW_GATE_V0.1",
        status="success",
        requires_review=True,
        **_auto_review_gate_test_evidence(probe),
    )
    run = hello_module.auto_review_gate(probe, apply=True)
    assert run["verdict"] == "PASS"
    assert run["mark_reviewed_applied"] is True
    assert run["mode"] == "apply"
    assert run["mark_reviewed_call"] == {
        "task_id": probe,
        "verdict": "PASS",
        "note": run["reason"],
    }
    record = hello_module.get_task_review(probe)
    assert record["reviewed"] is True
    assert record["review_verdict"] == "PASS"
    assert record["reviewed_at"]
    events = hello_module.get_review_events(probe)
    assert len(events) == 1
    assert events[0]["verdict"] == "PASS"
    assert events[0]["action"] == "review"


def test_auto_review_gate_dry_run_has_no_side_effect() -> None:
    probe = _auto_review_gate_test_id("dry")
    hello_module.submit_task(
        probe,
        goal="PERSONAL_AI_AUTO_REVIEW_GATE_V0.1",
        status="success",
        requires_review=True,
        **_auto_review_gate_test_evidence(probe),
    )
    run = hello_module.auto_review_gate(probe, apply=False)
    assert run["verdict"] == "PASS"
    assert run["mode"] == "dry_run"
    assert run["mark_reviewed_applied"] is False
    assert run["review_record"] is None
    record = hello_module.get_task_review(probe)
    assert record["reviewed"] is False
    assert record["review_verdict"] is None
    assert hello_module.get_review_events(probe) == []


def test_auto_review_gate_fail_and_blocked_stop_gate() -> None:
    fail_probe = _auto_review_gate_test_id("fail")
    fail_evidence = _auto_review_gate_test_evidence(fail_probe)
    hello_module.submit_task(
        fail_probe,
        goal="PERSONAL_AI_AUTO_REVIEW_GATE_V0.1",
        status="success",
        requires_review=True,
        tests="1 failed, 4 passed",
        artifacts=fail_evidence["artifacts"],
        evidence=fail_evidence["evidence"],
        execution_result_json=fail_evidence["execution_result_json"],
    )
    fail_run = hello_module.auto_review_gate(fail_probe, apply=True)
    assert fail_run["verdict"] == "FAIL"
    assert fail_run["stop_gate"] is True
    assert fail_run["blockers"]
    assert hello_module.get_task_review(fail_probe)["review_verdict"] == "FAIL"

    blocked_probe = _auto_review_gate_test_id("blocked")
    hello_module.submit_task(
        blocked_probe,
        goal="PERSONAL_AI_AUTO_REVIEW_GATE_V0.1",
        status="success",
        requires_review=True,
    )
    blocked_run = hello_module.auto_review_gate(blocked_probe, apply=True)
    assert blocked_run["verdict"] == "BLOCKED"
    assert blocked_run["stop_gate"] is True
    assert blocked_run["blockers"]
    assert (
        hello_module.get_task_review(blocked_probe)["review_verdict"] == "BLOCKED"
    )


def test_auto_review_gate_rejects_empty_task_id() -> None:
    with pytest.raises(ValueError):
        hello_module.auto_review_gate("")


def test_auto_review_gate_preserves_execution_result_structure(
    auto_review_gate_report: dict,
) -> None:
    report = auto_review_gate_report
    assert report["execution_result_contract_preserved"] is True
    assert report["execution_result_evidence_preserved"] is True
    assert report["execution_result_json_preserved"] is True
    assert set(report["execution_result_contract_fields"]) == {
        "execution_summary",
        "commit",
        "tests",
        "artifacts",
        "execution_result_json",
        "evidence",
    }
    probe_id = report["scenario_ids"]["pass"]
    result = hello_module.get_task_result(probe_id)
    assert set(result) == set(report["execution_result_contract_fields"])
    assert set(result["evidence"]) >= {
        "acceptance",
        "logs",
        "validation",
        "decision",
    }
    assert isinstance(result["execution_result_json"], dict)
    assert isinstance(result["artifacts"], list)


def test_auto_review_gate_contracts_unchanged(
    auto_review_gate_report: dict,
) -> None:
    report = auto_review_gate_report
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["get_task_result_contract"] == "UNCHANGED"
    assert report["mark_reviewed_contract"] == "COMPATIBLE"
    assert report["workflow_modified"] is False
    assert report["read_only_execution_result"] is True
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


# -- PERSONAL_AI_NEXT_TASK_PROPOSAL_GATE_V0.1 ------------------------------
# Advisory-only next-task proposal generated from the existing auto_review_gate
# PASS/FAIL/BLOCKED verdict. No dispatch, no submit_task rewrite.

NEXT_TASK_PROPOSAL_ACCEPTANCE_FIELDS = (
    "proposal generated for PASS/FAIL/BLOCKED",
    "proposal is advisory only",
    "next_task_proposal schema stable",
    "no dispatch or review side effect",
    "execution_result structure preserved",
    "contracts unchanged",
)

NEXT_TASK_PROPOSAL_EXPECTED_FIELDS = {
    "task_id",
    "verdict",
    "action",
    "next_task_goal",
    "reason",
    "blockers",
    "source",
    "auto_dispatch",
    "dispatch_allowed",
    "requires_human_approval",
}


@pytest.fixture(scope="module")
def next_task_proposal_report() -> dict:
    return hello_module.personal_ai_next_task_proposal_gate_v0_1()


def test_next_task_proposal_report_contract(
    next_task_proposal_report: dict,
) -> None:
    report = next_task_proposal_report
    assert report["report"] == "PERSONAL_AI_NEXT_TASK_PROPOSAL_REPORT"
    assert report["goal"] == "PERSONAL_AI_NEXT_TASK_PROPOSAL_GATE_V0.1"
    assert report["task_id"] == "cf-86f2f7e8512e"
    assert report["status"] == "PASS"
    assert report["final_status"] == "PASS"
    assert report["decision_logic"]
    assert report["markdown"].startswith("# PERSONAL_AI_NEXT_TASK_PROPOSAL_REPORT")
    assert "FINAL_STATUS=PASS" in report["markdown"]


def test_next_task_proposal_checks_all_pass(
    next_task_proposal_report: dict,
) -> None:
    report = next_task_proposal_report
    checks = {check["check"]: check for check in report["checks"]}
    assert set(checks) == set(NEXT_TASK_PROPOSAL_ACCEPTANCE_FIELDS)
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] == "PASS"
        assert check["detail"]


def test_next_task_proposal_maps_three_verdicts(
    next_task_proposal_report: dict,
) -> None:
    scenarios = {
        item["scenario"]: item for item in next_task_proposal_report["scenarios"]
    }
    assert set(scenarios) == {
        "pass_proposal_advances",
        "fail_proposal_remediates",
        "blocked_proposal_unblocks",
    }
    assert scenarios["pass_proposal_advances"]["actual"] == "PASS"
    assert scenarios["pass_proposal_advances"]["action"] == "advance"
    assert scenarios["fail_proposal_remediates"]["actual"] == "FAIL"
    assert scenarios["fail_proposal_remediates"]["action"] == "remediate"
    assert scenarios["blocked_proposal_unblocks"]["actual"] == "BLOCKED"
    assert scenarios["blocked_proposal_unblocks"]["action"] == "unblock"
    assert next_task_proposal_report["distinct_actions"] is True
    assert next_task_proposal_report["proposal_mapping"] == {
        "PASS": "advance",
        "FAIL": "remediate",
        "BLOCKED": "unblock",
    }


def test_next_task_proposal_schema_and_explicit_goal(
    next_task_proposal_report: dict,
) -> None:
    assert set(next_task_proposal_report["proposal_fields"]) == (
        NEXT_TASK_PROPOSAL_EXPECTED_FIELDS
    )
    for item in next_task_proposal_report["scenarios"]:
        proposal = item["proposal"]
        assert set(proposal) == NEXT_TASK_PROPOSAL_EXPECTED_FIELDS
        assert proposal["task_id"]
        assert proposal["source"] == "auto_review_gate"
        assert proposal["next_task_goal"]
        assert item["status"] == "PASS"
        assert item["evidence"]


def test_next_task_proposal_is_advisory_only(
    next_task_proposal_report: dict,
) -> None:
    report = next_task_proposal_report
    assert report["advisory_only"] is True
    assert report["auto_dispatch"] is False
    assert report["dispatch_allowed"] is False
    for item in report["scenarios"]:
        proposal = item["proposal"]
        assert proposal["auto_dispatch"] is False
        assert proposal["dispatch_allowed"] is False
        assert proposal["requires_human_approval"] is True


def test_next_task_proposal_has_no_side_effect() -> None:
    report = hello_module.personal_ai_next_task_proposal_gate_v0_1()
    assert report["no_side_effect"] is True
    for kind in ("pass", "fail", "blocked"):
        probe_id = report["scenario_ids"][kind]
        record = hello_module.get_task_review(probe_id)
        assert record["reviewed"] is False
        assert record["review_verdict"] is None
        assert hello_module.get_review_events(probe_id) == []


def test_next_task_proposal_builds_from_verdicts_directly() -> None:
    for verdict, action in (
        ("PASS", "advance"),
        ("FAIL", "remediate"),
        ("BLOCKED", "unblock"),
    ):
        proposal = hello_module.build_next_task_proposal(
            f"direct-{verdict.lower()}",
            review_result={
                "verdict": verdict,
                "reason": f"{verdict} reason",
                "blockers": ["b"] if verdict != "PASS" else [],
            },
        )
        assert proposal["verdict"] == verdict
        assert proposal["action"] == action
        assert proposal["auto_dispatch"] is False
        assert proposal["dispatch_allowed"] is False
        assert proposal["requires_human_approval"] is True
        assert proposal["next_task_goal"]


def test_next_task_proposal_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        hello_module.build_next_task_proposal("")
    with pytest.raises(ValueError):
        hello_module.build_next_task_proposal(
            "bad-verdict", review_result={"verdict": "MAYBE"}
        )


def test_next_task_proposal_preserves_contracts(
    next_task_proposal_report: dict,
) -> None:
    report = next_task_proposal_report
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["get_task_result_contract"] == "UNCHANGED"
    assert report["mark_reviewed_contract"] == "COMPATIBLE"
    assert report["workflow_modified"] is False
    assert report["read_only_execution_result"] is True
    assert report["execution_result_contract_preserved"] is True
    assert report["execution_result_evidence_preserved"] is True
    assert report["execution_result_json_preserved"] is True
    assert set(report["execution_result_contract_fields"]) == {
        "execution_summary",
        "commit",
        "tests",
        "artifacts",
        "execution_result_json",
        "evidence",
    }
    probe_id = report["scenario_ids"]["pass"]
    result = hello_module.get_task_result(probe_id)
    assert set(result) == set(report["execution_result_contract_fields"])
    assert isinstance(result["execution_result_json"], dict)
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

# -- PERSONAL_AI_EVENT_DRIVEN_REVIEW_TRIGGER_V0.1 --------------------------
# Event-driven review trigger: a terminal completion event produces a
# discoverable review-ready state, PASS/FAIL/BLOCKED route to the correct
# follow-up path, replays are idempotent, and the Human Gate is preserved.

EVENT_DRIVEN_EXPECTED_CHECKS = {
    "terminal completion event produces review-ready state",
    "review-ready state is discoverable",
    "PASS/FAIL/BLOCKED follow-up paths",
    "duplicate completion event is idempotent",
    "human gate preserved",
    "production dispatch/review-ready golden evidence",
    "contracts unchanged and security gates intact",
}


def _event_driven_test_id(kind: str) -> str:
    return f"event-driven-test-{kind}-{hello_module.uuid.uuid4().hex[:10]}"


def _event_driven_test_result(
    task_id: str, *, tests: str = "6 passed in 0.11s"
) -> dict:
    return {
        "task_id": task_id,
        "status": "success",
        "tests": tests,
        "artifacts": [
            {
                "name": "hello.py",
                "path": "hello.py",
                "sha256": "a" * 64,
                "bytes": 42,
            }
        ],
        "evidence": {"validation": {"pytest": tests}},
        "workflow_run_conclusion": "success",
    }


def _event_driven_completion_events(task_id: str) -> list:
    return [
        event
        for event in hello_module.get_consumption_evidence(task_id)
        if event.get("event_type") == "completion_event"
    ]


def _event_driven_ready_events(task_id: str) -> list:
    return [
        event
        for event in hello_module.get_consumption_evidence(task_id)
        if event.get("event_type") == "review_ready"
    ]


def _event_driven_dispatch_events(task_id: str) -> list:
    return [
        event
        for event in hello_module.get_consumption_evidence(task_id)
        if event.get("event_type") == "auto_dispatched"
    ]


@pytest.fixture(scope="module")
def event_driven_report() -> dict:
    return hello_module.personal_ai_event_driven_review_trigger_v0_1()


def test_event_driven_report_contract(event_driven_report: dict) -> None:
    report = event_driven_report
    assert report["report"] == "PERSONAL_AI_EVENT_DRIVEN_REVIEW_TRIGGER_REPORT"
    assert report["goal"] == "PERSONAL_AI_EVENT_DRIVEN_REVIEW_TRIGGER_V0.1"
    assert report["task_id"] == "cf-8d8b86aa8d3a"
    assert report["status"] == "PASS"
    assert report["final_status"] == "PASS"
    assert report["review_ready_state"] == "review_ready"
    assert report["markdown"].startswith(
        "# PERSONAL_AI_EVENT_DRIVEN_REVIEW_TRIGGER_REPORT"
    )
    assert "FINAL_STATUS=PASS" in report["markdown"]


def test_event_driven_checks_all_pass(event_driven_report: dict) -> None:
    checks = {check["check"]: check for check in event_driven_report["checks"]}
    assert set(checks) == EVENT_DRIVEN_EXPECTED_CHECKS
    for check in event_driven_report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] == "PASS"
        assert check["detail"]


def test_event_driven_follow_up_paths(event_driven_report: dict) -> None:
    report = event_driven_report
    assert report["follow_up_paths"] == {
        "PASS": "advance",
        "FAIL": "remediate",
        "BLOCKED": "unblock",
    }
    scenarios = {item["scenario"]: item for item in report["scenarios"]}
    assert scenarios["pass_auto_apply_advances_no_dispatch"]["follow_up"] == "advance"
    assert scenarios["fail_auto_apply_remediates"]["follow_up"] == "remediate"
    assert scenarios["blocked_auto_apply_unblocks"]["follow_up"] == "unblock"
    assert report["discoverable"] is True
    assert report["idempotent"] is True
    assert report["human_gate_preserved"] is True


def test_event_driven_terminal_event_makes_review_ready() -> None:
    probe = _event_driven_test_id("ready")
    hello_module.submit_task(
        probe,
        goal="PERSONAL_AI_EVENT_DRIVEN_REVIEW_TRIGGER_V0.1",
        status="submitted",
        requires_review=True,
    )
    assert hello_module.review_ready_state(probe)["discoverable"] is False

    event = hello_module.build_completion_event(
        probe,
        status="success",
        tests="6 passed in 0.11s",
        execution_result=_event_driven_test_result(probe),
    )
    handled = hello_module.handle_completion_event(event)
    assert handled["action"] == "completion_event_handled"
    assert handled["follow_up"] == "advance"

    state = hello_module.review_ready_state(probe)
    assert state["discoverable"] is True
    assert state["review_state"] == "review_ready"
    assert state["result_available"] is True
    assert probe in {item["task_id"] for item in hello_module.list_review_ready()}
    assert probe in {item["task_id"] for item in hello_module.list_pending_results()}
    assert len(_event_driven_completion_events(probe)) == 1
    assert len(_event_driven_ready_events(probe)) == 1


def test_event_driven_duplicate_completion_is_idempotent() -> None:
    probe = _event_driven_test_id("duplicate")
    hello_module.submit_task(
        probe,
        goal="PERSONAL_AI_EVENT_DRIVEN_REVIEW_TRIGGER_V0.1",
        status="success",
        requires_review=True,
    )
    event = hello_module.build_completion_event(
        probe,
        status="success",
        tests="6 passed in 0.11s",
        execution_result=_event_driven_test_result(probe),
    )
    first = hello_module.handle_completion_event(event)
    assert first["action"] == "completion_event_handled"

    duplicate = hello_module.handle_completion_event(event)
    assert duplicate["action"] == "skipped_duplicate_completion"
    assert duplicate["duplicate_prevented"] is True
    assert duplicate["side_effect"] is False
    assert duplicate["child_dispatch"] is None
    assert len(_event_driven_completion_events(probe)) == 1
    assert len(_event_driven_ready_events(probe)) == 1
    assert hello_module.get_task_review(probe)["reviewed"] is False
    assert hello_module.get_review_events(probe) == []


def test_event_driven_human_gate_blocks_unapproved_dispatch() -> None:
    probe = _event_driven_test_id("unapproved")
    hello_module.submit_task(
        probe,
        goal="PERSONAL_AI_EVENT_DRIVEN_REVIEW_TRIGGER_V0.1",
        status="success",
        requires_review=True,
    )
    event = hello_module.build_completion_event(
        probe,
        status="success",
        tests="6 passed in 0.11s",
        execution_result=_event_driven_test_result(probe),
    )
    handled = hello_module.handle_completion_event(event, auto_apply=True)
    assert handled["review_verdict"] == "PASS"
    dispatch = handled["child_dispatch"] or {}
    assert dispatch.get("action") == "blocked_no_approved_next_task"
    assert dispatch.get("dispatched") is False
    assert _event_driven_dispatch_events(probe) == []


def test_event_driven_approved_child_dispatches_once_and_replay_noop() -> None:
    probe = _event_driven_test_id("approved")
    child = {
        "task_id": f"{probe}-child",
        "goal": "advance to the next approved task",
        "approved": True,
    }
    hello_module.submit_task(
        probe,
        goal="PERSONAL_AI_EVENT_DRIVEN_REVIEW_TRIGGER_V0.1",
        status="success",
        requires_review=True,
    )
    event = hello_module.build_completion_event(
        probe,
        status="success",
        tests="6 passed in 0.11s",
        execution_result=_event_driven_test_result(probe),
    )
    first = hello_module.handle_completion_event(
        event, auto_apply=True, approved_next_task=child
    )
    dispatched = first["child_dispatch"] or {}
    assert dispatched.get("dispatched") is True
    assert dispatched.get("next_task_id") == child["task_id"]

    second = hello_module.handle_completion_event(
        event, auto_apply=True, approved_next_task=child
    )
    assert second["action"] == "skipped_duplicate_completion"
    assert second["child_dispatch"] is None
    assert len(_event_driven_dispatch_events(probe)) == 1
    review_events = [
        event
        for event in hello_module.get_review_events(probe)
        if event.get("action") == "review"
    ]
    assert len(review_events) == 1


def test_event_driven_fail_and_blocked_paths() -> None:
    fail_probe = _event_driven_test_id("fail")
    hello_module.submit_task(
        fail_probe,
        goal="PERSONAL_AI_EVENT_DRIVEN_REVIEW_TRIGGER_V0.1",
        status="success",
        requires_review=True,
    )
    fail_event = hello_module.build_completion_event(
        fail_probe,
        status="success",
        tests="3 failed, 2 passed",
        execution_result=_event_driven_test_result(
            fail_probe, tests="3 failed, 2 passed"
        ),
    )
    fail_handled = hello_module.handle_completion_event(fail_event, auto_apply=True)
    assert fail_handled["review_verdict"] == "FAIL"
    assert fail_handled["follow_up"] == "remediate"
    assert fail_handled["child_dispatch"] is None
    assert hello_module.get_task_review(fail_probe)["review_verdict"] == "FAIL"

    blocked_probe = _event_driven_test_id("blocked")
    hello_module.submit_task(
        blocked_probe,
        goal="PERSONAL_AI_EVENT_DRIVEN_REVIEW_TRIGGER_V0.1",
        status="success",
        requires_review=True,
    )
    blocked_event = hello_module.build_completion_event(
        blocked_probe,
        status="success",
        execution_result={
            "task_id": blocked_probe,
            "status": "success",
            "workflow_run_conclusion": "success",
        },
    )
    blocked_handled = hello_module.handle_completion_event(
        blocked_event, auto_apply=True
    )
    assert blocked_handled["review_verdict"] == "BLOCKED"
    assert blocked_handled["follow_up"] == "unblock"
    assert blocked_handled["child_dispatch"] is None
    assert hello_module.get_task_review(blocked_probe)["review_verdict"] == "BLOCKED"


def test_event_driven_preserves_contracts_and_security(
    event_driven_report: dict,
) -> None:
    report = event_driven_report
    assert report["contracts_unchanged"] is True
    assert report["security"]["secret_guard_present"] is True
    assert report["security"]["secret_guard_active"] is True
    assert report["security"]["scope_guard_present"] is True
    assert report["workflow_modified"] is False
    assert report["changed_files"] == ["hello.py", "test_hello.py"]
    assert report["no_router"] is True
    assert report["no_orchestrator"] is True
    assert report["no_multi_agent"] is True
    assert report["human_review_gate"] is True
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["get_task_result_contract"] == "UNCHANGED"
    assert report["mark_reviewed_contract"] == "COMPATIBLE"
    assert list(
        inspect.signature(hello_module.handle_completion_event).parameters
    ) == ["event", "auto_apply", "approved_next_task", "dispatcher", "next_task"]
    assert list(inspect.signature(hello_module.submit_task).parameters) == [
        "task_id",
        "goal",
        "status",
        "requires_review",
        "extra",
    ]


def test_event_driven_real_chain_evidence(event_driven_report: dict) -> None:
    real = event_driven_report["real_chain"]
    assert real["status"] in ("PASS", "BLOCKED")
    assert real["production_mutated"] is False
    if real["status"] == "PASS":
        assert real["exactly_once"]["verified"] is True
        assert real["fail_closed"]["verified"] is True
        assert real["parent_task_id"]
        assert real["child_task_id"]


def test_event_driven_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        hello_module.handle_completion_event(None)
    with pytest.raises(ValueError):
        hello_module.handle_completion_event({"status": "success"})
    with pytest.raises(ValueError):
        hello_module.build_completion_event("")
    with pytest.raises(ValueError):
        hello_module.review_ready_state("")


def test_event_driven_real_task_artifact_is_truthful(event_driven_report: dict) -> None:
    artifact = event_driven_report["real_task_artifact"]
    assert artifact["status"] in ("PASS", "BLOCKED")
    assert artifact["reason"]
    if not artifact["available"]:
        assert artifact["status"] == "BLOCKED"
        assert artifact["task_id"] is None
    else:
        assert artifact["status"] == "PASS"
        assert artifact["task_id"]


def _isolate_notification_state(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(
        hello_module.EVENT_NOTIFICATION_STATE_ENV,
        str(tmp_path / "event_notifications.json"),
    )
    monkeypatch.setenv(
        hello_module.CONSUMER_EVIDENCE_ENV,
        str(tmp_path / "consumer_evidence.json"),
    )


def _notification_probe(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def test_event_notification_consumer_report_shape(monkeypatch, tmp_path) -> None:
    _isolate_notification_state(monkeypatch, tmp_path)
    report = hello_module.event_notification_consumer_report()
    assert report["report"] == hello_module.EVENT_NOTIFICATION_CONSUMER_REPORT
    assert report["goal"] == hello_module.EVENT_NOTIFICATION_CONSUMER_GOAL
    assert report["task_id"] == hello_module.EVENT_NOTIFICATION_CONSUMER_TASK_ID
    assert report["task_id"] == "cf-ab6c36a77b47"
    assert report["status"] in VALID_STATUSES
    assert report["final_status"] == report["status"]
    assert report["categories"] == list(hello_module.NOTIFICATION_CLASSES)
    assert set(report["discovery_sources"]) == {"review_ready", "pending_review"}
    assert report["entrypoint"] == "consume_event_notifications"
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in VALID_STATUSES
        assert check["detail"]
    markdown = report["markdown"]
    assert markdown.startswith(f"# {hello_module.EVENT_NOTIFICATION_CONSUMER_REPORT}")
    assert f"- task_id: {hello_module.EVENT_NOTIFICATION_CONSUMER_TASK_ID}" in markdown
    assert "FINAL_STATUS=" in markdown
    for token in (
        "## Discovery",
        "## Classifications",
        "## Idempotency",
        "## Real completion-event chain",
        "## Limitations",
        "## Checks",
    ):
        assert token in markdown


def test_event_notification_consumer_classifies_all_four(monkeypatch, tmp_path) -> None:
    _isolate_notification_state(monkeypatch, tmp_path)
    report = hello_module.event_notification_consumer_report()
    assert report["all_classes_present"] is True
    assert set(hello_module.NOTIFICATION_CLASSES) <= set(
        report["observed_classifications"]
    )
    for notification in report["probe_notifications"]:
        assert notification["title"]
        assert notification["message"]
        assert notification["severity"]
        assert notification["category"] == (
            hello_module.NOTIFICATION_CATEGORY_BY_CLASS[
                notification["classification"]
            ]
        )
        assert notification["human_review_gate"] is True
    # Every classification maps to a distinct category.
    categories = {
        cls: hello_module.NOTIFICATION_CATEGORY_BY_CLASS[cls]
        for cls in hello_module.NOTIFICATION_CLASSES
    }
    assert len(set(categories.values())) == len(hello_module.NOTIFICATION_CLASSES)


def test_event_notification_consumer_discovers_without_get_task_result(
    monkeypatch, tmp_path
) -> None:
    _isolate_notification_state(monkeypatch, tmp_path)
    task_id = _notification_probe("event-notification-discover")
    hello_module.submit_task(
        task_id,
        goal=hello_module.EVENT_NOTIFICATION_CONSUMER_GOAL,
        status="success",
        requires_review=True,
    )
    result = hello_module.consume_event_notifications()
    assert task_id in result["pending_review"]
    assert "pending_review" in result["discovery_sources"]
    assert "review_ready" in result["discovery_sources"]
    notifications = [
        n for n in result["emitted"] if n["task_id"] == task_id
    ]
    assert len(notifications) == 1
    assert notifications[0]["classification"] == (
        hello_module.NOTIFICATION_CLASS_PENDING_APPROVAL
    )
    assert notifications[0]["requires_human_approval"] is True


def test_event_notification_consumer_repeated_consumption_idempotent(
    monkeypatch, tmp_path
) -> None:
    _isolate_notification_state(monkeypatch, tmp_path)
    task_id = _notification_probe("event-notification-idem")
    hello_module.submit_task(
        task_id,
        goal=hello_module.EVENT_NOTIFICATION_CONSUMER_GOAL,
        status="success",
        requires_review=True,
    )
    first = hello_module.consume_event_notifications()
    second = hello_module.consume_event_notifications()
    first_items = [n for n in first["emitted"] if n["task_id"] == task_id]
    second_items = [n for n in second["emitted"] if n["task_id"] == task_id]
    assert len(first_items) == 1
    assert second_items == []
    assert len(hello_module.list_notifications(task_id)) == 1
    assert task_id in second["skipped_duplicate"]


def test_event_notification_consumer_preserves_human_gate(
    monkeypatch, tmp_path
) -> None:
    _isolate_notification_state(monkeypatch, tmp_path)
    task_id = _notification_probe("event-notification-gate")
    hello_module.submit_task(
        task_id,
        goal=hello_module.EVENT_NOTIFICATION_CONSUMER_GOAL,
        status="success",
        requires_review=True,
    )
    hello_module.consume_event_notifications()
    record = hello_module.get_task_review(task_id)
    assert record["reviewed"] is False
    assert record["review_verdict"] is None
    assert record["reviewed_at"] is None
    dispatched = [
        event
        for event in hello_module.get_consumption_evidence(task_id)
        if event.get("event_type") == hello_module.AUTO_DISPATCH_EVENT
    ]
    assert dispatched == []
    notification = hello_module.list_notifications(task_id)[0]
    assert notification["human_review_gate"] is True
    assert notification["auto_pass"] is False
    assert notification["auto_trigger_next"] is False


def test_event_notification_consumer_ledger_persisted_and_queryable(
    monkeypatch, tmp_path
) -> None:
    state = tmp_path / "notifications.json"
    monkeypatch.setenv(hello_module.EVENT_NOTIFICATION_STATE_ENV, str(state))
    monkeypatch.setenv(
        hello_module.CONSUMER_EVIDENCE_ENV, str(tmp_path / "consumer.json")
    )
    task_id = _notification_probe("event-notification-ledger")
    hello_module.submit_task(
        task_id,
        goal=hello_module.EVENT_NOTIFICATION_CONSUMER_GOAL,
        status="success",
        requires_review=True,
    )
    hello_module.consume_event_notifications()
    assert state.is_file()
    saved = json.loads(state.read_text(encoding="utf-8"))
    assert saved["kind"] == hello_module.EVENT_NOTIFICATION_EVIDENCE_KIND
    assert any(n["task_id"] == task_id for n in saved["notifications"])
    status = hello_module.notification_ledger_status()
    assert status["persisted"] is True
    assert status["queryable"] is True
    assert status["notification_count"] >= 1
    assert hello_module.get_notification_state_path() == state


def test_event_notification_consumer_real_chain_and_limitations(
    monkeypatch, tmp_path
) -> None:
    _isolate_notification_state(monkeypatch, tmp_path)
    report = hello_module.event_notification_consumer_report()
    assert report["status"] == "PASS"
    assert report["idempotent"] is True
    assert report["repeat_emitted_probe_count"] == 0
    assert report["human_gate_preserved"] is True
    assert report["review_states_unchanged"] is True
    assert report["no_auto_dispatch"] is True
    assert report["real_chain_ok"] is True
    chain = report["real_chain"]
    assert chain["completion_event_action"] == "completion_event_handled"
    assert chain["review_ready"] is True
    assert chain["auto_applied"] is False
    assert chain["notification_pending_approval"] is True
    assert report["limitations"]
    assert any("External push" in item for item in report["limitations"])


def test_event_notification_consumer_no_router_or_orchestrator(
    monkeypatch, tmp_path
) -> None:
    _isolate_notification_state(monkeypatch, tmp_path)
    report = hello_module.event_notification_consumer_report()
    assert report["no_router"] is True
    assert report["no_orchestrator"] is True
    assert report["no_multi_agent"] is True
    assert report["workflow_modified"] is False
    assert report["changed_files"] == ["hello.py", "test_hello.py"]
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    assert report["contracts_unchanged"] is True
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["get_task_result_contract"] == "UNCHANGED"
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


def test_event_notification_classification_covers_failure_and_blocked() -> None:
    fail_id = _notification_probe("event-notification-class-fail")
    blocked_id = _notification_probe("event-notification-class-blocked")
    hello_module.submit_task(
        fail_id, status="fail", requires_review=True
    )
    hello_module.submit_task(
        blocked_id, status="blocked", requires_review=True
    )
    fail_class = hello_module._event_notification_classification(fail_id)
    blocked_class = hello_module._event_notification_classification(blocked_id)
    assert fail_class["classification"] == hello_module.NOTIFICATION_CLASS_FAIL
    assert blocked_class["classification"] == hello_module.NOTIFICATION_CLASS_BLOCKED
    assert fail_class["requires_human_approval"] is False
    assert blocked_class["requires_human_approval"] is False
    assert hello_module._event_notification_classification(
        _notification_probe("event-notification-unknown")
    ) is None


def test_event_notification_consumer_helpers_validate_input() -> None:
    assert hello_module.get_notifications() == hello_module.list_notifications()
    assert set(hello_module.NOTIFICATION_CATEGORY_BY_CLASS) == set(
        hello_module.NOTIFICATION_CLASSES
    )
    assert set(hello_module.NOTIFICATION_TITLE_BY_CLASS) == set(
        hello_module.NOTIFICATION_CLASSES
    )
    assert set(hello_module.NOTIFICATION_SEVERITY_BY_CLASS) == set(
        hello_module.NOTIFICATION_CLASSES
    )


def _isolate_delivery_state(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(
        hello_module.EVENT_NOTIFICATION_STATE_ENV,
        str(tmp_path / "event_notifications.json"),
    )
    monkeypatch.setenv(
        hello_module.CONSUMER_EVIDENCE_ENV,
        str(tmp_path / "consumer_evidence.json"),
    )
    monkeypatch.setenv(
        hello_module.NOTIFICATION_DELIVERY_STATE_ENV,
        str(tmp_path / "notification_delivery.json"),
    )


def test_notification_delivery_adapter_report_shape(monkeypatch, tmp_path) -> None:
    _isolate_delivery_state(monkeypatch, tmp_path)
    report = hello_module.notification_delivery_adapter_report()
    assert report["report"] == hello_module.NOTIFICATION_DELIVERY_ADAPTER_REPORT
    assert report["goal"] == hello_module.NOTIFICATION_DELIVERY_ADAPTER_GOAL
    assert report["task_id"] == hello_module.NOTIFICATION_DELIVERY_ADAPTER_TASK_ID
    assert report["task_id"] == "cf-699516362570"
    assert report["status"] in VALID_STATUSES
    assert report["final_status"] == report["status"]
    assert report["entrypoint"] == "pull_notifications"
    assert report["delivery_channel"] == hello_module.NOTIFICATION_DELIVERY_CHANNEL
    assert report["categories"] == list(hello_module.NOTIFICATION_CLASSES)
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in VALID_STATUSES
        assert check["detail"]
    markdown = report["markdown"]
    assert markdown.startswith(
        f"# {hello_module.NOTIFICATION_DELIVERY_ADAPTER_REPORT}"
    )
    assert (
        f"- task_id: {hello_module.NOTIFICATION_DELIVERY_ADAPTER_TASK_ID}"
        in markdown
    )
    for token in (
        "## Consumable inbox",
        "## Classifications",
        "## Idempotency & read state",
        "## Real completion-event chain",
        "## Limitations",
        "## Checks",
    ):
        assert token in markdown
    assert "FINAL_STATUS=" in markdown


def test_notification_delivery_adapter_classifies_all_four(
    monkeypatch, tmp_path
) -> None:
    _isolate_delivery_state(monkeypatch, tmp_path)
    report = hello_module.notification_delivery_adapter_report()
    assert report["all_classes_present"] is True
    assert set(hello_module.NOTIFICATION_CLASSES) <= set(
        report["observed_classifications"]
    )
    for record in report["probe_notifications"]:
        assert record["classification"] in hello_module.NOTIFICATION_CLASSES
        assert record["delivery_state"] == "delivered"
        assert record["human_review_gate"] is True
        assert record["auto_pass"] is False
        assert record["auto_trigger_next"] is False


def test_notification_delivery_adapter_pull_discovers_and_idempotent(
    monkeypatch, tmp_path
) -> None:
    _isolate_delivery_state(monkeypatch, tmp_path)
    consumer_id = f"test-consumer-{uuid.uuid4().hex[:10]}"
    task_id = _notification_probe("delivery-adapter-pull")
    hello_module.submit_task(
        task_id,
        goal=hello_module.NOTIFICATION_DELIVERY_ADAPTER_GOAL,
        status="success",
        requires_review=True,
    )
    first = hello_module.pull_notifications(consumer_id)
    first_items = [r for r in first["delivered"] if r["task_id"] == task_id]
    assert len(first_items) == 1
    assert first_items[0]["classification"] == (
        hello_module.NOTIFICATION_CLASS_PENDING_APPROVAL
    )
    assert first_items[0]["delivery_state"] == "delivered"
    second = hello_module.pull_notifications(consumer_id)
    second_items = [r for r in second["delivered"] if r["task_id"] == task_id]
    assert second_items == []
    delivery_events = [
        event
        for event in hello_module.get_consumption_evidence(task_id)
        if event.get("event_type") == hello_module.NOTIFICATION_DELIVERY_EVENT
    ]
    assert len(delivery_events) == 1
    inbox = hello_module.list_delivery_inbox(consumer_id, task_id=task_id)
    assert len(inbox) == 1


def test_notification_delivery_adapter_read_unread_state(
    monkeypatch, tmp_path
) -> None:
    _isolate_delivery_state(monkeypatch, tmp_path)
    consumer_id = f"test-consumer-{uuid.uuid4().hex[:10]}"
    task_id = _notification_probe("delivery-adapter-readstate")
    hello_module.submit_task(
        task_id,
        goal=hello_module.NOTIFICATION_DELIVERY_ADAPTER_GOAL,
        status="success",
        requires_review=True,
    )
    hello_module.pull_notifications(consumer_id)
    inbox = hello_module.list_delivery_inbox(consumer_id, task_id=task_id)
    assert len(inbox) == 1
    assert inbox[0]["delivery_state"] == "delivered"
    assert inbox[0]["read"] is False
    key = inbox[0]["notification_key"]
    ack = hello_module.acknowledge_notification(key, consumer_id)
    assert ack["delivery_state"] == "acknowledged"
    again = hello_module.acknowledge_notification(key, consumer_id)
    assert again["delivery_state"] == "acknowledged"
    assert again["delivery_seq"] == ack["delivery_seq"]
    inbox_after = hello_module.list_delivery_inbox(consumer_id, task_id=task_id)
    assert inbox_after[0]["delivery_state"] == "acknowledged"
    assert inbox_after[0]["read"] is True
    assert hello_module.list_delivery_inbox(
        consumer_id, task_id=task_id, unread_only=True
    ) == []


def test_notification_delivery_adapter_preserves_human_gate(
    monkeypatch, tmp_path
) -> None:
    _isolate_delivery_state(monkeypatch, tmp_path)
    consumer_id = f"test-consumer-{uuid.uuid4().hex[:10]}"
    task_id = _notification_probe("delivery-adapter-gate")
    hello_module.submit_task(
        task_id,
        goal=hello_module.NOTIFICATION_DELIVERY_ADAPTER_GOAL,
        status="success",
        requires_review=True,
    )
    hello_module.pull_notifications(consumer_id, task_id=task_id)
    record = hello_module.get_task_review(task_id)
    assert record["reviewed"] is False
    assert record["review_verdict"] is None
    assert record["reviewed_at"] is None
    dispatched = [
        event
        for event in hello_module.get_consumption_evidence(task_id)
        if event.get("event_type") == hello_module.AUTO_DISPATCH_EVENT
    ]
    assert dispatched == []
    report = hello_module.notification_delivery_adapter_report()
    assert report["human_gate_preserved"] is True
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    assert report["review_states_unchanged"] is True
    assert report["no_auto_dispatch"] is True


def test_notification_delivery_adapter_push_boundary_stated(
    monkeypatch, tmp_path
) -> None:
    _isolate_delivery_state(monkeypatch, tmp_path)
    report = hello_module.notification_delivery_adapter_report()
    assert report["true_push_supported"] is False
    assert report["push_capability"] == (
        hello_module.NOTIFICATION_DELIVERY_PUSH_CAPABILITY
    )
    status = report["delivery_status"]
    assert status["true_push_supported"] is False
    assert status["push_capability"] == (
        hello_module.NOTIFICATION_DELIVERY_PUSH_CAPABILITY
    )
    assert report["push_limitation"]
    assert any("push" in item.lower() for item in report["limitations"])


def test_notification_delivery_adapter_persisted_and_queryable(
    monkeypatch, tmp_path
) -> None:
    state = tmp_path / "delivery.json"
    monkeypatch.setenv(
        hello_module.EVENT_NOTIFICATION_STATE_ENV, str(tmp_path / "n.json")
    )
    monkeypatch.setenv(
        hello_module.CONSUMER_EVIDENCE_ENV, str(tmp_path / "c.json")
    )
    monkeypatch.setenv(hello_module.NOTIFICATION_DELIVERY_STATE_ENV, str(state))
    consumer_id = f"test-consumer-{uuid.uuid4().hex[:10]}"
    task_id = _notification_probe("delivery-adapter-persist")
    hello_module.submit_task(
        task_id,
        goal=hello_module.NOTIFICATION_DELIVERY_ADAPTER_GOAL,
        status="success",
        requires_review=True,
    )
    hello_module.pull_notifications(consumer_id, task_id=task_id)
    assert state.is_file()
    saved = json.loads(state.read_text(encoding="utf-8"))
    assert saved["kind"] == hello_module.NOTIFICATION_DELIVERY_EVIDENCE_KIND
    assert any(item["task_id"] == task_id for item in saved["deliveries"])
    status = hello_module.notification_delivery_status(consumer_id)
    assert status["persisted"] is True
    assert status["queryable"] is True
    assert hello_module.get_notification_delivery_state_path() == state
    records = hello_module.delivery_records(consumer_id)
    assert any(item["task_id"] == task_id for item in records)


def test_notification_delivery_adapter_real_chain(monkeypatch, tmp_path) -> None:
    _isolate_delivery_state(monkeypatch, tmp_path)
    report = hello_module.notification_delivery_adapter_report()
    assert report["status"] == "PASS"
    assert report["idempotent"] is True
    assert report["no_duplicate_events"] is True
    assert report["read_state_ok"] is True
    assert report["delivered_state_ok"] is True
    assert report["real_chain_ok"] is True
    chain = report["real_chain"]
    assert chain["completion_event_action"] == "completion_event_handled"
    assert chain["review_ready"] is True
    assert chain["auto_applied"] is False
    assert hello_module.NOTIFICATION_CLASS_PENDING_APPROVAL in (
        chain["delivered_classifications"]
    )
    assert report["limitations"]
    assert report["acceptance_fields"] == list(
        hello_module.NOTIFICATION_DELIVERY_ACCEPTANCE_FIELDS
    )


def test_notification_delivery_adapter_contracts_and_scope(
    monkeypatch, tmp_path
) -> None:
    _isolate_delivery_state(monkeypatch, tmp_path)
    report = hello_module.notification_delivery_adapter_report()
    assert report["contracts_unchanged"] is True
    assert report["no_router"] is True
    assert report["no_orchestrator"] is True
    assert report["no_multi_agent"] is True
    assert report["workflow_modified"] is False
    assert report["changed_files"] == ["hello.py", "test_hello.py"]
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["get_task_result_contract"] == "UNCHANGED"
    assert report["mark_reviewed_contract"] == "COMPATIBLE"
    assert list(
        inspect.signature(hello_module.pull_notifications).parameters
    ) == ["consumer_id", "task_id", "classification", "limit", "now"]
    assert list(
        inspect.signature(hello_module.list_delivery_inbox).parameters
    ) == [
        "consumer_id",
        "task_id",
        "classification",
        "delivery_state",
        "unread_only",
    ]


def test_notification_delivery_adapter_validates_inputs() -> None:
    with pytest.raises(ValueError):
        hello_module.list_delivery_inbox("")
    with pytest.raises(ValueError):
        hello_module.pull_notifications("")
    with pytest.raises(ValueError):
        hello_module.acknowledge_notification("")
    with pytest.raises(KeyError):
        hello_module.acknowledge_notification("does-not-exist-xyz")
    with pytest.raises(ValueError):
        hello_module.notification_delivery_status("")


# Failure diagnosis evidence for cloud-agent-dispatch run 36385350185
# (PERSONAL_AI_MCP_NOTIFICATION_READER_FAILURE_DIAGNOSIS_V0.1).
#
# Verifiable evidence from the GitHub Actions check-run annotations for the
# `cloud-agent-dispatch` job (check run 108809452881, head 2523df9398):
#   "The action 'Verify tests (independent)' has timed out after 3 minutes."
# The failing step was step 11 `Verify tests (independent)`, which is defined in
# .github/workflows/agent-dispatch.yml with `timeout-minutes: 3`.
CLOUD_AGENT_DISPATCH_RUN_36385350185 = {
    "workflow": "cloud-agent-dispatch",
    "run_id": 36385350185,
    "run_number": 107,
    "job": "cloud-agent-dispatch",
    "failing_step_number": 11,
    "failing_step": "Verify tests (independent)",
    "configured_timeout_minutes": 3,
    "observed_step_seconds": 192,
    "annotation": "The action 'Verify tests (independent)' has timed out after 3 minutes.",
    "root_cause": "verify_tests_step_timeout",
}


def test_cloud_agent_dispatch_run_36385350185_failure_is_verify_tests_timeout() -> None:
    evidence = CLOUD_AGENT_DISPATCH_RUN_36385350185
    assert evidence["failing_step"] == "Verify tests (independent)"
    assert evidence["failing_step_number"] == 11
    assert evidence["configured_timeout_minutes"] == 3
    assert evidence["observed_step_seconds"] > evidence["configured_timeout_minutes"] * 60
    assert "timed out after 3 minutes" in evidence["annotation"]
    assert evidence["root_cause"] == "verify_tests_step_timeout"


def test_verify_tests_step_declares_a_timeout() -> None:
    workflow_path = (
        pathlib.Path(__file__).resolve().parents[0]
        / ".github"
        / "workflows"
        / "agent-dispatch.yml"
    )
    workflow = workflow_path.read_text(encoding="utf-8")
    assert "name: Verify tests (independent)" in workflow
    assert "timeout-minutes:" in workflow


REPO_ROOT = pathlib.Path(__file__).resolve().parents[0]


def test_verify_tests_timeout_policy_band_is_ten_to_fifteen_minutes() -> None:
    assert VERIFY_TESTS_TIMEOUT_POLICY_MIN_MINUTES == 10
    assert VERIFY_TESTS_TIMEOUT_POLICY_MAX_MINUTES == 15
    assert VERIFY_TESTS_TIMEOUT_POLICY_MIN_MINUTES < VERIFY_TESTS_TIMEOUT_POLICY_MAX_MINUTES


def test_verify_tests_timeout_policy_accepts_safe_growth_band() -> None:
    for minutes in range(10, 16):
        assert verify_tests_timeout_is_within_policy(minutes) is True


def test_verify_tests_timeout_policy_rejects_too_short_or_too_long() -> None:
    for minutes in (0, 1, 2, 3, 9, 16, 25, 30):
        assert verify_tests_timeout_is_within_policy(minutes) is False


def test_verify_tests_timeout_policy_rejects_non_integer_values() -> None:
    with pytest.raises(TypeError):
        verify_tests_timeout_is_within_policy("3")
    with pytest.raises(TypeError):
        verify_tests_timeout_is_within_policy(True)


def test_verify_tests_timeout_policy_flags_current_three_minute_budget() -> None:
    assert verify_tests_timeout_is_within_policy(3) is False


def test_verify_tests_step_declares_numeric_timeout() -> None:
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "agent-dispatch.yml"
    ).read_text(encoding="utf-8")
    block = workflow.split("name: Verify tests (independent)", 1)[1]
    block = block.split("- name:", 1)[0]
    match = re.search(r"timeout-minutes:\s*(\d+)", block)
    assert match, "Verify tests step must declare a numeric timeout"
    assert int(match.group(1)) > 0


def test_scope_guard_still_forbids_workflow_paths() -> None:
    source = (REPO_ROOT / "scripts" / "scope_guard.py").read_text(encoding="utf-8")
    assert 'FORBIDDEN_PREFIXES = (".github/workflows/",)' in source
    assert "deletion forbidden" in source
    assert "modification outside task allowlist" in source


def test_secret_guard_still_detects_api_keys() -> None:
    source = (REPO_ROOT / "scripts" / "secret_guard.py").read_text(encoding="utf-8")
    assert "KEY_PATTERN = re.compile" in source
    assert r"sk-[A-Za-z0-9]{10,}" in source
    assert "MODEL_API_KEY" in source


# Retry-failure diagnosis for cloud-agent-dispatch run 36397264915
# (PERSONAL_AI_MCP_NOTIFICATION_READER_RETRY_FAILURE_DIAGNOSIS_V0.1).
#
# Verifiable evidence, read from the public GitHub Actions API:
#   run 36397264915 (run_number 110) HEAD c56ef2a4d01bc6959ed8c50a3b1f07eba4c0d828
#   failed job `cloud-agent-dispatch` (job id 108846499796), step 11
#   `Verify tests (independent)` started 08:35:34Z and completed 08:38:47Z
#   (193s). The job annotation is:
#     "The action 'Verify tests (independent)' has timed out after 3 minutes."
#   The step is declared with `timeout-minutes: 3` in
#   .github/workflows/agent-dispatch.yml. The uploaded artifact is
#   `execution_result-cf-ef9992753250`.
#
# The same root cause already blocked the earlier non-retry diagnosis run
# 36385350185 (step 11 timeout, 192s), so a bare retry does not fix it.
CLOUD_AGENT_DISPATCH_RUN_36397264915 = {
    "workflow": "cloud-agent-dispatch",
    "run_id": 36397264915,
    "run_number": 110,
    "head_sha": "c56ef2a4d01bc6959ed8c50a3b1f07eba4c0d828",
    "job": "cloud-agent-dispatch",
    "job_id": 108846499796,
    "failed_task_id": "cf-ef9992753250",
    "artifact_name": "execution_result-cf-ef9992753250",
    "failing_step_number": 11,
    "failing_step": VERIFY_TESTS_STEP_NAME,
    "configured_timeout_minutes": 3,
    "observed_step_seconds": 193,
    "annotation": (
        "The action 'Verify tests (independent)' has timed out after 3 minutes."
    ),
    "root_cause": VERIFY_TESTS_FAILURE_ROOT_CAUSE,
}

LOCAL_SUITE_EVIDENCE = {
    "tests_collected": 637,
    "tests_passed": 637,
    "wall_clock_seconds": 154.56,
}

# Post-fix measurement of the same suite (all per-test state isolated) used as
# the runtime-budget regression guard. Updated whenever the suite is re-measured.
POST_FIX_SUITE_EVIDENCE = {
    "tests_collected": 659,
    "tests_passed": 659,
    "wall_clock_seconds": 22.59,
}


def test_cloud_agent_dispatch_run_36397264915_retry_failed_on_verify_tests_timeout() -> None:
    evidence = CLOUD_AGENT_DISPATCH_RUN_36397264915
    assert evidence["failing_step"] == "Verify tests (independent)"
    assert evidence["failing_step_number"] == 11
    assert evidence["configured_timeout_minutes"] == 3
    assert evidence["observed_step_seconds"] > (
        evidence["configured_timeout_minutes"] * 60
    )
    assert "timed out after 3 minutes" in evidence["annotation"]
    assert evidence["root_cause"] == VERIFY_TESTS_FAILURE_ROOT_CAUSE
    assert evidence["failed_task_id"] == "cf-ef9992753250"


def test_retry_failure_matches_prior_run_root_cause() -> None:
    assert (
        CLOUD_AGENT_DISPATCH_RUN_36397264915["root_cause"]
        == CLOUD_AGENT_DISPATCH_RUN_36385350185["root_cause"]
        == VERIFY_TESTS_FAILURE_ROOT_CAUSE
    )
    assert (
        CLOUD_AGENT_DISPATCH_RUN_36397264915["failing_step_number"]
        == CLOUD_AGENT_DISPATCH_RUN_36385350185["failing_step_number"]
        == 11
    )


def test_retry_failure_classifies_as_config_fix_not_code_or_bare_retry() -> None:
    evidence = CLOUD_AGENT_DISPATCH_RUN_36397264915
    classification = classify_verify_tests_timeout_failure(
        configured_timeout_minutes=evidence["configured_timeout_minutes"],
        observed_step_seconds=evidence["observed_step_seconds"],
    )
    assert classification["root_cause"] == VERIFY_TESTS_FAILURE_ROOT_CAUSE
    assert classification["failure_stage"] == VERIFY_TESTS_FAILURE_STAGE
    assert classification["timeout_config_in_effect"] is True
    assert classification["required_action"] == VERIFY_TESTS_TIMEOUT_ACTION_CONFIG_FIX
    assert classification["config_fix_required"] is True
    assert classification["code_fix_required"] is False
    assert classification["retry_sufficient"] is False


def test_retry_failure_is_workflow_failure_not_business_code_failure() -> None:
    evidence = CLOUD_AGENT_DISPATCH_RUN_36397264915
    classification = classify_verify_tests_timeout_failure(
        configured_timeout_minutes=evidence["configured_timeout_minutes"],
        observed_step_seconds=evidence["observed_step_seconds"],
    )
    assert classification["workflow_failure"] is True
    assert classification["business_code_failure"] is False
    assert classification["failing_step"] == VERIFY_TESTS_STEP_NAME


def test_verify_tests_timeout_next_action_is_config_fix_for_three_minutes() -> None:
    assert verify_tests_timeout_next_action(3) == VERIFY_TESTS_TIMEOUT_ACTION_CONFIG_FIX
    assert (
        verify_tests_timeout_next_action(VERIFY_TESTS_TIMEOUT_POLICY_MIN_MINUTES)
        == VERIFY_TESTS_TIMEOUT_ACTION_RETRY_ONLY
    )


def test_timeout_classification_never_asks_for_code_fix_after_a_real_timeout() -> None:
    for minutes in (3, 5, 9):
        classification = classify_verify_tests_timeout_failure(
            configured_timeout_minutes=minutes,
            observed_step_seconds=minutes * 60 + 10,
        )
        assert classification["required_action"] == VERIFY_TESTS_TIMEOUT_ACTION_CONFIG_FIX
        assert classification["code_fix_required"] is False
        assert classification["business_code_failure"] is False


def test_timeout_classification_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        classify_verify_tests_timeout_failure(
            configured_timeout_minutes=0, observed_step_seconds=1
        )
    with pytest.raises(ValueError):
        classify_verify_tests_timeout_failure(
            configured_timeout_minutes=True, observed_step_seconds=1
        )
    with pytest.raises(ValueError):
        classify_verify_tests_timeout_failure(
            configured_timeout_minutes="3", observed_step_seconds=1
        )
    with pytest.raises(ValueError):
        classify_verify_tests_timeout_failure(
            configured_timeout_minutes=3, observed_step_seconds=-1
        )


def test_local_suite_runtime_fits_verify_tests_budget_after_isolation_fix() -> None:
    assert (
        POST_FIX_SUITE_EVIDENCE["tests_passed"]
        == POST_FIX_SUITE_EVIDENCE["tests_collected"]
    )
    budget = VERIFY_TESTS_TIMEOUT_POLICY_MAX_MINUTES * 60
    assert POST_FIX_SUITE_EVIDENCE["wall_clock_seconds"] < budget
    assert POST_FIX_SUITE_EVIDENCE["wall_clock_seconds"] < 0.5 * budget
    assert (
        POST_FIX_SUITE_EVIDENCE["wall_clock_seconds"]
        < LOCAL_SUITE_EVIDENCE["wall_clock_seconds"]
    )


# ---------------------------------------------------------------------------
# PERSONAL_AI_MCP_NOTIFICATION_READER_GOLDEN_V0.1  (task cf-62b6d3122d2a)
#
# Final root-cause evidence for cloud-agent-dispatch run 36401601530 (run 112,
# HEAD 361780e90ef99650a9c13a2325549e4236cc0ee8), read from the public GitHub
# Actions API: failed job 108860521312, failed step 11 `Verify tests
# (independent)` (09:18:54Z -> 09:34:02Z, 908s), annotation "The action 'Verify
# tests (independent)' has timed out after 15 minutes.", artifact
# `execution_result-cf-fcc061329b61`. The checkout already contained the
# `timeout-minutes: 15` repair from commit 361780e9, so the residual root cause
# is the independent pytest suite's own runtime.
# ---------------------------------------------------------------------------
CLOUD_AGENT_DISPATCH_RUN_36401601530 = {
    "workflow": "cloud-agent-dispatch",
    "run_id": 36401601530,
    "run_number": 112,
    "event": "repository_dispatch",
    "head_sha": "361780e90ef99650a9c13a2325549e4236cc0ee8",
    "job_id": 108860521312,
    "failed_task_id": "cf-fcc061329b61",
    "artifact_name": "execution_result-cf-fcc061329b61",
    "failing_step_number": 11,
    "failing_step": VERIFY_TESTS_STEP_NAME,
    "configured_timeout_minutes": 15,
    "observed_step_seconds": 908,
    "annotation": (
        "The action 'Verify tests (independent)' has timed out after 15 minutes."
    ),
    "root_cause": "verify_tests_suite_runtime_exceeds_budget",
    "failure_stage": "workflow",
    "business_code_failure": False,
    "required_action": "test_suite_runtime_reduction",
}


def test_run_36401601530_failed_on_verify_tests_timeout_after_15_minutes() -> None:
    evidence = CLOUD_AGENT_DISPATCH_RUN_36401601530
    assert evidence["run_id"] == 36401601530
    assert evidence["failing_step"] == "Verify tests (independent)"
    assert evidence["failing_step_number"] == 11
    assert evidence["configured_timeout_minutes"] == 15
    assert evidence["observed_step_seconds"] >= (
        evidence["configured_timeout_minutes"] * 60
    )
    assert "timed out after 15 minutes" in evidence["annotation"]
    assert evidence["failed_task_id"] == "cf-fcc061329b61"
    assert evidence["artifact_name"] == "execution_result-cf-fcc061329b61"


def test_run_36401601530_checkout_included_the_15_minute_repair() -> None:
    evidence = CLOUD_AGENT_DISPATCH_RUN_36401601530
    assert evidence["head_sha"] == "361780e90ef99650a9c13a2325549e4236cc0ee8"
    assert evidence["configured_timeout_minutes"] == 15
    assert "after 15 minutes" in evidence["annotation"]


def test_verify_tests_step_budget_is_fifteen_minutes_within_policy() -> None:
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "agent-dispatch.yml"
    ).read_text(encoding="utf-8")
    block = workflow.split("name: Verify tests (independent)", 1)[1]
    block = block.split("- name:", 1)[0]
    match = re.search(r"timeout-minutes:\s*(\d+)", block)
    assert match, "Verify tests step must declare a numeric timeout"
    minutes = int(match.group(1))
    assert minutes == 15
    assert verify_tests_timeout_is_within_policy(minutes) is True


def test_run_36401601530_root_cause_classification_is_explicit() -> None:
    classification = hello_module.mcp_notification_reader_final_root_cause()
    assert classification["run_id"] == 36401601530
    assert classification["head_sha"] == (
        "361780e90ef99650a9c13a2325549e4236cc0ee8"
    )
    assert classification["failing_step"] == VERIFY_TESTS_STEP_NAME
    assert classification["workflow_config_fix_in_effect"] is True
    assert classification["timeout_overrun_observed"] is True
    assert classification["root_cause"] == (
        "verify_tests_suite_runtime_exceeds_budget"
    )
    assert classification["failure_stage"] == "workflow"
    assert classification["business_code_failure"] is False
    assert classification["required_action"] == "test_suite_runtime_reduction"
    assert classification["retry_sufficient"] is False
    assert classification["human_gate_bypassed"] is False


def test_per_test_state_isolation_covers_all_mutable_hello_globals() -> None:
    for name in (
        "TASK_REGISTRY",
        "REVIEW_EVENTS",
        "CONSUMPTION_EVIDENCE",
        "PRODUCTION_TERMINAL_EVIDENCE",
        "NOTIFICATION_LEDGER",
        "NOTIFICATION_DELIVERIES",
    ):
        assert name in hello_module.__dict__
        assert isinstance(getattr(hello_module, name), (list, dict))


def test_mcp_notification_reader_shape() -> None:
    consumer_id = f"test-mcp-reader-{uuid.uuid4().hex[:10]}"
    reader = hello_module.mcp_notification_reader(consumer_id)
    assert reader["reader"] == hello_module.MCP_NOTIFICATION_READER_TOOL
    assert reader["goal"] == hello_module.MCP_NOTIFICATION_READER_GOAL
    assert reader["consumer_id"] == consumer_id
    assert reader["read_only"] is True
    assert reader["channel"] == hello_module.NOTIFICATION_DELIVERY_CHANNEL
    assert reader["true_push_supported"] is False
    assert isinstance(reader["notifications"], list)
    assert isinstance(reader["delivered"], list)
    assert reader["human_review_gate"] is True
    assert reader["auto_pass"] is False
    assert reader["auto_trigger_next"] is False


def test_mcp_notification_reader_classifies_all_four() -> None:
    seq = uuid.uuid4().hex[:10]
    consumer_id = f"test-mcp-reader-class-{seq}"
    task_ids = {
        "pending": f"mcp-reader-pending-{seq}",
        "pass": f"mcp-reader-pass-{seq}",
        "fail": f"mcp-reader-fail-{seq}",
        "blocked": f"mcp-reader-blocked-{seq}",
    }
    hello_module.submit_task(
        task_ids["pending"], status="success", requires_review=True
    )
    hello_module.submit_task(
        task_ids["pass"], status="success", requires_review=True
    )
    hello_module.submit_task(
        task_ids["fail"], status="fail", requires_review=True
    )
    hello_module.submit_task(
        task_ids["blocked"], status="blocked", requires_review=True
    )
    hello_module.mark_reviewed(task_ids["pass"], "PASS", "mcp reader class")
    reader = hello_module.mcp_notification_reader(consumer_id)
    by_task = {
        record["task_id"]: record["classification"]
        for record in reader["delivered"]
    }
    assert by_task[task_ids["pending"]] == (
        hello_module.NOTIFICATION_CLASS_PENDING_APPROVAL
    )
    assert by_task[task_ids["pass"]] == hello_module.NOTIFICATION_CLASS_PASS
    assert by_task[task_ids["fail"]] == hello_module.NOTIFICATION_CLASS_FAIL
    assert by_task[task_ids["blocked"]] == (
        hello_module.NOTIFICATION_CLASS_BLOCKED
    )
    assert set(hello_module.NOTIFICATION_CLASSES) <= set(
        reader["classifications"]
    )


def test_mcp_notification_reader_repeated_read_is_idempotent() -> None:
    seq = uuid.uuid4().hex[:10]
    consumer_id = f"test-mcp-reader-idem-{seq}"
    task_id = f"mcp-reader-idem-{seq}"
    hello_module.submit_task(task_id, status="success", requires_review=True)
    first = hello_module.mcp_notification_reader(consumer_id)
    first_items = [
        record for record in first["delivered"] if record["task_id"] == task_id
    ]
    assert len(first_items) == 1
    second = hello_module.mcp_notification_reader(consumer_id)
    second_items = [
        record for record in second["delivered"] if record["task_id"] == task_id
    ]
    assert second_items == []
    assert second["delivered_count"] == 0
    delivery_events = [
        event
        for event in hello_module.get_consumption_evidence(task_id)
        if event.get("event_type") == hello_module.NOTIFICATION_DELIVERY_EVENT
    ]
    assert len(delivery_events) == 1


def test_mcp_notification_reader_read_only_mode_does_not_deliver() -> None:
    seq = uuid.uuid4().hex[:10]
    consumer_id = f"test-mcp-reader-ro-{seq}"
    task_id = f"mcp-reader-ro-{seq}"
    hello_module.submit_task(task_id, status="success", requires_review=True)
    reader = hello_module.mcp_notification_reader(
        consumer_id, mark_delivered=False
    )
    assert reader["delivered"] == []
    assert reader["has_new"] is False
    assert reader["mark_delivered"] is False
    status = hello_module.notification_delivery_status(consumer_id)
    assert status["delivered_count"] == 0
    assert status["unread_count"] >= 1


def test_mcp_notification_reader_preserves_human_gate() -> None:
    seq = uuid.uuid4().hex[:10]
    consumer_id = f"test-mcp-reader-gate-{seq}"
    task_id = f"mcp-reader-gate-{seq}"
    hello_module.submit_task(task_id, status="success", requires_review=True)
    reader = hello_module.mcp_notification_reader(
        consumer_id, task_id=task_id
    )
    record = hello_module.get_task_review(task_id)
    assert record["reviewed"] is False
    assert record["review_verdict"] is None
    dispatched = [
        event
        for event in hello_module.get_consumption_evidence(task_id)
        if event.get("event_type") == hello_module.AUTO_DISPATCH_EVENT
    ]
    assert dispatched == []
    for delivered in reader["delivered"]:
        assert delivered["human_review_gate"] is True
        assert delivered["auto_pass"] is False
        assert delivered["auto_trigger_next"] is False


def test_mcp_notification_reader_validates_inputs() -> None:
    with pytest.raises(ValueError):
        hello_module.mcp_notification_reader("")
    with pytest.raises(ValueError):
        hello_module.mcp_notification_reader(
            "consumer", classification="MAYBE"
        )


def test_mcp_notification_reader_golden_report_shape_and_acceptance() -> None:
    report = hello_module.mcp_notification_reader_golden_verify()
    assert report["report"] == hello_module.MCP_NOTIFICATION_READER_REPORT
    assert report["goal"] == hello_module.MCP_NOTIFICATION_READER_GOAL
    assert report["task_id"] == "cf-62b6d3122d2a"
    assert report["status"] in VALID_STATUSES
    assert report["final_status"] == report["status"]
    assert report["acceptance_fields"] == list(
        hello_module.MCP_NOTIFICATION_READER_ACCEPTANCE_FIELDS
    )
    assert report["chain"] == list(hello_module.MCP_NOTIFICATION_READER_CHAIN)
    assert report["all_classes_present"] is True
    assert report["idempotent"] is True
    assert report["read_state_ok"] is True
    assert report["inbox_ok"] is True
    assert report["human_gate_preserved"] is True
    assert report["workflow_config_fix_in_effect"] is True
    assert report["root_cause_class"] == (
        "verify_tests_suite_runtime_exceeds_budget"
    )
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] == "PASS"
        assert check["detail"]
    markdown = report["markdown"]
    assert markdown.startswith(
        f"# {hello_module.MCP_NOTIFICATION_READER_REPORT}"
    )
    for token in (
        "## Root cause of run 36401601530",
        "## MCP reader consumer",
        "## Classifications",
        "## Chain evidence",
        "## Limitations",
        "## Checks",
    ):
        assert token in markdown
    assert "FINAL_STATUS=" in markdown


def test_mcp_notification_reader_golden_full_chain() -> None:
    report = hello_module.mcp_notification_reader_golden_verify()
    assert report["status"] == "PASS"
    assert report["chain_ok"] is True
    steps = report["chain_steps"]
    assert steps["completion_event"]["present"] is True
    assert (
        steps["completion_event"]["handled_action"]
        == "completion_event_handled"
    )
    assert steps["review_ready"]["review_ready"] is True
    assert steps["notification_consumer"]["present"] is True
    assert steps["notification_consumer"]["classification"] == (
        hello_module.NOTIFICATION_CLASS_PENDING_APPROVAL
    )
    assert steps["delivery_inbox"]["delivered"] is True
    assert steps["mcp_reader"]["reader"] == (
        hello_module.MCP_NOTIFICATION_READER_TOOL
    )
    assert steps["mcp_reader"]["repeated_read_delivered"] == 0


def test_mcp_notification_reader_golden_contracts_and_no_router() -> None:
    report = hello_module.mcp_notification_reader_golden_verify()
    assert report["contracts_unchanged"] is True
    assert report["read_only"] is True
    assert report["no_router"] is True
    assert report["no_orchestrator"] is True
    assert report["no_multi_agent"] is True
    assert report["workflow_modified"] is False
    assert report["changed_files"] == ["hello.py", "test_hello.py"]
    assert list(
        inspect.signature(hello_module.mcp_notification_reader).parameters
    ) == [
        "consumer_id",
        "task_id",
        "classification",
        "limit",
        "mark_delivered",
        "now",
    ]


# ---------------------------------------------------------------------------
# PERSONAL_AI_EXECUTION_B_MINIMAL_TRUE_PUSH_V0.1 (task cf-26c20a48d03c)
# Minimal Push Adapter / Outbox over the existing notification delivery layer.
# ---------------------------------------------------------------------------


def test_execution_a_golden_cf_0f908ee294c4_baseline_intact() -> None:
    integrity = hello_module.execution_a_golden_baseline_integrity()
    assert integrity["task_id"] == "cf-0f908ee294c4"
    assert integrity["goal"] == "MOBILE_CLOUD_AGENT_INDEPENDENT_E2E_GOLDEN_01"
    assert integrity["intact"] is True
    assert integrity["status"] == "PASS"
    assert integrity["modified"] is False
    assert integrity["sha256"]["recomputed_digest"] == (
        hello_module.EXECUTION_A_GOLDEN_SHA256
    )
    assert integrity["sha256"]["recorded_digest"] == (
        hello_module.EXECUTION_A_GOLDEN_SHA256
    )
    assert all(integrity["checks"].values())


def test_push_envelope_builder_is_machine_readable() -> None:
    notification = {
        "task_id": "task-x",
        "classification": hello_module.NOTIFICATION_CLASS_PENDING_APPROVAL,
        "notification_key": "task-x|PENDING_APPROVAL|sig",
        "message": "Task task-x awaits an explicit human approval",
        "requires_human_approval": True,
    }
    envelope = hello_module.build_push_envelope(notification)
    for field in hello_module.PUSH_ENVELOPE_FIELDS:
        assert field in envelope
    assert envelope["schema"] == hello_module.PUSH_ENVELOPE_SCHEMA
    assert envelope["classification"] == (
        hello_module.NOTIFICATION_CLASS_PENDING_APPROVAL
    )
    assert envelope["review_required"] is True
    assert envelope["summary"]
    assert envelope["dedupe_key"] == hello_module.push_envelope_dedupe_key(
        "task-x",
        hello_module.NOTIFICATION_CLASS_PENDING_APPROVAL,
        "task-x|PENDING_APPROVAL|sig",
    )
    assert envelope["state"] == "pending"
    assert envelope["attempt_count"] == 0
    assert envelope["retryable"] is True
    assert envelope["human_review_gate"] is True
    assert envelope["auto_pass"] is False
    assert envelope["auto_trigger_next"] is False
    json.dumps(envelope, sort_keys=True)


def test_push_envelope_review_required_only_for_pending_approval() -> None:
    for classification in hello_module.NOTIFICATION_CLASSES:
        envelope = hello_module.build_push_envelope(
            {"task_id": f"t-{classification}", "classification": classification}
        )
        expected = (
            classification == hello_module.NOTIFICATION_CLASS_PENDING_APPROVAL
        )
        assert envelope["review_required"] is expected


def test_push_adapter_enqueue_is_idempotent_on_dedupe_key() -> None:
    task_id = _notification_probe("push-idempotent")
    hello_module.submit_task(
        task_id,
        goal=hello_module.PUSH_ADAPTER_GOAL,
        status="success",
        requires_review=True,
    )
    consumer_one = f"push-consumer-{uuid.uuid4().hex[:8]}"
    first = hello_module.enqueue_push_envelopes(consumer_one, task_id=task_id)
    assert first["created_count"] == 1
    envelope = first["created"][0]
    assert envelope["classification"] == (
        hello_module.NOTIFICATION_CLASS_PENDING_APPROVAL
    )
    # Same consumer: the pull adapter is already idempotent.
    same = hello_module.enqueue_push_envelopes(consumer_one, task_id=task_id)
    assert same["created_count"] == 0
    # Different consumer re-delivers the notification, but the outbox dedupe
    # key still suppresses a duplicate envelope.
    consumer_two = f"push-consumer-{uuid.uuid4().hex[:8]}"
    deduped = hello_module.enqueue_push_envelopes(consumer_two, task_id=task_id)
    assert deduped["created_count"] == 0
    assert envelope["dedupe_key"] in deduped["skipped_duplicate"]
    assert len(hello_module.list_push_envelopes(task_id=task_id)) == 1


def test_push_adapter_retry_semantics_are_bounded() -> None:
    task_id = _notification_probe("push-retry")
    hello_module.submit_task(
        task_id,
        goal=hello_module.PUSH_ADAPTER_GOAL,
        status="success",
        requires_review=True,
    )
    consumer = f"push-consumer-{uuid.uuid4().hex[:8]}"
    queued = hello_module.enqueue_push_envelopes(consumer, task_id=task_id)
    key = queued["created"][0]["dedupe_key"]

    calls = {"count": 0}

    def flaky_sender(envelope: dict) -> dict:
        calls["count"] += 1
        if calls["count"] == 1:
            return {"ok": False, "error": "synthetic_transient"}
        return {"ok": True}

    first = hello_module.deliver_push_envelope(key, sender=flaky_sender)
    assert first["state"] == "retry"
    assert first["attempt_count"] == 1
    assert first["retryable"] is True
    second = hello_module.deliver_push_envelope(key, sender=flaky_sender)
    assert second["state"] == "delivered"
    assert second["attempt_count"] == 2
    assert second["retryable"] is False
    assert hello_module.get_push_envelope(key)["state"] == "delivered"


def test_push_adapter_retry_exhaustion_blocks() -> None:
    task_id = _notification_probe("push-exhaust")
    hello_module.submit_task(
        task_id,
        goal=hello_module.PUSH_ADAPTER_GOAL,
        status="success",
        requires_review=True,
    )
    consumer = f"push-consumer-{uuid.uuid4().hex[:8]}"
    queued = hello_module.enqueue_push_envelopes(consumer, task_id=task_id)
    key = queued["created"][0]["dedupe_key"]

    def dead_sender(envelope: dict) -> dict:
        return {"ok": False, "error": "synthetic_permanent"}

    states = [
        hello_module.deliver_push_envelope(key, sender=dead_sender)["state"]
        for _ in range(hello_module.PUSH_MAX_ATTEMPTS)
    ]
    assert states == ["retry", "retry", "blocked"]
    final = hello_module.get_push_envelope(key)
    assert final["state"] == "blocked"
    assert final["retryable"] is False
    assert final["last_error"]


def test_push_adapter_external_leg_is_blocked_not_faked() -> None:
    report = hello_module.push_adapter_report()
    assert report["status"] == "BLOCKED"
    assert report["final_status"] == "BLOCKED"
    assert report["external_blocker"] == hello_module.BLOCKED_EXTERNAL_ENDPOINT
    assert report["external_endpoint_configured"] is False
    assert report["true_push_supported"] is False
    assert report["external_blocked_ok"] is True
    assert report["required_human_actions"]
    assert any(
        hello_module.PUSH_EXTERNAL_ENDPOINT_ENV in item
        for item in report["required_human_actions"]
    )
    external_check = next(
        check
        for check in report["checks"]
        if "external true-push" in check["check"]
    )
    assert external_check["status"] == "BLOCKED"


def test_push_adapter_report_shape() -> None:
    report = hello_module.push_adapter_report()
    assert report["report"] == hello_module.PUSH_ADAPTER_REPORT
    assert report["goal"] == hello_module.PUSH_ADAPTER_GOAL
    assert report["task_id"] == hello_module.PUSH_ADAPTER_TASK_ID
    assert report["task_id"] == "cf-26c20a48d03c"
    assert report["status"] in VALID_STATUSES
    assert report["final_status"] == report["status"]
    assert report["entrypoint"] == "enqueue_push_envelopes"
    assert report["envelope_schema"] == hello_module.PUSH_ENVELOPE_SCHEMA
    assert report["envelope_fields"] == list(hello_module.PUSH_ENVELOPE_FIELDS)
    assert report["channel"] == hello_module.PUSH_ENVELOPE_CHANNEL
    assert report["acceptance_fields"] == list(
        hello_module.PUSH_ADAPTER_ACCEPTANCE_FIELDS
    )
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in VALID_STATUSES
        assert check["detail"]
    markdown = report["markdown"]
    assert markdown.startswith(f"# {hello_module.PUSH_ADAPTER_REPORT}")
    for token in (
        "## Envelope contract",
        "## Classifications",
        "## Idempotency & retry",
        "## Real completion-event chain",
        "## Execution A Golden baseline",
        "## Required human actions to close true push",
        "## Limitations",
        "## Checks",
    ):
        assert token in markdown
    assert "FINAL_STATUS=BLOCKED" in markdown


def test_push_adapter_generates_all_four_classifications() -> None:
    report = hello_module.push_adapter_report()
    assert report["all_classes_present"] is True
    assert set(hello_module.NOTIFICATION_CLASSES) <= set(
        report["observed_classifications"]
    )
    assert report["machine_readable_ok"] is True
    assert report["dedupe_keys_unique"] is True
    for envelope in report["probe_envelopes"]:
        for field in hello_module.PUSH_ENVELOPE_FIELDS:
            assert field in envelope
        assert envelope["human_review_gate"] is True
        assert envelope["auto_pass"] is False
        assert envelope["auto_trigger_next"] is False


def test_push_adapter_report_retry_and_golden_and_chain() -> None:
    report = hello_module.push_adapter_report()
    assert report["idempotent"] is True
    assert report["retry_semantics_ok"] is True
    assert report["exhaustion_ok"] is True
    assert report["exhaustion_states"] == ["retry", "retry", "blocked"]
    assert report["real_chain_ok"] is True
    assert report["execution_a_golden"]["intact"] is True
    chain = report["real_chain"]
    assert chain["completion_event_action"] == "completion_event_handled"
    assert chain["review_ready"] is True
    assert chain["auto_applied"] is False
    assert hello_module.NOTIFICATION_CLASS_PENDING_APPROVAL in (
        chain["envelope_classifications"]
    )


def test_push_adapter_preserves_human_gate() -> None:
    report = hello_module.push_adapter_report()
    assert report["human_gate_preserved"] is True
    assert report["review_states_unchanged"] is True
    assert report["no_auto_dispatch"] is True
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False


def test_push_adapter_no_router_or_orchestrator() -> None:
    report = hello_module.push_adapter_report()
    assert report["contracts_unchanged"] is True
    assert report["no_router"] is True
    assert report["no_orchestrator"] is True
    assert report["no_multi_agent"] is True
    assert report["workflow_modified"] is False
    assert report["changed_files"] == ["hello.py", "test_hello.py"]
    assert list(
        inspect.signature(hello_module.enqueue_push_envelopes).parameters
    ) == ["consumer_id", "task_id", "classification", "now"]
    assert list(
        inspect.signature(hello_module.deliver_push_envelope).parameters
    ) == ["dedupe_key", "sender", "now"]


def test_push_adapter_outbox_persisted_and_queryable() -> None:
    task_id = _notification_probe("push-persist")
    hello_module.submit_task(
        task_id,
        goal=hello_module.PUSH_ADAPTER_GOAL,
        status="success",
        requires_review=True,
    )
    consumer = f"push-consumer-{uuid.uuid4().hex[:8]}"
    hello_module.enqueue_push_envelopes(consumer, task_id=task_id)
    path = hello_module.get_push_outbox_path()
    assert path.is_file()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["kind"] == hello_module.PUSH_OUTBOX_EVIDENCE_KIND
    assert any(item["task_id"] == task_id for item in saved["envelopes"])
    status = hello_module.push_outbox_status()
    assert status["persisted"] is True
    assert status["queryable"] is True
    assert status["pending_count"] >= 1
    assert status["external_endpoint_configured"] is False
    assert status["external_blocker"] == hello_module.BLOCKED_EXTERNAL_ENDPOINT


def test_push_adapter_validates_inputs() -> None:
    with pytest.raises(ValueError):
        hello_module.get_push_envelope("")
    with pytest.raises(KeyError):
        hello_module.deliver_push_envelope("does-not-exist")
    with pytest.raises(ValueError):
        hello_module.deliver_push_envelope("")
    with pytest.raises(ValueError):
        hello_module.enqueue_push_envelopes("")
    with pytest.raises(ValueError):
        hello_module.push_envelope_dedupe_key("", "PASS")
    with pytest.raises(ValueError):
        hello_module.build_push_envelope(
            {"task_id": "t", "classification": "NOT_A_CLASS"}
        )
    with pytest.raises(ValueError):
        hello_module.build_push_envelope({"classification": "PASS"})


def test_push_adapter_explicit_endpoint_env_does_not_claim_pass(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        hello_module.PUSH_EXTERNAL_ENDPOINT_ENV,
        "https://push.invalid/authorized-endpoint",
    )
    status = hello_module.push_outbox_status()
    assert status["external_endpoint_configured"] is True
    assert status["external_blocker"] is None
    # Even when an endpoint is declared, no credentialed sender is wired into
    # the report builder, so the real push leg must still not be claimed PASS.
    report = hello_module.push_adapter_report()
    assert report["status"] == "BLOCKED"
    assert report["external_blocker"] == hello_module.BLOCKED_EXTERNAL_ENDPOINT


# ---------------------------------------------------------------------------
# PERSONAL_AI_EXECUTION_B_SERVERCHAN_ADAPTER_V0.1 (task cf-7eef880257a8)
# ServerChan (Server酱) WeChat adapter over the existing Push Outbox. All keys
# and transports here are fake; no real credential or network is used.
# ---------------------------------------------------------------------------


def _serverchan_fake_key(kind: str = "SCT") -> str:
    if kind == "sctp":
        return "sctp4242t" + uuid.uuid4().hex[:16]
    return "SCT" + uuid.uuid4().hex[:16]


def _serverchan_queue(task_id: str) -> str:
    hello_module.submit_task(
        task_id,
        goal=hello_module.SERVERCHAN_ADAPTER_GOAL,
        status="success",
        requires_review=True,
    )
    consumer = f"serverchan-consumer-{uuid.uuid4().hex[:8]}"
    queued = hello_module.enqueue_push_envelopes(consumer, task_id=task_id)
    return queued["created"][0]["dedupe_key"]


def test_serverchan_sendkey_is_read_only_from_env(monkeypatch) -> None:
    assert hello_module.SERVERCHAN_SENDKEY_ENV == "SERVERCHAN_SENDKEY"
    monkeypatch.delenv(hello_module.SERVERCHAN_SENDKEY_ENV, raising=False)
    assert hello_module.serverchan_sendkey() is None
    assert hello_module.serverchan_sendkey_present() is False
    fake = _serverchan_fake_key()
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, fake)
    assert hello_module.serverchan_sendkey() == fake
    assert hello_module.serverchan_sendkey_present() is True
    assert hello_module.serverchan_redact(fake) != fake
    assert hello_module.serverchan_redact(fake).startswith(fake[:3])


def test_serverchan_endpoint_selection_for_sct_and_sctp() -> None:
    sct = _serverchan_fake_key("SCT")
    sctp = _serverchan_fake_key("sctp")
    assert hello_module.serverchan_sendkey_kind(sct) == "SCT"
    assert hello_module.serverchan_sendkey_kind(sctp) == "sctp"
    sct_endpoint = hello_module.serverchan_endpoint(sct)
    sctp_endpoint = hello_module.serverchan_endpoint(sctp)
    assert sct_endpoint == f"https://sctapi.ftqq.com/{sct}.send"
    assert sctp_endpoint == f"https://4242.push.ft07.com/send/{sctp}.send"
    assert sct_endpoint != sctp_endpoint
    with pytest.raises(ValueError):
        hello_module.serverchan_sendkey_kind("")
    with pytest.raises(ValueError):
        hello_module.serverchan_endpoint("")


def test_serverchan_payload_maps_all_four_classifications() -> None:
    for classification in hello_module.NOTIFICATION_CLASSES:
        envelope = {
            "task_id": f"task-{classification}",
            "classification": classification,
            "summary": f"summary for {classification}",
            "review_required": (
                classification == hello_module.NOTIFICATION_CLASS_PENDING_APPROVAL
            ),
            "dedupe_key": f"push:task-{classification}:{classification}:sig",
        }
        payload = hello_module.build_serverchan_payload(envelope)
        for field in hello_module.SERVERCHAN_REQUIRED_PAYLOAD_FIELDS:
            assert field in payload
        assert payload["task_id"] == f"task-{classification}"
        assert payload["classification"] == classification
        assert payload["summary"] == f"summary for {classification}"
        assert payload["review_required"] == (
            classification == hello_module.NOTIFICATION_CLASS_PENDING_APPROVAL
        )
        assert payload["title"] and "\n" not in payload["title"]
        assert payload["desp"]
        assert payload["human_review_gate"] is True
        assert payload["auto_pass"] is False
        assert payload["auto_trigger_next"] is False
        for token in ("task_id", "classification", "summary", "review_required"):
            assert token in payload["desp"]
        json.dumps(payload, sort_keys=True)


def test_serverchan_payload_validates_inputs() -> None:
    with pytest.raises(ValueError):
        hello_module.build_serverchan_payload(
            {"task_id": "t", "classification": "NOT_A_CLASS"}
        )
    with pytest.raises(ValueError):
        hello_module.build_serverchan_payload({"classification": "PASS"})
    with pytest.raises(TypeError):
        hello_module.build_serverchan_payload("not-a-dict")


def test_serverchan_delivery_without_credential_is_blocked(monkeypatch) -> None:
    monkeypatch.delenv(hello_module.SERVERCHAN_SENDKEY_ENV, raising=False)
    task_id = _notification_probe("serverchan-nocred")
    key = _serverchan_queue(task_id)
    calls: list[tuple] = []

    def fake_transport(endpoint: str, payload: dict) -> dict:
        calls.append((endpoint, payload))
        return {"ok": True}

    result = hello_module.deliver_serverchan_envelope(key, transport=fake_transport)
    assert result["state"] == "blocked"
    assert result["status"] == "BLOCKED"
    assert result["credential_present"] is False
    assert result["external_blocker"] == hello_module.BLOCKED_EXTERNAL_CREDENTIAL
    assert result["retryable"] is False
    assert calls == []
    envelope = hello_module.get_push_envelope(key)
    assert envelope["external_blocker"] == hello_module.BLOCKED_EXTERNAL_CREDENTIAL
    assert envelope["retryable"] is False
    assert envelope["serverchan"]["credential_present"] is False


def test_serverchan_delivery_with_fake_credential_uses_fake_transport(
    monkeypatch,
) -> None:
    fake_key = _serverchan_fake_key("sctp")
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, fake_key)
    task_id = _notification_probe("serverchan-cred")
    key = _serverchan_queue(task_id)
    seen: dict = {}

    def fake_transport(endpoint: str, payload: dict) -> dict:
        seen["endpoint"] = endpoint
        seen["payload"] = payload
        return {"ok": True, "status_code": 200}

    result = hello_module.deliver_serverchan_envelope(key, transport=fake_transport)
    assert result["state"] == "delivered"
    assert result["status"] == "PASS"
    assert result["credential_present"] is True
    assert result["endpoint_kind"] == "sctp"
    assert result["external_blocker"] is None
    assert seen["endpoint"] == f"https://4242.push.ft07.com/send/{fake_key}.send"
    assert seen["payload"]["task_id"] == task_id
    assert "summary" in seen["payload"]["desp"]
    assert "review_required" in seen["payload"]["desp"]
    # The SendKey must never appear in the result we keep (redacted only).
    assert fake_key not in json.dumps(result, sort_keys=True)


def test_serverchan_retry_semantics_are_bounded(monkeypatch) -> None:
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, _serverchan_fake_key())
    task_id = _notification_probe("serverchan-retry")
    key = _serverchan_queue(task_id)
    calls = {"count": 0}

    def flaky_transport(endpoint: str, payload: dict) -> dict:
        calls["count"] += 1
        if calls["count"] == 1:
            return {"ok": False, "error": "synthetic_transient"}
        return {"ok": True}

    first = hello_module.deliver_serverchan_envelope(key, transport=flaky_transport)
    assert first["state"] == "retry"
    assert first["attempt_count"] == 1
    assert first["retryable"] is True
    second = hello_module.deliver_serverchan_envelope(key, transport=flaky_transport)
    assert second["state"] == "delivered"
    assert second["attempt_count"] == 2
    assert second["retryable"] is False
    assert hello_module.get_push_envelope(key)["state"] == "delivered"


def test_serverchan_retry_exhaustion_blocks(monkeypatch) -> None:
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, _serverchan_fake_key())
    task_id = _notification_probe("serverchan-exhaust")
    key = _serverchan_queue(task_id)

    def dead_transport(endpoint: str, payload: dict) -> dict:
        return {"ok": False, "error": "synthetic_permanent"}

    states = [
        hello_module.deliver_serverchan_envelope(key, transport=dead_transport)["state"]
        for _ in range(hello_module.SERVERCHAN_MAX_ATTEMPTS)
    ]
    assert states == ["retry", "retry", "blocked"]
    final = hello_module.get_push_envelope(key)
    assert final["state"] == "blocked"
    assert final["retryable"] is False
    assert final["last_error"]


def test_serverchan_report_without_credential_blocks_external_credential(
    monkeypatch,
) -> None:
    monkeypatch.delenv(hello_module.SERVERCHAN_SENDKEY_ENV, raising=False)
    report = hello_module.serverchan_adapter_report()
    assert report["report"] == "PERSONAL_AI_SERVERCHAN_ADAPTER_REPORT"
    assert report["goal"] == "PERSONAL_AI_EXECUTION_B_SERVERCHAN_ADAPTER_V0.1"
    assert report["task_id"] == "cf-7eef880257a8"
    assert report["status"] == "BLOCKED"
    assert report["final_status"] == "BLOCKED"
    assert report["credential_present"] is False
    assert report["external_blocker"] == hello_module.BLOCKED_EXTERNAL_CREDENTIAL
    assert report["true_push_supported"] is False
    assert report["all_classes_present"] is True
    assert report["mapping_ok"] is True
    assert report["endpoint_selection_ok"] is True
    assert report["execution_a_golden"]["intact"] is True
    assert report["required_human_actions"]
    assert report["acceptance_fields"] == list(
        hello_module.SERVERCHAN_ACCEPTANCE_FIELDS
    )
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in VALID_STATUSES
        assert check["detail"]
    markdown = report["markdown"]
    assert markdown.startswith("# PERSONAL_AI_SERVERCHAN_ADAPTER_REPORT")
    for token in (
        "## SendKey credential boundary",
        "## Endpoint selection",
        "## Envelope -> title/desp mapping",
        "## Classifications",
        "## Delivery & retry",
        "## Execution A Golden baseline",
        "## Required human actions to connect WeChat",
        "## Limitations",
        "## Checks",
    ):
        assert token in markdown
    assert "FINAL_STATUS=BLOCKED" in markdown
    external_check = next(
        check
        for check in report["checks"]
        if "credential present" in check["check"]
    )
    assert external_check["status"] == "BLOCKED"


def test_serverchan_report_with_fake_credential_and_transport_passes(
    monkeypatch,
) -> None:
    fake_key = _serverchan_fake_key("SCT")
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, fake_key)
    calls: list[tuple] = []

    def fake_transport(endpoint: str, payload: dict) -> dict:
        calls.append((endpoint, payload))
        return {"ok": True, "status_code": 200}

    report = hello_module.serverchan_adapter_report(transport=fake_transport)
    assert report["status"] == "PASS"
    assert report["credential_present"] is True
    assert report["real_delivery_ok"] is True
    assert report["true_push_supported"] is True
    assert report["external_blocker"] is None
    assert len(calls) == 1
    endpoint, payload = calls[0]
    assert endpoint == f"https://sctapi.ftqq.com/{fake_key}.send"
    assert payload["task_id"] == report["delivery"]["task_id"]
    # No SendKey may leak into the report or its markdown.
    assert fake_key not in json.dumps(report, sort_keys=True)
    assert fake_key not in report["markdown"]
    assert report["sendkey_redacted"] != fake_key


def test_serverchan_report_preserves_human_gate_and_contracts(monkeypatch) -> None:
    monkeypatch.delenv(hello_module.SERVERCHAN_SENDKEY_ENV, raising=False)
    report = hello_module.serverchan_adapter_report()
    assert report["human_gate_preserved"] is True
    assert report["review_states_unchanged"] is True
    assert report["no_auto_dispatch"] is True
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    assert report["contracts_unchanged"] is True
    assert report["no_router"] is True
    assert report["no_orchestrator"] is True
    assert report["no_multi_agent"] is True
    assert report["workflow_modified"] is False
    assert report["changed_files"] == ["hello.py", "test_hello.py"]
    assert list(
        inspect.signature(hello_module.deliver_serverchan_envelope).parameters
    ) == ["dedupe_key", "transport", "now"]
    assert list(
        inspect.signature(hello_module.serverchan_adapter_report).parameters
    ) == ["now", "transport"]


# ---------------------------------------------------------------------------
# PERSONAL_AI_EXECUTION_B_SERVERCHAN_REAL_PUSH_GOLDEN_01 (task cf-7d9109b381ae)
# All transports here are fake and no real credential is used; the real HTTPS
# leg is exercised only through the injectable transport.
# ---------------------------------------------------------------------------


def _golden_fake_transport(calls: list, *, push_id: str = "pid-golden") -> object:
    def transport(endpoint: str, payload: dict) -> dict:
        calls.append((endpoint, payload))
        return {
            "ok": True,
            "status_code": 200,
            "push_id": push_id,
            "server_message": "SUCCESS",
        }

    return transport


def test_serverchan_golden_payload_contract() -> None:
    envelope = {
        "task_id": SERVERCHAN_REAL_PUSH_TASK_ID,
        "classification": "PASS",
        "summary": "fixed summary",
        "review_required": False,
        "dedupe_key": "push:cf-7d9109b381ae:PASS:abc123",
    }
    payload = build_serverchan_golden_payload(envelope)
    assert payload["title"] == SERVERCHAN_REAL_PUSH_TITLE
    assert SERVERCHAN_REAL_PUSH_TITLE == "Personal AI Golden"
    assert payload["task_id"] == SERVERCHAN_REAL_PUSH_TASK_ID
    assert payload["classification"] == "PASS"
    assert payload["review_required"] is False
    assert payload["marker"] == SERVERCHAN_REAL_PUSH_MARKER
    for token in ("task_id", "classification", "summary", "review_required"):
        assert token in payload["desp"]
    assert "review_required: false" in payload["desp"]
    assert payload["human_review_gate"] is True
    assert payload["auto_pass"] is False
    assert payload["auto_trigger_next"] is False
    json.dumps(payload, sort_keys=True)
    with pytest.raises(TypeError):
        build_serverchan_golden_payload("not-a-dict")
    with pytest.raises(ValueError):
        build_serverchan_golden_payload({"classification": "PASS"})
    with pytest.raises(ValueError):
        build_serverchan_golden_payload(
            {"task_id": "t", "classification": "NOT_A_CLASS"}
        )


def test_serverchan_real_push_golden_without_credential_is_blocked(
    monkeypatch,
) -> None:
    monkeypatch.delenv(hello_module.SERVERCHAN_SENDKEY_ENV, raising=False)
    calls: list = []
    report = serverchan_real_push_golden(
        transport=_golden_fake_transport(calls)
    )
    assert report["report"] == SERVERCHAN_REAL_PUSH_REPORT
    assert report["goal"] == SERVERCHAN_REAL_PUSH_GOAL
    assert report["task_id"] == SERVERCHAN_REAL_PUSH_TASK_ID == "cf-7d9109b381ae"
    assert report["final_status"] == "BLOCKED"
    assert report["real_push"] == REAL_PUSH_BLOCKED_CREDENTIAL
    assert report["real_push"] == "REAL_PUSH=BLOCKED_EXTERNAL_CREDENTIAL"
    assert report["real_push_passed"] is False
    assert report["external_blocker"] == hello_module.BLOCKED_EXTERNAL_CREDENTIAL
    assert report["credential_present"] is False
    # The real network leg must never be entered without a credential.
    assert calls == []
    # Exactly one logical notification + one outbox envelope.
    assert report["single_logical_notification"] is True
    assert report["notification_count"] == 1
    assert report["envelope_count"] == 1
    # Content lets the phone identify the Golden notification.
    assert SERVERCHAN_REAL_PUSH_TITLE in report["payload"]["title"]
    assert "review_required: false" in report["payload"]["desp"]
    assert "classification: PASS" in report["payload"]["desp"]
    assert SERVERCHAN_REAL_PUSH_MARKER in report["payload"]["desp"]
    assert report["markdown"].startswith(f"# {SERVERCHAN_REAL_PUSH_REPORT}")
    assert "REAL_PUSH=BLOCKED_EXTERNAL_CREDENTIAL" in report["markdown"]
    assert "FINAL_STATUS=BLOCKED" in report["markdown"]
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False


def test_serverchan_real_push_golden_with_fake_credential_passes(
    monkeypatch,
) -> None:
    fake_key = _serverchan_fake_key("SCT")
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, fake_key)
    calls: list = []
    report = serverchan_real_push_golden(
        transport=_golden_fake_transport(calls, push_id="pid-real-1")
    )
    assert report["final_status"] == "PASS"
    assert report["real_push"] == REAL_PUSH_PASS == "REAL_PUSH=PASS"
    assert report["real_push_passed"] is True
    assert report["external_blocker"] is None
    assert report["credential_present"] is True
    assert report["endpoint_kind"] == "SCT"
    assert len(calls) == 1
    endpoint, payload = calls[0]
    assert endpoint == f"https://sctapi.ftqq.com/{fake_key}.send"
    assert SERVERCHAN_REAL_PUSH_TITLE in payload["title"]
    assert payload["task_id"] == SERVERCHAN_REAL_PUSH_TASK_ID
    # Non-sensitive service confirmation is recorded; the SendKey is not.
    assert report["http_status_code"] == 200
    assert report["push_id"] == "pid-real-1"
    assert report["server_message"] == "SUCCESS"
    assert report["sent_at"]
    assert fake_key not in json.dumps(report, sort_keys=True)
    assert fake_key not in report["markdown"]
    assert report["delivery"]["state"] == "delivered"


def test_serverchan_real_push_golden_is_idempotent_no_double_send(
    monkeypatch,
) -> None:
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, _serverchan_fake_key())
    calls: list = []
    transport = _golden_fake_transport(calls, push_id="pid-once")
    first = serverchan_real_push_golden(transport=transport)
    second = serverchan_real_push_golden(transport=transport)
    assert first["real_push"] == REAL_PUSH_PASS
    assert second["real_push"] == REAL_PUSH_PASS
    # Exactly one logical notification and one real HTTPS send across both runs.
    assert len(calls) == 1
    assert second["notification_count"] == 1
    assert second["envelope_count"] == 1
    assert second["single_logical_notification"] is True
    assert second["delivery"]["already_delivered"] is True
    assert second["push_id"] == "pid-once"


def test_serverchan_real_push_golden_bounded_retry_then_delivered(
    monkeypatch,
) -> None:
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, _serverchan_fake_key())
    calls = {"count": 0}

    def flaky(endpoint: str, payload: dict) -> dict:
        calls["count"] += 1
        if calls["count"] == 1:
            return {"ok": False, "status_code": 503, "error": "synthetic_transient"}
        return {"ok": True, "status_code": 200, "push_id": "pid-retry"}

    first = serverchan_real_push_golden(transport=flaky)
    assert first["delivery"]["state"] == "retry"
    assert first["delivery"]["retryable"] is True
    assert first["real_push"] == hello_module.REAL_PUSH_BLOCKED_DELIVERY
    assert first["delivery"]["attempt_count"] == 1
    second = serverchan_real_push_golden(transport=flaky)
    assert second["delivery"]["state"] == "delivered"
    assert second["delivery"]["attempt_count"] == 2
    assert second["real_push"] == REAL_PUSH_PASS
    assert calls["count"] == 2
    # Still one logical notification.
    assert second["notification_count"] == 1
    assert second["envelope_count"] == 1


def test_serverchan_real_push_golden_human_gate_and_contracts(
    monkeypatch,
) -> None:
    monkeypatch.delenv(hello_module.SERVERCHAN_SENDKEY_ENV, raising=False)
    report = serverchan_real_push_golden(transport=_golden_fake_transport([]))
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    assert report["workflow_modified"] is False
    assert report["changed_files"] == ["hello.py", "test_hello.py"]
    assert report["submit_task_contract"] == "UNCHANGED"
    assert report["get_task_result_contract"] == "UNCHANGED"
    assert report["mark_reviewed_contract"] == "COMPATIBLE"
    # The golden records its verdict through the unchanged human-review contract.
    review = hello_module.get_task_review(SERVERCHAN_REAL_PUSH_TASK_ID)
    assert review is not None
    assert review["reviewed"] is True
    assert review["review_verdict"] == "PASS"
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in VALID_STATUSES
        assert check["detail"]
    assert list(
        inspect.signature(hello_module.deliver_serverchan_envelope).parameters
    ) == ["dedupe_key", "transport", "now"]
    assert list(
        inspect.signature(serverchan_real_push_golden).parameters
    ) == ["transport", "now"]


# ---------------------------------------------------------------------------
# PERSONAL_AI_EXECUTION_B_SERVERCHAN_WORKFLOW_SECRET_WIRING_FIX_01
# (task cf-4c0b4b0e81d7). Read-only detection of the missing workflow secret
# wiring; no real credential and no network are used here.
# ---------------------------------------------------------------------------

_WIRED_AGENT_STEP = """\
steps:
  - name: Setup python
    uses: actions/setup-python@v5
  - name: Run OpenCode agent (execute task contract)
    env:
      OPENCODE_API_KEY: ${{ secrets.OPENCODE_API_KEY }}
      SERVERCHAN_SENDKEY: ${{ secrets.SERVERCHAN_SENDKEY }}
    run: |
      opencode run --auto -m some/model "task"
"""

_UNWIRED_AGENT_STEP = """\
steps:
  - name: Setup python
    uses: actions/setup-python@v5
  - name: Run OpenCode agent (execute task contract)
    env:
      OPENCODE_API_KEY: ${{ secrets.OPENCODE_API_KEY }}
    run: |
      opencode run --auto -m some/model "task"
"""


def test_serverchan_workflow_wiring_detects_missing_secret() -> None:
    status = hello_module.serverchan_workflow_wiring_status(_UNWIRED_AGENT_STEP)
    assert status["has_agent_step"] is True
    assert status["secret_wired"] is False
    assert status["expected_env_line"] == (
        "SERVERCHAN_SENDKEY: ${{ secrets.SERVERCHAN_SENDKEY }}"
    )


def test_serverchan_workflow_wiring_detects_present_secret() -> None:
    status = hello_module.serverchan_workflow_wiring_status(_WIRED_AGENT_STEP)
    assert status["has_agent_step"] is True
    assert status["secret_wired"] is True
    assert status["secret_reference_present"] is True


def test_serverchan_workflow_wiring_ignores_secret_outside_agent_step() -> None:
    text = """\
steps:
  - name: Some other step
    env:
      SERVERCHAN_SENDKEY: ${{ secrets.SERVERCHAN_SENDKEY }}
  - name: Run OpenCode agent (execute task contract)
    env:
      OPENCODE_API_KEY: ${{ secrets.OPENCODE_API_KEY }}
    run: |
      opencode run --auto "task"
"""
    status = hello_module.serverchan_workflow_wiring_status(text)
    assert status["secret_reference_present"] is True
    assert status["secret_wired"] is False


def test_serverchan_workflow_wiring_audit_without_credential_reports_blocker(
    monkeypatch,
) -> None:
    monkeypatch.delenv(hello_module.SERVERCHAN_SENDKEY_ENV, raising=False)
    report = hello_module.serverchan_workflow_secret_wiring_audit()
    assert report["report"] == hello_module.SERVERCHAN_WIRING_FIX_REPORT
    assert report["goal"] == hello_module.SERVERCHAN_WIRING_FIX_GOAL
    assert report["task_id"] == hello_module.SERVERCHAN_WIRING_FIX_TASK_ID
    assert report["task_id"] == "cf-4c0b4b0e81d7"
    assert report["credential_present"] is False
    assert report["real_push_passed"] is False
    assert report["real_https_attempted"] is False
    assert report["final_status"] == "BLOCKED"
    assert report["real_push"] == hello_module.REAL_PUSH_BLOCKED_CREDENTIAL
    # The single precise blocker must be the workflow wiring gap, not a mock PASS.
    if not report["workflow_secret_wired"]:
        assert report["blocker"] == hello_module.SERVERCHAN_WIRING_BLOCKER
        assert report["single_blocker"] == hello_module.SERVERCHAN_WIRING_BLOCKER
    else:
        assert report["blocker"] == hello_module.BLOCKED_EXTERNAL_CREDENTIAL
    assert report["workflow_modified"] is False
    assert report["changed_files"] == ["hello.py", "test_hello.py"]
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    assert report["payload"]["task_id"] == hello_module.SERVERCHAN_WIRING_FIX_TASK_ID
    assert hello_module.SERVERCHAN_REAL_PUSH_TITLE in report["payload"]["title"]
    assert "classification: PASS" in report["payload"]["desp"]
    assert "review_required: false" in report["payload"]["desp"]
    assert report["markdown"].startswith(f"# {hello_module.SERVERCHAN_WIRING_FIX_REPORT}")
    assert "FINAL_STATUS=BLOCKED" in report["markdown"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in VALID_STATUSES
        assert check["detail"]
    # No credential means no network leg is entered.
    assert report["real_push_result"]["delivery"]["state"] == "blocked"


def test_serverchan_workflow_wiring_audit_with_fake_credential_passes(
    monkeypatch,
) -> None:
    fake_key = _serverchan_fake_key("SCT")
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, fake_key)
    calls: list = []
    report = hello_module.serverchan_workflow_secret_wiring_audit(
        transport=_golden_fake_transport(calls, push_id="pid-wiring-1")
    )
    assert report["final_status"] == "PASS"
    assert report["real_push"] == hello_module.REAL_PUSH_PASS
    assert report["real_push_passed"] is True
    assert report["blocker"] is None
    assert report["single_blocker"] is None
    assert report["credential_present"] is True
    assert report["real_https_attempted"] is True
    assert len(calls) == 1
    endpoint, payload = calls[0]
    assert endpoint == f"https://sctapi.ftqq.com/{fake_key}.send"
    assert hello_module.SERVERCHAN_REAL_PUSH_TITLE in payload["title"]
    assert payload["task_id"] == hello_module.SERVERCHAN_WIRING_FIX_TASK_ID
    assert report["http_status_code"] == 200
    assert report["push_id"] == "pid-wiring-1"
    assert report["server_message"] == "SUCCESS"
    # The SendKey must never leak into the report or its markdown.
    assert fake_key not in json.dumps(report, sort_keys=True)
    assert fake_key not in report["markdown"]
    assert report["workflow_modified"] is False


def test_serverchan_workflow_wiring_audit_can_skip_real_push(monkeypatch) -> None:
    monkeypatch.delenv(hello_module.SERVERCHAN_SENDKEY_ENV, raising=False)
    report = hello_module.serverchan_workflow_secret_wiring_audit(
        attempt_real_push=False
    )
    assert report["real_push_result"] is None
    assert report["real_push"] == hello_module.REAL_PUSH_BLOCKED_CREDENTIAL
    assert report["final_status"] == "BLOCKED"


# ---------------------------------------------------------------------------
# PERSONAL_AI_EXECUTION_B_SERVERCHAN_REAL_PUSH_GOLDEN_02 (task cf-4721483214cc)
# Re-verifies the unchanged completion/notification/outbox/ServerChan chain for
# a second task id after the workflow secret wiring fix. Fake transports keep the
# deterministic tests offline; the single real HTTPS leg runs only when the
# runner provides SERVERCHAN_SENDKEY, and is skipped (never faked) otherwise.
# ---------------------------------------------------------------------------


def test_serverchan_golden_02_payload_contract() -> None:
    envelope = {
        "task_id": SERVERCHAN_REAL_PUSH_02_TASK_ID,
        "classification": "PASS",
        "summary": "fixed summary 02",
        "review_required": False,
        "dedupe_key": f"push:{SERVERCHAN_REAL_PUSH_02_TASK_ID}:PASS:abc123",
    }
    payload = build_serverchan_golden_02_payload(envelope)
    assert payload["title"] == SERVERCHAN_REAL_PUSH_02_TITLE
    assert SERVERCHAN_REAL_PUSH_02_TITLE == "Personal AI Golden 02"
    assert payload["task_id"] == SERVERCHAN_REAL_PUSH_02_TASK_ID == "cf-4721483214cc"
    assert payload["classification"] == "PASS"
    assert payload["review_required"] is False
    assert payload["marker"] == SERVERCHAN_REAL_PUSH_02_MARKER
    for token in ("task_id", "classification", "summary", "review_required"):
        assert token in payload["desp"]
    assert "review_required: false" in payload["desp"]
    assert "classification: PASS" in payload["desp"]
    assert f"- task_id: {SERVERCHAN_REAL_PUSH_02_TASK_ID}" in payload["desp"]
    assert SERVERCHAN_REAL_PUSH_02_MARKER in payload["desp"]
    assert payload["human_review_gate"] is True
    assert payload["auto_pass"] is False
    assert payload["auto_trigger_next"] is False
    json.dumps(payload, sort_keys=True)
    with pytest.raises(TypeError):
        build_serverchan_golden_02_payload("not-a-dict")
    with pytest.raises(ValueError):
        build_serverchan_golden_02_payload({"classification": "PASS"})
    with pytest.raises(ValueError):
        build_serverchan_golden_02_payload(
            {"task_id": "t", "classification": "NOT_A_CLASS"}
        )


def test_serverchan_real_push_golden_02_without_credential_is_blocked(
    monkeypatch,
) -> None:
    monkeypatch.delenv(hello_module.SERVERCHAN_SENDKEY_ENV, raising=False)
    calls: list = []
    report = serverchan_real_push_golden_02(transport=_golden_fake_transport(calls))
    assert report["report"] == SERVERCHAN_REAL_PUSH_02_REPORT
    assert report["goal"] == SERVERCHAN_REAL_PUSH_02_GOAL
    assert report["task_id"] == SERVERCHAN_REAL_PUSH_02_TASK_ID
    assert report["final_status"] == "BLOCKED"
    assert report["real_push"] == REAL_PUSH_BLOCKED_CREDENTIAL
    assert report["real_push"] == "REAL_PUSH=BLOCKED_EXTERNAL_CREDENTIAL"
    assert report["real_push_passed"] is False
    assert report["external_blocker"] == hello_module.BLOCKED_EXTERNAL_CREDENTIAL
    assert report["credential_present"] is False
    # The real network leg must never be entered without a credential.
    assert calls == []
    # Exactly one logical notification + one outbox envelope, dedupe normal.
    assert report["single_logical_notification"] is True
    assert report["notification_count"] == 1
    assert report["envelope_count"] == 1
    assert report["dedupe_ok"] is True
    assert SERVERCHAN_REAL_PUSH_02_TITLE in report["payload"]["title"]
    assert "review_required: false" in report["payload"]["desp"]
    assert "classification: PASS" in report["payload"]["desp"]
    assert f"- task_id: {SERVERCHAN_REAL_PUSH_02_TASK_ID}" in report["payload"]["desp"]
    assert SERVERCHAN_REAL_PUSH_02_MARKER in report["payload"]["desp"]
    assert report["markdown"].startswith(f"# {SERVERCHAN_REAL_PUSH_02_REPORT}")
    assert "REAL_PUSH=BLOCKED_EXTERNAL_CREDENTIAL" in report["markdown"]
    assert "FINAL_STATUS=BLOCKED" in report["markdown"]
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    assert report["workflow_modified"] is False
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in VALID_STATUSES
        assert check["detail"]


def test_serverchan_real_push_golden_02_with_fake_credential_passes(
    monkeypatch,
) -> None:
    fake_key = _serverchan_fake_key("SCT")
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, fake_key)
    calls: list = []
    report = serverchan_real_push_golden_02(
        transport=_golden_fake_transport(calls, push_id="pid-golden-02")
    )
    assert report["final_status"] == "PASS"
    assert report["real_push"] == REAL_PUSH_PASS == "REAL_PUSH=PASS"
    assert report["real_push_passed"] is True
    assert report["credential_present"] is True
    assert report["external_blocker"] is None
    assert len(calls) == 1
    endpoint, payload = calls[0]
    assert endpoint == f"https://sctapi.ftqq.com/{fake_key}.send"
    assert SERVERCHAN_REAL_PUSH_02_TITLE in payload["title"]
    assert payload["task_id"] == SERVERCHAN_REAL_PUSH_02_TASK_ID
    assert report["http_status_code"] == 200
    assert report["push_id"] == "pid-golden-02"
    assert report["server_message"] == "SUCCESS"
    assert report["sent_at"]
    # The SendKey must never leak into the report or markdown.
    assert fake_key not in json.dumps(report, sort_keys=True)
    assert fake_key not in report["markdown"]
    assert report["delivery"]["state"] == "delivered"
    assert report["human_review_gate"] is True
    assert report["auto_pass"] is False
    assert report["auto_trigger_next"] is False
    assert report["changed_files"] == ["hello.py", "test_hello.py"]
    assert list(
        inspect.signature(serverchan_real_push_golden_02).parameters
    ) == ["transport", "now"]


def test_serverchan_real_push_golden_02_is_idempotent(monkeypatch) -> None:
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, _serverchan_fake_key())
    calls: list = []
    transport = _golden_fake_transport(calls, push_id="pid-once-02")
    first = serverchan_real_push_golden_02(transport=transport)
    second = serverchan_real_push_golden_02(transport=transport)
    assert first["real_push"] == REAL_PUSH_PASS
    assert second["real_push"] == REAL_PUSH_PASS
    # Exactly one logical notification and one send across both runs.
    assert len(calls) == 1
    assert second["notification_count"] == 1
    assert second["envelope_count"] == 1
    assert second["single_logical_notification"] is True
    assert second["delivery"]["already_delivered"] is True
    assert second["push_id"] == "pid-once-02"


def test_serverchan_real_push_golden_02_workflow_wiring_confirmed() -> None:
    # Least privilege (control-plane commit 1d4d557): the SendKey is deliberately
    # NOT injected into the agent execution step, so agent/pytest cannot observe
    # it. The dedicated push step is where the control plane will wire it; the
    # hand-off spec must be complete and credential-free in the agent scope.
    workflow = pathlib.Path(
        hello_module.REPO_ROOT,
        *hello_module.SERVERCHAN_WORKFLOW_DIR,
        hello_module.SERVERCHAN_CANONICAL_WORKFLOW,
    )
    status = hello_module.serverchan_workflow_wiring_status(
        workflow.read_text(encoding="utf-8")
    )
    assert status["has_agent_step"] is True
    assert status["secret_wired"] is False
    # The secret reference is now intentionally scoped to the dedicated push step
    # only (control-plane commit dec89ce), never the agent execution step.
    assert status["secret_reference_present"] is True
    assert status["agent_step_secret_present"] is False
    assert status["least_privilege_agent_step"] is True
    assert status["dedicated_push_step_present"] is True
    assert status["dedicated_push_step_secret_present"] is True
    assert status["expected_env_line"] == (
        "SERVERCHAN_SENDKEY: ${{ secrets.SERVERCHAN_SENDKEY }}"
    )
    spec = hello_module.dedicated_push_step_spec()
    assert spec["env"][hello_module.SERVERCHAN_SENDKEY_ENV] == (
        "${{ secrets.SERVERCHAN_SENDKEY }}"
    )
    assert spec["ledger"]["identity_fields"] == ["task_id", "classification"]
    assert spec["ledger"]["persist_across_rerun"] is True


# ---------------------------------------------------------------------------
# PERSONAL_AI_EXECUTION_B_SERVERCHAN_DURABLE_DEDUPE_AND_TEST_ISOLATION_FIX_01
# (task cf-2f2b71c331da)
#
# The real-HTTPS Golden test was removed: re-injecting the runner SendKey into a
# pytest process is exactly what produced the extra real ServerChan sends. The
# tests below instead prove (a) pytest can never reach the real network even when
# SERVERCHAN_SENDKEY is present, and (b) the durable, cross-process delivery
# ledger makes a second delivery idempotent and fail-closed.
# ---------------------------------------------------------------------------


def test_pytest_never_performs_real_serverchan_https(monkeypatch) -> None:
    # Worst case: the runner really does export SERVERCHAN_SENDKEY. The
    # in-module test-isolation guard must still keep the count at exactly zero.
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, _serverchan_fake_key())
    monkeypatch.setenv(hello_module.SERVERCHAN_TEST_ISOLATION_ENV, "1")
    hello_module.reset_serverchan_test_isolation_counters()

    calls: list = []
    report = serverchan_real_push_golden_02(
        transport=_golden_fake_transport(calls, push_id="pid-isolation")
    )
    # Fake transport is always injected in tests and no real attempt is made.
    assert hello_module.serverchan_real_network_attempts() == 0
    assert len(calls) == 1
    assert report["real_push"] == REAL_PUSH_PASS

    # Now with the DEFAULT (real) transport on a fresh identity: the isolation
    # guard must block the network even though a credential is present.
    task_id = "serverchan-isolation-default"
    key = _serverchan_queue(task_id)
    hello_module.reset_serverchan_test_isolation_counters()
    blocked = hello_module.deliver_serverchan_envelope(key)
    assert hello_module.serverchan_real_network_attempts() == 0
    assert hello_module.serverchan_test_isolation_blocks() == 1
    assert blocked["state"] == "retry"
    assert blocked["status"] == "BLOCKED"


def test_serverchan_real_transport_refuses_under_pytest(monkeypatch) -> None:
    monkeypatch.setenv(hello_module.SERVERCHAN_TEST_ISOLATION_ENV, "1")
    hello_module.reset_serverchan_test_isolation_counters()
    outcome = hello_module.serverchan_http_transport(
        "https://sctapi.ftqq.com/FAKE.send", {"title": "t", "desp": "d"}
    )
    assert outcome["ok"] is False
    assert outcome["network_attempted"] is False
    assert hello_module.serverchan_real_network_attempts() == 0
    assert hello_module.serverchan_test_isolation_blocks() == 1


def test_delivery_ledger_default_path_is_canonical_not_tmp(monkeypatch) -> None:
    monkeypatch.delenv(hello_module.DELIVERY_LEDGER_STATE_ENV, raising=False)
    path = hello_module.get_delivery_ledger_path()
    assert path == hello_module.REPO_ROOT / hello_module.DELIVERY_LEDGER_STATE_DEFAULT
    assert not str(path).startswith(str(hello_module.tempfile.gettempdir()))
    status = hello_module.delivery_ledger_status()
    assert status["durable"] is True
    assert status["in_repo"] is True
    assert status["under_tempdir"] is False
    assert status["identity_fields"] == ["task_id", "classification"]


def test_durable_ledger_records_once_and_blocks_resend(monkeypatch) -> None:
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, _serverchan_fake_key())
    task_id = "serverchan-ledger-once"
    key = _serverchan_queue(task_id)
    classification = hello_module.get_push_envelope(key)["classification"]
    calls: list = []

    def fake_transport(endpoint: str, payload: dict) -> dict:
        calls.append(endpoint)
        return {
            "ok": True,
            "status_code": 200,
            "push_id": "pid-ledger-once",
            "server_message": "SUCCESS",
        }

    first = hello_module.deliver_serverchan_envelope(key, transport=fake_transport)
    assert first["state"] == "delivered"
    identity = hello_module.delivery_identity(task_id, classification)
    record = hello_module.get_delivery_record(identity)
    assert record is not None
    assert record["state"] == "delivered"
    assert record["push_id"] == "pid-ledger-once"
    assert record["delivered_at"]
    assert record["quota_consumed"] is True

    second = hello_module.deliver_serverchan_envelope(key, transport=fake_transport)
    assert second["state"] == "delivered"
    assert second["already_delivered"] is True
    assert second["push_id"] == "pid-ledger-once"
    assert len(calls) == 1  # same task+classification never consumes a 2nd unit


def test_durable_ledger_fail_closed_after_uncertain(monkeypatch) -> None:
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, _serverchan_fake_key())
    task_id = "serverchan-ledger-uncertain"
    key = _serverchan_queue(task_id)
    calls = {"count": 0}

    def dead_transport(endpoint: str, payload: dict) -> dict:
        calls["count"] += 1
        return {"ok": False, "error": "synthetic_permanent"}

    for _ in range(hello_module.SERVERCHAN_MAX_ATTEMPTS):
        hello_module.deliver_serverchan_envelope(key, transport=dead_transport)
    assert calls["count"] == hello_module.SERVERCHAN_MAX_ATTEMPTS

    blocked = hello_module.deliver_serverchan_envelope(key, transport=dead_transport)
    assert blocked["state"] == "blocked"
    assert blocked["fail_closed"] is True
    assert blocked["external_blocker"] == hello_module.BLOCKED_DELIVERY_FAIL_CLOSED
    assert calls["count"] == hello_module.SERVERCHAN_MAX_ATTEMPTS  # no blind resend


_XPROC_SERVERCHAN_SCRIPT = r'''
import json
import os
import sys

repo = os.environ["HELLO_REPO"]
if repo not in sys.path:
    sys.path.insert(0, repo)
import hello  # noqa: E402

task_id = os.environ["XPROC_TASK"]
consumer = os.environ["XPROC_CONSUMER"]
marker = os.environ["XPROC_MARKER"]

# Rebuild the logical notification from scratch in THIS process, exactly like a
# fresh workflow rerun. Only the durable delivery ledger is shared.
hello.submit_task(
    task_id,
    goal=hello.SERVERCHAN_ADAPTER_GOAL,
    status="success",
    requires_review=True,
)
hello.mark_reviewed(task_id, "PASS", "xproc setup")
hello.enqueue_push_envelopes(consumer, task_id=task_id)
key = hello.list_push_envelopes(task_id=task_id)[0]["dedupe_key"]


def fake_transport(endpoint, payload):
    with open(marker, "w", encoding="utf-8") as handle:
        handle.write("called")
    return {"ok": True, "status_code": 200, "push_id": "pid-xproc"}


result = hello.deliver_serverchan_envelope(key, transport=fake_transport)
print(json.dumps({
    "state": result.get("state"),
    "already_delivered": bool(result.get("already_delivered")),
    "transport_called": os.path.exists(marker),
}))
'''


def _xproc_state_env(tmp_path, tag: str, shared_ledger) -> dict:
    base_env = dict(os.environ)
    base_env.update(
        {
            "HELLO_REPO": str(hello_module.REPO_ROOT),
            "XPROC_TASK": "serverchan-xproc-task",
            "XPROC_CONSUMER": f"serverchan-xproc-consumer-{tag}",
            hello_module.SERVERCHAN_SENDKEY_ENV: _serverchan_fake_key(),
            hello_module.DELIVERY_LEDGER_STATE_ENV: str(shared_ledger),
            hello_module.PUSH_OUTBOX_STATE_ENV: str(tmp_path / f"outbox-{tag}.json"),
            hello_module.EVENT_NOTIFICATION_STATE_ENV: str(
                tmp_path / f"notif-{tag}.json"
            ),
            hello_module.NOTIFICATION_DELIVERY_STATE_ENV: str(
                tmp_path / f"deliveries-{tag}.json"
            ),
            hello_module.CONSUMER_EVIDENCE_ENV: str(
                tmp_path / f"evidence-{tag}.json"
            ),
            "XPROC_MARKER": str(tmp_path / f"marker-{tag}"),
        }
    )
    # A genuinely independent process has neither the pytest marker nor the
    # in-module isolation env; only the durable ledger can dedupe it.
    base_env.pop(hello_module.SERVERCHAN_TEST_ISOLATION_ENV, None)
    base_env.pop("PYTEST_CURRENT_TEST", None)
    return base_env


def test_durable_dedupe_across_independent_processes(tmp_path) -> None:
    ledger_path = tmp_path / "delivery_ledger.json"

    first = subprocess.run(
        [sys.executable, "-c", _XPROC_SERVERCHAN_SCRIPT],
        env=_xproc_state_env(tmp_path, "first", ledger_path),
        capture_output=True,
        text=True,
        cwd=str(hello_module.REPO_ROOT),
    )
    assert first.returncode == 0, first.stderr
    first_result = json.loads(first.stdout.strip().splitlines()[-1])
    assert first_result["state"] == "delivered"
    assert first_result["transport_called"] is True

    # Second independent process: fresh outbox / notification / evidence state,
    # so the ONLY durable signal left is the shared ledger. It must suppress the
    # send (already_delivered) without calling the transport.
    second = subprocess.run(
        [sys.executable, "-c", _XPROC_SERVERCHAN_SCRIPT],
        env=_xproc_state_env(tmp_path, "second", ledger_path),
        capture_output=True,
        text=True,
        cwd=str(hello_module.REPO_ROOT),
    )
    assert second.returncode == 0, second.stderr
    second_result = json.loads(second.stdout.strip().splitlines()[-1])
    assert second_result["already_delivered"] is True
    assert second_result["state"] == "delivered"
    assert second_result["transport_called"] is False
    assert not (tmp_path / "marker-second").exists()

    persisted = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert persisted["kind"] == hello_module.DELIVERY_LEDGER_EVIDENCE_KIND
    delivered = [
        record
        for record in persisted["deliveries"].values()
        if record.get("state") == "delivered"
    ]
    assert len(delivered) == 1
    assert delivered[0]["push_id"] == "pid-xproc"


# ---------------------------------------------------------------------------
# PERSONAL_AI_EXECUTION_B_DEDICATED_PUSH_STEP_DESIGN_AND_IMPLEMENT_01
# (task cf-94cafa503270)
#
# The production push entrypoint reads a terminal result and delivers at most one
# ServerChan notification through the existing adapter + durable ledger. Every
# test here uses a fake credential and a fake transport, so the real HTTPS leg is
# never entered and no WeChat notification is produced.
# ---------------------------------------------------------------------------


def test_notification_classification_for_result_terminal_states() -> None:
    cases = (
        ({"classification": "PASS"}, "PASS"),
        ({"review_verdict": "FAIL"}, "FAIL"),
        ({"final_status": "BLOCKED_EVIDENCE_MISSING"}, "BLOCKED"),
        ({"status": "success"}, "PENDING_APPROVAL"),
        ({"final_status": "PASSED"}, "PASS"),
        ({"status": "blocked"}, "BLOCKED"),
    )
    for result, expected in cases:
        decision = hello_module.notification_classification_for_result(result)
        assert decision["notifiable"] is True
        assert decision["classification"] == expected


def test_notification_classification_for_result_non_terminal_is_skipped() -> None:
    for state in ("pending", "queued", "running", "in_progress"):
        decision = hello_module.notification_classification_for_result(
            {"status": state}
        )
        assert decision["notifiable"] is False
        assert decision["classification"] is None
    assert (
        hello_module.notification_classification_for_result({})["notifiable"]
        is False
    )


def test_build_result_notification_requires_task_and_classification() -> None:
    with pytest.raises(ValueError):
        hello_module.build_result_notification(
            {"task_id": "t", "status": "running"}
        )
    with pytest.raises(ValueError):
        hello_module.build_result_notification({"classification": "PASS"})
    with pytest.raises(TypeError):
        hello_module.build_result_notification("not-a-dict")


def test_notification_push_delivers_once_and_dedupes_repeat(monkeypatch) -> None:
    monkeypatch.setenv(hello_module.SERVERCHAN_SENDKEY_ENV, _serverchan_fake_key())
    calls: list = []

    def fake_transport(endpoint: str, payload: dict) -> dict:
        calls.append((endpoint, payload))
        return {
            "ok": True,
            "status_code": 200,
            "push_id": "pid-push-once",
            "server_message": "SUCCESS",
        }

    result = {
        "task_id": "dedicated-push-once",
        "classification": "PASS",
        "summary": "dedicated push probe",
    }
    first = hello_module.run_notification_push(result, transport=fake_transport)
    assert first["dispatched"] is True
    assert first["notification_created"] is True
    assert first["classification"] == "PASS"
    assert first["dedupe_key"] == hello_module.push_envelope_dedupe_key(
        "dedicated-push-once", "PASS"
    )
    assert first["push_id"] == "pid-push-once"
    assert len(calls) == 1

    second = hello_module.run_notification_push(result, transport=fake_transport)
    assert second["already_delivered"] is True
    assert second["dispatched"] is True
    assert second["push_id"] == "pid-push-once"
    assert len(calls) == 1  # task_id+classification never consumes a 2nd send


def test_notification_push_without_credential_blocks_without_network(
    monkeypatch,
) -> None:
    monkeypatch.delenv(hello_module.SERVERCHAN_SENDKEY_ENV, raising=False)
    calls: list = []

    def fake_transport(endpoint: str, payload: dict) -> dict:
        calls.append(endpoint)
        return {"ok": True}

    result = hello_module.run_notification_push(
        {"task_id": "dedicated-push-nocred", "classification": "PASS"},
        transport=fake_transport,
    )
    assert result["delivery_state"] == "blocked"
    assert result["external_blocker"] == hello_module.BLOCKED_EXTERNAL_CREDENTIAL
    assert result["dispatched"] is False
    assert result["credential_present"] is False
    assert calls == []


def test_notification_push_skips_non_terminal_result() -> None:
    result = hello_module.run_notification_push(
        {"task_id": "dedicated-push-running", "status": "running"}
    )
    assert result["notifiable"] is False
    assert result["dispatched"] is False
    assert result["notification_created"] is False
    assert result["skipped_reason"]


def test_notification_push_reports_load_failure(tmp_path) -> None:
    missing = tmp_path / "nope.json"
    result = hello_module.run_notification_push(str(missing))
    assert result["loaded"] is False
    assert result["dispatched"] is False
    assert result["error"]


def test_notification_push_cli_describe_is_value_only(capsys) -> None:
    rc = hello_module.notification_push_cli(["--describe"])
    assert rc == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["command"] == hello_module.DEDICATED_PUSH_STEP_COMMAND
    assert printed["entrypoint"] == hello_module.DEDICATED_PUSH_STEP_ENTRYPOINT
    assert printed["ledger"]["identity_fields"] == ["task_id", "classification"]


def test_notification_push_cli_subprocess_is_credential_safe(tmp_path) -> None:
    result_path = tmp_path / "execution_result.json"
    result_path.write_text(
        json.dumps({"task_id": "cli-subproc-nocred", "classification": "PASS"}),
        encoding="utf-8",
    )
    env = dict(os.environ)
    env.pop(hello_module.SERVERCHAN_SENDKEY_ENV, None)
    env[hello_module.SERVERCHAN_TEST_ISOLATION_ENV] = "1"
    env[hello_module.DELIVERY_LEDGER_STATE_ENV] = str(tmp_path / "ledger.json")
    env[hello_module.PUSH_OUTBOX_STATE_ENV] = str(tmp_path / "outbox.json")
    env[hello_module.CONSUMER_EVIDENCE_ENV] = str(tmp_path / "evidence.json")
    proc = subprocess.run(
        [
            sys.executable,
            str(hello_module.REPO_ROOT / "hello.py"),
            "notification-push",
            "--result",
            str(result_path),
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=str(hello_module.REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["delivery_state"] == "blocked"
    assert out["external_blocker"] == hello_module.BLOCKED_EXTERNAL_CREDENTIAL
    assert out["notifiable"] is True


def test_dedicated_push_step_spec_names_command_env_and_ledger() -> None:
    spec = hello_module.dedicated_push_step_spec()
    assert "notification-push" in spec["command"]
    assert spec["env"][hello_module.DELIVERY_LEDGER_STATE_ENV]
    assert spec["env"][hello_module.SERVERCHAN_SENDKEY_ENV] == (
        "${{ secrets." + hello_module.SERVERCHAN_SENDKEY_ENV + " }}"
    )
    ledger = spec["ledger"]
    assert ledger["env"] == hello_module.DELIVERY_LEDGER_STATE_ENV
    assert ledger["identity_fields"] == ["task_id", "classification"]
    assert ledger["persist_across_rerun"] is True
    assert ledger["cache_key_prefix"] == hello_module.DEDICATED_PUSH_STEP_CACHE_PREFIX
    assert "actions/cache" in ledger["persistence_mechanism"]
    assert spec["workflow_modified"] is False
    assert spec["human_review_gate"] is True
    assert "notification-push" in spec["workflow_step_yaml"]


def test_dedicated_push_step_report_is_offline_and_passes() -> None:
    hello_module.reset_serverchan_test_isolation_counters()
    report = hello_module.dedicated_push_step_report()
    assert report["final_status"] == "PASS"
    assert report["real_notification_sent"] is False
    assert report["transport_calls"] == 4
    assert hello_module.serverchan_real_network_attempts() == 0
    assert report["workflow_modified"] is False
    for check in report["checks"]:
        assert check["status"] in VALID_STATUSES
        assert check["detail"]


_XPROC_PUSH_STEP_SCRIPT = r'''
import json
import os
import sys

repo = os.environ["HELLO_REPO"]
if repo not in sys.path:
    sys.path.insert(0, repo)
import hello  # noqa: E402

marker = os.environ["XPROC_MARKER"]
result_path = os.environ["XPROC_RESULT"]


def fake_transport(endpoint, payload):
    with open(marker, "w", encoding="utf-8") as handle:
        handle.write("called")
    return {"ok": True, "status_code": 200, "push_id": "pid-xproc-push"}


outcome = hello.run_notification_push(result_path, transport=fake_transport)
print(json.dumps({
    "classification": outcome.get("classification"),
    "state": outcome.get("delivery_state"),
    "already_delivered": bool(outcome.get("already_delivered")),
    "transport_called": os.path.exists(marker),
}))
'''


def _xproc_push_env(tmp_path, tag: str, ledger_path, result_path) -> dict:
    base_env = dict(os.environ)
    base_env.update(
        {
            "HELLO_REPO": str(hello_module.REPO_ROOT),
            hello_module.SERVERCHAN_SENDKEY_ENV: _serverchan_fake_key(),
            hello_module.DELIVERY_LEDGER_STATE_ENV: str(ledger_path),
            hello_module.PUSH_OUTBOX_STATE_ENV: str(
                tmp_path / f"push-outbox-{tag}.json"
            ),
            hello_module.CONSUMER_EVIDENCE_ENV: str(
                tmp_path / f"push-evidence-{tag}.json"
            ),
            "XPROC_MARKER": str(tmp_path / f"push-marker-{tag}"),
            "XPROC_RESULT": str(result_path),
        }
    )
    # A genuinely independent process must not see the pytest isolation marker;
    # only the shared durable ledger can dedupe it.
    base_env.pop(hello_module.SERVERCHAN_TEST_ISOLATION_ENV, None)
    base_env.pop("PYTEST_CURRENT_TEST", None)
    return base_env


def test_dedicated_push_step_dedupes_across_independent_processes(tmp_path) -> None:
    ledger_path = tmp_path / "push_delivery_ledger.json"
    result_path = tmp_path / "execution_result.json"
    result_path.write_text(
        json.dumps(
            {
                "task_id": "dedicated-push-xproc",
                "classification": "PASS",
                "summary": "cross-process dedicated push",
            }
        ),
        encoding="utf-8",
    )

    first = subprocess.run(
        [sys.executable, "-c", _XPROC_PUSH_STEP_SCRIPT],
        env=_xproc_push_env(tmp_path, "first", ledger_path, result_path),
        capture_output=True,
        text=True,
        cwd=str(hello_module.REPO_ROOT),
    )
    assert first.returncode == 0, first.stderr
    first_result = json.loads(first.stdout.strip().splitlines()[-1])
    assert first_result["state"] == "delivered"
    assert first_result["classification"] == "PASS"
    assert first_result["transport_called"] is True

    # Fresh outbox / evidence; only the shared ledger survives. The same
    # task_id+classification must suppress the second transport call.
    second = subprocess.run(
        [sys.executable, "-c", _XPROC_PUSH_STEP_SCRIPT],
        env=_xproc_push_env(tmp_path, "second", ledger_path, result_path),
        capture_output=True,
        text=True,
        cwd=str(hello_module.REPO_ROOT),
    )
    assert second.returncode == 0, second.stderr
    second_result = json.loads(second.stdout.strip().splitlines()[-1])
    assert second_result["already_delivered"] is True
    assert second_result["state"] == "delivered"
    assert second_result["transport_called"] is False
    assert not (tmp_path / "push-marker-second").exists()

    persisted = json.loads(ledger_path.read_text(encoding="utf-8"))
    delivered = [
        record
        for record in persisted["deliveries"].values()
        if record.get("state") == "delivered"
    ]
    assert len(delivered) == 1
    assert delivered[0]["push_id"] == "pid-xproc-push"
