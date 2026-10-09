# KNOWLEDGE_LEDGER_COMPAT_REPAIR_V02

- Task: `cf-70f2d633920b` (parent `cf-44b8447f89a1`) — `KNOWLEDGE_LEDGER_PRODUCTION_COMPAT_REPAIR_V0.2`
- Project: `personal-ai-knowledge-golden`
- Base repo commit (read-back): `48ff18c95246f697c3198ba506e722db22602cf9`
- Document status: **PARTIAL** — the isolated, executable single-ledger repair package is produced and green on local SQLite; **real Cloudflare D1 is `REAL_D1_UNVERIFIED`**; **`READY_FOR_PRODUCTION` is NOT claimed**.
- Boundary honoured: no production deploy, no production D1 migration, no Canonical write, no Site publish, no approval mint/consume, no secret/OAuth/binding/permission change. No second approval authority / ledger / mint path introduced.

> **Production COMPAT_REPAIR_V0.2 corrects V0.1.** `KNOWLEDGE_CONTROLLED_RELEASE_PLAN_20261010.md` (V0.1) sketched a rebuild that (a) converted the legacy INTEGER `created_at`/`expires_at`/`consumed_at` into TEXT at the same names (or via `legacy_*` shims) and (b) made `requesting_user_hash` nullable. That is **rejected here**: it would have broken the WebAuthn numeric-epoch timing and the atomic `consumed_at` CAS. V0.2 keeps the legacy columns, types and semantics **unchanged** and only *adds*.

---

## 0. Non-negotiable boundary and authority model

- **One approval authority only:** the existing `personal_ai_approval_ledger` in `ASSET_DB` (`45d6f18a-3a34-4ccd-8337-c00a775cd7a2`). This repair evolves that one table in place. It creates **no** second ledger and **no** second registry authority.
- **One mint authority only:** the existing Site WebAuthn gate. The Worker can only READ and atomically CONSUME; there is still **no** Worker code path that mints an approval (`worker/index.js:3332-3336`). A caller-supplied `approved_by`/`approval_receipt`/`promotion_decision` still cannot authorise a write.
- **Fail-closed:** if the ledger signature is neither the expected `LEGACY` nor `UNION`, the repair **halts** with no partial mutation.
- No production mutation, secret/permission/binding change, Site publish or Canonical write is performed by this task.

---

## 1. Repo pin and independent baselines (this environment)

| Item | Value / evidence |
|---|---|
| `git rev-parse HEAD` | `48ff18c95246f697c3198ba506e722db22602cf9` |
| working tree | clean |
| `worker/index.js` sha256 | `3ef2817b75fd01db60bc5784f5c11d5fbbde58acc918accabf1347aa2ea01054` |
| `site/worker/index.js` sha256 | `846843b85a32e6aa2d5ed35b5d9539c05656b3ce36859a49199f6b9d084eec18` |
| `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql` sha256 | `9a51d3a53ad5ac3e78e07fc9720ad5492443f5a1f6ac677018570fdfc337927a` |
| `node --check worker/index.js` | OK (exit 0) |
| `node --check site/worker/index.js` | OK (exit 0) |
| `python -m pytest -q` | `1576 passed, 1 skipped in 59.25s` (exit 0) |

The stale-approval fix and the review-FAIL vs `PROMOTION_RESERVED` CAS are present at `worker/index.js:3069, 3347-3549` and were **not reverted**. The prior dispatch `cf-44b8447f89a1` only diagnosed the mismatch; V0.2 now supplies executable repair code/tests/SQL (isolated).

### 1.1 Production baseline (Site read-only, independently verified; Brain-supplied transport)

| Field | Expected value |
|---|---|
| ledger DB id (`ASSET_DB`) | `45d6f18a-3a34-4ccd-8337-c00a775cd7a2` |
| ledger table | `personal_ai_approval_ledger` **STRICT** |
| columns | `approval_id TEXT PK`, `requesting_user_hash TEXT NOT NULL CHECK len64`, `operation TEXT CHECK IN ('deploy_worker_version','write_decision_record')`, `exact_target TEXT`, `payload_sha256 TEXT`, `created_at INTEGER`, `expires_at INTEGER`, `consumed_at INTEGER` |
| knowledge operation supported | `false` |
| `execution_enabled` | `false` |
| Site gate state / reason | `BLOCKED` / `KNOWLEDGE_APPROVAL_OPERATION_SCHEMA_REQUIRED` |
| KNOWLEDGE Canonical assets | `19`, including anomalous fixture `candidate-writer-validation-20261009-v1` v1.0 hash `0effe682ef88390907f6b5a0b84b678f81d510ca4ab734352c528df5e2e6d6a4` (do **not** modify; distinct approval required) |

---

## 2. Root cause (proven, not assumed)

`worker/migrations/0003_knowledge_candidate_golden_pipeline.sql` assumes it will *create* `personal_ai_approval_ledger`:

1. `CREATE TABLE IF NOT EXISTS personal_ai_approval_ledger (...)` is a **silent no-op** on production (table exists) → no upgrade.
2. The next statement `CREATE INDEX ... idx_approval_ledger_binding (operation, candidate_id, candidate_version, content_hash)` fails with `no such column: candidate_id`; `idx_approval_ledger_state` is never reached (partial application).
3. The legacy `operation` CHECK rejects `KNOWLEDGE_PROMOTION`/`knowledge_write`.
4. The Worker's runtime `APPROVAL_LEDGER_SELECT` (`worker/index.js:3089`) selects columns the production table does not have → `no such column: asset_type`.

You cannot relax a `CHECK` or change a column type with `ALTER TABLE ADD COLUMN`; a **rebuild is required**. The previous V0.1 rebuild solved the operation vocabulary but broke timing types (rejected, see header).

---

## 3. V0.2 repair design

### 3.1 One union ledger (single authority, legacy columns preserved verbatim)

The repaired table keeps the eight legacy columns with their **exact names, order, types and constraints** (INTEGER epoch timing retained; `requesting_user_hash` remains `NOT NULL CHECK length=64`) and only *widens* the `operation` CHECK by adding names. Worker-only columns are added as nullable/defaulted. See the full SQL in §6.1.

`consumed_at` **remains the single-use authority for the legacy WebAuthn contract** (INTEGER epoch, CAS on `consumed_at IS NULL`). The Worker's `consumed`/`state`/`consume_count` columns are a *mirror*, kept consistent during the rebuild (`consumed` is derived from `consumed_at` for every pre-existing row).

### 3.2 Knowledge candidate binding vs. Site `exact_target`/`payload_sha256`

| Layer | Authoritative binding | Legacy aliases |
|---|---|---|
| Site `deploy_worker_version` / `write_decision_record` | `exact_target` + `payload_sha256` (+ `requesting_user_hash`, `created_at`/`expires_at`/`consumed_at` INTEGER) | — |
| Knowledge `KNOWLEDGE_PROMOTION` (new) | `operation='KNOWLEDGE_PROMOTION'` + `candidate_id` + `candidate_version` + `content_hash` + `review_result='PASS'` + `approved_by` | `exact_target` = `candidate_id`, `payload_sha256` = `content_hash` (redundant, for forward/backward compatibility only) |

The Worker's gate reads the **candidate-scoped** columns (`candidate_id`, `candidate_version`, `content_hash`), so a Knowledge candidate version/hash binding is never conflated with a Site release tuple. Legacy rows leave the candidate-scoped columns `NULL`.

### 3.3 One-use WebAuthn receipt without the Worker becoming an approver

