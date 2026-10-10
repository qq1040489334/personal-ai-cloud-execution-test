# ISSUE_7_GATED_RELEASE_PLAN

**RELEASE_NOT_PERFORMED. No production action is authorized by this plan.**

Baseline: `b55245d53533dc8da68a50de13c5da14803ad4e6`. A PR is a code candidate, not a deployment or successful Human Gate.

## Exact candidate source hashes

| Path | SHA-256 |
|---|---|
| `worker/index.js` | `bf8e4319a2ec5979644b66cd3879eb52a2912e23aaef4c84629698220a850a9d` |
| `site/worker/index.js` | `df2eaabf1bad185435319d0b5412ac2a7616e0a8252dd3bd6da5f6c83682bb3a` |
| `site/worker/knowledge-approval.js` | `ac9551cf71ad1f511a9ec1a47d3ab45ac1565c0e4750824460bef00d010f48e6` |
| `worker/knowledge-ledger-migrations.js` | `23e2c1c8988a3e34208c4585a28ab17bb8434ed2117159995e0700cdcde3374e` |
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
