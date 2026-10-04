# REALITY_CANONICAL_WRITER_IMPLEMENTATION_REPORT

- goal: `REALITY_CANONICAL_WRITER_L3_IMPLEMENTATION_V0.1`
- task_id: `cf-4666bf2857a7`
- project_id: `cloud-assets-activation`
- risk_level: `LOW`
- writer contract version: `PERSONAL_AI_REALITY_CANONICAL_WRITER_V0.1`
- reused capture contract: `PERSONAL_AI_REALITY_CAPTURE_NORMALIZATION_V0.1`
- reused provenance contract: `PERSONAL_AI_ASSET_PROVENANCE_V0.2`
- human gate: `HUMAN_GATE_REALITY_CANONICAL_WRITE_V0.1`
- report status: `PASS`
- production write status: `BLOCKED` (exact dependency in Section 7)
- final status: `BLOCKED_PRODUCTION_WRITE_UNAVAILABLE`

---

## 1. Scope and boundary

This report specifies and validates the next REALITY layer (L3) after
`REALITY_CAPTURE_IMPLEMENTATION_MATERIALIZATION_V0.1`
(`src/personal_ai_execution/reality_capture.py`, `tests/test_reality_capture.py`).

```
caller-supplied WeChat snapshot envelope                     (L1, out of scope)
        |
        v
normalize_reality_capture(...)   -- L2, read-only, already materialized
        |
        v
normalized REALITY candidate (status=VERIFIED, promotion_eligible)
        |
        v
REALITY canonical writer (L3, THIS REPORT)
        |  deterministic validation -> idempotency -> authorization
        v
existing Personal AI Canonical write surface  (ASSET_DB: assets/asset_versions)
```

The writer is **source/provenance, never a target**: a REALITY candidate carries
provenance and routes to an existing writable canonical target
(`KNOWLEDGE` / `SKILL` / `DECISION`) through the already-deployed Worker entry
points. No REALITY asset is created and no REALITY writer entry point is added.

The task's declared modification scope (`expected_files`) contains only this
report. Consistent with the repository's established contract pattern
(`REALITY_CAPTURE_NORMALIZATION_CONTRACT_V0.1.md`, Section 7), the normative
implementation is provided in full in Appendix A and was **validated
out-of-tree** (Appendix B/C). Materializing the module and its regression suite
into `src/` and `tests/` is a separate, separately-scoped task. No repository
path other than this report was modified.

## 2. Acceptance gate (input contract)

The writer accepts exactly the normalized result produced by
`normalize_reality_capture` and promotes it only when **all** of the following
hold:

| # | Gate | Required | Fail-closed result |
| --- | --- | --- | --- |
| 1 | input is a `Mapping` | yes | `QUARANTINED` |
| 2 | `result["candidate"]` is a `Mapping` | yes | `QUARANTINED` |
| 3 | `result["status"] == "VERIFIED"` and `result["verified"] is True` | yes | `QUARANTINED` |
| 4 | `result["promotion_eligible"] is True` | yes | `QUARANTINED` |
| 5 | `candidate["asset_type"] == "REALITY"` | yes | `QUARANTINED` |
| 6 | candidate schema complete | yes | `QUARANTINED` |
| 7 | content hash integrity (recompute == declared) | yes | `QUARANTINED` |
| 8 | target is an allowed writable type (not `REALITY`) | yes | `QUARANTINED` |
| 9 | promoted provenance evaluates `VERIFIED` | yes | `QUARANTINED` |
| 10 | human gate authorized | yes | `BLOCKED` |
| 11 | existing production write surface available | yes | `BLOCKED` |

Gate 4 is the concrete "accepts only verified promotion-eligible candidates"
requirement: `promotion_eligible` is `True` only when the L2 result is
`VERIFIED` **and** every required capture field is explicitly `OBSERVED`
(`reality_capture.py:386-389`). A structurally `VERIFIED` candidate whose values
are only `STATED`/`INFERRED` is rejected. `OBSERVED` / `STATED` / `INFERRED` /
`UNKNOWN` semantics are reused verbatim and never re-declared or upgraded.

## 3. Deterministic validation pipeline (before any write)

`validate_candidate(normalized, target_asset_type=...)` is pure, in-memory and
deterministic. It runs the steps below in order and returns an audit object with
`eligible`, `status`, the exact `reasons`, the resolved `target_asset_type`,
`content_hash`, `canonical_content_hash`, `hash_checked`, `hash_match`,
`provenance_status` and the completed `promoted_provenance`.

