# PERSONAL_AI_REALITY_CAPTURE_NORMALIZATION_CONTRACT_V0.1

Read-only REALITY capture/normalization interface: one documented, fail-closed
cloud-side contract that maps a **caller-supplied WeChat snapshot envelope** into
a **normalized REALITY candidate representation** -- with **no production write,
no Canonical write, no deploy, no credential/permission/binding/schema change and
no Worker change**.

- Task id: `cf-0c19506057cd`
- Parent task id: `cf-2a7dd4a2b665`
  ([`REALITY_AUTO_SYNC_CURRENT_STATE_AUDIT_REPORT.md`](REALITY_AUTO_SYNC_CURRENT_STATE_AUDIT_REPORT.md),
  Sections 2.3, 4, 5 and 6)
- Project: `cloud-assets-activation`
- Risk level: `LOW`
- Contract version tag: `PERSONAL_AI_REALITY_CAPTURE_NORMALIZATION_V0.1`
- Reused contract: `PERSONAL_AI_ASSET_PROVENANCE_V0.2`
  ([`ASSET_PROVENANCE_CONTRACT_V0.2.md`](ASSET_PROVENANCE_CONTRACT_V0.2.md))
- Normative reference implementation: Appendix A
- Validation evidence: Appendix B

---

## 1. Scope and boundary

This contract defines **only the cloud-side normalization link (L2)** of the
WeChat-to-Canonical-REALITY path audited in the parent report:

```
caller-supplied WeChat snapshot envelope            (L1, Windows/out of scope)
        |
        v
normalize_reality_capture(...)   <-- THIS CONTRACT (L2, cloud-only, read-only)
        |
        v
normalized REALITY candidate representation          (promotion/write L3+ out of scope)
```

Everything up to the candidate is specified and testable here. Nothing after the
candidate is performed:

- The normalizer **does not** read a WeChat store, a database, a file or a
  network endpoint.
- The normalizer **does not** decrypt, parse or infer any WeChat storage format,
  key or mechanism. It treats the content payload as an **opaque value supplied
  by the caller**.
- The normalizer **does not** set `canonical_version`, `promotion_decision`,
  `promotion_event` or `promoted_at`; those belong to the promotion gate (L3) and
  are surfaced as `UNKNOWN` until a separate, gated task fills them.
- The normalizer returns `read_only: true` and `write_performed: false` on every
  result, and holds no credential.

This is exactly the declared upstream dependency `reality_ingestion_contract`
recorded in `hello.py:21340-21346`, whose `reuse` is
`["ASSET_PROVENANCE_V0.2", "get_asset"]`.

## 2. Caller-supplied WeChat snapshot envelope

The envelope is an untrusted `Mapping`. Aliases let flat or nested historical
caller payloads be read without inventing metadata. The first meaningful alias
wins.

| Envelope field (canonical) | Meaning | Required | Aliases |
| --- | --- | --- | --- |
| `source_identity` | stable origin id, e.g. `wechat:conversation:42` | yes | `source.identity`, `source_identity`, `source_id`, `source.id`, `wechat_source` |
| `source_location` | where the snapshot came from (URI) | yes | `source.location`, `source_location`, `source_uri`, `source.url` |
| `source_version` | revision of the source record | yes | `source_version`, `source.version`, `source_revision` |
| `content_version` | revision of the captured content | yes | `content_version`, `source.content_version`, `content_revision` |
| `captured_at` | when the capture happened | yes | `captured_at`, `source.captured_at`, `source_timestamp` |
| `content` | the captured payload (opaque; text or structured) | yes | `content`, `snapshot.content`, `payload`, `body` |
| `verification_evidence` | explicit capture evidence (not a bare hash flag) | yes | `verification.evidence`, `verification_evidence`, `evidence`, `capture_evidence` |
| `candidate_id` | stable candidate identity (defaults from capture/message id) | no | `candidate_id`, `capture_id`, `message_id` |
| `capture_id` | snapshot capture id | no | `capture_id`, `snapshot_id` |
| `message_id` | source message id | no | `message_id`, `wechat_message_id` |
| `content_hash` | caller-declared hash of `content` (recomputed and checked) | no | `content_hash`, `canonical_content_hash`, `hash`, `snapshot_hash` |
| `source_content_hash` | caller-declared source-side hash | no | `source_content_hash`, `source.hash`, `source_hash` |
| `canonical_version` / `promotion_*` / `promoted_at` | promotion-time fields | no | provenance aliases (deliberately unset at capture) |
| `provenance` | an existing ASSET_PROVENANCE_V0.2 block to pass through | no | `provenance`, `asset_provenance` |
| `epistemic` | per-field epistemic status (see Section 3) | no | `epistemic`, `epistemics`, `evidence_status` |

The overlapping aliases are imported **directly** from
`PROVENANCE_FIELD_ALIASES` in
`src/personal_ai_execution/provenance_contract.py`, so the REALITY capture
vocabulary can never silently diverge from the ASSET_PROVENANCE_V0.2 vocabulary.

