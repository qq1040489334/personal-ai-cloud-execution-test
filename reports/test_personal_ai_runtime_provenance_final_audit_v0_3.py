"""Tests for PERSONAL_AI_RUNTIME_PROVENANCE_FINAL_AUDIT_V0.3.

Task: ``cf-619649c43aa2`` (risk: LOW).

These tests validate both the read-only final-audit engine and the committed
evidence artifacts. They assert the fail-closed contract:

* production identity is only ``VERIFIED`` on authoritative evidence, never on
  self-declared metadata alone;
* the canonical-source-to-live-runtime relationship is only ``VERIFIED`` when a
  canonical commit blob hash matches the declared production source hash *and* a
  Cloudflare deployment/version record links it to the live runtime;
* status-contract and asset-provenance Worker changes are proven included or
  explicitly ``BLOCKED``;
* report-only documentation commits are separated from required-but-undeployed
  runtime commits;
* no production mutation and no secret exposure is ever claimed, and no
  live-verified PASS is fabricated;
* ``OVERALL=PASS`` is impossible unless the relationship is ``VERIFIED``.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = REPORTS_DIR.parent
if str(REPORTS_DIR) not in sys.path:
    sys.path.insert(0, str(REPORTS_DIR))

import personal_ai_runtime_provenance_final_audit_v0_3 as audit  # noqa: E402

VALID_OVERALL = {"PASS", "FAIL", "BLOCKED"}

#: Fields that legitimately move when the audit artifact itself is committed or
#: when it is re-run in a different environment (HEAD and environment values).
VOLATILE_KEYS = {"generated_at", "markdown", "audit_context", "report_only_commits"}
VOLATILE_IDENTITY_KEYS = {
    "env_commit",
    "env_commit_names",
    "env_version",
    "env_version_names",
}
VOLATILE_EVIDENCE_KEYS = {
    "authoritative",
    "authoritative_sources",
    "cloudflare_deploy_credential_names_present",
}


def _normalized(report: dict) -> dict:
    """Return a HEAD/environment-stable view of a report for comparison."""
    view = copy.deepcopy(report)
    for key in VOLATILE_KEYS:
        view.pop(key, None)
    view["canonical_source"].pop("head_commit", None)
    for key in VOLATILE_IDENTITY_KEYS:
        view["deployment_identity"].pop(key, None)
    for key in VOLATILE_EVIDENCE_KEYS:
        view["deployment_identity_evidence"].pop(key, None)
    return view


# --- shape / evidence -------------------------------------------------------


def test_report_shape_and_fields() -> None:
    report = audit.build_report()
    assert report["report"] == audit.REPORT_NAME
    assert report["goal"] == "PERSONAL_AI_RUNTIME_PROVENANCE_FINAL_AUDIT_V0.3"
    assert report["task_id"] == "cf-619649c43aa2"
    assert set(audit.REPORT_FIELDS) <= set(report)
    assert report["generated_at"]
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in {"PASS", "FAIL", "BLOCKED"}
        assert check["detail"]
    assert report["overall"] in VALID_OVERALL


def test_deployment_identity_reported_from_baseline_evidence() -> None:
    report = audit.build_report()
    baseline = audit._load_json(audit.BASELINE_PATH)
    assert baseline is not None
    identity = report["deployment_identity"]
    assert identity["service"] == baseline["service"]
    assert identity["environment"] == baseline["environment"]
    assert identity["production_version"] == baseline["production_version"]
    assert identity["metadata_path"] == audit.BASELINE_PATH


def test_identity_classifier_is_fail_closed() -> None:
    assert (
        audit.classify_deployment_identity(
            metadata_present=False,
            version=None,
            service=None,
            authoritative_evidence=False,
        )
        == audit.RELATIONSHIP_UNVERIFIED
    )
    # Self-declared baseline only -> declared, not independently confirmed.
    assert (
        audit.classify_deployment_identity(
            metadata_present=True,
            version="3e2fed43",
            service="personal-ai-execution-mcp",
            authoritative_evidence=False,
        )
        == audit.RELATIONSHIP_PARTIAL
    )
    assert (
        audit.classify_deployment_identity(
            metadata_present=True,
            version="3e2fed43",
            service="personal-ai-execution-mcp",
            authoritative_evidence=True,
        )
        == audit.RELATIONSHIP_VERIFIED
    )


def test_relationship_classifier_is_fail_closed() -> None:
    assert (
        audit.classify_relationship(
            metadata_present=False,
            declared_hash=None,
            matching_on_history=False,
            matching_any=False,
            deployment_record_linked=False,
        )
        == audit.RELATIONSHIP_UNVERIFIED
    )
    assert (
        audit.classify_relationship(
            metadata_present=True,
            declared_hash=None,
            matching_on_history=False,
            matching_any=False,
            deployment_record_linked=False,
        )
        == audit.RELATIONSHIP_UNVERIFIED
    )
    assert (
        audit.classify_relationship(
            metadata_present=True,
            declared_hash="abc",
            matching_on_history=False,
            matching_any=False,
            deployment_record_linked=True,
        )
        == audit.RELATIONSHIP_UNVERIFIED
    )
    # Match exists but no Cloudflare deployment link -> only PARTIAL.
    assert (
        audit.classify_relationship(
            metadata_present=True,
            declared_hash="abc",
            matching_on_history=True,
            matching_any=True,
            deployment_record_linked=False,
        )
        == audit.RELATIONSHIP_PARTIAL
    )
    # Match on history with a deployment link -> VERIFIED.
    assert (
        audit.classify_relationship(
            metadata_present=True,
            declared_hash="abc",
            matching_on_history=True,
            matching_any=True,
            deployment_record_linked=True,
        )
        == audit.RELATIONSHIP_VERIFIED
    )


def test_declared_source_matches_baseline_evidence() -> None:
    report = audit.build_report()
    baseline = audit._load_json(audit.BASELINE_PATH)
    assert report["declared_source"]["file"] == baseline["source_file"]
    assert report["declared_source"]["sha256"] == baseline["source_sha256"]
    assert report["declared_source"]["bytes"] == baseline["source_bytes"]
    assert report["declared_source"]["lines"] == baseline["source_lines"]


def test_canonical_commit_and_exact_source_hash_verified() -> None:
    report = audit.build_report()
    canonical = report["canonical_source"]
    source = REPO_ROOT / audit.CANONICAL_SOURCE
    assert canonical["present"] is True
    assert source.is_file()
    assert canonical["head_sha256"] == audit._sha256_file(source)
    assert canonical["head_bytes"] == source.stat().st_size
    assert canonical["head_lines"] == len(
        source.read_text(encoding="utf-8", errors="ignore").splitlines()
    )
    assert canonical["last_source_commit"]


def test_deployed_runtime_not_traceable_to_commit_in_this_repo() -> None:
    report = audit.build_report()
    declared = report["declared_source"]["sha256"]
    canonical = report["canonical_source"]["head_sha256"]
    assert declared
    assert canonical
    assert declared.lower() != canonical.lower()
    assert report["canonical_source"]["matches_declared_hash"] is False
    assert report["matching_source_commits"] == []
    assert report["relationship_status"] == audit.RELATIONSHIP_UNVERIFIED


def test_cloudflare_deployment_link_is_absent() -> None:
    report = audit.build_report()
    identity = report["deployment_identity"]
    # The controlled deploy was blocked before any deployment, so no
    # Cloudflare deployment/version exists to link source to runtime.
    assert identity["cloudflare_deployment_id"] is None
    assert identity["cloudflare_version"] is None
    assert identity["deployment_timestamp"] is None
    assert identity["deploy_attempted"] is False
    assert report["deployment_identity_status"] != audit.RELATIONSHIP_VERIFIED


def test_relationship_status_classified_from_evidence() -> None:
    report = audit.build_report()
    assert report["relationship_status"] in audit.RELATIONSHIP_STATUSES
    assert report["relationship_reason"]
    if report["matching_source_commits"]:
        assert all(
            c["on_current_history"] for c in report["matching_source_commits"]
        )
    else:
        assert report["relationship_status"] != audit.RELATIONSHIP_VERIFIED
        assert report["overall"] != "PASS"


# --- runtime change inclusion ----------------------------------------------


def test_status_contract_and_asset_provenance_changes_present_and_blocked() -> None:
    report = audit.build_report()
    status = report["runtime_changes"]["status_contract"]
    provenance = report["runtime_changes"]["asset_provenance"]

    assert status["canonical_source_includes_change"] is True
    assert provenance["canonical_source_includes_change"] is True
    assert status["missing_tokens"] == []
    assert provenance["missing_tokens"] == []

    # Deployment inclusion cannot be proven while the deployed source hash is
    # not tied to a canonical commit -> explicitly BLOCKED, not silently PASS.
    for section in (status, provenance):
        assert section["deployed_inclusion_proven"] is False
        assert section["status"] == "BLOCKED"
        assert "not proven" in section["detail"]
        assert section["source_commits"]


def test_runtime_change_source_commits_are_identified() -> None:
    report = audit.build_report()
    status_commits = report["runtime_changes"]["status_contract"]["source_commits"]
    provenance_commits = report["runtime_changes"]["asset_provenance"][
        "source_commits"
    ]
    assert "0c3ac20392bf86bfecb68cbaadd77a7a2a398665" in status_commits
    assert "592e7c29af4a5e72e3ec12bb458538629011896b" in provenance_commits


def test_report_only_commits_separated_from_runtime_changes() -> None:
    report = audit.build_report()
    report_only = {c["commit"] for c in report["report_only_commits"]}
    runtime = {
        c["commit"] for c in report["execution_relevant_undeployed_commits"]
    }
    # 824bd4c only touched STATUS_CONTRACT_V0.2.md -> report-only.
    assert "824bd4c415554e111787d3fc1b1632e28863179b" in report_only
    assert "824bd4c415554e111787d3fc1b1632e28863179b" not in runtime
    # The worker-touching status/provenance commits are runtime changes, unproven.
    for commit in (
        "0c3ac20392bf86bfecb68cbaadd77a7a2a398665",
        "592e7c29af4a5e72e3ec12bb458538629011896b",
    ):
        assert commit in runtime
    for entry in report["execution_relevant_undeployed_commits"]:
        assert entry["proven_deployed"] is False
        assert "not deployment evidence" in entry["reason"]
    for entry in report["report_only_commits"]:
        assert not any(
            audit._is_execution_relevant(p) for p in entry["changed_paths"]
        )


# --- fail-closed guarantees -------------------------------------------------


def test_no_production_mutation() -> None:
    report = audit.build_report()
    assert report["production_mutated"] is False
    assert report["secrets_exposed"] is False
    assert report["read_only"] is True
    assert report["live_endpoint_checked"] is False
    check = next(
        c for c in report["checks"] if c["check"] == "no production mutation"
    )
    assert check["status"] == "PASS"


def test_no_fabricated_pass() -> None:
    report = audit.build_report()
    if report["relationship_status"] != audit.RELATIONSHIP_VERIFIED:
        assert report["overall"] != "PASS"
    if report["overall"] == "PASS":
        assert report["relationship_status"] == audit.RELATIONSHIP_VERIFIED
        assert (
            report["deployment_identity_status"] == audit.RELATIONSHIP_VERIFIED
        )
        assert all(c["status"] == "PASS" for c in report["checks"])


def test_live_endpoint_checks_not_fabricated() -> None:
    report = audit.build_report()
    live = report["live_endpoint_checks"]
    assert live["performed"] is False
    assert live["planned_read_only_checks"]
    assert report["live_endpoint_checked"] is False


def test_remaining_gap_is_explicit_and_actionable() -> None:
    report = audit.build_report()
    assert report["remaining_gap"]
    joined = " ".join(report["remaining_gap"])
    assert "credential" in joined
    assert "matches no canonical" in joined
    assert "VERIFIED" in joined


def test_audit_does_not_mutate_repository() -> None:
    before_status = audit._git("status", "--porcelain")
    before_source = audit._sha256_file(REPO_ROOT / audit.CANONICAL_SOURCE)
    before_baseline = audit._sha256_file(REPO_ROOT / audit.BASELINE_PATH)
    report = audit.build_report()
    after_status = audit._git("status", "--porcelain")
    after_source = audit._sha256_file(REPO_ROOT / audit.CANONICAL_SOURCE)
    after_baseline = audit._sha256_file(REPO_ROOT / audit.BASELINE_PATH)
    assert before_status == after_status
    assert before_source == after_source
    assert before_baseline == after_baseline
    assert report["production_mutated"] is False


# --- markdown / committed artifacts -----------------------------------------


def test_markdown_tokens() -> None:
    report = audit.build_report()
    markdown = report["markdown"]
    assert markdown.startswith(f"# {audit.REPORT_NAME}")
    assert f"- task_id: {audit.TASK_ID}" in markdown
    assert f"RELATIONSHIP_STATUS={report['relationship_status']}" in markdown
    assert "PRODUCTION_MUTATED=False" in markdown
    assert "SECRETS_EXPOSED=False" in markdown
    assert f"OVERALL={report['overall']}" in markdown


def test_committed_json_artifact_is_consistent() -> None:
    json_path = REPO_ROOT / audit.JSON_ARTIFACT
    assert json_path.is_file(), f"missing committed artifact {audit.JSON_ARTIFACT}"
    committed = json.loads(json_path.read_text(encoding="utf-8"))
    fresh = audit.build_report()

    # The markdown must be exactly reproducible from the committed JSON.
    assert committed["markdown"] == audit.render_markdown(committed)

    assert _normalized(committed) == _normalized(fresh)


def test_committed_markdown_artifact_present() -> None:
    md_path = REPO_ROOT / audit.MARKDOWN_ARTIFACT
    assert md_path.is_file(), f"missing committed artifact {audit.MARKDOWN_ARTIFACT}"
    markdown = md_path.read_text(encoding="utf-8")
    committed = json.loads((REPO_ROOT / audit.JSON_ARTIFACT).read_text(encoding="utf-8"))
    assert markdown == committed["markdown"] + "\n"
