"""REALITY_FIRST_CANDIDATE_REVIEW_V0.2 regression tests.

These tests pin the read-only review contract built on top of
``REALITY_CANDIDATE_HANDOFF_V0.1``:

* Review can read a Candidate Artifact (directly, from a Review Input, or from a
  caller-supplied store) and returns candidate_id / provenance / evidence status;
* the review is advisory and fail-closed: an unreadable artifact, a hash
  mismatch or a non-VERIFIED candidate is BLOCKED; insufficient evidence is
  PARTIAL / NEEDS_MORE_EVIDENCE and is never guessed into eligibility;
* ``promotion_status`` is always consistent with the review verdict;
* no Reality Canonical / Knowledge / Skill / Decision write and no deploy /
  secret / permission / binding / schema change is performed.
"""

from __future__ import annotations

import copy
import json

import pytest

from personal_ai_execution.reality_candidate_handoff import (
    HANDOFF_CONTRACT,
    build_candidate_artifact,
    candidate_artifact_to_review_input,
    stage_candidate_artifact,
)
from personal_ai_execution.reality_candidate_review import (
    EVIDENCE_SOURCES,
    NEEDS_MORE_EVIDENCE,
    PARTIAL,
    PROMOTION_BLOCKED,
    PROMOTION_ELIGIBLE,
    PROMOTION_STATUSES,
    REVIEW_CONTRACT,
    REVIEW_GOAL,
    REVIEW_REPORT,
    REVIEW_STATUSES,
    promotion_status_for_review,
    reality_candidate_review_matrix,
    review_candidate_artifact,
)
from personal_ai_execution.reality_capture import (
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


# -- read the Candidate Artifact --------------------------------------------


def test_review_reads_candidate_artifact_and_returns_identity_provenance_evidence():
    artifact = verified_artifact()
    report = review_candidate_artifact(artifact)

    assert report["report"] == REVIEW_REPORT
    assert report["goal"] == REVIEW_GOAL
    assert report["contract"] == REVIEW_CONTRACT
    assert report["handoff_contract"] == HANDOFF_CONTRACT
    assert report["input"] == "CANDIDATE_ARTIFACT"

    assert report["candidate_id"] == "cap-1"
    assert report["artifact_id"] == artifact["artifact_id"]
    assert report["artifact_location"] == artifact["artifact_location"]
    assert report["provenance"]["source_identity"] == SOURCE_IDENTITY
    assert report["artifact_provenance"]["handoff_contract"] == HANDOFF_CONTRACT
    assert report["provenance_status"] is not None
    assert report["evidence"]
    assert report["evidence_status"] in EVIDENCE_SOURCES


def test_review_accepts_review_input_from_handoff():
    artifact = verified_artifact()
    review_input = candidate_artifact_to_review_input(artifact)
    report = review_candidate_artifact(review_input=review_input)

    assert report["input"] == "CANDIDATE_REVIEW_INPUT"
    assert report["candidate_id"] == "cap-1"
    assert report["review_status"] == PASS
    assert report["promotion_status"] == PROMOTION_ELIGIBLE


def test_review_reads_artifact_from_store():
    artifact = verified_artifact()
    store: dict = {}
    stage_candidate_artifact(artifact, store)

    report = review_candidate_artifact(
        store=store, location=artifact["artifact_location"]
    )
    assert report["input"] == "CANDIDATE_ARTIFACT_FROM_STORE"
    assert report["candidate_id"] == "cap-1"
    assert report["review_status"] == PASS


def test_review_store_missing_location_is_fail_closed():
    report = review_candidate_artifact(store={}, location="reality-candidates/nope.json")
    assert report["review_status"] == BLOCKED
    assert report["promotion_status"] == PROMOTION_BLOCKED
    assert report["read_errors"]
    assert report["evidence_gaps"]


# -- verdicts -----------------------------------------------------------------


def test_verified_candidate_is_promotion_eligible():
    report = review_candidate_artifact(verified_artifact())

    assert report["review_status"] == PASS
    assert report["promotion_status"] == PROMOTION_ELIGIBLE
    assert report["promotion_eligible"] is True
    assert report["capture_status"] == STATUS_VERIFIED
    assert report["verified"] is True
    assert report["evidence_gaps"] == []
    assert report["evidence_status"] == EPISTEMIC_OBSERVED
    assert report["workflow_status"] == PASS
    assert all(check["status"] == PASS for check in report["checks"])


def test_default_no_input_is_blocked_and_read_only():
    report = review_candidate_artifact()

    assert report["input"] == "NO_INPUT"
    assert report["review_status"] == BLOCKED
    assert report["review_status"] in REVIEW_STATUSES
    assert report["promotion_status"] == PROMOTION_BLOCKED
    assert report["promotion_status"] in PROMOTION_STATUSES
    assert report["promotion_eligible"] is False
    assert report["evidence_gaps"]
    assert report["unknowns"]
    assert report["readable"] is False
    assert report["workflow_status"] == PASS
    assert report["final_status"] == (
        "REVIEW_STATUS=BLOCKED;PROMOTION_STATUS=" + PROMOTION_BLOCKED
    )


def test_stated_required_field_is_partial_needs_more_evidence():
    epistemic = all_observed()
    epistemic["source_version"] = EPISTEMIC_STATED
    report = review_candidate_artifact(
        build_candidate_artifact(capture_envelope(epistemic=epistemic))
    )

    assert report["review_status"] == PARTIAL
    assert report["promotion_status"] == NEEDS_MORE_EVIDENCE
    assert report["promotion_eligible"] is False
    assert (
        "required field 'source_version' is STATED, not OBSERVED"
        in report["evidence_gaps"]
    )
    assert "source_version" in report["epistemic_summary"]["stated"]


def test_unknown_required_field_is_blocked_and_never_guessed():
    epistemic = all_observed()
    epistemic["source_version"] = EPISTEMIC_UNKNOWN
    report = review_candidate_artifact(
        build_candidate_artifact(capture_envelope(epistemic=epistemic))
    )

    # An UNKNOWN required field makes the capture INCOMPLETE, so the review is
    # BLOCKED rather than guessed into a promotion-eligible state.
    assert report["capture_status"] == STATUS_INCOMPLETE
    assert report["review_status"] == BLOCKED
    assert report["promotion_status"] == PROMOTION_BLOCKED
    assert report["promotion_eligible"] is False
    assert "source_version" in report["epistemic_summary"]["unknown"]
    assert any("source_version" in gap for gap in report["evidence_gaps"])


def test_hash_mismatch_is_blocked():
    artifact = build_candidate_artifact(
        capture_envelope(content_hash="sha256:" + "0" * 64)
    )
    report = review_candidate_artifact(artifact)

    assert artifact["status"] == STATUS_HASH_MISMATCH
    assert report["review_status"] == BLOCKED
    assert report["promotion_status"] == PROMOTION_BLOCKED
    assert report["verified"] is False
    assert any("content_hash" in gap for gap in report["evidence_gaps"])


def test_incomplete_candidate_is_blocked():
    envelope = capture_envelope()
    envelope.pop("source_version")
    report = review_candidate_artifact(build_candidate_artifact(envelope))

    assert report["capture_status"] == STATUS_INCOMPLETE
    assert report["review_status"] == BLOCKED
    assert report["promotion_status"] == PROMOTION_BLOCKED
    assert any("source_version" in gap for gap in report["evidence_gaps"])


def test_malformed_artifact_is_blocked():
    report = review_candidate_artifact("not-an-artifact")  # type: ignore[arg-type]
    assert report["review_status"] == BLOCKED
    assert report["promotion_status"] == PROMOTION_BLOCKED
    assert report["evidence_gaps"]


def test_verified_but_promotion_ineligible_needs_more_evidence():
    # reader-derived source_identity is INFERRED, so promotion_eligible is False
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
    artifact = build_candidate_artifact(envelope)
    assert artifact["status"] == STATUS_VERIFIED
    assert artifact["promotion_eligible"] is False

    report = review_candidate_artifact(artifact)
    assert report["review_status"] == PARTIAL
    assert report["promotion_status"] == NEEDS_MORE_EVIDENCE
    assert report["promotion_eligible"] is False


# -- promotion consistency ----------------------------------------------------


def test_promotion_status_mapping_is_total_and_fail_closed():
    assert promotion_status_for_review(PASS) == PROMOTION_ELIGIBLE
    assert promotion_status_for_review(PARTIAL) == NEEDS_MORE_EVIDENCE
    assert promotion_status_for_review(BLOCKED) == PROMOTION_BLOCKED
    assert promotion_status_for_review("WAT") == PROMOTION_BLOCKED


@pytest.mark.parametrize(
    "artifact_factory, expected_review",
    [
        (lambda: verified_artifact(), PASS),
        (
            lambda: build_candidate_artifact(
                capture_envelope(content_hash="sha256:" + "0" * 64)
            ),
            BLOCKED,
        ),
        (lambda: None, BLOCKED),
    ],
)
def test_review_and_promotion_status_are_consistent(artifact_factory, expected_review):
    report = review_candidate_artifact(artifact_factory())
    assert report["review_status"] == expected_review
    assert report["promotion_status"] == promotion_status_for_review(expected_review)
    check = next(
        check
        for check in report["checks"]
        if check["check"] == "promotion status is valid and consistent with review"
    )
    assert check["status"] == PASS


def test_review_matrix_is_consistent_with_promotion_mapping():
    matrix = reality_candidate_review_matrix()
    assert matrix
    assert {row["review_status"] for row in matrix} <= set(REVIEW_STATUSES)
    for row in matrix:
        assert row["promotion_status"] == promotion_status_for_review(
            row["review_status"]
        )


# -- evidence tagging / no leaks ---------------------------------------------


def test_evidence_items_are_source_tagged():
    report = review_candidate_artifact(verified_artifact())
    assert report["evidence"]
    for item in report["evidence"]:
        assert set(item) == {"source", "detail"}
        assert item["source"] in EVIDENCE_SOURCES
        assert item["detail"]


def test_message_content_is_not_exposed():
    sentinel = "REVIEW_CONTENT_SENTINEL_9f2_DO_NOT_EXPOSE"
    artifact = verified_artifact(content={"text": sentinel})
    report = review_candidate_artifact(artifact)

    assert report["content_exposed"] is False
    assert report["message_content_exposed"] is False
    assert sentinel not in json.dumps(report)
    assert sentinel not in report["markdown"]


def test_review_does_not_mutate_inputs():
    artifact = verified_artifact()
    artifact_before = copy.deepcopy(artifact)

    review_input = candidate_artifact_to_review_input(artifact)
    review_input_before = copy.deepcopy(review_input)

    review_candidate_artifact(artifact)
    review_candidate_artifact(review_input=review_input)

    assert artifact == artifact_before
    assert review_input == review_input_before


# -- no production mutation ---------------------------------------------------


def test_review_is_read_only_and_never_auto_approved():
    report = review_candidate_artifact(verified_artifact())

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


def test_run_metadata_is_cited_or_marked_unknown():
    from personal_ai_execution.reality_candidate_review import REVIEW_RUN_FIELDS

    run = {
        "run_id": "run-1",
        "reader_version": "wechat-reader-v1.0.0",
        "source_db": "messages.sqlite",
        "window_start": "2026-10-01T00:00:00Z",
        "window_end": "2026-10-02T00:00:00Z",
        "produced_at": "2026-10-02T00:00:01Z",
    }
    report = review_candidate_artifact(verified_artifact(), run=run)
    assert set(report["run_fields_present"]) == set(REVIEW_RUN_FIELDS)
    assert report["run_fields_absent"] == []
    assert report["run"]["run_id"] == "run-1"

    bare = review_candidate_artifact(verified_artifact())
    assert bare["run_fields_present"] == []
    assert set(bare["run_fields_absent"]) == set(REVIEW_RUN_FIELDS)


def test_markdown_reports_final_status():
    report = review_candidate_artifact(verified_artifact())
    assert report["markdown"].startswith(f"# {REVIEW_GOAL}")
    assert f"FINAL_STATUS={report['final_status']}" in report["markdown"]
    assert report["final_status"] == (
        "REVIEW_STATUS=PASS;PROMOTION_STATUS=" + PROMOTION_ELIGIBLE
    )
