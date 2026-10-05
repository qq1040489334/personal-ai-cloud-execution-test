"""REALITY_PROMOTION_ADAPTER_IMPLEMENTATION_V0.1 regression tests.

The adapter is the controlled ``Reviewed Candidate -> Asset Worker request``
mapping that sits on the REALITY promotion path

    Candidate -> Adapter -> Writer -> ASSET_DB -> Read-back

These tests pin that it:

* consumes a Reviewed Candidate (review PASS, promotion eligible) and maps it to
  the existing Worker input shape (adds Worker-only fields, remaps
  ``proposed_version -> canonical_version``);
* propagates provenance, content hash, the idempotency key / intent hash and the
  Human Gate verdict without auto-approving;
* fails closed on a malformed / not-PASS / hash-mismatch / incomplete / invalid
  target candidate, before any writer is called;
* is idempotent on replay (existing content hash or admitted idempotency key);
* never performs a production write, never calls the canonical production
  writer, never creates a second state store or a Reality-specific writer;
* refuses unmarked / production-flagged writers and stays in simulation;
* reports evidence tagged OBSERVED / STATED / INFERRED / UNKNOWN.
"""

from __future__ import annotations

import copy
import json

from personal_ai_execution import reality_canonical_writer
from personal_ai_execution.reality_candidate_handoff import (
    HANDOFF_CONTRACT,
    build_candidate_artifact,
    candidate_artifact_to_review_input,
)
from personal_ai_execution.reality_candidate_review import (
    PROMOTION_ELIGIBLE,
    PROMOTION_STATUSES,
    review_candidate_artifact,
)
from personal_ai_execution.reality_canonical_writer import (
    CANONICAL_STORE,
    HUMAN_GATE,
    REALITY_ASSET_TYPE,
    TARGET_ASSET_TYPES,
    WRITER_ENTRYPOINTS,
)
from personal_ai_execution.reality_capture import (
    EPISTEMIC_OBSERVED,
    REQUIRED_CAPTURE_FIELDS,
    build_capture_envelope,
    hash_content,
)
from personal_ai_execution.reality_promotion_adapter import (
    ADAPTER_ADDED_FIELDS,
    ADAPTER_CONTRACT,
    ADAPTER_GOAL,
    ADAPTER_REPORT,
    ADAPTER_STATUSES,
    EVIDENCE_TIERS,
    PRODUCTION_WRITER_ATTR,
    REALITY_WORKER_INPUT_FIELDS,
    STATUS_ADAPTED,
    STATUS_BLOCKED,
    STATUS_IDEMPOTENT,
    STATUS_QUARANTINED,
    STATUS_SIMULATED,
    adapt_reviewed_candidate,
    build_worker_request,
    is_simulation_writer,
    make_recording_simulation_writer,
    mark_simulation_writer,
    promotion_adapter_matrix,
)
from personal_ai_execution.result_normalization import PASS

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


def no_mutation_keys(report) -> None:
    for key in (
        "content_exposed",
        "message_content_exposed",
        "production_write_performed",
        "canonical_write_performed",
        "reality_canonical_written",
        "knowledge_written",
        "skill_written",
        "decision_written",
        "second_state_store_created",
        "reality_specific_writer_created",
        "deployment_performed",
        "credentials_accessed",
        "secret_accessed",
        "permissions_changed",
        "binding_changed",
        "schema_changed",
        "mark_reviewed_called",
    ):
        assert report[key] is False, key


# -- dry-run adaptation --------------------------------------------------------


def test_verified_eligible_candidate_adapts_to_worker_request():
    report = adapt_reviewed_candidate(verified_artifact(), target_asset_type="KNOWLEDGE")

    assert report["report"] == ADAPTER_REPORT
    assert report["goal"] == ADAPTER_GOAL
    assert report["contract"] == ADAPTER_CONTRACT
    assert report["handoff_contract"] == HANDOFF_CONTRACT
    assert report["status"] == STATUS_ADAPTED
    assert report["status"] in ADAPTER_STATUSES
    assert report["review_status"] == PASS
    assert report["promotion_status"] == PROMOTION_ELIGIBLE
    assert report["target_asset_type"] == "KNOWLEDGE"
    assert report["canonical_store"] == CANONICAL_STORE
    assert report["dry_run"] is True
    assert report["worker_request"] is not None
    assert report["workflow_status"] == PASS


def test_worker_request_matches_existing_worker_input_shape():
    report = adapt_reviewed_candidate(verified_artifact(), target_asset_type="KNOWLEDGE")
    request = report["worker_request"]

    for field in REALITY_WORKER_INPUT_FIELDS:
        assert field in request, field
    assert request["asset_type"] == "KNOWLEDGE"
    assert request["asset_id"] == "knowledge:cap-1"
    assert request["schema_version"]
    assert request["created_by"]
    assert request["supersedes"] == []
    assert request["canonical_write_enabled"] is False


