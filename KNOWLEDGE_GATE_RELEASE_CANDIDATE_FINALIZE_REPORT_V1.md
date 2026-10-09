# KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_REPORT_V1

- Task ID: `cf-e92e0c936a1a` (stale-approval fix continuation of `cf-00bcf790b680`)
- Goal: `KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_V1`
- Repository: `qq1040489334/personal-ai-cloud-execution-test`
- Original base commit: `fb01f893f0357c4c6a1289a2ca098c139203650f`
- Continuation start commit: `66878d94107a0e828697f2a3138e5087deb59aab`
  (the prior run that only produced the two reports)
- Stale-approval fix base commit: `e3ead9540b48f58b02fbb75af86fa763ca041923`
  (business code `7908ef470baa27da7b1d9169970f4950aa4a4bb4`)
- Release-candidate commit: recorded as git `HEAD` at publication time (see §2;
  the `cloud agent: gpt task` commit that contains this report)
- Risk level: `LOW`
- Mode: `IMPLEMENT_AND_TEST`
- Production readiness: **`PARTIAL`** (implemented + isolated-verified; real
  Cloudflare D1 concurrency and production deploy/migration remain `UNVERIFIED`)

> **Hard-hold attestation.** No production deploy, no production D1 migration,
> no Canonical write, no production approval create/consume, and no
> secret/OAuth/permission/binding change was performed. No file was deleted and
> no path outside the corrected allowlist was modified. Everything below is
> either a repository reading or an executed in-repo/isolated test. Items that
> could not be executed are marked `UNVERIFIED`.
>
> **Test PASS is not production PASS.** A green `python -m pytest` proves no
> regression against an in-repo/isolated environment, not that a production
> closed loop works.

---

## 1. Fixed architecture

```
MCP tools/call -> write_knowledge_candidate   (single public Knowledge tool,
   |                                            frozen tools/list = 11 entries)
   |  candidate_operation = create            -> knowledge_candidates (DRAFT)
   |  candidate_operation = read  [read scope]-> independent read by candidate_id
   |  candidate_operation = submit_review     -> PENDING_REVIEW
   |  candidate_operation = review            -> review_state PASS/FAIL
   |  candidate_operation = promote (default) -> validateCandidateGate
   |                                                |
   |                                                v
   |                          personal_ai_approval_ledger (operation =
   |                          KNOWLEDGE_PROMOTION, bound to
   |                          candidate_id/version/content_hash/review_result/
   |                          approved_by/expires_at). Conditional CAS consume.
   |                                                |
   |                                                v
   |                          writeKnowledgeCandidate (existing Golden writer)
   |                                                |
   |                                                v
   |                          verifyKnowledgeVersion (authoritative read-back)
   v
promotion receipt (WRITTEN / IDEMPOTENT / REJECTED + recovery metadata)
```

- **P0-A (single approval authority).** `KNOWLEDGE_PROMOTION` is registered in
  the shared trusted ledger `personal_ai_approval_ledger`, whose operation
  registry `approval_ledger_operations` also carries `decision_write` and
  `knowledge_write`. The second authority `knowledge_promotion_approvals` is
  removed. The Worker has **no** approval-minting path: a caller-supplied
  `approved_by`, `approval_receipt` or `promotion_decision` cannot authorise a
  write. Approvals only enter the ledger out of band (trusted Human Gate).
- **P0-B (callable persistence).** `create`/`read`/`submit_review`/`review`/
  `promote` sub-operations are reachable through the MCP tool, backed by real
  table writes; an independent reader/session can read a candidate another agent
  persisted. `create` never promotes.
- **P0-C (migration).** `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql`
  is committed, additive-only and idempotent. The historical freeze tests were
  converted to additive-safety assertions (0001/0002 immutable, no
  `assets`/`asset_versions` mutation, no ungated write path).
- **P0-D (runbook).** `KNOWLEDGE_GATE_PRODUCTION_RELEASE_PLAN_V1.md` holds the
  unified release + rollback runbook; it is updated to the shipped code.
