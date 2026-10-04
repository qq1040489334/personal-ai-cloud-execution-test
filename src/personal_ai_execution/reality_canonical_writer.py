"""Normative reference implementation -- REALITY_CANONICAL_WRITER_V0.1 (L3).

Promotion boundary between a normalized REALITY candidate (L2,
``PERSONAL_AI_REALITY_CAPTURE_NORMALIZATION_V0.1``) and the existing Personal AI
Canonical write surface (``ASSET_DB: assets / asset_versions``).

The writer is deterministic and fail-closed:

* it accepts a candidate **only** when the L2 result is ``VERIFIED`` and
  ``promotion_eligible`` is ``True`` (every required capture field explicitly
  ``OBSERVED``);
* it re-validates candidate schema, provenance completeness, hash integrity,
  idempotency key, duplicate detection and the authorization boundary before any
  write is even considered;
* REALITY is **source/provenance, never a target** -- promotion routes to an
  existing writable target (``KNOWLEDGE`` / ``SKILL`` / ``DECISION``) through the
  existing writer entry points;
* it never creates a second state store and never performs a production write on
  its own: the production write is delegated to an injected, existing write
  surface and is otherwise reported ``BLOCKED`` with the exact missing
  dependency.

It reuses ASSET_PROVENANCE_V0.2 and REALITY_CAPTURE_V0.1 directly; no alias,
hash or epistemic vocabulary is re-declared.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping

from personal_ai_execution.provenance_contract import (
    PROVENANCE_CONTRACT_VERSION,
    STATUS_VERIFIED as PROVENANCE_VERIFIED,
    build_provenance,
    evaluate_provenance,
)
from personal_ai_execution.reality_capture import (
    REALITY_CONTRACT_VERSION,
    STATUS_VERIFIED as CAPTURE_VERIFIED,
    hash_content,
)

WRITER_CONTRACT_VERSION = "PERSONAL_AI_REALITY_CANONICAL_WRITER_V0.1"
HUMAN_GATE = "HUMAN_GATE_REALITY_CANONICAL_WRITE_V0.1"

REALITY_ASSET_TYPE = "REALITY"
REALITY_ROLE = "SOURCE_PROVENANCE"
CANONICAL_STORE = "ASSET_DB:assets/asset_versions"

TARGET_ASSET_TYPES = ("KNOWLEDGE", "SKILL", "DECISION")
WRITER_ENTRYPOINTS = {
    "KNOWLEDGE": "writeKnowledgeCandidate",
    "SKILL": "writeSkillCandidate",
    "DECISION": "writeDecisionRecord",
}
WRITER_CONTRACTS = {
    "KNOWLEDGE": "PERSONAL_AI_KNOWLEDGE_CANDIDATE_WRITER_V0.1",
    "SKILL": "PERSONAL_AI_SKILL_CANDIDATE_WRITER_V0.1",
    "DECISION": "PERSONAL_AI_DECISION_WRITER_V0.1",
}

STATUS_PROMOTED = "PROMOTED"
STATUS_IDEMPOTENT = "IDEMPOTENT"
STATUS_QUARANTINED = "QUARANTINED"
STATUS_BLOCKED = "BLOCKED"

REQUIRED_CANDIDATE_FIELDS = (
    "candidate_id",
    "asset_type",
    "source_identity",
    "source_location",
    "source_version",
    "content_version",
    "captured_at",
    "content",
    "content_hash",
    "verification_evidence",
)

_HASH_PREFIXES = ("sha256:", "sha-256:", "sha256-", "sha512:", "sha-512:", "0x")

ProductionWriteSurface = Callable[[Mapping[str, Any]], Any]


def _meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _normalize_hash(value: Any) -> str:
    text = str(value).strip().lower()
    for prefix in _HASH_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    return text.replace(" ", "")


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


def resolve_target(candidate: Mapping[str, Any], explicit: Any = None) -> str | None:
    """Resolve the writable target from an explicit value or the candidate.

    The target must be an existing writable canonical asset type. REALITY is
    never a valid target (it is source/provenance only).
    """
    raw = explicit
    if not _meaningful(raw):
        for key in ("target_asset_type", "target", "classification"):
            raw = candidate.get(key)
            if _meaningful(raw):
                break
    if not _meaningful(raw):
        return None
    target = str(raw).strip().upper()
    if target not in TARGET_ASSET_TYPES:
        return None
    return target


def validate_candidate(
    normalized: Mapping[str, Any],
    *,
    target_asset_type: Any = None,
) -> dict[str, Any]:
    """Run the full deterministic validation pipeline (no write, no auth).

    Returns an audit object with ``status`` in ``{"ELIGIBLE", "QUARANTINED"}``
    plus the exact reason, resolved candidate fields, validated content hash and
    the promoted provenance (whether the supplied L2 provenance was already
    complete or the writer completed it with promotion fields).
    """
    audit: dict[str, Any] = {
        "contract": WRITER_CONTRACT_VERSION,
        "capture_contract": REALITY_CONTRACT_VERSION,
        "provenance_contract": PROVENANCE_CONTRACT_VERSION,
        "status": STATUS_QUARANTINED,
        "eligible": False,
        "reasons": [],
        "candidate_id": None,
        "source_identity": None,
        "target_asset_type": None,
        "content_hash": None,
        "provenance_status": None,
        "hash_checked": False,
        "hash_match": None,
    }

    if not isinstance(normalized, Mapping):
        audit["reasons"].append("normalized candidate is not a mapping")
        return audit

    candidate = normalized.get("candidate")
    if not isinstance(candidate, Mapping):
        audit["reasons"].append("normalized result has no candidate mapping")
        return audit

    audit["candidate_id"] = candidate.get("candidate_id")
    audit["source_identity"] = candidate.get("source_identity")

    if normalized.get("status") != CAPTURE_VERIFIED or normalized.get("verified") is not True:
        audit["reasons"].append(
            "capture status is not VERIFIED (status="
            + str(normalized.get("status"))
            + ")"
        )
    if normalized.get("promotion_eligible") is not True:
        audit["reasons"].append("candidate is not promotion_eligible=true")
    if candidate.get("asset_type") != REALITY_ASSET_TYPE:
        audit["reasons"].append("candidate asset_type is not REALITY")

    missing = [
        field
        for field in REQUIRED_CANDIDATE_FIELDS
        if not _meaningful(candidate.get(field))
        and not (field == "content_hash" and _meaningful(candidate.get("content")))
    ]
    if missing:
        audit["reasons"].append(
            "candidate schema missing required fields: " + ", ".join(missing)
        )

    target = resolve_target(candidate, target_asset_type)
    if target is None:
        audit["reasons"].append(
            "target is not an allowed canonical asset type (REALITY is "
            "source/provenance, never a target)"
        )
    else:
        audit["target_asset_type"] = target

    content = candidate.get("content")
    declared_hash = candidate.get("content_hash")
    if _meaningful(content):
        recomputed = hash_content(content)
        audit["hash_checked"] = True
        if _meaningful(declared_hash) and _normalize_hash(declared_hash) != _normalize_hash(
            recomputed
        ):
            audit["hash_match"] = False
            audit["reasons"].append("content hash integrity check failed")
        else:
            audit["hash_match"] = True
        audit["content_hash"] = recomputed
        # The canonical store holds 64-char lowercase hex (no algorithm prefix),
        # exactly like assets.content_hash / asset_versions.content_hash.
        audit["canonical_content_hash"] = _normalize_hash(recomputed)
    else:
        audit["reasons"].append("candidate content is empty; hash cannot be verified")

    if audit["reasons"]:
        return audit

    promoted_provenance = _build_promoted_provenance(
        candidate, audit["canonical_content_hash"]
    )
    provenance = evaluate_provenance(
        promoted_provenance, content_hash=audit["content_hash"]
    )
    audit["provenance_status"] = provenance["status"]
    audit["promoted_provenance"] = promoted_provenance
    if provenance["status"] != PROVENANCE_VERIFIED:
        audit["reasons"].append(
            "promoted provenance is not VERIFIED: " + provenance["reason"]
        )
        return audit

    audit["eligible"] = True
    audit["status"] = "ELIGIBLE"
    return audit


def _build_promoted_provenance(
    candidate: Mapping[str, Any], content_hash: str
) -> dict[str, Any]:
    """Complete the L2 provenance with the promotion fields, fail-closed.

    ``canonical_version`` / ``promotion_decision`` / ``promotion_event`` /
    ``promoted_at`` are intentionally unset at capture; the writer fills them
    deterministically (an explicit value on the candidate always wins) and then
    re-evaluates the provenance under ASSET_PROVENANCE_V0.2.
    """
    candidate_id = candidate.get("candidate_id")
    promoted_at = candidate.get("promoted_at") or candidate.get("captured_at")
    canonical_version = candidate.get("canonical_version") or 1
    promotion_decision = candidate.get("promotion_decision") or "PROMOTE"
    promotion_event = candidate.get("promotion_event") or (
        "promote:" + str(candidate_id) + ":" + str(canonical_version)
    )
    existing = candidate.get("provenance")
    existing = existing if isinstance(existing, Mapping) else {}

    evidence = candidate.get("verification_evidence")
    verification = {"evidence": evidence} if _meaningful(evidence) else None

    built = build_provenance(
        source_identity=str(candidate.get("source_identity")),
        source_location=str(candidate.get("source_location")),
        source_version=str(candidate.get("source_version")),
        content_version=str(candidate.get("content_version")),
        canonical_version=canonical_version,
        content_hash=content_hash,
        verification_evidence=evidence,
        promotion_decision=promotion_decision,
        promotion_event=promotion_event,
        captured_at=str(candidate.get("captured_at")),
        promoted_at=str(promoted_at),
        source_content_hash=candidate.get("source_content_hash"),
    )
    if existing:
        for key, value in existing.items():
            if key not in built:
                built[key] = value
    if verification is not None:
        built.setdefault("verification", {})
        if isinstance(built["verification"], Mapping):
            built["verification"] = {**built["verification"], **verification}
    return built


def prepare_promotion(
    normalized: Mapping[str, Any],
    *,
    target_asset_type: Any = None,
    existing_asset: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic, side-effect-free promotion plan (PREPARE).

    The plan never touches a store. ``status`` is ``IDEMPOTENT`` when the
    existing canonical pointer already holds the same content hash (no new
    version) or ``PROMOTED``-ready otherwise.
    """
    audit = validate_candidate(normalized, target_asset_type=target_asset_type)
    plan: dict[str, Any] = {
        "contract": WRITER_CONTRACT_VERSION,
        "phase": "PREPARE",
        "status": STATUS_QUARANTINED,
        "eligible": audit["eligible"],
        "reasons": list(audit["reasons"]),
        "candidate_id": audit["candidate_id"],
        "source_identity": audit["source_identity"],
        "source_asset_type": REALITY_ASSET_TYPE,
        "reality_role": REALITY_ROLE,
        "target_asset_type": audit["target_asset_type"],
        "canonical_store": CANONICAL_STORE,
        "reused_canonical_writer": None,
        "reused_writer_contract": None,
        "content_hash": audit.get("canonical_content_hash") or audit["content_hash"],
        "idempotency_key": None,
        "intent_hash": None,
        "proposed_version": None,
        "replay": False,
        "requires_human_gate": True,
        "human_gate": HUMAN_GATE,
        "write_request": None,
        "production_write_performed": False,
        "second_state_store_created": False,
    }
    if not audit["eligible"]:
        return plan

    target = audit["target_asset_type"]
    candidate = normalized["candidate"]
    content_hash = audit["canonical_content_hash"]
    asset_id = target.lower() + ":" + str(audit["candidate_id"])
    idempotency_key = target.lower() + ":" + str(audit["candidate_id"]) + ":" + content_hash

    current_version = 0
    replay = False
    if isinstance(existing_asset, Mapping):
        raw_version = existing_asset.get("current_version")
        if isinstance(raw_version, int) and not isinstance(raw_version, bool) and raw_version >= 0:
            current_version = raw_version
        existing_hash = existing_asset.get("content_hash")
        if _meaningful(existing_hash) and _normalize_hash(existing_hash) == _normalize_hash(
            content_hash
        ):
            replay = True
    version = current_version if replay else current_version + 1

    write_request = {
        "phase": "EXECUTE",
        "canonical_writer": WRITER_ENTRYPOINTS[target],
        "canonical_writer_contract": WRITER_CONTRACTS[target],
        "canonical_store": CANONICAL_STORE,
        "asset_id": asset_id,
        "asset_type": target,
        "content": candidate.get("content"),
        "content_hash": content_hash,
        "candidate_id": audit["candidate_id"],
        "source_identity": audit["source_identity"],
        "source_asset_type": REALITY_ASSET_TYPE,
        "reality_role": REALITY_ROLE,
        "provenance_contract": PROVENANCE_CONTRACT_VERSION,
        "provenance": audit.get("promoted_provenance"),
        "idempotency_key": idempotency_key,
        "proposed_version": version,
        "supersedes": list(existing_asset.get("supersedes", []))
        if isinstance(existing_asset, Mapping)
        else [],
        "canonical_write_enabled": False,
    }
    intent_hash = _sha256(write_request)

    plan.update(
        {
            "status": STATUS_IDEMPOTENT if replay else "PREPARED",
            "reused_canonical_writer": WRITER_ENTRYPOINTS[target],
            "reused_writer_contract": WRITER_CONTRACTS[target],
            "idempotency_key": idempotency_key,
            "intent_hash": intent_hash,
            "proposed_version": version,
            "replay": replay,
            "write_request": write_request,
        }
    )
    plan["write_request"]["intent_hash"] = intent_hash
    return plan


