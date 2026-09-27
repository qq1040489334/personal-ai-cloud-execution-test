"""Tests for PERSONAL_AI_CANONICAL_WORKER_CONTROLLED_PRODUCTION_DEPLOY_V0.1.

Task: ``cf-7afde7d95cdb``.

These tests validate both the read-only preflight/deploy-gate engine and the
committed evidence artifacts. They assert the fail-closed contract:

* a production deployment is never claimed without a Cloudflare deploy
  credential and without canonical-source verification;
* no production mutation and no secret exposure is ever claimed;
* the committed JSON/markdown evidence is self-consistent and reproducible;
* the commit -> source hash -> Cloudflare deployment/version link is recorded as
  incomplete while the deploy is blocked, so the next runtime provenance audit
  can verify it once a real deployment exists.
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = REPORTS_DIR.parent
if str(REPORTS_DIR) not in sys.path:
    sys.path.insert(0, str(REPORTS_DIR))

import production_deploy_v0_1 as deploy  # noqa: E402

VALID_VERDICTS = {"PASS", "FAIL", "BLOCKED"}
HEAD_VOLATILE = (
    ("canonical_head_commit",),
    ("preflight", "canonical_head_commit"),
    ("preflight", "canonical_head_date"),
    ("preflight", "origin_main_commit"),
    ("provenance_chain", "git_commit"),
    ("provenance_chain", "git_commit_date"),
)


def _normalized(report: dict) -> dict:
    data = copy.deepcopy(report)
    data.pop("generated_at", None)
    data.pop("markdown", None)
    for path in HEAD_VOLATILE:
        cursor = data
        for key in path[:-1]:
            cursor = cursor.get(key, {})
        cursor.pop(path[-1], None)
    return data


# --- report shape and fail-closed verdict ----------------------------------


def test_report_shape_and_gates() -> None:
    report = deploy.build_report()
    assert report["report"] == deploy.REPORT_NAME
    assert report["goal"] == deploy.GOAL
    assert report["task_id"] == deploy.TASK_ID
    assert report["generated_at"]
    assert set(deploy.REPORT_FIELDS) <= set(report)
    assert report["gates"]
    for gate in report["gates"]:
        assert set(gate) >= {"gate", "status", "detail"}
        assert gate["status"] in VALID_VERDICTS
        assert gate["detail"]
    assert report["overall"] in VALID_VERDICTS
    assert report["verdict"] == report["overall"]


def test_no_credential_means_blocked_and_no_deploy_attempt() -> None:
    # In this execution environment no Cloudflare deploy credential is present.
    assert deploy._env_names_present(deploy.DEPLOY_TOKEN_ENV) == []
    report = deploy.build_report()
    assert report["verdict"] == "BLOCKED"
    assert report["overall"] == "BLOCKED"
    assert report["deployment_attempted"] is False
    assert report["deployment"] is None
    assert report["production_mutated"] is False
    assert report["secrets_exposed"] is False
    check = next(g for g in report["gates"] if g["gate"] == "Cloudflare deploy credential available")
    assert check["status"] == "BLOCKED"


def test_no_fabricated_success_ever() -> None:
    report = deploy.build_report()
    if report["overall"] == "PASS":
        assert report["deployment_attempted"] is True
        assert report["deployment"]
        assert report["live_verification"]["performed"] is True
    else:
        assert report["deployment_attempted"] is False
        assert report["live_verification"]["performed"] is False


# --- canonical source preflight --------------------------------------------


def test_canonical_source_hash_matches_repository_file() -> None:
    report = deploy.build_report()
    source = report["preflight"]["canonical_source"]
    actual = deploy._sha256_file(REPO_ROOT / deploy.CANONICAL_SOURCE)
    assert source["file"] == deploy.CANONICAL_SOURCE
    assert source["present"] is True
    assert source["sha256"] == actual
    assert source["bytes"] == (REPO_ROOT / deploy.CANONICAL_SOURCE).stat().st_size
    assert source["bytes"] > 0
    assert source["lines"] > 0


def test_canonical_head_is_recorded() -> None:
    report = deploy.build_report()
    assert report["canonical_head_commit"] == deploy._git("rev-parse", "HEAD")
    assert report["preflight"]["canonical_head_commit"] == report["canonical_head_commit"]


def test_worker_bindings_preflight() -> None:
    report = deploy.build_report()
    bindings = report["preflight"]["bindings"]
    assert bindings["ASSET_DB"] == "45d6f18a-3a34-4ccd-8337-c00a775cd7a2"
    assert bindings["TASK_REGISTRY"] == "60f6203f262d44378abd0accfa7fef46"
    gate = next(g for g in report["gates"] if g["gate"] == "worker bindings present")
    assert gate["status"] == "PASS"


def test_secret_names_are_reported_but_values_are_not() -> None:
    report = deploy.build_report()
    expected = {"GITHUB_TOKEN", "MCP_AUTH_TOKEN", "OAUTH_SIGNING_KEY", "OWNER_PASSWORD"}
    assert expected <= set(report["preflight"]["secret_names"])
    assert report["preflight"]["credentials"]["values_recorded"] is False
    # No secret value from the environment may appear in the evidence.
    text = json.dumps(report) + report["markdown"]
    for name in ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN", "CLOUDFLARE_API_KEY"):
        value = os.environ.get(name, "")
        if value:
            assert value not in text


# --- migration compatibility -----------------------------------------------


def test_migration_is_additive_idempotent_and_non_destructive() -> None:
    report = deploy.build_report()
    migration = report["preflight"]["migration"]
    assert migration["path"] == deploy.MIGRATION_PATH
    assert migration["present"] is True
    assert migration["additive"] is True
    assert migration["idempotent"] is True
    assert migration["destructive_statements"] == []
    assert migration["required_by_worker_source"] is False
    assert migration["applied"] is False
    assert "wrangler d1 execute" in migration["apply_method"]
    gate = next(g for g in report["gates"] if g["gate"].startswith("asset provenance migration"))
    assert gate["status"] == "PASS"


# --- provenance chain ------------------------------------------------------


def test_provenance_chain_incomplete_while_blocked() -> None:
    report = deploy.build_report()
    chain = report["provenance_chain"]
    assert chain["git_commit"]
    assert chain["source_file"] == deploy.CANONICAL_SOURCE
    assert chain["source_sha256"] == report["preflight"]["canonical_source"]["sha256"]
    assert chain["cloudflare_deployment_id"] is None
    assert chain["cloudflare_version"] is None
    assert chain["deployment_timestamp"] is None
    assert chain["link_status"] == "INCOMPLETE_BLOCKED"
    assert chain["prior_production_version"] == "3e2fed43"


def test_live_verification_not_performed_and_planned_checks_listed() -> None:
    report = deploy.build_report()
    live = report["live_verification"]
    assert live["performed"] is False
    checks = {c["check"] for c in live["planned_read_only_checks"]}
    assert "health endpoint" in checks
    assert "auth boundary" in checks
    assert "MCP tools/list schema" in checks
    assert "get_task_result truthfulness" in checks
    assert "asset provenance read/search path" in checks


# --- committed artifacts ---------------------------------------------------


def test_committed_json_artifact_is_consistent() -> None:
    json_path = REPO_ROOT / deploy.JSON_ARTIFACT
    assert json_path.is_file(), f"missing committed artifact {deploy.JSON_ARTIFACT}"
    committed = json.loads(json_path.read_text(encoding="utf-8"))
    fresh = deploy.build_report()

    # The markdown must be exactly reproducible from the committed JSON.
    assert committed["markdown"] == deploy.render_markdown(committed)
    assert _normalized(committed) == _normalized(fresh)


def test_committed_markdown_artifact_present() -> None:
    md_path = REPO_ROOT / deploy.MARKDOWN_ARTIFACT
    assert md_path.is_file(), f"missing committed artifact {deploy.MARKDOWN_ARTIFACT}"
    markdown = md_path.read_text(encoding="utf-8")
    committed = json.loads((REPO_ROOT / deploy.JSON_ARTIFACT).read_text(encoding="utf-8"))
    assert markdown == committed["markdown"] + "\n"
    assert f"VERDICT={committed['verdict']}" in markdown
    assert "PRODUCTION_MUTATED=False" in markdown
    assert "SECRETS_EXPOSED=False" in markdown


def test_baseline_records_blocked_deploy_without_changing_production_identity() -> None:
    baseline = deploy._load_json(REPO_ROOT / deploy.BASELINE_PATH)
    assert baseline is not None
    # Declared production identity is preserved, never overwritten by a blocked attempt.
    assert baseline["production_version"] == "3e2fed43"
    assert (
        baseline["source_sha256"]
        == "8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1"
    )
    record = baseline["controlled_deploy_v0_1"]
    assert record["task_id"] == deploy.TASK_ID
    assert record["result"] == "BLOCKED"
    assert record["deployment_attempted"] is False
    assert record["production_mutated"] is False
    assert record["cloudflare_deployment_id"] is None
    assert record["cloudflare_version"] is None
    assert record["evidence_artifact"] == deploy.JSON_ARTIFACT
    assert record["canonical_source_sha256"] == deploy.build_report()["preflight"]["canonical_source"]["sha256"]


def test_engine_does_not_mutate_repository_or_remote() -> None:
    before_status = deploy._git("status", "--porcelain")
    before_source = deploy._sha256_file(REPO_ROOT / deploy.CANONICAL_SOURCE)
    report = deploy.build_report()
    after_status = deploy._git("status", "--porcelain")
    after_source = deploy._sha256_file(REPO_ROOT / deploy.CANONICAL_SOURCE)
    assert before_status == after_status
    assert before_source == after_source
    assert report["production_mutated"] is False
