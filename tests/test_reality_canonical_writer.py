"""REALITY canonical writer regression tests.

``REALITY_CANONICAL_WRITER_V0.1`` is the fail-closed promotion boundary between a
normalized REALITY candidate (L2, ``reality_capture.py``) and the existing
Personal AI Canonical write surface (``ASSET_DB: assets / asset_versions``).

The writer accepts a candidate **only** when the L2 result is ``VERIFIED`` and
``promotion_eligible`` is ``True``, re-validates schema, provenance, hash,
idempotency, duplicate detection and the human gate before any write, reuses the
existing Knowledge / Skill / Decision writer entry points without creating a
second state store, and is idempotent on repeat. A real production write
requires an injected, existing write surface; otherwise the result is ``BLOCKED``
with the exact ``ASSET_DB`` dependency.
"""

from __future__ import annotations

import copy

from personal_ai_execution.provenance_contract import (
    PROVENANCE_CONTRACT_VERSION,
    STATUS_VERIFIED as PROV_VERIFIED,
)
from personal_ai_execution.reality_canonical_writer import (
    CANONICAL_STORE,
    HUMAN_GATE,
    REALITY_ROLE,
    STATUS_BLOCKED,
    STATUS_IDEMPOTENT,
    STATUS_PROMOTED,
    STATUS_QUARANTINED,
    TARGET_ASSET_TYPES,
    WRITER_CONTRACTS,
    WRITER_ENTRYPOINTS,
    prepare_promotion,
    promote_reality_candidate,
    validate_candidate,
    writer_matrix,
)
from personal_ai_execution.reality_capture import (
    EPISTEMIC_OBSERVED,
    REQUIRED_CAPTURE_FIELDS,
    build_capture_envelope,
    hash_content,
    normalize_reality_capture,
)

CAPTURED_AT = "2026-10-01T00:00:00+00:00"
CONTENT = "hello reality"
EVIDENCE = {"method": "caller_snapshot", "checked_by": "bridge"}


def observed_epistemic():
    return {field: EPISTEMIC_OBSERVED for field in REQUIRED_CAPTURE_FIELDS}


def normalized(**overrides):
    envelope = build_capture_envelope(
        source_identity="wechat:conversation:42",
        source_location="wechat://local-snapshot/snap-42",
        source_version="rev-3",
        content_version="content-7",
        captured_at=CAPTURED_AT,
        content=CONTENT,
        verification_evidence=EVIDENCE,
        capture_id="snap-42",
        message_id="msg-42",
        epistemic=observed_epistemic(),
    )
    envelope.update(overrides)
    return normalize_reality_capture(envelope)


class FakeWriteSurface:
    def __init__(self):
        self.calls = []

    def __call__(self, request):
        self.calls.append(copy.deepcopy(request))
        return {"ok": True, "asset_id": request["asset_id"], "version": request["proposed_version"]}


def test_only_verified_promotion_eligible_is_eligible():
    audit = validate_candidate(normalized(), target_asset_type="KNOWLEDGE")
    assert audit["eligible"] is True
    assert audit["status"] == "ELIGIBLE"
    assert audit["provenance_status"] == PROV_VERIFIED
    assert audit["hash_match"] is True


def test_status_not_verified_is_quarantined():
    bad = normalized(content_hash="sha256:" + "0" * 64)
    audit = validate_candidate(bad, target_asset_type="KNOWLEDGE")
    assert audit["eligible"] is False
    assert audit["status"] == STATUS_QUARANTINED
    assert any("VERIFIED" in r for r in audit["reasons"])


def test_not_promotion_eligible_is_quarantined():
    stated = normalized(epistemic={})
    assert stated["promotion_eligible"] is False
    audit = validate_candidate(stated, target_asset_type="KNOWLEDGE")
    assert audit["eligible"] is False
    assert any("promotion_eligible" in r for r in audit["reasons"])


def test_incomplete_capture_is_quarantined():
    incomplete = normalized(verification_evidence=None)
    audit = validate_candidate(incomplete, target_asset_type="KNOWLEDGE")
    assert audit["eligible"] is False


def test_reality_target_is_quarantined():
    audit = validate_candidate(normalized(), target_asset_type="REALITY")
    assert audit["eligible"] is False
    assert any("never a target" in r for r in audit["reasons"])


def test_non_mapping_candidate_is_quarantined():
    audit = validate_candidate("not-a-mapping", target_asset_type="KNOWLEDGE")
    assert audit["eligible"] is False