def promote_reality_candidate(
    normalized: Mapping[str, Any],
    *,
    target_asset_type: Any = None,
    existing_asset: Mapping[str, Any] | None = None,
    human_gate_authorized: bool = False,
    authorization: Any = None,
    ledger: dict[str, Any] | None = None,
    write_surface: ProductionWriteSurface | None = None,
) -> dict[str, Any]:
    """Promote a normalized REALITY candidate through the existing write surface.

    Fail-closed ordering: validate -> duplicate/idempotency -> authorization ->
    write. Without an authorized human gate the result is ``BLOCKED``. With
    authorization but without an injected production write surface the result is
    ``BLOCKED`` and the exact missing dependency is reported. A repeated
    idempotency key returns ``IDEMPOTENT`` and never calls the write surface, so
    repeated promotion cannot create a duplicate canonical version.
    """
    plan = prepare_promotion(
        normalized,
        target_asset_type=target_asset_type,
        existing_asset=existing_asset,
    )
    result: dict[str, Any] = {
        "contract": WRITER_CONTRACT_VERSION,
        "phase": "EXECUTE",
        "status": STATUS_QUARANTINED,
        "candidate_id": plan["candidate_id"],
        "source_identity": plan["source_identity"],
        "target_asset_type": plan["target_asset_type"],
        "content_hash": plan["content_hash"],
        "idempotency_key": plan["idempotency_key"],
        "intent_hash": plan["intent_hash"],
        "canonical_store": CANONICAL_STORE,
        "canonical_write_performed": False,
        "second_state_store_created": False,
        "requires_human_gate": True,
        "human_gate": HUMAN_GATE,
        "human_gate_authorized": bool(human_gate_authorized),
        "write_surface": None,
        "reasons": list(plan["reasons"]),
        "write_response": None,
    }

    if not plan["eligible"] or plan["write_request"] is None:
        result["reasons"].append("plan is not eligible; promotion refused")
        return result

    if plan["replay"]:
        result["status"] = STATUS_IDEMPOTENT
        result["reasons"].append(
            "existing canonical version already holds the same content hash; "
            "no new version written"
        )
        return result

    key = plan["idempotency_key"]
    if isinstance(ledger, dict) and key in ledger:
        result["status"] = STATUS_IDEMPOTENT
        result["reasons"].append(
            "idempotency key already admitted; duplicate promotion suppressed"
        )
        result["write_response"] = ledger[key]
        return result

    authorized = bool(human_gate_authorized) and authorization in (HUMAN_GATE, True)
    if not authorized:
        result["status"] = STATUS_BLOCKED
        result["reasons"].append(
            "blocked: " + HUMAN_GATE + " is not authorized"
        )
        return result

    if write_surface is None:
        result["status"] = STATUS_BLOCKED
        result["reasons"].append(
            "blocked: no production write surface available -- provide the "
            "existing Personal AI Canonical write surface bound to the "
            "production ASSET_DB (dependency: Cloudflare ASSET_DB binding + "
            "authorized MCP invocation); no second state store is created"
        )
        return result

    result["write_surface"] = getattr(write_surface, "__name__", "production_write_surface")
    try:
        response = write_surface(plan["write_request"])
    except Exception as exc:  # pragma: no cover - defensive fail-closed
        result["status"] = STATUS_BLOCKED
        result["reasons"].append(
            "production write surface raised: " + type(exc).__name__
        )
        return result

    if isinstance(ledger, dict):
        ledger[key] = {"version": plan["proposed_version"], "intent_hash": plan["intent_hash"]}
    result["status"] = STATUS_PROMOTED
    result["canonical_write_performed"] = True
    result["write_response"] = response
    result["reasons"].append(
        "promoted via existing canonical writer " + str(plan["reused_canonical_writer"])
    )
    return result


def writer_matrix() -> tuple[dict[str, Any], ...]:
    """Documented promotion decision matrix (a defensive copy)."""
    rows = (
        ("VERIFIED + promotion_eligible + authorized + write surface", STATUS_PROMOTED),
        ("same candidate already promoted (existing content hash)", STATUS_IDEMPOTENT),
        ("repeated promotion with admitted idempotency key", STATUS_IDEMPOTENT),
        ("VERIFIED but promotion_eligible=false", STATUS_QUARANTINED),
        ("capture status HASH_MISMATCH/INCOMPLETE", STATUS_QUARANTINED),
        ("target is REALITY", STATUS_QUARANTINED),
        ("eligible but human gate not authorized", STATUS_BLOCKED),
        ("eligible + authorized but no write surface/credential", STATUS_BLOCKED),
    )
    return tuple({"scenario": scenario, "status": status} for scenario, status in rows)