1. **Candidate schema** — every required candidate field is present and
   meaningful: `candidate_id`, `asset_type`, `source_identity`,
   `source_location`, `source_version`, `content_version`, `captured_at`,
   `content`, `content_hash`, `verification_evidence`. (`content_hash` may be
   absent from the raw candidate because L2 always recomputes it.)
2. **Provenance completeness** — the writer completes the L2 provenance with the
   promotion fields (`canonical_version`, `promotion_decision="PROMOTE"`,
   `promotion_event`, `promoted_at`) and re-evaluates it with the existing
   `evaluate_provenance(...)` from `provenance_contract.py`. It must be
   `VERIFIED`; the completion never invents evidence and never weakens the
   ASSET_PROVENANCE_V0.2 fail-closed rules.
3. **Hash integrity** — the content hash is recomputed with the L2
   `hash_content(...)` (opaque content, canonical JSON for structured content)
   and compared, prefix/case normalized, against the declared hash. A mismatch
   is quarantined. The value handed to the canonical store is the 64-character
   lowercase hex (no algorithm prefix), matching `assets.content_hash` /
   `asset_versions.content_hash`.
4. **Idempotency key** — `"<target>:<candidate_id>:<canonical_content_hash>"`,
   mirroring the existing writer's identical-content rule, plus a deterministic
   `intent_hash` = sha256 over the canonical JSON of the write request.
5. **Duplicate detection** — if the existing canonical pointer already holds the
   same content hash the plan is `IDEMPOTENT` and the version does not advance
   (`version_policy = existing.current_version + 1`, unchanged for a replay);
   an already-admitted `idempotency_key` in the admission ledger also returns
   `IDEMPOTENT`.
6. **Authorization boundary** — execution requires `human_gate_authorized=True`
   **and** the `HUMAN_GATE_REALITY_CANONICAL_WRITE_V0.1` token; otherwise the
   result is `BLOCKED`.
7. **Production write surface** — a real write requires an injected, existing
   canonical write surface. Without it the result is `BLOCKED` with the exact
   dependency (Section 7); the writer never fabricates a write and never opens a
   second store.

## 4. Reuse of the existing canonical write surface (no second state store)

The writer reuses the already-deployed Worker entry points, asserted from
`worker/index.js`:

| Target | Existing entry point | Existing contract | Worker location |
| --- | --- | --- | --- |
| `KNOWLEDGE` | `writeKnowledgeCandidate` | `PERSONAL_AI_KNOWLEDGE_CANDIDATE_WRITER_V0.1` | `worker/index.js:2853` |
| `SKILL` | `writeSkillCandidate` | `PERSONAL_AI_SKILL_CANDIDATE_WRITER_V0.1` | `worker/index.js:2953` |
| `DECISION` | `writeDecisionRecord` | `PERSONAL_AI_DECISION_WRITER_V0.1` | `worker/index.js:3037` |

The MCP tools `write_knowledge_candidate` (`worker/index.js:3326`),
`write_skill_candidate` (`:3365`) and `write_decision_record` (`:3390`) are the
production surface; each writes only to the existing `ASSET_DB`
`assets` / `asset_versions` tables. `REALITY` is a declared asset type
(`worker/index.js:952`) but has **no** writer entry point and is never a target,
so `resolve_target` rejects a `REALITY` target as a quarantine condition. The
writer object exposes `second_state_store_created: false` and
`canonical_store: "ASSET_DB:assets/asset_versions"` on every plan and result.

The existing Knowledge / Skill / Decision writer code paths are not modified;
this layer only prepares a validated request for them.

## 5. Idempotency behavior

Two independent, deterministic guards make repeated promotion safe:

- **Existing-pointer replay**: when `existing_asset.content_hash` already equals
  the promoted content hash, `prepare_promotion` returns `IDEMPOTENT` and
  `promote_reality_candidate` returns `IDEMPOTENT` without touching the write
  surface (`canonical_write_performed: false`).
- **Admission ledger replay**: when the `idempotency_key` is already present in
  the in-memory ledger, the result is `IDEMPOTENT`, returns the recorded version
  and does **not** call the write surface.

Worked evidence (Appendix C): first promotion `PROMOTED` with
`WRITE_SURFACE_CALLS = 1`; an identical repeat is `IDEMPOTENT` and the write
surface is still called exactly once. Repeated promotion therefore cannot create
a duplicate canonical asset version.

## 6. Preserved semantics

- **ASSET_PROVENANCE_V0.2** is reused directly (`evaluate_provenance`,
  `build_provenance`); the writer re-declares no alias table and fabricates no
  evidence. The promoted provenance is `VERIFIED` and carries
  `promotion.decision = "PROMOTE"` and an append-only `promotion.event_id`.
