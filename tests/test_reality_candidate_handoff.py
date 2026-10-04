"""REALITY_CANDIDATE_HANDOFF_V0.1 regression tests.

These tests pin the read-only handoff contract:

* a Reality Snapshot normalizes into a deterministic Candidate artifact;
* the artifact schema and its explicit provenance fields are stable;
* Review can read the artifact and receives a fail-closed, advisory verdict;
* missing fields / UNKNOWN epistemic values are never upgraded to VERIFIED;
* nothing performs a production/Canonical write or creates a second store.
"""

from __future__ import annotations

import copy

from personal_ai_execution.provenance_contract import PROVENANCE_CONTRACT_VERSION
from personal_ai_execution.reality_capture import (
    EPISTEMIC_INFERRED,
    EPISTEMIC_OBSERVED,
    EPISTEMIC_UNKNOWN,
    REALITY_CONTRACT_VERSION,
    REQUIRED_CAPTURE_FIELDS,
    STATUS_HASH_MISMATCH,
    STATUS_INCOMPLETE,
    STATUS_VERIFIED,
    hash_content,
    normalize_reality_capture,
)
from personal_ai_execution.reality_daily_snapshot import reader_item_to_envelope
from personal_ai_execution.reality_candidate_handoff import (
    ARTIFACT_PROVENANCE_FIELDS,
    ARTIFACT_SCHEMA,
    ARTIFACT_TYPE,
    CANDIDATE_ARTIFACT_FIELDS,
    HANDOFF_CONTRACT,
    REVIEW_INPUT_CONTRACT,
    build_candidate_artifact,
    candidate_artifact_id,
    candidate_artifact_location,
    candidate_artifact_to_review_input,
    handoff_matrix,
    read_candidate_artifact,
    run_candidate_handoff,
    stage_candidate_artifact,
    validate_candidate_artifact,
    validate_review_input,
)
from personal_ai_execution.result_normalization import BLOCKED, FAIL, PASS

CAPTURED_AT = "2026-10-01T00:00:00+00:00"
CONTENT = "hello reality"
SOURCE_IDENTITY = "wechat:conversation:conv-42"


def capture_envelope(**overrides):
    envelope = {
        "capture_id": "cap-1",
        "message_id": "msg-42",
        "source_identity": SOURCE_IDENTITY,
        "source_location": "wechat://local-snapshot/MSG.db/conv-42",
        "source_version": "rev-3",
        "content_version": "content-7",
        "captured_at": CAPTURED_AT,
        "content": CONTENT,
        "content_hash": None,
        "verification_evidence": {"capability": "wechat-reader-v1"},
        "epistemic": {},
        "provenance": None,
    }
    envelope.update(overrides)
    return envelope


def observed_epistemic():
    return {field: EPISTEMIC_OBSERVED for field in REQUIRED_CAPTURE_FIELDS}


def verified_artifact(**overrides):
    return build_candidate_artifact(
        capture_envelope(epistemic=observed_epistemic(), **overrides),
        snapshot_id="snap-42",
    )


# -- candidate artifact lifecycle -------------------------------------------


def test_artifact_location_is_deterministic():
    assert candidate_artifact_location("msg-42") == (
        "reality-candidates/msg-42.candidate.json"
    )
    assert candidate_artifact_location("msg-42") == candidate_artifact_location("msg-42")


def test_artifact_location_is_sanitized_and_unknown_safe():
    location = candidate_artifact_location("a/b c")
    leaf = location[len("reality-candidates/") :]
    assert "/" not in leaf
    assert candidate_artifact_location(None).endswith(".candidate.json")
    assert candidate_artifact_location(None).startswith("reality-candidates/")


def test_artifact_id_is_deterministic_and_content_sensitive():
    first = candidate_artifact_id("msg-42", "sha256:abc", SOURCE_IDENTITY)
    same = candidate_artifact_id("msg-42", "sha256:abc", SOURCE_IDENTITY)
    changed = candidate_artifact_id("msg-42", "sha256:def", SOURCE_IDENTITY)
    assert first == same
    assert first != changed
    assert first.startswith("reality-candidate:")


