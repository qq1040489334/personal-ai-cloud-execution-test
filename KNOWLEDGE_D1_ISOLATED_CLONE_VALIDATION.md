# KNOWLEDGE_D1_ISOLATED_CLONE_VALIDATION

## PR #8 P2 repair verification (2026-10-10)

Review baseline: `bd3d6ca6febf5722363d3e3e64d781abcb318fd1`. The remote head and latest comments were re-read before editing and before submission. Work used a separate Windows checkout; existing user checkouts were untouched.

- P2-1: Worker loads and validates the complete Site exact_target and SHA-256, filters by that generation, and atomically pins operation/id/version/hash/asset/PASS/reviewed_at at reservation and consumption. Persisted review timestamps advance monotonically even with a frozen/rolled-back clock. A stale receipt cannot shadow a fresh same-expiry receipt.
- P2-2: reviewed table/index SQL and index_list/index_xinfo verify table ownership, uniqueness, origin, partial predicates, ordered columns, expressions, collation and direction; additional enforcing indexes halt.
- P2-3: the original schema/registry/history snapshot guards, complete postconditions and successful history inserts run in one D1 batch. Preconditions are pinned before classification; postconditions execute before success records. Failures roll back DDL/data/history. ALREADY_APPLIED also runs a read-only guarded batch. No post-commit history deletion occurs.
- P2-4: complete reviewed 13-column candidate DDL and both indexes are checked before apply/adoption and on every idempotent return. Literal whitespace/case, types, defaults, nullability, PK and added constraints are significant. Immutable 0003 remains `9a51d3a53ad5ac3e78e07fc9720ad5492443f5a1f6ac677018570fdfc337927a`.

Fresh executable evidence on Windows/Python 3.11.9/Node 26.7.0 (not Linux/Node 24): `site/tests/pr8-p2-regressions.mjs`: **127 passed, 0 failed**. On original committed Worker/runner bytes the same suite produces **6 passed, 121 failed**; the four original unsafe scenarios each fail their safe expectation. This suite is wrapped by `tests/test_pr8_p2_regressions.py` for complete CI. It asserts actual persisted rows, zero writer attempts and unconsumed receipts, and schema/data/history equality across drift failures. Synthetic Ed25519 verifier and isolated Node SQLite only.

Fresh original bridge: **26 passed**. Fresh Site security/readonly: **17 passed**. Related Python tests: **54 passed** (includes the bridge and P2 wrappers; do not add these counts to the 127+26+17 scenario totals).

Linux/Python 3.11/Node 24 full CI: PENDING for this revised commit, not inferred from old 1588/1. Windows complete diagnostic: PENDING; an earlier connection interruption produced no valid complete result. Official portable Node 24 download was attempted but the nodejs.org transport returned EOF; no installation or persistent environment change occurred. Exact Node 24 verification will be recorded from the existing Linux CI.

Parent-supplied read-only observation at **2026-10-10 02:30:26 UTC**: deployed Site v0.3.6 reports Knowledge execution disabled, BLOCKED/KNOWLEDGE_APPROVAL_OPERATION_SCHEMA_REQUIRED, SITE_ONLY_LEGACY_WRITER_HAS_NO_RECEIPT_ARGUMENT, approval_live_verified=false, GOLDEN_RECEIPT_INVALID_OR_EXPIRED. This was supplied by the delegating thread, not freshly queried by this repair checkout. No deployed source/verifier completion receipt or preauthorized real nonproduction D1 identity/restore/query transport is available.

Current acceptance: **CODE_PARTIAL (local regressions pass; revised full Linux CI pending); SITE_WORKER_BLOCKED; REAL_D1_UNVERIFIED; RELEASE_NOT_PERFORMED. Production is not ready.** PR remains draft and Issue #7 open. No merge/deploy, production migration/mint/consume/Canonical write, keys/bindings/permissions change, second approval authority, or paid API/resource was used. Separate explicit authorization and the missing integration/isolated-D1 prerequisites are required for those future stages.


**REAL_D1_UNVERIFIED. RELEASE_NOT_PERFORMED.** Issue #7, 2026-10-10.

No pre-authorized, independently proven nonproduction D1 database ID/binding or isolated D1 execution transport was available. Local environment inspection returned no configured Cloudflare credential variable names. The connected Site provides read-only gate/Worker metadata, but no approved database export/restore or general D1 query transport. No cloud resource was created and no secret value was requested. This stage stopped at its required boundary.

There is **no Cloudflare D1 run ID, remote command success receipt, production snapshot, cloud schema hash or cloud rollback receipt**. None of the SQLite results below are a real-D1 PASS.

## Actual runner and migration changes