- **P0-E (stale-approval fix).** `recordKnowledgeCandidateReview` now (a) only
  accepts legal pre-promotion transitions (a `PROMOTED` /
  `CANONICAL_READBACK_VERIFIED` candidate can never be reviewed back) and (b)
  atomically revokes, in the same `db.batch` boundary as the status change,
  every still-live (unconsumed, non-invalidated) `KNOWLEDGE_PROMOTION` approval
  bound to the candidate. A later PASS therefore requires a **new** Human-Gate
  approval; the revoked one is permanently dead. The gate read and the consume
  CAS both exclude invalidated rows.

---

## 2. Files changed and commit

| File | Change |
|---|---|
| `worker/index.js` | P0-A: ledger constants now target `personal_ai_approval_ledger`; removed `knowledge_promotion_approvals` SQL and the approval-mint function. P0-B: added `createKnowledgeCandidate`, `readKnowledgeCandidate`, `submitKnowledgeCandidateForReview`, `knowledgeCandidateReadOperation` and `candidate_operation` routing + permission isolation in the MCP dispatch. `promoteKnowledgeCandidate` now selects/consumes the trusted ledger atomically and takes the writer actor from the ledger approval. |
| `hello.py` | Added `read_knowledge_candidate` plus a durable, isolated-SQLite candidate/ledger harness (`knowledge_candidate_sqlite_connect`, `sqlite_stage_knowledge_candidate`, `sqlite_read_knowledge_candidate`, `sqlite_submit_...`, `sqlite_record_...`, `sqlite_register_knowledge_promotion_approval`, `sqlite_consume_promotion_approval`) that applies the real migration 0003 and performs the same CAS consume. |
| `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql` | New additive migration: `knowledge_candidates`, `approval_ledger_operations`, `personal_ai_approval_ledger` + indexes. Stale-approval fix adds `invalidated` / `invalidated_at` columns (additive, still no `ALTER`/`DROP`). |
| `tests/test_knowledge_candidate_golden_pipeline.py` | Rewritten to the ledger-reuse architecture; added MCP lifecycle, candidate-bound/single-use approval, read-back-failure, canonical-write-failure recovery, and isolated-SQLite migration/persistence/CAS tests. Stale-approval fix adds PASS->approval->FAIL->PASS regression (worker + Python + isolated SQLite), fresh-approval success, and terminal-state review rejection. |
| `hello.py` | Stale-approval fix: `record_knowledge_candidate_review` accepts an optional `ledger` and revokes stale approvals on FAIL; `invalidate_knowledge_promotion_approvals`; gate + consume reject invalidated approvals; isolated SQLite helpers mirror the same atomic revoke semantics. |
| `tests/test_decision_ingestion_writer.py` | `test_no_new_migration_added` converted to `test_migration_set_is_additive_only_and_immutable_history`. |
| `tests/test_knowledge_candidate_writer.py` | Scope assertion updated for the read/write sub-operation isolation. |
| `KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_REPORT_V1.md` | This report. |
| `KNOWLEDGE_GATE_PRODUCTION_RELEASE_PLAN_V1.md` | Updated production plan/runbook. |

Command: `git add -A && git commit -m 'cloud agent: gpt task'`.
Release-candidate commit SHA: recorded as git `HEAD` at publication time. The
business/ledger implementation was frozen at
`7908ef470baa27da7b1d9169970f4950aa4a4bb4`; the stale-approval fix continues
from `e3ead9540b48f58b02fbb75af86fa763ca041923`. The exact SHA of the
code+migration+test+report commit produced by this run is recorded in the run's
`agent_result.json` (a report-only refresh may follow that records this SHA).

---

## 3. Approval Ledger integration evidence