def test_build_artifact_from_verified_snapshot():
    artifact = verified_artifact()
    assert artifact["artifact_contract"] == HANDOFF_CONTRACT
    assert artifact["artifact_schema"] == ARTIFACT_SCHEMA
    assert artifact["artifact_type"] == ARTIFACT_TYPE
    assert artifact["asset_type"] == "REALITY"
    assert artifact["status"] == STATUS_VERIFIED
    assert artifact["verified"] is True
    assert artifact["candidate_id"] == "cap-1"
    assert artifact["artifact_location"] == (
        "reality-candidates/cap-1.candidate.json"
    )
    assert artifact["handoff"]["snapshot_id"] == "snap-42"


def test_artifact_carries_every_declared_schema_field():
    artifact = verified_artifact()
    for field in CANDIDATE_ARTIFACT_FIELDS:
        assert field in artifact, field


def test_artifact_provenance_fields_are_explicit():
    artifact = verified_artifact()
    provenance = artifact["artifact_provenance"]
    for field in ARTIFACT_PROVENANCE_FIELDS:
        assert field in provenance, field
    assert provenance["handoff_contract"] == HANDOFF_CONTRACT
    assert provenance["capture_contract"] == REALITY_CONTRACT_VERSION
    assert provenance["provenance_contract"] == PROVENANCE_CONTRACT_VERSION
    assert provenance["source_identity"] == SOURCE_IDENTITY
    assert provenance["content_hash"] == artifact["content_hash"]


# -- review input -----------------------------------------------------------


def test_verified_artifact_review_input_is_readable_and_pass():
    review_input = candidate_artifact_to_review_input(verified_artifact())
    assert review_input["review_contract"] == REVIEW_INPUT_CONTRACT
    assert review_input["readable"] is True
    assert review_input["review"]["verdict"] == PASS
    assert review_input["candidate_id"] == "cap-1"
    assert review_input["review"]["reasons"]
    assert validate_review_input(review_input)["ok"] is True


def test_review_input_is_advisory_and_never_auto_approved():
    review_input = candidate_artifact_to_review_input(verified_artifact())
    review = review_input["review"]
    assert review["advisory"] is True
    assert review["requires_human_review"] is True
    assert review["auto_reviewed"] is False
    assert review["auto_mark_reviewed_called"] is False
    assert review["evidence_refs"]


def test_review_input_links_back_to_the_artifact():
    artifact = verified_artifact()
    review_input = candidate_artifact_to_review_input(artifact)
    assert review_input["artifact_id"] == artifact["artifact_id"]
    assert review_input["artifact_location"] == artifact["artifact_location"]


def test_review_input_missing_expected_files_is_not_fabricated():
    review_input = candidate_artifact_to_review_input(verified_artifact())
    assert review_input["missing"] == []


# -- fail-closed: UNKNOWN / missing fields ----------------------------------


def test_missing_source_version_never_becomes_verified():
    envelope = capture_envelope(epistemic=observed_epistemic())
    envelope.pop("source_version")
    artifact = build_candidate_artifact(envelope)
    assert artifact["status"] == STATUS_INCOMPLETE
    assert artifact["verified"] is False
    assert "source_version" in artifact["missing"]
    review_input = candidate_artifact_to_review_input(artifact)
    assert review_input["review"]["verdict"] == BLOCKED


def test_unknown_epistemic_value_keeps_unknown_and_blocks_review():
    envelope = capture_envelope(
        epistemic={**observed_epistemic(), "source_version": EPISTEMIC_UNKNOWN}
    )
    artifact = build_candidate_artifact(envelope)
    assert artifact["status"] == STATUS_INCOMPLETE
    assert artifact["verified"] is False
    assert artifact["epistemic"]["source_version"] == EPISTEMIC_UNKNOWN
    assert candidate_artifact_to_review_input(artifact)["review"]["verdict"] == BLOCKED


def test_content_unavailable_is_incomplete_and_never_verified():
    artifact = build_candidate_artifact(
        capture_envelope(content=None, content_available=False)
    )
    assert artifact["status"] == STATUS_INCOMPLETE
    assert artifact["verified"] is False
    assert "content" in artifact["missing"]
    assert candidate_artifact_to_review_input(artifact)["review"]["verdict"] == BLOCKED


