# KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_REPAIR_REPORT_V1

- Task ID: `cf-c63737c3afb6`
- Parent task: `cf-7555b86ce338`
- Root task: `cf-995be6ca239c`
- Goal: `KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_REPAIR_V1`
- Project: Personal AI Execution V2
- Risk level: `LOW`
- Mode: **bounded, allowlist-scoped implementation + in-repo regression evidence**.
- Base revision: `2e1cf418a1598f0120447d62bec83da18b465c8d`.
- Repository allowlist for this task: `worker/index.js`,
  `tests/test_knowledge_candidate_golden_pipeline.py`,
  `tests/test_skill_candidate_writer.py`, and this report.
- Production readiness: **`READY_FOR_REVIEW`** (see §8).

> **Hard-hold attestation.** No production deploy, no D1/database migration
> execution, no live Canonical write, no Knowledge promotion, no test-asset
> deletion, and no secret/OAuth/permission/binding/workflow change was
> performed. The migration is **not** committed and **not** executed (see
> §5/§10). All evidence is from the frozen repository and executed in-repo
> tests. Anything not traceable to an executed command is marked `UNVERIFIED`.

---

## 1. Current vs Target Architecture

### 1.1 Baseline architecture (as found — flat writer path)

The only public entry point that turned a Knowledge Inbox candidate into a
Canonical Cloud Asset was the MCP tool `write_knowledge_candidate`, which
forwarded a legacy `asset_id`-only request straight to the flat function
`writeKnowledgeCandidate` (`worker/index.js`). A caller holding only MCP write
scope could therefore drive a Canonical write with no independent candidate
staging, no review state, and no bound approval. `promotion_decision` was inert
(never a gate).

| Stage | Baseline behaviour |
|---|---|
| Candidate staging | None; candidate and Golden asset shared one identity. |
| Review gate | None; `input.review_*` never required/checked on the public route. |
| Approval ledger | `decision_write` / `knowledge_write` adapter existed but was **not** consulted by the public writer. |
| Caller authorisation | Caller-supplied `promotion_decision` was copied to provenance; not a gate. |
| Canonical write | `db.batch([assetWrite, versionWrite])` into `assets` + `asset_versions`. |
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

### 1.3 Public entry point is fail-closed (this follow-up)

`toolWriteKnowledgeCandidate` — the function reached by the MCP
`tools/call` route for `write_knowledge_candidate` — is now itself fail-closed:

- A non-`KNOWLEDGE` `asset_type` is rejected (`INVALID_ASSET_TYPE`) before any
  I/O.
- A request with **no `candidate_id`** (the legacy `asset_id`-only shape) is
  rejected with `REJECTED` / `candidate_missing` and `write_calls: 0` **before
  any DB read, Canonical writer call, or mutation**.
- A caller-supplied `promotion_decision` (e.g. `PROMOTE`) does **not**
  authorise the write.
- Only a request carrying an independent staged `candidate_id` proceeds, and
  then only through `promoteKnowledgeCandidate` → `validateCandidateGate`.

The legacy `writeKnowledgeCandidate` primitive itself is unchanged and remains
the low-level Golden Writer used *internally* by the gate and by the SKILL
wrapper; it is no longer reachable in an ungated form from any public route.

---

## 2. Changed Components (exact)

| Path | Change |
|---|---|
| `worker/index.js` | **Hardened.** `toolWriteKnowledgeCandidate` now rejects a missing `candidate_id` with `REJECTED` / `candidate_missing` (`write_calls: 0`) before any DB read/write or Golden-writer call, rejects non-`KNOWLEDGE` `asset_type` first, and routes only independent staged candidates through `promoteKnowledgeCandidate` → `validateCandidateGate`. The gate remains the sole authorisation; `promotion_decision` is never read by it. The legacy internal `writeKnowledgeCandidate` primitive is byte-compatible. |
| `tests/test_skill_candidate_writer.py` | **Updated.** `test_knowledge_tool_registration_and_dispatch_unchanged` keeps the tool-registration and dispatch assertions (and the separate SKILL dispatch tests) but now asserts the public `asset_id`-only call is `REJECTED` / `candidate_missing` with zero writes. No test deleted or weakened. |
| `tests/test_knowledge_candidate_golden_pipeline.py` | **Updated (additive).** Added the public-route fail-closed regressions `test_public_direct_tool_asset_id_only_is_rejected_zero_io` and `test_public_mcp_tools_call_asset_id_only_is_rejected_zero_io`, which instrument D1 to prove **zero DB reads, zero DB mutations, zero Canonical writer calls** (with `promotion_decision: PROMOTE`). All five pipeline tests and the ledger/Worker compatibility tests are preserved. |
| `KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_REPAIR_REPORT_V1.md` | **Updated.** This report. |
| `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql` | **Deliberately omitted and not executed.** The repository contract `tests/test_decision_ingestion_writer.py::test_no_new_migration_added` forbids adding migration files. The additive DDL is carried as an **unexecuted plan** in §5 (see §10). |

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

