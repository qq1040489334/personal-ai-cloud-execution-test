# KNOWLEDGE_GATE_PRODUCTION_RELEASE_PLAN_V1

- Companion task: `cf-88666f9c9147` (`KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_V1`)
- Repository: `qq1040489334/personal-ai-cloud-execution-test`
- Baseline commit analyzed: `fb01f893f0357c4c6a1289a2ca098c139203650f`
- Document status: **STAGED — NOT EXECUTABLE YET**
- Intended use: direct input to a **separate**, explicitly authorized production
  execution task. This document requires no implicit context from the finalize
  run.

> **Read this first.** At the analyzed baseline the Knowledge Promotion Gate is
> **BLOCKED** (see `KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_REPORT_V1.md` §3,
> §8, §10). Do **not** execute any step in this plan until every precondition in
> §1 is satisfied and independently verified. This document is a plan, not a
> production PASS.

---

## 0. Scope and non-negotiables

In scope for the eventual production task:

- Deploy the **fail-closed** Worker that gates Knowledge promotion.
- Apply an approved, additive-only D1 migration.
- Controlled end-to-end validation and independent Canonical read-back.

Hard prohibitions (inherit from the task contract):

- No production deploy without a dedicated Worker approval.
- No production D1 migration without a dedicated migration approval.
- No production Canonical write without a separate, explicit authorization.
- Never restore or use the old flat writer as a rollback target.
- Do not drop/rewrite historical Knowledge data.
- Do not modify existing isolated TEST fixtures.
- Do not touch other three assets (REALITY / SKILL / DECISION) behaviour.
- No second Canonical and no second approval authority.

---

## 1. Preconditions (all must be true and evidenced before ANY production step)

| # | Precondition | Verification |
|---|---|---|
| P1 | P0-A fixed: `KNOWLEDGE_PROMOTION` bound to existing `personal_ai_approval_ledger`; no `knowledge_promotion_approvals` authority; agent-supplied `approved_by`/`approval_receipt`/`promotion_decision` cannot authorize | code review + regression tests |
| P2 | P0-B fixed: callable `create_candidate` → DRAFT persisted → `submit_for_review` → PASS/FAIL → await Human Gate → promote; cross-session read proven | cross-agent test evidence |
| P3 | P0-C fixed: `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql` committed; freeze tests revised to additive-only assertions; migration idempotent/compatible on **isolated** D1 | isolated D1 logs |
| P4 | Full repository suite green on the exact RC commit | `python -m pytest -q` output |
| P5 | Worker build/deploy dry-run green | wrangler dry-run output |
| P6 | MCP tool registration/dispatch verified for candidate tools | `tools/list` + dispatch tests |
| P7 | No unresolved P0 security defect | security review sign-off |
| P8 | RC commit SHA frozen and recorded | git rev-parse |

If any precondition fails: do not proceed; report `BLOCKED`.

---

## 2. Production Release Runbook (exact order)

The order below is mandatory. Each step must be separately approved and recorded
with actor, timestamp, command, and result.

```
Step 0  Preflight (read-only)
Step 1  Human Gate Approval  (Worker scope AND migration scope, separately)
Step 2  Deploy fail-closed Worker
Step 3  Verify legacy bypass rejected (live)
Step 4  Apply approved D1 migration
Step 5  Verify Candidate storage / approval ledger
Step 6  Controlled end-to-end validation
Step 7  Independent Canonical read-back
Step 8  Production PASS or fail-closed
```

### Step 0 — Preflight (read-only)

1. Record current production Worker version/deployment ID and the current D1
   schema (read-only `PRAGMA table_info`).
2. Snapshot the existing Knowledge corpus manifest: for every KNOWLEDGE asset,
   record `asset_id`, current `version`, `content_hash`, status (read-only).
   This is the pre-change consistency baseline.
3. Confirm no in-flight Knowledge promotions (`knowledge_candidates` absent or
   empty at this point) and no pending approvals.
4. Confirm `personal_ai_approval_ledger` is reachable and its
   `KNOWLEDGE_PROMOTION` operation definition matches the RC.

Output: `preflight_manifest.json` + `preflight_schema.txt`.
Gate: any anomaly (unexpected writes, unknown schema drift) → STOP.

### Step 1 — Human Gate Approval

Requires **two independent approvals** with distinct scope:

- **1a. Worker deploy scope.** Approve deploying the exact RC commit SHA to the
  production Worker. Bind approval to commit SHA + artifact hash.
- **1b. Migration scope.** Approve applying
  `0003_knowledge_candidate_golden_pipeline.sql` to production D1. Bind approval
  to migration file content hash + target `database_id`.

Both approvals must be recorded in the trusted `personal_ai_approval_ledger`
with operation binding, `expires_at`, and single-use semantics. An approval the
agent minted for itself is invalid. If either is missing/expired/replayed: STOP
(fail-closed).

### Step 2 — Deploy fail-closed Worker

1. Deploy the approved RC commit SHA (same artifact verified in Step 1a).
2. The deployed Worker must default to **reject** for any Knowledge write that
   lacks a staged, reviewed, ledger-approved candidate.
3. Record `CLOUDFLARE_VERSION_ID` and `CLOUDFLARE_DEPLOYMENT_ID`.
4. If deploy fails: Worker remains fail-closed; Knowledge Promotion stays
   disabled; go to Rollback (§4). Do not enable any bypass.

### Step 3 — Verify legacy bypass rejected (live)

