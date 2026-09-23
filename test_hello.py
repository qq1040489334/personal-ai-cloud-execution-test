"""Automated test for hello.py."""

from datetime import datetime

from hello import (
    DEPLOY_VERIFY_COMMIT,
    DEPLOY_VERIFY_TASK_ID,
    REQUIRED_RESULT_FIELDS,
    cloud_agent_test,
    cloud_agent_test_2,
    cloud_asset_status,
    cloudflare_mcp_test,
    get_task_result,
    goodbye,
    gpt_bridge_test,
    hello,
    mcp_bridge_test,
    mcp_runtime_deploy_verify,
    oauth_mcp_test,
    security_test,
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
