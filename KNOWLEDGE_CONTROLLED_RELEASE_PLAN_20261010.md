# KNOWLEDGE_CONTROLLED_RELEASE_PLAN_20261010

- Task: `cf-44b8447f89a1` — `KNOWLEDGE_PRODUCTION_BASELINE_AND_ISOLATED_D1_RELEASE_PREFLIGHT_V0.1`
- Document status: **PREPARED — NOT EXECUTED** (`PARTIAL`; production release `BLOCKED` until the schema-rebuild is approved and real-D1-verified)
- Repo pin at preparation: `1b7dabc3b0c48afc773dfbb77f2276007148d258`
- **Nothing in production was deployed, migrated, promoted, published or written by this task.**

---

## 0. Non-negotiable boundary and authority model

- **One approval authority only:** the existing `personal_ai_approval_ledger` in `ASSET_DB` (`45d6f18a-3a34-4ccd-8337-c00a775cd7a2`). This plan introduces **no** second ledger, **no** new production store, and **no** new approval-mint path.
- **One Human Gate only:** the existing Site WebAuthn gate (`Site v0.3.6` knowledge approval gate) that writes approvals into that one ledger out of band. The worker can only read/consume; it can never mint (`worker/index.js:3332-3336`).
- **Fail-closed:** if any precondition is unmet, promotion stays `REJECTED`/disabled. The old flat writer is never a fallback.
- No secret/OAuth/binding/permission change is part of this plan except the single reviewed migration below, which itself remains gated.

The production operation vocabulary (`deploy_worker_version`, `write_decision_record`) belongs to that **existing** Site/Human-Gate toolchain, not to this repo's worker. Any remediation must evolve that **one** existing ledger in place; it must never fork a parallel ledger.

---

## 1. Why a controlled schema rebuild is required (proven, not assumed)

From `KNOWLEDGE_PRODUCTION_BASELINE_20261010.md` §2 and `KNOWLEDGE_ISOLATED_D1_VALIDATION_20261010.md` §2–§4, reproduced in isolated SQLite:

1. `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql` does **not** upgrade the existing table — `CREATE TABLE IF NOT EXISTS` is a no-op and the migration aborts at `CREATE INDEX … (candidate_id, …)` with `no such column: candidate_id`.
2. The production `operation CHECK IN ('deploy_worker_version','write_decision_record')` rejects `KNOWLEDGE_PROMOTION` and `knowledge_write`. SQLite/D1 cannot relax a `CHECK` in place.
3. The worker's live select (`worker/index.js:3089`) fails on the production table (`no such column: asset_type`).

Because `CHECK` constraints and column types cannot be changed additively, the honest options are:

- **(A) Do nothing (recommended interim).** Knowledge promotion stays disabled/fail-closed. No production risk. This plan defaults to A until approved.
- **(B) Reviewed in-place rebuild of the single existing ledger** to a union schema (preserving every existing column and row), plus registration of the legacy operations — behind the single Human Gate. **Prepared below; NOT applied.**

A separate new ledger table would violate the "one approval authority" rule and is **rejected**.

---

## 2. Prepared migration design `0004_knowledge_approval_ledger_rebuild.sql` (documented only — NOT committed, NOT applied)

> The task allowlist for this run is only the three `*.md` files, so no `.sql` file was created. The DDL below is the reviewed proposal for a later, separately approved change. It is **not** the final artifact; the exact types must be agreed with the Site gate owner.

Design goals:
- Preserve **all** existing production columns and rows (`approval_id`, `requesting_user_hash`, `operation`, `exact_target`, `payload_sha256`, `created_at`, `expires_at`, `consumed_at`).
- Add the RC-required columns (`asset_type`, `candidate_id`, `candidate_version`, `content_hash`, `review_result`, `approved_by`, `state`, `consumed`, `consume_count`, `invalidated`, `invalidated_at`) as nullable/defaulted so Decision/deploy rows remain valid.
- Widen `operation` to the union `('deploy_worker_version','write_decision_record','decision_write','knowledge_write','KNOWLEDGE_PROMOTION')`.
- Keep the table `STRICT`.
- Register every operation in `approval_ledger_operations` (including the two legacy names) so the FK/registry stays consistent and no existing row is orphaned.

Proposed shape (illustrative; **requires Site-owner review**):

