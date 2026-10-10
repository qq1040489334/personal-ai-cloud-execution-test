# SITE_KNOWLEDGE_APPROVAL_BRIDGE_VALIDATION

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


Issue #7; baseline `b55245d53533dc8da68a50de13c5da14803ad4e6`, re-read from GitHub main and local HEAD on 2026-10-10. This is a limited implementation candidate, with no production effect.

**CODE_PASS (isolated implementation tests). SITE_WORKER_BLOCKED: deployed verifier/source integration is not yet accessible.** Local adapter/consumer contracts pass; that does not prove the deployed Site has been repaired.

## Independently read production identity

Read-only connector evidence is preserved in `reports/issue7-production-readonly.json`.

- Published Site version **31** has a successful publication receipt; exact opaque production identifiers are retained in the private local owner evidence, excluded from this public PR. Site identity fingerprint: `c291c21d17e429fad51b33609293761a0d3ba022d65d6f830421166f1e19dc28`.
- Site archive SHA-256 `87276f2ac56579986382ae033ad1acd2e0b3a8df133d6b953ac3dfe0223558b2`. The private source commit and successful publication metadata were read independently. Current tools cannot retrieve archive bytes; metadata is not a source audit.
- The live `get_knowledge_approval_gate` reports `KNOWLEDGE_APPROVAL_GATE_ADAPTER_V1`, `/knowledge`, operation `write_knowledge_candidate`, TTL 300000 ms, single use `CONDITIONAL_UPDATE_RETURNING`, same ledger/database, `execution_enabled=false`, `BLOCKED/KNOWLEDGE_APPROVAL_OPERATION_SCHEMA_REQUIRED`.
- The live contract explicitly reports `SITE_ONLY_LEGACY_WRITER_HAS_NO_RECEIPT_ARGUMENT`. This differs from the repo Worker candidate lifecycle and its `KNOWLEDGE_PROMOTION` consumer. Never mount the adapter to this legacy flat writer.
- Live production Worker deployment/version/binding identity fingerprint: `e9380edbabd782197a154496ba9e0b92101eeac0919de0b9e9706420c293a7ed`; 100% traffic, verified by read-only GET metadata. The raw identifiers and binding names remain private owner evidence. This fingerprint is a runtime identity, not a repo artifact hash.
- The repo Site file is a candidate-version control module without the deployed passkey handlers. **Repo source does not equal deployed source.** Signing credentials, passkey implementation and live mint ownership cannot be independently source-verified from these bytes; the live read-only contract confirms the existing ledger, but not a successful mint.

## Limited candidate implementation

`site/worker/knowledge-approval.js` exposes a server-owned factory through the existing Site module. The host must mount the returned handler into its existing `/knowledge/approve` completion path and supply its **existing** `humanGate.verifyAndConsume` closure and the **same** D1 ledger binding. No default HTTP server, credential, token, challenge store, new Site, new Worker or alternative verifier is added. Absence of that existing closure rejects the request.

The verifier must independently verify the WebAuthn signature, credential ownership, RP ID, origin, UP+UV, counter, exact challenge payload and one-use challenge CAS. It must return server-derived `verified`, `operation`, `exact_target`, `payload_sha256`, `requesting_user_hash`, `signer_identity`, `ceremony_id` and integer epoch `expires_at`. These fields are a required host integration interface, **not a claim that the deployed verifier already implements it**. Its existing challenge TTL bounds the 300-second adapter limit. Review the exact host implementation before mounting.

The adapter reads a persisted reviewed-PASS candidate, binds operation/id/version/hash/asset destination/review generation, calls that sole verifier, then uses conditional INSERT SELECT into `personal_ai_approval_ledger`. Raw client approver/receipt/expiry fields are rejected. Signer identity comes only from the trusted closure. A changed candidate or FAIL/re-PASS during the ceremony results in zero mint rows. A spent ceremony never authorizes a retry; an ambiguous insert requires read-only reconciliation by ceremony ID.

