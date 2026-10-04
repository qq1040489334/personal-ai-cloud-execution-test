"""REALITY daily WeChat snapshot adapter regression tests.

The adapter is a cloud-side L2 boundary that maps a local ``wechat-reader-v1``
output item into the existing REALITY capture envelope and assembles a daily
bundle. It is dry-run only: no production write, no Canonical write, no second
state store. These tests pin the contract properties:

* reader output -> existing capture envelope mapping (no alternate schema);
* a reader item normalizes through ``normalize_reality_capture`` unchanged;
* UNKNOWN/missing source metadata stays missing and can never silently become
  ``VERIFIED``;
* ``content_available=false`` is ``INCOMPLETE`` and never verified;
* declared-hash disagreement is ``HASH_MISMATCH``;
* bundle id / idempotency keys are deterministic;
* promotion is only previewed through the existing gated writer and REALITY is
  never a target;
* evidence distinguishes OBSERVED / STATED / INFERRED / UNKNOWN.
"""

from __future__ import annotations

import copy

from personal_ai_execution.reality_capture import (
    EPISTEMIC_INFERRED,
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_UNKNOWN,
    REALITY_CONTRACT_VERSION,
    REQUIRED_CAPTURE_FIELDS,
    STATUS_HASH_MISMATCH,
    STATUS_INCOMPLETE,
    STATUS_VERIFIED,
    hash_content,
    normalize_reality_capture,
)
from personal_ai_execution.reality_canonical_writer import (
    HUMAN_GATE,
    STATUS_QUARANTINED,
    WRITER_CONTRACT_VERSION,
    prepare_promotion,
)
from personal_ai_execution.reality_daily_snapshot import (
    BUNDLE_CONTRACT,
    READER_CAPABILITY,
    MODE_DRY_RUN,
    assemble_daily_bundle,
    bundle_fingerprint,
    bundle_id_for,
    bundle_idempotency_key,
    dry_run_bundle,
    reader_item_to_envelope,
    snapshot_idempotency_key,
    validate_bundle,
)

CAPTURED_AT = "2026-10-01T00:00:00+00:00"
WINDOW_START = "2026-10-01T00:00:00+00:00"
WINDOW_END = "2026-10-02T00:00:00+00:00"
CONTENT = "hello reality"
CHAT_ID = "conv-42"


def reader_item(**overrides):
    item = {
        "chat_id": CHAT_ID,
        "message_id": "msg-42",
        "sender_id": "user-7",
        "create_time_iso": CAPTURED_AT,
        "content_available": True,
        "source_db": "MSG.db",
        "content": CONTENT,
        "source_version": "rev-3",
        "content_version": "content-7",
    }
    item.update(overrides)
    return item


def observed_epistemic():
    return {field: EPISTEMIC_OBSERVED for field in REQUIRED_CAPTURE_FIELDS}


def daily_bundle(items=None, **overrides):
    kwargs = {
        "chat_id": CHAT_ID,
        "reader_items": items if items is not None else [reader_item()],
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "reader_version": "1.4.0",
        "observed_at": "2026-10-02T00:05:00+00:00",
    }
    kwargs.update(overrides)
    return assemble_daily_bundle(**kwargs)


# -- reader output -> existing capture envelope -----------------------------


def test_reader_item_maps_to_existing_capture_envelope_fields():
    envelope = reader_item_to_envelope(reader_item())
    assert envelope["source_identity"] == "wechat:conversation:conv-42"
    assert envelope["source_location"] == "wechat://local-snapshot/MSG.db/conv-42"
    assert envelope["source_version"] == "rev-3"
    assert envelope["content_version"] == "content-7"
    assert envelope["captured_at"] == CAPTURED_AT
    assert envelope["message_id"] == "msg-42"
    assert envelope["content"] == CONTENT


def test_reader_item_evidence_is_explicit_capability_object():
    envelope = reader_item_to_envelope(
        reader_item(), reader_version="1.4.0", observed_at="2026-10-02T00:05:00+00:00"
    )
    evidence = envelope["verification_evidence"]
    assert evidence["capability"] == READER_CAPABILITY
    assert evidence["method"] == READER_CAPABILITY
    assert evidence["reader_version"] == "1.4.0"
    assert evidence["source_db"] == "MSG.db"
    assert evidence["sender_id"] == "user-7"
    assert evidence["content_available"] is True


