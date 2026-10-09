# KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_REPAIR_REPORT_V1

- Task ID: `cf-0b1c56efed85` (parent `cf-995be6ca239c`)
- Goal: `KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_REPAIR_V1`
- Project: Personal AI Execution V2
- Risk level: `LOW`
- Mode: **bounded, allowlist-scoped implementation + in-repo regression evidence**.
- Repository allowlist for this task: `worker/index.js`, `hello.py`,
  `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql` (optional),
  `tests/test_knowledge_candidate_golden_pipeline.py`, and this report.
- Production readiness: **`READY_FOR_REVIEW`** (see §8).

> **Hard-hold attestation.** No production deploy, no D1/database migration
> execution, no live Canonical write, no Knowledge promotion, no test-asset
> deletion, and no secret/OAuth/permission/binding/workflow change was
> performed. The migration is **not** committed (see §5/§10). All evidence is
> from the frozen repository and executed in-repo tests. Anything not traceable
> to an executed command is marked `UNVERIFIED`.

---

## 1. Current vs Target Architecture

### 1.1 Current architecture (as found — flat writer path)

The only entry point that turns a Knowledge Inbox candidate into a Canonical
Cloud Asset was the single function `writeKnowledgeCandidate`
(`worker/index.js`). It is a **flat candidate-to-Canonical writer**: a caller
holding only MCP write scope could drive a Canonical write with no independent
candidate staging, no review state, and no bound approval. `promotion_decision`
was inert (never a gate). `verifyKnowledgeVersion` provided a genuine
post-write read-back, but it ran *after* an ungated write.

| Stage | Baseline behaviour |
|---|---|
| Candidate staging | None; candidate and Golden asset shared one identity. |
| Review gate | None; `input.review_*` never required/checked. |
| Approval ledger | `decision_write` / `knowledge_write` adapter existed but was **not** consulted by the writer. |
| Caller authorisation | Caller-supplied `promotion_decision` was copied to provenance; not a gate. |
| Canonical write | `db.batch([assetWrite, versionWrite])` directly into `assets` + `asset_versions`. |
| Read-back | `verifyKnowledgeVersion` (authoritative), applied after an ungated write. |

### 1.2 Target architecture (implemented)

```
Candidate staging (independent D1 tables: knowledge_candidates)
        │  candidate_id, status, content, content_hash, version,
        │  provenance, created_at, review_state   (distinct from Golden)
        ▼
Review  ──PASS──►  status = APPROVED_FOR_PROMOTION
        ▼
Knowledge Promotion Approval Ledger  operation = KNOWLEDGE_PROMOTION
        │  binding: candidate_id, candidate_version, content_hash,
        │           review_result, approval_receipt, approved_by, expires_at
        ▼
validate_candidate_gate  (SOLE write authorisation)
        │   state == APPROVED_FOR_PROMOTION
        │   review_state == PASS and review_result == PASS
        │   recomputed == stored == supplied hash; version match
        │   valid, unexpired, single-use approval bound to same candidate
        │   caller-supplied promotion_decision is NOT an input
        ▼
Golden Writer  → existing assets / asset_versions (unchanged shape)
        ▼
Authoritative Canonical read-back (verifyKnowledgeVersion)
        ▼
PROMOTED → CANONICAL_READBACK_VERIFIED
```

Candidate states: `DRAFT`, `PENDING_REVIEW`, `APPROVED_FOR_PROMOTION`,
`PROMOTED`, `CANONICAL_READBACK_VERIFIED`. A failed gate returns `REJECTED`
with **zero** write attempts. Repeat promotion is idempotent and never duplicates
a Golden asset/version.

---

## 2. Changed Components (exact)