The Site registers the receipt but does not consume the approval or write Canonical. The existing Worker alone reserves the candidate, checks and consumes the matching approval, then calls its internal Golden writer. Its final CAS rechecks id/version/hash/PASS/expiry and uses server time with INTEGER `consumed_at`; caller-provided `now` no longer authorizes an expired receipt. The original FAIL/reservation ordering and fail-revocation logic remain in place. A legacy flat MCP call still fails before a Canonical write.

## Deterministic proof and limitations

`node --test site/tests/knowledge-approval-bridge.mjs`: 26 passing scenarios, executing the real candidate route, real Worker bundle and real migration SQL against isolated SQLite. The test signer performs synthetic Ed25519 signature verification through the server-owned seam, with one-use ceremony state. **It is not the deployed WebAuthn verifier, does not use real owner credentials, and is not a D1 run.**

Cases include successful one-use promotion and authoritative local readback; forged authority/signature/origin; missing verifier; expired/invalidated/consumed/wrong-operation/wrong-version/wrong-hash receipts; max TTL; candidate change and FAIL/re-PASS during mint; FAIL invalidation; competing Worker consumers; expiry between initial check and consume; flat-writer bypass rejection. Existing Site security/read-only suites: 17 passed. Existing Knowledge targeted suite: 53 passed before final full-suite verification.

**Remaining blocker:** obtain the exact deployed Site archive/source, confirm its sole WebAuthn completion/challenge-CAS interface and ledger binding, port this seam into that host, and verify its mapping reaches this gated Worker consumer. No production passkey mint/consume has been performed. Production prerequisites and a fresh exact-payload Human Gate must be satisfied before any authorized release or Golden write.

## Full-suite execution and changed paths

The complete Windows diagnostic run covered all 1589 collected tests: 1507 passed, 81 failed, 1 skipped. Most failures were caused by the existing Node executable check rejecting Windows `node.EXE`, leaving a 180 KB bundle on the command line (WinError 206). The existing spill shim now case-folds the executable basename; the actual source and assertions are unchanged. After that fix, 200 related regression tests passed with process-local `PYTHONUTF8=1`. Additional existing Windows path/symlink limitations are retained as diagnostics; the symlink fixture requires a privilege unavailable here (WinError 1314). No OS privilege setting or unrelated product code was changed to force PASS.

The authoritative complete run for the frozen PR source is the existing Linux GitHub CI (`python -m pytest -q`, full Git history/tags, Python 3.11, Node 24). Its commit/run identity, completion status and test totals are recorded in the PR checks and description after independent readback. This document does not infer a full-suite PASS from the diagnostic Windows run or from a queued CI job.

A separate real-SQL regression probe failed against the pinned baseline's expired-approval consume and passed against this candidate, demonstrating that the expiry correction changes the failing behavior.

Changed paths:

- `.github/workflows/ci.yml`
- `site/worker/index.js`
- `site/worker/knowledge-approval.js`
- `site/tests/knowledge-approval-bridge.mjs`
- `worker/index.js`
- `worker/knowledge-ledger-migrations.js`
- `worker/migrations/0002z_knowledge_approval_ledger_compat.sql`
- `tests/conftest.py`
- `tests/helpers/sqlite-d1.mjs`
- `tests/test_knowledge_ledger_legacy_compat.py`
- `tests/test_site_knowledge_approval_bridge.py`
- `reports/issue7-production-readonly.json`
- `SITE_KNOWLEDGE_APPROVAL_BRIDGE_VALIDATION.md`
- `KNOWLEDGE_D1_ISOLATED_CLONE_VALIDATION.md`
- `ISSUE_7_GATED_RELEASE_PLAN.md`

Secret-pattern scan and diff whitespace checks passed. Production Canonical was independently listed again after implementation: the same 19 asset IDs, versions and content hashes as the initial manifest. The fixture was preserved. Production writes, approval mint/consume, migration, publish, deployment, configuration or permission changes: zero.