def test_declared_hash_mismatch_is_fail():
    artifact = build_candidate_artifact(
        capture_envelope(content_hash="sha256:" + "0" * 64)
    )
    assert artifact["status"] == STATUS_HASH_MISMATCH
    assert artifact["verified"] is False
    review_input = candidate_artifact_to_review_input(artifact)
    assert review_input["review"]["verdict"] == FAIL


def test_matching_declared_hash_stays_verified():
    artifact = build_candidate_artifact(
        capture_envelope(content_hash=hash_content(CONTENT))
    )
    assert artifact["status"] == STATUS_VERIFIED


def test_inferred_epistemic_tag_is_preserved():
    envelope = reader_item_to_envelope(
        {
            "chat_id": "conv-42",
            "message_id": "msg-42",
            "create_time_iso": CAPTURED_AT,
            "content_available": True,
            "source_db": "MSG.db",
            "content": CONTENT,
        }
    )
    artifact = build_candidate_artifact(envelope)
    assert artifact["epistemic"]["source_identity"] == EPISTEMIC_INFERRED
    assert artifact["promotion_eligible"] is False


def test_verified_but_promotion_ineligible_notes_human_confirmation():
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
    artifact = build_candidate_artifact(envelope)
    assert artifact["status"] == STATUS_VERIFIED
    assert artifact["verified"] is True
    assert artifact["promotion_eligible"] is False
    review_input = candidate_artifact_to_review_input(artifact)
    assert review_input["review"]["verdict"] == PASS
    codes = {reason["code"] for reason in review_input["review"]["reasons"]}
    assert "NOT_PROMOTION_ELIGIBLE" in codes


# -- artifact validation ----------------------------------------------------


def test_validate_accepts_a_well_formed_artifact():
    validation = validate_candidate_artifact(verified_artifact())
    assert validation["ok"] is True
    assert validation["readable"] is True
    assert validation["reasons"] == []


def test_validate_rejects_non_mapping():
    validation = validate_candidate_artifact(None)
    assert validation["ok"] is False
    assert validation["readable"] is False


def test_validate_rejects_forged_verified_flag():
    artifact = verified_artifact()
    artifact["status"] = STATUS_INCOMPLETE
    artifact["verified"] = True
    artifact["artifact_provenance"]["status"] = STATUS_INCOMPLETE
    artifact["artifact_provenance"]["verified"] = True
    validation = validate_candidate_artifact(artifact)
    assert validation["ok"] is False
    assert any("fail-closed" in reason for reason in validation["reasons"])


def test_validate_rejects_wrong_contract():
    artifact = verified_artifact()
    artifact["artifact_contract"] = "WRONG"
    validation = validate_candidate_artifact(artifact)
    assert validation["ok"] is False
    assert any("artifact_contract" in reason for reason in validation["reasons"])


def test_validate_rejects_non_deterministic_location():
    artifact = verified_artifact()
    artifact["artifact_location"] = "somewhere/else.json"
    validation = validate_candidate_artifact(artifact)
    assert validation["ok"] is False
    assert any("artifact_location" in reason for reason in validation["reasons"])


def test_validate_rejects_missing_provenance_field():
    artifact = verified_artifact()
    artifact["artifact_provenance"].pop("source_identity")
    validation = validate_candidate_artifact(artifact)
    assert validation["ok"] is False
    assert any("source_identity" in reason for reason in validation["reasons"])


# -- staging and read-back --------------------------------------------------


def test_stage_and_read_roundtrip():
    artifact = verified_artifact()
    store = {}
    staged = stage_candidate_artifact(artifact, store)
    assert staged["stored"] is True
    assert store[artifact["artifact_location"]]["artifact_id"] == artifact["artifact_id"]

    retrieved, errors = read_candidate_artifact(store, artifact["artifact_location"])
    assert errors == []
    assert retrieved["artifact_id"] == artifact["artifact_id"]


def test_stage_invalid_artifact_is_not_stored():
    store = {}
    staged = stage_candidate_artifact(None, store)
    assert staged["stored"] is False
    assert store == {}
    assert staged["production_write_performed"] is False


def test_stage_without_store_is_fail_closed():
    staged = stage_candidate_artifact(verified_artifact(), None)
    assert staged["stored"] is False
    assert staged["reasons"]


def test_read_missing_location_is_fail_closed():
    retrieved, errors = read_candidate_artifact({}, "reality-candidates/nope.json")
    assert retrieved is None
    assert errors