| Path | Change |
|---|---|
| `worker/index.js` | **Implemented.** Added `KNOWLEDGE_CANDIDATE_*` state vocabulary, `validateCandidateGate` (pure, sole authorisation; ignores `promotion_decision`), independent candidate staging (`stageKnowledgeCandidate`), review advancement (`recordKnowledgeCandidateReview`), candidate-bound promotion approval registration (`registerKnowledgePromotionApproval`), and the gated pipeline `promoteKnowledgeCandidate` (gate → single-use consume → existing Golden writer → authoritative read-back → state advance). `toolWriteKnowledgeCandidate` routes a staged `candidate_id` through the gate. The legacy `asset_id`-only Golden Writer is byte-compatible. |
| `hello.py` | **Implemented.** Added `KNOWLEDGE_PROMOTION` as an additive approval-ledger operation (`production_approval_ledger_schema(..., include_knowledge_promotion=True)`) bound to the seven required fields; added the independent candidate staging store (`new_knowledge_candidate_store`, `stage_knowledge_candidate`, `submit_knowledge_candidate_for_review`, `record_knowledge_candidate_review`), `validate_candidate_gate`, `promote_knowledge_candidate`, and `knowledge_candidate_promotion_ledger`. Existing `decision_write` / `knowledge_write` definitions and replay semantics are unchanged. |
| `tests/test_knowledge_candidate_golden_pipeline.py` | **New.** The five requested tests plus additive-ledger compatibility, existing-Knowledge preservation, worker source-contract, and real-Worker-under-Node gate/pipeline probes. |
| `KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_REPAIR_REPORT_V1.md` | **Updated.** This report. |
| `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql` | **Deliberately omitted.** The repository contract `tests/test_decision_ingestion_writer.py::test_no_new_migration_added` forbids adding migration files. Per the task instruction, the additive DDL is carried as an **unexecuted plan** in §5 instead of a committed artifact (see §10). |

### 2.1 Verified unchanged

- `assets` / `asset_versions` schema and existing KNOWLEDGE rows/data — untouched.
- Existing approval operations `decision_write` / `knowledge_write` — byte-identical
  definitions; first consume `ACCEPTED`, replay `REPLAY_REJECTED`; unknown op
  `unsupported_operation`.
- `.github/workflows/**`, secrets/tokens/credentials/`.env`/`.pem`/`.key` — untouched.
- No file was deleted.

---

## 3. Implementation Detail

### 3.1 Independent Candidate staging

`knowledge_candidates` (or the in-repo staging structure) is physically distinct
from the Golden `assets` / `asset_versions`. Fields: `candidate_id`, `status`,
`content`, `content_hash`, `version`, `provenance`, `created_at`, `review_state`
(plus `asset_id`/`title`). States are exactly the five required values.

### 3.2 Approval-ledger extension (`KNOWLEDGE_PROMOTION`)

Additive only. Each approval binds to `candidate_id`, `candidate_version`,
`content_hash`, `review_result` (`PASS`), `approval_receipt`, `approved_by`, and
`expires_at`. The schema is only emitted when `include_knowledge_promotion=True`,
so the pre-existing `include_knowledge_write` adapter and its tests are unchanged.

### 3.3 `validate_candidate_gate` (sole write authorisation)

Returns `ok` only when **all** hold; otherwise `{ok: false, reason}` and the
caller returns `REJECTED` before touching the Golden writer:

1. candidate exists and `status == APPROVED_FOR_PROMOTION`;
2. stored `review_state == PASS` **and** supplied `review_result == PASS`;
3. recomputed `sha256(content) == stored content_hash`;
4. `stored content_hash == supplied content_hash`;
5. `stored version == supplied candidate_version`;
6. a valid, unexpired, single-use `KNOWLEDGE_PROMOTION` approval bound to the same
   candidate/version/hash/review exists.

`promotion_decision` is never read by the gate. Failure paths (`candidate_state`,
`missing_or_expired_approval`, `content_hash_mismatch`, `candidate_version_mismatch`,
`stored_review_not_pass`, `review_not_pass`) all return `REJECTED` with
`write_calls == 0` / `canonical_write_attempts == 0`.

---

## 4. Test Results

### 4.1 New suite (executed)

```
python -m pytest -q tests/test_knowledge_candidate_golden_pipeline.py
→ 15 passed
```

The five requested acceptance tests:

| # | Test | Assertion |
|---|---|---|
| 1 | `test_1_draft_direct_write_rejected_zero_writes` (+ Worker variant) | `REJECTED` / `candidate_state`, `canonical_write_attempts == 0`, Golden empty. |
| 2 | `test_2_forged_promotion_decision_without_approval_rejected` (+ Worker variant) | `REJECTED` / `missing_or_expired_approval`, `promotion_decision` ignored, zero writes. |
| 3 | `test_3_wrong_hash_rejected` (+ Worker variant) | `REJECTED` / `content_hash_mismatch`, approval not consumed, zero writes. |
| 4 | `test_4_valid_full_flow_reaches_authoritative_readback` (+ Worker variant) | states DRAFT→PENDING_REVIEW→APPROVED_FOR_PROMOTION→PROMOTED→CANONICAL_READBACK_VERIFIED; exactly one Golden version; read-back re-reads the persisted row. |
| 5 | `test_5_repeat_promotion_creates_no_duplicate_golden` (+ Worker variant) | second promote `IDEMPOTENT`, `write_calls == 0`, one asset, one version. |