```sql
-- 0004 (PREPARED, NOT APPLIED)
INSERT OR IGNORE INTO approval_ledger_operations
  (operation, asset_type, canonical_writer, single_use, replay_guard) VALUES
  ('deploy_worker_version','DEPLOY','deployWorkerVersion',1,1),
  ('write_decision_record','DECISION','writeDecisionRecord',1,1);

CREATE TABLE personal_ai_approval_ledger__new (
  approval_id           TEXT PRIMARY KEY,
  requesting_user_hash  TEXT CHECK (requesting_user_hash IS NULL OR length(requesting_user_hash)=64),
  operation             TEXT NOT NULL CHECK (operation IN
      ('deploy_worker_version','write_decision_record','decision_write','knowledge_write','KNOWLEDGE_PROMOTION')),
  exact_target          TEXT,
  payload_sha256        TEXT,
  -- legacy epoch integers retained; RC TEXT semantics added separately
  created_at            TEXT NOT NULL,
  expires_at            TEXT NOT NULL,
  consumed_at           TEXT,
  legacy_created_at     INTEGER,
  legacy_expires_at     INTEGER,
  legacy_consumed_at    INTEGER,
  asset_type            TEXT,
  candidate_id          TEXT,
  candidate_version     INTEGER,
  content_hash          TEXT,
  review_result         TEXT,
  approved_by           TEXT,
  state                 TEXT NOT NULL DEFAULT 'REGISTERED',
  consumed              INTEGER NOT NULL DEFAULT 0,
  consume_count         INTEGER NOT NULL DEFAULT 0,
  invalidated           INTEGER NOT NULL DEFAULT 0,
  invalidated_at        TEXT
) STRICT;

INSERT INTO personal_ai_approval_ledger__new
  (approval_id, requesting_user_hash, operation, exact_target, payload_sha256,
   legacy_created_at, legacy_expires_at, legacy_consumed_at,
   created_at, expires_at, consumed_at, state, consumed, consume_count, invalidated)
SELECT approval_id, requesting_user_hash, operation, exact_target, payload_sha256,
       created_at, expires_at, consumed_at,
       COALESCE(datetime(created_at,'unixepoch'), '1970-01-01T00:00:00Z'),
       COALESCE(datetime(expires_at,'unixepoch'), '1970-01-01T00:00:00Z'),
       CASE WHEN consumed_at IS NULL THEN NULL ELSE datetime(consumed_at,'unixepoch') END,
       CASE WHEN consumed_at IS NULL THEN 'REGISTERED' ELSE 'CONSUMED' END,
       CASE WHEN consumed_at IS NULL THEN 0 ELSE 1 END,
       0, 0
FROM personal_ai_approval_ledger;

DROP TABLE personal_ai_approval_ledger;
ALTER TABLE personal_ai_approval_ledger__new RENAME TO personal_ai_approval_ledger;

CREATE INDEX IF NOT EXISTS idx_approval_ledger_binding
  ON personal_ai_approval_ledger (operation, candidate_id, candidate_version, content_hash);
CREATE INDEX IF NOT EXISTS idx_approval_ledger_state
  ON personal_ai_approval_ledger (operation, consumed, invalidated);
```