- **OBSERVED / STATED / INFERRED / UNKNOWN** are taken from
  `reality_capture.py`; promotion eligibility is derived from the L2
  `promotion_eligible` flag, so the writer can never promote a `STATED`-only
  candidate.
- **REALITY is source/provenance**: `source_asset_type = "REALITY"`,
  `reality_role = "SOURCE_PROVENANCE"`; the target is a writable asset type.

## 7. Human Gate and production write boundary

Everything in Sections 1–6 (validation, planning, replay) is reversible,
non-production repository work and does not cross the gate. Exactly one action
crosses the gate: executing an existing canonical writer against the production
`ASSET_DB`.

Human Gate authorization for this phase is recorded as granted. Fail-closed
behavior is nevertheless preserved: even with authorization, a real write
requires the existing production surface bound to `ASSET_DB`. That surface
(D1/Cloudflare `ASSET_DB` binding plus an authorized MCP invocation) is **not
available in this execution environment**, so the writer returns `BLOCKED` and
performs no write:

```
AUTHORIZED_BUT_NO_SURFACE_STATUS BLOCKED
reason: blocked: no production write surface available -- provide the existing
Personal AI Canonical write surface bound to the production ASSET_DB
(dependency: Cloudflare ASSET_DB binding + authorized MCP invocation);
no second state store is created
```

This mirrors the repository's existing
`worker/PRODUCTION-BASELINE.json` controlled-deploy record, which is also
`BLOCKED` because no Cloudflare production deploy credential is present. The
exact dependency to unblock is: inject the Cloudflare `ASSET_DB` binding and
invoke the authorized MCP write tools (`write_knowledge_candidate` /
`write_skill_candidate` / `write_decision_record`) for an eligible promoted
request. No credential, token or secret is read, logged or stored by this
report or the reference implementation.

## 8. What is deliberately unchanged

- No `.github/workflows/` change.
- No change to `worker/index.js`, `worker/migrations/`, `ASSET_DB`, or any D1
  schema. No new table, store, inbox, queue or curator.
- No change to the Knowledge / Skill / Decision writer paths, their contracts or
  their tests.
- No change to `src/personal_ai_execution/reality_capture.py` or
  `src/personal_ai_execution/provenance_contract.py`.
- No production write, no deploy, no credential/secret/permission/binding change.
- Only `REALITY_CANONICAL_WRITER_IMPLEMENTATION_REPORT.md` is added.

## 9. Evidence

### 9.1 Focused out-of-tree validation

The Appendix A implementation was executed against the Appendix B focused suite
(19 tests) with the repository's materialized L2 and provenance modules on
`sys.path`:

```
$ python -m pytest -q test_reality_canonical_writer.py
19 passed in 0.04s
```

Coverage: only `VERIFIED`+`promotion_eligible` accepted; non-verified,
non-promotion-eligible, incomplete and non-mapping candidates quarantined;
`REALITY` target quarantined; zero-mutation PREPARE; all three targets reuse the
existing writers/contracts; deterministic intent hash and idempotency key;
first promotion writes once; repeated promotion is `IDEMPOTENT` with one write;
existing-pointer replay is idempotent; unauthorized is `BLOCKED`; authorized but
no write surface is `BLOCKED` with the `ASSET_DB` dependency; tampered content
fails hash integrity; input is never mutated; provenance re-evaluates
`VERIFIED`.

### 9.2 Full repository regression

```
$ python -m pytest -q
1130 passed, 1 skipped in 41.36s
```

No existing test changed or failed.

### 9.3 Worked examples

See Appendix C for the full deterministic output (eligible audit, prepared plan,
promotion / replay, blocked-with-dependency).

## 10. Changed files

- `REALITY_CANONICAL_WRITER_IMPLEMENTATION_REPORT.md` (this report, new)

No other repository path was modified, and no file was deleted.

## 11. Acceptance mapping

