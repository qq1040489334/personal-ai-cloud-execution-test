# PERSONAL_AI_DECISION_INGESTION_WRITER_SPEC_V0.1

Specification for the minimal **DECISION writer** that persists already-normalized
`PERSONAL_AI_DECISION_INGESTION_V0.1` records into the **existing canonical
DECISION asset path** (`assets` / `asset_versions`, `asset_type = 'DECISION'`).

This document is **specification + test specification only**. It performs **no
production write, no deploy, no D1 mutation, no credential/OAuth/security/binding
change, no `.github/workflows/` change and no PersonOS/Curator/Inbox restoration**.
The writer implementation and the first production DECISION Golden write are
explicitly **out of scope** and require a separate, later Human Gate.

- Task id: `cf-60656d12bd7a`
- Risk level: `LOW`
- Contract version: `PERSONAL_AI_DECISION_WRITER_V0.1`
- Depends on: `DECISION_INGESTION_CONTRACT_V0.1.md`,
  `ASSET_PROVENANCE_CONTRACT_V0.2.md`, `CLOUDFLARE_WORKER_CANONICAL_DEPLOY_V0.2.md`
- Precedent (same canonical path, non-DECISION): `writeKnowledgeCandidate`
  (`PERSONAL_AI_KNOWLEDGE_CANDIDATE_WRITER_V0.1`, `worker/index.js`)

---

## 1. Scope and non-goals

### 1.1 In scope (specified here, implemented later)

- One minimal, audited writer that turns a **normalized, `VERIFIED` DECISION
  record** into one versioned canonical DECISION asset.
- Reuse of the **existing** canonical asset storage and read path: the D1
  `assets` / `asset_versions` tables behind `ASSET_DB`, the existing
  `ASSET_PROVENANCE_V0.2` provenance evaluator, and the existing `get_asset` /
  `search_assets` read tools.
- Payload validation, idempotency/dedup, provenance/audit fields,
  error/status semantics and a read-back acceptance contract.
- The concrete regression test plan an implementation must satisfy.

### 1.2 Explicit non-goals

- No new state store, no new canonical table, no second provenance vocabulary.
- No new general "agent platform", no PersonOS / Curator / Inbox resurrection.
- No production write or deployment in this task; no D1/DECISION record written.
- No credential, secret, OAuth, security, binding or workflow change.
- No UI automation or local-device operation.
- No change to `mark_reviewed`, `submit_task`, dispatch, or `worker/index.js`.

### 1.3 Reused canonical components (single source of truth)

| Concern | Existing component (reused as-is) |
| --- | --- |
| Canonical DECISION storage | D1 `assets` + `asset_versions` (`worker/migrations/`), `asset_type = 'DECISION'` |
| Canonical read path | `get_asset`, `search_assets` (`worker/index.js`) |
| Provenance contract | `ASSET_PROVENANCE_V0.2` (`evaluateAssetProvenance` / `src/personal_ai_execution/provenance_contract.py`) |
| Decision normalization | `PERSONAL_AI_DECISION_INGESTION_V0.1` (`src/personal_ai_execution/decision_contract.py`) |
| Review verdict vocabulary | `status_contract.REVIEW_VERDICTS` = `PASS` / `FAIL` / `BLOCKED` |
| Dispatch-outcome vocabulary | `advancement` `PENDING` / `DISPATCHED` / `FAILED` (also `task_dispatch_markers.dispatch_state`) |
| Asset-type vocabulary | `ASSET_TYPES` = `KNOWLEDGE` / `SKILL` / `REALITY` / `DECISION` |
| Promotion status CHECK | `assets.status IN (staging, accepted, superseded, retired)` |

`ASSET_TYPES` already contains `DECISION`, and `search_assets` already documents
`decision` as a canonical asset type. The writer therefore adds **no new
storage**, only the controlled entry point that appends DECISION versions.

---

## 2. Minimal writer interface

### 2.1 Function and tool surface

```
writeDecisionRecord(env, input) -> { isError, text, structuredContent? }   # worker
toolWriteDecisionRecord(env, args) -> { isError, text, structuredContent? }
write_decision_record                                                        # MCP tool name
```

- Runs only when `env.ASSET_DB` is the canonical D1 binding; otherwise
  `ASSET_WRITE_UNAVAILABLE`.
