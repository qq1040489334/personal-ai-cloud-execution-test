# KNOWLEDGE_PRODUCTION_BASELINE_20261010

- Task: `cf-44b8447f89a1` — `KNOWLEDGE_PRODUCTION_BASELINE_AND_ISOLATED_D1_RELEASE_PREFLIGHT_V0.1`
- Project: `personal-ai-knowledge-golden`
- Document status: **PARTIAL** (repo pin PASS; production read-back is Brain-supplied evidence, not independently re-read from this environment; migration compatibility **BLOCKED**)
- Generated: 2026-10-10 (UTC), read-only
- Boundary honoured: no production deploy, no production D1 migration/schema change, no Canonical write, no Site publish, no approval mint/consume, no secret/OAuth/binding/permission change. No second Canonical or approval authority created.

---

## 0. Repo pin read-back (independently verified in this environment)

| Item | Value | Evidence |
|---|---|---|
| `git rev-parse HEAD` | `1b7dabc3b0c48afc773dfbb77f2276007148d258` | matches the task pin `1b7dabc3b0c48afc773dfbb77f2276007148d258` |
| working tree | clean (`git status --porcelain` empty) | `git status` |
| `worker/index.js` sha256 | `3ef2817b75fd01db60bc5784f5c11d5fbbde58acc918accabf1347aa2ea01054` | `sha256sum` |
| `worker/index.js` size / lines | `179680` bytes / `4138` lines | `wc -c`, `wc -l` |
| `worker/migrations/0001_asset_provenance_v0_2.sql` | sha256 `c5417eee980b00425775d20d0541b5795094314ef8e75c361a45027019b98fab` | `sha256sum` |
| `worker/migrations/0002_dispatch_idempotency.sql` | sha256 `364db94d4c29de6806714ac8c0f925325a013f7087bbb60c86080e923b0a2f78` | `sha256sum` |
| `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql` | sha256 `9a51d3a53ad5ac3e78e07fc9720ad5492443f5a1f6ac677018570fdfc337927a` | `sha256sum` |
| `node --check worker/index.js` | OK (exit 0) | `node --check` |
| `node --check site/worker/index.js` | OK (exit 0) | `node --check` |
| full suite | `1576 passed, 1 skipped in 69.55s` | `python -m pytest -q` |

The "1576 passed" claim is **independently reproduced** on the pinned commit (not trusted from prose). The prior stale-approval fix and the review-FAIL / promotion-reservation CAS are present in `worker/index.js:3069-3094, 3347-3549` and were not reverted.

### Repo-vs-production source drift (noted, informational)

`worker/PRODUCTION-BASELINE.json` records the *older* Quick-Edit baseline version `3e2fed43` with `source_sha256=8D0EFBDC…`, `source_bytes=55278`, `source_lines=1543`. The pinned repo source is `179680` bytes / `4138` lines. The repo source has therefore never been the deployed artifact verbatim; the deployed artifact for this task is version `1b6a318a-…` (below). This reinforces that *repo source hash is not a production identity* and that production must be read back directly.

---

## 1. Fresh production evidence (Brain read-back — supplied, not independently re-read here)

The following is the production evidence supplied with the task contract ("Brain 已用生产 GET 和独立 Cloud Asset Read 回读"). This environment has **no Cloudflare credential** (`env | grep -i cloudflare` empty; no `CLOUDFLARE_API_TOKEN` / `CF_API_TOKEN` / `CLOUDFLARE_API_KEY`; `npx wrangler whoami` unauthenticated — consistent with `reports/production_deploy_v0.1.json`). Therefore these values are recorded **as supplied** and flagged `independently_verified: false` in this environment.

### 1.1 Worker `personal-ai-execution-mcp`

| Field | Value |
|---|---|
| `deployment_id` | `2626653a-c984-4160-942f-ed8ce3b51c97` |
| `version_id` | `1b6a318a-c40c-413c-b62e-3d5497e4d0c2` |
| `binding_hash` | `bd15a472be5527c50f892d851c71f610fc6ce6a2bdf38abf7b8efbdf0534c36d` |
| traffic | `100% active` |
| account | `78a22a0699aa94a39d8f7bfdbac18249` (`worker/PRODUCTION-BASELINE.json`) |

### 1.2 Site `v0.3.6` knowledge approval gate

| Field | Value |
|---|---|
| gate state | `BLOCKED` |
| reason | `KNOWLEDGE_APPROVAL_OPERATION_SCHEMA_REQUIRED` |
| `execution_enabled` | `false` |
| `ledger knowledge_operation_supported` | `false` |
| production `candidate_preflight` | `CANDIDATE_BASELINE_CHANGED` |

