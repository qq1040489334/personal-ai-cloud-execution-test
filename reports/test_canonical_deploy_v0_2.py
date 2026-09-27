"""Tests for CLOUDFLARE_WORKER_CANONICAL_DEPLOY_V0.2.

Task: ``cf-0fe692a1235b``.

These tests validate both the read-only deploy engine and the committed
evidence artifacts. They assert the acceptance contract:

* ``DEPLOY_STATUS`` is explicitly one of PASS/FAIL/BLOCKED;
* a successful deploy must return git commit, source hash, Cloudflare version
  id and deployment id -- a PASS without them is a fabricated success;
* the canonical source -> runtime provenance relationship is only VERIFIED when
  a real Cloudflare version id / deployment id exists;
* no secret value is ever exposed;
* no unrelated production resource is modified (exact binding/secret set is
  preserved and the production baseline is untouched).
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

import canonical_deploy_v0_2 as deploy  # noqa: E402

VALID_STATUS = {"PASS", "FAIL", "BLOCKED"}
HEAD_VOLATILE = (
    ("canonical", "git_commit"),
    ("preflight", "canonical_head_commit"),
    ("preflight", "canonical_head_date"),
    ("provenance", "git_commit"),
    ("provenance", "git_commit_date"),
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


# --- report shape and fail-closed status -----------------------------------


def test_report_shape_and_status_is_explicit() -> None:
    report = deploy.build_report()
    assert report["report"] == deploy.REPORT_NAME
    assert report["goal"] == deploy.GOAL
    assert report["task_id"] == deploy.TASK_ID
    assert report["generated_at"]
    assert set(deploy.REPORT_FIELDS) <= set(report)
    assert report["deploy_status"] in VALID_STATUS
    assert report["verdict"] == report["deploy_status"]
    assert report["overall"] == report["deploy_status"]
    for gate in report["gates"]:
        assert set(gate) >= {"gate", "status", "detail"}
        assert gate["status"] in VALID_STATUS
        assert gate["detail"]


def test_no_write_credential_means_blocked() -> None:
    # This execution environment exposes no Cloudflare write credential.
    assert deploy._env_names_present(deploy.DEPLOY_TOKEN_ENV) == []
    report = deploy.build_report()
    assert report["deploy_status"] == "BLOCKED"
    assert report["deployment_attempted"] is False
    assert report["production_mutated"] is False
    assert report["secrets_exposed"] is False
    assert report["cloudflare"]["version_id"] is None
    assert report["cloudflare"]["deployment_id"] is None
    assert report["provenance"]["relationship_status"] == "BLOCKED"


def test_success_requires_full_provenance_tuple() -> None:
    report = deploy.build_report()
    if report["deploy_status"] == "PASS":
        canonical = report["canonical"]
        assert canonical["git_commit"]
        assert canonical["source_sha256"]
        assert report["cloudflare"]["version_id"]
        assert report["cloudflare"]["deployment_id"]
        assert report["cloudflare"]["deployment_timestamp"]
        assert report["provenance"]["relationship_status"] == "VERIFIED"
        assert report["provenance"]["closed_on_deploy"] is True
        assert report["live_verification"]["performed"] is True
    else:
        assert report["cloudflare"]["version_id"] is None
        assert report["cloudflare"]["deployment_id"] is None
        assert report["provenance"]["relationship_status"] in {"BLOCKED", "UNVERIFIED"}


# --- canonical source / module worker --------------------------------------


def test_canonical_source_hash_matches_repository_file() -> None:
    report = deploy.build_report()
    canonical = report["canonical"]
    assert canonical["source_file"] == deploy.CANONICAL_SOURCE
    assert canonical["source_sha256"] == deploy._sha256_file(
        REPO_ROOT / deploy.CANONICAL_SOURCE
    )
    assert canonical["source_bytes"] == (
        REPO_ROOT / deploy.CANONICAL_SOURCE
    ).stat().st_size
    assert canonical["source_lines"] > 0
    assert report["canonical"]["git_commit"] == deploy._git("rev-parse", "HEAD")


def test_canonical_source_is_a_module_worker() -> None:
    report = deploy.build_report()
    source = report["preflight"]["canonical_source"]
    assert source["module_worker"] is True
    gate = next(
        g for g in report["gates"] if g["gate"].startswith("module worker syntax")
    )
    assert gate["status"] == "PASS"


def test_module_upload_metadata_uses_main_module_and_preserves_bindings() -> None:
    report = deploy.build_report()
    upload = report["module_upload"]
    assert upload["format"] == "module"
    assert upload["main_module"] == "index.js"
    assert upload["module_content_type"] == "application/javascript+module"
    metadata = upload["metadata"]
    assert metadata["main_module"] == "index.js"
    assert metadata["keep_bindings"] == ["secret_text"]
    binding_names = {b["name"] for b in metadata["bindings"]}
    binding_names |= set(metadata["preserved_secret_bindings"])
    assert binding_names == set(deploy.PRESERVED_BINDING_NAMES)
    assert set(deploy.SECRET_BINDING_NAMES) == set(metadata["preserved_secret_bindings"])
    gate = next(
        g for g in report["gates"] if "preserved binding/secret names" in g["gate"]
    )
    assert gate["status"] == "PASS"


def test_versions_api_used_instead_of_content_endpoint() -> None:
    report = deploy.build_report()
    plan = report["versions_api"]
    assert plan["strategy"] == "versions_api"
    assert "legacy_content_endpoint_retry" in plan["forbidden_strategies"]
    assert plan["create_version"]["path"].endswith("/versions")
    assert plan["create_version"]["method"] == "POST"
    assert plan["create_deployment"]["path"].endswith("/deployments")
    assert plan["create_deployment"]["body"]["percentage"] == 100


# --- secret non-exposure and production preservation -----------------------


def test_secret_names_reported_but_values_never_recorded() -> None:
    report = deploy.build_report()
    assert set(deploy.SECRET_BINDING_NAMES) <= set(report["preflight"]["secret_names"])
    assert report["preflight"]["credentials"]["values_recorded"] is False
    text = json.dumps(report) + report["markdown"]
    for name in deploy.DEPLOY_TOKEN_ENV:
        value = os.environ.get(name, "")
        if value:
            assert value not in text
    for name in deploy.SECRET_BINDING_NAMES:
        value = os.environ.get(name, "")
        if value:
            assert value not in text


def test_production_resources_are_preserved_and_unmodified() -> None:
    baseline_before = deploy._sha256_file(REPO_ROOT / deploy.BASELINE_PATH)
    wrangler_before = deploy._sha256_file(REPO_ROOT / deploy.WRANGLER_CONFIG)
    source_before = deploy._sha256_file(REPO_ROOT / deploy.CANONICAL_SOURCE)

    report = deploy.build_report()

    assert report["production_mutated"] is False
    assert deploy._sha256_file(REPO_ROOT / deploy.BASELINE_PATH) == baseline_before
    assert deploy._sha256_file(REPO_ROOT / deploy.WRANGLER_CONFIG) == wrangler_before
    assert deploy._sha256_file(REPO_ROOT / deploy.CANONICAL_SOURCE) == source_before

    baseline = deploy._load_json(REPO_ROOT / deploy.BASELINE_PATH)
    assert baseline["production_version"] == "3e2fed43"
    assert baseline["bindings"]["ASSET_DB"] == "45d6f18a-3a34-4ccd-8337-c00a775cd7a2"
    assert (
        baseline["bindings"]["TASK_REGISTRY"]
        == "60f6203f262d44378abd0accfa7fef46"
    )


def test_no_fabricated_success_ever() -> None:
    report = deploy.build_report()
    if report["deploy_status"] == "PASS":
        assert report["deployment_attempted"] is True
        assert report["live_verification"]["performed"] is True
    else:
        assert report["deployment_attempted"] is False
        assert report["live_verification"]["performed"] is False


# --- committed artifacts ---------------------------------------------------


def test_committed_json_artifact_is_consistent() -> None:
    json_path = REPO_ROOT / deploy.JSON_ARTIFACT
    assert json_path.is_file(), f"missing committed artifact {deploy.JSON_ARTIFACT}"
    committed = json.loads(json_path.read_text(encoding="utf-8"))
    fresh = deploy.build_report()
    assert committed["markdown"] == deploy.render_markdown(committed)
    assert _normalized(committed) == _normalized(fresh)


def test_committed_markdown_artifact_present() -> None:
    md_path = REPO_ROOT / deploy.MARKDOWN_ARTIFACT
    assert md_path.is_file(), f"missing committed artifact {deploy.MARKDOWN_ARTIFACT}"
    markdown = md_path.read_text(encoding="utf-8")
    committed = json.loads(
        (REPO_ROOT / deploy.JSON_ARTIFACT).read_text(encoding="utf-8")
    )
    assert markdown == committed["markdown"] + "\n"
    assert f"DEPLOY_STATUS={committed['deploy_status']}" in markdown
    assert "PRODUCTION_MUTATED=False" in markdown
    assert "SECRETS_EXPOSED=False" in markdown


def test_engine_does_not_mutate_repository_or_remote() -> None:
    before_status = deploy._git("status", "--porcelain")
    report = deploy.build_report()
    after_status = deploy._git("status", "--porcelain")
    assert before_status == after_status
    assert report["production_mutated"] is False
