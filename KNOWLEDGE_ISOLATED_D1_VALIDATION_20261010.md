# KNOWLEDGE_ISOLATED_D1_VALIDATION_20261010

- Task: `cf-44b8447f89a1` — `KNOWLEDGE_PRODUCTION_BASELINE_AND_ISOLATED_D1_RELEASE_PREFLIGHT_V0.1`
- Document status: **PARTIAL / BLOCKED** — SQLite isolation reproduces the production mismatch; **real Cloudflare D1 is `REAL_D1_UNVERIFIED`** (no transport/credential in this environment)
- All writes below are confined to `/tmp/opencode` (outside the repo) and to pytest `tmp_path`. **No production D1, no production Worker, no Canonical store was touched.**
- Repo pin: `1b7dabc3b0c48afc773dfbb77f2276007148d258`; `worker/migrations/0003…sql` sha256 `9a51d3a53ad5ac3e78e07fc9720ad5492443f5a1f6ac677018570fdfc337927a`.

> **Transport disclosure (must not be overstated).** `sqlite3` here is CPython 3.11.17 bundled SQLite `3.45.1`. This is a **local SQLite simulation**, not Cloudflare D1. There is no `CLOUDFLARE_API_TOKEN` / `CF_API_TOKEN` / `CLOUDFLARE_API_KEY` in the environment (`env | grep -i cloudflare` empty; consistent with `reports/production_deploy_v0.1.json`). No credential was simulated, no production DB was opened, and no second durable Canonical DB was created. Real-D1 concurrency/STRICT/CHECK behaviour remains **UNVERIFIED**. The local SQLite semantics for `STRICT`, `CHECK`, `CREATE INDEX … (missing column)` and conditional `UPDATE` are directionally faithful for the migration-compatibility question below (SQLite D1 is built on SQLite), but they are **not** a substitute for a real D1 run.

---

## 1. Scenario A — empty SQLite DB (what the existing suite exercises)

Command: `python3 /tmp/opencode/prod_schema_repro.py` (scenario A part).

```
sqlite_version = 3.45.1
0001 OK
0002 OK
0003 OK
created ledger cols: approval_id, operation, asset_type, candidate_id, candidate_version,
  content_hash, review_result, approved_by, expires_at, state, consumed, consume_count,
  invalidated, invalidated_at, created_at, consumed_at
```

Interpretation: on a **fresh empty** database `0003` builds the repo's ledger schema. This is exactly why the shipped tests pass and gives **false confidence** for production. `tests/test_knowledge_candidate_golden_pipeline.py:1226` models only an empty DB plus `assets`/`asset_versions`.

---

## 2. Scenario B — production-similar DB (STRICT pre-existing ledger): migration FAILS

Setup in isolation: create `personal_ai_approval_ledger` **STRICT** with the exact production columns/constraints from the baseline report, seed `assets` (19 KNOWLEDGE incl. the anomalous fixture) and `asset_versions`, then apply `0001` + `0002` + `0003` in order.

Command: `python3 /tmp/opencode/prod_schema_repro.py` and `python3 /tmp/opencode/isolated_matrix.py` (D1 section).

```
0001 OK
0002 OK
0003 on production-similar DB -> OperationalError: no such column: candidate_id
```

Object diff (before → after `0003` attempt), from `isolated_matrix.py`:

```
added:
  table:knowledge_candidates
  table:approval_ledger_operations
  table:asset_provenance_events      (from 0001)
  table:asset_supersessions          (from 0001)
  table:task_dispatch_markers        (from 0002)
  index:idx_knowledge_candidates_status
  index:idx_knowledge_candidates_asset
  index:idx_asset_provenance_events_asset
  index:idx_asset_provenance_events_type
  index:idx_asset_supersessions_successor
  index:idx_task_dispatch_markers_parent
  index:idx_task_dispatch_markers_child
  index:idx_task_dispatch_markers_state
removed: (none)
ledger_cols_unchanged:
  approval_id, requesting_user_hash, operation, exact_target, payload_sha256,
  created_at, expires_at, consumed_at
idx_approval_ledger_binding_present: false   <-- NOT created
idx_approval_ledger_state_present:   false   <-- NOT created
```

**Result:** `0003` is **not additive-safe against the real production table**.
1. `CREATE TABLE IF NOT EXISTS personal_ai_approval_ledger` is a **silent no-op** (table exists) — no upgrade.
2. The very next statement `CREATE INDEX IF NOT EXISTS idx_approval_ledger_binding ON personal_ai_approval_ledger (operation, candidate_id, candidate_version, content_hash)` fails with **`no such column: candidate_id`**.
3. Because a migration runner aborts on the first failing statement, `idx_approval_ledger_state` is never created either; the migration is left partially applied (`knowledge_candidates` and `approval_ledger_operations` exist, ledger index objects do not).

This is **tested, not hypothesised**, as required by STAGE 1.

---

## 3. Scenario C — CHECK constraint blocks the required operations

Against the production-shaped STRICT ledger, inserting the operations the worker needs fails:

```
KNOWLEDGE_PROMOTION insert -> IntegrityError CHECK constraint failed:
  operation IN ('deploy_worker_version','write_decision_record')
knowledge_write insert     -> IntegrityError CHECK constraint failed:
  operation IN ('deploy_worker_version','write_decision_record')
```