- The MCP tool is write-only and **must** require the write scope
  (`hasWriteScope(auth)`); the read tools stay read-only.
- The writer is the **only** entry point allowed to persist `asset_type =
  'DECISION'`; it never writes any other asset type.
- The writer accepts **only** an input that already normalizes to `VERIFIED`
  under `normalize_decision`; it never invents missing decision evidence.

### 2.2 Input payload (canonical decision content)

The payload maps 1:1 onto the canonical DECISION shape of
`DECISION_INGESTION_CONTRACT_V0.1` plus the explicit agent/user decision fields
needed to keep recommendation, human choice/override and later outcome distinct.

| Field | Meaning | Required |
| --- | --- | --- |
| `decision_id` | stable DECISION identity; defaults to `task_id` | yes (present after default) |
| `task_id` | task the decision belongs to | yes |
| `review_verdict` | human verdict (`PASS` / `FAIL` / `BLOCKED`) | yes |
| `dispatch_outcome` | `PENDING` / `DISPATCHED` / `FAILED` | yes |
| `promotion_decision` | provenance promotion decision (e.g. `PROMOTE`) | yes |
| `promotion_event` | append-only promotion event id | yes |
| `agent_recommendation` | the agent's proposed choice/verdict | yes |
| `user_choice` | the human's **final** choice | yes |
| `user_outcome` | observed outcome of that choice | yes |
| `user_override` | `true` iff `user_choice != agent_recommendation` | derived (never caller-invented) |
| `override_reason` | required when `user_override` is `true` | conditional |
| `outcome_feedback` | later feedback/outcome linkage (append-only) | optional |
| `decided_at` | when the decision was recorded | yes |
| `evidence_ref` | reference to the source registry/event record | yes |
| `supersedes` | prior DECISION version(s) this version supersedes | derived |
| `actor` / `created_by` | who authored the canonical version | yes (default `cloud-agent`) |

`user_override`, `supersedes` and `superseded_by` are **derived by the writer**,
never trusted from the caller. A caller-supplied value that contradicts the
derived value is rejected (`INVALID_OVERRIDE`).

### 2.3 Canonical persisted content

- `asset_id` = `decision:<decision_id>` (validated against `ASSET_ID_RE`).
- `assets.asset_type` = `DECISION`; `assets.status` = `accepted` on promotion
  (never the legacy `ACTIVE`); `assets.current_version` points at the new version.
- `asset_versions.content` = canonical JSON of the decision content
  (`content_hash = sha256(canonical_json(content))`, raw 64-char lowercase hex in
  **both** `assets.content_hash` and `asset_versions.content_hash`).
- `asset_versions.provenance` = an `ASSET_PROVENANCE_V0.2` record;
  `asset_versions.verification` = its `verification` block.
- `asset_versions.created_by` is NOT NULL and non-empty.

---

## 3. Payload validation (fail-closed)

Validation is strict and runs **before** any write; a rejected payload writes
nothing and leaves no partial row.

| Condition | Result | Error text |
| --- | --- | --- |
| `ASSET_DB` binding missing | reject | `ASSET_WRITE_UNAVAILABLE` |
| input is not an object / array | reject | `INVALID_INPUT` |
| `asset_type` present and `!= DECISION` | reject | `INVALID_ASSET_TYPE` |
| `asset_id` / `decision_id` empty, unsafe or not `ASSET_ID_RE` | reject | `INVALID_ASSET_ID` |
| `task_id` empty | reject | `INVALID_TASK_ID` |
| `review_verdict` not in `REVIEW_VERDICTS` | reject | `INVALID_REVIEW_VERDICT` |
| `dispatch_outcome` not in dispatch vocabulary | reject | `INVALID_DISPATCH_OUTCOME` |
| `promotion_decision` / `promotion_event` empty | reject | `INVALID_PROMOTION` |
| `agent_recommendation` empty | reject | `INVALID_AGENT_RECOMMENDATION` |
| `user_choice` empty | reject | `INVALID_USER_CHOICE` |
| `user_outcome` empty | reject | `INVALID_USER_OUTCOME` |
| `user_choice != agent_recommendation` and `override_reason` empty | reject | `INVALID_OVERRIDE_REASON` |
| caller `user_override` contradicts derived override | reject | `INVALID_OVERRIDE` |
| `decided_at` empty / not parseable | reject | `INVALID_DECIDED_AT` |
| `evidence_ref` empty | reject | `INVALID_EVIDENCE_REF` |
| `normalize_decision(input).status != VERIFIED` | reject | `INCOMPLETE_DECISION` |
| canonical hash not 64 lowercase hex | reject | `ASSET_WRITE_FAILED` |

