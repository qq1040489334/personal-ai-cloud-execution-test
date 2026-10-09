# KNOWLEDGE_GATE_PRODUCTION_RELEASE_PLAN_V1

- Companion task: `cf-00bcf790b680` (`KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_V1`)
- Repository: `qq1040489334/personal-ai-cloud-execution-test`
- Original base commit: `fb01f893f0357c4c6a1289a2ca098c139203650f`
- Document status: **STAGED — NOT EXECUTABLE YET** (`PARTIAL`; real D1 UNVERIFIED)
- Intended use: direct input to a **separate**, explicitly authorized production
  execution task. It requires no implicit context from the finalize run.

> **Read this first.** The release candidate now implements the gate (ledger
> reuse, callable candidate persistence, additive migration) and is green in
> an in-repo/isolated environment (`1560 passed, 1 skipped`). It is **not** a
> production PASS: real Cloudflare D1 concurrency/migration and production
> deploy/Canonical read-back are `UNVERIFIED`. Do not execute any step below
> until §1 is satisfied and independently verified.

---

## 0. Scope and non-negotiables

- Deploy the **fail-closed** Worker that gates Knowledge promotion.
- Apply an approved, additive-only D1 migration.
- Controlled end-to-end validation and independent Canonical read-back.
- Hard prohibitions: no production deploy without a dedicated Worker approval;
  no production D1 migration without a dedicated migration approval; no
  production Canonical write without a separate explicit authorization; never
  restore the old flat writer; do not drop/rewrite historical Knowledge data; do
  not modify existing isolated TEST fixtures; do not affect REALITY/SKILL/
  DECISION; no second Canonical and no second approval authority.

The single public Knowledge MCP tool is `write_knowledge_candidate` with
`candidate_operation` in {create, read, submit_review, review, promote}. The
`tools/list` surface stays at 11 tools.

---

## 1. Preconditions (all must be true and evidenced before ANY production step)

| # | Precondition | Verification | Status at RC |
|---|---|---|---|
| P1 | P0-A: `KNOWLEDGE_PROMOTION` uses the shared `personal_ai_approval_ledger`; no `knowledge_promotion_approvals`; worker cannot mint approvals | code review + regression tests | DONE (in-repo) |
| P2 | P0-B: `create -> DRAFT persisted -> submit/review -> Human Gate -> promote`; cross-session read proven | MCP + isolated-DB tests | DONE (isolated SQLite) |
| P3 | P0-C: `0003_knowledge_candidate_golden_pipeline.sql` committed; freeze tests converted to additive safety; idempotent on isolated DB | isolated-DB logs | DONE (isolated SQLite); real Cloudflare D1 `UNVERIFIED` |
| P4 | Full repository suite green on the exact RC commit | `python -m pytest -q` | DONE (1560 passed, 1 skipped) |
| P5 | Worker build/deploy dry-run green | wrangler dry-run | **UNVERIFIED** (no wrangler toolchain) |
| P6 | MCP tool registration/dispatch verified | `tools/list` + dispatch tests | DONE (11 tools; sub-ops tested) |
| P7 | No unresolved P0 security defect | security review | DONE in code; real-D1 concurrency `UNVERIFIED` |
| P8 | RC commit SHA frozen and recorded | `git rev-parse HEAD` | DONE (see finalize report §2) |

If any precondition fails: do not proceed; report `BLOCKED` (or `PARTIAL` when
only external real-D1 evidence is missing).

---

## 2. Production Release Runbook (exact order)

Mandatory order; each step separately approved and recorded with actor,
timestamp, command, result.

```
Step 0  Preflight (read-only)
Step 1  Human Gate Approval (Worker scope AND migration scope, separately)
Step 2  Deploy fail-closed Worker
Step 3  Verify legacy bypass rejected (live)
Step 4  Apply approved D1 migration
Step 5  Verify Candidate storage / approval ledger
Step 6  Controlled end-to-end validation
Step 7  Independent Canonical read-back
Step 8  Production PASS or fail-closed
```

### Step 0 — Preflight (read-only)
1. Record production Worker version/deployment ID and D1 schema
   (`PRAGMA table_info`).
2. Snapshot the Knowledge corpus manifest (`asset_id`, version, content_hash,
   status) as the pre-change baseline.
3. Confirm no in-flight promotions and no pending approvals.
4. Confirm `personal_ai_approval_ledger` and its `approval_ledger_operations`
   registry match the RC (`KNOWLEDGE_PROMOTION` present).

Output: `preflight_manifest.json` + `preflight_schema.txt`. Any anomaly -> STOP.

### Step 1 — Human Gate Approval
Two independent approvals with distinct scope:
- **1a. Worker deploy**: exact RC commit SHA + artifact hash.
- **1b. Migration**: `0003` file content hash + target `database_id`.