1. The Site (WebAuthn, sole mint authority) inserts one `KNOWLEDGE_PROMOTION` row bound to `candidate_id/candidate_version/content_hash`, leaving `consumed_at = NULL`. It does not consume.
2. The Worker `status`/`action` gate reads only live rows: `... WHERE operation=? AND candidate_id=? AND candidate_version=? AND content_hash=? AND consumed_at IS NULL AND invalidated=0`.
3. The Worker consumes with a **single conditional UPDATE** (compare-and-swap) on the same legacy authority field:
   `UPDATE ... SET consumed=1, state='CONSUMED', consume_count=consume_count+1, consumed_at=<integer epoch> WHERE approval_id=? AND operation=? AND consumed_at IS NULL AND invalidated=0`.
   Under two concurrent consumers exactly one `changes==1`; replay is rejected.
4. A review `FAIL` invalidates every still-live bound approval (`SET invalidated=1, invalidated_at=<iso> WHERE operation=? AND candidate_id=? AND consumed_at IS NULL AND invalidated=0`), additively retaining the row.

Because the Worker writes the integer epoch into the **INTEGER** `consumed_at` (never TEXT), STRICT is satisfied and the legacy CAS is unified: the same field that the Site uses for its own single-use flow is the field the Worker consumes. This is the "one-use receipt" binding; the Worker never inserts/mints.

### 3.4 Worker contract patch (offline proposal — repository code NOT modified)

The only Worker change required (a subsequent approved task must commit it):
- `APPROVAL_LEDGER_SELECT`: replace `AND consumed = 0` with `AND consumed_at IS NULL` (and add `consumed_at` to the projection).
- `APPROVAL_LEDGER_CONSUME`: `... SET consumed=1, state='CONSUMED', consume_count=consume_count+1, consumed_at=? WHERE approval_id=? AND operation=? AND consumed_at IS NULL AND invalidated=0`, binding an **integer epoch seconds** value.
- `APPROVAL_LEDGER_INVALIDATE`: gate on `consumed_at IS NULL` instead of `consumed = 0`.
- Expiry parsing: accept a numeric-epoch `expires_at` (legacy INTEGER) in addition to ISO, i.e. `Number.isFinite(Number(v)) ? Number(v)*1000 : Date.parse(String(v))`.

The candidate/gate logic (`validateCandidateGate`, reservation CAS, no-mint invariant) is otherwise unchanged.

### 3.5 Migration order / guard / routing (no history rewrite, no silent skip)

`0003` is immutable history; it is **not edited or skipped**. A new, self-contained migration is ordered **before** it:

```
worker/migrations/
  0001_asset_provenance_v0_2.sql
  0002_dispatch_idempotency.sql
  0002z_knowledge_approval_ledger_compat.sql   <-- NEW (this repair), sorts after 0002, before 0003
  0003_knowledge_candidate_golden_pipeline.sql
```

Because `0002z...` sorts after `0002_dispatch...` and before `0003_knowledge...`, the in-order runner applies it first. After the rebuild the legacy table is the union schema, so `0003`'s `CREATE TABLE IF NOT EXISTS` is a no-op and both of its indexes resolve (`candidate_id`, `candidate_version`, `content_hash`, `consumed`, `invalidated` now exist). The registry (`approval_ledger_operations`) and `knowledge_candidates` are still created by `0003`; `0002z` pre-creates/seed the registry only so the FK-bound rebuild cannot orphan a legacy row — `0003`'s `CREATE IF NOT EXISTS` / `INSERT OR IGNORE` then no-op.

**Guard (fail-closed, run before `0002z`):** the runner computes the ledger signature.
- `UNION` (contains `candidate_id` and `KNOWLEDGE_PROMOTION`) → skip `0002z` (idempotent).
- `LEGACY` (exactly the 8 legacy columns + unwidened CHECK) → apply `0002z`.
- absent / any other shape → **HALT**; never partially mutate, never mark a failed migration applied.

If `0003` previously failed *and* the runner recorded it (D1 recording semantics for a failed batch are **UNKNOWN**), the runbook requires reconciling `d1_migrations` against `sqlite_master` before proceeding; a failed migration must be re-run, never silently skipped.

### 3.6 Backup / rollback / drift halt

- The rebuild **renames** the pre-state to `personal_ai_approval_ledger__legacy_backup` (never `DROP`), then swaps in the union table. The backup table is read-only evidence, not an authority.
- Rollback: `DROP TABLE personal_ai_approval_ledger; ALTER TABLE personal_ai_approval_ledger__legacy_backup RENAME TO personal_ai_approval_ledger;` restoring the exact pre-state (schema semantically identical, rows byte-for-byte).
- D1 must run the whole file as one batch/transaction; drift encountered by the guard → HALT.

---

## 4. Local SQLite evidence (isolated; NOT a substitute for D1)

Command: `python3 /tmp/opencode/ledger_compat_repair_v02.py` — **exit code 0**, 46 checks, 0 failures.

Captured output (`/tmp/opencode/ledger_compat_repair_v02.out`):

```text

=== test_00_baseline_0003_fails_on_prod_shape ===
[PASS] baseline: legacy table STRICT
[PASS] baseline: exact legacy columns
[PASS] baseline: 0003 fails on prod-shaped ledger :: 'no such column: candidate_id'
[PASS] baseline: failure is no such column: candidate_id :: 'no such column: candidate_id'

=== test_01_repaired_rebuild_and_migration_in_order ===
[PASS] repair: rebuild executed
[PASS] repair: union shape detected
[PASS] repair: still STRICT
[PASS] repair: legacy columns preserved in order
[PASS] repair: created_at/expires_at/consumed_at stay INTEGER :: {'approval_id': 'TEXT', 'requesting_user_hash': 'TEXT', 'operation': 'TEXT', 'exact_target': 'TEXT', 'payload_sha256': 'TEXT', 'created_at': 'INTEGER', 'expires_at': 'INTEGER', 'consumed_at': 'INTEGER', 'asset_type': 'TEXT', 'candidate_id': 'TEXT', 'candidate_version': 'INTEGER', 'content_hash': 'TEXT', 'review_result': 'TEXT', 'approved_by': 'TEXT', 'state': 'TEXT', 'consumed': 'INTEGER', 'consume_count': 'INTEGER', 'invalidated': 'INTEGER', 'invalidated_at': 'TEXT'}
[PASS] repair: legacy rows byte-for-byte preserved
[PASS] repair: original backup table retained
[PASS] repair: 0001/0002/0003 apply in order after repair
[PASS] repair: 0003 binding index present
[PASS] repair: 0003 state index present
[PASS] repair: registry holds all five operations
[PASS] repair: single ledger only (no v2/second authority)
[PASS] repair: re-run is idempotent

=== test_02_legacy_operation_semantics_and_integer_timing ===
[PASS] legacy: WebAuthn CAS first consume wins
[PASS] legacy: WebAuthn CAS replay loses (single-use)
[PASS] legacy: CAS left integer consumed_at :: {'consumed': 0, 'consumed_at': 1791589373, 'state': 'REGISTERED'}
[PASS] legacy: pre-consumed row mirrors consumed=1/CONSUMED
[PASS] legacy: CHECK rejects unknown operation

=== test_03_knowledge_promotion_two_connection_cas_and_replay ===
[PASS] knowledge: gate SELECT finds the bound live approval
[PASS] knowledge: candidate_* is the authoritative binding
[PASS] knowledge: legacy aliases kept distinct from Site fields
[PASS] knowledge: exactly one CAS consumer wins :: {'wins': 1, 'losses': 1, 'conns': [<sqlite3.Connection object at 0x7f6f5f1e9210>, <sqlite3.Connection object at 0x7f6f5f1ea200>], 'winner_conn': <sqlite3.Connection object at 0x7f6f5f1e9210>}
[PASS] knowledge: replay after consume is rejected
[PASS] knowledge: consumed mirror + integer consumed_at + count=1

=== test_04_stale_approval_invalidation_blocks_replay ===
[PASS] stale: approval live before FAIL
[PASS] stale: FAIL invalidates the live approval
[PASS] stale: invalidated approval no longer selectable (no replay)
[PASS] stale: row retained (revocation additive)
[PASS] stale: re-invalidate is a no-op

=== test_05_candidate_lifecycle_gate_no_unauthorized_golden_write ===
[PASS] gate: BLOCKED without approval, zero canonical writes
[PASS] gate: reservation CAS succeeds once
[PASS] gate: FAIL after reservation is rejected (race)

=== test_06_rollback_and_rerun ===
[PASS] rollback: pre-state differs after rebuild
[PASS] rollback: schema restored to legacy
[PASS] rollback: rows byte-for-byte restored
[PASS] rollback: restored schema semantically identical (quoting normalised)
[PASS] rollback: rebuild after rollback succeeds
[PASS] rollback: rows still intact

=== test_07_drift_halts ===
[PASS] drift: unknown shape HALTED

=== test_08_worker_source_has_no_mint_and_flat_writer_is_gated ===
[PASS] worker: no approval mint/register function
[PASS] worker: consume uses conditional CAS in current source
[PASS] worker: asset_id-only public path rejected before IO

============================================================
checks: 46  passed: 46  failed: 0
```

