# KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_REPORT_V1

- Task ID: `cf-88666f9c9147`
- Goal: `KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_V1`
- Repository: `qq1040489334/personal-ai-cloud-execution-test`
- Base commit: `fb01f893f0357c4c6a1289a2ca098c139203650f`
- Verified HEAD at execution: `fb01f893f0357c4c6a1289a2ca098c139203650f`
- Risk level: `LOW`
- Mode: `IMPLEMENT_AND_TEST` (bounded by the injected allowlist, see §2)
- Production readiness: **`BLOCKED`** (not `READY_FOR_HUMAN_APPROVAL`; see §8 and §10)

> **Hard-hold attestation.** No production deploy, no production D1 migration, no
> Canonical write, no production approval create/consume, and no
> secret/OAuth/permission/binding change was performed. No file was deleted.
> Everything below is either a repository reading or an executed in-repo test.
> Anything not traceable to an executed command is marked `UNVERIFIED`.

---

## 1. Executive Summary

The task asked for four P0 repairs (reuse the existing approval ledger, add
callable candidate persistence entry points, unblock the migration, and produce
a unified release/rollback runbook), plus green tests and a Release Candidate.

**The repository at the pinned baseline does not meet the §7 acceptance
conditions, and this execution was not permitted to change the files required to
meet them.** The injected workflow allowlist for this run restricts repository
writes to exactly two files:

```
KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_REPORT_V1.md   (this report)
KNOWLEDGE_GATE_PRODUCTION_RELEASE_PLAN_V1.md
```

Every code artifact required by the task (`worker/index.js`,
`worker/migrations/*.sql`, `tests/*.py`) is **outside** that allowlist, so the
implementation portion of the contract could not be legally performed in this
run. The task's own §5 `FORBID` list also forbids production D1 migration and
production deploy, which is compatible with the hard-hold, but the allowlist is
stricter still.

The baseline contents were nevertheless fully audited and tested. Concrete,
still-open P0 gaps were found (see §3), so the correct verdict is **`BLOCKED`**
with a precise minimum fix plan, not `READY_FOR_HUMAN_APPROVAL` and not
`PARTIAL` (there is a hard authorization/allowed-scope blocker, not merely a
residual technical risk).

No code PASS is represented here as a production closed-loop PASS.

---

## 2. Scope Constraint Collision (root cause of BLOCKED)

| Source | Permitted writes |
|---|---|
| Task §5 `ALLOW` | Worker/MCP/ledger code, new candidate tools, new migration, revise outdated test constraints, new regression tests, commit |
| Injected workflow hard rule | **Only** `task.expected_files` (`…FINALIZE_REPORT_V1.md`, `…PRODUCTION_RELEASE_PLAN_V1.md`) |
| Task §5 `FORBID` | Production deploy / migration / Canonical write / production approval consume / second Canonical / restore flat writer |

The injected hard rule is part of the execution contract given to this agent and
overrides the task body where they conflict. The task body requires modifying
`worker/index.js`, `worker/migrations/`, and `tests/*.py`; that is disallowed
here. This is an authorization blocker that requires a follow-up task/allowlist
widening, or a human decision to relax the hard rule. It is reported as
`BLOCKED`, not silently worked around.

---

## 3. Findings at Baseline (P0 gaps, with evidence)

### 3.1 P0-A — Approval Ledger is NOT reused (second approval authority exists)

- The Worker defines its **own** promotion approval table
  `knowledge_promotion_approvals` (`worker/index.js:3030–3032`), separate from
  the trusted `personal_ai_approval_ledger`.
- A repository-wide search finds **no** use of `personal_ai_approval_ledger` in
  `worker/index.js`; the ledger implementation lives in `hello.py`
  (`hello.py:29112` `production_approval_ledger_schema`, including an
  `include_knowledge_promotion` adapter at `hello.py:29128`). The Worker does not
  call or consult it.
- `registerKnowledgePromotionApproval` (`worker/index.js:3125–3146`) accepts a
  **caller-supplied** `approval_receipt` and `approved_by` and inserts them as a
  valid, consumable approval. This directly conflicts with task requirement
  P0-A#5 ("Agent 自行提供的 `approved_by`、`approval_receipt` … 不得成为有效授权").