Rules:

- **No fabrication**: missing decision evidence is never defaulted; the exact
  missing fields from `normalize_decision` are surfaced in the error detail.
- **No mutation**: the input mapping is never mutated.
- **No partial write**: validation completes before the D1 batch is opened.

---

## 4. Idempotency / dedup

- **Dedup key**: canonical `asset_id` (`decision:<decision_id>`), with a fast
  path keyed on the canonical `content_hash` of the decision content.
- **Idempotent replay**: if `assets` already holds a row whose
  `content_hash` equals the recomputed hash, the writer performs the mandatory
  read-back verification (`verifyDecisionVersion`). Only a genuine
  `accepted`, `VERIFIED` current version short-circuits to
  `status = IDEMPOTENT` (`idempotent = true`, `created = false`, no new version).
  Any other stored state fails closed (`ASSET_WRITE_FAILED`).
- **New version**: if the stored decision content differs, the writer appends a
  new `asset_versions` row (`version = previous_version + 1`), records
  `supersedes = [<previous_version>]` (merged with any caller lineage), and
  updates `assets` pointer + `assets.status = accepted` in a **single D1 batch**.
- **Exactly-once promotion**: the promotion `event_id` is stable and derived
  from `decision_id` + `canonical_version`, so replaying the same decision never
  emits a second promotion event for the same version.
- **Atomicity**: `assets` pointer and `asset_versions` row are written in one
  `db.batch`. If batch is unavailable or throws, the writer fails closed and
  leaves no half-written pointer.
- **Read-back required**: the writer may never report `WRITTEN` / `IDEMPOTENT`
  unless `verifyDecisionVersion` confirms the canonical version row matches the
  expected version, content, hash, status, `created_by` and verified provenance.

---

## 5. Provenance / auditability

Each persisted DECISION version carries an `ASSET_PROVENANCE_V0.2` record that
`evaluateAssetProvenance` evaluates to `VERIFIED`:

- `source.identity` = the originating registry/event reference (`evidence_ref`);
- `source.location` = canonical DECISION path identifier;
- `source_version` / `content_version` = the decision revision;
- `canonical_version` = the appended version;
- `content_hash` = recomputed canonical hash (agrees with verification evidence);
- `verification.evidence` = recomputed hash + writer identity + `verified_at`;
- `verification.content_hash_matches = true`;
- `promotion` = `{decision: <promotion_decision>, event_id: <promotion_event>,
  decided_at: <decided_at>, actor: <created_by>}`;
- `captured_at` / `promoted_at`;
- `supersedes` / `superseded_by` lineage.

Audit requirements:

- The `user_choice`, `user_override`, `override_reason` and `user_outcome` are
  persisted **inside** the canonical content so the human's final decision is
  always distinguishable from the agent recommendation after the fact.
- Later `outcome_feedback` is append-only: it creates a **new version** rather
  than mutating a promoted version.
- Every version records `created_by` and `created_at`; the append-only
  `asset_versions` history is the audit trail.
- The writer never marks `historical_provenance_incomplete = false` unless the
  provenance actually evaluates `VERIFIED`.

---

## 6. Error / status semantics

Success statuses:

| Status | `isError` | Meaning |
| --- | --- | --- |
| `WRITTEN` | false | a new canonical DECISION version was appended and read back |
| `IDEMPOTENT` | false | identical content already present and verified; nothing written |

Success result (`structuredContent`):

```
{
  "contract": "PERSONAL_AI_DECISION_WRITER_V0.1",
  "asset_id", "asset_type": "DECISION", "schema_version", "title",
  "status": "WRITTEN" | "IDEMPOTENT",
  "created", "idempotent", "version", "previous_version",
  "content_hash", "provenance_status": "VERIFIED", "provenance_verified": true,
  "promotion_event", "supersedes",
  "user_override", "user_choice", "agent_recommendation",
  "updated_at"
}
```

Failure error codes (all `isError = true`, `text = <CODE>`):