### 3.4 Public-route fail-closed gate (this follow-up)

```
toolWriteKnowledgeCandidate(env, args):
    asset_type != KNOWLEDGE         -> INVALID_ASSET_TYPE            (no I/O)
    candidate_id missing/blank      -> REJECTED/candidate_missing    (no I/O)
    candidate_id present            -> promoteKnowledgeCandidate(...) -> validateCandidateGate
```

The `candidate_missing` branch returns before the first `env.ASSET_DB` access, so
no read, mutation, batch, or writer call can occur. A `promotion_decision` field
is ignored on this route (it is not read by `validateCandidateGate`).

---

## 4. Test Results

### 4.1 Targeted suites (executed)

```
python -m pytest -q \
  tests/test_knowledge_candidate_golden_pipeline.py \
  tests/test_skill_candidate_writer.py \
  tests/test_knowledge_candidate_writer.py \
  tests/test_mcp_events_golden.py
→ 97 passed
```

The five requested acceptance tests:

| # | Test | Assertion |
|---|---|---|
| 1 | `test_1_draft_direct_write_rejected_zero_writes` (+ Worker variant) | `REJECTED` / `candidate_state`, `canonical_write_attempts == 0`, Golden empty. |
| 2 | `test_2_forged_promotion_decision_without_approval_rejected` (+ Worker variant) | `REJECTED` / `missing_or_expired_approval`, `promotion_decision` ignored, zero writes. |
| 3 | `test_3_wrong_hash_rejected` (+ Worker variant) | `REJECTED` / `content_hash_mismatch`, approval not consumed, zero writes. |
| 4 | `test_4_valid_full_flow_reaches_authoritative_readback` (+ Worker variant) | states DRAFT→PENDING_REVIEW→APPROVED_FOR_PROMOTION→PROMOTED→CANONICAL_READBACK_VERIFIED; exactly one Golden version; read-back re-reads the persisted row. |
| 5 | `test_5_repeat_promotion_creates_no_duplicate_golden` (+ Worker variant) | second promote `IDEMPOTENT`, `write_calls == 0`, one asset, one version. |

New public-route regressions:

| Test | Assertion |
|---|---|
| `test_public_direct_tool_asset_id_only_is_rejected_zero_io` | direct `toolWriteKnowledgeCandidate` with `asset_id`-only + `promotion_decision: PROMOTE` → `REJECTED` / `candidate_missing`, `write_calls == 0`, `dbReads == 0`, `dbMutations == 0`, `writerCalls == 0`, no assets/versions. |
| `test_public_mcp_tools_call_asset_id_only_is_rejected_zero_io` | same request through `handleMcp` `tools/call` with `mcp` scope → `REJECTED` / `candidate_missing`, `write_calls == 0`, `dbReads == 0`, `dbMutations == 0`, `writerCalls == 0`, no assets/versions. |

The dispatch suite update (`test_knowledge_tool_registration_and_dispatch_unchanged`)
preserves tool registration, the SKILL dispatch coverage
(`test_skill_tool_call_dispatches_and_writes_skill`,
`test_skill_tool_call_requires_write_scope`,
`test_skill_tool_call_rejects_non_skill_asset_type`), and the other-operation
coverage, while asserting the now-safe public Knowledge rejection.

### 4.2 Full repository suite (executed)