Both recorded in the trusted ledger with operation binding, `expires_at`,
single-use. An agent-minted approval is invalid. Missing/expired/replayed ->
STOP (fail-closed).

### Step 2 — Deploy fail-closed Worker
1. Deploy the approved RC SHA (same artifact as 1a).
2. Deployed Worker defaults to **reject** for any Knowledge write lacking a
   staged, reviewed, ledger-approved candidate.
3. Record `CLOUDFLARE_VERSION_ID` / `CLOUDFLARE_DEPLOYMENT_ID`.
4. On failure: stay fail-closed; go to Rollback (§4); never enable a bypass.

### Step 3 — Verify legacy bypass rejected (live)
- `asset_id`-only -> `REJECTED`/`candidate_missing`, zero writes.
- DRAFT direct promotion -> `REJECTED`.
- Forged `promotion_decision`/`approved_by`/`approval_receipt` without a ledger
  approval -> `REJECTED`.
- Wrong hash / wrong version / expired / replayed / cross-candidate approval
  -> `REJECTED`.
- Concurrency: two consumes of one approval -> at most one succeeds; two
  promotions -> no duplicate Golden.

Any failure -> STOP; promotion stays disabled; Rollback §4.

### Step 4 — Apply approved D1 migration
1. Apply `0003` with the exact artifact approved in 1b.
2. Additive only: creates `knowledge_candidates`,
   `approval_ledger_operations`, `personal_ai_approval_ledger`; never alters
   `assets`, `asset_versions` or existing Knowledge rows.
3. Run once; verify idempotent re-run is a no-op on a clone if available.
4. Record `D1_MIGRATION_RESULT` and post-migration `PRAGMA table_info`.
5. On failure: leave tables absent/unused; stay disabled; Rollback §4.

### Step 5 — Verify Candidate storage / approval ledger
1. Create a DRAFT candidate (authorized agent); read it back by `candidate_id`
   from an independent session/worker.
2. Submit for review; verify PASS/FAIL state control; verify content/version
   change invalidates prior approvals.
3. Verify the approval is in the trusted ledger, bound to
   candidate/version/hash/review/approver/expiry/operation.

### Step 6 — Controlled end-to-end validation
1. Run one controlled promotion for a designated validation asset (explicit
   authorization required if it writes Canonical).
2. Verify single-use consumption and Golden write exactly once.
3. Verify DECISION/SKILL/REALITY unaffected.

### Step 7 — Independent Canonical read-back
1. Re-read the promoted asset via `verifyKnowledgeVersion`; confirm
   hash/version match the candidate.
2. Diff the full corpus against `preflight_manifest.json`.
3. A write response alone is NOT proof; emit `CANONICAL_READBACK_VERIFIED` only
   on successful authoritative read-back.

### Step 8 — Production PASS or fail-closed
Only if Steps 0–7 all succeed may production success be reported, labelled by
the exact evidence. Any failure keeps promotion disabled and reports
fail-closed. Never represent test results as a production closed-loop PASS.

---

## 3. Post-release consistency checks

- Re-run the Step 0 manifest and diff against the pre-change baseline.
- Confirm `assets`/`asset_versions` counts/hashes for pre-existing Knowledge
  unchanged.
- Confirm no orphan candidates/approvals and no unconsumed validation approvals.
- Confirm DECISION/SKILL/REALITY counters unchanged.

---

## 4. Security Rollback Runbook

Rollback **must preserve the gate**; the old flat writer is never a rollback
target.

1. **Triggers:** Step 2/4/5/6/7 failure; unauthorized approval consumption;
   corpus drift; any P0 regression.
2. **Primary rollback — fail-closed disable.** Disable Knowledge promotion;
   public Knowledge writes return `REJECTED`; no flat-writer fallback; other
   assets continue.
3. **Worker revert.** Revert only to the last **gated** Worker version. If the
   only alternative is the pre-repair flat writer, do not deploy it.
4. **Schema rollback.** Leave additive tables in place (unused). Do not drop
   historical data. If forcibly dropped, the gate finds no candidate/approval
   and rejects; it never re-enables the bypass.
5. **Ledger.** Do not delete consumed approval evidence; never reuse a consumed
   approval.
6. **Post-rollback verification:** re-run Step 3 rejection probes and the Step 0
   corpus diff.

Invariant: at no point may rollback restore or recommend the old
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
result. Mark unverifiable items `UNVERIFIED`. Do not convert in-repo/isolated
results into production PASS.

Final status vocabulary: `READY_FOR_HUMAN_APPROVAL` (only if the finalize
report §7 conditions all hold and are evidenced), else `PARTIAL` or `BLOCKED`
with exact blockers.
