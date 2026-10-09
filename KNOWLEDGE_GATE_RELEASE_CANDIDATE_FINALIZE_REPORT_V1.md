# KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_REPORT_V1

- Task ID: `cf-eb01535abaf2` (concurrency-race fix; parent task
  `cf-e92e0c936a1a`, stale-approval fix continuation of `cf-00bcf790b680`)
- Goal: `KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_V1`
- Repository: `qq1040489334/personal-ai-cloud-execution-test`
- Original base commit: `fb01f893f0357c4c6a1289a2ca098c139203650f`
- Continuation start commit: `66878d94107a0e828697f2a3138e5087deb59aab`
  (the prior run that only produced the two reports)
- Stale-approval fix base commit: `e3ead9540b48f58b02fbb75af86fa763ca041923`
  (business code `7908ef470baa27da7b1d9169970f4950aa4a4bb4`)
- Release-candidate code commit (prior, stale-approval fix):
  `9f23886927473268a18b3bc6f6bbdf75bf81d4e0`
- Race-fix base commit: `46a9af6caf8f608037a7ce69726371df56a80675`
  (report-only refresh that followed the stale-approval fix; this race fix is
  built on top of it and does NOT revert the accepted stale-approval fix)
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
   |                          atomic promotion claim (linearization point):
   |                          knowledge_candidates
   |                          APPROVED_FOR_PROMOTION --CAS--> PROMOTION_RESERVED
   |                          (fails closed with write_calls=0 if lost to a
   |                           concurrent review FAIL / competing promotion)
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
   |                          guarded PROMOTION_RESERVED -> PROMOTED ->
   |                          CANONICAL_READBACK_VERIFIED transitions
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
- **P0-F (review-FAIL vs promotion race fix).** Promotion now performs an
  **atomic promotion claim** before consuming the approval or calling the
  Canonical writer: `KNOWLEDGE_CANDIDATE_RESERVE` is a guarded CAS
  (`UPDATE knowledge_candidates SET status='PROMOTION_RESERVED' WHERE
  candidate_id=? AND status='APPROVED_FOR_PROMOTION' AND review_state='PASS'`).
  This is the linearization point against `recordKnowledgeCandidateReview`,
  whose guarded UPDATE only matches `DRAFT` / `PENDING_REVIEW` /
  `APPROVED_FOR_PROMOTION`:
  - If a review `FAIL` wins first, the candidate is `PENDING_REVIEW` and the
    live approval is invalidated; the promotion claim returns `changes === 0`
    and the promotion is `REJECTED` with `write_calls: 0` (no approve consume,
    no writer call).
  - If the promotion claim wins first, the candidate is `PROMOTION_RESERVED`;
    the racing `FAIL` is `REJECTED` (`candidate_state`) and can neither revoke
    the in-use approval nor be recorded.
  - All promotion lifecycle transitions after the claim are **guarded**
    (`PROMOTION_RESERVED -> PROMOTED -> CANONICAL_READBACK_VERIFIED`, and the
    compensating `PROMOTION_RESERVED -> APPROVED_FOR_PROMOTION` release on
    consume/writer failure) so a promotion can never overwrite a recorded FAIL.
  - No new approval authority or worker mint path is introduced; the claim lives
    in `knowledge_candidates.status` (free-form TEXT, so **no DDL change**).

---

## 2. Files changed and commit