- Worker SQL constants now reference `personal_ai_approval_ledger`:
  - `APPROVAL_LEDGER_SELECT` selects the operation-bound row for
    `(operation, candidate_id, candidate_version, content_hash)` and excludes
    consumed **and invalidated** rows, so a revoked stale approval is never
    returned to the gate.
  - `APPROVAL_LEDGER_CONSUME` is a compare-and-swap:
    `UPDATE personal_ai_approval_ledger SET consumed = 1, state='CONSUMED',
    consume_count = consume_count + 1, consumed_at = ? WHERE approval_id = ?
    AND operation = ? AND consumed = 0 AND invalidated = 0` (at most one
    `meta.changes === 1`; a concurrently invalidated approval loses the CAS).
  - `APPROVAL_LEDGER_INVALIDATE` revokes stale approvals on review FAIL:
    `UPDATE personal_ai_approval_ledger SET invalidated = 1,
    state='INVALIDATED', invalidated_at = ? WHERE operation = ?
    AND candidate_id = ? AND consumed = 0 AND invalidated = 0`. It only touches
    unconsumed rows (input ignored). Called in the same `db.batch` as the
    review status update, so revocation + status change are atomic.
- `validateCandidateGate` verifies `operation == KNOWLEDGE_PROMOTION` and the
  candidate/version/hash/review/approver/expiry binding, and rejects any
  `invalidated` / `state='INVALIDATED'` approval, before any write.
- No worker path inserts into the ledger (grep-verifiable absence of a mint
  function and of `knowledge_promotion_approvals`).
- Tests: `test_worker_approval_is_candidate_bound_and_single_use`,
  `test_worker_2_forged_decision_without_approval_rejected`,
  `test_worker_gate_rejects_expired_and_consumed_approval`,
  `test_isolated_sqlite_atomic_approval_consume_is_single_use`.

---

## 4. Candidate create / independent-read / submit / review entry points

| Sub-operation | Scope | Effect |
|---|---|---|
| `create` | write (`mcp`) | INSERT independent DRAFT row in `knowledge_candidates` |
| `read` | read (`asset.read`) | SELECT by `candidate_id` (cross-agent / cross-session) |
| `submit_review` | write | DRAFT -> PENDING_REVIEW (state checked) |
| `review` | write | record PASS/FAIL; PASS -> APPROVED_FOR_PROMOTION |
| `promote` | write | gate + CAS consume + Golden write + read-back |

Permission isolation: read requires `asset.read`; every mutation requires `mcp`
write scope. Tests: `test_worker_callable_candidate_lifecycle_cross_agent`
(MCP `tools/call`, Agent A create / Agent B read / no-scope rejection) and
`test_isolated_sqlite_cross_agent_candidate_persistence` (two separate
connections to an isolated DB file).

---

## 5. Migration SQL and isolated-environment evidence

`worker/migrations/0003_knowledge_candidate_golden_pipeline.sql`:

- `CREATE TABLE IF NOT EXISTS knowledge_candidates` (independent staging;
  PK `candidate_id`; status/review_state/version/hash/provenance).
- `CREATE TABLE IF NOT EXISTS approval_ledger_operations` (operation registry;
  `decision_write`, `knowledge_write`, `KNOWLEDGE_PROMOTION`).
- `CREATE TABLE IF NOT EXISTS personal_ai_approval_ledger` (single-use,
  operation-bound, FK to the registry; CAS consumption).
- Additive only: no `ALTER`/`DROP`/`DELETE`; never references `assets` /
  `asset_versions` writes.

Isolated verification (SQLite, NOT production D1):

| Check | Command | Result |
|---|---|---|
| Apply 0001 + 0002 + 0003 | `sqlite3 mig_test.db < 000{1,2,3}...sql` | exit 0 |
| Re-apply 0003 (idempotency) | same file twice | exit 0 |
| Existing rows preserved | seeded `assets`/`asset_versions` rows byte-identical after double apply | PASS (`test_isolated_sqlite_migration_is_idempotent_and_preserves_history`) |
| CAS single-use | two connections consume one approval | exactly one accepted (`test_isolated_sqlite_atomic_approval_consume_is_single_use`) |
| Operation registry FK | insert unknown operation | `IntegrityError` (rejected) |
| Cross-connection persistence | create on conn A, read on conn B | PASS (`test_isolated_sqlite_cross_agent_candidate_persistence`) |

Real Cloudflare D1 (remote) migration: **`UNVERIFIED` / NOT APPLIED** — no
wrangler/toolchain credential exists in this environment.

---

## 6. Full test and CI results

