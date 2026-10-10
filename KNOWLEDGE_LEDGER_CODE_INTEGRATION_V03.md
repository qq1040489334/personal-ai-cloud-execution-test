# KNOWLEDGE_LEDGER_CODE_INTEGRATION_V03

- Task: `cf-b92be4c2cc0a` (parent `cf-ee61ff33f0e2`, root `cf-44b8447f89a1`)
- Project: `personal-ai-knowledge-golden`
- Contract: `KNOWLEDGE_LEDGER_COMPAT_CODE_INTEGRATION_V0.3R1`
- Base repo: `qq1040489334/personal-ai-cloud-execution-test`
- Base HEAD (read-back): `651ced597917144fdf7c1dd2944f1a33d30afc79`
- Risk level: LOW

## 1. Purpose

The previous dispatch `cf-ee61ff33f0e2` (GitHub Actions run `38006260531`)
failed deterministically at **Gate 2** because its `expected_files` allowlist
omitted `worker/index.js` and
`tests/test_knowledge_candidate_golden_pipeline.py` although the instructions
allowed their modification. The agent produced local commit
`bbd4e9c560eb40e6a42a68e81f6c9592944d2aeb` (1590 passed / 1 skipped) but the
push was **SKIPPED**; that commit is not on GitHub and is **not** claimed to be
recoverable here.

This run re-executes the durable integration with the **complete five-file
allowlist** and persists the code, SQL and tests to GitHub.

## 2. Allowlist (exactly five paths)

```
worker/index.js
tests/test_knowledge_candidate_golden_pipeline.py
worker/migrations/0002z_knowledge_approval_ledger_compat.sql
tests/test_knowledge_ledger_legacy_compat.py
KNOWLEDGE_LEDGER_CODE_INTEGRATION_V03.md
```

No `.github/workflows/`, no secret/token/credential/.env/.pem/.key path, no
deletion, no path outside this list.

## 3. What is committed

### 3.1 `worker/migrations/0002z_knowledge_approval_ledger_compat.sql` (new)

Offline, versioned, self-contained union rebuild. It sorts after
`0002_dispatch_idempotency.sql` and **before**
`0003_knowledge_candidate_golden_pipeline.sql`, so the pre-existing
production ledger (`personal_ai_approval_ledger`, **STRICT**) is reshaped
before `0003`'s `CREATE TABLE IF NOT EXISTS` no-op and its two indexes run.

- Legacy columns/order/types/constraints preserved verbatim; INTEGER epoch
  timing (`created_at`/`expires_at`/`consumed_at`) is **never** converted to
  TEXT.
- The old operation CHECK is widened by **addition** only
  (`decision_write`, `knowledge_write`, `KNOWLEDGE_PROMOTION`); it is a
  `CHECK`, so a rebuild is required.
- Pre-state is retained by `RENAME` to
  `personal_ai_approval_ledger__legacy_backup` (never `DROP`) for byte-for-byte
  rollback; `consumed` mirror is derived from legacy `consumed_at`.
- FK-bound: the `approval_ledger_operations` registry is created/seeded with
  all five operations before the rebuild so no legacy row is orphaned.

### 3.2 `worker/index.js` (patched, Site-compatible single-use gate)

Only the approval-ledger gate SQL and expiry parsing changed:

- `APPROVAL_LEDGER_SELECT`: gate now `... AND consumed_at IS NULL AND
  invalidated = 0` and projects `consumed_at` (was `consumed = 0`).
- `APPROVAL_LEDGER_CONSUME`: `... AND consumed_at IS NULL ...` (was
  `consumed = 0`).
- `APPROVAL_LEDGER_INVALIDATE`: `... AND consumed_at IS NULL ...` (was
  `consumed = 0`).
- Consume binds an **integer epoch second** (`Math.floor(Date.now()/1000)`),
  not an ISO string.
- `validateCandidateGate`: expiry accepts a numeric-epoch `expires_at` in
  addition to ISO (`Number.isFinite(Number(v)) ? Number(v)*1000 :
  Date.parse(String(v))`) and rejects any non-null `consumed_at`.
- The Worker still has **no** approval mint/register path.

### 3.3 `tests/test_knowledge_ledger_legacy_compat.py` (new)

Production-shaped **STRICT** legacy-ledger regression suite (11 tests). It
executes the **real committed migration files** and the **real Worker SQL
constants extracted with Node** (not a hand-copied Python string) against
isolated SQLite:

- baseline: `0001+0002+0003` fail on the prod-shaped ledger with
  `no such column: candidate_id`;
- `0002z` guarded rebuild → `UNION`, still STRICT, INTEGER timing, legacy rows
  byte-for-byte, backup retained, then `0001/0002/0003` apply in order and both
  `0003` indexes resolve; registry holds all five operations; single ledger;
  idempotent re-run;
- legacy WebAuthn CAS on integer `consumed_at` stays single-use;
- Worker real SQL two-connection CAS: exactly one winner, replay rejected,
  `consume_count = 1`, integer `consumed_at`;
