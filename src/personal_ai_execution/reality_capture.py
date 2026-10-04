"""Reference implementation for PERSONAL_AI_REALITY_CAPTURE_NORMALIZATION_V0.1.

This is the *reference* form of the read-only REALITY capture/normalization
boundary described in ``REALITY_CAPTURE_NORMALIZATION_CONTRACT_V0.1.md``. It maps
a caller-supplied (untrusted) WeChat snapshot envelope into a normalized REALITY
*candidate* representation. It performs no write, holds no credential and makes
no assumption about how/where WeChat stores or encrypts data: the caller
supplies the content payload and the capture evidence, and the cloud only
normalizes, tags epistemic status and recomputes a content hash.

It reuses ASSET_PROVENANCE_V0.2 by importing ``PROVENANCE_FIELD_ALIASES`` and
``evaluate_provenance`` directly.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from personal_ai_execution.provenance_contract import (
    PROVENANCE_FIELD_ALIASES as _PROVENANCE_ALIASES,
    evaluate_provenance as _evaluate_provenance,
)

REALITY_CONTRACT_VERSION = "PERSONAL_AI_REALITY_CAPTURE_NORMALIZATION_V0.1"
PROVENANCE_CONTRACT_VERSION = "PERSONAL_AI_ASSET_PROVENANCE_V0.2"

STATUS_VERIFIED = "VERIFIED"
STATUS_INCOMPLETE = "INCOMPLETE"
STATUS_HASH_MISMATCH = "HASH_MISMATCH"
REALITY_STATUSES = (STATUS_VERIFIED, STATUS_INCOMPLETE, STATUS_HASH_MISMATCH)

EPISTEMIC_OBSERVED = "OBSERVED"
EPISTEMIC_STATED = "STATED"
EPISTEMIC_INFERRED = "INFERRED"
EPISTEMIC_UNKNOWN = "UNKNOWN"
EPISTEMIC_STATUSES = (
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_INFERRED,
    EPISTEMIC_UNKNOWN,
)

REALITY_CANDIDATE_FIELDS = (
    "candidate_id",
    "asset_type",
    "source_identity",
    "source_location",
    "source_version",
    "content_version",
    "capture_id",
    "message_id",
    "captured_at",
    "content",
    "content_hash",
    "source_content_hash",
    "verification_evidence",
    "canonical_version",
    "promotion_decision",
    "promotion_event",
    "promoted_at",
    "provenance",
)

REQUIRED_CAPTURE_FIELDS = (
    "source_identity",
    "source_location",
    "source_version",
    "content_version",
    "captured_at",
    "content",
    "verification_evidence",
)

OPTIONAL_CAPTURE_FIELDS = (
    "candidate_id",
    "asset_type",
    "capture_id",
    "message_id",
    "content_hash",
    "source_content_hash",
    "canonical_version",
    "promotion_decision",
    "promotion_event",
    "promoted_at",
    "provenance",
)

REALITY_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "asset_type": ("asset_type",),
    "candidate_id": ("candidate_id", "capture_id", "message_id"),
    "capture_id": ("capture_id", "snapshot_id"),
    "message_id": ("message_id", "wechat_message_id"),
    "source_identity": tuple(_PROVENANCE_ALIASES["source_identity"])
    + ("wechat_source",),
    "source_location": tuple(_PROVENANCE_ALIASES["source_location"]),
    "source_version": tuple(_PROVENANCE_ALIASES["source_version"]),
    "content_version": tuple(_PROVENANCE_ALIASES["content_version"]),
    "captured_at": tuple(_PROVENANCE_ALIASES["captured_at"]),
    "content": ("content", "snapshot.content", "payload", "body"),
    "content_hash": tuple(_PROVENANCE_ALIASES["content_hash"])
    + ("snapshot_hash",),
    "source_content_hash": tuple(_PROVENANCE_ALIASES["source_content_hash"]),
    "verification_evidence": tuple(_PROVENANCE_ALIASES["verification_evidence"])
    + ("capture_evidence",),
    "canonical_version": tuple(_PROVENANCE_ALIASES["canonical_version"]),
    "promotion_decision": tuple(_PROVENANCE_ALIASES["promotion_decision"]),
    "promotion_event": tuple(_PROVENANCE_ALIASES["promotion_event"]),
    "promoted_at": tuple(_PROVENANCE_ALIASES["promoted_at"]),
    "provenance": ("provenance", "asset_provenance"),
}

EPISTEMIC_BLOCK_KEYS = ("epistemic", "epistemics", "evidence_status")

_HASH_PREFIXES = ("sha256:", "sha-256:", "sha256-", "sha512:", "sha-512:", "0x")

REALITY_MATRIX = (
    {
        "scenario": "complete envelope, declared hash agrees with recomputed hash",
        "required_fields": "all present",
        "hash_match": True,
        "status": STATUS_VERIFIED,
        "complete": True,
        "verified": True,
    },
    {
        "scenario": "capture evidence never supplied",
        "required_fields": "verification_evidence absent",
        "hash_match": True,
        "status": STATUS_INCOMPLETE,
        "complete": False,
        "verified": False,
    },
    {
        "scenario": "declared content hash disagrees with recomputed hash",
        "required_fields": "all present",
        "hash_match": False,
        "status": STATUS_HASH_MISMATCH,
        "complete": True,
        "verified": False,
    },
    {
        "scenario": "required field only UNKNOWN epistemic status",
        "required_fields": "present but epistemic UNKNOWN",
        "hash_match": True,
        "status": STATUS_INCOMPLETE,
        "complete": False,
        "verified": False,
    },
    {
        "scenario": "unrecognized epistemic status on a captured field",
        "required_fields": "present but invalid epistemic token",
        "hash_match": True,
        "status": STATUS_INCOMPLETE,
        "complete": False,
        "verified": False,
    },
)


def _lookup(mapping: Any, path: str) -> Any:
    current = mapping
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


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


def _resolve(record: Mapping[str, Any], field: str) -> Any:
    for alias in REALITY_FIELD_ALIASES[field]:
        value = _lookup(record, alias)
        if _meaningful(value):
            return value
    return None


def _normalize_hash(value: Any) -> str:
    text = str(value).strip().lower()
    for prefix in _HASH_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    return text.replace(" ", "")


def hash_content(content: Any) -> str:
    """Deterministically hash a captured content payload.

    Text is hashed as-is; structured content is hashed over its canonical JSON
    encoding. This is pure hashing -- it neither parses nor decrypts any WeChat
    store and assumes nothing about the source mechanism.
    """
    if isinstance(content, str):
        payload = content
    else:
        payload = json.dumps(
            content,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _epistemic_block(envelope: Mapping[str, Any]) -> tuple[Mapping[str, Any], str | None]:
    for key in EPISTEMIC_BLOCK_KEYS:
        value = envelope.get(key)
        if isinstance(value, Mapping):
            return value, None
        if isinstance(value, str) and _meaningful(value):
            return {}, value
    return {}, None


def _epistemic_status(
    declared: Mapping[str, Any],
    record_default: str | None,
    field: str,
    present: bool,
) -> tuple[str, bool]:
    raw = declared.get(field)
    if not _meaningful(raw):
        raw = record_default
    if not _meaningful(raw):
        return (EPISTEMIC_STATED if present else EPISTEMIC_UNKNOWN), True
    token = _text(raw).upper()
    if token not in EPISTEMIC_STATUSES:
        return EPISTEMIC_UNKNOWN, False
    return token, True


def normalize_reality_capture(
    envelope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Normalize a caller-supplied WeChat snapshot envelope into a REALITY
    candidate, fail-closed.

    The input mapping is never mutated and no production state is written.
    """
    source = envelope if isinstance(envelope, Mapping) else {}

    fields: dict[str, Any] = {}
    for field in REALITY_CANDIDATE_FIELDS:
        fields[field] = _resolve(source, field)

    declared_epistemic, record_default = _epistemic_block(source)

    candidate_id = fields["candidate_id"]
    if candidate_id is None:
        candidate_id = fields["message_id"]
    if candidate_id is None:
        candidate_id = fields["capture_id"]
    fields["candidate_id"] = candidate_id

    content = fields["content"]
    computed_hash = hash_content(content) if content is not None else None

    declared_hash = fields["content_hash"]
    source_content_hash = fields["source_content_hash"] or declared_hash

    hash_checked = computed_hash is not None
    hash_match: bool | None = True if hash_checked else None
    if (
        computed_hash is not None
        and declared_hash is not None
        and _normalize_hash(declared_hash) != _normalize_hash(computed_hash)
    ):
        hash_match = False

    epistemic: dict[str, str] = {}
    invalid: list[str] = []
    missing: list[str] = []
    for field in REALITY_CANDIDATE_FIELDS:
        raw = fields[field]
        if field == "asset_type":
            epistemic[field] = EPISTEMIC_STATED
            continue
        present = _meaningful(raw)
        if field == "content_hash" and computed_hash is not None:
            present = True
        status, valid = _epistemic_status(
            declared_epistemic, record_default, field, present
        )
        if not valid:
            invalid.append(field)
        epistemic[field] = status

    for field in REQUIRED_CAPTURE_FIELDS:
        if not _meaningful(fields[field]):
            missing.append(field)
        elif epistemic.get(field) == EPISTEMIC_UNKNOWN:
            if field not in missing:
                missing.append(field)

    unknown = sorted(f for f in fields if epistemic.get(f) == EPISTEMIC_UNKNOWN)
    observed = sorted(f for f in fields if epistemic.get(f) == EPISTEMIC_OBSERVED)
    stated = sorted(f for f in fields if epistemic.get(f) == EPISTEMIC_STATED)
    inferred = sorted(f for f in fields if epistemic.get(f) == EPISTEMIC_INFERRED)

    complete = not missing and not invalid
    verified = bool(complete and hash_match is not False)

    if hash_match is False:
        status = STATUS_HASH_MISMATCH
        reason = (
            "reality capture hash mismatch: declared content_hash does not "
            "agree with the recomputed content hash"
        )
    elif verified:
        status = STATUS_VERIFIED
        reason = (
            "reality capture complete: source/version/capture/content/evidence "
            "linked and content hash consistent"
        )
    else:
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if invalid:
            details.append("unrecognized epistemic status for " + ", ".join(invalid))
        status = STATUS_INCOMPLETE
        reason = "reality capture incomplete: " + "; ".join(details)

    candidate = {
        "asset_type": "REALITY",
        "candidate_id": candidate_id,
        "source_identity": fields["source_identity"],
        "source_location": fields["source_location"],
        "source_version": fields["source_version"],
        "content_version": fields["content_version"],
        "capture_id": fields["capture_id"],
        "message_id": fields["message_id"],
        "captured_at": fields["captured_at"],
        "content": content,
        "content_hash": computed_hash,
        "source_content_hash": source_content_hash,
        "verification_evidence": fields["verification_evidence"],
        "canonical_version": fields["canonical_version"],
        "promotion_decision": fields["promotion_decision"],
        "promotion_event": fields["promotion_event"],
        "promoted_at": fields["promoted_at"],
        "provenance": fields["provenance"],
        "epistemic": epistemic,
    }

    provenance_block = fields["provenance"]
    if not isinstance(provenance_block, Mapping):
        provenance_block = {
            "source": {
                "identity": fields["source_identity"],
                "location": fields["source_location"],
            },
            "source_version": fields["source_version"],
            "content_version": fields["content_version"],
            "source_content_hash": source_content_hash,
            "content_hash": computed_hash,
            "verification": {"evidence": fields["verification_evidence"]},
            "captured_at": fields["captured_at"],
            "canonical_version": fields["canonical_version"],
            "promotion": {
                "decision": fields["promotion_decision"],
                "event_id": fields["promotion_event"],
            },
            "promoted_at": fields["promoted_at"],
        }

    provenance_completeness = _evaluate_provenance(provenance_block)

    required_observed = all(
        epistemic.get(field) == EPISTEMIC_OBSERVED for field in REQUIRED_CAPTURE_FIELDS
    )
    promotion_eligible = bool(verified and required_observed)

    return {
        "contract": REALITY_CONTRACT_VERSION,
        "provenance_contract": PROVENANCE_CONTRACT_VERSION,
        "status": status,
        "complete": complete,
        "verified": verified,
        "missing": missing,
        "invalid": invalid,
        "hash_checked": hash_checked,
        "hash_match": hash_match,
        "fields": fields,
        "candidate": candidate,
        "epistemic": epistemic,
        "epistemic_summary": {
            "observed": observed,
            "stated": stated,
            "inferred": inferred,
            "unknown": unknown,
        },
        "provenance_completeness": provenance_completeness,
        "promotion_eligible": promotion_eligible,
        "read_only": True,
        "write_performed": False,
        "reason": reason,
    }


def build_capture_envelope(
    *,
    source_identity: str,
    source_location: str,
    source_version: str,
    content_version: str,
    captured_at: str,
    content: Any,
    verification_evidence: Any,
    capture_id: str | None = None,
    message_id: str | None = None,
    content_hash: str | None = None,
    epistemic: Mapping[str, str] | None = None,
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structurally complete capture envelope.

    The returned mapping round-trips through :func:`normalize_reality_capture`
    to ``VERIFIED`` when the declared content hash agrees with the recomputed
    hash (or when no hash is declared).
    """
    return {
        "capture_id": capture_id,
        "message_id": message_id,
        "source_identity": source_identity,
        "source_location": source_location,
        "source_version": source_version,
        "content_version": content_version,
        "captured_at": captured_at,
        "content": content,
        "content_hash": content_hash,
        "verification_evidence": verification_evidence,
        "epistemic": dict(epistemic) if epistemic else {},
        "provenance": provenance,
    }


def reality_matrix() -> tuple[dict[str, Any], ...]:
    """Return the documented REALITY capture matrix (a defensive copy)."""
    return tuple(dict(row) for row in REALITY_MATRIX)
