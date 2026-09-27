"""Tests for PERSONAL_AI_RUNTIME_PROVENANCE_V0.2 (task cf-883c3502ff24).

These tests validate both the audit engine and the committed evidence artifacts.
The audit is read-only; the tests assert that no production mutation is claimed
or performed, and that the canonical-source-to-runtime relationship is
classified fail-closed from evidence rather than inferred from repository
presence.
"""

from __future__ import annotations

import json

import runtime_provenance_v0_2 as rp

VALID_OVERALL = {"PASS", "FAIL", "BLOCKED"}


def test_report_shape_and_fields() -> None:
    report = rp.build_report()
    assert report["report"] == rp.REPORT_NAME
    assert report["goal"] == "PERSONAL_AI_RUNTIME_PROVENANCE_V0.2"
    assert report["task_id"] == "cf-883c3502ff24"
    assert set(rp.REPORT_FIELDS) <= set(report)
    assert report["generated_at"]
    assert report["checks"]
    for check in report["checks"]:
        assert set(check) >= {"check", "status", "detail"}
        assert check["status"] in {"PASS", "FAIL", "BLOCKED"}
        assert check["detail"]
    assert report["overall"] in VALID_OVERALL


def test_deployment_identity_reported_from_evidence() -> None:
    report = rp.build_report()
    baseline = rp._load_baseline()
    assert baseline is not None
    identity = report["deployment_identity"]
    assert identity["service"] == baseline["service"]
    assert identity["environment"] == baseline["environment"]
    assert identity["production_version"] == baseline["production_version"]
    assert identity["metadata_path"] == rp.BASELINE_PATH
    assert report["deployment_identity_status"] == rp.RELATIONSHIP_VERIFIED


def test_declared_source_matches_baseline_evidence() -> None:
    report = rp.build_report()
    baseline = rp._load_baseline()
    assert report["declared_source"]["file"] == baseline["source_file"]
    assert report["declared_source"]["sha256"] == baseline["source_sha256"]
    assert report["declared_source"]["bytes"] == baseline["source_bytes"]
    assert report["declared_source"]["lines"] == baseline["source_lines"]


def test_relationship_classifier_is_fail_closed() -> None:
    assert (
        rp.classify_relationship(
            metadata_present=False,
            declared_hash=None,
            matching_on_history=False,
            matching_any=False,
        )
        == rp.RELATIONSHIP_UNVERIFIED
    )
    assert (
        rp.classify_relationship(
            metadata_present=True,
            declared_hash=None,
            matching_on_history=False,
            matching_any=False,
        )
        == rp.RELATIONSHIP_UNVERIFIED
    )
    assert (
        rp.classify_relationship(
            metadata_present=True,
            declared_hash="abc",
            matching_on_history=False,
            matching_any=False,
        )
        == rp.RELATIONSHIP_UNVERIFIED
    )
    assert (
        rp.classify_relationship(
            metadata_present=True,
            declared_hash="abc",
            matching_on_history=False,
            matching_any=True,
        )
        == rp.RELATIONSHIP_PARTIAL
    )
    assert (
        rp.classify_relationship(
            metadata_present=True,
            declared_hash="abc",
            matching_on_history=True,
            matching_any=True,
        )
        == rp.RELATIONSHIP_VERIFIED
    )


def test_relationship_status_classified_from_evidence() -> None:
    report = rp.build_report()
    assert report["relationship_status"] in rp.RELATIONSHIP_STATUSES
    assert report["relationship_reason"]
    # The declared production source hash must match exactly one canonical
    # commit on current history to be VERIFIED; otherwise it must not be.
    if report["matching_source_commits"]:
        assert all(
            c["on_current_history"] for c in report["matching_source_commits"]
        )
        assert report["relationship_status"] == rp.RELATIONSHIP_VERIFIED
    else:
        assert report["relationship_status"] != rp.RELATIONSHIP_VERIFIED
        assert report["overall"] != "PASS"


def test_deployed_runtime_not_traceable_to_commit_in_this_repo() -> None:
    report = rp.build_report()
    declared = report["declared_source"]["sha256"]
    canonical = report["canonical_source"]["head_sha256"]
    assert declared
    assert canonical
    assert declared.lower() != canonical.lower()
    assert report["canonical_source"]["matches_declared_hash"] is False
    assert report["matching_source_commits"] == []
    assert report["relationship_status"] == rp.RELATIONSHIP_UNVERIFIED


def test_candidate_source_commits_are_hashed() -> None:
    report = rp.build_report()
    candidates = report["candidate_source_commits"]
    assert candidates
    for candidate in candidates:
        assert candidate["commit"]
        assert candidate["source_sha256"]
        assert isinstance(candidate["source_bytes"], int)
        assert isinstance(candidate["source_lines"], int)
        assert isinstance(candidate["on_current_history"], bool)


def test_recent_undeployed_source_commits_identified() -> None:
    report = rp.build_report()
    shorts = {entry["short"] for entry in report["undeployed_source_commits"]}
    # Commits after the recovered production baseline that changed the worker
    # source must be reported as unproven, not silently treated as live.
    assert "9d60c7bfedca" in shorts
    assert "0c3ac20392bf" in shorts
    assert "592e7c29af4a" in shorts
    for entry in report["undeployed_source_commits"]:
        assert entry["on_current_history"] is True
        assert "not deployment evidence" in entry["reason"]