`ASSET_WRITE_UNAVAILABLE`, `INVALID_INPUT`, `INVALID_ASSET_TYPE`,
`INVALID_ASSET_ID`, `INVALID_TASK_ID`, `INVALID_REVIEW_VERDICT`,
`INVALID_DISPATCH_OUTCOME`, `INVALID_PROMOTION`,
`INVALID_AGENT_RECOMMENDATION`, `INVALID_USER_CHOICE`, `INVALID_USER_OUTCOME`,
`INVALID_OVERRIDE_REASON`, `INVALID_OVERRIDE`, `INVALID_DECIDED_AT`,
`INVALID_EVIDENCE_REF`, `INCOMPLETE_DECISION`, `ASSET_WRITE_FAILED`.

Fail-closed guarantees: unknown/unrecognized values are never coerced to a
valid one; a failed batch, an ignored version INSERT, a missing `created_by`, a
non-`accepted` status, an incomplete provenance or a hash mismatch all return
`ASSET_WRITE_FAILED` and never `WRITTEN` / `IDEMPOTENT`.

---

## 7. Read-back acceptance contract

A DECISION write is accepted only when all of the following hold via the
existing canonical read path:

1. `get_asset(decision:<id>)` returns the current version with `asset_type =
   DECISION` and `status = accepted`.
2. The returned `content` equals the canonicalized decision content, and
   `content_hash` equals the recomputed 64-char lowercase hash.
3. `provenance_status = VERIFIED`, `provenance_verified = true`,
   `historical_provenance_incomplete = false`.
4. `search_assets(asset_type = 'decision')` lists the asset with
   `provenance_verified = true`.
5. The provenance read back satisfies `evaluate_provenance(...)` with
   `status = VERIFIED`, `missing = []`, `hash_match = true`.
6. The audit fields `agent_recommendation`, `user_choice`, `user_override`,
   `override_reason` (when overridden), `user_outcome` and `evidence_ref`
   round-trip intact.

---

## 8. Decision coverage

| Decision path | Required evidence | Persisted distinction |
| --- | --- | --- |
| Agent recommendation / decision | `agent_recommendation`, `review_verdict`, `dispatch_outcome`, `promotion_decision` | recommendation stored verbatim |
| User final choice | `user_choice`, `decided_at`, `evidence_ref` | `user_choice` is the final human choice |
| User override | `user_choice != agent_recommendation` + `override_reason` | `user_override = true` (derived), reason stored |
| Later outcome / feedback | `user_outcome`; later `outcome_feedback` | appended as a new version, never mutates history |

A DECISION cannot be written without the human final choice, the override reason
(if applicable) and the observed outcome -- matching the fail-closed
`PERSONAL_AI_DECISION_INGESTION_V0.1` requirement that an agent decision is never
canonical without the human decision and its outcome.

---

## 9. Test specification (regression plan)

The writer implementation is out of scope, so this section is the normative test
plan the implementation must satisfy. Tests follow the existing
`tests/test_knowledge_candidate_writer.py` pattern: execute the production Worker
under Node with a **constraint-enforcing** mocked `ASSET_DB` (status CHECK,
64-char lowercase hash, NOT NULL version `content_hash` / `created_by`), and read
back through `get_asset` / `search_assets`. Focused suite path:
`tests/test_decision_writer.py` (to be added with the implementation).

### 9.1 Source contract
- worker source encodes `PERSONAL_AI_DECISION_WRITER_V0.1`,
  `writeDecisionRecord`, `toolWriteDecisionRecord`, `"write_decision_record"`,
  `INSERT INTO asset_versions`, `INSERT INTO assets`, `UPDATE assets`,
  `ASSET_WRITE_UNAVAILABLE`, `INVALID_*`, `ASSET_WRITE_FAILED`,
  `canonicalDecisionContent`, `sha256Hex`, `verifyDecisionVersion`,
  `DECISION_WRITE_STATUS`, `created_by`.
- tool is registered and requires `hasWriteScope(auth)`; it advertises only
  `DECISION`.
- `DECISION_WRITE_STATUS === "accepted"` and `"ACTIVE"` is absent.

### 9.2 Validation / fail-closed (`test_invalid_inputs_fail_closed_and_write_nothing`)
Parametrized cases for every code in section 3, asserting `isError = true`,
exact error text, and that **no** `assets` / `asset_versions` row is written.
Plus: missing `ASSET_DB` -> `ASSET_WRITE_UNAVAILABLE`; non-object args rejected;
`normalize_decision(input) != VERIFIED` -> `INCOMPLETE_DECISION`.

