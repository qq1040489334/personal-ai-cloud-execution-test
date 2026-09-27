"""PERSONAL_AI_ASSET_PROVENANCE_V0.2 -- canonical Cloud Asset provenance.

This module defines the single, documented provenance contract for a canonical
Personal AI Cloud Asset. Every canonical asset version must be traceable, end to
end, to:

* **source identity / location** -- what the asset was derived from and where it
  lives;
* **source / content version** -- which revision of the source and of the source
  content produced the asset;
* **canonical version** -- the ``asset_versions.version`` the provenance belongs
  to;
* **content hash** -- the hash of the canonicalized content that was promoted;
* **verification evidence** -- how the asset was checked (e.g. recomputing the
  content hash) and when;
* **promotion decision / event** -- the explicit promotion decision and its
  append-only event id;
* **timestamps** -- when the source was captured and when the asset was promoted;
* **supersession lineage** -- which version an asset supersedes, and which
  version (if any) supersedes it.

The contract is *fail-closed*. A record that is missing any required field is
reported as ``INCOMPLETE`` and is **never** treated as verified: provenance
completeness is stated explicitly, with the exact list of missing fields, so a
historical asset can never be silently upgraded to a verified state. A hash that
does not agree with the recorded verification evidence is reported as
``HASH_MISMATCH`` and is likewise never verified.

The same contract is implemented in ``worker/index.js`` (the deployed asset read
path); a regression test asserts the field/alias tables are identical.
"""

from __future__ import annotations

from typing import Any, Mapping

#: Version tag shared by the Python and Worker implementations.
PROVENANCE_CONTRACT_VERSION = "PERSONAL_AI_ASSET_PROVENANCE_V0.2"

#: Provenance verification states.
STATUS_VERIFIED = "VERIFIED"
STATUS_INCOMPLETE = "INCOMPLETE"
STATUS_HASH_MISMATCH = "HASH_MISMATCH"
PROVENANCE_STATUSES = (STATUS_VERIFIED, STATUS_INCOMPLETE, STATUS_HASH_MISMATCH)

#: Every field the canonical provenance can carry, in contract order.
PROVENANCE_FIELDS = (
    "source_identity",
    "source_location",
    "source_version",
    "content_version",
    "canonical_version",
    "content_hash",
    "source_content_hash",
    "verification_evidence",
    "promotion_decision",
    "promotion_event",
    "captured_at",
    "promoted_at",
    "supersedes",
    "superseded_by",
)

#: Fields that must be present for a provenance to be considered complete.
REQUIRED_PROVENANCE_FIELDS = (
    "source_identity",
    "source_location",
    "source_version",
    "content_version",
    "canonical_version",
    "content_hash",
    "verification_evidence",
    "promotion_decision",
    "promotion_event",
    "captured_at",
    "promoted_at",
)

#: Fields that are only required "where applicable" (e.g. supersession lineage).
OPTIONAL_PROVENANCE_FIELDS = (
    "source_content_hash",
    "supersedes",
    "superseded_by",
)

#: Accepted locations for each canonical field. The first meaningful alias wins,
#: which lets historical records (flat or nested, with legacy names) be read
#: without inventing any metadata.
PROVENANCE_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "source_identity": ("source.identity", "source_identity", "source_id", "source.id"),
    "source_location": ("source.location", "source_location", "source_uri", "source.url"),
    "source_version": ("source_version", "source.version", "source_revision"),
    "content_version": ("content_version", "source.content_version", "content_revision"),
    "canonical_version": ("canonical_version", "target_version", "version"),
    "content_hash": ("content_hash", "canonical_content_hash", "hash"),
    "source_content_hash": ("source_content_hash", "source.hash", "source_hash"),
    "verification_evidence": (
        "verification.evidence",
        "verification_evidence",
        "evidence",
    ),
    "promotion_decision": ("promotion.decision", "promotion_decision", "decision"),
    "promotion_event": (
        "promotion.event_id",
        "promotion_event",
        "promotion_event_id",
        "promotion.id",
    ),
    "captured_at": ("captured_at", "source.captured_at", "source_timestamp"),
    "promoted_at": ("promoted_at", "promotion.decided_at", "promotion.timestamp"),
    "supersedes": ("supersedes", "supersession", "lineage.supersedes"),
    "superseded_by": ("superseded_by", "lineage.superseded_by"),
}