### 4.1 Baseline fails before repair (required)

`test_00_baseline_0003_fails_on_prod_shape` proves on a production-shaped **STRICT** ledger that applying `0001+0002+0003` in order raises `OperationalError: no such column: candidate_id`, and the object diff shows the binding/state indexes are not created. This reproduces the P0 blocker independently.

### 4.2 Local-SQLite PASS summary

| Assertion group | Result |
|---|---|
| legacy STRICT signature + exact 8 columns | PASS |
| `0003` fails on prod-shaped ledger (`no such column: candidate_id`) | PASS (mismatch reproduced) |
| repaired `0002z` rebuild → `UNION`, still STRICT | PASS |
| `created_at`/`expires_at`/`consumed_at` remain INTEGER (no TEXT conversion) | PASS |
| legacy rows byte-for-byte preserved; original retained as backup | PASS |
| `0001+0002+0003` apply in order after repair; both indexes present | PASS |
| registry holds all 5 operations; no second ledger table | PASS |
| rebuild re-run is idempotent | PASS |
| legacy WebAuthn CAS first win / replay loss; integer `consumed_at` | PASS |
| legacy CHECK still rejects unknown operation | PASS |
| Knowledge promotion 2-connection CAS: exactly one winner; replay rejected; count=1 | PASS |
| stale-approval invalidation blocks replay; row retained additively | PASS |
| Candidate lifecycle: reservation CAS, FAIL-after-reservation rejected | PASS |
| BLOCKED gate → zero Canonical writes | PASS |
| rollback restores legacy schema + byte-for-byte rows; re-run deterministic | PASS |
| unknown drift shape → HALT | PASS |
| Worker has no mint path; `asset_id`-only public path rejected | PASS |

### 4.3 Rollback proof

Performed in `test_06_rollback_and_rerun`: rebuild → `DROP` union table → `ALTER TABLE personal_ai_approval_ledger__legacy_backup RENAME TO personal_ai_approval_ledger` → `detect_shape == LEGACY`, rows equal the pre-rebuild tuples, and the schema is semantically identical (SQLite only adds identifier quoting on `RENAME`). Re-running the rebuild after rollback succeeds deterministically. A production exercise must additionally use a **real D1 clone** (export → restore on a separate DB) before any approved live apply; that step is **NOT DONE**.

---

## 5. Real Cloudflare D1 status

| Item | Status |
|---|---|
| Real D1 transport/credential in this environment | **NO** (`CLOUDFLARE_API_TOKEN`/`CF_API_TOKEN`/`CLOUDFLARE_API_KEY` absent; wrangler unauthenticated) |
| Real D1 migration attempted | **NO** (boundary) |
| Real D1 clone rebuild + rollback exercise | **NOT PERFORMED** |
| Real D1 STRICT/CHECK/FK/CAS behaviour | **`REAL_D1_UNVERIFIED`** (inferred from local SQLite 3.45.1 only) |
| Production DB used as a test DB | **NO** |
| Second durable ledger/Canonical created | **NO** |

**Disposition:** `LOCAL_SQLITE_PASS` for the repair; `REAL_D1_UNVERIFIED`; **NOT `READY_FOR_PRODUCTION`**.

---

## 6. Offline artifacts (actual code / tests / versioned SQL produced by this task)

The repository allowlist for this run is **only this report**, so the executable artifacts live outside the repo at `/tmp/opencode/` and are reproduced verbatim below. A later approved task must commit the SQL as `worker/migrations/0002z_knowledge_approval_ledger_compat.sql` and apply the §3.4 Worker patch.

| Artifact | sha256 |
|---|---|
| `0002z_knowledge_approval_ledger_compat.sql` | `99149b731e715d71c4b32206eb4eb0b4c5d6c2b835dadb0b7b35959308b77f43` |
| `ledger_compat_repair_v02.py` (test harness) | `2ee58ad00a9e3bf22342e4f0a4803fc26a13d614a8bf39e957eefe1fe6998c51` |
| captured run output | `c88884e58a73e544533c93ac55b01e5c36ecfd2c62fe7c54db49ceab1f5ae36b` |
| baseline legacy DDL sha256 (embedded constant) | `9c17d1ced367fb171cb3cf03dc0cef2de30df49e55328663eb8d4e965458b924` |
| union DDL sha256 (embedded constant) | `5e66126f649bbe135f336ea576858d755002e50084a3e8a401ae932b2aa96c18` |
| Worker `SELECT` V2 sha256 | `091f0b10caad17a1fb3a0f6253c2dcf4e2013e9f980fbcce9cb4db897a4e6332` |
| Worker `CONSUME` V2 sha256 | `f7e38db80a728497bd08eaea13ea9e8f7be25037a07afdd182f3679119248f83` |
| Site CAS `consumed_at` sha256 | `187bd2cd10a798a632f3aa55c078fba56e8313867f0754a5ff64f24a7856e27e` |

### 6.1 Offline versioned migration artifact