SQLite (hence D1) cannot drop or modify a `CHECK` constraint in place; relaxing it requires a **table rebuild** (copy → drop → rename). This is the core remediation constraint and cannot be solved by an additive `ALTER TABLE ADD COLUMN`. It also matches the Site's fail-closed state `KNOWLEDGE_APPROVAL_OPERATION_SCHEMA_REQUIRED`.

---

## 4. Scenario D — worker runtime query on the production-shaped ledger fails

The worker's live approval lookup (`worker/index.js:3089`) executed against the production-shaped table:

```
worker APPROVAL_LEDGER_SELECT -> OperationalError: no such column: asset_type
```

Even a hypothetically "index-only" repair would leave the gate unable to read/consume a production approval.

---

## 5. Scenario E — the repo's *adapted* schema matrix (genuinely isolated, SQLite)

Applied `0001 + 0002 + 0003` to a fresh isolated file DB and exercised the gate semantics. This validates the **logic** of the candidate/approval design, **conditional on** the ledger schema matching the repo (which production does **not**). Command: `python3 /tmp/opencode/isolated_matrix.py` (D2 section).

| Exercise | Command primitive | Result | Expected |
|---|---|---|---|
| Idempotent re-apply of `0003` | `executescript(M3)` twice | `stable: true`, 19 objects | no drift |
| Seeded corpus | insert 18 + 1 anomalous assets | `19` | 19 |
| Single-use approval, 2 connections | conditional `UPDATE … WHERE consumed=0` on 2 connections | `(consumed=1, consume_count=1)` | exactly one winner |
| Replay of consumed approval | same `UPDATE` again | `(1, 1)` unchanged | replay rejected |
| Stale approval after review FAIL | `UPDATE … SET invalidated=1 … WHERE consumed=0` | `consumed=0, invalidated=1, state=INVALIDATED` | revoked, retained |
| review-FAIL vs promotion-reservation CAS | reserve first (2 conn), then FAIL guarded `UPDATE` | `status=PROMOTION_RESERVED`, `review_state=PASS` | FAIL after claim is a no-op |
| No duplicate Golden | canonical write keyed by content_hash twice | `WRITTEN` then `IDEMPOTENT`, `versions=1` | one row |
| No writes when gate rejects | staged DRAFT, no approval | `live_approvals=0, canonical_assets=0` | fail-closed |

These mirror the shipped assertions in `tests/test_knowledge_candidate_golden_pipeline.py` (all green on the pinned commit; see §6).

---

## 6. Existing regression commands and results (recorded)

| Command | Result |
|---|---|
| `python -m pytest -q` | `1576 passed, 1 skipped in 69.55s` |
| `python -m pytest -q tests/test_knowledge_candidate_golden_pipeline.py -k "isolated or race or migration or stale or duplicate" -v` | `17 passed, 24 deselected in 0.54s` |
| `node --check worker/index.js` | OK (exit 0) |
| `node --check site/worker/index.js` | OK (exit 0) |

Existing coverage maps to the matrix above:
`test_isolated_sqlite_migration_is_idempotent_and_preserves_history`
(`test_knowledge_candidate_golden_pipeline.py:1226`), `…atomic_approval_consume_is_single_use`
(`:1309`), `…fail_revokes_stale_approval` (`:1358`), and the `test_worker_race_*`
concurrency tests (`:1468+`).

**Critical coverage gap:** every isolated migration test starts from an **empty** DB. No test reproduces a **pre-existing, production-shaped STRICT ledger**, so the suite could not detect the mismatch that this task reproduces.

---

## 7. Real Cloudflare D1 status

| Item | Status |
|---|---|
| Real D1 transport available | **NO** (`CLOUDFLARE_API_TOKEN`/`CF_API_TOKEN`/`CLOUDFLARE_API_KEY` absent; wrangler unauthenticated) |
| Real D1 migration attempted | **NO** (boundary: no production migration) |
| Real D1 rebuild/backup/restore | **NOT PERFORMED** |
| Real D1 STRICT/CHECK behaviour | **REAL_D1_UNVERIFIED** (inferred from SQLite only) |
| Credentials simulated | **NO** |
| Production DB used as test DB | **NO** |
| Second durable Canonical/ledger created | **NO** |

Fail-closed disposition: `STAGE 2 real-D1 = BLOCKED / REAL_D1_UNVERIFIED`. No retry loop; no 429.

---

## 8. STATUS

| Layer | STATUS |
|---|---|
| Local SQLite empty-DB migration | PASS |
| Local SQLite production-similar migration (mismatch reproduction) | PASS (mismatch proven) |
| Local SQLite CHECK/worker-query incompatibility | PASS (incompatibility proven) |
| Local SQLite gate CAS/idempotency/replay/stale/no-duplicate | PASS |
| Real Cloudflare D1 migration/idempotency | **BLOCKED / REAL_D1_UNVERIFIED** |
| Production deploy | **NOT ATTEMPTED** |

No production object was read back independently in this environment; the production ledger/corpus in `KNOWLEDGE_PRODUCTION_BASELINE_20261010.md` is Brain-supplied evidence, and the mismatch it implies is now reproduced in isolation.