Plus `test_ledger_additive_and_backward_compatible`,
`test_existing_knowledge_golden_writer_unchanged`,
`test_worker_source_encodes_candidate_gate_and_pipeline`,
`test_no_new_migration_artifact_added_and_plan_documented`, and
`test_worker_gate_rejects_expired_and_consumed_approval`.

### 4.2 Full repository suite (executed)

```
python -m pytest -q
→ 1550 passed, 1 skipped
```

No collection errors. Existing `test_knowledge_candidate_writer.py`,
`test_skill_candidate_writer.py`, `test_mcp_events_golden.py` (tool count),
`test_decision_ingestion_writer.py::test_no_new_migration_added`, and all
`test_hello.py` Knowledge approval-ledger / Golden-write tests pass unchanged.

### 4.3 Real Worker execution

The Worker suite strips the ES `export` block and executes the production
`worker/index.js` under Node with a D1 mock that enforces the audited
constraints (`assets.status` CHECK, 64-hex hash, NOT NULL version
hash/created_by) and supports the additive `knowledge_candidates` /
`knowledge_promotion_approvals` statements. This proves the gate and the full
D1-backed promotion path, not just a model.

---

## 5. Migration Plan (NOT EXECUTED)

> Nothing in this section was applied. No D1 statement was run. No Canonical
> write occurred. This DDL is an unexecuted plan because the repository contract
> forbids committing new migration files (§10). **If** a future allowlisted task
> lifts that contract, the following additive DDL is the migration to add as
> `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql` (review/apply
> only with the gate deployed fail-closed):

```sql
-- Additive only. assets / asset_versions are NOT touched.
CREATE TABLE IF NOT EXISTS knowledge_candidates (
  candidate_id TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL,
  title TEXT,
  status TEXT NOT NULL CHECK (status IN (
    'DRAFT','PENDING_REVIEW','APPROVED_FOR_PROMOTION',
    'PROMOTED','CANONICAL_READBACK_VERIFIED')),
  content TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  version INTEGER NOT NULL,
  provenance TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  review_state TEXT NOT NULL DEFAULT 'NOT_REVIEWED'
    CHECK (review_state IN ('NOT_REVIEWED','PASS','FAIL'))
);

CREATE TABLE IF NOT EXISTS knowledge_promotion_approvals (
  approval_receipt TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL,
  candidate_version INTEGER NOT NULL,
  content_hash TEXT NOT NULL,
  review_result TEXT NOT NULL,
  approved_by TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  consumed INTEGER NOT NULL DEFAULT 0,
  consumed_at TEXT,
  created_at TEXT
);
```

Steps (none executed):

1. Add the two additive tables above. No change to `assets`, `asset_versions`,
   or existing KNOWLEDGE rows.
2. Deploy Worker code **fail-closed first** (gate defaults to rejecting).
3. No backfill. Existing Knowledge assets/versions/provenance are read-only.
4. Run the §4.1 regression suite against the real worker + a read-only
   production read-back confirming the existing corpus is byte-identical.
5. Emit counters for `REJECTED` (must correlate with zero writer calls) and
   read-back failures.

---

## 6. Rollback Plan

A rollback of this repair **must keep the writer gate enforced**. The prior flat
writer is the defect; restoring it is explicitly forbidden.

1. **Primary rollback — fail-closed flag.** Disable the promotion pipeline. In
   this state the Worker returns `REJECTED` / `ASSET_WRITE_FAILED` for promotion
   requests. It **does not** fall back to the flat writer.
2. **Code rollback.** Revert the Worker deploy to the *gated* baseline, never to
   the pre-repair flat writer. If the only available artefact is the flat writer,
   rollback means disabling the promotion path entirely (fail closed).
3. **Schema rollback.** Leave the additive `knowledge_candidates` and
   `knowledge_promotion_approvals` tables in place (nullable/unused). Do not drop
   them: dropping buys nothing and risks audit loss. If forced to drop, the gate
   then finds no candidate/approval and returns `REJECTED` — it never re-enables
   the bypass.
4. **Non-negotiable invariant.** At no point may a rollback restore or recommend
   the old flat candidate-to-Canonical bypass. `validate_candidate_gate` remains
   the sole write authorisation.