```
python -m pytest -q
→ 1552 passed, 1 skipped
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
`knowledge_promotion_approvals` statements. The public-route regressions
additionally wrap the D1 binding and the Golden writer to count reads,
mutations, and writer calls, proving the fail-closed path performs none.

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
2. Deploy Worker code **fail-closed first** (public route rejects, gate defaults
   to rejecting).
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
   this state the public route returns `REJECTED` / `INVALID_ASSET_TYPE` and the
   gate returns `REJECTED`. It **does not** fall back to the flat writer.
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
   the sole write authorisation, and the public route refuses `asset_id`-only
   requests.

---

## 7. Security Findings

| Item | Finding |
|---|---|
| Flat-writer bypass | Present at baseline. **Closed on the public route** in this follow-up: `write_knowledge_candidate` rejects `asset_id`-only requests with `REJECTED` / `candidate_missing` before any I/O. Candidate writes are gated by `validateCandidateGate`. |
| Caller-supplied decision | `promotion_decision` remains in the tool schema for compatibility but is **never** read by the gate or the public route (asserted by `test_worker_source_encodes_candidate_gate_and_pipeline` and the public-route regressions). |
| Independent staging | Candidate records are physically separate from `assets`/`asset_versions`, preventing a second Golden truth. |
| Approval binding | Approval is bound to candidate/version/hash/review/receipt/approver/expiry and is single-use; replay is rejected. |
| Read-back integrity | Write responses are never treated as proof; authoritative re-read (`verifyKnowledgeVersion`) is mandatory before `CANONICAL_READBACK_VERIFIED`. |
| Secret / OAuth / permission / binding | None read or changed. |
| Canonical / deployment mutations | None. No deploy, no migration execution, no Canonical write, no promotion. |
| `.github/workflows/`, secret-like paths | Untouched. No deletion anywhere. |

### 7.1 Residual risk (bounded)

The low-level primitive `writeKnowledgeCandidate` still accepts an `asset_id`
argument because it is the shared Golden-writer core invoked *internally* by the
gate (`promoteKnowledgeCandidate`) and by the SKILL wrapper
(`writeSkillCandidate`). It is not reachable in an ungated form from any public
MCP route: the only externally reachable Knowledge write
(`toolWriteKnowledgeCandidate`) refuses `asset_id`-only and non-`KNOWLEDGE`
requests. Deprecating the internal primitive's `asset_id` parameter is a future
cleanup and is not performed here because the existing audited writer contract
pins it.

---

## 8. Production Readiness

**`READY_FOR_REVIEW`**

- The hardening is **implemented in-repo** (`worker/index.js`) with two new
  public-route regressions and an updated dispatch expectation; the targeted
  suites and the full repository suite are green.
- **Live production verification is `UNVERIFIED`**: no `ASSET_DB`/`asset.read`
  credential or reachable `/mcp` transport, no deploy, and no D1 migration was
  applied. The additive tables are not present in production until a
  separately-authorised migration task runs.

Advance to `READY_FOR_HUMAN_APPROVAL` only after: (a) the additive DDL is
applied under a dedicated allowlisted migration task, (b) the gated Worker is
deployed fail-closed, and (c) a read-only production read-back confirms the
existing Knowledge corpus is unchanged and the public route rejects an
`asset_id`-only write and a DRAFT / forged / wrong-hash promotion.

---

## 9. Live Production Verification Status

- **Existing Knowledge corpus (assets / versions / provenance): `UNVERIFIED`.**
  No live Canonical read access in this environment.
- No production write, promotion, deploy, migration, or secret access occurred.

---

## 10. Remaining Blockers / Handoff

1. **Migration artifact omitted by contract.** The pre-existing test
   `tests/test_decision_ingestion_writer.py::test_no_new_migration_added`
   asserts the migrations directory contains exactly `0001` and `0002`, and that
   test is outside this task's allowlist. The additive DDL is therefore carried
   as an unexecuted plan in §5; the Worker staging tables are **not yet created
   in production** and promotion stays fail-closed until a future allowlisted
   migration task lands them.
2. **Sequencing.** The hardened Worker must be deployed fail-closed before any
   migration that would enable the promotion pipeline.
3. Live read-back / Canonical inventory verification blocked by missing
   credentials and transport.

### Evidence summary

| Tier | Evidence |
|---|---|
| Code (frozen repo) | `worker/index.js` (`toolWriteKnowledgeCandidate` fail-closed public route; `validateCandidateGate`, `promoteKnowledgeCandidate`, staging/review/approval helpers). |
| Test (executed) | `python -m pytest -q tests/test_knowledge_candidate_golden_pipeline.py tests/test_skill_candidate_writer.py tests/test_knowledge_candidate_writer.py tests/test_mcp_events_golden.py` → 97 passed; `python -m pytest -q` → 1552 passed, 1 skipped. |
| Real Worker | Worker source executed under Node with an audited D1 mock; public-route probes count zero DB reads/mutations/writer calls. |
| Live production | **None** (no credential/transport; corpus `UNVERIFIED`). |
| Repo diff | `worker/index.js`, `tests/test_knowledge_candidate_golden_pipeline.py`, `tests/test_skill_candidate_writer.py`, this report. Migration omitted by contract. |