Against the live endpoint, via an authorized read/write-scope probe:

- `write_knowledge_candidate` with `asset_id`-only → `REJECTED` /
  `candidate_missing`, zero writes.
- DRAFT candidate direct promotion → `REJECTED`.
- Forged `promotion_decision` without ledger approval → `REJECTED`.
- Wrong content hash / wrong version / expired approval / replayed approval /
  cross-candidate approval reuse → `REJECTED`.
- Concurrency: two simultaneous consumes of the same approval → at most one
  succeeds; two simultaneous promotions → no duplicate Golden.

If any probe fails: STOP; Knowledge Promotion stays disabled; Rollback §4.

### Step 4 — Apply approved D1 migration

1. Apply `0003` to production D1 using the **exact** artifact approved in 1b.
2. Migration is additive only: creates `knowledge_candidates` and (if used)
   ledger-compatible promotion structures; never alters `assets`,
   `asset_versions`, or existing Knowledge rows.
3. Run the migration **once**; verify idempotent re-run is a no-op on a clone if
   available.
4. Record `D1_MIGRATION_RESULT` and post-migration `PRAGMA table_info`.
5. On failure: leave tables absent/unused; Knowledge Promotion stays disabled;
   Rollback §4. Never re-enable the flat writer.

### Step 5 — Verify Candidate storage / approval ledger

1. Create a DRAFT candidate (authorized agent), read it back by `candidate_id`
   from an independent session/worker.
2. Submit for review; verify PASS/FAIL state control; verify content/version
   change invalidates prior approvals.
3. Verify the approval is stored in the trusted ledger, bound to
   candidate/version/hash/review/approver/expiry/operation.

### Step 6 — Controlled end-to-end validation

1. Run one controlled promotion for a **non-production-impacting** test asset or
   a designated validation asset (require explicit authorization if it writes
   Canonical).
2. Verify single-use approval consumption and Golden write exactly once.
3. Verify other operations (DECISION / SKILL / REALITY) are unaffected.

> If Step 6 requires a production Canonical write, it MUST be covered by a
> separate Human Gate authorization (precondition B7). Without it, restrict E2E
> to the read-only + rejection paths.

### Step 7 — Independent Canonical read-back

1. Re-read the promoted asset from an independent path (`verifyKnowledgeVersion`)
   and confirm `content_hash`/version match the candidate.
2. Re-inventory the full Knowledge corpus and diff against
   `preflight_manifest.json`: pre-existing assets must be byte-identical
   (no silent mutation).
3. A write response alone is **not** proof. `CANONICAL_READBACK_VERIFIED` may be
   emitted only when the authoritative read-back succeeds.

### Step 8 — Production PASS or fail-closed

- Only if Steps 0–7 all succeed may the task report production success, and it
  must be labelled by the exact evidence collected.
- Any failure keeps Knowledge Promotion **disabled** and reports fail-closed.
- Never represent test-environment results as a production closed-loop PASS.

---

## 3. Post-release consistency checks

- Re-run Step 0 manifest and diff against pre-change baseline.
- Confirm `assets` / `asset_versions` row counts and hashes for pre-existing
  Knowledge unchanged.
- Confirm no orphan candidates/approvals and no unconsumed approvals from the
  validation.
- Confirm DECISION/SKILL/REALITY tool counters unchanged.

---

## 4. Security Rollback Runbook

Rollback **must preserve the gate**. The old flat writer is a defect and is
never a rollback target.

1. **Trigger conditions:** Step 2/4/5/6/7 failure; unauthorized approval
   consumption; drift in pre-existing corpus; any P0 regression.
2. **Primary rollback — fail-closed disable.** Disable the Knowledge promotion
   path. Public Knowledge writes return `REJECTED`; no fallback to the flat
   writer. Other assets continue normally.
3. **Worker revert.** Revert to the last **gated** Worker version only. If the
   only alternative is the pre-repair flat writer, do not deploy it — use the
   fail-closed disable instead.
4. **Schema rollback.** Leave additive tables in place (unused). Do not drop
   historical data. If forcibly dropped, the gate finds no candidate/approval and
   rejects — it never re-enables the bypass.
5. **Ledger.** Do not delete consumed approval evidence. Record rollback in the
   ledger as an audit event if supported; never reuse a consumed approval.
6. **Post-rollback verification:** re-run Step 3 rejection probes and Step 0
   corpus diff.

Invariant: at no point may rollback restore or recommend the old flat
candidate-to-Canonical bypass.

---

## 5. Roles / approvals matrix

| Action | Approver | Binding |
|---|---|---|
| Deploy fail-closed Worker | Human Gate (1a) | commit SHA + artifact hash |
| Apply D1 migration `0003` | Human Gate (1b) | migration file hash + database_id |
| Production Canonical write (if any) | Separate Human Gate | asset scope + approval receipt |
| Rollback to fail-closed | On-call + recorded | incident id |

---

## 6. Reporting requirements for the execution task

For every step record: command, environment, exit code, pass/fail counts,
evidence file, commit SHA, Cloudflare version/deployment IDs, D1 migration
result. Mark unverifiable items `UNVERIFIED`. Do not convert in-repo/mock
results into production PASS.

Final status vocabulary: `READY_FOR_HUMAN_APPROVAL` (only if
`KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_REPORT_V1.md` §7 conditions all hold
and are evidenced), else `PARTIAL` or `BLOCKED` with exact blockers.
