# ISSUE_7_GATED_RELEASE_PLAN

## PR #8 P2 repair verification (2026-10-10)

Review baseline: `bd3d6ca6febf5722363d3e3e64d781abcb318fd1`. The remote head and latest comments were re-read before editing and before submission. Work used a separate Windows checkout; existing user checkouts were untouched.

- P2-1: Worker loads and validates the complete Site exact_target and SHA-256, filters by that generation, and atomically pins operation/id/version/hash/asset/PASS/reviewed_at at reservation and consumption. Persisted review timestamps advance monotonically even with a frozen/rolled-back clock. A stale receipt cannot shadow a fresh same-expiry receipt.
- P2-2: reviewed table/index SQL and index_list/index_xinfo verify table ownership, uniqueness, origin, partial predicates, ordered columns, expressions, collation and direction; additional enforcing indexes halt.
- P2-3: the original schema/registry/history snapshot guards, complete postconditions and successful history inserts run in one D1 batch. Preconditions are pinned before classification; postconditions execute before success records. Failures roll back DDL/data/history. ALREADY_APPLIED also runs a read-only guarded batch. No post-commit history deletion occurs.
- P2-4: complete reviewed 13-column candidate DDL and both indexes are checked before apply/adoption and on every idempotent return. Literal whitespace/case, types, defaults, nullability, PK and added constraints are significant. Immutable 0003 remains `9a51d3a53ad5ac3e78e07fc9720ad5492443f5a1f6ac677018570fdfc337927a`.

Fresh executable evidence on Windows/Python 3.11.9/Node 26.7.0 (not Linux/Node 24): `site/tests/pr8-p2-regressions.mjs`: **127 passed, 0 failed**. On original committed Worker/runner bytes the same suite produces **6 passed, 121 failed**; the four original unsafe scenarios each fail their safe expectation. This suite is wrapped by `tests/test_pr8_p2_regressions.py` for complete CI. It asserts actual persisted rows, zero writer attempts and unconsumed receipts, and schema/data/history equality across drift failures. Synthetic Ed25519 verifier and isolated Node SQLite only.

Fresh original bridge: **26 passed**. Fresh Site security/readonly: **17 passed**. Related Python tests: **54 passed** (includes the bridge and P2 wrappers; do not add these counts to the 127+26+17 scenario totals).