**Open design points requiring human review (do not execute until resolved):**
- Whether `requesting_user_hash` must remain NOT NULL for legacy rows (production rows may be empty in this environment's model).
- Epoch→ISO conversion vs. retaining both (shown) — a lossy conversion would break legacy audit.
- Whether the Site gate writer must be updated to the widened `operation` vocabulary in the same release window (it is the authority that mints).
- `0004` must be verified on a **real D1 clone** (not only local SQLite) before approval.

---

## 3. Backup / rollback / integrity runbook (to run only after a separate human approval)

```
Step B0  Read-only snapshot: PRAGMA table_info(personal_ai_approval_ledger);
         SELECT COUNT(*), operation, COUNT(*) FROM personal_ai_approval_ledger GROUP BY operation;
         npx wrangler d1 export ASSET_DB --remote --output=ledger_backup_<ts>.sql
         sha256sum ledger_backup_<ts>.sql; record row counts per operation.
Step B1  Capture fresh preconditions (see §4). Any mismatch -> STOP.
Step B2  Apply 0004 in a single D1 batch/transaction (SQLite D1 runs the batch atomically).
Step B3  Verify post-migration: PRAGMA table_info; row counts per operation unchanged;
         legacy ids/hashes byte-identical; new indexes present.
Step B4  On ANY failure: do NOT retry destructively. Restore from B0 export on a clone first,
         prove restoration, then restore production under incident protocol.
```

**Rollback principle:** the gate is never weakened. If the rebuild fails, promotion remains
`REJECTED`. If the ledger is restored, it must be the pre-rebuild schema with the original rows.
Existing approval evidence is never deleted on rollback.

---

## 4. Fresh baseline preconditions (all must be re-read immediately before any approved step)

| # | Precondition | Expected | Verified here? |
|---|---|---|---|
| C1 | Worker deployment id | `2626653a-c984-4160-942f-ed8ce3b51c97` | supplied (Brain), not re-read |
| C2 | Worker active version id | `1b6a318a-c40c-413c-b62e-3d5497e4d0c2` | supplied, not re-read |
| C3 | binding_hash | `bd15a472be5527c50f892d851c71f610fc6ce6a2bdf38abf7b8efbdf0534c36d` | supplied, not re-read |
| C4 | traffic | 100% active | supplied |
| C5 | ledger DB id | `45d6f18a-3a34-4ccd-8337-c00a775cd7a2` | matches `wrangler.toml` |
| C6 | ledger schema + per-operation row counts + backup sha256 | recorded at B0 | NOT yet (requires transport) |
| C7 | Knowledge corpus manifest (19 assets incl. anomalous fixture) hashes | recorded read-only | supplied, not re-read |
| C8 | repo commit + `0003` sha256 | `1b7dabc…` / `9a51d3a5…` | **PASS** (this env) |
| C9 | full suite green | `1576 passed, 1 skipped` | **PASS** (this env) |
| C10 | real D1 clone verification of `0004` + rollback restore | pass | **NOT DONE / BLOCKED** |

Any precondition failure ⇒ STOP and stay fail-closed.

---

## 5. Human Gate decision request

**HUMAN_GATE_REQUIRED.** This is **not** a request to execute a release, because not all gates are met (C6, C7 independently, C10 remain unverified; real D1 transport absent). It is a request for the **single existing Human Gate** to decide between:

- **(A) Hold** — keep the knowledge approval gate disabled (current production state; default), and separately schedule the schema owner review of the `0004` design; **or**
- **(B) Authorize a future, separately-scoped execution task** that (i) verifies `0004` on a real D1 clone, (ii) obtains distinct Worker+migration approvals in the one ledger, (iii) executes §3, and (iv) performs the §7 read-back.

No production mutation, approval mint/consume, secret/OAuth/binding/permission change, Site publish or Canonical write is performed by this task.

The P0 governance incident (contaminated Golden fixture, baseline §1.4) is **not** remediated here; deleting/overwriting it requires a **distinct** approval and is explicitly out of scope.

---

## 6. Changed-files allowlist for this task

Only the three files below were created/changed by this run (all markdown; no code/migration/test/schema change):

```
KNOWLEDGE_PRODUCTION_BASELINE_20261010.md
KNOWLEDGE_ISOLATED_D1_VALIDATION_20261010.md
KNOWLEDGE_CONTROLLED_RELEASE_PLAN_20261010.md
```

No `.github/workflows/`, no secret/token/credential/.env/.pem/.key path, no file deleted, no `.sql`/`worker`/`site`/`tests` file added or modified. The reproduction scripts live **outside** the repository at `/tmp/opencode/`.

Direct evidence references:
- code: `worker/index.js:3062-3094` (SQL), `worker/index.js:3100-3131` (gate), `worker/index.js:3332-3549` (promote/consume/reserve), `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql:81-106`.
- tests: `tests/test_knowledge_candidate_golden_pipeline.py:1226,1309,1358,1468`; `tests/test_decision_ingestion_writer.py:993-1030`.
- SQL reproduction: `KNOWLEDGE_ISOLATED_D1_VALIDATION_20261010.md` §1–§5.

**Commit SHA / test counts:** prepared on `1b7dabc3b0c48afc773dfbb77f2276007148d258`; `python -m pytest -q` ⇒ `1576 passed, 1 skipped`; `node --check worker/index.js` and `node --check site/worker/index.js` ⇒ OK. The final commit that adds these three documents is recorded by the task runner.

---

## 7. Independent post-deploy Cloud Asset Read plan (to run only after later approval)

Goal: prove the 19-asset Knowledge baseline is preserved and **zero unintended mutations** occur. A write response alone is never proof.

1. **Pre-manifest (before any approved change):** read-only list of all KNOWLEDGE assets (`asset_id`, version, content_hash, status). Expect **19** entries including `candidate-writer-validation-20261009-v1` v1.0 hash `0effe682ef88390907f6b5a0b84b678f81d510ca4ab734352c528df5e2e6d6a4`. Record manifest sha256.
2. **No-op / disabled check:** with the gate still disabled, a promotion attempt returns `REJECTED` with `write_calls: 0`; the manifest is byte-identical.
3. **After the approved rebuild only:** re-apply the same manifest read; diff must show **no unexpected** asset add/remove/change. The anomalous fixture must remain untouched (its removal is a distinct approval).
4. **Approval ledger read-back:** per-operation counts unchanged except any explicitly-approved new rows; indexes `idx_approval_ledger_binding`/`idx_approval_ledger_state` present; no second ledger table exists.
5. **Controlled promotion (separate scope):** exactly one designated validation candidate promotes; Golden write occurs once; authoritative read-back (`verifyKnowledgeVersion`) matches candidate version/hash; a repeat is idempotent (no duplicate Golden).
6. **Cross-tenant:** DECISION/SKILL/REALITY counters unchanged.
7. Any drift ⇒ fail-closed + rollback §3; never convert an isolated/SQLite result into a production PASS.

---

## 8. Status summary

| Item | Status |
|---|---|
| Baseline + mismatch discovered/reproduced | **PASS** |
| Repair prepared (design + runbook, documented) | **PARTIAL** (not applied; allowlist forbids `.sql`) |
| Real D1 verification of repair | **BLOCKED / REAL_D1_UNVERIFIED** |
| Production release | **NOT PERFORMED** |
| Authoritative production deployment | **UNTOUCHED** |
| Candidate promotion | **NOT PERFORMED** |
| Canonical corpus | **UNTOUCHED** (contaminated fixture remains; distinct approval required) |
| Human Gate | **HUMAN_GATE_REQUIRED** (hold-or-authorize-future-task; no release execution requested) |