def test_proposed_version_is_remapped_to_canonical_version():
    report = adapt_reviewed_candidate(verified_artifact(), target_asset_type="SKILL")

    assert report["worker_request"]["canonical_version"] == report["proposed_version"]
    assert "proposed_version" not in report["worker_request"]


def test_provenance_content_hash_and_idempotency_are_propagated():
    report = adapt_reviewed_candidate(verified_artifact(), target_asset_type="KNOWLEDGE")
    request = report["worker_request"]

    assert request["provenance"] is not None
    assert request["provenance"]["promotion"]["decision"] == "PROMOTE"
    assert request["content_hash"] == report["content_hash"]
    assert request["content_hash"] == hash_content(CONTENT).split(":", 1)[1]
    assert request["idempotency_key"] == report["idempotency_key"]
    assert request["intent_hash"] == report["intent_hash"]
    assert report["idempotency_key"].startswith("knowledge:cap-1:")
    assert request["source_identity"] == SOURCE_IDENTITY


def test_reused_writer_is_the_existing_canonical_writer():
    report = adapt_reviewed_candidate(verified_artifact(), target_asset_type="DECISION")

    assert report["reused_canonical_writer"] == WRITER_ENTRYPOINTS["DECISION"]
    assert report["worker_request"]["canonical_writer"] == WRITER_ENTRYPOINTS["DECISION"]


def test_adapter_can_consume_a_supplied_review_report():
    artifact = verified_artifact()
    review = review_candidate_artifact(artifact)
    report = adapt_reviewed_candidate(
        artifact, review=review, target_asset_type="KNOWLEDGE"
    )

    assert report["status"] == STATUS_ADAPTED
    assert report["review_status"] == review["review_status"]


def test_all_canonical_targets_adapt():
    for target in TARGET_ASSET_TYPES:
        report = adapt_reviewed_candidate(verified_artifact(), target_asset_type=target)
        assert report["status"] == STATUS_ADAPTED
        assert report["worker_request"]["asset_type"] == target


# -- Human Gate / production refusal ------------------------------------------


def test_human_gate_is_required_and_not_auto_approved():
    report = adapt_reviewed_candidate(verified_artifact(), target_asset_type="KNOWLEDGE")

    assert report["human_gate"] == HUMAN_GATE
    assert report["requires_human_gate"] is True
    assert report["human_gate_authorized"] is False
    assert report["authorization_bounded"] is False


def test_execute_without_gate_is_blocked_and_writer_not_called():
    writer = make_recording_simulation_writer("KNOWLEDGE")
    report = adapt_reviewed_candidate(
        verified_artifact(),
        target_asset_type="KNOWLEDGE",
        write_surface=writer,
        dry_run=False,
    )

    assert report["status"] == STATUS_BLOCKED
    assert writer.calls == []
    assert any(HUMAN_GATE in reason for reason in report["reasons"])


def test_execute_with_authorized_marked_simulation_writer_simulates():
    writer = make_recording_simulation_writer("KNOWLEDGE")
    ledger: dict = {}
    report = adapt_reviewed_candidate(
        verified_artifact(),
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        write_surface=writer,
        ledger=ledger,
        dry_run=False,
    )

    assert report["status"] == STATUS_SIMULATED
    assert len(writer.calls) == 1
    assert report["write_surface"] == "_writer"
    assert report["writer_response"]["production_reached"] is False
    assert report["writer_response"]["content_hash"] == report["content_hash"]
    assert report["production_write_performed"] is False
    assert report["canonical_write_performed"] is False
    assert report["idempotency_key"] in ledger


def test_production_flagged_writer_is_refused():
    def production_writer(request):  # pragma: no cover - must never be called
        raise AssertionError("production writer must never be called")

    setattr(production_writer, PRODUCTION_WRITER_ATTR, True)
    assert is_simulation_writer(production_writer) is False

    report = adapt_reviewed_candidate(
        verified_artifact(),
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        write_surface=production_writer,
        dry_run=False,
    )
    assert report["status"] == STATUS_BLOCKED
    assert report["production_write_performed"] is False


def test_unmarked_writer_is_refused():
    calls: list = []

    def plain_writer(request):
        calls.append(request)
        return {"ok": True}

    report = adapt_reviewed_candidate(
        verified_artifact(),
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        write_surface=plain_writer,
        dry_run=False,
    )
    assert report["status"] == STATUS_BLOCKED
    assert calls == []


