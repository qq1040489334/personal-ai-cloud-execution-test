# KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_REPAIR_REPORT_V1

- Task ID: `cf-995be6ca239c`
- Goal: `KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_REPAIR_V1`
- Project: Personal AI Execution V2
- Risk level: `LOW`
- Mode: **bounded, allowlist-scoped repair / architecture + test-plan evidence**.
- Repository allowlist for this task: `KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_REPAIR_REPORT_V1.md` **only**.
- Production readiness: **NOT_READY** (see §8).

> **Hard-hold attestation.** This task contract authorises modification of exactly one repository
> path: this report. No production deploy, no D1/database migration execution, no Canonical write,
> no Knowledge promotion, no test-asset deletion, and no secret/OAuth/permission/binding change was
> performed. The repair implementation, its D1 migration, and its regression tests are **specified
> and validated against a reference model** (§4.3) but deliberately **not executed in-repo**, because
> doing so would require creating/modifying files outside the task allowlist. The rollback plan
> (§6) can never re-enable the flat-writer bypass.

> **Evidence discipline.** Code/test evidence below is drawn from the frozen repository
> (`worker/index.js`, `hello.py`, `test_hello.py`, `tests/test_knowledge_candidate_writer.py`) and
> from a task-scoped reference model executed outside the repository (`/tmp`). **Live production
> evidence is absent**: this environment holds no `ASSET_DB`/`asset.read` credential and no reachable
> `/mcp` transport, and the worker was not deployed. Any statement that cannot be traced to a frozen
> artifact or an executed command is marked `UNKNOWN`/`UNVERIFIED`.

---

## 1. Current vs Target Architecture

### 1.1 Current architecture (as found — flat writer path)

The only entry point that turns a Knowledge Inbox candidate into a Canonical Cloud Asset is the
single function `writeKnowledgeCandidate` in `worker/index.js:2868`. It is a **flat
candidate-to-Canonical writer**: staging, review, approval and promotion are *not* separate states.

| Stage | Current behaviour | Source |
|---|---|---|
| Candidate staging | **None.** Candidate and Golden asset share one identity (`asset_id`/`candidate_id`). No independent staging record. | `worker/index.js:2875` |
| Review gate | **None.** `input.review_*` is never required or checked. | `worker/index.js:2868-2967` |
| Approval ledger | Separate adapter exists for `decision_write` + `knowledge_write` (`register`/`consume`, single-use, replay-rejected) but it is **not consulted by the writer**. | `hello.py:29030-29330` |
| Caller authorisation | Caller-supplied `promotion_decision` (schema exposes it at `worker/index.js:3359`) is copied into provenance (`worker/index.js:2831`); it is inert but also **not a gate** — a write proceeds with or without it. | `worker/index.js:2830-2835` |
| Canonical write | `db.batch([assetWrite, versionWrite])` writes `assets` + `asset_versions` directly. | `worker/index.js:2925-2945` |
| Auth on entry | MCP `hasWriteScope(auth)` only. | `worker/index.js:3455` |
| Read-back | `verifyKnowledgeVersion` re-reads the persisted version and verifies hash/status/provenance. This is genuine read-back, applied **after** an ungated write. | `worker/index.js:2842-2867`, `2946` |
| Idempotency | Matching `content_hash` on the existing asset short-circuits to `IDEMPOTENT`. | `worker/index.js:2894-2912` |
| Golden truth | The single `assets`/`asset_versions` pair is the only store. | `worker/index.js:2889-2946` |

**Defect.** A caller holding only MCP write scope can drive a Canonical write with no independent
candidate staging, no review state, and no bound approval. There is no `validate_candidate_gate`,
so nothing prevents a `DRAFT` candidate (or a forged `promotion_decision=PROMOTE`) from being
written. The existing approval ledger is not wired to the Knowledge writer.

### 1.2 Target architecture (specified, not executed in-repo)

```
Candidate staging (independent from Golden)
        │  candidate_id, status, content, content_hash, version,
        │  provenance, created_at, review_state
        ▼
Review  ──PASS──►  status = APPROVED_FOR_PROMOTION
        │
        ▼
Approval Ledger  operation = KNOWLEDGE_PROMOTION
        │  binding: candidate_id, candidate_version, content_hash,
        │           review_result, approval_receipt, approved_by, expires_at
        ▼
validate_candidate_gate  (SOLE write authorisation)
        │   state == APPROVED_FOR_PROMOTION
        │   review_result == PASS
        │   candidate/content hash match
        │   version match
        │   valid, unexpired approval bound to same candidate/version/hash/review
        │   caller-supplied promotion_decision is NOT an input
        ▼
Golden Writer  → existing assets / asset_versions (unchanged shape)
        ▼
Canonical read-back verification (authoritative, independent re-read)
        ▼
PROMOTED → CANONICAL_READBACK_VERIFIED
```

