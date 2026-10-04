"""REALITY_FIRST_CANONICAL_PROMOTION_PREFLIGHT_V0.1 regression tests.

These tests pin the read-only preflight that runs immediately before HG-3 (the
first REALITY Canonical promotion):

* the preflight reads a Candidate Artifact / Review Input / caller store and
  emits exactly PASS / PARTIAL / BLOCKED;
* a complete, VERIFIED, promotion_eligible candidate with a unique canonical
  target is PASS and reports the HG-3 write preconditions satisfied;
* a non-VERIFIED / hash-mismatch / unreadable artifact is BLOCKED; insufficient
  evidence or an unresolved target is PARTIAL and is never guessed;
* every conclusion is OBSERVED / STATED / INFERRED / UNKNOWN tagged and missing
  values stay UNKNOWN;
* no Reality / Canonical / Knowledge / Skill / Decision write, no deploy and no
  secret / permission / binding / schema change occurs, and no second state
  store is created.
"""

from __future__ import annotations

import copy
import json

from personal_ai_execution.reality_candidate_handoff import (
    HANDOFF_CONTRACT,
    build_candidate_artifact,
    candidate_artifact_to_review_input,
    stage_candidate_artifact,
)
from personal_ai_execution.reality_candidate_review import (
    NEEDS_MORE_EVIDENCE,
    PARTIAL,
    PROMOTION_BLOCKED,
    PROMOTION_ELIGIBLE,
    PROMOTION_STATUSES,
)
from personal_ai_execution.reality_canonical_promotion_preflight import (
    CANONICAL_STORE,
    CANONICAL_TARGETS,
    EVIDENCE_TIERS,
    HG3_GATE,
    HG3_PRECONDITIONS,
    PREFLIGHT_CONTRACT,
    PREFLIGHT_GOAL,
    PREFLIGHT_REPORT,
    PREFLIGHT_STATUSES,
    canonical_promotion_preflight,
    promotion_preflight_matrix,
)
from personal_ai_execution.reality_canonical_writer import (
    HUMAN_GATE,
    TARGET_ASSET_TYPES,
)
from personal_ai_execution.reality_capture import (
    EPISTEMIC_INFERRED,
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_UNKNOWN,
    REQUIRED_CAPTURE_FIELDS,
    STATUS_HASH_MISMATCH,
    STATUS_INCOMPLETE,
    STATUS_VERIFIED,
    build_capture_envelope,
    hash_content,
)
from personal_ai_execution.result_normalization import BLOCKED, PASS

CAPTURED_AT = "2026-10-01T00:00:00+00:00"
CONTENT = "hello reality"
SOURCE_IDENTITY = "wechat:conversation:conv-42"


def all_observed() -> dict[str, str]:
    return {field: EPISTEMIC_OBSERVED for field in REQUIRED_CAPTURE_FIELDS}


def capture_envelope(**overrides):
    envelope = build_capture_envelope(
        source_identity=SOURCE_IDENTITY,
        source_location="wechat://local-snapshot/MSG.db/conv-42",
        source_version="rev-3",
        content_version="content-7",
        captured_at=CAPTURED_AT,
        content=CONTENT,
        verification_evidence={"capability": "wechat-reader-v1"},
        capture_id="cap-1",
        message_id="msg-42",
        epistemic=overrides.pop("epistemic", all_observed()),
    )
    envelope.update(overrides)
    return envelope


def verified_artifact(**overrides):
    return build_candidate_artifact(
        capture_envelope(**overrides), snapshot_id="snap-42"
    )


def reader_artifact():
    from personal_ai_execution.reality_daily_snapshot import reader_item_to_envelope

    envelope = reader_item_to_envelope(
        {
            "chat_id": "conv-42",
            "message_id": "msg-42",
            "create_time_iso": CAPTURED_AT,
            "content_available": True,
            "source_db": "MSG.db",
            "source_version": "rev-3",
            "content": CONTENT,
        }
    )
    return build_candidate_artifact(envelope)


# -- PASS ----------------------------------------------------------------------