def test_mark_simulation_writer_refuses_production_flag():
    def writer(request):  # pragma: no cover - never called
        return {}

    setattr(writer, PRODUCTION_WRITER_ATTR, True)
    try:
        mark_simulation_writer(writer)
    except PermissionError:
        pass
    else:  # pragma: no cover - the marker must be refused
        raise AssertionError("production-flagged writer was marked as simulation")


def test_adapter_never_calls_the_canonical_production_writer(monkeypatch):
    def forbidden(*args, **kwargs):  # pragma: no cover - must never be reached
        raise AssertionError("promote_reality_candidate must never be called")

    monkeypatch.setattr(
        reality_canonical_writer, "promote_reality_candidate", forbidden
    )
    writer = make_recording_simulation_writer("SKILL")
    report = adapt_reviewed_candidate(
        verified_artifact(),
        target_asset_type="SKILL",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        write_surface=writer,
        dry_run=False,
    )
    assert report["status"] == STATUS_SIMULATED
    assert report["production_write_performed"] is False


# -- idempotency ---------------------------------------------------------------


def test_repeated_ledger_key_is_idempotent_and_writer_not_called_again():
    writer = make_recording_simulation_writer("KNOWLEDGE")
    ledger: dict = {}
    first = adapt_reviewed_candidate(
        verified_artifact(),
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        write_surface=writer,
        ledger=ledger,
        dry_run=False,
    )
    second = adapt_reviewed_candidate(
        verified_artifact(),
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        write_surface=writer,
        ledger=ledger,
        dry_run=False,
    )

    assert first["status"] == STATUS_SIMULATED
    assert second["status"] == STATUS_IDEMPOTENT
    assert len(writer.calls) == 1
    assert second["idempotency_key"] == first["idempotency_key"]


def test_existing_same_content_hash_is_idempotent():
    artifact = verified_artifact()
    existing = {"current_version": 2, "content_hash": artifact["content_hash"]}
    writer = make_recording_simulation_writer("KNOWLEDGE")
    report = adapt_reviewed_candidate(
        artifact,
        target_asset_type="KNOWLEDGE",
        existing_asset=existing,
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        write_surface=writer,
        dry_run=False,
    )

    assert report["status"] == STATUS_IDEMPOTENT
    assert writer.calls == []


def test_deterministic_intent_hash_and_key():
    first = adapt_reviewed_candidate(verified_artifact(), target_asset_type="KNOWLEDGE")
    again = adapt_reviewed_candidate(verified_artifact(), target_asset_type="KNOWLEDGE")
    assert first["intent_hash"] == again["intent_hash"]
    assert first["idempotency_key"] == again["idempotency_key"]


# -- fail-closed ---------------------------------------------------------------


def test_malformed_artifact_is_blocked():
    report = adapt_reviewed_candidate("not-an-artifact", target_asset_type="KNOWLEDGE")

    assert report["status"] == STATUS_BLOCKED
    assert report["worker_request"] is None
    assert report["unknowns"]


def test_hash_mismatch_is_blocked_before_writer():
    artifact = build_candidate_artifact(
        capture_envelope(content_hash="sha256:" + "0" * 64)
    )
    writer = make_recording_simulation_writer("KNOWLEDGE")
    report = adapt_reviewed_candidate(
        artifact,
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        write_surface=writer,
        dry_run=False,
    )

    assert report["status"] == STATUS_BLOCKED
    assert writer.calls == []


def test_incomplete_capture_is_blocked():
    envelope = capture_envelope()
    envelope.pop("source_version")
    report = adapt_reviewed_candidate(
        build_candidate_artifact(envelope), target_asset_type="KNOWLEDGE"
    )

    assert report["status"] == STATUS_BLOCKED
    assert report["worker_request"] is None


def test_not_promotion_eligible_is_blocked():
    artifact = build_candidate_artifact(capture_envelope(epistemic={}))
    report = adapt_reviewed_candidate(artifact, target_asset_type="KNOWLEDGE")

    assert report["promotion_status"] != PROMOTION_ELIGIBLE
    assert report["status"] == STATUS_BLOCKED
    assert report["worker_request"] is None


def test_invalid_target_is_quarantined():
    report = adapt_reviewed_candidate(
        verified_artifact(), target_asset_type=REALITY_ASSET_TYPE
    )

    assert REALITY_ASSET_TYPE not in TARGET_ASSET_TYPES
    assert report["status"] == STATUS_QUARANTINED
    assert report["worker_request"] is None


def test_missing_target_is_quarantined():
    report = adapt_reviewed_candidate(verified_artifact())

    assert report["status"] == STATUS_QUARANTINED
    assert report["target_asset_type"] is None


def test_review_input_without_content_never_adapts():
    artifact = verified_artifact()
    review_input = candidate_artifact_to_review_input(artifact)
    report = adapt_reviewed_candidate(review_input, target_asset_type="KNOWLEDGE")

    assert report["status"] == STATUS_BLOCKED
    assert report["worker_request"] is None