Required candidate states: `DRAFT`, `PENDING_REVIEW`, `APPROVED_FOR_PROMOTION`, `PROMOTED`,
`CANONICAL_READBACK_VERIFIED`. A failed gate returns `REJECTED` and makes **zero** Golden/Canonical
write attempts. Repeated promotion is idempotent and never duplicates a Golden asset. A write
response alone is never accepted as read-back proof (§4.3, scenario 4).

---

## 2. Changed Components

### 2.1 Changed in this task (exact)

| Path | Change |
|---|---|
| `KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_REPAIR_REPORT_V1.md` | **New.** This report. |

### 2.2 Verified unchanged (asserted against the working tree)

No diff was produced for any of the following (working tree is clean except this report):

- `worker/index.js` — flat writer left intact (not deployed, not edited).
- `worker/migrations/*` — no migration added or changed.
- `hello.py`, `test_hello.py` — approval-ledger adapter untouched.
- `tests/*` — no test added, changed, or deleted.
- `src/**`, `docs/**`, `outputs/**`, `reports/**`, `planner/**`, `scripts/**` — untouched.
- `.github/workflows/**`, secrets/tokens/credentials/`.env`/`.pem`/`.key` — untouched by construction.

### 2.3 Proposed components (NOT executed, listed for the implementation PR)

These are the exact components the repair must change, offered here as the implementation contract:

1. `worker/index.js`
   - Add candidate staging store/contract (`knowledge_candidates` shape; fields as §1.2).
   - Add `validate_candidate_gate(...)`; make `writeKnowledgeCandidate` call it before any write.
   - Remove reliance on caller-supplied `promotion_decision`; keep it inert (never an authorisation).
   - Keep `verifyKnowledgeVersion` as authoritative read-back; set `PROMOTED` only after it passes.
2. `hello.py` (approval-ledger module)
   - Extend supported operations with `KNOWLEDGE_PROMOTION`, bound to the seven fields in §1.2.
   - Preserve `decision_write` and `knowledge_write` definitions byte-identically.
3. `tests/test_knowledge_candidate_golden_pipeline.py` (new regression suite; **not created** here)
   - The five tests in §4.2 plus backward-compatibility assertions.

---

## 3. Implementation Specification (target)

### 3.1 Candidate staging model (independent from Golden)

```
candidate_id    string   stable id (distinct namespace from asset_id)
status          enum     DRAFT | PENDING_REVIEW | APPROVED_FOR_PROMOTION |
                         PROMOTED | CANONICAL_READBACK_VERIFIED
content         text/json
content_hash    string   sha256( canonical(content) ), 64 lowercase hex
version         integer  monotonically increasing per candidate
provenance      json     source identity/location, actor, captured_at
created_at      timestamp
review_state    string   NOT_REVIEWED | PASS | FAIL
```

Candidate records are held in a staging structure that is **not** `assets` / `asset_versions`.
Golden truth remains the single existing Canonical store.

### 3.2 Approval-ledger extension (`KNOWLEDGE_PROMOTION`)

Additive only. Each approval binds to:

| Field | Purpose |
|---|---|
| `candidate_id` | Which staged candidate |
| `candidate_version` | Which version |
| `content_hash` | Exact content authorised |
| `review_result` | Must be `PASS` |
| `approval_receipt` | Non-empty human/audit receipt id |
| `approved_by` | Non-empty approver identity |
| `expires_at` | Must be in the future at gate time |

Existing `decision_write` / `knowledge_write` operations remain single-use and replay-rejected,
with unchanged definitions.

### 3.3 `validate_candidate_gate` (sole write authorisation)

Returns `ok` only when **all** hold; otherwise `{ok: false, reason}` and the caller returns
`REJECTED` before touching the Golden writer:

1. candidate exists and `status == APPROVED_FOR_PROMOTION`;
2. stored `review_state == PASS` **and** supplied `review_result == PASS`;
3. `sha256(candidate.content) == candidate.content_hash`;
4. `candidate.content_hash == supplied content_hash`;
5. `candidate.version == supplied candidate_version`;
6. a valid, unexpired `KNOWLEDGE_PROMOTION` approval bound to the same
   candidate/version/hash/review exists.

`promotion_decision=PROMOTE` supplied by the caller is **not** read by the gate and can never
authorise a write.

---

## 4. Test Results

### 4.1 Existing regression suite (executed, in-repo)

Command:

```
python -m pytest -q
```

Outcome (this run):

```
1535 passed, 1 skipped in 59.17s
```

Relevant existing suites confirmed green:

