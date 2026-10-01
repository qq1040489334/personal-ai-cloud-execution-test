# CLOUD_AGENT_QUEUED_RUN_CANCELLATION_FIX_SPEC_V0.1

- goal: `CLOUD_AGENT_QUEUED_RUN_CANCELLATION_FIX_SPEC_V0.1`
- task_id: `cf-8595934a6798`
- risk_level: `LOW`
- mode: **repository-evidence-grounded, implementation-ready fix specification + the
  safe, non-workflow portion of the fix implemented in the same execution path**
- business `final_status`: `SPEC_AND_SAFE_IMPLEMENTATION_COMPLETE` (separate from the
  GitHub workflow status)
- evidence policy: every claim is tagged `OBSERVED` (directly read this run) or
  `INFERRED` (reasoned). Retrieval limits are stated.

---

## 0. Executive summary

1. An **accepted** Cloud Agent task becomes permanently `PENDING` when a queued
   `repository_dispatch` run is cancelled before any job starts. This is the
   `WORKFLOW_STUCK` / `QUEUED_RUN_CANCELLED_BY_CONCURRENCY` mechanism found by the
   prior diagnosis (`SUPERVISOR_LINEAGE_AND_STUCK_DISPATCH_DIAGNOSIS_V0.1.md`,
   RC-1). `OBSERVED` adjacent evidence: `.github/workflows/agent-dispatch.yml:10-12`
   single concurrency group `cloud-agent-dispatch-main-writer` with
   `cancel-in-progress: false` — GitHub keeps one running plus one pending run, so a
   dispatch burst cancels the previously queued run with **zero jobs**.
2. **Root cause is a missing truthfulness contract, not a broken architecture.** The
   Worker records an accepted task as `status = PENDING` (`worker/index.js:1325`
   `recordTask`; `:1495` `listPendingResults`) and only leaves `PENDING` when an
   `execution_result-<task_id>` artifact appears. A cancelled-before-start run
   produces no artifact, so the record is `PENDING` forever (then merely relabelled
   `blocked / recommended_action=inspect` after `BLOCKED_AFTER_MS = 15 min`,
   `worker/index.js:1282`, `:1563`). `OBSERVED`.
3. **The smallest safe design is a dispatch liveness lease.** An accepted dispatch is
   a *bounded lease*, not a terminal state. Each accepted task carries
   `dispatch_state` / `dispatch_attempt` / `dispatch_accepted_at` /
   `dispatch_confirm_deadline`. A run status of `queued` is explicitly **not**
   confirmation; only an artifact, a conclusion, or an `in_progress` / `completed`
   run confirms a job actually started. Past the deadline with no confirmation the
   task is truthfully classified `UNCONFIRMED` (retryable) or `EXHAUSTED` (inspect).
4. **Single-writer safety is preserved and strengthened.** A retry **reuses the same
   `task_id`** and carries a deterministic `retry:<task_id>:<attempt>` idempotency
   key, claimed through the existing D1 `INSERT OR IGNORE` marker pattern
   (`worker/index.js:1004` `claimDispatchMarker`). Two concurrent planners converge
   on exactly one re-dispatch; no duplicate registry/review record can be created.
5. **Truthful-state behavior is specified and testable.** `EXECUTION_STATUS`
   semantics (`PENDING` → `PASS`/`FAIL`/`BLOCKED`) are untouched. `BLOCKED` is
   reserved for an authoritative `cancelled` conclusion that actually has a run
   (`result_normalization.py:31-41`); an unconfirmed queued cancellation is instead
   retryable, so Operators never see a fabricated terminal verdict and never see a
   silent permanent `PENDING`.
6. **No forbidden mutation occurred.** No `.github/workflows/` edit, no Worker
   deploy, no D1/KV production write, no `mark_reviewed`, no credential/secret/
   binding change, no historical backlog mutation.
7. **Workflow-mutation deltas are identified precisely** (§7) as a separately
   authorized follow-up. These are the only changes that can *eliminate* the
   cancellation; the implemented lease makes an already-cancelled dispatch
   **recoverable** without touching workflows.