def test_verified_eligible_candidate_with_target_is_pass():
    report = canonical_promotion_preflight(verified_artifact(), target_asset_type="KNOWLEDGE")

    assert report["report"] == PREFLIGHT_REPORT
    assert report["goal"] == PREFLIGHT_GOAL
    assert report["contract"] == PREFLIGHT_CONTRACT
    assert report["handoff_contract"] == HANDOFF_CONTRACT
    assert report["verdict"] == PASS
    assert report["preflight_status"] == PASS
    assert report["review_status"] == PASS
    assert report["promotion_status"] == PROMOTION_ELIGIBLE
    assert report["target_asset_type"] == "KNOWLEDGE"
    assert report["target_unique"] is True
    assert report["first_promotion"] is True
    assert report["promoted_provenance_status"] == "VERIFIED"
    assert report["canonical_store"] == CANONICAL_STORE
    assert report["hg3_write_preconditions_satisfied"] is True
    assert report["workflow_status"] == PASS
    assert all(check["status"] == PASS for check in report["checks"])


def test_pass_reports_hg3_gate_and_preconditions():
    report = canonical_promotion_preflight(verified_artifact(), target_asset_type="SKILL")

    assert report["hg3_gate"] == HG3_GATE
    assert report["hg3_gate"] == HUMAN_GATE
    assert report["hg3_required"] is True
    assert report["human_gate_required"] is True
    assert report["hg3_authorized"] is False
    names = {item["name"] for item in report["preconditions"]}
    assert names == set(HG3_PRECONDITIONS)
    assert all(item["satisfied"] for item in report["preconditions"])


def test_preflight_accepts_review_input_but_stays_partial_without_candidate():
    artifact = verified_artifact()
    review_input = candidate_artifact_to_review_input(artifact)
    report = canonical_promotion_preflight(review_input=review_input, target_asset_type="DECISION")

    # The Review Input carries candidate identity/provenance but not the raw
    # candidate content, so the promoted provenance cannot be re-verified here:
    # the preflight stays PARTIAL and keeps the missing evaluation UNKNOWN.
    assert report["candidate_id"] == "cap-1"
    assert report["verdict"] == PARTIAL
    assert report["promotion_status"] == PROMOTION_ELIGIBLE
    assert report["promoted_provenance_status"] is None
    assert report["hg3_write_preconditions_satisfied"] is False
    assert any("provenance" in unknown for unknown in report["unknowns"])


def test_preflight_reads_artifact_from_store():
    artifact = verified_artifact()
    store: dict = {}
    stage_candidate_artifact(artifact, store)

    report = canonical_promotion_preflight(
        store=store, location=artifact["artifact_location"], target_asset_type="KNOWLEDGE"
    )
    assert report["candidate_id"] == "cap-1"
    assert report["artifact_id"] == artifact["artifact_id"]
    assert report["verdict"] == PASS


# -- PARTIAL ------------------------------------------------------------------


def test_eligible_candidate_without_target_is_partial_and_unknown():
    report = canonical_promotion_preflight(verified_artifact())

    assert report["verdict"] == PARTIAL
    assert report["promotion_status"] == PROMOTION_ELIGIBLE
    assert report["target_asset_type"] is None
    assert report["target_unique"] is False
    assert report["hg3_write_preconditions_satisfied"] is False
    assert any("target" in unknown for unknown in report["unknowns"])
    assert report["promotion_status"] in PROMOTION_STATUSES


def test_promotion_ineligible_candidate_is_partial():
    report = canonical_promotion_preflight(reader_artifact(), target_asset_type="KNOWLEDGE")

    assert report["capture_status"] == STATUS_VERIFIED
    assert report["promotion_eligible"] is False
    assert report["verdict"] == PARTIAL
    assert report["promotion_status"] == NEEDS_MORE_EVIDENCE
    assert report["hg3_write_preconditions_satisfied"] is False


def test_stated_required_field_is_partial():
    epistemic = all_observed()
    epistemic["source_version"] = EPISTEMIC_STATED
    artifact = build_candidate_artifact(capture_envelope(epistemic=epistemic))
    report = canonical_promotion_preflight(artifact, target_asset_type="KNOWLEDGE")

    assert report["verdict"] == PARTIAL
    assert report["promotion_status"] == NEEDS_MORE_EVIDENCE
    assert "source_version" in report["epistemic_summary"]["stated"]