| Acceptance criterion | Evidence |
| --- | --- |
| No second Canonical/state database created | `second_state_store_created: false`; `canonical_store = ASSET_DB:assets/asset_versions`; target resolves to existing Worker writers (Sections 4, 8) |
| Writer accepts only verified promotion-eligible candidates | Gates 3–4 (Section 2); `validate_candidate`; Appendix B tests |
| Idempotent repeated promotion does not create duplicate Canonical assets | existing-hash replay + admission ledger replay; Appendix C `PROMOTED` then `IDEMPOTENT`, one write surface call (Section 5) |
| Existing Knowledge/Skill/Decision paths unchanged | reused only; no diff to `worker/index.js` or their tests (Section 8) |
| Tests pass | Appendix B `19 passed`; full suite `1130 passed, 1 skipped` (Section 9) |
| Any production write evidence is explicit and auditable | write requires an injected surface; result carries `canonical_write_performed`, `write_surface`, `idempotency_key`, `intent_hash`, `write_response`; no fabricated write (Sections 3, 7) |
| Secrets never exposed | no credential read, logged or stored; no secret in this report or the implementation (Section 7) |
| Stop at BLOCKED if a required dependency is unavailable | `BLOCKED` with the exact `ASSET_DB` binding + authorized MCP dependency (Section 7) |

## Verdict

The REALITY canonical writer logic is specified, fail-closed and validated: it
accepts only `VERIFIED` and `promotion_eligible` REALITY candidates, re-validates
schema, provenance, hash, idempotency, duplicates and authorization before any
write, reuses the existing canonical write surface without a second state store,
and is idempotent on repeat. The report portion is `PASS`; the actual production
write is `BLOCKED` because the production `ASSET_DB`-bound write surface is not
available in this environment, and the exact unblock dependency is identified.
Materializing the Appendix A module and Appendix B suite into the repository is
a separate, separately-scoped task.

---

## Appendix A: Normative reference implementation

```python
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
```

## Appendix B: Focused validation suite (out-of-tree)

```python
"""Focused out-of-tree validation for REALITY_CANONICAL_WRITER_V0.1."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO = Path("/home/runner/work/personal-ai-cloud-execution-test/personal-ai-cloud-execution-test")
for path in (str(REPO / "src"), str(Path(__file__).resolve().parent)):
    if path not in sys.path:
        sys.path.insert(0, path)

from reality_canonical_writer import (  # noqa: E402
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
from personal_ai_execution.provenance_contract import (  # noqa: E402
    PROVENANCE_CONTRACT_VERSION,
    STATUS_VERIFIED as PROV_VERIFIED,
)
from personal_ai_execution.reality_capture import (  # noqa: E402
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
```

## Appendix C: Worked example output

```
$ python -m pytest -q test_reality_canonical_writer.py
19 passed in 0.04s

ELIGIBLE_AUDIT
{
  "candidate_id": "snap-42",
  "canonical_content_hash": "be0c274fa5c249968d8bee2501ddd1815768b73d557a85d61028bec9917f05a1",
  "capture_contract": "PERSONAL_AI_REALITY_CAPTURE_NORMALIZATION_V0.1",
  "content_hash": "sha256:be0c274fa5c249968d8bee2501ddd1815768b73d557a85d61028bec9917f05a1",
  "contract": "PERSONAL_AI_REALITY_CANONICAL_WRITER_V0.1",
  "eligible": true,
  "hash_checked": true,
  "hash_match": true,
  "provenance_contract": "PERSONAL_AI_ASSET_PROVENANCE_V0.2",
  "provenance_status": "VERIFIED",
  "reasons": [],
  "source_identity": "wechat:conversation:42",
  "status": "ELIGIBLE",
  "target_asset_type": "KNOWLEDGE"
}

PREPARED_PLAN (abridged)
{
  "canonical_store": "ASSET_DB:assets/asset_versions",
  "idempotency_key": "knowledge:snap-42:be0c274f...f05a1",
  "intent_hash": "a0b0df75c68dffbeeb63b00f65d5fa02fa6ccafae074e9cad1c387d4a40f2ff8",
  "phase": "PREPARE",
  "production_write_performed": false,
  "reality_role": "SOURCE_PROVENANCE",
  "reused_canonical_writer": "writeKnowledgeCandidate",
  "reused_writer_contract": "PERSONAL_AI_KNOWLEDGE_CANDIDATE_WRITER_V0.1",
  "second_state_store_created": false,
  "source_asset_type": "REALITY",
  "status": "PREPARED",
  "target_asset_type": "KNOWLEDGE"
}

FIRST_PROMOTION_STATUS PROMOTED
REPEAT_PROMOTION_STATUS IDEMPOTENT
WRITE_SURFACE_CALLS 1

AUTHORIZED_BUT_NO_SURFACE_STATUS BLOCKED
AUTHORIZED_BUT_NO_SURFACE_REASONS [
  "blocked: no production write surface available -- provide the existing
   Personal AI Canonical write surface bound to the production ASSET_DB
   (dependency: Cloudflare ASSET_DB binding + authorized MCP invocation);
   no second state store is created"
]
```