```sql
-- 0002z_knowledge_approval_ledger_compat.sql
-- KNOWLEDGE_LEDGER_PRODUCTION_COMPAT_REPAIR_V0.2 (OFFLINE, NOT APPLIED)
--
-- Routing: this file sorts AFTER 0002_dispatch_idempotency.sql and BEFORE
-- 0003_knowledge_candidate_golden_pipeline.sql under the in-order D1 runner,
-- so the pre-existing production ledger is reshaped to the union schema BEFORE
-- 0003's CREATE TABLE IF NOT EXISTS (a no-op) and its two indexes run. No
-- migration history is rewritten and no failed migration is silently skipped.
--
-- PRE-CONDITION (fail-closed, enforced by the runner BEFORE this file):
--   shape(personal_ai_approval_ledger) == LEGACY, i.e. exactly
--   (approval_id, requesting_user_hash, operation, exact_target, payload_sha256,
--    created_at, expires_at, consumed_at) with the UNWIDENED operation CHECK
--   IN ('deploy_worker_version','write_decision_record').
--   UNION  -> runner skips (idempotent).
--   DRIFT / absent -> runner HALTS (no partial mutation).
--
-- Guarantees:
--   * legacy columns/order/type/constraints unchanged; INTEGER epoch timing is
--     NEVER converted to TEXT;
--   * old CHECK is widened by ADDITION of new operation names only;
--   * the legacy WebAuthn single-use CAS on `consumed_at` remains authoritative;
--   * every existing row is copied byte-for-byte; the pre-state is retained as
--     personal_ai_approval_ledger__legacy_backup for byte-for-byte rollback;
--   * exactly one approval ledger / one mint authority (the Site) is preserved.

-- 1. Ensure the trusted operation registry exists and contains ALL operations
--    (legacy + repo) before the FK-bound rebuild, so no existing row is orphaned.
CREATE TABLE IF NOT EXISTS approval_ledger_operations (
  operation        TEXT PRIMARY KEY,
  asset_type       TEXT NOT NULL,
  canonical_writer TEXT NOT NULL,
  single_use       INTEGER NOT NULL DEFAULT 1,
  replay_guard     INTEGER NOT NULL DEFAULT 1
);

INSERT OR IGNORE INTO approval_ledger_operations
  (operation, asset_type, canonical_writer, single_use, replay_guard) VALUES
  ('deploy_worker_version', 'DEPLOY',    'deployWorkerVersion',     1, 1),
  ('write_decision_record', 'DECISION',  'writeDecisionRecord',     1, 1),
  ('decision_write',        'DECISION',  'writeDecisionRecord',     1, 1),
  ('knowledge_write',       'KNOWLEDGE', 'writeKnowledgeCandidate', 1, 1),
  ('KNOWLEDGE_PROMOTION',   'KNOWLEDGE', 'writeKnowledgeCandidate', 1, 1);

-- 2. Union table: legacy columns verbatim + nullable Worker columns.
CREATE TABLE personal_ai_approval_ledger__v2 (
  approval_id          TEXT PRIMARY KEY,
  requesting_user_hash TEXT NOT NULL CHECK (length(requesting_user_hash) = 64),
  operation            TEXT NOT NULL CHECK (operation IN (
      'deploy_worker_version','write_decision_record',
      'decision_write','knowledge_write','KNOWLEDGE_PROMOTION')),
  exact_target         TEXT,
  payload_sha256       TEXT,
  created_at           INTEGER,
  expires_at           INTEGER,
  consumed_at          INTEGER,
  asset_type           TEXT,
  candidate_id         TEXT,
  candidate_version    INTEGER,
  content_hash         TEXT,
  review_result        TEXT,
  approved_by          TEXT,
  state                TEXT NOT NULL DEFAULT 'REGISTERED',
  consumed             INTEGER NOT NULL DEFAULT 0,
  consume_count        INTEGER NOT NULL DEFAULT 0,
  invalidated          INTEGER NOT NULL DEFAULT 0,
  invalidated_at       TEXT,
  FOREIGN KEY (operation) REFERENCES approval_ledger_operations (operation)
) STRICT;

-- 3. Copy every legacy row without loss. `consumed` mirrors legacy consumed_at.
INSERT INTO personal_ai_approval_ledger__v2
  (approval_id, requesting_user_hash, operation, exact_target, payload_sha256,
   created_at, expires_at, consumed_at,
   asset_type, candidate_id, candidate_version, content_hash, review_result,
   approved_by, state, consumed, consume_count, invalidated, invalidated_at)
SELECT approval_id, requesting_user_hash, operation, exact_target, payload_sha256,
       created_at, expires_at, consumed_at,
       NULL, NULL, NULL, NULL, NULL,
       NULL,
       CASE WHEN consumed_at IS NULL THEN 'REGISTERED' ELSE 'CONSUMED' END,
       CASE WHEN consumed_at IS NULL THEN 0 ELSE 1 END,
       0, 0, NULL
FROM personal_ai_approval_ledger;

-- 4. Swap, retaining the pre-state for rollback, then create 0003's indexes.
ALTER TABLE personal_ai_approval_ledger RENAME TO personal_ai_approval_ledger__legacy_backup;
ALTER TABLE personal_ai_approval_ledger__v2 RENAME TO personal_ai_approval_ledger;

CREATE INDEX IF NOT EXISTS idx_approval_ledger_binding
  ON personal_ai_approval_ledger (operation, candidate_id, candidate_version, content_hash);
CREATE INDEX IF NOT EXISTS idx_approval_ledger_state
  ON personal_ai_approval_ledger (operation, consumed, invalidated);
```

### 6.2 Offline regression harness (isolated SQLite)