| # | Command | Environment | Exit | Result |
|---|---|---|---|---|
| 1 | `python -m pytest -q` | Python 3.11.17, pytest 9.1.1 | 0 | **1566 passed, 1 skipped** (72.00s) |
| 2 | `node --check worker/index.js` | Node v20.20.2 | 0 | syntax OK |
| 3 | `python -m pytest -q tests/test_knowledge_candidate_golden_pipeline.py` | as above | 0 | 31 passed (6 new stale-approval tests) |
| 4 | isolated `sqlite3` migration apply x2 | sqlite3 (via tests) | 0/0 | additive + idempotent |
| 5 | `git rev-parse HEAD` | repo | 0 | recorded in `agent_result.json` (fix continues from `e3ead9540b48f58b02fbb75af86fa763ca041923`) |

Targeted suites: `test_knowledge_candidate_golden_pipeline.py`,
`test_decision_ingestion_writer.py`, `test_knowledge_candidate_writer.py`,
`test_mcp_events_golden.py`, `test_skill_candidate_writer.py`.

CI (`.github/workflows/ci.yml`) only runs `python -m pytest -q`; it is green at
this commit (1566 passed, 1 skipped).

---

## 7. Concurrency and failure-recovery tests

| Test | Expectation | Where |
|---|---|---|
| Old `asset_id` direct write | REJECTED, zero I/O | `test_public_*` |
| No `candidate_id` | REJECTED `candidate_missing` | `test_public_*` |
| DRAFT direct promotion | REJECTED `candidate_state` | `test_worker_1...` |
| Review FAIL | not APPROVED_FOR_PROMOTION; atomically revokes all live candidate-bound approvals | `recordKnowledgeCandidateReview` |
| PASS -> approval -> FAIL -> PASS + old approval | REJECTED `missing_or_expired_approval`, `write_calls=0`, no Golden; old approval `invalidated=1` | `test_worker_review_fail_revokes_stale_approval` |
| PASS -> FAIL -> PASS + **new** approval | WRITTEN (fresh approval consumed once; old stays invalidated) | `test_worker_repromotion_requires_a_fresh_approval_after_fail` |
| Review on PROMOTED / CANONICAL_READBACK_VERIFIED | REJECTED `candidate_state`, status never regressed | `test_worker_review_rejects_regression_from_terminal_candidate` |
| Stale invalidation (Python + isolated SQLite) | revoke durable, old unconsumable, new required | `test_6_*`, `test_isolated_sqlite_fail_revokes_stale_approval` |
| Forged approval / `promotion_decision` | REJECTED | `test_worker_2...` |
| Expired approval | REJECTED | `test_worker_gate_rejects_expired...` |
| Cross-candidate approval reuse | REJECTED | `test_worker_approval_is_candidate_bound...` |
| Content-hash change | REJECTED | `test_worker_3...` |
| Candidate version change | REJECTED | gate binding |
| Approval replay | REJECTED / IDEMPOTENT no duplicate | `test_worker_5...`, SQL CAS test |
| Concurrent approval consume | at most one success; an invalidated row loses the CAS (`invalidated = 0`) | SQL CAS; real D1 `UNVERIFIED` |
| Two agents promote same candidate | no duplicate Golden | `test_worker_5...` |
| Canonical write ok + read-back fail | never VERIFIED; recovery metadata | `test_worker_readback_failure_is_never_reported_verified` |
| Canonical sink unavailable (429-class) | fail closed; no false success; consumed once | `test_worker_canonical_write_failure_consumes_once_and_stays_recoverable` |
| Old Knowledge read | compatible | existing writer/read suites |
| SKILL / DECISION writers | unaffected | `test_other_writers_and_legacy_reads_unaffected` |

Failure-recovery strategy: the approval is consumed before the Golden write. If
the write/read-back then fails, the result is `REJECTED` with
`recovery_required: true` and `approval_consumed: true`; the consumed approval
can never be replayed, so completion requires a fresh Human-Gate-bound approval.
If the Golden row was written but the authoritative read-back failed, the
candidate stays `PROMOTED` (never `CANONICAL_READBACK_VERIFIED`) and a later
attempt is idempotent (no duplicate).