Interpretation: the Site control plane already refuses to enable the knowledge approval operation because the production ledger does not support the knowledge operation — i.e. production is **fail-closed today**. This is the same conclusion the isolated reproduction reached (§3).

### 1.3 Production approval ledger schema (STRICT)

- Ledger DB id: `45d6f18a-3a34-4ccd-8337-c00a775cd7a2` (the `ASSET_DB` binding, `worker/wrangler.toml:10`).
- Table `personal_ai_approval_ledger` is **STRICT** with exactly:

```
approval_id          TEXT PRIMARY KEY
requesting_user_hash TEXT CHECK (length(requesting_user_hash) = 64)
operation            TEXT CHECK (operation IN ('deploy_worker_version','write_decision_record'))
exact_target         TEXT
payload_sha256       TEXT
created_at           INTEGER
expires_at           INTEGER
consumed_at          INTEGER
```

### 1.4 Knowledge corpus baseline (read-only, supplied)

- `KNOWLEDGE` asset count: **19**.
- Anomalous asset present in **true Canonical**:
  - `asset_id`: `candidate-writer-validation-20261009-v1`
  - `version`: `1.0`
  - `content_hash`: `0effe682ef88390907f6b5a0b84b678f81d510ca4ab734352c528df5e2e6d6a4`
  - content string: `此资产不得进入 Golden Knowledge`
  - recorded status: `PROMOTE` / `verified` **despite** the self-describing prohibition.