- Net effect: two potential approval authorities, and an agent-supplied receipt
  is accepted as authorization by the internal registration path.

### 3.2 P0-B — No callable candidate persistence entry points

- The MCP `tools/call` dispatcher (`worker/index.js:3768–3790`) exposes only
  `write_knowledge_candidate` for Knowledge writes. There is **no**
  `create_candidate`, `submit_for_review`, `register_promotion_approval`, or
  `promote_knowledge_candidate` tool.
- `stageKnowledgeCandidate` (`worker/index.js:3062`),
  `recordKnowledgeCandidateReview` (`worker/index.js:3106`), and
  `registerKnowledgePromotionApproval` (`worker/index.js:3125`) are **not called
  by any dispatch path**; they are reachable only from the Node test harness
  (`tests/test_knowledge_candidate_golden_pipeline.py:542,548,558`). They are
  dead code from a production standpoint.
- Because promotion reads only `knowledge_promotion_approvals`
  (`worker/index.js:3190`) and nothing populates it through a trusted,
  agent-callable path, the pipeline as shipped is either permanently
  fail-closed (no promotion possible) or, if the internal registration function
  were exposed, self-approvable. Either way it is not a usable authorized flow.
- The required cross-session/cross-agent persistence test cannot exist because
  the persistence entry points do not. The current tests validate in-process
  behavior through an injected fake D1, not real D1 persistence.

### 3.3 P0-C — Migration blocker unresolved

- `worker/migrations/` contains only `0001_asset_provenance_v0_2.sql` and
  `0002_dispatch_idempotency.sql`. There is **no**
  `0003_knowledge_candidate_golden_pipeline.sql`.
- The freeze test is still active and unmodified:
  `tests/test_decision_ingestion_writer.py:993 test_no_new_migration_added`
  asserts the migration set is exactly `{0001, 0002}`.
- The pipeline regression also pins that:
  `tests/test_knowledge_candidate_golden_pipeline.py:379
  test_no_new_migration_artifact_added_and_plan_documented` asserts no new
  migration file and that the DDL stays an unexecuted plan in the repair report.
- The required migration artifact, isolation-D1 execution, idempotency and
  compatibility verification cannot be delivered while those tests are frozen
  and outside the allowlist. The `knowledge_candidates` /
  `knowledge_promotion_approvals` tables therefore **do not exist in any D1
  environment**, including production.

### 3.4 P0-D — Release runbook

A unified Release Runbook and rollback plan are provided as
`KNOWLEDGE_GATE_PRODUCTION_RELEASE_PLAN_V1.md`. They are **provisional**: they
gate on the blockers above and must not be executed until §10 items are cleared.
The runbook is written so a later task can consume it without this run's
implicit context.

---

## 4. Executed Verification Evidence

| # | Command | Environment | Exit | Result |
|---|---|---|---|---|
| 1 | `git rev-parse HEAD` | runner container, baseline `fb01f89…` | 0 | `fb01f893f0357c4c6a1289a2ca098c139203650f` |
| 2 | `python -m pytest -q` | Python 3.11, pytest 9.1.1 | 0 | **1552 passed, 1 skipped** (56.66s) |
| 3 | `grep` worker for ledger/promotion symbols | repo | 0 | `knowledge_promotion_approvals` independent table present; no `personal_ai_approval_ledger` use |
| 4 | `grep` migrations | repo | 0 | only `0001`, `0002` |
| 5 | MCP dispatcher inspection (`worker/index.js:3768–3790`) | repo | 0 | no candidate/review/promote tools |
| 6 | Freeze tests inspection (`test_decision_ingestion_writer.py:993`, `test_knowledge_candidate_golden_pipeline.py:379`) | repo | 0 | still enforce no-new-migration |

- **Targeted pipeline suite** (from the prior baseline report, unchanged at this
  commit): `python -m pytest -q tests/test_knowledge_candidate_golden_pipeline.py
  tests/test_skill_candidate_writer.py tests/test_knowledge_candidate_writer.py
  tests/test_mcp_events_golden.py` → 97 passed (as recorded at
  `fb01f89`; the full suite above re-runs all of these green).
