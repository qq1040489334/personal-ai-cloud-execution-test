"""REALITY capture/normalization contract regression tests.

``normalize_reality_capture`` maps a caller-supplied (untrusted) WeChat snapshot
envelope into a normalized ``REALITY`` *candidate*. The boundary is read-only and
fail-closed:

* a structurally complete, hash-consistent capture is ``VERIFIED``;
* a capture missing (or explicitly ``UNKNOWN`` for) a required field is
  ``INCOMPLETE`` and never verified;
* a declared content hash that disagrees with the recomputed hash is
  ``HASH_MISMATCH`` and never verified;
* present values default to ``STATED`` (never ``OBSERVED``);
* promotion-time fields stay ``UNKNOWN`` for the separate, gated writer.

It reuses ``PERSONAL_AI_ASSET_PROVENANCE_V0.2`` field aliases and
``evaluate_provenance``; a regression test asserts that reuse so the two
vocabularies cannot drift.
"""

from __future__ import annotations

import copy

from personal_ai_execution.provenance_contract import (
    PROVENANCE_CONTRACT_VERSION,
    PROVENANCE_FIELD_ALIASES,
)
from personal_ai_execution.reality_capture import (
    EPISTEMIC_INFERRED,
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_STATUSES,
    EPISTEMIC_UNKNOWN,
    REALITY_CANDIDATE_FIELDS,
    REALITY_CONTRACT_VERSION,
    REALITY_FIELD_ALIASES,
    REALITY_STATUSES,
    REQUIRED_CAPTURE_FIELDS,
    STATUS_HASH_MISMATCH,
    STATUS_INCOMPLETE,
    STATUS_VERIFIED,
    build_capture_envelope,
    hash_content,
    normalize_reality_capture,
    reality_matrix,
)

CAPTURED_AT = "2026-10-01T00:00:00+00:00"
CONTENT = "hello reality"


def complete_envelope(**overrides):
    envelope = build_capture_envelope(
        source_identity="wechat:conversation:42",
        source_location="wechat://local-snapshot/snap-42",
        source_version="rev-3",
        content_version="content-7",
        captured_at=CAPTURED_AT,
        content=CONTENT,
        verification_evidence={"method": "caller_snapshot", "checked_by": "bridge"},
        capture_id="snap-42",
        message_id="msg-42",
    )
    envelope.update(overrides)
    return envelope


def observed_epistemic():
    return {field: EPISTEMIC_OBSERVED for field in REQUIRED_CAPTURE_FIELDS}


# -- version / structure ----------------------------------------------------


def test_contract_and_provenance_versions():
    result = normalize_reality_capture(complete_envelope())
    assert result["contract"] == REALITY_CONTRACT_VERSION
    assert result["provenance_contract"] == PROVENANCE_CONTRACT_VERSION
    assert result["provenance_contract"] == PROVENANCE_CONTRACT_VERSION


def test_asset_type_always_reality_candidate():
    result = normalize_reality_capture(complete_envelope(asset_type="SOMETHING_ELSE"))
    assert result["candidate"]["asset_type"] == "REALITY"
    assert result["fields"]["asset_type"] == "SOMETHING_ELSE"


def test_statuses_and_epistemic_statuses_are_fixed_sets():
    assert REALITY_STATUSES == (
        STATUS_VERIFIED,
        STATUS_INCOMPLETE,
        STATUS_HASH_MISMATCH,
    )
    assert EPISTEMIC_STATUSES == (
        EPISTEMIC_OBSERVED,
        EPISTEMIC_STATED,
        EPISTEMIC_INFERRED,
        EPISTEMIC_UNKNOWN,
    )


# -- matrix -----------------------------------------------------------------


def test_reality_matrix_statuses_match_contract():
    matrix = reality_matrix()
    assert len(matrix) == 5
    scenarios = {row["scenario"]: row for row in matrix}
    assert (
        scenarios[
            "complete envelope, declared hash agrees with recomputed hash"
        ]["status"]
        == STATUS_VERIFIED
    )
    assert scenarios["capture evidence never supplied"]["status"] == STATUS_INCOMPLETE
    assert (
        scenarios["declared content hash disagrees with recomputed hash"]["status"]
        == STATUS_HASH_MISMATCH
    )
    assert (
        scenarios["required field only UNKNOWN epistemic status"]["status"]
        == STATUS_INCOMPLETE
    )
    assert (
        scenarios["unrecognized epistemic status on a captured field"]["status"]
        == STATUS_INCOMPLETE
    )