**Real D1 concurrency is `UNVERIFIED`.** The CAS is exercised with two SQLite
connections (SQL-level single-use) and with the Node fake-D1 single thread; per
task §4 this is explicitly not claimed as real Cloudflare D1 concurrency. The
stale-approval revocation is additionally covered by the review `db.batch`
atomicity on the fake D1 and by the isolated SQLite transaction.

---

## 8. Production deploy Runbook

See `KNOWLEDGE_GATE_PRODUCTION_RELEASE_PLAN_V1.md` §2. Required order:
Preflight (read-only) -> Human Gate Worker approval + Migration approval
(separate scope, bound to commit SHA / migration hash + database_id) -> deploy
fail-closed Worker -> verify legacy bypass rejected live -> apply approved D1
migration `0003` -> verify Candidate storage + ledger -> controlled E2E ->
independent Canonical read-back -> Production PASS or fail-closed.

## 9. Security rollback Runbook

See `KNOWLEDGE_GATE_PRODUCTION_RELEASE_PLAN_V1.md` §4. Rollback preserves the
gate: disable Knowledge promotion (public Knowledge writes return `REJECTED`);
never restore the old flat writer; leave additive tables in place; never delete
or reuse consumed approval evidence; revert only to the last gated Worker.

## 10. Pre/post-production consistency check method

Re-inventory every KNOWLEDGE asset (`asset_id`, version, content_hash, status)
before and after; diff manifests; assert pre-existing assets are byte-identical;
assert `assets`/`asset_versions` row counts/hashes unchanged for pre-existing
data; assert no orphan candidates/approvals and no unconsumed validation
approvals; assert SKILL/DECISION/REALITY tool counters unchanged.

---

## 11. Not-yet-verified risks

1. Real Cloudflare D1 concurrency semantics for the CAS consume: `UNVERIFIED`.
2. `wrangler deploy --dry-run` / Worker bundle build: `UNVERIFIED` (no wrangler
   toolchain in this environment); only `node --check` + in-process execution.
3. Production D1 migration apply + idempotency on the real database:
   `UNVERIFIED` / NOT APPLIED.
4. Live production Canonical read-back and corpus diff: `UNVERIFIED` (no
   credential/transport).
5. The candidate sub-operations are exposed through the existing
   `write_knowledge_candidate` MCP tool (to keep the frozen `tools/list`
   contract of 11 tools intact). If a future task is allowed to change
   `tools/list`, dedicated tools can be split out.
6. Atomic review-status + stale-approval revocation depends on D1 `batch`
   transactional semantics; modelled here with the fake D1 and isolated SQLite,
   but not exercised on real Cloudflare D1: `UNVERIFIED`.

---

## 12. Human Gate approvals required next

1. Scope: authorize an isolated **Cloudflare D1** environment to replace the
   SQLite/fake-D1 `UNVERIFIED` concurrency + migration evidence.
2. Deploy gate (1a): approve deploying the exact RC commit SHA (bound to commit
   SHA + artifact hash).
3. Migration gate (1b): approve applying
   `0003_knowledge_candidate_golden_pipeline.sql` (bound to file hash +
   `database_id`).
4. Canonical-write gate: separate authorization only if the controlled E2E must
   write production Canonical storage.
5. Optional: authorize dedicated candidate MCP tools if a `tools/list` change is
   acceptable.

## 13. Status

**`PARTIAL`.** All in-scope code/migration/test/report deliverables are
implemented and green (`1566 passed, 1 skipped`), the migration is
isolated-verified, and no unresolved P0 **code** defect remains (including the
stale-approval vulnerability, now fixed by atomic FAIL-time revocation). The
status is not `READY_FOR_HUMAN_APPROVAL` because §7 requires real isolated-D1
(Cloudflare) concurrency/migration verification, which this environment cannot
perform; those items are `UNVERIFIED`, and no production operation was
performed. In particular, no production deploy, production migration, Canonical
write, approval create/consume, or secret/permission/binding change was
executed; test PASS is **not** claimed as production PASS.