## 3. Explicit OBSERVED / STATED / INFERRED / UNKNOWN handling

Cloud cannot observe a Windows-local WeChat store, so nothing is implicitly
trusted. Every candidate field carries an explicit epistemic status:

| Status | Meaning | May support `promotion_eligible` |
| --- | --- | --- |
| `OBSERVED` | the caller attests the value was directly observed at the source | yes |
| `STATED` | the caller asserts the value but did not/ cannot observe it at ingestion time | no |
| `INFERRED` | derived by the caller from other facts | no |
| `UNKNOWN` | not known / not supplied | no |

Fail-closed rules:

- A field that is present but has **no explicit status defaults to `STATED`**
  (the caller stated it), never `OBSERVED`. The cloud never upgrades a claim to
  an observed fact.
- A required capture field that is present but marked `UNKNOWN` is treated as
  **missing** and the result is `INCOMPLETE`.
- An epistemic token outside the four recognized values is reported in
  `invalid`, the field is treated as `UNKNOWN`, and the result is `INCOMPLETE`.
- `promotion_eligible` is `true` only when the result is `VERIFIED` **and** every
  required field is explicitly `OBSERVED`. A structurally `VERIFIED` candidate
  whose values are only `STATED` is deliberately **not** promotion-eligible.
- The four statuses are summarized in `epistemic_summary`.

This is the concrete application of the audit's evidence discipline
(OBSERVED/STATED/INFERRED/UNKNOWN) to the capture boundary, and it ensures the
future Windows bridge cannot smuggle an inference into Canonical REALITY.

## 4. Normalized REALITY candidate representation

`normalize_reality_capture(envelope)` returns:

```jsonc
{
  "contract": "PERSONAL_AI_REALITY_CAPTURE_NORMALIZATION_V0.1",
  "provenance_contract": "PERSONAL_AI_ASSET_PROVENANCE_V0.2",
  "status": "VERIFIED" | "INCOMPLETE" | "HASH_MISMATCH",
  "complete": true,
  "verified": true,
  "missing": ["...exact missing/unknown required fields..."],
  "invalid": ["...fields with an unrecognized epistemic token..."],
  "hash_checked": true,
  "hash_match": true,
  "fields": { "...resolved raw envelope values..." },
  "candidate": {
    "asset_type": "REALITY",
    "candidate_id": "msg-42",
    "source_identity": "wechat:conversation:42",
    "source_location": "wechat://local-snapshot/snap-42",
    "source_version": "rev-3",
    "content_version": "content-7",
    "capture_id": "snap-42",
    "message_id": "msg-42",
    "captured_at": "2026-10-01T00:00:00+00:00",
    "content": "hello reality",
    "content_hash": "sha256:be0c274f...f05a1",
    "source_content_hash": null,
    "verification_evidence": { "...": "..." },
    "canonical_version": null,
    "promotion_decision": null,
    "promotion_event": null,
    "promoted_at": null,
    "provenance": null,
    "epistemic": { "...field -> status..." }
  },
  "epistemic": { "...field -> status..." },
  "epistemic_summary": {"observed": [], "stated": [], "inferred": [], "unknown": []},
  "provenance_completeness": { "...ASSET_PROVENANCE_V0.2 evaluation..." },
  "promotion_eligible": true,
  "read_only": true,
  "write_performed": false,
  "reason": "reality capture complete: ..."
}
```

Key properties:

- `candidate.asset_type` is always `"REALITY"`; the normalizer produces a
  **candidate**, never a canonical asset.
- `candidate.content_hash` is the hash the cloud **recomputed** over the opaque
  content. If the caller declared `content_hash` and it disagrees, the result is
  `HASH_MISMATCH` and is never verified.
- `content` is passed through unchanged; hashing neither parses nor decrypts it.
- `provenance_completeness` is the existing
  `evaluate_provenance(...)` result over a synthesized ASSET_PROVENANCE_V0.2
  block. It is `INCOMPLETE` by design at capture time because the promotion
  fields are intentionally unset; it becomes `VERIFIED` only after a separate
  promotion gate fills them.

## 5. Fail-closed decision matrix

| Scenario | Required fields | Hash | Status | Verified |
| --- | --- | --- | --- | --- |
| complete envelope, declared hash agrees with recomputed hash | all present | match | `VERIFIED` | yes |
| capture evidence never supplied | `verification_evidence` absent | n/a | `INCOMPLETE` | no |
| declared content hash disagrees with recomputed hash | all present | mismatch | `HASH_MISMATCH` | no |
| required field only `UNKNOWN` epistemic status | present but `UNKNOWN` | n/a | `INCOMPLETE` | no |
| unrecognized epistemic status on a captured field | present but invalid token | n/a | `INCOMPLETE` | no |

Rules:

- Missing (or `UNKNOWN`) required fields are listed exactly and in contract order
  in `missing`; an `INCOMPLETE` candidate is **never** verified.