#: Hash-only keys inside a verification block that are not, by themselves,
#: verification evidence.
_VERIFICATION_HASH_KEYS = frozenset(
    {"content_hash_matches", "expected_content_hash", "content_hash"}
)

_HASH_PREFIXES = ("sha256:", "sha-256:", "sha256-", "sha-512:", "0x")


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


def _resolve(provenance: Mapping[str, Any], field: str) -> Any:
    for alias in PROVENANCE_FIELD_ALIASES[field]:
        value = _lookup(provenance, alias)
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


def _expected_hashes(
    provenance: Mapping[str, Any], verification: Mapping[str, Any] | None
) -> list[Any]:
    expected: list[Any] = []
    for source in (_lookup(provenance, "verification"), verification):
        if not isinstance(source, Mapping):
            continue
        for key in ("expected_content_hash", "content_hash"):
            if _meaningful(source.get(key)):
                expected.append(source.get(key))
    return expected


def _explicit_match(
    provenance: Mapping[str, Any], verification: Mapping[str, Any] | None
) -> bool | None:
    for source in (_lookup(provenance, "verification"), verification):
        if isinstance(source, Mapping) and "content_hash_matches" in source:
            return bool(source.get("content_hash_matches"))
    return None


def evaluate_provenance(
    provenance: Mapping[str, Any] | None,
    *,
    content_hash: Any = None,
    canonical_version: Any = None,
    verification: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate provenance completeness and verification, fail-closed.

    ``content_hash`` / ``canonical_version`` are the values stored on the
    canonical ``assets`` row (the current version's content hash and version).
    ``verification`` is the separate ``asset_versions.verification`` column,
    used as a fallback for verification evidence and the expected content hash so
    records that split provenance and verification across two columns are still
    evaluated correctly.
    """
    source = provenance if isinstance(provenance, Mapping) else {}

    fields: dict[str, Any] = {}
    for field in PROVENANCE_FIELDS:
        fields[field] = _resolve(source, field)

    if fields["canonical_version"] is None and _meaningful(canonical_version):
        fields["canonical_version"] = canonical_version

    if fields["verification_evidence"] is None and isinstance(verification, Mapping):
        candidate = verification.get("evidence")
        if not _meaningful(candidate):
            candidate = verification.get("method")
        if _meaningful(candidate):
            fields["verification_evidence"] = candidate
        else:
            extra = {
                key: value
                for key, value in verification.items()
                if key not in _VERIFICATION_HASH_KEYS and _meaningful(value)
            }
            if extra:
                fields["verification_evidence"] = extra

    missing = [
        field for field in REQUIRED_PROVENANCE_FIELDS if fields[field] is None
    ]

    declared = fields["content_hash"]
    expected = _expected_hashes(source, verification)
    stored = content_hash if _meaningful(content_hash) else None

    pairs: list[tuple[Any, Any]] = []
    if declared is not None and stored is not None:
        pairs.append((declared, stored))
    if declared is not None and expected:
        pairs.append((declared, expected[0]))
    if stored is not None and expected:
        pairs.append((stored, expected[0]))

    hash_checked = False
    hash_match: bool | None = None
    for left, right in pairs:
        hash_checked = True
        if _normalize_hash(left) != _normalize_hash(right):
            hash_match = False
            break
        if hash_match is None:
            hash_match = True

    explicit = _explicit_match(source, verification)
    if explicit is not None:
        hash_checked = True
        if explicit is False:
            hash_match = False
        elif hash_match is None:
            hash_match = explicit

    complete = not missing
    verified = bool(complete and hash_match is not False)

    supersedes = fields.get("supersedes")
    if isinstance(supersedes, (list, tuple, set)):
        supersedes = [entry for entry in supersedes]
    elif supersedes is None:
        supersedes = []
    else:
        supersedes = [supersedes]

    if hash_match is False:
        status = STATUS_HASH_MISMATCH
        reason = (
            "provenance hash mismatch: content_hash does not agree with the "
            "recorded verification evidence"
        )
    elif verified:
        status = STATUS_VERIFIED
        reason = (
            "provenance complete: source/version/hash/verification/promotion "
            "evidence linked"
        )
    else:
        status = STATUS_INCOMPLETE
        reason = "provenance incomplete: missing " + ", ".join(missing)

    return {
        "contract": PROVENANCE_CONTRACT_VERSION,
        "status": status,
        "complete": complete,
        "verified": verified,
        "missing": missing,
        "fields": fields,
        "hash_checked": hash_checked,
        "hash_match": hash_match,
        "lineage": {
            "supersedes": supersedes,
            "superseded_by": fields.get("superseded_by"),
        },
        "reason": reason,
    }


def build_provenance(
    *,
    source_identity: str,
    source_location: str,
    source_version: str,
    canonical_version: Any,
    content_hash: str,
    verification_evidence: Any,
    promotion_decision: str,
    promotion_event: str,
    captured_at: str,
    promoted_at: str,
    content_version: str | None = None,
    source_content_hash: str | None = None,
    actor: str | None = None,
    method: str | None = None,
    verified_at: str | None = None,
    supersedes: list[Any] | None = None,
    superseded_by: Any = None,
) -> dict[str, Any]:
    """Build a canonical, structurally complete provenance record.

    The returned mapping round-trips through :func:`evaluate_provenance` to
    ``VERIFIED`` when the declared content hash agrees with the recorded
    evidence.
    """
    return {
        "source": {
            "identity": source_identity,
            "location": source_location,
        },
        "source_version": source_version,
        "content_version": content_version if content_version is not None else source_version,
        "source_content_hash": source_content_hash,
        "canonical_version": canonical_version,
        "content_hash": content_hash,
        "verification": {
            "evidence": verification_evidence,
            "method": method or "recompute_content_hash",
            "verified_at": verified_at or promoted_at,
            "content_hash_matches": True,
        },
        "promotion": {
            "decision": promotion_decision,
            "event_id": promotion_event,
            "decided_at": promoted_at,
            "actor": actor,
        },
        "captured_at": captured_at,
        "promoted_at": promoted_at,
        "supersedes": list(supersedes or []),
        "superseded_by": superseded_by,
    }


#: Documented provenance decision matrix (also rendered in the contract doc).
PROVENANCE_MATRIX = (
    {
        "scenario": "complete provenance, content hash agrees",
        "required_fields": "all present",
        "hash_match": True,
        "status": STATUS_VERIFIED,
        "complete": True,
        "verified": True,
    },
    {
        "scenario": "historical record missing verification evidence",
        "required_fields": "verification_evidence absent",
        "hash_match": None,
        "status": STATUS_INCOMPLETE,
        "complete": False,
        "verified": False,
    },
    {
        "scenario": "content hash disagrees with verification evidence",
        "required_fields": "all present",
        "hash_match": False,
        "status": STATUS_HASH_MISMATCH,
        "complete": True,
        "verified": False,
    },
    {
        "scenario": "promotion decision/event never recorded",
        "required_fields": "promotion_decision/promotion_event absent",
        "hash_match": None,
        "status": STATUS_INCOMPLETE,
        "complete": False,
        "verified": False,
    },
    {
        "scenario": "supersession lineage recorded",
        "required_fields": "all present",
        "hash_match": True,
        "status": STATUS_VERIFIED,
        "complete": True,
        "verified": True,
    },
)


def provenance_matrix() -> tuple[dict[str, Any], ...]:
    """Return the documented provenance matrix (a defensive copy)."""
    return tuple(dict(row) for row in PROVENANCE_MATRIX)