### 9.3 Canonical persistence / hash / provenance
- `test_write_persists_canonical_decision_with_content_hash`
- `test_persisted_rows_satisfy_audited_production_constraints`
- `test_written_provenance_satisfies_canonical_verification` (evaluates
  `evaluate_provenance(...)` to `VERIFIED`)
- `test_written_provenance_reuses_asset_provenance_v0_2_contract`

### 9.4 Idempotency / dedup
- `test_identical_decision_is_idempotent_and_writes_no_new_version`
- `test_idempotent_replay_matches_on_normalized_hash`
- `test_new_decision_creates_a_new_version_and_supersedes_lineage`
- `test_stable_promotion_event_is_not_duplicated_on_replay`

### 9.5 Provenance / auditability + user choice/override
- `test_agent_recommendation_and_user_choice_are_both_persisted`
- `test_user_override_sets_flag_and_requires_reason`
- `test_user_override_rejects_contradicting_caller_flag`
- `test_missing_override_reason_is_rejected`
- `test_later_outcome_feedback_appends_new_version_without_mutating_history`

### 9.6 Fail-closed persistence
- `test_failed_version_insertion_rolls_back_and_fails_closed`
- `test_ignored_version_insertion_fails_closed_without_false_success`
- `test_batch_unavailable_fails_closed_before_writing_either_row`
- `test_idempotent_path_fails_closed_on_incomplete_provenance`
- `test_idempotent_path_fails_closed_on_hash_mismatch_provenance`
- `test_idempotent_path_fails_closed_on_non_accepted_status`
- `test_idempotent_path_fails_closed_on_missing_created_by`
- `test_idempotent_path_fails_closed_when_version_row_is_missing`
- `test_mock_enforces_the_audited_constraints`

### 9.7 Read-back / error semantics
- `test_written_decision_reads_back_through_get_asset`
- `test_written_decision_is_searchable_through_search_assets`
- `test_read_back_reports_verified_provenance_and_audit_fields`
- `test_read_back_rejects_missing_decision_asset`

### 9.8 Reuse guards (no architecture expansion)
- `test_decision_asset_type_is_already_canonical` (`ASSET_TYPES` contains
  `DECISION`; no new type added)
- `test_no_new_migration_added` (writer reuses existing `assets` /
  `asset_versions`; no new SQL migration file)
- `test_decision_ingestion_contract_is_reused` (`normalize_decision` /
  `REVIEW_VERDICTS` imported, not re-declared)
- `test_no_personos_or_curator_symbols_introduced`

### 9.9 This specification
- `test_spec_exists_and_documents_the_writer_contract` asserts this file exists
  and contains the key invariants (interface, validation, idempotency,
  provenance, error/status, read-back, Human Gate).

Focused command: `python -m pytest -q tests/test_decision_contract.py tests/test_decision_writer.py`
Full command: `python -m pytest -q`

---

## 10. What is deliberately not changed in this task

- No production write, deploy, D1 mutation or canonical DECISION/Golden record.
- No credential, secret, OAuth, security, binding or production-config change.
- No `.github/workflows/` change and no workflow dispatch.
- No `worker/index.js` change, no new migration, no new asset type.
- No second state store and no PersonOS / Curator / Inbox resurrection.
- No UI automation or local-device operation.

## 11. Bounded next action

**Smallest safe next action:** implement
`tests/test_decision_writer.py` as the pure, non-production regression suite for
the interface defined here (Node + mocked constraint-enforcing `ASSET_DB`, no
binding to production), and only then, behind an explicit approval, implement
`writeDecisionRecord` behind the existing write scope.

**Human Gate:** **YES.** Implementing any production DECISION writer, or
performing the first production DECISION Golden write, is *not* authorized by
this specification task. That step requires a new, explicit Human Gate and a
separate task contract.

## Verdict: PASS (specification only)

A minimal, fail-closed DECISION writer contract now exists on paper, reusing the
existing canonical `assets` / `asset_versions` DECISION path, the
`ASSET_PROVENANCE_V0.2` provenance contract and the
`PERSONAL_AI_DECISION_INGESTION_V0.1` normalization contract -- with no
production write, deployment, credential change or architecture expansion.