| File | Change |
|---|---|
| `worker/index.js` | P0-A: ledger constants now target `personal_ai_approval_ledger`; removed `knowledge_promotion_approvals` SQL and the approval-mint function. P0-B: added `createKnowledgeCandidate`, `readKnowledgeCandidate`, `submitKnowledgeCandidateForReview`, `knowledgeCandidateReadOperation` and `candidate_operation` routing + permission isolation in the MCP dispatch. `promoteKnowledgeCandidate` now selects/consumes the trusted ledger atomically and takes the writer actor from the ledger approval. P0-F: added the `PROMOTION_RESERVED` state, `KNOWLEDGE_CANDIDATE_RESERVE` (guarded claim CAS), `KNOWLEDGE_CANDIDATE_GUARDED_UPDATE` (guarded lifecycle transitions), `releaseKnowledgeCandidateReservation` (compensating release) and stale-claim recovery. |
| `hello.py` | Added `read_knowledge_candidate` plus a durable, isolated-SQLite candidate/ledger harness (`knowledge_candidate_sqlite_connect`, `sqlite_stage_knowledge_candidate`, `sqlite_read_knowledge_candidate`, `sqlite_submit_...`, `sqlite_record_...`, `sqlite_register_knowledge_promotion_approval`, `sqlite_consume_promotion_approval`) that applies the real migration 0003 and performs the same CAS consume. P0-F: `reserve_knowledge_candidate_promotion` / `release_knowledge_candidate_promotion` (in-memory) and `sqlite_reserve_knowledge_candidate_promotion` / `sqlite_release_...` (isolated DB); the SQLite review helper now checks its guarded UPDATE `rowcount` and fails closed on a lost race. |
| `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql` | New additive migration: `knowledge_candidates`, `approval_ledger_operations`, `personal_ai_approval_ledger` + indexes. Stale-approval fix adds `invalidated` / `invalidated_at` columns (additive, still no `ALTER`/`DROP`). P0-F: comment documents `PROMOTION_RESERVED`; the DDL is unchanged because `status` is free-form TEXT (`no ALTER`/`DROP`, still additive/idempotent). |
| `tests/test_knowledge_candidate_golden_pipeline.py` | Rewritten to the ledger-reuse architecture; added MCP lifecycle, candidate-bound/single-use approval, read-back-failure, canonical-write-failure recovery, and isolated-SQLite migration/persistence/CAS tests. Stale-approval fix adds PASS->approval->FAIL->PASS regression (worker + Python + isolated SQLite), fresh-approval success, and terminal-state review rejection. P0-F: added deterministic FAIL-vs-promotion interleaving tests at the reservation / approval-consume / writer-call / post-write boundaries, stale-claim recovery, Python reservation/release semantics and isolated-SQLite reservation-vs-FAIL CAS tests. |
| `hello.py` | Stale-approval fix: `record_knowledge_candidate_review` accepts an optional `ledger` and revokes stale approvals on FAIL; `invalidate_knowledge_promotion_approvals`; gate + consume reject invalidated approvals; isolated SQLite helpers mirror the same atomic revoke semantics. |
| `tests/test_decision_ingestion_writer.py` | `test_no_new_migration_added` converted to `test_migration_set_is_additive_only_and_immutable_history`. |
| `tests/test_knowledge_candidate_writer.py` | Scope assertion updated for the read/write sub-operation isolation. |
| `KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_REPORT_V1.md` | This report. |
| `KNOWLEDGE_GATE_PRODUCTION_RELEASE_PLAN_V1.md` | Updated production plan/runbook. |

Command: `git add -A && git commit -m 'cloud agent: gpt task'`.
Prior release-candidate code+migration+test+report commit SHA (stale-approval
fix): `9f23886927473268a18b3bc6f6bbdf75bf81d4e0`. The business/ledger
implementation was frozen at
`7908ef470baa27da7b1d9169970f4950aa4a4bb4`; the stale-approval fix continues
from `e3ead9540b48f58b02fbb75af86fa763ca041923`; the report-only refresh is
`46a9af6caf8f608037a7ce69726371df56a80675`. This P0-F race fix is built on top
of `46a9af6...` (it does not revert the accepted stale-approval fix). The final
HEAD of this run is recorded in the run's `agent_result.json`.

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
- Race-fix note: the new `PROMOTION_RESERVED` candidate status requires **no
  DDL** (`status` is free-form TEXT); the file changes only in comments, so the
  migration stays additive/idempotent.
- Migration file SHA-256: `9a51d3a53ad5ac3e78e07fc9720ad5492443f5a1f6ac677018570fdfc337927a`.

Isolated verification (SQLite, NOT production D1):