| Suite | Tests | Role |
|---|---|---|
| `tests/test_knowledge_candidate_writer.py` | 30 | Flat Knowledge writer behaviour (baseline preserved) |
| `tests/test_skill_candidate_writer.py` | 26 | SKILL writer + Knowledge dispatch unchanged |
| `test_hello.py -k approval_ledger` | 10 | `decision_write` / `knowledge_write` ledger compatibility |
| Full collection | 1536 | No collection errors |

This is **code/test evidence** from the frozen repository, not live production evidence.

### 4.2 The five requested acceptance tests (specified)

Because their would-be path (`tests/test_knowledge_candidate_golden_pipeline.py`) is outside this
task's allowlist, these tests are **not merged**. They are specified exactly as required:

1. **DRAFT direct write is REJECTED with no asset created and zero writer calls.**
   Assert `status == REJECTED`, `reason == candidate_state`, `writer.write_calls == 0`,
   `assets == {}`.
2. **Forged `promotion_decision=PROMOTE` without approval is REJECTED.**
   Approved-for-promotion candidate, valid hash/version, no ledger approval,
   `promotion_decision="PROMOTE"` supplied → `status == REJECTED`,
   `reason == missing_or_expired_approval`, `writer.write_calls == 0`.
3. **Bad content hash is REJECTED.** Valid approval bound to the real hash, promotion driven with
   `content_hash = "0"*64` → `status == REJECTED`, `reason == content_hash_mismatch`,
   `writer.write_calls == 0`.
4. **Valid DRAFT → review PASS → approval → promotion → authoritative read-back PASS.**
   Assert terminal `status == CANONICAL_READBACK_VERIFIED`, candidate state advanced through all
   five states, exactly one Golden version created, read-back re-reads the persisted version row
   (hash + status match), not merely the write response.
5. **Repeating promotion does not create a duplicate Golden asset.**
   Second authorised promotion returns `idempotent == True`, `len(assets) == 1`,
   `len(versions) == 1`.

Plus: **other approval-ledger operations remain compatible** (unknown operation →
`unsupported_operation` rejection; `decision_write` / `knowledge_write` unchanged) and **existing
Knowledge asset/version/provenance fixtures are preserved** (`tests/test_knowledge_candidate_writer.py`
fixtures still pass unmodified).

### 4.3 Task-specific validation (reference model, executed outside the repo)

To provide executed evidence for the five behaviours **without** writing any file outside the
allowlist, a faithful reference model of §1.2–§3 was executed at
`/tmp/opencode/knowledge_pipeline_refmodel.py`. It is a *design/behaviour* model, not the production
worker.

Command and outcome:

```
python /tmp/opencode/knowledge_pipeline_refmodel.py   →  reference_model_all_passed: true
```

| Scenario | Result |
|---|---|
| 1. DRAFT direct write | REJECTED (`candidate_state`), writer_calls = 0 |
| 2. forged `promotion_decision=PROMOTE`, no approval | REJECTED (`missing_or_expired_approval`), writer_calls = 0 |
| 3. bad content hash | REJECTED (`content_hash_mismatch`), writer_calls = 0 |
| 4. valid full flow | `CANONICAL_READBACK_VERIFIED`, writer_calls = 1, read-back verified |
| 5. repeat promotion | idempotent, assets = 1, versions = 1 |
| compat: other ledger operations | `decision_write`/`knowledge_write` registered; unknown op rejected |

**Evidence limit.** This proves the specified state machine and gate semantics. It does **not**
prove the production `worker/index.js` implementation, because that code was intentionally not
modified or deployed.

---

## 5. Migration Plan (NOT EXECUTED)

> Nothing in this section was applied. No D1 statement was run. No Canonical write occurred.

1. **Additive schema — candidate staging.**
   Create `knowledge_candidates` with the §3.1 columns. Additive; **no** change to `assets`,
   `asset_versions`, or existing Knowledge rows.
2. **Additive schema — approval binding.**
   Create a `knowledge_promotion_approvals` view/table (or add nullable binding columns to the
   approval ledger) carrying the seven §3.2 fields keyed by `candidate_id`/`candidate_version`.
   Existing ledger rows are untouched; definitions for `decision_write` and `knowledge_write`
   remain byte-identical.
3. **Worker code rollout (behind a fail-closed flag).**
   Deploy the candidate store, `validate_candidate_gate`, and the gated Golden writer. Default the
   gate to *off = fail closed* (`ASSET_WRITE_FAILED`/`REJECTED`), never to the legacy bypass.
4. **Wire the writer.** `writeKnowledgeCandidate` must call the gate before any
   `db.batch(...)`. Remove `promotion_decision` from any authorising role.
5. **Backfill.** None. Existing Knowledge assets/versions/provenance are read-only and unchanged.
6. **Verification.** Run the §4.2 regression suite; read back existing assets and assert byte-level
   equality of `assets`/`asset_versions` counts, hashes and provenance against pre-migration
   snapshots.