def test_workflow_repair_commit_and_successors_are_unproven() -> None:
    report = rp.build_report()
    tracked = {entry["commit"]: entry for entry in report["tracked_execution_commits"]}
    repair = tracked[rp.REPAIR_COMMIT]
    assert repair["touches_workflow"] is True
    assert ".github/workflows/agent-dispatch.yml" in repair["paths"]
    assert repair["proven_deployed"] is False
    # The execution/status/provenance successors must all be unproven too.
    for commit in rp.SUBSEQUENT_COMMITS:
        assert tracked[commit]["proven_deployed"] is False
    # Worker-source successors are also present in the undeployed source list.
    undeployed = {
        entry["commit"] for entry in report["undeployed_source_commits"]
    }
    assert "0c3ac20392bf86bfecb68cbaadd77a7a2a398665" in undeployed
    assert "592e7c29af4a5e72e3ec12bb458538629011896b" in undeployed


def test_execution_relevant_undeployed_commits_include_repair_and_worker_changes() -> None:
    report = rp.build_report()
    entries = report["execution_relevant_undeployed_commits"]
    by_commit = {entry["commit"]: entry for entry in entries}
    assert rp.REPAIR_COMMIT in by_commit
    assert by_commit[rp.REPAIR_COMMIT]["touches_workflow"] is True
    assert by_commit[rp.REPAIR_COMMIT]["proven_deployed"] is False
    worker_changers = [
        entry for entry in entries if entry["touches_worker_source"]
    ]
    assert worker_changers
    assert all(entry["proven_deployed"] is False for entry in entries)
    assert all(entry["is_tracked_task_commit"] for entry in entries if entry["commit"] in rp.TRACKED_EXECUTION_COMMITS)


def test_no_production_mutation() -> None:
    report = rp.build_report()
    assert report["production_mutated"] is False
    assert report["read_only"] is True
    assert report["live_endpoint_checked"] is False
    check = next(c for c in report["checks"] if c["check"] == "no production mutation")
    assert check["status"] == "PASS"


def test_audit_does_not_mutate_repository() -> None:
    before_status = rp._git("status", "--porcelain")
    before_source = rp._sha256_file(rp.REPO_ROOT / rp.CANONICAL_SOURCE)
    before_baseline = rp._sha256_file(rp.REPO_ROOT / rp.BASELINE_PATH)
    report = rp.build_report()
    after_status = rp._git("status", "--porcelain")
    after_source = rp._sha256_file(rp.REPO_ROOT / rp.CANONICAL_SOURCE)
    after_baseline = rp._sha256_file(rp.REPO_ROOT / rp.BASELINE_PATH)
    assert before_status == after_status
    assert before_source == after_source
    assert before_baseline == after_baseline
    assert report["production_mutated"] is False


def test_no_fabricated_pass() -> None:
    report = rp.build_report()
    if report["relationship_status"] != rp.RELATIONSHIP_VERIFIED:
        assert report["overall"] != "PASS"
    if report["overall"] == "PASS":
        assert report["relationship_status"] == rp.RELATIONSHIP_VERIFIED
        assert all(c["status"] == "PASS" for c in report["checks"])


def test_markdown_tokens() -> None:
    report = rp.build_report()
    markdown = report["markdown"]
    assert markdown.startswith(f"# {rp.REPORT_NAME}")
    assert f"- task_id: {rp.TASK_ID}" in markdown
    assert f"RELATIONSHIP_STATUS={report['relationship_status']}" in markdown
    assert "PRODUCTION_MUTATED=False" in markdown
    assert f"OVERALL={report['overall']}" in markdown


def test_committed_json_artifact_is_consistent() -> None:
    json_path = rp.REPO_ROOT / rp.JSON_ARTIFACT
    assert json_path.is_file(), f"missing committed artifact {rp.JSON_ARTIFACT}"
    committed = json.loads(json_path.read_text(encoding="utf-8"))
    fresh = rp.build_report()

    # The markdown must be exactly reproducible from the committed JSON.
    assert committed["markdown"] == rp.render_markdown(committed)

    # generated_at and the rendered markdown embed the generation timestamp;
    # the markdown is checked for self-consistency via render_markdown above.
    volatile = {"generated_at", "markdown"}
    for key in rp.REPORT_FIELDS:
        if key in volatile:
            continue
        if key == "canonical_source":
            committed_canonical = dict(committed[key])
            fresh_canonical = dict(fresh[key])
            # HEAD moves when this report is committed; the source blob does not.
            committed_canonical.pop("head_commit", None)
            fresh_canonical.pop("head_commit", None)
            assert committed_canonical == fresh_canonical
            continue
        assert committed[key] == fresh[key], f"stale artifact field: {key}"


def test_committed_markdown_artifact_present() -> None:
    md_path = rp.REPO_ROOT / rp.MARKDOWN_ARTIFACT
    assert md_path.is_file(), f"missing committed artifact {rp.MARKDOWN_ARTIFACT}"
    markdown = md_path.read_text(encoding="utf-8")
    json_path = rp.REPO_ROOT / rp.JSON_ARTIFACT
    committed = json.loads(json_path.read_text(encoding="utf-8"))
    assert markdown == committed["markdown"] + "\n"


def test_execution_paths_are_read_only_audited() -> None:
    # The audit must never claim to mutate workflows or production assets.
    report = rp.build_report()
    assert report["production_mutated"] is False
    assert report["live_endpoint_checked"] is False
    assert report["repository_presence_is_not_deployment_evidence"] is True