def test_reader_item_uses_build_capture_envelope_shape():
    envelope = reader_item_to_envelope(reader_item())
    for key in REQUIRED_CAPTURE_FIELDS:
        assert key in envelope


def test_source_location_is_opaque_and_does_not_leak_local_path():
    envelope = reader_item_to_envelope(
        reader_item(source_db="C:/Users/me/Documents/WeChat/Msg.db")
    )
    location = envelope["source_location"]
    assert location.startswith("wechat://local-snapshot/")
    assert "C:" not in location
    assert location.endswith("/conv-42")


# -- normalization through the existing L2 contract -------------------------


def test_reader_item_normalizes_to_verified_candidate():
    result = normalize_reality_capture(reader_item_to_envelope(reader_item()))
    assert result["status"] == STATUS_VERIFIED
    assert result["verified"] is True
    assert result["candidate"]["asset_type"] == "REALITY"
    assert result["candidate"]["source_identity"] == "wechat:conversation:conv-42"
    assert result["write_performed"] is False


def test_synthesized_fields_default_to_inferred_not_observed():
    result = normalize_reality_capture(reader_item_to_envelope(reader_item()))
    assert result["epistemic"]["source_identity"] == EPISTEMIC_INFERRED
    assert result["epistemic"]["source_location"] == EPISTEMIC_INFERRED
    assert result["epistemic"]["verification_evidence"] == EPISTEMIC_INFERRED
    assert result["promotion_eligible"] is False


def test_explicit_observed_attestation_can_be_promotion_eligible():
    item = reader_item(epistemic=observed_epistemic())
    result = normalize_reality_capture(reader_item_to_envelope(item))
    assert result["status"] == STATUS_VERIFIED
    assert result["promotion_eligible"] is True


def test_declared_hash_is_checked_against_recomputed_hash():
    ok = reader_item_to_envelope(reader_item(content_hash=hash_content(CONTENT)))
    assert normalize_reality_capture(ok)["status"] == STATUS_VERIFIED

    bad = reader_item_to_envelope(reader_item(content_hash="sha256:" + "0" * 64))
    result = normalize_reality_capture(bad)
    assert result["status"] == STATUS_HASH_MISMATCH
    assert result["verified"] is False


# -- fail-closed: UNKNOWN stays UNKNOWN -------------------------------------


def test_missing_chat_id_never_verifies():
    item = reader_item()
    item.pop("chat_id")
    result = normalize_reality_capture(reader_item_to_envelope(item))
    assert result["status"] == STATUS_INCOMPLETE
    assert "source_identity" in result["missing"]
    assert result["verified"] is False


def test_missing_source_version_never_verifies_even_if_attested_observed():
    item = reader_item(epistemic=observed_epistemic())
    item.pop("source_version")
    result = normalize_reality_capture(reader_item_to_envelope(item))
    assert result["status"] == STATUS_INCOMPLETE
    assert "source_version" in result["missing"]
    assert result["verified"] is False


def test_content_unavailable_is_incomplete_and_never_verified():
    item = reader_item(content_available=False)
    envelope = reader_item_to_envelope(item)
    assert envelope["content"] is None
    result = normalize_reality_capture(envelope)
    assert result["status"] == STATUS_INCOMPLETE
    assert "content" in result["missing"]
    assert result["verified"] is False


def test_content_unavailable_drops_supplied_content_payload():
    item = reader_item(content_available=False, content="must not leak")
    assert reader_item_to_envelope(item)["content"] is None


def test_unknown_metadata_never_silently_becomes_verified():
    item = reader_item()
    item.pop("source_version")
    item.pop("content_version")
    item["epistemic"] = observed_epistemic()
    result = normalize_reality_capture(reader_item_to_envelope(item))
    assert result["status"] == STATUS_INCOMPLETE
    assert result["verified"] is False
    assert result["promotion_eligible"] is False


# -- bundle structure, fingerprint and idempotency --------------------------