def test_reality_matrix_is_defensive_copy():
    first = reality_matrix()
    first[0]["status"] = "TAMPERED"
    assert reality_matrix()[0]["status"] == STATUS_VERIFIED


# -- complete capture -------------------------------------------------------


def test_complete_envelope_is_verified():
    result = normalize_reality_capture(complete_envelope())
    assert result["status"] == STATUS_VERIFIED
    assert result["complete"] is True
    assert result["verified"] is True
    assert result["missing"] == []
    assert result["invalid"] == []
    assert result["hash_checked"] is True
    assert result["hash_match"] is True
    assert result["read_only"] is True
    assert result["write_performed"] is False


def test_declared_and_recomputed_hash_agree():
    envelope = complete_envelope(content_hash=hash_content(CONTENT))
    result = normalize_reality_capture(envelope)
    assert result["status"] == STATUS_VERIFIED
    assert result["candidate"]["content_hash"] == hash_content(CONTENT)


def test_content_hash_is_recomputed_over_opaque_content():
    envelope = complete_envelope(content_hash="sha256:deadbeef")
    result = normalize_reality_capture(envelope)
    assert result["candidate"]["content_hash"] == hash_content(CONTENT)
    assert result["candidate"]["content_hash"] != "sha256:deadbeef"


def test_hash_prefix_and_case_are_normalized():
    computed = hash_content(CONTENT)
    envelope = complete_envelope(content_hash=computed[7:].upper())
    result = normalize_reality_capture(envelope)
    assert result["status"] == STATUS_VERIFIED
    assert result["hash_match"] is True


# -- fail-closed paths ------------------------------------------------------


def test_hash_mismatch_is_never_verified():
    envelope = complete_envelope(content_hash="sha256:" + "0" * 64)
    result = normalize_reality_capture(envelope)
    assert result["status"] == STATUS_HASH_MISMATCH
    assert result["verified"] is False
    assert result["hash_match"] is False
    assert result["complete"] is True


def test_missing_evidence_is_incomplete():
    envelope = complete_envelope()
    envelope["verification_evidence"] = None
    result = normalize_reality_capture(envelope)
    assert result["status"] == STATUS_INCOMPLETE
    assert result["verified"] is False
    assert "verification_evidence" in result["missing"]


def test_missing_required_fields_listed_in_contract_order():
    result = normalize_reality_capture(
        {"source_identity": "wechat:conversation:42", "content": CONTENT}
    )
    assert result["status"] == STATUS_INCOMPLETE
    expected = [
        f for f in REQUIRED_CAPTURE_FIELDS if f not in {"source_identity", "content"}
    ]
    assert result["missing"] == expected


def test_required_field_marked_unknown_is_treated_missing():
    envelope = complete_envelope(epistemic={"content": EPISTEMIC_UNKNOWN})
    result = normalize_reality_capture(envelope)
    assert result["status"] == STATUS_INCOMPLETE
    assert "content" in result["missing"]
    assert result["verified"] is False


def test_invalid_epistemic_token_is_reported_and_incomplete():
    envelope = complete_envelope(epistemic={"content": "PROBABLY"})
    result = normalize_reality_capture(envelope)
    assert result["status"] == STATUS_INCOMPLETE
    assert "content" in result["invalid"]
    assert result["epistemic"]["content"] == EPISTEMIC_UNKNOWN
    assert result["verified"] is False


def test_non_mapping_envelope_is_incomplete_not_crash():
    result = normalize_reality_capture(None)
    assert result["status"] == STATUS_INCOMPLETE
    assert set(result["missing"]) == set(REQUIRED_CAPTURE_FIELDS)
    assert result["write_performed"] is False


# -- epistemology -----------------------------------------------------------


def test_present_values_default_to_stated_never_observed():
    result = normalize_reality_capture(complete_envelope())
    assert result["epistemic"]["source_identity"] == EPISTEMIC_STATED
    assert result["epistemic"]["content"] == EPISTEMIC_STATED
    assert result["promotion_eligible"] is False


def test_promotion_eligible_only_when_required_are_observed():
    result = normalize_reality_capture(
        complete_envelope(epistemic=observed_epistemic())
    )
    assert result["status"] == STATUS_VERIFIED
    assert result["promotion_eligible"] is True


def test_inferred_status_blocks_promotion_eligibility():
    result = normalize_reality_capture(
        complete_envelope(epistemic={"content": EPISTEMIC_INFERRED})
    )
    assert result["epistemic"]["content"] == EPISTEMIC_INFERRED
    assert result["promotion_eligible"] is False