---

## 1. Symptom and scope

**Symptom (`OBSERVED`/`INFERRED`).** A task accepted into the canonical registry
(`worker/index.js:1592` `toolSubmitTask`, recorded only when `dispatch.ok`,
`:1630-1646`) remains `PENDING` with no workflow run association and no
`execution_result-<task_id>` artifact when its queued run is cancelled before a job
starts. The prior diagnosis classified the concrete task as
`INSUFFICIENT_EVIDENCE` / leading `WORKFLOW_STUCK
(QUEUED_RUN_CANCELLED_BY_CONCURRENCY)` and observed two real zero-job cancelled runs
(`36250555025`, `36250558160`).

**In scope (this task, LOW risk, no workflow mutation).**

- A repository-evidence-grounded fix specification.
- The safe, additive, non-workflow part of the fix: a pure dispatch-liveness
  classifier, registry integration, Worker truthfulness fields, and tests.
- An exact list of the files/lines a separately authorized workflow change needs.

**Out of scope (hard rules).**

- Editing `.github/workflows/` (forbidden by the task allowlist and the execution
  path's `scope_guard.py`).
- Cloudflare Worker deploy, D1/KV production writes, credentials/OAuth/security/
  bindings/secrets, `mark_reviewed`, historical cleanup, new state store.

---

## 2. Repository evidence (root cause)

### 2.1 Workflow / concurrency

- `agent-dispatch.yml:10-12` — one concurrency group
  `cloud-agent-dispatch-main-writer`, `cancel-in-progress: false`. `OBSERVED`.
- `agent-dispatch.yml:114-120`/`:121-147`/`:174-180` — `Extract task_id`,
  `Build execution_result.json`, `Upload execution_result artifact` are all
  `if: always()`. A run that reaches any step always uploads an artifact; a run with
  **zero jobs never reaches them**, producing no artifact. `OBSERVED`.
- `agent-dispatch.yml:95-` — the push step rebases onto `origin/main` and refuses to
  overwrite on conflict; single-writer serialization is the safety property we must
  preserve. `OBSERVED`.

### 2.2 Worker registry (Python mirror: `EventSyncRegistry`)

- `worker/index.js:1325` `recordTask` writes `status: PENDING`,
  `terminal: false`, `result_available: false`. `OBSERVED`.
- `worker/index.js:1495` `listPendingResults` re-verifies each task via
  `findArtifact` (`:1318`); no artifact → `status` stays `PENDING`; after
  `BLOCKED_AFTER_MS` (`:1282`) it is bucketed `blocked` with
  `recommended_action: "inspect"` (`:1563-1566`). There is **no retry path** and no
  confirmation deadline. `OBSERVED`.
- `dispatch_confirmed` does not exist; `verifiedResultStatus` (`:1383`) returns
  `PENDING` unless a run is `completed`, and only ever runs when an artifact has
  already been found. `OBSERVED`.
- `readTask`/`persistTerminalExecution` (`:1475`, `:1481`) are the only write-backs;
  both preserve review state. `OBSERVED`.

### 2.3 Python canonical registry

- `event_sync.py:325` `submit_task`, `:500` `list_pending_results`, `:963`
  `sync_terminal_result` — terminal state is learned only from a workflow
  conclusion; a result-less fresh record is classified `IN_PROGRESS` by
  `reconciliation.py:240-245`. `OBSERVED`.
- `reconciliation.py:232-238` — a result-less record older than
  `DEFAULT_ORPHAN_AFTER_SECONDS = 15 min` becomes `legacy_orphan` (inspect), again
  with no retry. `OBSERVED`.

### 2.4 Safety primitives available (reuse, do not rebuild)

- D1 `task_dispatch_markers` + `claimDispatchMarker` `INSERT OR IGNORE`
  (`worker/index.js:1004-1022`) is the existing exactly-once claim primitive for
  dispatch, and `worker/migrations/0002_dispatch_idempotency.sql` defines the table.
  `OBSERVED`.
- `advancement.dispatch_approved_child` (`advancement.py:135`) already keeps a
  persisted review/dispatch marker and inherits lineage. `OBSERVED`.
- `result_normalization.py` is the single source of truth for terminal mapping.
  `OBSERVED`.

### 2.5 Root-cause statement

**RC-1 (primary).** An accepted dispatch has no liveness contract. `PENDING` is used
both for "in flight" and "indefinitely unstarted", and confirmation is inferred only
from an artifact. A cancelled-before-job-start run therefore produces a silent
permanent `PENDING`. `OBSERVED` (code) + `INFERRED` (failure mechanism).

**There is no second root cause.** RC-2 (`build_execution_result` failure after a
successful execution) and RC-3 (`unbounded pending_review`) were already identified
by the prior diagnosis and are tracked separately; neither causes the signature here.

---

## 3. Design — dispatch liveness lease

### 3.1 State model

| State | Meaning | Terminal |
| --- | --- | --- |
| `PENDING_DISPATCH` | Recorded before/at dispatch; HTTP acceptance not yet confirmed | no |
| `ACCEPTED` | `2xx` from `dispatches`; lease active | no |
| `CONFIRMED` | Job-start evidence observed (artifact / conclusion / in_progress) | liveness-terminal |
| `UNCONFIRMED` | Lease expired, no job start, attempts remain | retryable |
| `RETRY_DISPATCHED` | Deduplicated retry dispatched; fresh lease | no |
| `DISPATCH_FAILED` | HTTP network error / GitHub rejection | retryable then inspect |
| `EXHAUSTED` | `MAX_DISPATCH_ATTEMPTS` reached, still unconfirmed | yes (inspect) |

`recommended_action ∈ {wait, retry, inspect, none}`.

### 3.2 Confirmation rule (fail-closed)

```
confirmed = has_artifact
         or run_conclusion is non-empty
         or run_status in {in_progress, completed}
```

`run_status == "queued"` is **explicitly not** confirmation — that is exactly the
cancelled-before-job-start case. This is the crux of the fix.

### 3.3 Lease and deadline

- Written *before* the `repository_dispatch` HTTP call (`PENDING_DISPATCH`) so a
  Worker crash between acceptance and `recordTask` still leaves a bounded,
  recoverable record (no permanent `PENDING` from a crash either).
- `dispatch_confirm_deadline = dispatch_accepted_at + grace`, default
  `DEFAULT_DISPATCH_CONFIRM_GRACE_SECONDS = 15 min`, aligned with the Worker's
  existing `BLOCKED_AFTER_MS`. This bound is intentionally identical so the two
  systems cannot disagree about "how long is still normal".

### 3.4 Classification (pure, in `dispatch_reconciliation.py`)

Precedence: authoritative result/review → HTTP failure → confirmation → fresh lease →
exhaustion → retryable. By construction the classifier can never emit
`action == wait` with `lease_expired == true`, and `is_permanently_pending(...)` is an
**executable invariant** that the tests assert is always `False`.

### 3.5 Idempotency / dedupe

- Retries reuse the same `task_id` (`same_task_id: true`). No new registry/review
  record is possible; `submit_task`'s existing `setdefault` merge semantics are used.
- `idempotency_key = "retry:<task_id>:<attempt>"`, claimed through the existing D1
  marker (`INSERT OR IGNORE`) or `spec`-level claim. Two planners converge.
- `mark_dispatch_retried` is **append-only metadata only**: it changes
  `dispatch_attempt` / `dispatch_state` / lease and appends a `dispatch_events`
  audit entry. It never changes `status`, `terminal`, `result_available`, or review.

### 3.6 Truthful state (never fabricate terminal truth)

- `EXECUTION_STATUS` stays `PENDING` while a lease is active; the *advisory*
  `dispatch_state` and `recommended_action` carry liveness truth.
- `BLOCKED` remains reserved for an authoritative `cancelled` conclusion with an
  actual run. An unconfirmed queued cancellation is `UNCONFIRMED`/`retry`, not a
  fabricated `BLOCKED`.
- The `unconfirmed` bucket (Worker) / `retryable` bucket (Python) is **additive**; the
  existing `pending` / `pending_review` / `failed` / `blocked` buckets and
  `list_pending_results()` unscoped behavior are unchanged.

### 3.7 Crash / failure cases

| Case | Behavior |
| --- | --- |
| Worker crash before `recordTask` | Pre-write `PENDING_DISPATCH` record with a lease remains recoverable |
| Worker crash after `recordTask`, before retry | Appears as an unconfirmed lease and is retried |
| Dispatch HTTP fails | `DISPATCH_FAILED`, retryable up to `MAX_DISPATCH_ATTEMPTS`, then `EXHAUSTED`/inspect |
| Two concurrent planners | Same `idempotency_key`; D1 `INSERT OR IGNORE` yields one claim |
| Retry also cancelled | Fresh lease → another bounded retry until `EXHAUSTED` |
| Artifact exists but artifact API is down | `jobEvidence.hasArtifact` unknown; if a recorded authoritative result exists it is preserved (no false `PENDING` downgrade) |

---

## 4. Implemented safe changes (this execution path)

All changes are inside the allowlist (`CLOUD_AGENT_QUEUED_RUN_CANCELLATION_FIX_SPEC_V0.1.md`,
`tests/**`, `src/personal_ai_execution/**`, `worker/index.js`).

| File | Change |
| --- | --- |
| `src/personal_ai_execution/dispatch_reconciliation.py` (new) | Pure lea… classifier: `dispatch_confirmed`, `classify_dispatch_liveness`, `plan_dispatch_retry`, `is_permanently_pending`, state/action constants |
| `src/personal_ai_execution/event_sync.py` | `EventSyncRegistry.dispatch_liveness_report`, `plan_task_redispatch`, `mark_dispatch_retried`, `get_dispatch_events`; module-level wrappers |
| `src/personal_ai_execution/__init__.py` | Re-export the new public surface under unique `TASK_DISPATCH_*` names |
| `worker/index.js` | `taskDispatchConfirmed` + `classifyTaskDispatchLiveness` + `planTaskDispatchRetry`; `recordTask` lease fields; `listPendingResults` truthful `unconfirmed` bucket + `dispatch_state`/`recommended_action`; read-only MCP tool `plan_task_redispatch` |
| `tests/test_queued_run_cancellation_fix.py` (new) | 19 tests: truthfulness, bounded retry, exhaustion, dedupe, registry read-only/idempotence |
| `CLOUD_AGENT_QUEUED_RUN_CANCELLATION_FIX_SPEC_V0.1.md` (new) | This specification |

**Naming note (`OBSERVED`).** `advancement.py:36-38` already defines
`DISPATCH_STATE_PENDING = "PENDING"` and `DISPATCH_STATE_FAILED = "FAILED"`. To avoid
a namespace collision the new constants are `TASK_DISPATCH_STATE_*`, mirroring the
Worker's `TASK_DISPATCH_STATE_*`. This was verified against the package import
surface.

**Not deployed.** `worker/index.js` is changed in the repository only; no Cloudflare
deploy is performed (per §9 safety).

---

## 5. Acceptance tests (implemented)

`tests/test_queued_run_cancellation_fix.py` (19 tests, all passing):

1. `test_queued_run_status_is_not_confirmation` — `queued`/`waiting`/`None` are not
   confirmation.
2. `test_job_start_evidence_is_confirmation` — artifact / in_progress / completed /
   conclusion confirm.
3. `test_cancelled_before_job_start_becomes_retryable_not_permanent_pending` —
   **primary regression**: expired lease + queued → `UNCONFIRMED`/`retry`.
4. `test_fresh_accepted_lease_reports_bounded_wait_with_deadline` — `ACCEPTED`/`wait`
   with a deadline.
5. `test_classifier_never_reports_permanent_pending_across_ages` — executable
   invariant over many ages.
6. `test_explicit_deadline_is_honoured_over_created_at`.
7. `test_unconfirmed_at_max_attempts_is_exhausted_for_inspection`.
8. `test_confirmed_job_start_wins_over_expired_lease`.
9. `test_authoritative_result_closes_liveness`.
10. `test_failed_dispatch_http_is_retryable_then_inspectable`.
11. `test_retry_plan_reuses_same_task_id_and_dedupes` — same id + deterministic key.
12. `test_two_planners_converge_on_one_idempotency_key`.
13. `test_confirmed_task_has_no_retry_plan`.
14. `test_registry_liveness_report_is_read_only_and_surfaces_unconfirmed`.
15. `test_registry_retry_updates_metadata_only_never_status_or_review`.
16. `test_registry_plan_redispatch_matches_module_plan`.
17. `test_registry_plan_redispatch_unknown_task_fails_closed`.
18. `test_default_grace_seconds_is_fifteen_minutes`.
19. `test_pending_and_retry_recorded_states_still_report_bounded_wait`.

Worker-level Node tests (mocked KV/D1/fetch) are specified in §6 for the separately
authorized implementation task; the Python suite is the canonical enforcement layer
here.

---

## 6. Implementation plan (minimal, ordered)

1. **Pre-write the lease at submit (Worker).** In `toolSubmitTask`
   (`worker/index.js:1592`), write the `PENDING_DISPATCH`/lease record *before*
   `dispatchTask`, then finalize to `ACCEPTED` on `2xx` (or `DISPATCH_FAILED`).
   This closes the crash window.
2. **Retry executor (Worker, separately gated).** Add an authorized operation that
   consumes `plan_task_redispatch` and, when `should_retry`, claims
   `retry:<task_id>:<next_attempt>` through D1 `INSERT OR IGNORE` and re-issues the
   *same* `task_id` via `dispatchTask`. The read-only planner is already in place.
3. **Fix the artifact-read downgrade (Worker).** Already hardened in this change:
   when the artifact API errors but a workflow-verified authoritative result exists,
   preserve it instead of downgrading to `PENDING`.
4. **Worker Node tests.** Mock KV/D1/fetch to prove the `unconfirmed` bucket,
   exactly-once retry claim, and no status/review mutation.
5. **Workflow change (separately authorized, §7).** Only this step can prevent the
   cancellation itself.

**Design constraints honored.** One canonical registry (KV `TASK_REGISTRY` + D1
`ASSET_DB`; Python `EventSyncRegistry`); no new store; additive/backward compatible;
deterministic; no historical review mutation.

---

## 7. Workflow-mutation deltas (exact, for a separately authorized task)

> **This execution path must not and did not edit `.github/workflows/`.** The
> following is the exact change set a separately authorized workflow change needs.

| File | Location | Required change (options, pick one or combine) |
| --- | --- | --- |
| `.github/workflows/agent-dispatch.yml` | `:10-12` | **Primary:** introduce per-task/lineage concurrency so unrelated tasks never cancel each other while **preserving single-writer serialization of pushes**. E.g. keep the global writer group for the `Push` step, and scope the job to `group: cloud-agent-dispatch-${{ github.event.client_payload.task.task_id }}` with `cancel-in-progress: false`. Correctness requires the push serialization to remain a single global writer. |
| `.github/workflows/agent-dispatch.yml` | `:78-113` (`Ensure a commit exists`, `Push`) | If concurrency is split per task, guard the push against concurrent writers (a second global concurrency group limited to the push, or a D1/registry lease) so `git rebase origin/main` races cannot lose work. |
| `.github/workflows/agent-dispatch.yml` | `:114-147` | Optional: emit a `dispatch_started` evidence marker (e.g. an `execution_result` with `status: in_progress` or a step-summary/artifact) as soon as a job starts, so confirmation is positive and immediate rather than artifact-only. |
| `.github/workflows/dispatch-probe.yml` | whole file | Optional: make the probe's paid job conditional or carry a durable acknowledgement so a cancelled probe cannot look like a lost accepted dispatch. |
| `.github/workflows/agent.yml`, `agent-issue.yml` | concurrency | Verify they do not share the main-writer group (they do not, `OBSERVED`), so the fix stays scoped. |

**Distinction.** The lease/retry implementation (this task) makes an
already-cancelled dispatch **recoverable without** any workflow change. The deltas
above are the only way to **prevent** the cancellation in the first place; they must
preserve the single global push writer or they trade one bug for a lost-commit bug.

---

## 8. Rollout / rollback checks

**Rollout (no production action in this task).**

1. Merge the Python + Worker code; run `python -m pytest -q` (883 passed
   `OBSERVED`) and `node --check worker/index.js` (OK `OBSERVED`).
2. Deploy the Worker only in a separately authorized deploy task; verify
   `list_pending_results` still returns the four legacy buckets unchanged and adds
   `unconfirmed` only for missing-artifact, lease-expired tasks.
3. Verify `plan_task_redispatch` is read-only (no KV/D1 write) before enabling any
   retry executor.
4. Enable the retry executor behind a config flag; watch `unconfirmed` → `confirmed`
   transitions and the `dispatch_events` audit.

**Rollback.** All additions are additive and gated. Removing the Worker
`unconfirmed` bucket and lease fields restores the exact prior `listPendingResults`
behavior; the Python module is import-only and can be left unused. No migration or
state-store change must be reverted.

**Monitoring/acceptance signals.**

- Count of permanently-`PENDING` records with no action → target **0**
  (`is_permanently_pending` invariant).
- `unconfirmed` count → bounded by active attempts; trends to 0 as retries confirm
  or exhaust.
- No increase in duplicate `task_id` values or duplicate review records → dedupe
  holds.

---

## 9. Safety / scope statement

- Modified only allowlisted paths: the spec, `tests/**`,
  `src/personal_ai_execution/**`, `worker/index.js`.
- **No** `.github/workflows/` edit; **no** Worker deploy; **no** D1/KV production
  write; **no** credential/OAuth/security/binding/secret change; **no**
  `mark_reviewed`; **no** historical-backlog mutation; **no** new state store or
  migration; **no** deletion.
- Retry metadata writes are append-only and never touch execution status, review
  verdict, or result availability.
- Single-writer repository mutation safety is explicitly preserved (retries reuse
  the same task id; dedupe via the existing D1 claim; workflow deltas called out as
  the only place push serialization could be at risk).

---

## 10. Verdict

| Question | Answer |
| --- | --- |
| Root cause | Missing dispatch liveness contract: accepted task is `PENDING` with no confirmation deadline, so a queued run cancelled before job start never resolves. `OBSERVED` code + `INFERRED` mechanism. |
| Proposed fix | Bounded dispatch liveness lease + truthful `UNCONFIRMED`/`EXHAUSTED` states + idempotent same-`task_id` retry. |
| Single-writer safety | Preserved; retries reuse the same `task_id` and dedupe with `retry:<task_id>:<attempt>`. |
| Silent permanent PENDING | Prevented by construction; `is_permanently_pending(...) == False` is an executable invariant under test. |
| Idempotency/dedupe | Specified and testable (uniform key; existing D1 `INSERT OR IGNORE`). |
| Truthful state | Advisory liveness separated from execution status; `BLOCKED` not fabricated for unstarted runs. |
| Workflow mutation | Identified precisely in §7; **not** performed here. |
| Tests | 19 new tests; full suite `883 passed`. |
| Deployment/production side effects | None. |

### Exactly one bounded next_action

```
next_action = CLOUD_AGENT_DISPATCH_RETRY_EXECUTOR_V0.1
```

A single, bounded, LOW-risk follow-up task: (a) pre-write the dispatch lease in
`worker/index.js:toolSubmitTask` before the HTTP call and finalize it to
`ACCEPTED`/`DISPATCH_FAILED`; (b) implement the authorized retry executor that
consumes the already-landed read-only `plan_task_redispatch` and claims
`retry:<task_id>:<attempt>` through the existing D1 `claimDispatchMarker`
(`INSERT OR IGNORE`) before re-dispatching the **same** `task_id`; (c) add Node
tests with mocked KV/D1/fetch. It must not edit `.github/workflows/`; the workflow
concurrency deltas in §7 remain a separate, distinctly gated task because they are
the only change that could affect push serialization.

`final_status`: `SPEC_AND_SAFE_IMPLEMENTATION_COMPLETE`