def test_bundle_has_expected_two_level_structure():
    bundle = daily_bundle()
    assert bundle["bundle_contract"] == BUNDLE_CONTRACT
    assert bundle["bundle_id"] == bundle_id_for(CHAT_ID, WINDOW_START, WINDOW_END)
    assert bundle["producer"]["reader_capability"] == READER_CAPABILITY
    assert bundle["producer"]["runtime"] == "windows_local"
    assert bundle["window"]["start"] == WINDOW_START
    assert bundle["window"]["end"] == WINDOW_END
    assert isinstance(bundle["snapshots"], list)
    assert len(bundle["snapshots"]) == 1


def test_bundle_snapshots_are_existing_capture_envelopes():
    bundle = daily_bundle([reader_item(), reader_item(message_id="msg-43")])
    for snapshot in bundle["snapshots"]:
        for field in REQUIRED_CAPTURE_FIELDS:
            assert field in snapshot


def test_bundle_id_uses_wechat_daily_namespace():
    assert bundle_id_for(CHAT_ID, WINDOW_START, WINDOW_END) == (
        "wechat-daily:conv-42:2026-10-01T00:00:00+00:00:2026-10-02T00:00:00+00:00"
    )


def test_bundle_fingerprint_is_deterministic_and_content_sensitive():
    first = daily_bundle()
    same = daily_bundle()
    assert bundle_fingerprint(first) == bundle_fingerprint(same)
    assert bundle_fingerprint(first).startswith("sha256:")

    changed = daily_bundle([reader_item(content="different")])
    assert bundle_fingerprint(changed) != bundle_fingerprint(first)


def test_bundle_idempotency_key_is_deterministic():
    bundle = daily_bundle()
    assert bundle_idempotency_key(bundle) == (
        bundle["bundle_id"] + ":" + bundle_fingerprint(bundle)
    )
    assert bundle_idempotency_key(bundle) == bundle_idempotency_key(daily_bundle())


def test_snapshot_idempotency_key_from_normalized_result():
    result = normalize_reality_capture(reader_item_to_envelope(reader_item()))
    key = snapshot_idempotency_key(result)
    assert key == str(result["candidate"]["candidate_id"]) + ":" + str(
        result["candidate"]["content_hash"]
    )


def test_snapshot_idempotency_key_accepts_target_prefix():
    result = normalize_reality_capture(reader_item_to_envelope(reader_item()))
    key = snapshot_idempotency_key(result, target="KNOWLEDGE")
    assert key.startswith("knowledge:")
    assert key.endswith(snapshot_idempotency_key(result))


# -- dry-run bundle ingestion -----------------------------------------------


def test_dry_run_bundle_verified_and_no_write():
    report = dry_run_bundle(daily_bundle())
    assert report["mode"] == MODE_DRY_RUN
    assert report["contract"] == BUNDLE_CONTRACT
    assert report["capture_contract"] == REALITY_CONTRACT_VERSION
    assert report["ok"] is True
    assert report["all_verified"] is True
    assert report["status_counts"][STATUS_VERIFIED] == 1
    assert report["write_performed"] is False
    assert report["production_write_performed"] is False
    assert report["canonical_write_performed"] is False
    assert report["second_state_store_created"] is False
    assert report["requires_human_gate"] is True
    assert report["human_gate"] == HUMAN_GATE
    assert report["snapshot_results"][0]["write_performed"] is False


def test_dry_run_bundle_reports_epistemic_breakdown():
    report = dry_run_bundle(daily_bundle())
    totals = report["epistemic_totals"]
    assert set(totals) == {
        EPISTEMIC_OBSERVED,
        EPISTEMIC_STATED,
        EPISTEMIC_INFERRED,
        EPISTEMIC_UNKNOWN,
    }
    assert totals[EPISTEMIC_INFERRED] >= 1
    assert totals[EPISTEMIC_UNKNOWN] >= 1
    per_snapshot = report["snapshot_results"][0]["epistemic"]
    assert per_snapshot["source_identity"] == EPISTEMIC_INFERRED
    assert per_snapshot["promotion_decision"] == EPISTEMIC_UNKNOWN
    assert per_snapshot["captured_at"] == EPISTEMIC_STATED