Fresh complete Linux CI on exact code commit `873c5336b9e56dcc7d6582ab52ecb4399e9a3db4`: **1589 passed, 1 skipped in 59.70s**, read from [run 38018275254 / job 114113357869](https://github.com/qq1040489334/personal-ai-cloud-execution-test/actions/runs/38018275254/job/114113357869). Actual runtime: **Python 3.11.17 / Node 24.21.0**. This is a new run, not the old 1588/1 receipt. The final documentation-only head is checked separately in the PR description; Worker/runner/test bytes are unchanged from this verified code commit.

Windows complete diagnostic: **TIMED_OUT after 240.03s** for `python -u -m pytest -q --tb=short --durations=10` on Windows/Python 3.11.9/Node 26.7.0. Collection separately confirmed 1590 tests; execution produced no complete pass/fail/skip summary. It progressed through early historical-audit cases but did not finish within the diagnostic bound. The original unbounded attempt was interrupted rather than left running. Root cause is not established; this is a local diagnostic blocker, not a Windows full-suite PASS or a counted test failure. The existing complete Linux run remains the code acceptance evidence. An earlier connection interruption produced no valid complete result. The local Node 26 and remote Node 24 results are kept separate. Official portable Node 24 download returned EOF; no installation or persistent environment change occurred. No OS privilege or unrelated product code was changed for this diagnostic.

Parent-supplied read-only observation at **2026-10-10 02:30:26 UTC**: deployed Site v0.3.6 reports Knowledge execution disabled, BLOCKED/KNOWLEDGE_APPROVAL_OPERATION_SCHEMA_REQUIRED, SITE_ONLY_LEGACY_WRITER_HAS_NO_RECEIPT_ARGUMENT, approval_live_verified=false, GOLDEN_RECEIPT_INVALID_OR_EXPIRED. This was supplied by the delegating thread, not freshly queried by this repair checkout. No deployed source/verifier completion receipt or preauthorized real nonproduction D1 identity/restore/query transport is available.

Current acceptance: **CODE_PASS (fresh complete Linux CI and isolated regressions); SITE_WORKER_BLOCKED; REAL_D1_UNVERIFIED; RELEASE_NOT_PERFORMED. Production is not ready.** PR remains draft and Issue #7 open. No merge/deploy, production migration/mint/consume/Canonical write, keys/bindings/permissions change, second approval authority, or paid API/resource was used. Separate explicit authorization and the missing integration/isolated-D1 prerequisites are required for those future stages.

The remaining sections retain historical implementation/background evidence. The dated PR #8 section above controls the current validation counts and status; historical Windows results below are not revised-head results.



**RELEASE_NOT_PERFORMED. No production action is authorized by this plan.**

Baseline: `b55245d53533dc8da68a50de13c5da14803ad4e6`. A PR is a code candidate, not a deployment or successful Human Gate.

## Exact candidate source hashes

| Path | SHA-256 |
|---|---|
| `worker/index.js` | `a3a463ff423034304320c10dbb5059d6f2e78464af6a1a42eea937632e5fa134` |
| `site/worker/index.js` | `df2eaabf1bad185435319d0b5412ac2a7616e0a8252dd3bd6da5f6c83682bb3a` |
| `site/worker/knowledge-approval.js` | `ac9551cf71ad1f511a9ec1a47d3ab45ac1565c0e4750824460bef00d010f48e6` |
| `worker/knowledge-ledger-migrations.js` | `810c5c0d27568689d2cd580fb53c2f47ddf2aa86356b95d154868e98f6abe9a0` |
| `worker/migrations/0002z_knowledge_approval_ledger_compat.sql` | `e9221650ae7f0befd69ad17ca9685a305f9b7099c8b1bf4927c703fd091034ed` |
| `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql` | `9a51d3a53ad5ac3e78e07fc9720ad5492443f5a1f6ac677018570fdfc337927a` |

| `tests/conftest.py` | `63fc3f7175892d7c2c47aa6c4fa8b7d04b80aa3a6fadc0cebc3f4175f7c12592` |

Knowledge manifest: 19 assets, sorted by asset_id with keys serialized using Python json.dumps(sort_keys=True, ensure_ascii=False, separators=(",", ":")). SHA-256: `a92405c2c13b85723f8d1eb10a040afec54b099d5615c85c9b14efdf297e48c6`. Exact entries are retained in `reports/issue7-production-readonly.json`; the existing test fixture remains untouched.

## Required gates in order

1. Independently retrieve and inspect the deployed Site source/archive matching its recorded commit/hash. Confirm /knowledge, credential signer, challenge CAS and sole ledger. Mount the candidate adapter only into that existing verifier. Confirm the Site calls the gated candidate consumer rather than its live legacy flat writer. Until then: SITE_WORKER_BLOCKED.
2. Obtain already authorized isolated D1 and read-only production backup transport. Verify nonproduction identity and approved resource scope. Capture full schema/data/migration history/bookmark and independent backup proof. No paid resource creation.
3. Execute and record real isolated D1 validation with original row/hash/count comparisons, exact CHECK/FK/indexes, transactional failure and history rollback, idempotence/adoption, legacy Deploy/Decision CAS, real Site mint and Worker replay tests. Until cloud receipts exist: REAL_D1_UNVERIFIED.
4. Re-read current production identity and the complete 19-asset manifest. Any source, version, binding, schema, ledger-history or Canonical drift invalidates the prepared plan and requires reconciliation. Do not blindly save or retry.
5. Only after all prerequisites pass, prepare reviewable exact production migration/source/version/rollback payloads and request separate explicit approval through the existing Human Gate. This Issue approval does not authorize those effects. Preserve binding/secret/OAuth/permission configuration and existing Deploy/Decision authority.
6. A later authorized release must use exact reviewed bytes and active version/config inheritance, independently verify final source/runtime/ledger/manifest identities, and obtain a fresh candidate-scoped passkey approval for each separately authorized Golden write. Never use the unintended fixture as a Golden target.

## Rollback preparation

Before any later authorized migration, capture an independently restorable full D1 snapshot/bookmark and record row/schema/history hashes. Preserve the old Site artifact and Worker version; the exact current Worker and Site deployment/version identities are retained only in the private local owner evidence. Public Worker identity fingerprint: `e9380edbabd782197a154496ba9e0b92101eeac0919de0b9e9706420c293a7ed`; Site identity fingerprint: `c291c21d17e429fad51b33609293761a0d3ba022d65d6f830421166f1e19dc28` (published version 31). The approved owner must retrieve and re-read the exact raw identities immediately before preparing a production approval payload. This public plan is incomplete for release until that private reconciliation is done.

A failed suffix batch must leave its rows/schema/history unchanged; reconcile before retry. A post-commit rollback requires its own explicit recovery authorization and the full verified backup, including migration history. The retained legacy table is only an inactive pre-state and must never be activated as a second ledger or used to discard newer approvals. If any approved writes occur after the snapshot, restoring that snapshot would lose them: halt and prepare a reconciled recovery payload rather than blind restoration. Verify backup restore on isolated D1 before treating rollback as ready.

No release command, cloud backup/restore, production passkey operation or production write was executed in this task.