| Check | Command | Result |
|---|---|---|
| Apply 0001 + 0002 + 0003 | `sqlite3 mig_test.db < 000{1,2,3}...sql` | exit 0 (re-run this task: all 3 applied) |
| Re-apply 0003 (idempotency) | same file twice | exit 0 (re-run this task: idempotent) |
| Existing rows preserved | seeded `assets`/`asset_versions` rows byte-identical after double apply | PASS (`test_isolated_sqlite_migration_is_idempotent_and_preserves_history`) |
| CAS single-use | two connections consume one approval | exactly one accepted (`test_isolated_sqlite_atomic_approval_consume_is_single_use`) |
| Operation registry FK | insert unknown operation | `IntegrityError` (rejected) |
| Cross-connection persistence | create on conn A, read on conn B | PASS (`test_isolated_sqlite_cross_agent_candidate_persistence`) |
| Reservation CAS blocks FAIL | reserve first, then FAIL | reserve wins, FAIL rejected, approval stays live (`test_isolated_sqlite_reservation_blocks_review_fail`) |
| FAIL-first blocks reservation | FAIL first, then reserve | FAIL records + revokes; reserve returns False (`test_isolated_sqlite_fail_first_blocks_promotion_reservation`) |

Real Cloudflare D1 (remote) migration: **`UNVERIFIED` / NOT APPLIED** — no
wrangler/toolchain credential exists in this environment.

---

## 6. Full test and CI results

| # | Command | Environment | Exit | Result |
|---|---|---|---|---|
| 1 | `python -m pytest -q` | Python 3.11.17, pytest 9.1.1 | 0 | **1576 passed, 1 skipped** (61.98s) |
| 2 | `node --check worker/index.js` | Node v20.20.2 | 0 | syntax OK |
| 3 | `python -m pytest -q tests/test_knowledge_candidate_golden_pipeline.py` | as above | 0 | **41 passed** (31 prior + 10 new race/stale-claim tests) |
| 4 | isolated `sqlite3` migration apply (0001+0002+0003) + re-apply 0003 | sqlite3 CLI | 0/0 | additive + idempotent; tables created |
| 5 | `git rev-parse HEAD` (at report time) | repo | 0 | race fix based on `46a9af6caf8f608037a7ce69726371df56a80675`; final HEAD in `agent_result.json` |

Targeted suites: `test_knowledge_candidate_golden_pipeline.py`,
`test_decision_ingestion_writer.py`, `test_knowledge_candidate_writer.py`,
`test_mcp_events_golden.py`, `test_skill_candidate_writer.py`.

CI (`.github/workflows/ci.yml`) only runs `python -m pytest -q`; it is green at
this commit (1576 passed, 1 skipped).

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
| **FAIL injected at approval consume** (promotion claim already held) | FAIL `REJECTED`/`candidate_state` (not recorded); promotion `WRITTEN`, `write_calls=1`, candidate `CANONICAL_READBACK_VERIFIED`, approval `consumed=1`/`invalidated=0` | `test_worker_race_fail_during_consume_is_rejected_and_promotion_wins` |
| **FAIL injected before reservation** (FAIL wins first) | FAIL records (`PENDING_REVIEW`), revokes live approval (`approvals_invalidated=1`); promotion `REJECTED`/`candidate_state`, `write_calls=0`, zero Golden, approval `consumed=0`/`invalidated=1` | `test_worker_race_fail_first_blocks_reservation_zero_writes` |
| **FAIL injected during writer call** (exact original bug window) | FAIL `REJECTED`; promotion `WRITTEN`, `write_calls=1`, exactly one Golden/version | `test_worker_race_fail_during_writer_call_is_rejected` |
| **FAIL injected after write, before PROMOTED transition** | FAIL `REJECTED`; guarded transition not overwritten; promotion `WRITTEN` | `test_worker_race_fail_after_write_before_status_update_is_rejected` |
| Stale claim, no Canonical row | `REJECTED`/`promotion_reserved`, `write_calls=0`, no approval consume | `test_worker_stale_reservation_without_canonical_fails_closed` |
| Stale claim, Canonical row present | `IDEMPOTENT`, `write_calls=0`, no duplicate | `test_worker_stale_reservation_with_canonical_advances_without_new_write` |
| Reservation vs FAIL (Python model + isolated SQLite CAS) | claim wins -> FAIL rejected; FAIL first -> claim lost | `test_python_reservation_blocks_concurrent_review_fail`, `test_isolated_sqlite_*` |
| Two agents promote same candidate | no duplicate Golden | `test_worker_5...` |
| Canonical write ok + read-back fail | never VERIFIED; recovery metadata | `test_worker_readback_failure_is_never_reported_verified` |
| Canonical sink unavailable (429-class) | fail closed; no false success; consumed once; claim released | `test_worker_canonical_write_failure_consumes_once_and_stays_recoverable` |
| Old Knowledge read | compatible | existing writer/read suites |
| SKILL / DECISION writers | unaffected | `test_other_writers_and_legacy_reads_unaffected` |