7. **Observability.** Emit a counter for `REJECTED` (must correlate with zero writer calls) and for
   read-back failures.

---

## 6. Rollback Plan

A rollback of this repair **must keep the new writer gate enforced**. The prior flat writer is the
defect; restoring it is explicitly forbidden.

1. **Primary rollback — fail-closed flag.** Set `knowledge_promotion_pipeline_enabled = false`.
   In this state the Knowledge writer returns `REJECTED` / `ASSET_WRITE_FAILED` for promotion
   requests. It **does not** fall back to the flat writer.
2. **Code rollback.** Revert the worker deploy, but the reverted artefact must be the *gated*
   baseline, not the pre-repair flat writer. If the only available artefact is the flat writer,
   rollback means disabling the `write_knowledge_candidate` path entirely (fail closed), not
   re-enabling it.
3. **Schema rollback.** Leave the additive `knowledge_candidates` table and approval-binding
   columns in place (nullable, unused). **Do not drop** them in a rollback: dropping risks
   disturbing audit data and buys nothing.
4. **Non-negotiable invariant.** At no point may a rollback restore or recommend the old flat
   candidate-to-Canonical bypass. `validate_candidate_gate` remains the sole write authorisation.

---

## 7. Security Check

| Item | Finding |
|---|---|
| Flat-writer bypass | **Confirmed present at baseline.** `writeKnowledgeCandidate` (`worker/index.js:2868`) writes Canonical with no candidate/review/approval gate; only MCP `hasWriteScope` guards it (`worker/index.js:3455`). |
| Caller-supplied decision | `promotion_decision` is exposed in the tool schema (`worker/index.js:3359`) and copied to provenance (`worker/index.js:2831`); the target gate removes it from any authorising role. |
| Independent staging | Target isolates candidate records from `assets`/`asset_versions`, preventing a second source of Golden truth. |
| Approval binding | Target binds approval to candidate/version/hash/review/receipt/approver/expiry, preventing replay/mismatch promotion. |
| Read-back integrity | Write responses are never treated as proof; authoritative re-read is mandatory before `CANONICAL_READBACK_VERIFIED`. |
| Secret / OAuth / permission / binding changes | **None.** No credential, secret, OAuth, permission, or binding was read or changed. |
| Canonical / deployment mutations in this task | **None.** No deploy, no migration execution, no Canonical write, no promotion. |
| `.github/workflows/`, secret-like paths | **Untouched.** No deletion anywhere. |

The only repository diff produced by this task is the addition of this report.

---

## 8. Production Readiness

**`NOT_READY`**

Rationale:

- The repair is **specified and behaviour-validated**, but the production writer
  (`worker/index.js`) was **not modified** because that path is outside this task's allowlist.
- The five requested regression tests are specified and executed only against a reference model;
  they are **not merged** in this change.
- No migration was applied and no deploy occurred.
- **Live production evidence is absent**: no `asset.read`/`ASSET_DB` credential and no reachable
  `/mcp` transport.

Advancement criteria to reach `READY_FOR_REVIEW`: land the §2.3 components in an allowlisted
implementation task and merge the §4.2 tests. Advance to `READY_FOR_HUMAN_APPROVAL` only after
those tests run green against the real worker and a read-only production read-back confirms the
existing Knowledge corpus is unchanged.

---

## 9. Live Production Verification Status

- **19 Knowledge assets / versions / provenance: `UNVERIFIED`.**
  The frozen dedup report `knowledge_canonical_fulltext_dedup_recovery_report.md` records a
  20-asset Knowledge corpus with **19/20 full bodies unread** (`19`, `19/20`, `full_bodies_unread:
  19`). This environment has no live Canonical read access, so neither the stated count of 19 nor the
  asset versions/provenance could be independently verified read-only. It is reported as
  **UNVERIFIED**, not claimed as live-verified.
- No production write, promotion, deploy, migration, or secret access occurred.

---

## 10. Remaining Blockers / Handoff

1. Implementation files (`worker/index.js`, `hello.py`) and the new test suite are outside this
   task's allowlist; the repair cannot be landed under this contract.
2. Live read-back / canonical inventory verification is blocked by missing credentials and transport.
3. `NOT_READY` persists until an allowlisted implementation task lands §2.3 and merges §4.2.

### Evidence summary

| Tier | Evidence |
|---|---|
| Code (frozen repo) | `worker/index.js:2788-2976`, `3342-3365`, `3455`; `hello.py:29030-29330` |
| Test (executed) | `python -m pytest -q` → `1535 passed, 1 skipped`; 10 approval-ledger tests green |
| Test (reference model) | `/tmp/opencode/knowledge_pipeline_refmodel.py` → all six scenarios pass |
| Live production | **None** (no credential/transport; 19 assets UNVERIFIED) |
| Repo diff | `KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_REPAIR_REPORT_V1.md` only |