def test_record_default_epistemic_applies_to_present_fields():
    envelope = complete_envelope()
    envelope.pop("epistemic")
    envelope["evidence_status"] = EPISTEMIC_OBSERVED
    result = normalize_reality_capture(envelope)
    assert result["epistemic"]["content"] == EPISTEMIC_OBSERVED
    assert result["promotion_eligible"] is True


def test_epistemic_summary_buckets():
    envelope = complete_envelope(
        epistemic={
            "content": EPISTEMIC_OBSERVED,
            "captured_at": EPISTEMIC_INFERRED,
        }
    )
    summary = normalize_reality_capture(envelope)["epistemic_summary"]
    assert "content" in summary["observed"]
    assert "captured_at" in summary["inferred"]
    assert "source_identity" in summary["stated"]
    assert "promotion_decision" in summary["unknown"]


# -- aliases / identity -----------------------------------------------------


def test_nested_provenance_style_aliases_resolve():
    envelope = {
        "source": {
            "identity": "wechat:conversation:42",
            "location": "wechat://local-snapshot/snap-42",
            "version": "rev-3",
            "content_version": "content-7",
            "captured_at": CAPTURED_AT,
        },
        "content": CONTENT,
        "verification": {"evidence": {"method": "caller_snapshot"}},
    }
    result = normalize_reality_capture(envelope)
    assert result["status"] == STATUS_VERIFIED
    assert result["candidate"]["source_identity"] == "wechat:conversation:42"
    assert result["candidate"]["source_location"] == "wechat://local-snapshot/snap-42"


def test_wechat_source_alias_resolves():
    envelope = complete_envelope(source_identity=None)
    envelope.pop("source_identity")
    envelope["wechat_source"] = "wechat:conversation:99"
    result = normalize_reality_capture(envelope)
    assert result["candidate"]["source_identity"] == "wechat:conversation:99"


def test_candidate_id_falls_back_to_message_then_capture():
    by_message = complete_envelope()
    by_message.pop("capture_id")
    assert (
        normalize_reality_capture(by_message)["candidate"]["candidate_id"] == "msg-42"
    )

    by_capture = complete_envelope()
    by_capture.pop("message_id")
    assert (
        normalize_reality_capture(by_capture)["candidate"]["candidate_id"] == "snap-42"
    )


# -- provenance promotion fields / reuse ------------------------------------


def test_promotion_fields_unset_and_unknown_at_capture():
    result = normalize_reality_capture(complete_envelope())
    candidate = result["candidate"]
    for field in (
        "canonical_version",
        "promotion_decision",
        "promotion_event",
        "promoted_at",
    ):
        assert candidate[field] is None
        assert result["epistemic"][field] == EPISTEMIC_UNKNOWN


def test_provenance_completeness_incomplete_until_promotion():
    result = normalize_reality_capture(complete_envelope())
    completeness = result["provenance_completeness"]
    assert completeness["contract"] == PROVENANCE_CONTRACT_VERSION
    assert completeness["status"] == STATUS_INCOMPLETE
    assert completeness["verified"] is False
    assert "promotion_decision" in completeness["missing"]


def test_reality_aliases_do_not_drift_from_provenance_aliases():
    for field, aliases in PROVENANCE_FIELD_ALIASES.items():
        if field not in REALITY_FIELD_ALIASES:
            continue
        reality_aliases = REALITY_FIELD_ALIASES[field]
        assert reality_aliases[: len(aliases)] == aliases, field


# -- purity -----------------------------------------------------------------


def test_input_mapping_is_never_mutated():
    envelope = complete_envelope(epistemic={"content": EPISTEMIC_OBSERVED})
    snapshot = copy.deepcopy(envelope)
    normalize_reality_capture(envelope)
    assert envelope == snapshot


def test_structured_content_hashes_canonically():
    assert hash_content({"b": 1, "a": 2}) == hash_content({"a": 2, "b": 1})
    envelope = complete_envelope(content={"b": 1, "a": 2})
    result = normalize_reality_capture(envelope)
    assert result["candidate"]["content_hash"] == hash_content({"a": 2, "b": 1})


def test_all_candidate_fields_are_present_in_output():
    result = normalize_reality_capture(complete_envelope())
    for field in REALITY_CANDIDATE_FIELDS:
        assert field in result["candidate"]
        assert field in result["epistemic"]
