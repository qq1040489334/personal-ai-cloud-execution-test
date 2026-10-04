"""REALITY_CANDIDATE_HANDOFF_V0.1 -- Snapshot -> Candidate artifact -> Review.

This module defines the smallest possible, read-only *handoff contract* between a
Reality Snapshot and the Candidate Review readable input. It owns exactly one
lifecycle concern: the **Candidate artifact** that is derived from an already
normalized Reality capture.

It deliberately does *not*:

* read WeChat, a reader database, Hermes or any relay (the Snapshot is supplied
  by the caller);
* modify the WeChatRead/Hermes collection chain, the Reality Canonical writer or
  any Canonical target (KNOWLEDGE / SKILL / DECISION);
* perform a production write, create a second state store, deploy, or change a
  secret / permission / binding / schema.

It reuses the existing contracts directly instead of re-declaring them:

* :mod:`personal_ai_execution.reality_capture` --
  ``normalize_reality_capture`` produces the candidate; the artifact is always
  re-normalized from the supplied snapshot so a missing field can never be
  silently upgraded to ``VERIFIED``;
* :mod:`personal_ai_execution.provenance_contract` --
  ``evaluate_provenance`` re-evaluates the artifact provenance, fail-closed;
* :mod:`personal_ai_execution.result_normalization` --
  the ``PASS`` / ``FAIL`` / ``BLOCKED`` review vocabulary.

The handoff chain is::

    Snapshot envelope
        -> normalize_reality_capture (existing)
        -> Candidate artifact (this module, deterministic location + schema)
        -> Review input (this module, fail-closed verdict, never auto-approved)
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Mapping, MutableMapping

from personal_ai_execution.provenance_contract import (
    PROVENANCE_CONTRACT_VERSION,
    evaluate_provenance,
)
from personal_ai_execution.reality_capture import (
    EPISTEMIC_INFERRED,
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_UNKNOWN,
    REALITY_CANDIDATE_FIELDS,
    REALITY_CONTRACT_VERSION,
    REALITY_STATUSES,
    STATUS_HASH_MISMATCH,
    STATUS_INCOMPLETE,
    STATUS_VERIFIED,
    normalize_reality_capture,
)
from personal_ai_execution.result_normalization import (
    BLOCKED,
    FAIL,
    PASS,
)

#: Version tag of this handoff contract.
HANDOFF_CONTRACT = "REALITY_CANDIDATE_HANDOFF_V0.1"
#: Version tag of the Candidate artifact schema.
ARTIFACT_SCHEMA = "REALITY_CANDIDATE_ARTIFACT_SCHEMA_V0.1"
#: Version tag of the Candidate Review input format.
REVIEW_INPUT_CONTRACT = "REALITY_CANDIDATE_REVIEW_INPUT_V0.1"

#: The artifact carries only Reality candidates; REALITY is source/provenance,
#: never a writable canonical target.
ARTIFACT_TYPE = "REALITY_CANDIDATE"
ASSET_TYPE = "REALITY"

#: Logical (not filesystem) artifact root. The handoff never resolves a real
#: path, writes a file or touches a store unless the caller supplies one.
ARTIFACT_ROOT = "reality-candidates"
ARTIFACT_SUFFIX = ".candidate.json"

#: How the snapshot reached :func:`build_candidate_artifact`.
SOURCE_KIND_ENVELOPE = "SNAPSHOT_ENVELOPE"
SOURCE_KIND_NORMALIZED = "NORMALIZED_CAPTURE"

#: Every top-level field the Candidate artifact schema can carry, in order.
CANDIDATE_ARTIFACT_FIELDS = (
    "artifact_contract",
    "artifact_schema",
    "artifact_type",
    "artifact_id",
    "artifact_location",
    "candidate_id",
    "asset_type",
    "status",
    "complete",
    "verified",
    "promotion_eligible",
    "missing",
    "invalid",
    "hash_checked",
    "hash_match",
    "content_hash",
    "epistemic",
    "epistemic_summary",
    "candidate",
    "provenance",
    "artifact_provenance",
    "provenance_completeness",
    "handoff",
    "read_only",
    "write_performed",
    "production_write_performed",
    "canonical_write_performed",
)

#: Fields that must be present for an artifact to be structurally readable.
REQUIRED_ARTIFACT_FIELDS = (
    "artifact_contract",
    "artifact_schema",
    "artifact_type",
    "artifact_id",
    "artifact_location",
    "candidate_id",
    "asset_type",
    "status",
    "verified",
    "candidate",
    "provenance",
    "artifact_provenance",
    "provenance_completeness",
    "handoff",
)

#: Explicit, flattened **artifact provenance** fields handed to Review. These
#: name the origin of the artifact itself (the handoff/schema/capture contracts)
#: in addition to the underlying candidate source provenance. Values may be
#: ``None`` for an incomplete capture; a missing field is never fabricated.
ARTIFACT_PROVENANCE_FIELDS = (
    "handoff_contract",
    "capture_contract",
    "provenance_contract",
    "artifact_schema",
    "artifact_id",
    "artifact_location",
    "snapshot_id",
    "asset_type",
    "candidate_id",
    "source_identity",
    "source_location",
    "source_version",
    "content_version",
    "source_content_hash",
    "content_hash",
    "verification_evidence",
    "captured_at",
    "epistemic",
    "status",
    "complete",
    "verified",
    "promotion_eligible",
)

#: Review-input fields, in order.
CANDIDATE_REVIEW_INPUT_FIELDS = (
    "review_contract",
    "handoff_contract",
    "artifact_schema",
    "artifact_id",
    "artifact_location",
    "candidate_id",
    "asset_type",
    "source_identity",
    "status",
    "verified",
    "promotion_eligible",
    "missing",
    "hash_match",
    "content_hash",
    "epistemic",
    "artifact_provenance",
    "provenance",
    "review",
    "readable",
    "read_only",
)

EPISTEMIC_STATUSES = (
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_INFERRED,
    EPISTEMIC_UNKNOWN,
)

_SAFE_SEGMENT_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _safe_segment(value: Any) -> str:
    text = _SAFE_SEGMENT_RE.sub("_", _text(value))
    return text or "unknown"


def candidate_artifact_location(candidate_id: Any) -> str:
    """Return the deterministic, logical artifact location for a candidate.

    The location is a contract-level URI, not a filesystem path::

        reality-candidates/<safe candidate_id>.candidate.json
    """
    return ARTIFACT_ROOT + "/" + _safe_segment(candidate_id) + ARTIFACT_SUFFIX


def candidate_artifact_id(
    candidate_id: Any,
    content_hash: Any,
    source_identity: Any,
) -> str:
    """Deterministic artifact id over the candidate identity + content hash."""
    core = {
        "candidate_id": candidate_id,
        "content_hash": content_hash,
        "source_identity": source_identity,
    }
    return "reality-candidate:" + _sha256(core)


def _is_normalized_result(source: Mapping[str, Any]) -> bool:
    return (
        isinstance(source.get("candidate"), Mapping)
        and str(source.get("status")) in REALITY_STATUSES
    )


def _as_envelope(source: Mapping[str, Any]) -> dict[str, Any]:
    """Coerce a normalized capture result back into a capture envelope.

    Passing the normalized candidate back through ``normalize_reality_capture``
    guarantees the artifact status/verified flags are re-derived from scratch and
    are never trusted from a caller-supplied object.
    """
    if _is_normalized_result(source):
        candidate = source["candidate"]
        envelope = {
            field: candidate.get(field) for field in REALITY_CANDIDATE_FIELDS
        }
        envelope["epistemic"] = source.get("epistemic")
        envelope["provenance"] = candidate.get("provenance")
        return envelope
    return dict(source)


def build_artifact_provenance(
    normalized: Mapping[str, Any],
    *,
    artifact_id: str,
    artifact_location: str,
    snapshot_id: Any,
) -> dict[str, Any]:
    """Build the explicit artifact provenance block (values never fabricated)."""
    candidate = normalized.get("candidate")
    candidate = candidate if isinstance(candidate, Mapping) else {}
    return {
        "handoff_contract": HANDOFF_CONTRACT,
        "capture_contract": REALITY_CONTRACT_VERSION,
        "provenance_contract": PROVENANCE_CONTRACT_VERSION,
        "artifact_schema": ARTIFACT_SCHEMA,
        "artifact_id": artifact_id,
        "artifact_location": artifact_location,
        "snapshot_id": snapshot_id,
        "asset_type": ASSET_TYPE,
        "candidate_id": candidate.get("candidate_id"),
        "source_identity": candidate.get("source_identity"),
        "source_location": candidate.get("source_location"),
        "source_version": candidate.get("source_version"),
        "content_version": candidate.get("content_version"),
        "source_content_hash": candidate.get("source_content_hash"),
        "content_hash": candidate.get("content_hash"),
        "verification_evidence": candidate.get("verification_evidence"),
        "captured_at": candidate.get("captured_at"),
        "epistemic": dict(normalized.get("epistemic") or {}),
        "status": normalized.get("status"),
        "complete": normalized.get("complete"),
        "verified": normalized.get("verified"),
        "promotion_eligible": normalized.get("promotion_eligible"),
    }


def build_candidate_artifact(
    snapshot: Mapping[str, Any] | None,
    *,
    snapshot_id: Any = None,
) -> dict[str, Any]:
    """Build a Candidate artifact from a Reality Snapshot, fail-closed.

    ``snapshot`` may be a raw capture envelope or an already normalized capture
    result; either way it is re-normalized through the existing
    :func:`normalize_reality_capture`, so an ``INCOMPLETE`` / ``HASH_MISMATCH``
    capture can never produce an artifact that claims ``VERIFIED``.

    The returned artifact is a plain, serializable mapping. No store is touched
    and the input mapping is never mutated.
    """
    source = snapshot if isinstance(snapshot, Mapping) else {}
    source_kind = (
        SOURCE_KIND_NORMALIZED if _is_normalized_result(source) else SOURCE_KIND_ENVELOPE
    )
    normalized = normalize_reality_capture(_as_envelope(source))

    candidate = normalized["candidate"]
    candidate_id = candidate.get("candidate_id")
    content_hash = candidate.get("content_hash")
    source_identity = candidate.get("source_identity")

    artifact_id = candidate_artifact_id(candidate_id, content_hash, source_identity)
    location = candidate_artifact_location(candidate_id)
    resolved_snapshot_id = snapshot_id if _meaningful(snapshot_id) else candidate_id
    provenance = candidate.get("provenance")
    if not isinstance(provenance, Mapping):
        provenance = None

    artifact: dict[str, Any] = {
        "artifact_contract": HANDOFF_CONTRACT,
        "artifact_schema": ARTIFACT_SCHEMA,
        "artifact_type": ARTIFACT_TYPE,
        "artifact_id": artifact_id,
        "artifact_location": location,
        "candidate_id": candidate_id,
        "asset_type": ASSET_TYPE,
        "status": normalized["status"],
        "complete": normalized["complete"],
        "verified": normalized["verified"],
        "promotion_eligible": normalized["promotion_eligible"],
        "missing": list(normalized["missing"]),
        "invalid": list(normalized["invalid"]),
        "hash_checked": normalized["hash_checked"],
        "hash_match": normalized["hash_match"],
        "content_hash": content_hash,
        "epistemic": dict(normalized["epistemic"]),
        "epistemic_summary": dict(normalized["epistemic_summary"]),
        "candidate": candidate,
        "provenance": provenance,
        "artifact_provenance": build_artifact_provenance(
            normalized,
            artifact_id=artifact_id,
            artifact_location=location,
            snapshot_id=resolved_snapshot_id,
        ),
        "provenance_completeness": normalized["provenance_completeness"],
        "handoff": {
            "contract": HANDOFF_CONTRACT,
            "source_kind": source_kind,
            "snapshot_id": resolved_snapshot_id,
            "capture_contract": REALITY_CONTRACT_VERSION,
            "provenance_contract": PROVENANCE_CONTRACT_VERSION,
            "artifact_schema": ARTIFACT_SCHEMA,
        },
        "read_only": True,
        "write_performed": False,
        "production_write_performed": False,
        "canonical_write_performed": False,
    }
    return artifact


def validate_candidate_artifact(
    artifact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Structurally validate a Candidate artifact, fail-closed.

    Returns ``{"ok", "reasons", "readable", ...}``. A malformed artifact, a
    forged ``verified=true`` on a non-``VERIFIED`` capture, or an artifact whose
    provenance completeness disagrees with the re-evaluated provenance is
    rejected; ``readable`` is then ``False``.
    """
    audit: dict[str, Any] = {
        "contract": HANDOFF_CONTRACT,
        "ok": False,
        "readable": False,
        "reasons": [],
        "artifact_id": None,
        "artifact_location": None,
        "candidate_id": None,
        "status": None,
        "verified": None,
        "promotion_eligible": None,
    }
    if not isinstance(artifact, Mapping):
        audit["reasons"].append("candidate artifact is not a mapping")
        return audit

    audit["artifact_id"] = artifact.get("artifact_id")
    audit["artifact_location"] = artifact.get("artifact_location")
    audit["candidate_id"] = artifact.get("candidate_id")
    audit["status"] = artifact.get("status")
    audit["verified"] = artifact.get("verified")
    audit["promotion_eligible"] = artifact.get("promotion_eligible")

    for field in REQUIRED_ARTIFACT_FIELDS:
        if field not in artifact:
            audit["reasons"].append("artifact missing required field: " + field)

    if artifact.get("artifact_contract") != HANDOFF_CONTRACT:
        audit["reasons"].append("artifact_contract is not " + HANDOFF_CONTRACT)
    if artifact.get("artifact_schema") != ARTIFACT_SCHEMA:
        audit["reasons"].append("artifact_schema is not " + ARTIFACT_SCHEMA)
    if artifact.get("artifact_type") != ARTIFACT_TYPE:
        audit["reasons"].append("artifact_type is not " + ARTIFACT_TYPE)
    if artifact.get("asset_type") != ASSET_TYPE:
        audit["reasons"].append("asset_type is not " + ASSET_TYPE)

    candidate_id = artifact.get("candidate_id")
    if not _meaningful(candidate_id):
        audit["reasons"].append("candidate_id is missing")
    else:
        expected_location = candidate_artifact_location(candidate_id)
        if artifact.get("artifact_location") != expected_location:
            audit["reasons"].append(
                "artifact_location is not the deterministic location for the "
                "candidate"
            )

    status = artifact.get("status")
    if status not in REALITY_STATUSES:
        audit["reasons"].append("status is not a REALITY capture status")

    artifact_provenance = artifact.get("artifact_provenance")
    if not isinstance(artifact_provenance, Mapping):
        audit["reasons"].append("artifact_provenance is not a mapping")
    else:
        for field in ARTIFACT_PROVENANCE_FIELDS:
            if field not in artifact_provenance:
                audit["reasons"].append(
                    "artifact_provenance missing field: " + field
                )
        if artifact_provenance.get("status") != status:
            audit["reasons"].append(
                "artifact_provenance.status disagrees with artifact status"
            )
        if bool(artifact_provenance.get("verified")) != bool(artifact.get("verified")):
            audit["reasons"].append(
                "artifact_provenance.verified disagrees with artifact verified"
            )

    verified = bool(artifact.get("verified"))
    if status != STATUS_VERIFIED and verified:
        audit["reasons"].append(
            "fail-closed violation: a non-VERIFIED capture claims verified=true"
        )
    if verified:
        if not artifact.get("complete"):
            audit["reasons"].append(
                "fail-closed violation: verified artifact is not complete"
            )
        if artifact.get("missing"):
            audit["reasons"].append(
                "fail-closed violation: verified artifact has missing fields: "
                + ", ".join(str(field) for field in artifact.get("missing") or [])
            )
        if not _meaningful(artifact.get("content_hash")):
            audit["reasons"].append(
                "fail-closed violation: verified artifact has no content_hash"
            )

    candidate = artifact.get("candidate")
    provenance_block = None
    if isinstance(candidate, Mapping):
        provenance_block = candidate.get("provenance")
    recomputed = evaluate_provenance(
        provenance_block if isinstance(provenance_block, Mapping) else {}
    )
    stored = artifact.get("provenance_completeness")
    if isinstance(stored, Mapping) and stored.get("status") != recomputed["status"]:
        audit["reasons"].append(
            "provenance completeness disagrees with re-evaluated provenance"
        )

    audit["ok"] = not audit["reasons"]
    audit["readable"] = audit["ok"]
    return audit