- **Worker build / MCP registration check:** no `package.json` build script
  exists at repo root; the Worker is a single ESM `worker/index.js` executed
  directly by the Worker suite. Registration is verified by static dispatch
  inspection (§3.2) and by `test_mcp_events_golden.py`. `UNVERIFIED` as a real
  `wrangler deploy --dry-run` because no wrangler/toolchain credential is present.
- **D1 migration dry-run:** `UNVERIFIED` — no migration artifact exists to dry
  run, and no isolated D1 instance is provisioned in this environment.
- **Approval atomic-consume under real concurrency:** `UNVERIFIED` — only a
  single-threaded fake-D1 harness exists; real D1 concurrency semantics cannot be
  exercised here. Per task §4 this is explicitly reported as `UNVERIFIED` and is
  **not** replaced with a mock PASS.

### 4.1 Test-suite green does not imply acceptance

`python -m pytest -q` is green because the suite encodes the *current* (frozen)
architecture, including the no-new-migration contract and the in-process fake-D1
harness. Green here means "no regression against the frozen baseline", **not**
"the §7 acceptance conditions are met". The three open P0 gaps in §3 are exactly
the cases the frozen suite does not (and is not allowed to) assert.

---

## 5. Architecture As Found (baseline `fb01f89`)

```
MCP tools/call ──► write_knowledge_candidate (worker/index.js:3612)
                        │
                        ├─ asset_type != KNOWLEDGE ──► INVALID_ASSET_TYPE
                        ├─ candidate_id missing ─────► REJECTED/candidate_missing (zero I/O)
                        └─ candidate_id present ─────► promoteKnowledgeCandidate (3149)
                                                          │ read knowledge_candidates (3026)
                                                          │ read knowledge_promotion_approvals (3030)
                                                          │ validateCandidateGate (3039)
                                                          │ single-use consume (3031)
                                                          ▼
                                              writeKnowledgeCandidate → assets/asset_versions
                                                          ▼
                                              verifyKnowledgeVersion (authoritative read-back)

Unreachable internal helpers (tests only):
  stageKnowledgeCandidate (3062)
  recordKnowledgeCandidateReview (3106)
  registerKnowledgePromotionApproval (3125)  ← accepts caller receipt/approved_by
```

Target architecture required by the task (NOT achieved):

```
create_candidate ─► knowledge_candidates DRAFT persisted (real D1, migration 0003)
      │
      ▼  submit_for_review ─► review PASS/FAIL (controlled)
      ▼
Human Gate ─► existing personal_ai_approval_ledger, operation=KNOWLEDGE_PROMOTION
      │        bound to candidate_id/version/content_hash/review_result/approved_by/expires_at
      ▼        (agent-supplied approved_by/receipt/decision is NOT valid)
promote ─► validateCandidateGate ─► Golden writer ─► Canonical read-back
```

---

## 6. What Would Be Delivered Once Unblocked (minimum fix plan)

1. **P0-A (ledger reuse).** Replace the `knowledge_promotion_approvals` table
   reads/writes in `worker/index.js` with the trusted
   `personal_ai_approval_ledger` + `KNOWLEDGE_PROMOTION` operation already
   modeled in `hello.py:29112` (`include_knowledge_promotion=True`). Remove the
   agent-callable registration path, or make it a no-op that can never mint a
   valid approval. Bind `candidate_id`, `candidate_version`, `content_hash`,
   `review_result`, `approved_by`, `expires_at`, `operation`. Enforce atomic
   single-use consumption against the ledger.
2. **P0-B (entry points).** Register minimal MCP tools `create_candidate`,
   `submit_for_review`, and `promote_knowledge_candidate` with permission
   isolation (write scope + intended-scope checks), backed by real D1
   persistence through the migration, and add an Agent A create → Agent B read →
   review → await-human-gate cross-session test.
3. **P0-C (migration).** Revise the freeze tests to assert *additive-only* safety
   (0001/0002 unchanged, no `assets`/`asset_versions` mutation, no new ungated
   write path) rather than "exactly two files"; add
   `worker/migrations/0003_knowledge_candidate_golden_pipeline.sql`; verify
   compatibility/idempotency on an **isolated** D1 (never production).
4. **P0-D (runbook).** Keep the provided runbook, re-validate after (1)–(3).

---

## 7. Security Findings

