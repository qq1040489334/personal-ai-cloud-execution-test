"""Reference implementation for HERMES_REALITY_DAILY_SYNC_BINDING_V0.1.

Pure, cloud-side binding between the **existing** Reality daily WeChat snapshot
bundle (:mod:`personal_ai_execution.reality_daily_snapshot`) and the **existing**
Hermes result transport envelope
(:mod:`personal_ai_execution.hermes_orchestration`).

The binding is the smallest possible seam:

* :func:`attach_bundle_to_result_envelope` validates a daily bundle and attaches
  it to a Hermes result envelope as *advisory artifact evidence*;
* :func:`extract_bundle_from_result_envelope` fail-closed extracts and
  re-validates that bundle;
* :func:`dry_run_bundle_from_transport` runs the extracted bundle through the
  existing read-only L2 dry-run.

It is deliberately inert:

* no WeChat, Hermes runtime, network, relay or local filesystem access;
* no production write, no Reality Canonical write, no second state store;
* no credential, permission, binding or schema change, no deploy.

Every derived epistemic field keeps its existing tag; the binding never upgrades
an ``INFERRED``/``STATED``/``UNKNOWN`` value to ``OBSERVED``.
"""

from __future__ import annotations

from typing import Any, Mapping

from personal_ai_execution.hermes_orchestration import (
    TERMINAL_TASK_STATES,
    TRANSPORT_CONTRACT_VERSION,
    build_hermes_result_envelope,
    compute_evidence_hash,
    validate_result_envelope,
)
from personal_ai_execution.reality_capture import (
    EPISTEMIC_INFERRED,
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_UNKNOWN,
    REALITY_CONTRACT_VERSION,
    STATUS_HASH_MISMATCH,
    STATUS_INCOMPLETE,
    STATUS_VERIFIED,
)
from personal_ai_execution.reality_daily_snapshot import (
    BUNDLE_CONTRACT,
    MODE_DRY_RUN,
    bundle_fingerprint,
    dry_run_bundle,
    validate_bundle,
)
from personal_ai_execution.reality_canonical_writer import HUMAN_GATE

BINDING_CONTRACT = "HERMES_REALITY_DAILY_SYNC_BINDING_V0.1"
BUNDLE_ARTIFACT_KIND = "reality_daily_bundle"
DEFAULT_EXECUTOR_IDENTITY = "hermes-native-hand"

EPISTEMIC_STATUSES = (
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_INFERRED,
    EPISTEMIC_UNKNOWN,
)


class RealityDailySyncBindingError(ValueError):
    """Raised when a bundle cannot be attached to a result envelope."""