def test_dry_run_bundle_mixed_statuses():
    items = [
        reader_item(),
        reader_item(message_id="msg-43", content_available=False),
        reader_item(message_id="msg-44", content_hash="sha256:" + "0" * 64),
    ]
    report = dry_run_bundle(daily_bundle(items))
    assert report["snapshot_count"] == 3
    assert report["status_counts"][STATUS_VERIFIED] == 1
    assert report["status_counts"][STATUS_INCOMPLETE] == 1
    assert report["status_counts"][STATUS_HASH_MISMATCH] == 1
    assert report["all_verified"] is False
    assert report["any_incomplete"] is True
    assert report["any_hash_mismatch"] is True
    assert "content" in report["aggregated_missing"]


def test_dry_run_bundle_reality_is_never_a_target():
    items = [reader_item(epistemic=observed_epistemic())]
    report = dry_run_bundle(daily_bundle(items), target_asset_type="REALITY")
    preview = report["promotion_previews"][0]
    assert preview["status"] == STATUS_QUARANTINED
    assert preview["eligible"] is False
    assert preview["production_write_performed"] is False
    assert preview["second_state_store_created"] is False


def test_dry_run_bundle_promotion_preview_uses_existing_writer_and_gate():
    items = [reader_item(epistemic=observed_epistemic())]
    report = dry_run_bundle(daily_bundle(items), target_asset_type="KNOWLEDGE")
    preview = report["promotion_previews"][0]
    assert preview["phase"] == "PREPARE"
    assert preview["status"] == "PREPARED"
    assert preview["eligible"] is True
    assert preview["target_asset_type"] == "KNOWLEDGE"
    assert preview["requires_human_gate"] is True
    assert preview["human_gate"] == HUMAN_GATE
    assert preview["production_write_performed"] is False
    assert preview["second_state_store_created"] is False
    assert preview["idempotency_key"].startswith("knowledge:")


def test_prepare_promotion_reuse_contract_matches_writer():
    result = normalize_reality_capture(
        reader_item_to_envelope(reader_item(epistemic=observed_epistemic()))
    )
    plan = prepare_promotion(result, target_asset_type="KNOWLEDGE")
    assert plan["contract"] == WRITER_CONTRACT_VERSION
    assert plan["status"] == "PREPARED"
    assert plan["production_write_performed"] is False


# -- bundle validation / failure handling -----------------------------------


def test_validate_bundle_accepts_well_formed_bundle():
    validation = validate_bundle(daily_bundle())
    assert validation["ok"] is True
    assert validation["reasons"] == []
    assert validation["snapshot_count"] == 1


def test_validate_bundle_rejects_wrong_contract():
    bundle = daily_bundle()
    bundle["bundle_contract"] = "WRONG"
    validation = validate_bundle(bundle)
    assert validation["ok"] is False
    assert any("bundle_contract" in reason for reason in validation["reasons"])


def test_validate_bundle_rejects_missing_window():
    bundle = daily_bundle()
    bundle["window"] = {"timezone": "UTC"}
    validation = validate_bundle(bundle)
    assert validation["ok"] is False
    assert any("window.start" in reason for reason in validation["reasons"])


def test_dry_run_bundle_malformed_input_is_fail_closed():
    report = dry_run_bundle({"bundle_contract": "WRONG"})
    assert report["ok"] is False
    assert report["write_performed"] is False
    assert report["second_state_store_created"] is False
    assert report["snapshot_results"] == []


def test_dry_run_non_mapping_input_does_not_crash():
    report = dry_run_bundle(None)
    assert report["ok"] is False
    assert report["write_performed"] is False
    assert report["status_counts"][STATUS_VERIFIED] == 0


# -- purity / no production mutation ----------------------------------------


def test_reader_item_is_not_mutated():
    item = reader_item(epistemic={"content": EPISTEMIC_OBSERVED})
    snapshot = copy.deepcopy(item)
    reader_item_to_envelope(item)
    assert item == snapshot


def test_bundle_input_is_not_mutated_by_dry_run():
    bundle = daily_bundle()
    snapshot = copy.deepcopy(bundle)
    dry_run_bundle(bundle, target_asset_type="KNOWLEDGE")
    assert bundle == snapshot