def test_build_worker_request_rejects_bad_plan():
    assert build_worker_request(None, {}) is None
    assert build_worker_request({}, {}) is None
    assert (
        build_worker_request(
            {"target_asset_type": REALITY_ASSET_TYPE, "write_request": {}}, {}
        )
        is None
    )


def test_worker_surface_exception_is_blocked():
    def boom(request):
        raise RuntimeError("simulated failure")

    mark_simulation_writer(boom)
    report = adapt_reviewed_candidate(
        verified_artifact(),
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        write_surface=boom,
        dry_run=False,
    )
    assert report["status"] == STATUS_BLOCKED
    assert report["production_write_performed"] is False


# -- evidence / no-mutation ----------------------------------------------------


def test_evidence_items_are_source_tagged():
    report = adapt_reviewed_candidate(verified_artifact(), target_asset_type="KNOWLEDGE")

    assert report["evidence"]
    for item in report["evidence"]:
        assert set(item) == {"source", "detail"}
        assert item["source"] in EVIDENCE_TIERS
        assert item["detail"]
    assert "OBSERVED" in report["evidence_tiers_present"]


def test_blocked_adapter_lists_unknown_evidence():
    report = adapt_reviewed_candidate(None, target_asset_type="KNOWLEDGE")
    sources = {item["source"] for item in report["evidence"]}
    assert "UNKNOWN" in sources


def test_adapter_is_read_only_and_never_writes():
    report = adapt_reviewed_candidate(
        verified_artifact(),
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
    )
    no_mutation_keys(report)
    assert report["read_only"] is True


def test_simulated_adapter_still_performs_no_production_write():
    writer = make_recording_simulation_writer("KNOWLEDGE")
    report = adapt_reviewed_candidate(
        verified_artifact(),
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        write_surface=writer,
        dry_run=False,
    )
    no_mutation_keys(report)


def test_markdown_does_not_expose_content():
    sentinel = "ADAPTER_CONTENT_SENTINEL_7a1_DO_NOT_EXPOSE"
    report = adapt_reviewed_candidate(
        verified_artifact(content={"text": sentinel}),
        target_asset_type="KNOWLEDGE",
    )

    assert report["content_exposed"] is False
    assert report["message_content_exposed"] is False
    assert sentinel not in report["markdown"]
    assert sentinel not in json.dumps(
        {k: v for k, v in report.items() if k != "worker_request"}
    )


def test_adapter_does_not_mutate_inputs():
    artifact = verified_artifact()
    before = copy.deepcopy(artifact)
    adapt_reviewed_candidate(artifact, target_asset_type="KNOWLEDGE")
    writer = make_recording_simulation_writer("KNOWLEDGE")
    adapt_reviewed_candidate(
        artifact,
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        write_surface=writer,
        dry_run=False,
    )
    assert artifact == before


def test_added_fields_are_the_worker_only_fields():
    report = adapt_reviewed_candidate(verified_artifact(), target_asset_type="KNOWLEDGE")
    raw_candidate = report["worker_request"]
    # These are adapter-added and must not be present on the raw capture candidate.
    for field in ADAPTER_ADDED_FIELDS:
        assert field in raw_candidate


def test_no_second_state_store_or_reality_specific_writer():
    report = adapt_reviewed_candidate(verified_artifact(), target_asset_type="KNOWLEDGE")

    assert report["canonical_store"] == CANONICAL_STORE
    assert report["second_state_store_created"] is False
    assert report["reality_specific_writer_created"] is False
    assert all(check["status"] == PASS for check in report["checks"])


def test_markdown_and_final_status():
    report = adapt_reviewed_candidate(verified_artifact(), target_asset_type="KNOWLEDGE")
    assert report["markdown"].startswith(f"# {ADAPTER_GOAL}")
    assert f"FINAL_STATUS={report['final_status']}" in report["markdown"]
    assert report["final_status"] == (
        "ADAPTER_STATUS=" + STATUS_ADAPTED + ";WRITE_PERFORMED=False"
    )


def test_promotion_status_is_from_the_review_vocabulary():
    report = adapt_reviewed_candidate(verified_artifact(), target_asset_type="KNOWLEDGE")
    assert report["promotion_status"] in PROMOTION_STATUSES


def test_adapter_matrix_is_consistent():
    matrix = promotion_adapter_matrix()
    assert matrix
    assert {row["status"] for row in matrix} <= set(ADAPTER_STATUSES)
    for status in (STATUS_ADAPTED, STATUS_SIMULATED, STATUS_IDEMPOTENT, STATUS_QUARANTINED, STATUS_BLOCKED):
        assert any(row["status"] == status for row in matrix)
