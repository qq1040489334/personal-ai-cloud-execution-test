"""HERMES_REALITY_DAILY_SYNC_BINDING_V0.1 regression tests.

The binding is a pure, cloud-side mapping between the existing daily WeChat
snapshot bundle and the existing Hermes result transport envelope. These tests
pin the contract properties:

* round-trip attach/extract succeeds and is idempotent;
* the attached artifact uses the existing Hermes ``artifacts`` advisory-evidence
  slot and the envelope evidence hash is stamped by the existing builder;
* extraction is fail-closed for a non-terminal / malformed / hash-mismatched
  envelope and never fabricates a bundle;
* the dry-run path reuses ``dry_run_bundle`` and preserves the
  OBSERVED / STATED / INFERRED / UNKNOWN distinctions;
* no production write, no Canonical write, no second state store.
"""

from __future__ import annotations

import copy

import pytest

from personal_ai_execution.hermes_orchestration import (
    TRANSPORT_CONTRACT_VERSION,
    build_hermes_result_envelope,
    compute_evidence_hash,
)
from personal_ai_execution.reality_capture import (
    EPISTEMIC_INFERRED,
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_UNKNOWN,
    REQUIRED_CAPTURE_FIELDS,
    STATUS_INCOMPLETE,
    STATUS_VERIFIED,
    hash_content,
)
from personal_ai_execution.reality_daily_snapshot import (
    BUNDLE_CONTRACT,
    assemble_daily_bundle,
    bundle_fingerprint,
)
from personal_ai_execution.reality_hermes_daily_sync import (
    BINDING_CONTRACT,
    BUNDLE_ARTIFACT_KIND,
    RealityDailySyncBindingError,
    attach_bundle_to_result_envelope,
    extract_bundle_from_result_envelope,
    dry_run_bundle_from_transport,
)

CAPTURED_AT = "2026-10-01T00:00:00+00:00"
WINDOW_START = "2026-10-01T00:00:00+00:00"
WINDOW_END = "2026-10-02T00:00:00+00:00"
CONTENT = "hello reality"
CHAT_ID = "conv-42"
TASK_ID = "task-cf-01a2da456c1b"
WORKER_ID = "worker-win-1"
LEASE_ID = "lease-1"


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


def attached_envelope(bundle=None, **overrides):
    kwargs = {
        "task_id": TASK_ID,
        "worker_id": WORKER_ID,
        "lease_id": LEASE_ID,
    }
    kwargs.update(overrides)
    return attach_bundle_to_result_envelope(
        daily_bundle() if bundle is None else bundle, **kwargs
    )


# -- attach: artifact shape, evidence hash, idempotency ----------------------


def test_attach_returns_existing_hermes_result_envelope():
    envelope = attached_envelope()
    assert envelope["contract_version"] == TRANSPORT_CONTRACT_VERSION
    assert envelope["task_id"] == TASK_ID
    assert envelope["worker_id"] == WORKER_ID
    assert envelope["lease_id"] == LEASE_ID
    assert envelope["task_state"] == "TASK_STATE_COMPLETED"
    assert envelope["evidence_hash"].startswith("sha256:")
    assert envelope["evidence_hash"] == compute_evidence_hash(envelope)


def test_attach_places_bundle_in_advisory_artifacts_slot():
    bundle = daily_bundle()
    envelope = attached_envelope(bundle)
    artifact = envelope["artifacts"][0]
    assert artifact["kind"] == BUNDLE_ARTIFACT_KIND
    assert artifact["bundle_contract"] == BUNDLE_CONTRACT
    assert artifact["bundle_fingerprint"] == bundle_fingerprint(bundle)
    assert artifact["bundle"] == bundle


def test_attach_is_deterministic_and_idempotent():
    bundle = daily_bundle()
    first = attached_envelope(bundle)
    second = attached_envelope(bundle)
    assert first["evidence_hash"] == second["evidence_hash"]
    assert first["artifacts"] == second["artifacts"]