This is treated as a **P0 governance incident** (see §4). No delete/overwrite was attempted (would require a *distinct* approval and is outside this task's boundary).

---

## 2. The STRICT ledger / migration-0003 mismatch (P0 blocker)

`worker/migrations/0003_knowledge_candidate_golden_pipeline.sql` declares (line 81):

```sql
CREATE TABLE IF NOT EXISTS personal_ai_approval_ledger (
  approval_id TEXT PRIMARY KEY,
  operation TEXT NOT NULL,
  asset_type TEXT NOT NULL,
  candidate_id TEXT,
  candidate_version INTEGER,
  content_hash TEXT,
  review_result TEXT,
  approved_by TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'REGISTERED',
  consumed INTEGER NOT NULL DEFAULT 0,
  consume_count INTEGER NOT NULL DEFAULT 0,
  invalidated INTEGER NOT NULL DEFAULT 0,
  invalidated_at TEXT,
  created_at TEXT NOT NULL,
  consumed_at TEXT,
  FOREIGN KEY (operation) REFERENCES approval_ledger_operations (operation)
);
```

Compatibility matrix against the actual production table:

| Aspect | Repo / migration 0003 | Production (actual) | Compatible? |
|---|---|---|---|
| `CREATE TABLE IF NOT EXISTS` | table already exists in prod → **no-op** | existing table | **No upgrade** |
| `operation` domain | free TEXT + FK to registry | `CHECK IN ('deploy_worker_version','write_decision_record')` | **No** |
| `asset_type` | NOT NULL | absent | **No** |
| `candidate_id` / `candidate_version` / `content_hash` / `review_result` | present | absent | **No** |
| `approved_by` | NOT NULL | absent | **No** |
| `state` / `consumed` / `consume_count` / `invalidated` / `invalidated_at` | present | absent | **No** |
| `created_at` / `expires_at` / `consumed_at` type | TEXT | INTEGER | **Type clash** |
| extra prod columns | absent in repo | `requesting_user_hash`, `exact_target`, `payload_sha256` | repo code ignores/never writes them |
| STRICT | not declared | **STRICT** | new columns must be typed |
| operation names | `decision_write`, `knowledge_write`, `KNOWLEDGE_PROMOTION` | `deploy_worker_version`, `write_decision_record` | **Even the Decision op name differs** |

### 2.1 Why 0003 "succeeds on empty SQLite" but cannot migrate production

`0003` is only safe against a database that does **not** already have a `personal_ai_approval_ledger`. On an empty SQLite DB the `CREATE TABLE IF NOT EXISTS` builds the repo's schema and every following index/statement succeeds. Against production the `CREATE TABLE IF NOT EXISTS` is a silent no-op and the *next* index statements reference columns that do not exist:

```sql
CREATE INDEX IF NOT EXISTS idx_approval_ledger_binding
  ON personal_ai_approval_ledger (operation, candidate_id, candidate_version, content_hash);
CREATE INDEX IF NOT EXISTS idx_approval_ledger_state
  ON personal_ai_approval_ledger (operation, consumed, invalidated);
```

`candidate_id`, `candidate_version`, `content_hash`, `consumed`, `invalidated` are all absent → `no such column`. This is **proven**, not hypothesised, in `KNOWLEDGE_ISOLATED_D1_VALIDATION_20261010.md` §2. Additionally, even if the migration were manually repaired, the worker's runtime `APPROVAL_LEDGER_SELECT` (`worker/index.js:3089`) selects `asset_type, candidate_id, …, consumed, invalidated` and would fail with `no such column: asset_type`, and `INSERT` of `KNOWLEDGE_PROMOTION`/`knowledge_write` is rejected by the production `CHECK` constraint.

> **Do not claim production migration is possible from an empty-SQLite pass.** The prior `KNOWLEDGE_GATE_PRODUCTION_RELEASE_PLAN_V1.md` assumed `0003` was additive-safe for production and that the production ledger already matched the RC (`KNOWLEDGE_PROMOTION` present). The fresh production evidence **falsifies that assumption**.

### 2.2 Consequence: the repo's approval architecture was never deployed

Production operation names (`deploy_worker_version`, `write_decision_record`) do not match the repo's (`decision_write`, `knowledge_write`, `KNOWLEDGE_PROMOTION`). Production's ledger was evidently created by the Site/Human-Gate toolchain, not by `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql`. The worker's Knowledge promotion gate has therefore **never had a compatible production ledger** to consume from. The Site reports exactly this: `KNOWLEDGE_APPROVAL_OPERATION_SCHEMA_REQUIRED`.

---

## 3. Compatibility evidence index

| Evidence | Location / command |
|---|---|
| 0003 creates a different ledger on empty DB | `KNOWLEDGE_ISOLATED_D1_VALIDATION_20261010.md` §1 |
| 0003 fails on production-shaped DB at `idx_approval_ledger_binding` | `KNOWLEDGE_ISOLATED_D1_VALIDATION_20261010.md` §2 |
| CHECK blocks `KNOWLEDGE_PROMOTION` and `knowledge_write` | `KNOWLEDGE_ISOLATED_D1_VALIDATION_20261010.md` §3 |
| worker SELECT fails on production-shaped ledger | `KNOWLEDGE_ISOLATED_D1_VALIDATION_20261010.md` §4 |
| registry / FK / no-second-authority code | `worker/index.js:3084-3094, 3113-3131, 3332-3346` |
| migration freeze test (additive-only) | `tests/test_decision_ingestion_writer.py:993-1030` |
| empty-DB migration test (what existing suite covers) | `tests/test_knowledge_candidate_golden_pipeline.py:1226-1264` |

---

## 4. Risk register

| # | Risk | Severity | Status | Note |
|---|---|---|---|---|
| R1 | `0003` is **not** production-applicable; applying it fails at index creation against the live ledger | **P0** | OPEN / BLOCKED | proven in isolation §2 |
| R2 | Production `operation` CHECK rejects knowledge ops → knowledge approval gate cannot be enabled | **P0** | OPEN / BLOCKED | Site already reports it |
| R3 | Repo/prod ledger column + type + operation-name divergence | **P0** | OPEN / BLOCKED | requires table rebuild |
| R4 | Contaminated Golden fixture `candidate-writer-validation-20261009-v1` present in true Canonical with a self-describing prohibition | **P0 governance** | OPEN | do not delete/overwrite without distinct approval |
| R5 | No Cloudflare transport in this environment → real D1 unverifiable | P1 | BLOCKED | `REAL_D1_UNVERIFIED` |
| R6 | `worker/PRODUCTION-BASELINE.json` does not describe the current deployment/version | P2 | OPEN | source identity drift |
| R7 | Existing test suite only exercises an **empty-DB** ledger replica (false confidence) | P1 | OPEN | §2.1 |
| R8 | Prior release plan's precondition P3 ("idempotent, additive") is falsified against production | P1 | OPEN | update plan |

---

## 5. Baseline STATUS

| Layer | STATUS | Evidence basis |
|---|---|---|
| Repo pin / HEAD / hashes / tests / node check | **PASS** | independently executed |
| Production Worker deployment read-back | **PARTIAL** | supplied by Brain; not independently re-read (no credential) |
| Production ledger schema read-back | **PARTIAL** | supplied by Brain; independently *modelled* and proven incompatible |
| Production Knowledge corpus baseline (19 assets) | **PARTIAL** | supplied by Brain; not independently re-read |
| Migration 0003 vs production ledger | **BLOCKED** | isolated reproduction §2 |
| Real Cloudflare D1 execution | **BLOCKED / REAL_D1_UNVERIFIED** | no transport/credential |

**Baseline outcome: `BLOCKED` for production migration; `PARTIAL` overall.** The mismatch is real, reproducible and must be resolved by the controlled repair/rebuild runbook in `KNOWLEDGE_CONTROLLED_RELEASE_PLAN_20261010.md` under a single Human Gate. No production change is performed by this document.