def test_read_empty_location_is_fail_closed():
    retrieved, errors = read_candidate_artifact({}, "")
    assert retrieved is None
    assert errors


def test_read_invalid_artifact_is_fail_closed():
    artifact = verified_artifact()
    artifact["artifact_contract"] = "WRONG"
    store = {artifact["artifact_location"]: artifact}
    retrieved, errors = read_candidate_artifact(store, artifact["artifact_location"])
    assert retrieved is None
    assert errors


# -- end-to-end handoff -----------------------------------------------------


def test_run_candidate_handoff_verified_is_pass():
    report = run_candidate_handoff(
        capture_envelope(epistemic=observed_epistemic()), snapshot_id="snap-42"
    )
    assert report["status"] == PASS
    assert report["review_verdict"] == PASS
    assert report["capture_status"] == STATUS_VERIFIED
    assert all(check["passed"] for check in report["checks"])


def test_run_candidate_handoff_incomplete_is_fail_closed():
    envelope = capture_envelope(epistemic=observed_epistemic())
    envelope.pop("source_version")
    report = run_candidate_handoff(envelope)
    assert report["status"] == PASS
    assert report["capture_status"] == STATUS_INCOMPLETE
    assert report["verified"] is False
    assert report["review_verdict"] == BLOCKED
    assert report["review_input"]["verified"] is False


def test_run_candidate_handoff_never_writes():
    report = run_candidate_handoff(capture_envelope())
    assert report["read_only"] is True
    assert report["write_performed"] is False
    assert report["production_write_performed"] is False
    assert report["canonical_write_performed"] is False
    assert report["second_state_store_created"] is False
    assert report["requires_human_gate"] is True


def test_run_candidate_handoff_uses_caller_store():
    store = {}
    report = run_candidate_handoff(capture_envelope(), store=store)
    assert report["artifact_location"] in store
    assert report["staged"]["stored"] is True


def test_run_candidate_handoff_reports_every_check():
    report = run_candidate_handoff(capture_envelope())
    names = {check["name"] for check in report["checks"]}
    assert "snapshot_normalized_to_candidate" in names
    assert "candidate_artifact_staged_and_readable" in names
    assert "review_input_readable_and_linked" in names
    assert "artifact_provenance_fields_explicit" in names
    assert "unknown_never_upgraded_to_verified" in names
    assert "no_production_or_canonical_write" in names


def test_run_candidate_handoff_contract_labels():
    report = run_candidate_handoff(capture_envelope())
    assert report["contract"] == HANDOFF_CONTRACT
    assert report["capture_contract"] == REALITY_CONTRACT_VERSION
    assert report["provenance_contract"] == PROVENANCE_CONTRACT_VERSION
    assert report["review_contract"] == REVIEW_INPUT_CONTRACT


# -- reuse / purity ---------------------------------------------------------


def test_build_accepts_normalized_capture_result_too():
    envelope = capture_envelope(epistemic=observed_epistemic())
    normalized = normalize_reality_capture(envelope)
    from_envelope = build_candidate_artifact(envelope)
    from_normalized = build_candidate_artifact(normalized)
    for field in (
        "artifact_id",
        "artifact_location",
        "candidate_id",
        "status",
        "verified",
        "content_hash",
    ):
        assert from_envelope[field] == from_normalized[field], field
    assert from_normalized["handoff"]["source_kind"] == "NORMALIZED_CAPTURE"


def test_build_does_not_mutate_snapshot():
    envelope = capture_envelope(epistemic=observed_epistemic())
    before = copy.deepcopy(envelope)
    build_candidate_artifact(envelope)
    assert envelope == before


def test_review_input_does_not_mutate_artifact():
    artifact = verified_artifact()
    before = copy.deepcopy(artifact)
    candidate_artifact_to_review_input(artifact)
    assert artifact == before


def test_validate_review_input_rejects_auto_approved():
    review_input = candidate_artifact_to_review_input(verified_artifact())
    review_input["review"]["auto_reviewed"] = True
    validation = validate_review_input(review_input)
    assert validation["ok"] is False


def test_handoff_matrix_documents_fail_closed_rows():
    matrix = handoff_matrix()
    assert matrix
    statuses = {row["review_verdict"] for row in matrix}
    assert {PASS, FAIL, BLOCKED} <= statuses