---

## 7. Security Findings

| Item | Finding |
|---|---|
| Flat-writer bypass | Present at baseline. Removed from the promotion path: staged `candidate_id` writes are gated by `validateCandidateGate`; a failed gate returns `REJECTED` before any Golden write. |
| Caller-supplied decision | `promotion_decision` remains in the tool schema for compatibility but is **never** read by the gate (asserted by `test_worker_source_encodes_candidate_gate_and_pipeline`). |
| Independent staging | Candidate records are physically separate from `assets`/`asset_versions`, preventing a second Golden truth. |
| Approval binding | Approval is bound to candidate/version/hash/review/receipt/approver/expiry and is single-use; replay is rejected. |
| Read-back integrity | Write responses are never treated as proof; authoritative re-read (`verifyKnowledgeVersion`) is mandatory before `CANONICAL_READBACK_VERIFIED`. |
| Secret / OAuth / permission / binding | None read or changed. |
| Canonical / deployment mutations | None. No deploy, no migration execution, no Canonical write, no promotion. |
| `.github/workflows/`, secret-like paths | Untouched. No deletion anywhere. |

### 7.1 Known limitation / residual risk (fail-closed)

The MCP tool `write_knowledge_candidate` and the internal
`writeKnowledgeCandidate` primitive still accept a legacy `asset_id`-only call
for backward compatibility (existing suites depend on it). That legacy path is
the low-level Golden Writer, not the candidate promotion path. Removing it is a
follow-up deprecation and is **not** performed here because the existing
regression contract pins it. This is reported explicitly rather than silently
bypassed; the new promotion path is the one the gate authorises.

---

## 8. Production Readiness

**`READY_FOR_REVIEW`**

- The repair is **implemented in-repo** (`worker/index.js`, `hello.py`) with the
  five requested tests plus compatibility/source-contract tests, all green.
- **Live production verification is `UNVERIFIED`**: no `ASSET_DB`/`asset.read`
  credential or reachable `/mcp` transport, no deploy, and no D1 migration was
  applied. The additive tables are not present in production until a
  separately-authorised migration task runs.

Advance to `READY_FOR_HUMAN_APPROVAL` only after: (a) the additive DDL is
applied under a dedicated allowlisted migration task, (b) the gated Worker is
deployed fail-closed, and (c) a read-only production read-back confirms the
existing Knowledge corpus is unchanged and the new pipeline rejects a DRAFT /
forged / wrong-hash promotion.

---

## 9. Live Production Verification Status

- **Existing Knowledge corpus (assets / versions / provenance): `UNVERIFIED`.**
  No live Canonical read access in this environment.
- No production write, promotion, deploy, migration, or secret access occurred.

---

## 10. Remaining Blockers / Handoff

1. **Migration artifact omitted by contract.** The task allowlist named
   `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql`, but the
   pre-existing test `tests/test_decision_ingestion_writer.py::test_no_new_migration_added`
   asserts the migrations directory contains exactly `0001` and `0002`. Adding
   the file would fail `python -m pytest -q`, and that test is outside this
   task's allowlist. Per the task instruction ("If an existing supported staging
   mechanism makes the migration unnecessary, omit the migration file and
   explain why"), the file is omitted and the full additive DDL is specified as
   an unexecuted plan in §5. The Worker staging tables therefore are **not yet
   created in production** and promotion stays fail-closed until a future
   allowlisted migration task lands them.
2. **Legacy `asset_id`-only writer** remains for backward compatibility (§7.1);
   deprecation is a follow-up.
3. Live read-back / canonical inventory verification blocked by missing
   credentials and transport.

### Evidence summary

| Tier | Evidence |
|---|---|
| Code (frozen repo) | `worker/index.js` (`validateCandidateGate`, `promoteKnowledgeCandidate`, staging/review/approval helpers); `hello.py` (`KNOWLEDGE_PROMOTION`, candidate pipeline). |
| Test (executed) | `python -m pytest -q tests/test_knowledge_candidate_golden_pipeline.py` → 15 passed; `python -m pytest -q` → 1550 passed, 1 skipped. |
| Real Worker | Worker source executed under Node with an audited D1 mock (gate + full D1-backed promotion + idempotent replay). |
| Live production | **None** (no credential/transport; corpus `UNVERIFIED`). |
| Repo diff | `worker/index.js`, `hello.py`, `tests/test_knowledge_candidate_golden_pipeline.py`, this report. Migration omitted by contract. |