- stale-approval invalidation blocks replay, row retained additively;
- migration-ordering guard HALTs on drift and on an absent ledger (fail-closed);
- `0003` immutable (sha256 pinned);
- Worker cannot mint an approval;
- `0002z` is offline/additive and never touches Golden storage.

A Node probe also drives the real `validateCandidateGate` to prove
numeric-epoch expiry acceptance, ISO expiry acceptance, expiry rejection and
`consumed_at` single-use rejection.

### 3.4 `tests/test_knowledge_candidate_golden_pipeline.py` (minimal adjustment)

The exact migration-set assertion now includes
`0002z_knowledge_approval_ledger_compat.sql` (one added line). No other change.

### 3.5 `KNOWLEDGE_LEDGER_CODE_INTEGRATION_V03.md` (this report)

## 4. Site ↔ Worker integration: **BLOCKED**

The task requires an explicit comparison of the Site mint adapter
(`write_knowledge_candidate` / WebAuthn) against the Worker
`KNOWLEDGE_PROMOTION` consumer. Independent inspection of the repository:

```
site/worker/index.js   -> deploy/write-site (AUTHORIZED_RELEASE_TUPLES,
                          candidate audit/create); no WebAuthn handler,
                          no write_knowledge_candidate, no
                          personal_ai_approval_ledger, no KNOWLEDGE_PROMOTION.
site/tests/*.mjs       -> no ledger / no knowledge approval flow.
```

No Site side mint adapter for `KNOWLEDGE_PROMOTION` exists in this repository.
Therefore a Site-minted approval cannot be produced or independently
demonstrated here, and the **Site ↔ Worker integration is labelled
`BLOCKED`** — this is not rescued by the local SQLite tests passing.

## 5. Cloudflare D1 status

| Item | Status |
|---|---|
| Real D1 credential/transport in this environment | **NO** |
| Real D1 migration attempted | **NO** (boundary) |
| Real D1 clone rebuild + rollback exercise | **NOT PERFORMED** |
| Real D1 STRICT/CHECK/FK/CAS behaviour | **`REAL_D1_UNVERIFIED`** |
| Production DB used as a test DB | **NO** |

Disposition: `LOCAL_SQLITE_PASS` + `SITE_WORKER_BLOCKED` +
`REAL_D1_UNVERIFIED`; **not** `READY_FOR_PRODUCTION`.

## 6. Boundary honoured

No production deploy, no production D1 migration, no Canonical write, no Site
publish, no approval register/consume, no secret/OAuth/binding/permission
change. Production worker, D1, Site, Canonical storage and secrets are
untouched. No second approval authority / ledger / mint path is introduced.

## 7. Evidence

| Artifact | sha256 |
|---|---|
| `worker/index.js` | `a7d1e31f304958555bdab4d90ac55ade006e44d48d250cf40843aa867805f28f` |
| `worker/migrations/0002z_knowledge_approval_ledger_compat.sql` | `53ef35d384db7c8a93c1546499996573609bd06cd5bf248719dc9f022dd3a2ef` |
| `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql` (unchanged) | `9a51d3a53ad5ac3e78e07fc9720ad5492443f5a1f6ac677018570fdfc337927a` |
| `tests/test_knowledge_ledger_legacy_compat.py` | `c4b7ac160e15ef623ff8f944a2b1fa0b949a90e6a27eb0910efa60a6f5841d1c` |
| `tests/test_knowledge_candidate_golden_pipeline.py` | `5692760fc9d16da988a1ddc01fee1faec7dd432fb57db4203a201ecd7df5aee0` |

Commands: `node --check worker/index.js` (exit 0), `python -m pytest -q` and
the focused suites (exit 0).

## 8. Status matrix

| Layer | Status |
|---|---|
| Durable SQL + patched Worker + tests committed to GitHub | **PASS** |
| Production-shaped STRICT legacy → union rebuild (local SQLite) | **PASS** |
| Legacy columns / integer timing / WebAuthn single-use preserved | **PASS** |
| Worker real-SQL single-use CAS + replay + stale invalidation | **PASS** |
| Migration-order guard HALTs on drift/absent; `0003` immutable | **PASS** |
| Worker cannot mint approvals | **PASS** |
| Site ↔ Worker `KNOWLEDGE_PROMOTION` mint/consume | **BLOCKED** (no Site adapter) |
| Real Cloudflare D1 execution | **BLOCKED / `REAL_D1_UNVERIFIED`** |
| Release decision | **HUMAN_GATE_REQUIRED — not `READY_FOR_PRODUCTION`** |

## 9. Remaining gaps

1. No Site-side mint adapter for `KNOWLEDGE_PROMOTION` exists; one must be
   authored and reviewed before the end-to-end Site→Worker single-use receipt
   can be demonstrated.
2. Real D1 clone rebuild + rollback must be exercised before any live apply.
3. Production migration / Site publish / Canonical write remain out of scope
   and require the Human Gate.