Failure-recovery strategy: promotion first atomically claims the candidate
(`APPROVED_FOR_PROMOTION -> PROMOTION_RESERVED`), then consumes the approval,
then calls the Golden writer. If the **writer** fails, the claim is released
back to `APPROVED_FOR_PROMOTION` and the result is `REJECTED` with
`recovery_required: true` and `approval_consumed: true`; the consumed approval
can never be replayed, so completion requires a fresh Human-Gate-bound approval.
If the Golden row was written but the authoritative read-back failed, the
candidate stays `PROMOTED` (never `CANONICAL_READBACK_VERIFIED`) and a later
attempt is idempotent (no duplicate). A crash that leaves a stale
`PROMOTION_RESERVED` claim advances idempotently when the Canonical row is
present, and otherwise fails closed (`promotion_reserved`, `write_calls: 0`)
without a second Canonical write.

**Real D1 concurrency is `UNVERIFIED`.** The claim CAS and the approval CAS are
exercised with the Node fake-D1 single thread and, for the ledger, with two
independent SQLite connections; per the task contract this is explicitly not
claimed as real Cloudflare D1 concurrency. The review `db.batch` atomicity
(status + stale-approval revocation) is covered on the fake D1 and in the
isolated SQLite transaction.

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

1. Real Cloudflare D1 concurrency semantics for the CAS consume **and** the
   promotion claim (`APPROVED_FOR_PROMOTION -> PROMOTION_RESERVED`):
   `UNVERIFIED`. The claim competes with a review FAIL in the same guarded
   UPDATE, but true multi-request D1 interleaving has not been observed.
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
7. The promotion claim, the approval consume and the guarded status transitions
   are separate D1 statements (the claim must be *read back* before the consume
   decides), not a single transaction. The linearization point is the claim CAS;
   the stale-claim path fails closed, but real D1 statement-level interleaving is
   `UNVERIFIED`.

---

## 12. Human Gate approvals required next

1. Scope: authorize an isolated **Cloudflare D1** environment to replace the
   SQLite/fake-D1 `UNVERIFIED` concurrency + migration evidence.
2. Deploy gate (1a): approve deploying the exact RC commit SHA (bound to commit
   SHA + artifact hash).
3. Migration gate (1b): approve applying
   `0003_knowledge_candidate_golden_pipeline.sql` (bound to file hash
   `9a51d3a5...` + `database_id`).
4. Canonical-write gate: separate authorization only if the controlled E2E must
   write production Canonical storage.
5. Optional: authorize dedicated candidate MCP tools if a `tools/list` change is
   acceptable.

## 13. Status

**`PARTIAL`.** All in-scope code/migration/test/report deliverables are
implemented and green (`1576 passed, 1 skipped`), the migration is
isolated-verified, and no unresolved P0 **code** defect remains: the
stale-approval vulnerability is fixed by atomic FAIL-time revocation and the
review-FAIL-vs-promotion concurrency race is fixed by the atomic
`PROMOTION_RESERVED` claim with guarded lifecycle transitions. The status is not
`READY_FOR_HUMAN_APPROVAL` because §7/§11 require real isolated-D1 (Cloudflare)
concurrency/migration verification, which this environment cannot perform;
those items are `UNVERIFIED`, and no production operation was performed. In
particular, no production deploy, production migration, Canonical write,
approval create/consume, or secret/permission/binding change was executed; test
PASS is **not** claimed as production PASS.