def test_invalid_target_is_partial_and_never_a_target():
    report = canonical_promotion_preflight(
        verified_artifact(), target_asset_type="REALITY"
    )

    assert "REALITY" not in CANONICAL_TARGETS
    assert report["verdict"] == PARTIAL
    assert report["target_unique"] is False
    assert report["promoted_provenance_status"] is None


def test_already_promoted_candidate_is_partial_not_pass():
    artifact = verified_artifact()
    existing = {"current_version": 1, "content_hash": artifact["content_hash"]}
    report = canonical_promotion_preflight(
        artifact, target_asset_type="KNOWLEDGE", existing_asset=existing
    )

    assert report["first_promotion"] is False
    assert report["verdict"] == PARTIAL
    assert report["promotion_status"] == PROMOTION_ELIGIBLE


# -- BLOCKED ------------------------------------------------------------------


def test_no_input_is_blocked():
    report = canonical_promotion_preflight()

    assert report["verdict"] == BLOCKED
    assert report["verdict"] in PREFLIGHT_STATUSES
    assert report["review_status"] == BLOCKED
    assert report["promotion_status"] == PROMOTION_BLOCKED
    assert report["readable"] is False
    assert report["hg3_write_preconditions_satisfied"] is False
    assert report["evidence_gaps"]
    assert report["unknowns"]
    # The workflow itself still completed its read-only checks successfully.
    assert report["workflow_status"] == PASS


def test_incomplete_candidate_is_blocked():
    envelope = capture_envelope()
    envelope.pop("source_version")
    report = canonical_promotion_preflight(
        build_candidate_artifact(envelope), target_asset_type="KNOWLEDGE"
    )

    assert report["capture_status"] == STATUS_INCOMPLETE
    assert report["verdict"] == BLOCKED
    assert report["promotion_status"] == PROMOTION_BLOCKED
    assert any("source_version" in gap for gap in report["evidence_gaps"])


def test_unknown_required_field_is_blocked_and_never_guessed():
    epistemic = all_observed()
    epistemic["source_version"] = EPISTEMIC_UNKNOWN
    artifact = build_candidate_artifact(capture_envelope(epistemic=epistemic))
    report = canonical_promotion_preflight(artifact, target_asset_type="KNOWLEDGE")

    assert report["capture_status"] == STATUS_INCOMPLETE
    assert report["verdict"] == BLOCKED
    assert "source_version" in report["epistemic_summary"]["unknown"]


def test_hash_mismatch_is_blocked():
    artifact = build_candidate_artifact(
        capture_envelope(content_hash="sha256:" + "0" * 64)
    )
    report = canonical_promotion_preflight(artifact, target_asset_type="KNOWLEDGE")

    assert artifact["status"] == STATUS_HASH_MISMATCH
    assert report["verdict"] == BLOCKED
    assert report["promotion_status"] == PROMOTION_BLOCKED
    assert any("content_hash" in gap for gap in report["evidence_gaps"])


def test_malformed_artifact_is_blocked():
    report = canonical_promotion_preflight("not-an-artifact", target_asset_type="KNOWLEDGE")  # type: ignore[arg-type]

    assert report["verdict"] == BLOCKED
    assert report["promotion_status"] == PROMOTION_BLOCKED
    assert report["evidence_gaps"]


def test_matching_declared_hash_stays_verified_and_pass():
    artifact = build_candidate_artifact(
        capture_envelope(content_hash=hash_content(CONTENT))
    )
    report = canonical_promotion_preflight(artifact, target_asset_type="KNOWLEDGE")
    assert artifact["status"] == STATUS_VERIFIED
    assert report["verdict"] == PASS


# -- evidence tagging ----------------------------------------------------------


def test_evidence_items_are_source_tagged():
    report = canonical_promotion_preflight(verified_artifact(), target_asset_type="KNOWLEDGE")

    assert report["evidence"]
    for item in report["evidence"]:
        assert set(item) == {"source", "detail"}
        assert item["source"] in EVIDENCE_TIERS
        assert item["detail"]
    assert set(report["evidence_tiers_present"]) <= set(EVIDENCE_TIERS)
    assert "OBSERVED" in report["evidence_tiers_present"]
    assert set(EVIDENCE_TIERS) == {
        EPISTEMIC_OBSERVED,
        EPISTEMIC_STATED,
        EPISTEMIC_INFERRED,
        EPISTEMIC_UNKNOWN,
    }