def stage_candidate_artifact(
    artifact: Mapping[str, Any] | None,
    store: MutableMapping[str, Any] | None,
) -> dict[str, Any]:
    """Stage a validated artifact into a caller-supplied, in-memory store.

    The store is caller-owned and non-production; the handoff itself never
    creates a store. An invalid artifact is never staged and
    ``production_write_performed`` / ``canonical_write_performed`` stay ``False``.
    """
    result = {
        "stored": False,
        "location": None,
        "reasons": [],
        "read_only": True,
        "write_performed": False,
        "production_write_performed": False,
        "canonical_write_performed": False,
        "second_state_store_created": False,
    }
    validation = validate_candidate_artifact(artifact)
    if not validation["ok"] or not isinstance(artifact, Mapping):
        result["reasons"] = list(validation["reasons"])
        return result
    if not isinstance(store, MutableMapping):
        result["reasons"] = ["no mutable artifact store supplied by the caller"]
        return result

    location = str(artifact["artifact_location"])
    store[location] = copy.deepcopy(dict(artifact))
    result["stored"] = True
    result["location"] = location
    return result


def read_candidate_artifact(
    store: Mapping[str, Any] | None,
    location: Any,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Fail-closed read of a Candidate artifact from an artifact store.

    Returns ``(artifact, errors)``. The artifact is ``None`` whenever the
    location is missing, absent or holds an invalid artifact; every reason is
    reported and no partial value is returned.
    """
    if not isinstance(store, Mapping):
        return None, ["artifact store is not a mapping"]
    text = _text(location)
    if not text:
        return None, ["artifact location is empty"]
    candidate = store.get(text)
    if candidate is None:
        return None, ["no candidate artifact at location " + text]
    validation = validate_candidate_artifact(candidate)
    if not validation["ok"]:
        return None, list(validation["reasons"])
    return dict(candidate), []


def candidate_artifact_to_review_input(
    artifact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Map a Candidate artifact to the Candidate Review readable input.

    The verdict is fail-closed and **advisory**: only a complete, ``VERIFIED``
    candidate yields ``PASS``; a hash mismatch yields ``FAIL``; anything else
    (including a missing field / ``UNKNOWN`` epistemic value) yields ``BLOCKED``.
    The review is never auto-approved and never calls ``mark_reviewed``.
    """
    validation = validate_candidate_artifact(artifact)
    artifact = artifact if isinstance(artifact, Mapping) else {}

    candidate_id = artifact.get("candidate_id")
    artifact_id = artifact.get("artifact_id")
    location = artifact.get("artifact_location")
    status = artifact.get("status")
    verified = bool(artifact.get("verified"))
    promotion_eligible = bool(artifact.get("promotion_eligible"))
    missing = list(artifact.get("missing") or [])
    hash_match = artifact.get("hash_match")
    content_hash = artifact.get("content_hash")
    epistemic = dict(artifact.get("epistemic") or {})
    artifact_provenance = artifact.get("artifact_provenance")
    artifact_provenance = (
        dict(artifact_provenance)
        if isinstance(artifact_provenance, Mapping)
        else {}
    )
    provenance = artifact.get("provenance")
    provenance = dict(provenance) if isinstance(provenance, Mapping) else None

    reasons: list[dict[str, str]] = []
    refs: list[dict[str, Any]] = []

    def add_reason(code: str, message: str) -> None:
        reasons.append({"code": code, "message": message})

    def add_ref(source: str, field: str, value: Any) -> None:
        refs.append({"source": source, "field": field, "value": value})

    if artifact_id is not None:
        add_ref("artifact", "artifact_id", artifact_id)
    if location is not None:
        add_ref("artifact", "artifact_location", location)
    if candidate_id is not None:
        add_ref("artifact", "candidate_id", candidate_id)
    if status is not None:
        add_ref("artifact", "status", status)
    if artifact_provenance.get("source_identity") is not None:
        add_ref("artifact_provenance", "source_identity", artifact_provenance.get("source_identity"))
    if content_hash is not None:
        add_ref("artifact", "content_hash", content_hash)

    readable = bool(validation["ok"])
    if not readable:
        verdict = BLOCKED
        add_reason(
            "ARTIFACT_NOT_READABLE",
            "candidate artifact is not readable: "
            + ("; ".join(validation["reasons"]) or "unknown reason"),
        )
    elif status == STATUS_HASH_MISMATCH or hash_match is False:
        verdict = FAIL
        add_reason(
            "CANDIDATE_HASH_MISMATCH",
            "candidate content hash does not agree with the recomputed hash",
        )
    elif status == STATUS_VERIFIED and verified and not missing:
        verdict = PASS
        add_reason(
            "CANDIDATE_VERIFIED",
            "candidate capture is complete and VERIFIED; advisory only",
        )
        if not promotion_eligible:
            add_reason(
                "NOT_PROMOTION_ELIGIBLE",
                "candidate is not promotion_eligible; a human must confirm the "
                "inferred fields before any Canonical promotion",
            )
    else:
        verdict = BLOCKED
        add_reason(
            "CANDIDATE_INCOMPLETE",
            "candidate capture is not VERIFIED"
            + (": missing " + ", ".join(str(field) for field in missing) if missing else ""),
        )

    review = {
        "contract": REVIEW_INPUT_CONTRACT,
        "verdict": verdict,
        "advisory": True,
        "requires_human_review": True,
        "auto_reviewed": False,
        "auto_mark_reviewed_called": False,
        "reasons": reasons,
        "evidence_refs": refs,
    }

    return {
        "review_contract": REVIEW_INPUT_CONTRACT,
        "handoff_contract": HANDOFF_CONTRACT,
        "artifact_schema": artifact.get("artifact_schema"),
        "artifact_id": artifact_id,
        "artifact_location": location,
        "candidate_id": candidate_id,
        "asset_type": artifact.get("asset_type"),
        "source_identity": artifact_provenance.get("source_identity"),
        "status": status,
        "verified": verified,
        "promotion_eligible": promotion_eligible,
        "missing": missing,
        "hash_match": hash_match,
        "content_hash": content_hash,
        "epistemic": epistemic,
        "artifact_provenance": artifact_provenance,
        "provenance": provenance,
        "review": review,
        "readable": readable,
        "read_only": True,
    }


def validate_review_input(review_input: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate the Candidate Review input format, fail-closed."""
    reasons: list[str] = []
    if not isinstance(review_input, Mapping):
        return {
            "ok": False,
            "reasons": ["review input is not a mapping"],
            "verdict": None,
            "readable": False,
        }
    for field in CANDIDATE_REVIEW_INPUT_FIELDS:
        if field not in review_input:
            reasons.append("review input missing field: " + field)
    if review_input.get("review_contract") != REVIEW_INPUT_CONTRACT:
        reasons.append("review_contract is not " + REVIEW_INPUT_CONTRACT)
    review = review_input.get("review")
    if not isinstance(review, Mapping):
        reasons.append("review block is not a mapping")
    else:
        if review.get("verdict") not in (PASS, FAIL, BLOCKED):
            reasons.append("review verdict is not PASS/FAIL/BLOCKED")
        if review.get("auto_reviewed") is not False:
            reasons.append("review must never be auto-reviewed")
        if review.get("requires_human_review") is not True:
            reasons.append("review must require human review")
    return {
        "ok": not reasons,
        "reasons": reasons,
        "verdict": (review or {}).get("verdict") if isinstance(review, Mapping) else None,
        "readable": bool(review_input.get("readable")),
    }


def run_candidate_handoff(
    snapshot: Mapping[str, Any] | None,
    *,
    snapshot_id: Any = None,
    store: MutableMapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Read-only end-to-end verification of the handoff chain.

    Snapshot -> Candidate artifact -> store -> read-back -> Review input. The
    ``store`` (when supplied) is caller-owned, in-memory and non-production; the
    report always states that no production/Canonical write and no second state
    store occurred.
    """
    artifact = build_candidate_artifact(snapshot, snapshot_id=snapshot_id)
    validation = validate_candidate_artifact(artifact)

    active_store = store if isinstance(store, MutableMapping) else {}
    staged = stage_candidate_artifact(artifact, active_store)
    retrieved, read_errors = read_candidate_artifact(
        active_store, artifact["artifact_location"]
    )
    review_input = candidate_artifact_to_review_input(artifact)
    review_validation = validate_review_input(review_input)

    review = review_input["review"]
    provenance = artifact.get("artifact_provenance") or {}
    provenance_fields_present = all(
        field in provenance for field in ARTIFACT_PROVENANCE_FIELDS
    )
    fail_closed = (
        artifact["status"] == STATUS_VERIFIED
        or (artifact["verified"] is False and review["verdict"] != PASS)
    )

    checks = [
        {
            "name": "snapshot_normalized_to_candidate",
            "passed": bool(artifact["candidate_id"])
            and artifact["status"] in REALITY_STATUSES,
        },
        {
            "name": "candidate_artifact_valid",
            "passed": validation["ok"],
        },
        {
            "name": "candidate_artifact_staged_and_readable",
            "passed": staged["stored"]
            and retrieved is not None
            and retrieved.get("artifact_id") == artifact["artifact_id"],
        },
        {
            "name": "review_input_readable_and_linked",
            "passed": review_validation["ok"]
            and review_input["readable"]
            and review_input["artifact_id"] == artifact["artifact_id"]
            and review_input["artifact_location"] == artifact["artifact_location"],
        },
        {
            "name": "artifact_provenance_fields_explicit",
            "passed": provenance_fields_present,
        },
        {
            "name": "unknown_never_upgraded_to_verified",
            "passed": fail_closed,
        },
        {
            "name": "no_production_or_canonical_write",
            "passed": artifact["production_write_performed"] is False
            and artifact["canonical_write_performed"] is False
            and staged["production_write_performed"] is False
            and staged["second_state_store_created"] is False,
        },
        {
            "name": "review_is_advisory_only",
            "passed": review["auto_reviewed"] is False
            and review["auto_mark_reviewed_called"] is False
            and review["requires_human_review"] is True,
        },
    ]

    passed = all(check["passed"] for check in checks)
    return {
        "goal": HANDOFF_CONTRACT,
        "contract": HANDOFF_CONTRACT,
        "artifact_schema": ARTIFACT_SCHEMA,
        "review_contract": REVIEW_INPUT_CONTRACT,
        "capture_contract": REALITY_CONTRACT_VERSION,
        "provenance_contract": PROVENANCE_CONTRACT_VERSION,
        "status": PASS if passed else FAIL,
        "candidate_id": artifact["candidate_id"],
        "artifact_id": artifact["artifact_id"],
        "artifact_location": artifact["artifact_location"],
        "capture_status": artifact["status"],
        "verified": artifact["verified"],
        "promotion_eligible": artifact["promotion_eligible"],
        "review_verdict": review["verdict"],
        "artifact": artifact,
        "review_input": review_input,
        "validation": validation,
        "staged": staged,
        "read_errors": list(read_errors),
        "checks": checks,
        "read_only": True,
        "write_performed": False,
        "production_write_performed": False,
        "canonical_write_performed": False,
        "second_state_store_created": False,
        "requires_human_gate": True,
    }


def handoff_matrix() -> tuple[dict[str, Any], ...]:
    """Documented handoff decision matrix (a defensive copy)."""
    rows = (
        (
            "complete snapshot, hash agrees",
            STATUS_VERIFIED,
            PASS,
            "artifact VERIFIED; review recommends PASS (advisory)",
        ),
        (
            "required field missing / only UNKNOWN epistemic",
            STATUS_INCOMPLETE,
            BLOCKED,
            "artifact INCOMPLETE; missing field never upgraded to VERIFIED",
        ),
        (
            "declared hash disagrees with recomputed hash",
            STATUS_HASH_MISMATCH,
            FAIL,
            "artifact HASH_MISMATCH; review recommends FAIL",
        ),
        (
            "malformed or forged artifact",
            None,
            BLOCKED,
            "artifact not readable; review BLOCKED",
        ),
    )
    return tuple(
        {
            "scenario": scenario,
            "capture_status": capture_status,
            "review_verdict": review_verdict,
            "outcome": outcome,
        }
        for scenario, capture_status, review_verdict, outcome in rows
    )