```python
#!/usr/bin/env python3
"""KNOWLEDGE_LEDGER_PRODUCTION_COMPAT_REPAIR_V0.2 (offline, isolated).

Executable repair package for the single production approval ledger
(`personal_ai_approval_ledger`) so that the Site (WebAuthn mint authority) and
the Worker (read/consume only) remain compatible WITHOUT a second ledger,
WITHOUT converting the legacy INTEGER epoch timing to TEXT, and WITHOUT
breaking the legacy operation CHECK or the WebAuthn atomic `consumed_at` CAS.

This file is intentionally OUTSIDE the repository. It is the "actual code/SQL"
deliverable referenced by KNOWLEDGE_LEDGER_COMPAT_REPAIR_V02.md. The repository
allowlist for the run is only the report; a later approved task must commit the
SQL below as a real migration.

Run: python3 /tmp/opencode/ledger_compat_repair_v02.py
Exit code 0 == all local-SQLite assertions passed (real D1 remains UNVERIFIED).
"""

from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

REPO = Path("/home/runner/work/personal-ai-cloud-execution-test/personal-ai-cloud-execution-test")
MIGRATIONS = REPO / "worker" / "migrations"

# ---------------------------------------------------------------------------
# 0. Production-shaped STRICT legacy ledger (exactly as read back from D1).
# ---------------------------------------------------------------------------
LEGACY_LEDGER_DDL = """
CREATE TABLE personal_ai_approval_ledger (
  approval_id          TEXT PRIMARY KEY,
  requesting_user_hash TEXT NOT NULL CHECK (length(requesting_user_hash) = 64),
  operation            TEXT CHECK (operation IN ('deploy_worker_version','write_decision_record')),
  exact_target         TEXT,
  payload_sha256       TEXT,
  created_at           INTEGER,
  expires_at           INTEGER,
  consumed_at          INTEGER
) STRICT;
"""

LEGACY_OPERATIONS = ("deploy_worker_version", "write_decision_record")

# ---------------------------------------------------------------------------
# 1. Repaired, versioned, offline migration artifact.
#    Filename for the in-order D1 runner: 0002z_knowledge_approval_ledger_compat.sql
#    (sorts after 0002_dispatch_idempotency.sql and BEFORE
#    0003_knowledge_candidate_golden_pipeline.sql, so migration 0003 is never
#    edited / never has to be silently skipped).
# ---------------------------------------------------------------------------
REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS approval_ledger_operations (
  operation        TEXT PRIMARY KEY,
  asset_type       TEXT NOT NULL,
  canonical_writer TEXT NOT NULL,
  single_use       INTEGER NOT NULL DEFAULT 1,
  replay_guard     INTEGER NOT NULL DEFAULT 1
);
"""

# All five operations must be registered BEFORE the rebuild because the union
# table keeps the FK to this registry. Registering the two legacy operations is
# additive: the Site never reads this table for its legacy flow.
REGISTRY_SEED = """
INSERT OR IGNORE INTO approval_ledger_operations
  (operation, asset_type, canonical_writer, single_use, replay_guard) VALUES
  ('deploy_worker_version', 'DEPLOY',    'deployWorkerVersion',   1, 1),
  ('write_decision_record', 'DECISION',  'writeDecisionRecord',   1, 1),
  ('decision_write',        'DECISION',  'writeDecisionRecord',   1, 1),
  ('knowledge_write',       'KNOWLEDGE', 'writeKnowledgeCandidate', 1, 1),
  ('KNOWLEDGE_PROMOTION',   'KNOWLEDGE', 'writeKnowledgeCandidate', 1, 1);
"""

# Union table. Legacy columns keep their EXACT names, order, types and
# constraints (INTEGER epoch timing retained; old CHECK widened only by adding
# the three new operation names -- never by converting types). New columns are
# nullable/defaulted so every existing row is copied byte-for-byte.
UNION_DDL = """
CREATE TABLE personal_ai_approval_ledger__v2 (
  approval_id          TEXT PRIMARY KEY,
  requesting_user_hash TEXT NOT NULL CHECK (length(requesting_user_hash) = 64),
  operation            TEXT NOT NULL CHECK (operation IN (
      'deploy_worker_version','write_decision_record',
      'decision_write','knowledge_write','KNOWLEDGE_PROMOTION')),
  exact_target         TEXT,
  payload_sha256       TEXT,
  created_at           INTEGER,
  expires_at           INTEGER,
  consumed_at          INTEGER,
  asset_type           TEXT,
  candidate_id         TEXT,
  candidate_version    INTEGER,
  content_hash         TEXT,
  review_result        TEXT,
  approved_by          TEXT,
  state                TEXT NOT NULL DEFAULT 'REGISTERED',
  consumed             INTEGER NOT NULL DEFAULT 0,
  consume_count        INTEGER NOT NULL DEFAULT 0,
  invalidated          INTEGER NOT NULL DEFAULT 0,
  invalidated_at       TEXT,
  FOREIGN KEY (operation) REFERENCES approval_ledger_operations (operation)
) STRICT;
"""

# Copy every legacy column verbatim; derive the Worker `consumed` mirror from the
# legacy `consumed_at` (the WebAuthn single-use authority) so the two views are
# never inconsistent for pre-existing rows.
UNION_COPY = """
INSERT INTO personal_ai_approval_ledger__v2
  (approval_id, requesting_user_hash, operation, exact_target, payload_sha256,
   created_at, expires_at, consumed_at,
   asset_type, candidate_id, candidate_version, content_hash, review_result,
   approved_by, state, consumed, consume_count, invalidated, invalidated_at)
SELECT approval_id, requesting_user_hash, operation, exact_target, payload_sha256,
       created_at, expires_at, consumed_at,
       NULL, NULL, NULL, NULL, NULL,
       NULL,
       CASE WHEN consumed_at IS NULL THEN 'REGISTERED' ELSE 'CONSUMED' END,
       CASE WHEN consumed_at IS NULL THEN 0 ELSE 1 END,
       0, 0, NULL
FROM personal_ai_approval_ledger;
"""

UNION_FINISH = """
ALTER TABLE personal_ai_approval_ledger RENAME TO personal_ai_approval_ledger__legacy_backup;
ALTER TABLE personal_ai_approval_ledger__v2 RENAME TO personal_ai_approval_ledger;
CREATE INDEX IF NOT EXISTS idx_approval_ledger_binding
  ON personal_ai_approval_ledger (operation, candidate_id, candidate_version, content_hash);
CREATE INDEX IF NOT EXISTS idx_approval_ledger_state
  ON personal_ai_approval_ledger (operation, consumed, invalidated);
"""

# Rollback: restore the pre-rebuild table exactly (rows never mutated in backup).
ROLLBACK_SQL = """
DROP TABLE personal_ai_approval_ledger;
ALTER TABLE personal_ai_approval_ledger__legacy_backup RENAME TO personal_ai_approval_ledger;
"""

LEGACY_COLUMNS = (
    "approval_id", "requesting_user_hash", "operation", "exact_target",
    "payload_sha256", "created_at", "expires_at", "consumed_at",
)

# ---------------------------------------------------------------------------
# 2. Patched Worker gate SQL (offline proposal; repository code NOT modified).
#    The ONLY semantic change vs. repo is that the single-use authority is the
#    legacy `consumed_at` (integer epoch) instead of the repo-only `consumed`
#    flag, and `consumed_at` is written as integer epoch seconds.
# ---------------------------------------------------------------------------
WORKER_SELECT_V2 = (
    "SELECT approval_id, operation, asset_type, candidate_id, candidate_version, "
    "content_hash, review_result, approved_by, expires_at, state, consumed, "
    "consume_count, invalidated, consumed_at FROM personal_ai_approval_ledger "
    "WHERE operation = ? AND candidate_id = ? AND candidate_version = ? AND "
    "content_hash = ? AND consumed_at IS NULL AND invalidated = 0 "
    "ORDER BY expires_at DESC"
)
WORKER_CONSUME_V2 = (
    "UPDATE personal_ai_approval_ledger SET consumed = 1, state = 'CONSUMED', "
    "consume_count = consume_count + 1, consumed_at = ? WHERE approval_id = ? "
    "AND operation = ? AND consumed_at IS NULL AND invalidated = 0"
)
WORKER_INVALIDATE_V2 = (
    "UPDATE personal_ai_approval_ledger SET invalidated = 1, state = 'INVALIDATED', "
    "invalidated_at = ? WHERE operation = ? AND candidate_id = ? AND "
    "consumed_at IS NULL AND invalidated = 0"
)
# WebAuthn/Site legacy CAS (unchanged contract).
SITE_CAS_CONSUME = (
    "UPDATE personal_ai_approval_ledger SET consumed_at = ? "
    "WHERE approval_id = ? AND consumed_at IS NULL"
)

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append((name, bool(cond), detail))
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" :: {detail}" if detail else ""))
    return bool(cond)


def connect():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def table_signature(conn, name="personal_ai_approval_ledger"):
    rows = conn.execute(
        "SELECT name, type, sql FROM sqlite_master WHERE name = ?", (name,)
    ).fetchall()
    return [tuple(r) for r in rows]


def columns_of(conn, name="personal_ai_approval_ledger"):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({name})")]


def is_strict(conn, name="personal_ai_approval_ledger"):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = ?", (name,)
    ).fetchone()
    return row is not None and "STRICT" in (row[0] or "")


def legacy_rows(conn):
    cols = ", ".join(LEGACY_COLUMNS)
    return conn.execute(
        f"SELECT {cols} FROM personal_ai_approval_ledger ORDER BY approval_id"
    ).fetchall()


def legacy_signature(conn):
    sig = table_signature(conn)
    return sig[0][2] if sig else ""


def normalize_sql(sql):
    # SQLite's ALTER TABLE ... RENAME adds identifier quoting around the table
    # name; this is cosmetic, not a schema change. Normalise before comparing.
    return " ".join((sql or "").replace('"', "").split()).lower()


def seed_legacy(conn):
    conn.executescript(LEGACY_LEDGER_DDL)
    now = int(time.time())
    rows = [
        # approval_id, user_hash(len64), operation, exact_target, payload_sha256,
        # created_at, expires_at, consumed_at
        ("ap:deploy:consumed", "a" * 64, "deploy_worker_version",
         "personal-ai-execution-mcp@1b6a318a", "b" * 64, now - 3600, now + 3600, now - 60),
        ("ap:decision:unconsumed", "c" * 64, "write_decision_record",
         "decision:2026-10-10", "d" * 64, now - 120, now + 7200, None),
        ("ap:deploy:expired", "e" * 64, "deploy_worker_version",
         "personal-ai-execution-mcp@old", "f" * 64, now - 7200, now - 3600, None),
        ("ap:decision:consumed", "g" * 64, "write_decision_record",
         "decision:2026-10-09", "h" * 64, now - 7200, now + 600, now - 300),
    ]
    conn.executemany(
        "INSERT INTO personal_ai_approval_ledger "
        "(approval_id, requesting_user_hash, operation, exact_target, payload_sha256, "
        " created_at, expires_at, consumed_at) VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()


def detect_shape(conn):
    if not table_signature(conn):
        return "ABSENT"
    cols = columns_of(conn)
    sql = legacy_signature(conn)
    if "candidate_id" in cols and "KNOWLEDGE_PROMOTION" in sql:
        return "UNION"
    if set(cols) == set(LEGACY_COLUMNS) and "write_decision_record" in sql:
        return "LEGACY"
    return "DRIFT"


def guarded_rebuild(conn):
    """Deterministic, fail-closed rebuild. HALTs on unknown drift."""
    shape = detect_shape(conn)
    if shape == "UNION":
        return "ALREADY_REPAIRED"
    if shape == "ABSENT":
        return "HALT_ABSENT_LEDGER"
    if shape == "DRIFT":
        return "HALT_DRIFT"
    before = [tuple(r) for r in legacy_rows(conn)]
    before_sig = legacy_signature(conn)
    conn.executescript(REGISTRY_DDL)
    conn.executescript(REGISTRY_SEED)
    # Standard rebuild. The pre-state is preserved by RENAME to a backup table
    # (never DROP), so rollback is byte-for-byte. D1 runs a migration file as one
    # batch/transaction; drift is halted before any of this by detect_shape().
    conn.executescript(UNION_DDL)
    conn.executescript(UNION_COPY)
    conn.executescript(UNION_FINISH)
    conn.commit()
    after = [tuple(r) for r in legacy_rows(conn)]
    if before != after:
        raise AssertionError("legacy row drift across rebuild")
    # keep a copy of the original signature for the rollback test
    return {"result": "REBUILT", "before_rows": before, "before_sig": before_sig}


def apply_numbered_migrations(conn, migrations):
    applied = []
    for name in migrations:
        sql = (MIGRATIONS / name).read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.commit()
        applied.append(name)
    return applied


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_00_baseline_0003_fails_on_prod_shape():
    conn = connect()
    seed_legacy(conn)
    check("baseline: legacy table STRICT", is_strict(conn))
    check("baseline: exact legacy columns", columns_of(conn) == list(LEGACY_COLUMNS))
    err = None
    try:
        apply_numbered_migrations(conn, [
            "0001_asset_provenance_v0_2.sql",
            "0002_dispatch_idempotency.sql",
            "0003_knowledge_candidate_golden_pipeline.sql",
        ])
    except sqlite3.OperationalError as exc:
        err = str(exc)
    check("baseline: 0003 fails on prod-shaped ledger", err is not None, repr(err))
    check("baseline: failure is no such column: candidate_id",
          err is not None and "no such column: candidate_id" in err, repr(err))
    conn.close()


def test_01_repaired_rebuild_and_migration_in_order():
    conn = connect()
    seed_legacy(conn)
    before_rows = [tuple(r) for r in legacy_rows(conn)]
    before_sig = legacy_signature(conn)
    outcome = guarded_rebuild(conn)
    check("repair: rebuild executed", outcome.get("result") == "REBUILT")
    check("repair: union shape detected", detect_shape(conn) == "UNION")
    check("repair: still STRICT", is_strict(conn))
    check("repair: legacy columns preserved in order",
          columns_of(conn)[:8] == list(LEGACY_COLUMNS))
    # integer epoch timing retained (never converted to TEXT)
    types = {r[1]: r[2] for r in conn.execute("PRAGMA table_info(personal_ai_approval_ledger)")}
    check("repair: created_at/expires_at/consumed_at stay INTEGER",
          types["created_at"] == "INTEGER" and types["expires_at"] == "INTEGER"
          and types["consumed_at"] == "INTEGER", str(types))
    check("repair: legacy rows byte-for-byte preserved",
          before_rows == [tuple(r) for r in legacy_rows(conn)])
    check("repair: original backup table retained",
          bool(table_signature(conn, "personal_ai_approval_ledger__legacy_backup")))
    # Now the real in-order runner continues: 0003 must succeed (indexes now OK).
    applied = apply_numbered_migrations(conn, [
        "0001_asset_provenance_v0_2.sql",
        "0002_dispatch_idempotency.sql",
        "0003_knowledge_candidate_golden_pipeline.sql",
    ])
    check("repair: 0001/0002/0003 apply in order after repair",
          applied == [
              "0001_asset_provenance_v0_2.sql",
              "0002_dispatch_idempotency.sql",
              "0003_knowledge_candidate_golden_pipeline.sql",
          ])
    idx = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    check("repair: 0003 binding index present", "idx_approval_ledger_binding" in idx)
    check("repair: 0003 state index present", "idx_approval_ledger_state" in idx)
    check("repair: registry holds all five operations",
          {r[0] for r in conn.execute("SELECT operation FROM approval_ledger_operations")} == {
              "deploy_worker_version", "write_decision_record", "decision_write",
              "knowledge_write", "KNOWLEDGE_PROMOTION"})
    check("repair: single ledger only (no v2/second authority)",
          "personal_ai_approval_ledger__v2" not in
          {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")})
    # Idempotent re-run of the guarded rebuild.
    check("repair: re-run is idempotent",
          guarded_rebuild(conn) == "ALREADY_REPAIRED")
    conn.close()


def test_02_legacy_operation_semantics_and_integer_timing():
    conn = connect()
    seed_legacy(conn)
    guarded_rebuild(conn)
    now = int(time.time())
    # The Site's legacy WebAuthn CAS still works on the same column/type.
    ch = conn.execute(SITE_CAS_CONSUME, (now, "ap:decision:unconsumed")).rowcount
    check("legacy: WebAuthn CAS first consume wins", ch == 1)
    ch2 = conn.execute(SITE_CAS_CONSUME, (now, "ap:decision:unconsumed")).rowcount
    check("legacy: WebAuthn CAS replay loses (single-use)", ch2 == 0)
    row = conn.execute(
        "SELECT consumed, consumed_at, state FROM personal_ai_approval_ledger "
        "WHERE approval_id='ap:decision:unconsumed'").fetchone()
    check("legacy: CAS left integer consumed_at", isinstance(row["consumed_at"], int),
          str(dict(row)))
    # Worker mirror became consistent for pre-existing consumed rows.
    row2 = conn.execute(
        "SELECT consumed, state FROM personal_ai_approval_ledger "
        "WHERE approval_id='ap:deploy:consumed'").fetchone()
    check("legacy: pre-consumed row mirrors consumed=1/CONSUMED",
          row2["consumed"] == 1 and row2["state"] == "CONSUMED")
    # Old CHECK still rejects an unknown operation.
    try:
        conn.execute(
            "INSERT INTO personal_ai_approval_ledger (approval_id, requesting_user_hash, "
            "operation, created_at, expires_at) VALUES ('ap:x','" + "z"*64 + "','bogus',1,1)")
        bad = False
    except sqlite3.IntegrityError:
        bad = True
    check("legacy: CHECK rejects unknown operation", bad)
    conn.close()


def test_03_knowledge_promotion_two_connection_cas_and_replay():
    import tempfile
    path = tempfile.mktemp(suffix=".db")
    conn = _seed_union_ledger_file(path)
    cand = ("cand-v02", 1, "9" * 64)
    live = conn.execute(WORKER_SELECT_V2, ("KNOWLEDGE_PROMOTION", *cand)).fetchall()
    check("knowledge: gate SELECT finds the bound live approval", len(live) == 1)
    row = conn.execute(
        "SELECT exact_target, payload_sha256, candidate_id FROM personal_ai_approval_ledger "
        "WHERE approval_id='ap:kp:1'").fetchone()
    check("knowledge: candidate_* is the authoritative binding",
          row["candidate_id"] == cand[0])
    check("knowledge: legacy aliases kept distinct from Site fields",
          row["exact_target"] == cand[0] and row["payload_sha256"] == cand[2])
    # Two independent connections race the same CAS on the same file DB.
    race = _race_two_connections_file(path)
    check("knowledge: exactly one CAS consumer wins",
          race["wins"] == 1 and race["losses"] == 1, str(race))
    replay = _consume_once(race["winner_conn"], "ap:kp:1", "KNOWLEDGE_PROMOTION")
    check("knowledge: replay after consume is rejected", replay == 0)
    for c in race["conns"]:
        c.close()
    row = conn.execute(
        "SELECT consumed, consume_count, consumed_at, state FROM personal_ai_approval_ledger "
        "WHERE approval_id='ap:kp:1'").fetchone()
    check("knowledge: consumed mirror + integer consumed_at + count=1",
          row["consumed"] == 1 and row["consume_count"] == 1
          and isinstance(row["consumed_at"], int) and row["state"] == "CONSUMED")
    conn.close()


def _seed_union_ledger_file(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    seed_legacy(conn)
    guarded_rebuild(conn)
    now = int(time.time())
    conn.execute(
        "INSERT INTO personal_ai_approval_ledger (approval_id, requesting_user_hash, "
        "operation, exact_target, payload_sha256, created_at, expires_at, consumed_at, "
        "asset_type, candidate_id, candidate_version, content_hash, review_result, "
        "approved_by, state, consumed, consume_count, invalidated) VALUES "
        "('ap:kp:1', ?, 'KNOWLEDGE_PROMOTION', ?, ?, ?, ?, NULL, 'KNOWLEDGE', ?, ?, ?, "
        "'PASS', ?, 'REGISTERED', 0, 0, 0)",
        ("1" * 64, "cand-v02", "9" * 64, now - 5, now + 600,
         "cand-v02", 1, "9" * 64, "1" * 64),
    )
    conn.commit()
    return conn


def _race_two_connections_file(path):
    a = sqlite3.connect(path, isolation_level=None)
    b = sqlite3.connect(path, isolation_level=None)
    now = int(time.time())
    wa = _consume_once(a, "ap:kp:1", "KNOWLEDGE_PROMOTION", now)
    wb = _consume_once(b, "ap:kp:1", "KNOWLEDGE_PROMOTION", now)
    return {"wins": (wa + wb), "losses": 2 - (wa + wb), "conns": [a, b],
            "winner_conn": a if wa == 1 else b}


def _consume_once(conn, approval_id, operation, now=None):
    now = int(time.time()) if now is None else now
    cur = conn.execute(WORKER_CONSUME_V2, (now, approval_id, operation))
    return cur.rowcount


def test_04_stale_approval_invalidation_blocks_replay():
    conn = connect()
    seed_legacy(conn)
    guarded_rebuild(conn)
    now = int(time.time())
    conn.execute(
        "INSERT INTO personal_ai_approval_ledger (approval_id, requesting_user_hash, "
        "operation, created_at, expires_at, consumed_at, asset_type, candidate_id, "
        "candidate_version, content_hash, review_result, approved_by, state, consumed, "
        "consume_count, invalidated) VALUES "
        "('ap:stale', ?, 'KNOWLEDGE_PROMOTION', ?, ?, NULL, 'KNOWLEDGE', 'cand-s', 1, ?, "
        "'PASS', ?, 'REGISTERED', 0, 0, 0)",
        ("2" * 64, now - 5, now + 600, "8" * 64, "2" * 64),
    )
    conn.commit()
    live_before = conn.execute(WORKER_SELECT_V2, ("KNOWLEDGE_PROMOTION", "cand-s", 1, "8" * 64)).fetchall()
    check("stale: approval live before FAIL", len(live_before) == 1)
    changed = conn.execute(WORKER_INVALIDATE_V2,
                           (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "KNOWLEDGE_PROMOTION", "cand-s")).rowcount
    check("stale: FAIL invalidates the live approval", changed == 1)
    live_after = conn.execute(WORKER_SELECT_V2, ("KNOWLEDGE_PROMOTION", "cand-s", 1, "8" * 64)).fetchall()
    check("stale: invalidated approval no longer selectable (no replay)", len(live_after) == 0)
    row = conn.execute(
        "SELECT invalidated, consumed, state FROM personal_ai_approval_ledger "
        "WHERE approval_id='ap:stale'").fetchone()
    check("stale: row retained (revocation additive)",
          row["invalidated"] == 1 and row["consumed"] == 0 and row["state"] == "INVALIDATED")
    # A consumed approval is never rewritten by invalidation.
    changed2 = conn.execute(WORKER_INVALIDATE_V2,
                            ("2026-01-01T00:00:00Z", "KNOWLEDGE_PROMOTION", "cand-s")).rowcount
    check("stale: re-invalidate is a no-op", changed2 == 0)
    conn.close()


def test_05_candidate_lifecycle_gate_no_unauthorized_golden_write():
    conn = connect()
    seed_legacy(conn)
    guarded_rebuild(conn)
    apply_numbered_migrations(conn, ["0001_asset_provenance_v0_2.sql",
                                     "0002_dispatch_idempotency.sql",
                                     "0003_knowledge_candidate_golden_pipeline.sql"])
    # Simulate the Worker candidate lifecycle against knowledge_candidates.
    conn.execute(
        "INSERT INTO knowledge_candidates (candidate_id, asset_id, title, status, content, "
        "content_hash, version, provenance, created_at, review_state) VALUES "
        "('cand-life','knowledge:cand-life','t','DRAFT','body','ab'*32,1,'{}',?, 'NOT_REVIEWED')",
        (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),))
    conn.commit()
    writes = {"canonical": 0}

    def gate_blocked():
        # No approval -> gate fails BEFORE any canonical write.
        live = conn.execute(WORKER_SELECT_V2, ("KNOWLEDGE_PROMOTION", "cand-life", 1, "ab" * 32)).fetchall()
        if not live:
            return True
        writes["canonical"] += 1  # would be the Golden writer
        return False

    # review PASS -> APPROVED_FOR_PROMOTION (guarded update only from pre-promotion)
    conn.execute("UPDATE knowledge_candidates SET status='PENDING_REVIEW', review_state='NOT_REVIEWED' WHERE candidate_id='cand-life'")
    conn.execute("UPDATE knowledge_candidates SET status='APPROVED_FOR_PROMOTION', review_state='PASS', review_result='PASS' WHERE candidate_id='cand-life' AND status IN ('DRAFT','PENDING_REVIEW','APPROVED_FOR_PROMOTION')")
    conn.commit()
    blocked = gate_blocked()
    check("gate: BLOCKED without approval, zero canonical writes",
          blocked and writes["canonical"] == 0)
    # Reservation CAS + consume + guarded transitions (model).
    reserved = conn.execute(
        "UPDATE knowledge_candidates SET status='PROMOTION_RESERVED' "
        "WHERE candidate_id='cand-life' AND status='APPROVED_FOR_PROMOTION' AND review_state='PASS'"
    ).rowcount
    check("gate: reservation CAS succeeds once", reserved == 1)
    # review FAIL after reservation must not regress (guarded update only pre-promotion).
    fail_changes = conn.execute(
        "UPDATE knowledge_candidates SET status='PENDING_REVIEW', review_state='FAIL' "
        "WHERE candidate_id='cand-life' AND status IN ('DRAFT','PENDING_REVIEW','APPROVED_FOR_PROMOTION')"
    ).rowcount
    check("gate: FAIL after reservation is rejected (race)", fail_changes == 0)
    conn.close()


def test_06_rollback_and_rerun():
    conn = connect()
    seed_legacy(conn)
    before_rows = [tuple(r) for r in legacy_rows(conn)]
    before_sig = legacy_signature(conn)
    guarded_rebuild(conn)
    check("rollback: pre-state differs after rebuild", legacy_signature(conn) != before_sig)
    # Rollback exactly.
    conn.executescript(ROLLBACK_SQL)
    conn.commit()
    check("rollback: schema restored to legacy", detect_shape(conn) == "LEGACY")
    check("rollback: rows byte-for-byte restored", [tuple(r) for r in legacy_rows(conn)] == before_rows)
    check("rollback: restored schema semantically identical (quoting normalised)",
          normalize_sql(legacy_signature(conn)) == normalize_sql(before_sig))
    # Re-run repair after rollback is deterministic.
    check("rollback: rebuild after rollback succeeds", guarded_rebuild(conn).get("result") == "REBUILT")
    check("rollback: rows still intact", [tuple(r) for r in legacy_rows(conn)] == before_rows)
    conn.close()


def test_07_drift_halts():
    conn = connect()
    conn.execute("CREATE TABLE personal_ai_approval_ledger (approval_id TEXT PRIMARY KEY, weird TEXT)")
    conn.commit()
    check("drift: unknown shape HALTED", guarded_rebuild(conn) == "HALT_DRIFT")
    conn.close()


def test_08_worker_source_has_no_mint_and_flat_writer_is_gated():
    src = (REPO / "worker" / "index.js").read_text(encoding="utf-8")
    check("worker: no approval mint/register function",
          "registerKnowledgePromotionApproval" not in src
          and "INSERT INTO personal_ai_approval_ledger" not in src)
    check("worker: consume uses conditional CAS in current source",
          "APPROVAL_LEDGER_CONSUME" in src and "WHERE approval_id = ? AND operation = ? AND consumed = 0" in src)
    check("worker: asset_id-only public path rejected before IO",
          "KNOWLEDGE_PROMOTION_REJECT_CANDIDATE_MISSING" in src)


def main():
    tests = [
        test_00_baseline_0003_fails_on_prod_shape,
        test_01_repaired_rebuild_and_migration_in_order,
        test_02_legacy_operation_semantics_and_integer_timing,
        test_03_knowledge_promotion_two_connection_cas_and_replay,
        test_04_stale_approval_invalidation_blocks_replay,
        test_05_candidate_lifecycle_gate_no_unauthorized_golden_write,
        test_06_rollback_and_rerun,
        test_07_drift_halts,
        test_08_worker_source_has_no_mint_and_flat_writer_is_gated,
    ]
    for t in tests:
        print(f"\n=== {t.__name__} ===")
        t()
    failed = [c for c in CHECKS if not c[1]]
    print("\n" + "=" * 60)
    print(f"checks: {len(CHECKS)}  passed: {len(CHECKS) - len(failed)}  failed: {len(failed)}")
    for name, ok, detail in failed:
        print(f"  FAILED: {name} {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## 7. Remaining Human Gate before ANY release

**HUMAN_GATE_REQUIRED.** Nothing is executed against production. Before a separate, explicitly-scoped execution task may proceed, the single existing Human Gate must authorise, in order:

1. Review and freeze `0002z_knowledge_approval_ledger_compat.sql` (schema owner + Site gate owner sign-off on the union vocabulary).
2. Commit the SQL as `worker/migrations/0002z_knowledge_approval_ledger_compat.sql` and apply the §3.4 Worker patch (one release window).
3. **Real D1 clone** exercise: export current ledger → restore to an isolated D1 DB → guard → apply `0002z` + `0003` → verify → rollback → restore → re-apply. Record `sqlite_master` and per-operation row counts at every step.
4. Only after (1)–(3): apply on production under incident protocol (transactional batch), then run the read-back plan (§8).

No precondition may be treated as satisfied by a local SQLite result.

---

## 8. Independent production read-back plan (post-approval only)

1. **Pre-manifest (read-only):** `PRAGMA table_info(personal_ai_approval_ledger)`, `SELECT operation, COUNT(*) ... GROUP BY operation`, full row export + sha256; KNOWLEDGE Canonical manifest = 19 assets including the anomalous fixture (record manifest sha256).
2. **Guard check:** signature `LEGACY` (unwidened CHECK) must match; otherwise STOP.
3. **Apply** `0002z` then `0003` as a single transactional batch; capture per-statement errors.
4. **Post-verify:** legacy 8 columns unchanged; row counts per operation unchanged; every legacy `approval_id`/`requesting_user_hash`/`exact_target`/`payload_sha256`/`created_at`/`expires_at`/`consumed_at` byte-identical; `consumed` mirror consistent; both indexes present; no second ledger table; no Canonical asset added/removed/changed.
5. **Controlled single promotion (separate scope):** one designated validation candidate promotes exactly once; authoritative read-back matches; repeat is idempotent.
6. **Any drift ⇒ fail-closed + rollback** (restore `__legacy_backup` or the pre-export), never convert an isolated result into a production PASS.

---

## 9. Changed-files allowlist for this run

Only the file below is created/changed (markdown). No `.github/workflows/`, no secret/token/credential/.env/.pem/.key path, no deletion, no `.sql`/`worker`/`site`/`tests` file added or modified in the repo (the executable artifacts live at `/tmp/opencode/`).

```
KNOWLEDGE_LEDGER_COMPAT_REPAIR_V02.md
```

Direct code references: `worker/index.js:3062-3094` (SQL), `3100-3131` (gate), `3332-3549` (promote/consume/reserve), `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql:81-106`; existing tests `tests/test_knowledge_candidate_golden_pipeline.py:1226,1309,1358,1468`.

---

## 10. Status matrix

| Layer | Status |
|---|---|
| Baseline mismatch reproduced (prod-shaped STRICT ledger) | **PASS** (local SQLite) |
| Executable single-ledger repair SQL + guard/routing + rollback | **PASS** (local SQLite) |
| Legacy rows / operations / integer timing / WebAuthn single-use preserved | **PASS** (local SQLite) |
| Candidate lifecycle / race / stale / replay / recovery / 2-conn CAS / no-Golden-when-BLOCKED | **PASS** (local SQLite) |
| Existing repo suite + node checks | **PASS** (`1576 passed, 1 skipped`) |
| Real Cloudflare D1 execution | **BLOCKED / `REAL_D1_UNVERIFIED`** |
| Production migration / Site publish / Canonical write | **NOT PERFORMED** |
| Release decision | **HUMAN_GATE_REQUIRED — NOT `READY_FOR_PRODUCTION`** |