| Item | Finding |
|---|---|
| Flat/`asset_id`-only public write | Closed at the public route (`worker/index.js:2984–2990`): `REJECTED/candidate_missing` with zero I/O. |
| Second approval authority | **OPEN (P0-A).** `knowledge_promotion_approvals` is a distinct authority from `personal_ai_approval_ledger`. |
| Agent-supplied approval accepted | **OPEN (P0-A).** `registerKnowledgePromotionApproval` (`worker/index.js:3125`) trusts caller `approval_receipt`/`approved_by`. |
| Candidate persistence | **OPEN (P0-B).** No callable entry points; no migration; tables absent in D1. |
| Migration freeze | **OPEN (P0-C).** New migration forbidden by frozen tests; no isolated verification. |
| `promotion_decision` as auth | Closed: gate never reads it (`validateCandidateGate`, `worker/index.js:3039`). |
| Read-back integrity | Present: write responses are not proof; `verifyKnowledgeVersion` required. |
| Secret/OAuth/permission/binding | None read or changed. |
| Production mutations | None: no deploy, migration, Canonical write, or approval consume. |
| Deletions | None. |

Residual risk: the independently persisted candidate/approval tables cannot be
proven in a real D1 environment in this run; all concurrency claims are
`UNVERIFIED` against real D1.

---

## 8. Production Readiness Verdict

**`BLOCKED`.**

- The §7 acceptance conditions are **not** met at `fb01f89`.
- The required repairs target files outside this run's allowlist, so they could
  not be performed here.
- The provided release/rollback plan is documented but provisional and MUST NOT
  be executed until §10 is cleared.
- **No production closed-loop PASS is claimed.** All successful results are
  in-repo test results only.

---

## 9. Live Production Verification Status

- Existing Knowledge corpus (assets / versions / provenance): `UNVERIFIED` — no
  live Canonical read credential/transport in this environment.
- No production write, promotion, deploy, migration, or secret access occurred.

---

## 10. Blockers and Required Human Gate Approvals

| # | Blocker | Minimum resolution | Required approval |
|---|---|---|---|
| B1 | Allowlist forbids all code/migration/test writes | Widen `expected_files` (or provide a follow-up task) to include `worker/index.js`, `worker/migrations/0003_*.sql`, and the freeze tests | Human: authorize scope widening |
| B2 | P0-A second approval authority + agent-supplied receipt | Implement the §6.1 ledger-reuse repair | Human: authorize worker/ledger code change |
| B3 | P0-B no callable candidate tools | Register `create_candidate` / `submit_for_review` / `promote_knowledge_candidate` with permission isolation | Human: authorize new MCP tools |
| B4 | P0-C frozen migration contract | Revise freeze tests to additive-only assertions; add 0003; verify on isolated D1 | Human: authorize test-contract revision + isolated D1 |
| B5 | Real D1 concurrency / dry-run `UNVERIFIED` | Run against an isolated D1 instance | Human/external: provide isolated D1 access |
| B6 | Production Worker deploy + D1 migration | Execute only after B1–B5 and a separate gate | Human: separate scoped deploy/migration approval |
| B7 | Production Canonical write during E2E | Only if required; must be separately authorized | Human: separate Canonical-write approval |

Next Human Gate approval items (exact): (1) scope widening for B1; (2)
authorization to modify `worker/index.js` and `hello.py` ledger integration; (3)
authorization to add MCP candidate tools; (4) authorization to revise the
migration freeze tests and add `0003`; (5) isolated D1 environment access for
compatibility/idempotency/concurrency verification.

---

## 11. Evidence Summary

| Tier | Evidence |
|---|---|
| Code (frozen repo) | `worker/index.js:3030–3032` (separate approval table), `:3125–3146` (agent-supplied receipt), `:3768–3790` (no candidate tools), `:3039` (gate); `worker/migrations/` (0001/0002 only); `hello.py:29112` (existing ledger). |
| Test (executed) | `python -m pytest -q` → **1552 passed, 1 skipped**. |
| Real Worker | Static dispatch inspection + `test_mcp_events_golden.py`; no candidate tools registered. |
| Isolated D1 | **None** — `UNVERIFIED`. |
| Live production | **None** — `UNVERIFIED`. |
| Repo diff | Only this report + `KNOWLEDGE_GATE_PRODUCTION_RELEASE_PLAN_V1.md` (allowlist-limited). |