def test_attach_rejects_invalid_bundle():
    bundle = daily_bundle()
    bundle["bundle_contract"] = "WRONG"
    with pytest.raises(RealityDailySyncBindingError):
        attach_bundle_to_result_envelope(
            bundle, task_id=TASK_ID, worker_id=WORKER_ID, lease_id=LEASE_ID
        )


def test_attach_rejects_missing_bundle():
    with pytest.raises(RealityDailySyncBindingError):
        attach_bundle_to_result_envelope(
            None, task_id=TASK_ID, worker_id=WORKER_ID, lease_id=LEASE_ID
        )


# -- extract: round trip, fail-closed ----------------------------------------


def test_round_trip_extract_returns_original_bundle():
    bundle = daily_bundle()
    envelope = attached_envelope(bundle)
    extracted, errors = extract_bundle_from_result_envelope(envelope)
    assert errors == []
    assert extracted == bundle


def test_extract_non_terminal_envelope_is_fail_closed():
    envelope = build_hermes_result_envelope(
        task_id=TASK_ID,
        worker_id=WORKER_ID,
        lease_id=LEASE_ID,
        task_state="TASK_STATE_WORKING",
        artifacts=[
            {
                "kind": BUNDLE_ARTIFACT_KIND,
                "bundle_contract": BUNDLE_CONTRACT,
                "bundle_fingerprint": bundle_fingerprint(daily_bundle()),
                "bundle": daily_bundle(),
            }
        ],
    )
    extracted, errors = extract_bundle_from_result_envelope(envelope)
    assert extracted is None
    assert any("terminal" in error for error in errors)


def test_extract_missing_artifact_is_fail_closed():
    envelope = build_hermes_result_envelope(
        task_id=TASK_ID, worker_id=WORKER_ID, lease_id=LEASE_ID, artifacts=[]
    )
    extracted, errors = extract_bundle_from_result_envelope(envelope)
    assert extracted is None
    assert any(BUNDLE_ARTIFACT_KIND in error for error in errors)


def test_extract_malformed_artifact_is_fail_closed():
    envelope = build_hermes_result_envelope(
        task_id=TASK_ID,
        worker_id=WORKER_ID,
        lease_id=LEASE_ID,
        artifacts=[{"kind": "some_other_artifact", "value": 1}],
    )
    extracted, errors = extract_bundle_from_result_envelope(envelope)
    assert extracted is None
    assert errors


def test_extract_tampered_envelope_hash_is_fail_closed():
    envelope = attached_envelope()
    envelope["evidence_hash"] = "sha256:" + "0" * 64
    extracted, errors = extract_bundle_from_result_envelope(envelope)
    assert extracted is None
    assert any("evidence_hash" in error for error in errors)


def test_extract_tampered_bundle_fingerprint_is_fail_closed():
    envelope = attached_envelope()
    envelope["artifacts"][0]["bundle_fingerprint"] = "sha256:" + "0" * 64
    envelope["evidence_hash"] = compute_evidence_hash(envelope)
    extracted, errors = extract_bundle_from_result_envelope(envelope)
    assert extracted is None
    assert any("fingerprint" in error for error in errors)


def test_extract_invalid_embedded_bundle_is_fail_closed():
    envelope = attached_envelope()
    envelope["artifacts"][0]["bundle"]["bundle_contract"] = "WRONG"
    envelope["evidence_hash"] = compute_evidence_hash(envelope)
    extracted, errors = extract_bundle_from_result_envelope(envelope)
    assert extracted is None
    assert any("bundle_contract" in error for error in errors)


def test_extract_non_mapping_envelope_is_fail_closed():
    extracted, errors = extract_bundle_from_result_envelope(None)
    assert extracted is None
    assert errors


# -- dry-run through transport -----------------------------------------------