def _bundle_artifact(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Wrap a validated bundle as a Hermes ``artifacts`` entry."""
    return {
        "kind": BUNDLE_ARTIFACT_KIND,
        "bundle_contract": bundle.get("bundle_contract"),
        "bundle_fingerprint": bundle_fingerprint(bundle),
        "bundle": bundle,
    }


def attach_bundle_to_result_envelope(
    bundle: Mapping[str, Any] | None,
    task_id: str,
    worker_id: str,
    lease_id: str,
    *,
    executor_identity: str = DEFAULT_EXECUTOR_IDENTITY,
    task_state: str = "TASK_STATE_COMPLETED",
    status: str = "success",
    tests: str = "",
    summary: str = "",
    expected_files: list[str] | None = None,
    changed_files: list[str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Attach a validated daily bundle to the existing Hermes result envelope.

    The bundle is validated first with the existing
    :func:`reality_daily_snapshot.validate_bundle`; an invalid bundle raises
    :class:`RealityDailySyncBindingError` (fail-closed, no partial envelope).

    The bundle is carried in ``artifacts`` as
    ``{"kind": "reality_daily_bundle", "bundle_contract", "bundle_fingerprint",
    "bundle"}`` and the envelope evidence hash is stamped by the existing
    :func:`hermes_orchestration.build_hermes_result_envelope`.
    """
    validation = validate_bundle(bundle)
    if not validation["ok"]:
        raise RealityDailySyncBindingError(
            "daily bundle failed validation: " + "; ".join(validation["reasons"])
        )

    return build_hermes_result_envelope(
        task_id=task_id,
        worker_id=worker_id,
        lease_id=lease_id,
        task_state=task_state,
        executor_identity=executor_identity,
        status=status,
        tests=tests,
        artifacts=[_bundle_artifact(bundle)],
        expected_files=expected_files,
        changed_files=changed_files,
        summary=summary,
        **extra,
    )


def _find_bundle_artifact(envelope: Mapping[str, Any]) -> Mapping[str, Any] | None:
    artifacts = envelope.get("artifacts")
    if not isinstance(artifacts, list):
        return None
    for candidate in artifacts:
        if (
            isinstance(candidate, Mapping)
            and candidate.get("kind") == BUNDLE_ARTIFACT_KIND
        ):
            return candidate
    return None


def extract_bundle_from_result_envelope(
    envelope: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Fail-closed extraction of a daily bundle from a Hermes result envelope.

    Returns ``(bundle, errors)``. The bundle is ``None`` whenever anything is
    wrong, and every reason is recorded in ``errors`` -- no value is fabricated
    and no partial bundle is returned.
    """
    if not isinstance(envelope, Mapping):
        return None, ["result envelope is not a mapping"]

    errors = list(validate_result_envelope(envelope))
    if errors:
        return None, errors

    task_state = str(envelope.get("task_state") or "").upper()
    if task_state not in TERMINAL_TASK_STATES:
        return None, [f"task_state is not terminal: {task_state}"]

    declared_hash = str(envelope.get("evidence_hash") or "")
    expected_hash = compute_evidence_hash(envelope)
    if declared_hash != expected_hash:
        return None, [
            "envelope evidence_hash does not match the stable result fields"
        ]

    artifact = _find_bundle_artifact(envelope)
    if artifact is None:
        return None, [f"no {BUNDLE_ARTIFACT_KIND} artifact found in envelope"]

    bundle = artifact.get("bundle")
    validation = validate_bundle(bundle)
    if not validation["ok"]:
        return None, list(validation["reasons"])

    recomputed_fingerprint = bundle_fingerprint(bundle)
    declared_fingerprint = artifact.get("bundle_fingerprint")
    if declared_fingerprint != recomputed_fingerprint:
        return None, [
            "bundle fingerprint mismatch: declared "
            + str(declared_fingerprint)
            + " != recomputed "
            + recomputed_fingerprint
        ]

    declared_contract = artifact.get("bundle_contract")
    if declared_contract != bundle.get("bundle_contract"):
        return None, [
            "artifact bundle_contract does not match the embedded bundle"
        ]

    return bundle, []


def _fail_closed_report(errors: list[str]) -> dict[str, Any]:
    """Build a dry-run report shape for a bundle that could not be extracted."""
    return {
        "contract": BUNDLE_CONTRACT,
        "binding_contract": BINDING_CONTRACT,
        "capture_contract": REALITY_CONTRACT_VERSION,
        "mode": MODE_DRY_RUN,
        "bundle_id": None,
        "bundle_fingerprint": None,
        "bundle_idempotency_key": None,
        "validation": {
            "ok": False,
            "reasons": list(errors),
            "bundle_id": None,
            "snapshot_count": 0,
        },
        "snapshot_results": [],
        "promotion_previews": [],
        "status_counts": {
            STATUS_VERIFIED: 0,
            STATUS_INCOMPLETE: 0,
            STATUS_HASH_MISMATCH: 0,
        },
        "aggregated_missing": [],
        "epistemic_totals": {status: 0 for status in EPISTEMIC_STATUSES},
        "snapshot_count": 0,
        "all_verified": False,
        "any_incomplete": False,
        "any_hash_mismatch": False,
        "ok": False,
        "extracted": False,
        "errors": list(errors),
        "read_only": True,
        "write_performed": False,
        "production_write_performed": False,
        "canonical_write_performed": False,
        "second_state_store_created": False,
        "requires_human_gate": True,
        "human_gate": HUMAN_GATE,
    }


def dry_run_bundle_from_transport(
    envelope: Mapping[str, Any] | None,
    *,
    target_asset_type: Any = None,
) -> dict[str, Any]:
    """Extract a bundle from a transport envelope and dry-run it, read-only.

    On success the existing :func:`reality_daily_snapshot.dry_run_bundle` report
    is returned, annotated with the binding contract and extraction status. On a
    fail-closed extraction the returned report shape is identical in the
    no-write fields and carries the extraction ``errors``.

    Nothing is persisted: ``write_performed``, ``production_write_performed``,
    ``canonical_write_performed`` and ``second_state_store_created`` are always
    ``False``.
    """
    bundle, errors = extract_bundle_from_result_envelope(envelope)
    if bundle is None:
        return _fail_closed_report(errors)

    report = dry_run_bundle(bundle, target_asset_type=target_asset_type)
    report["binding_contract"] = BINDING_CONTRACT
    report["extracted"] = True
    report["errors"] = []
    report["target_asset_type"] = target_asset_type
    return report