def test_prepare_is_zero_mutation_and_routed():
    plan = prepare_promotion(normalized(), target_asset_type="KNOWLEDGE")
    assert plan["status"] == "PREPARED"
    assert plan["production_write_performed"] is False
    assert plan["second_state_store_created"] is False
    assert plan["canonical_store"] == CANONICAL_STORE
    assert plan["reality_role"] == REALITY_ROLE
    assert plan["reused_canonical_writer"] == WRITER_ENTRYPOINTS["KNOWLEDGE"]
    assert plan["reused_writer_contract"] == WRITER_CONTRACTS["KNOWLEDGE"]
    assert plan["write_request"]["content_hash"] == hash_content(CONTENT).split(":", 1)[1]
    assert plan["write_request"]["provenance_contract"] == PROVENANCE_CONTRACT_VERSION


def test_prepare_all_targets_reuse_existing_writers():
    for target in TARGET_ASSET_TYPES:
        plan = prepare_promotion(normalized(), target_asset_type=target)
        assert plan["target_asset_type"] == target
        assert plan["reused_canonical_writer"] == WRITER_ENTRYPOINTS[target]
        assert plan["reused_writer_contract"] == WRITER_CONTRACTS[target]


def test_intent_hash_and_idempotency_key_are_deterministic():
    first = prepare_promotion(normalized(), target_asset_type="KNOWLEDGE")
    again = prepare_promotion(normalized(), target_asset_type="KNOWLEDGE")
    assert first["intent_hash"] == again["intent_hash"]
    assert first["idempotency_key"] == again["idempotency_key"]
    assert first["idempotency_key"].startswith("knowledge:snap-42:")


def test_input_is_never_mutated():
    candidate = normalized()
    snapshot = copy.deepcopy(candidate)
    prepare_promotion(candidate, target_asset_type="SKILL")
    promote_reality_candidate(candidate, target_asset_type="SKILL")
    assert candidate == snapshot


def test_promote_with_authorization_and_surface_writes_once():
    surface = FakeWriteSurface()
    ledger: dict = {}
    result = promote_reality_candidate(
        normalized(),
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        ledger=ledger,
        write_surface=surface,
    )
    assert result["status"] == STATUS_PROMOTED
    assert result["canonical_write_performed"] is True
    assert len(surface.calls) == 1
    assert result["idempotency_key"] in ledger


def test_repeated_promotion_is_idempotent_and_no_duplicate():
    surface = FakeWriteSurface()
    ledger: dict = {}
    first = promote_reality_candidate(
        normalized(),
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        ledger=ledger,
        write_surface=surface,
    )
    second = promote_reality_candidate(
        normalized(),
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        ledger=ledger,
        write_surface=surface,
    )
    assert first["status"] == STATUS_PROMOTED
    assert second["status"] == STATUS_IDEMPOTENT
    assert len(surface.calls) == 1
    assert second["canonical_write_performed"] is False


def test_existing_same_content_hash_is_idempotent():
    surface = FakeWriteSurface()
    existing = {"current_version": 3, "content_hash": hash_content(CONTENT)}
    result = promote_reality_candidate(
        normalized(),
        target_asset_type="KNOWLEDGE",
        existing_asset=existing,
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        write_surface=surface,
    )
    assert result["status"] == STATUS_IDEMPOTENT
    assert surface.calls == []


def test_unauthorized_is_blocked():
    surface = FakeWriteSurface()
    result = promote_reality_candidate(
        normalized(), target_asset_type="KNOWLEDGE", write_surface=surface
    )
    assert result["status"] == STATUS_BLOCKED
    assert surface.calls == []
    assert any(HUMAN_GATE in r for r in result["reasons"])


def test_authorized_without_write_surface_is_blocked_with_dependency():
    result = promote_reality_candidate(
        normalized(),
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
    )
    assert result["status"] == STATUS_BLOCKED
    assert result["canonical_write_performed"] is False
    assert any("ASSET_DB" in r for r in result["reasons"])


def test_ineligible_never_reaches_write_surface():
    surface = FakeWriteSurface()
    bad = normalized(content_hash="sha256:" + "0" * 64)
    result = promote_reality_candidate(
        bad,
        target_asset_type="KNOWLEDGE",
        human_gate_authorized=True,
        authorization=HUMAN_GATE,
        write_surface=surface,
    )
    assert result["status"] == STATUS_QUARANTINED
    assert surface.calls == []


def test_tampered_content_hash_fails_integrity():
    candidate = normalized()
    candidate["candidate"]["content"] = "tampered after capture"
    audit = validate_candidate(candidate, target_asset_type="KNOWLEDGE")
    assert audit["eligible"] is False
    assert audit["hash_match"] is False


def test_provenance_is_reevaluated_verified_after_promotion():
    audit = validate_candidate(normalized(), target_asset_type="KNOWLEDGE")
    assert audit["provenance_status"] == PROV_VERIFIED
    assert audit["promoted_provenance"]["promotion"]["decision"] == "PROMOTE"


def test_writer_matrix_documented_statuses():
    statuses = {row["status"] for row in writer_matrix()}
    assert statuses == {
        STATUS_PROMOTED,
        STATUS_IDEMPOTENT,
        STATUS_QUARANTINED,
        STATUS_BLOCKED,
    }