def test_dry_run_from_transport_verified_and_no_write():
    report = dry_run_bundle_from_transport(attached_envelope())
    assert report["binding_contract"] == BINDING_CONTRACT
    assert report["extracted"] is True
    assert report["contract"] == BUNDLE_CONTRACT
    assert report["ok"] is True
    assert report["all_verified"] is True
    assert report["status_counts"][STATUS_VERIFIED] == 1
    assert report["write_performed"] is False
    assert report["production_write_performed"] is False
    assert report["canonical_write_performed"] is False
    assert report["second_state_store_created"] is False
    assert report["requires_human_gate"] is True


def test_dry_run_from_transport_preserves_epistemic_distinctions():
    report = dry_run_bundle_from_transport(attached_envelope())
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
    assert per_snapshot["captured_at"] == EPISTEMIC_STATED
    assert per_snapshot["promotion_decision"] == EPISTEMIC_UNKNOWN


def test_dry_run_from_transport_mixed_statuses():
    items = [
        reader_item(),
        reader_item(message_id="msg-43", content_available=False),
        reader_item(message_id="msg-44", content_hash="sha256:" + "0" * 64),
    ]
    report = dry_run_bundle_from_transport(attached_envelope(daily_bundle(items)))
    assert report["snapshot_count"] == 3
    assert report["status_counts"][STATUS_VERIFIED] == 1
    assert report["status_counts"][STATUS_INCOMPLETE] == 1
    assert report["all_verified"] is False


def test_dry_run_from_transport_reality_is_never_a_target():
    items = [reader_item(epistemic=observed_epistemic())]
    envelope = attached_envelope(daily_bundle(items))
    report = dry_run_bundle_from_transport(envelope, target_asset_type="REALITY")
    preview = report["promotion_previews"][0]
    assert preview["eligible"] is False
    assert preview["production_write_performed"] is False
    assert preview["second_state_store_created"] is False


def test_dry_run_from_transport_promotion_preview_uses_existing_gate():
    items = [reader_item(epistemic=observed_epistemic())]
    envelope = attached_envelope(daily_bundle(items))
    report = dry_run_bundle_from_transport(envelope, target_asset_type="KNOWLEDGE")
    preview = report["promotion_previews"][0]
    assert preview["eligible"] is True
    assert preview["requires_human_gate"] is True
    assert preview["production_write_performed"] is False
    assert preview["second_state_store_created"] is False


def test_dry_run_from_transport_fail_closed_for_non_terminal():
    envelope = build_hermes_result_envelope(
        task_id=TASK_ID,
        worker_id=WORKER_ID,
        lease_id=LEASE_ID,
        task_state="TASK_STATE_ERROR",
        artifacts=[],
    )
    report = dry_run_bundle_from_transport(envelope)
    assert report["binding_contract"] == BINDING_CONTRACT
    assert report["extracted"] is False
    assert report["ok"] is False
    assert report["snapshot_results"] == []
    assert report["epistemic_totals"] == {status: 0 for status in (
        EPISTEMIC_OBSERVED,
        EPISTEMIC_STATED,
        EPISTEMIC_INFERRED,
        EPISTEMIC_UNKNOWN,
    )}
    assert report["write_performed"] is False
    assert report["second_state_store_created"] is False
    assert report["errors"]


# -- purity ------------------------------------------------------------------


def test_attach_does_not_mutate_the_bundle():
    bundle = daily_bundle()
    snapshot = copy.deepcopy(bundle)
    attached_envelope(bundle)
    assert bundle == snapshot


def test_extract_and_dry_run_do_not_mutate_the_envelope():
    bundle = daily_bundle([reader_item(content=CONTENT)])
    envelope = attached_envelope(bundle)
    snapshot = copy.deepcopy(envelope)
    extract_bundle_from_result_envelope(envelope)
    dry_run_bundle_from_transport(envelope, target_asset_type="KNOWLEDGE")
    assert envelope == snapshot


def test_content_hash_fixture_matches_hash_content():
    item = reader_item(content_hash=hash_content(CONTENT))
    report = dry_run_bundle_from_transport(attached_envelope(daily_bundle([item])))
    assert report["status_counts"][STATUS_VERIFIED] == 1