- `verification_evidence` must be explicit. A lone `content_hash` or
  `content_hash_matches` flag is not treated as capture evidence (this mirrors
  the ASSET_PROVENANCE_V0.2 rule).
- The input mapping is never mutated.
- No Canonical write, D1 write, deploy or credential use is performed. The
  normalizer does not call any Worker tool and does not touch `ASSET_DB`.

## 6. Reuse of ASSET_PROVENANCE_V0.2

| Reused concept | Source | Use here |
| --- | --- | --- |
| field aliases (`source_identity` etc.) | `PROVENANCE_FIELD_ALIASES` | imported and extended, never re-declared |
| completeness/hash evaluation | `evaluate_provenance` | applied to the candidate's synthesized provenance block |
| `source_identity` example `wechat:conversation:42` | `ASSET_PROVENANCE_CONTRACT_V0.2.md:23` | canonical origin id |
| promotion fields | `promotion.decision` / `promotion.event_id` | passed through if supplied, otherwise `UNKNOWN` (never set) |

A regression test asserts the alias reuse so the two vocabularies cannot drift.

## 7. What is deliberately not changed

- No production write, no Canonical write, no D1/`ASSET_DB` mutation.
- No deploy and no Worker change (`worker/index.js` untouched).
- No credential, secret, permission, binding or schema change.
- No `.github/workflows/` change.
- No assumption about WeChat storage layout, database format, decryption or key
  handling; the WeChat data source remains **UNKNOWN** and is supplied opaquely
  by the caller.
- No `mark_reviewed`, no dispatch, no scheduler/cron/queue.
- This artifact adds **no** production code path; the reference implementation
  in Appendix A is the normative specification, validated out-of-tree (Appendix
  B). Materializing it as `src/personal_ai_execution/reality_capture.py` plus
  `tests/test_reality_capture.py` is the next, separately-scoped task.

## 8. Acceptance mapping

| Acceptance criterion | Evidence |
| --- | --- |
| No production writes or Canonical writes | `write_performed: false`, `read_only: true`; no writer called (Sections 1, 7) |
| No deployment/secret/permission/binding/schema changes | only `REALITY_CAPTURE_NORMALIZATION_CONTRACT_V0.1.md` added (Section 7) |
| Deliver a contract/spec artifact and implementation evidence | this document + Appendix A reference implementation + Appendix B validation |
| Tests pass | Appendix B (`21 passed` focused; full-repo regression below) |
| Report smallest next step toward Reality ingestion closure | Section 9 |

## 9. Smallest next step toward Reality ingestion closure

**Materialize and wire the contract**: add
`src/personal_ai_execution/reality_capture.py` (Appendix A verbatim) and
`tests/test_reality_capture.py`, then expose the candidate to a future
**REALITY canonical writer** behind an explicit Human Gate. This is cloud-only,
`LOW` risk and reversible; it still requires **no** production write, no deploy
and no credential change, and it is the declared upstream dependency
(`reality_ingestion_contract`) that unblocks the Windows WeChat snapshot bridge.

Deferred (require Windows / Human Gate, explicitly out of this step): the local
WeChat capture bridge (Windows-only, L1), the relay deploy + secret bindings
(Human Gate), the REALITY canonical writer deploy (Human Gate, L3), and any
scheduler/trigger (L5).

---

## Appendix A: Normative reference implementation

The following module was executed and tested (Appendix B). It is the normative
algorithm of this contract; a later task materializes it verbatim at
`src/personal_ai_execution/reality_capture.py`.

```python
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
```

## Appendix B: Validation evidence

The reference implementation above was executed out-of-tree against 21 focused
tests covering the documented matrix, missing/unknown required fields, hash
mismatch, epistemic defaults, alias resolution, input immutability and
ASSET_PROVENANCE_V0.2 reuse.

```
$ python -m pytest -q test_reality_capture.py
21 passed in 0.03s
```

Worked examples produced by the reference implementation:

```
COMPLETE_STATUS VERIFIED verified= True promotion_eligible= True
COMPUTED_HASH sha256:be0c274fa5c249968d8bee2501ddd1815768b73d557a85d61028bec9917f05a1
MISMATCH_STATUS HASH_MISMATCH verified= False hash_match= False
UNKNOWN_STATUS INCOMPLETE verified= False missing= ['content']
```

Full repository regression (no production path changed by this artifact):

```
$ python -m pytest -q
1101 passed, 1 skipped in 51.20s
```

## Verdict: PASS

A read-only, fail-closed REALITY capture/normalization contract now exists at the
cloud boundary. A caller-supplied WeChat snapshot envelope normalizes to one
`REALITY` candidate with explicit `OBSERVED/STATED/INFERRED/UNKNOWN` tagging and
a recomputed content hash; incomplete, unknown or hash-mismatched captures are
explicitly reported and are never verified, and promotion fields remain
deliberately unset for the separate, gated promotion step.