def test_blocked_preflight_lists_unknown_evidence():
    report = canonical_promotion_preflight()
    sources = {item["source"] for item in report["evidence"]}
    assert EPISTEMIC_UNKNOWN in sources


def test_epistemic_summary_lists_four_tiers():
    report = canonical_promotion_preflight(verified_artifact(), target_asset_type="KNOWLEDGE")
    summary = report["epistemic_summary"]
    assert set(summary) == {"observed", "stated", "inferred", "unknown"}


# -- no mutation / no leak -----------------------------------------------------


def test_preflight_is_read_only_and_never_writes():
    report = canonical_promotion_preflight(verified_artifact(), target_asset_type="KNOWLEDGE")

    for key in (
        "read_only",
        "content_exposed",
        "message_content_exposed",
        "write_performed",
        "production_write_performed",
        "canonical_write_performed",
        "reality_written",
        "reality_canonical_written",
        "canonical_written",
        "knowledge_written",
        "skill_written",
        "decision_written",
        "deployment_performed",
        "credentials_accessed",
        "secret_accessed",
        "permissions_changed",
        "binding_changed",
        "schema_changed",
        "mark_reviewed_called",
        "second_state_store_created",
    ):
        expected = key == "read_only"
        assert report[key] is expected, key


def test_message_content_is_not_exposed():
    sentinel = "PREFLIGHT_CONTENT_SENTINEL_7a1_DO_NOT_EXPOSE"
    artifact = verified_artifact(content={"text": sentinel})
    report = canonical_promotion_preflight(artifact, target_asset_type="KNOWLEDGE")

    assert report["content_exposed"] is False
    assert report["message_content_exposed"] is False
    assert sentinel not in json.dumps(report)
    assert sentinel not in report["markdown"]


def test_preflight_does_not_mutate_inputs():
    artifact = verified_artifact()
    before = copy.deepcopy(artifact)
    review_input = candidate_artifact_to_review_input(artifact)
    review_input_before = copy.deepcopy(review_input)

    canonical_promotion_preflight(artifact, target_asset_type="KNOWLEDGE")
    canonical_promotion_preflight(review_input=review_input, target_asset_type="KNOWLEDGE")

    assert artifact == before
    assert review_input == review_input_before


def test_hg3_authorized_is_recorded_but_no_write_occurs():
    report = canonical_promotion_preflight(
        verified_artifact(), target_asset_type="KNOWLEDGE", human_gate_authorized=True
    )

    assert report["hg3_authorized"] is True
    assert report["canonical_write_performed"] is False
    assert report["second_state_store_created"] is False


# -- canonical store / target uniqueness --------------------------------------


def test_canonical_targets_match_writer_targets():
    assert tuple(CANONICAL_TARGETS) == tuple(TARGET_ASSET_TYPES)
    assert "REALITY" not in CANONICAL_TARGETS


def test_canonical_store_is_the_existing_single_store():
    report = canonical_promotion_preflight(verified_artifact(), target_asset_type="KNOWLEDGE")
    assert report["canonical_store"] == "ASSET_DB:assets/asset_versions"
    assert CANONICAL_STORE == "ASSET_DB:assets/asset_versions"


def test_markdown_reports_final_status_and_preconditions():
    report = canonical_promotion_preflight(verified_artifact(), target_asset_type="KNOWLEDGE")
    assert report["markdown"].startswith(f"# {PREFLIGHT_GOAL}")
    assert f"FINAL_STATUS={report['final_status']}" in report["markdown"]
    assert report["final_status"] == (
        "PREFLIGHT_VERDICT=PASS;PROMOTION_STATUS=" + PROMOTION_ELIGIBLE
    )
    for name in HG3_PRECONDITIONS:
        assert name in report["markdown"]


def test_preflight_matrix_is_consistent():
    matrix = promotion_preflight_matrix()
    assert matrix
    assert {row["verdict"] for row in matrix} <= set(PREFLIGHT_STATUSES)
    assert any(row["verdict"] == PASS for row in matrix)
    assert any(row["verdict"] == PARTIAL for row in matrix)
    assert any(row["verdict"] == BLOCKED for row in matrix)