- `0003` remains byte-for-byte immutable, SHA-256 `9a51d3a53ad5ac3e78e07fc9720ad5492443f5a1f6ac677018570fdfc337927a`.
- `0002z` now contains executable precondition SQL before its DDL. Even the existing default Wrangler runner will execute this guard; protection no longer depends on a Python helper or a SQL comment. It conservatively accepts only the exact known STRICT eight-column legacy definition, no unreconciled backup/temp table, custom trigger/index, outgoing FK or incoming ledger FK. Unexpected spellings/shapes halt for explicit reconciliation. It preserves the legacy nullable operation constraint and INTEGER timestamps; a conflicting operation registry aborts the migration transaction.
- `worker/knowledge-ledger-migrations.js` is a reviewed maintenance function over the existing D1 binding, not a new HTTP/MCP route. It verifies source hashes, requires independently verified backup completion, detects exact LEGACY/UNION/ABSENT/DRIFT and checks UNION FK/index/registry mappings. The calling authorized maintenance context supplies committed migration bytes and their reviewed hash. `backupVerified` is a host precondition, not an external approval token or a replacement for backup proof.
- It rechecks ledger schema inside a single D1 batch, applies `0002z` before immutable `0003`, and records both under their actual names in **existing `d1_migrations`** in the same transaction. A verified existing UNION can be adopted without rebuilding or losing candidate columns. Existing recorded history is never rewritten/deleted. `0003` recorded without its prerequisite, duplicate history, or history/schema mismatch halts. A rolled-back batch leaves no success history; retry must reconcile schema/history first.
- This runner handles the two Knowledge suffix migrations only. Earlier `0001`/`0002` and base assets schema are existing prerequisites; it is not a substitute bootstrap runner. Standard Wrangler uses sequential migration transactions; the maintenance batch intentionally provides an all-or-nothing suffix transaction.
- D1 batch transaction behavior is documented by [Cloudflare](https://developers.cloudflare.com/d1/worker-api/d1-database/); [Wrangler migration docs](https://developers.cloudflare.com/d1/wrangler-commands/) describe migration rollback/history behavior. These docs are protocol requirements, not live validation evidence.

## Local isolated evidence

`node --test site/tests/knowledge-approval-bridge.mjs`: 26 passed, including actual Site mint and Worker one-use consume in an isolated SQLite binding transport. `python -m pytest -q tests/test_knowledge_ledger_legacy_compat.py`: 11 passed. The complete Linux suite receipt is recorded in the PR checks/description; the companion Site report distinguishes Windows diagnostics and local contract proof.

Production-shaped STRICT seed includes Deploy/Decision live, consumed, expired and nullable-operation historical rows. Tests compare all original eight columns before/after the rebuild; check STRICT INTEGER/CHECK/FK/indexes; exercise legacy `consumed_at IS NULL` CAS; guard both runner and direct migration against drift; adopt a verified UNION; reject missing backup/hash/history drift. An injected failure after candidate DDL rolls back tables, rows and migration history. An independent file backup is reopened and verifies exact legacy rows/schema; the repaired run subsequently succeeds. Tests exercise rollback and restoration locally, without exposing production ledger rows.

`personal_ai_approval_ledger__legacy_backup` is an inactive retained pre-state in the same database; no consumer or mint handler reads it. It is **not** a second approval authority. It cannot serve as a live rollback once approved writes have occurred; use a full verified pre-release backup and explicit recovery authorization.

## Exact prerequisites to resume real D1 validation

1. Existing, separately pre-authorized nonproduction D1 database, independently proved by account/database identity, inventory and absence from production bindings. Do not create/pay for one under this Issue authorization.
2. Authorized read-only production export/snapshot transport and safe local destination; capture full database/schema/migration history plus legacy row counts/hashes and Time Travel bookmark where supported. Do not turn a backup into a production ledger mutation.
3. Approved isolated restore/query transport, with credentials supplied through its normal secure mechanism (never chat). Record commands/run IDs and verify only the isolated ID is targeted.
4. Reconcile deployed Site source and sole verifier, and exercise it against the same isolated ledger and candidate Worker contract, preserving legacy Deploy/Decision flows.
5. On the clone run ordered migration, exact-schema/hash/count assertions, drift HALT, transaction-failure recovery, mint/consume/replay, expiry and invalidation, concurrent FAIL/reservation, legacy CAS and full snapshot restore. Compare original rows after restoration and retain cloud receipts.

Only these actual cloud receipts can upgrade `REAL_D1_UNVERIFIED` to `REAL_D1_PASS`. Production migration, release and Golden writes remain separate exact-payload Human Gates.
