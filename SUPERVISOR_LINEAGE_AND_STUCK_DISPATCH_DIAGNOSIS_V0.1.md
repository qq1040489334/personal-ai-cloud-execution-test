# SUPERVISOR_LINEAGE_AND_STUCK_DISPATCH_DIAGNOSIS_V0.1

- goal: `SUPERVISOR_LINEAGE_AND_STUCK_DISPATCH_DIAGNOSIS_V0.1`
- diagnosis task_id: `cf-b263511960d9`
- subject under diagnosis: `cf-9f9b621849e4` (active Cloud Assets Activation task)
- project: Cloud Assets Activation
- risk_level: `LOW`
- mode: **diagnosis + implementation-ready spec only** (no production code change, no
  Cloudflare deploy, no Worker/MCP change, no workflow change, no `mark_reviewed`, no
  historical review-state mutation)
- business `final_status`: `DIAGNOSIS_COMPLETE` (separate from GitHub workflow status)
- evidence policy: every claim is tagged `OBSERVED` (directly read in this run) or
  `INFERRED` (reasoned, not directly read). Retrieval limits are stated explicitly.

---

## 0. Executive summary

1. **`cf-9f9b621849e4` is not observable anywhere in the repository or in the public
   GitHub run/artifact metadata.** It appears in no tracked file, no commit across all
   142 commits / all refs, and there is no artifact named
   `execution_result-cf-9f9b621849e4` (GitHub artifacts API `total_count = 0`).
2. The task premise says it *remains `PENDING` with no workflow/artifact*. A
   repository/CI-level `PENDING` that never resolves has a **small set of deterministic
   mechanisms**, all of which are reproducible from existing evidence: dispatch not
   accepted (`DISPATCH_STUCK`), dispatch accepted but the run was cancelled before it
   executed (`WORKFLOW_STUCK`), or the run executed but result publication failed
   (`RESULT_SYNC_STUCK`). `RESULT_SYNC_STUCK` is **ruled out** here because no artifact
   exists at all; a completed run always uploads `execution_result-<task_id>`
   (`.github/workflows/agent-dispatch.yml:174-180`, step 17 is `if: always()`).
3. The **dominant, OBSERVED** mechanism that produces exactly this signature is
   **concurrency cancellation of queued `cloud-agent-dispatch` runs**: the workflow uses
   a single-writer concurrency group with `cancel-in-progress: false`
   (`agent-dispatch.yml:10-12`), so a burst of dispatches leaves one running and cancels
   previously *queued* runs. Two such runs in this repo were cancelled with **zero jobs**
   (never executed) and therefore produced no artifact and never updated any registry.
4. **Task-level classification: `INSUFFICIENT_EVIDENCE`** for the exact task, because the
   Worker KV registry and the `dispatch-probe` job logs (which carry the `task_id`) are
   not readable from this environment. **Leading mechanism class: `WORKFLOW_STUCK`**
   (`QUEUED_RUN_CANCELLED_BY_CONCURRENCY`), with `DISPATCH_STUCK` and
   `RESULT_SYNC_STUCK` disfavored and the exact disambiguating evidence named in §6.
5. The **structural fix** is a deterministic, additive **active-project lineage filter**:
   optional `project_id` / `root_task_id` (and existing `parent_task_id`) metadata on the
   canonical Task Registry, propagated through the existing dispatch edge, with an
   **optional** lineage scope on `list_pending_results`. Default (no scope) behavior is
   unchanged, so the 101 historical `pending_review` items are never bulk-cleaned and
   never hijack selection once the Supervisor passes the active project's lineage key.

No production deploy/write, no credential/OAuth/security/binding/workflow change, no
`mark_reviewed`, and no historical backlog mutation were performed.

---

## 1. Subject under diagnosis

| Field | Value |
| --- | --- |
| Diagnosis task_id | `cf-b263511960d9` |
| Subject task_id | `cf-9f9b621849e4` |
| Project | Cloud Assets Activation |
| Claimed symptom | Remains `PENDING`, no workflow run association, no artifact |
| Prior adjacent task (do NOT resubmit) | `cf-60656d12bd7a` — Decision Writer spec (`DECISION_INGESTION_WRITER_SPEC_V0.1.md`, HEAD `6912834`) |
| Canonical Worker / registry | `worker/index.js` (Cloudflare `personal-ai-execution-mcp`), KV `TASK_REGISTRY`, D1 `ASSET_DB` (`worker/wrangler.toml:8-14`) |
| Canonical Python registry | `src/personal_ai_execution/event_sync.py` (`EventSyncRegistry`) |

This task **did not** resubmit `cf-9f9b621849e4` and **did not** create a duplicate
Decision Writer task (`cf-60656d12bd7a`). Both are explicitly out of scope.

---

## 2. Evidence inventory (`OBSERVED` unless marked)

### 2.1 Repository evidence

- `cf-9f9b621849e4` does **not** appear in any tracked file. Searches over the working
  tree, all 142 commits, all branches (`main`, `codex/cloudflare-obsidian-mirror-20260930`)
  and both tags (`expected-files-v1-20260926`, `production-recovered-3e2fed43-20260926`)
  return no match.
- No report, JSON registry dump, or test fixture in the repo references Cloud Assets
  task `cf-9f9b621849e4`. The only Cloud Assets material is the static activation
  baseline `personal_ai_cloud_assets_activation_v1()` (`hello.py:20893`), which contains
  no task ids.
- The most recent committed Cloud Assets change is `790f09f` (`hello.py`, `test_hello.py`;
  dispatched as `cf-d623dfda0107`). It is unrelated to `cf-9f9b621849e4`.

### 2.2 Public GitHub evidence (read-only, no credentials)

Source of truth: `https://api.github.com/repos/qq1040489334/personal-ai-cloud-execution-test`.

| Evidence | Value |
| --- | --- |
| Artifacts total | `139` |
| Artifacts named `execution_result-cf-9f9b621849e4` | `0` (`total_count = 0`) |
| Workflow runs collected | `295` |
| `cloud-agent-dispatch` conclusions | success `110`, failure `28`, cancelled `8`, in_progress `1` |
| `dispatch-probe` runs | `106` (all success) |
| Active workflows | `cloud-agent-dispatch`, `cloud-agent-issue`, `cloud-agent`, `ci`, `dispatch-probe` |

Notable conditions derived from this data:

- Every completed/failed/cancelled `cloud-agent-dispatch` run that reached step 7
  (`Write task contract from client_payload`) and step 17 (`Upload execution_result
  artifact`) produced `execution_result-<task_id>`. Cancellation after step 7 still
  uploaded an artifact (e.g. run `36220934446` → `execution_result-cf-33ef3836eb27`).
- **Two cancelled runs produced no artifact because they never executed a job at all:**
  `36250555025` (run `#72`, `2026-09-26T15:02:36Z`) and `36250558160` (run `#73`,
  `2026-09-26T15:02:39Z`). The GitHub jobs API returns an **empty job list** for both.
  They were created 2–3 s after run `#71` (`36250553262`) on the same single-writer
  concurrency group. This is the exact "dispatch accepted, workflow never started, no
  artifact" signature.
- Runs can also fail *after* execution but before result publication, yielding no
  artifact (e.g. run `36191902461` `#48`: Gate 1–3 and Push succeeded, step 16
  `Build execution_result.json` failed, step 17 upload failed → no artifact).

### 2.3 Dispatch / registry code path (canonical, multi-file, no second store)

Production (Cloudflare Worker, `worker/index.js`):

1. MCP `submit_task` (`worker/index.js:2188`) → `toolSubmitTask` (`:1514`).
2. `buildContract` (`:900`) mints `task_id` = `cf-` + 12 hex and **carries no lineage
   fields** (only `task_id`, `goal`, `instructions`, `risk_level`, `expected_files`,
   `acceptance`).
3. `dispatchTask` (`:955`) → `POST .../dispatches` with `event_type = gpt_task`.
4. **Only if `dispatch.ok`** does `recordTask` (`:1266`) write KV `task:<task_id>` with
   `status = PENDING` (`:1269-1281`) and return `submitted: true, dispatch_status:
   "accepted"` (`:1548-1564`).
5. `listPendingResults` (`:1319`) re-verifies each task via `findArtifact` (`:1186`); if
   no artifact, status stays `PENDING` (`:1332-1350`) and after `BLOCKED_AFTER_MS = 15
   min` it is bucketed as `blocked` with `recommended_action: "inspect"` (`:1260`,
   `:1374-1379`). `pending_review` is only populated when `result_available` is true
   (`:1369-1372`).
6. `recordTask` metadata (`:1269-1281`) and `listTasks` (`:1288`) also carry **no lineage
   fields**. `dispatchApprovedChild` (`:1055`) records parent linkage only in D1
   `task_dispatch_markers` (`:999-1041`) and the parent's `review_dispatch`; the child
   contract built by `buildApprovedChildContract` (`:1044`) has **no** `parent_task_id`.

Python (canonical `EventSyncRegistry`, `src/personal_ai_execution/event_sync.py`):

7. `submit_task` (`:184`) writes a record with **no lineage fields**; extra keys are
   accepted via `setdefault` (`:251-255`), so adding lineage is additive.
8. `list_pending_results` (`:359`) returns **every** terminal, unreviewed task and sorts
   by `task_id` — i.e. it cannot distinguish the active project from historical backlog.
9. `advancement.dispatch_approved_child` (`advancement.py:135`) does add
   `parent_task_id` to the child contract (`:200`) and keeps a `review_dispatch` marker
   (`:198`), but the registry record for the child still has no project/root lineage.

Workflow (`.github/workflows/agent-dispatch.yml`):

10. `concurrency: group: cloud-agent-dispatch-main-writer, cancel-in-progress: false`
    (`:10-12`).
11. Artifact `execution_result-${{ task_id }}` is uploaded with `if: always()` when the
    task id was extracted (`:174-180`); step 17 is what makes any started run visible.

---

## 3. Findings on `cf-9f9b621849e4`

| Question | Finding | Evidence class |
| --- | --- | --- |
| Is the task present anywhere in repo history/tags/branches? | **No** | `OBSERVED` |
| Does a workflow artifact for it exist? | **No** (`total_count = 0`) | `OBSERVED` |
| Is there a GitHub run directly bound to it? | **Cannot bind** — `repository_dispatch` payloads are not exposed by the runs API, and `dispatch-probe` logs (which echo `task_id`) return HTTP 403 unauthenticated | `OBSERVED` (absence of binding) |
| Was its dispatch actually accepted? | **Not directly verifiable.** If its KV record is `PENDING`, acceptance is implied by `toolSubmitTask` recording only on `dispatch.ok` (`worker/index.js:1548-1549`). This is a **premise**, not an independently read fact | `INFERRED` |
| Did a workflow ever start? | **No artifact + no bound run.** Most consistent with either no run created or a run cancelled before any job step; the queued-cancellation mechanism is `OBSERVED` elsewhere in this repo | `INFERRED` |
| Is it RESULT_SYNC_STUCK? | **No** — RESULT_SYNC_STUCK requires a completed run with an artifact and a stale registry; there is no artifact | `OBSERVED` (ruled out) |
| Is it RUNNING / PENDING_VALID? | **Unlikely** — no active run for it; the only in-progress run is this diagnosis (`36823089911`) | `INFERRED` |

### 3.1 Classification (single primary field)

```
task_level_classification = INSUFFICIENT_EVIDENCE
leading_mechanism_class   = WORKFLOW_STUCK  (QUEUED_RUN_CANCELLED_BY_CONCURRENCY)
```

- `INSUFFICIENT_EVIDENCE` is the correct **task-level** verdict because the two
  authoritative sources that would name the task's run — the Worker KV record
  `task:cf-9f9b621849e4` and the paired `dispatch-probe` job log — are not readable in
  this environment.
- `WORKFLOW_STUCK` is the **leading mechanism**: given a KV record that is `PENDING` and
  no artifact, the only consistent classes are "never dispatched" (`DISPATCH_STUCK`) or
  "dispatched but the workflow never produced a result" (`WORKFLOW_STUCK`). The repository
  demonstrably exhibits `WORKFLOW_STUCK` via single-writer concurrency cancellation (zero
  job runs `36250555025`, `36250558160`), and the task is described as already accepted
  into the registry (`PENDING`), which favors `WORKFLOW_STUCK` over `DISPATCH_STUCK`.

---

## 4. Systemic root cause (why "PENDING with no artifact" happens)

**RC-1 (primary): single-writer concurrency cancels queued dispatches.**
`agent-dispatch.yml:10-12` puts every `gpt_task` dispatch in one concurrency group. GitHub
allows only one *pending* run per group; when a new dispatch is queued, the previously
queued run is cancelled while the running one continues. A burst therefore yields runs
that are `cancelled` with **zero jobs** (`OBSERVED`: `36250555025`, `36250558160`). Such a
run writes no `task.json`, uploads no artifact, and (for a child dispatch) never runs the
agent; the parent's KV record stays `PENDING` forever, then becomes `blocked /
recommended_action=inspect` after 15 minutes (`worker/index.js:1260`, `:1374-1379`).

**RC-2 (secondary): result build/upload can fail after a successful execution.**
Run `36191902461` (`#48`) executed through Push but step 16/17 failed, so no artifact was
produced. This is a `RESULT_SYNC_STUCK`-adjacent failure mode independent of RC-1.

**RC-3 (selection risk, independent of the stuck task): unbounded `pending_review`.**
`listPendingResults` (`worker/index.js:1319`) and `EventSyncRegistry.list_pending_results`
(`event_sync.py:359`) return *all* terminal-unreviewed tasks, sorted only by `task_id`.
With a large historical `pending_review` backlog (reported as 101 items), a Supervisor
that scans this list can select a stale task or mis-associate the active project. There is
**no lineage metadata** on records (`buildContract` `:900`, `recordTask` `:1269`,
`submit_task` `event_sync.py:184`) to disambiguate the active project.

None of these are caused by the canonical architecture being wrong; they are missing
metadata + a missing optional filter and one workflow-concurrency policy choice.

---

## 5. Fix specification — smallest deterministic active-project lineage filter

### 5.1 Design constraints

- Reuse the **existing canonical Task Registry** only: KV `TASK_REGISTRY` + D1
  `ASSET_DB` (Worker) and `EventSyncRegistry` (Python). **No second state store, no new
  agent platform, no PersonOS/Curator/Inbox, no new binding, no new secret.**
- **Additive and backward compatible**: with no scope supplied, behavior is byte-for-byte
  the current behavior.
- **No mutation of historical review state**; the 101 historical `pending_review` items
  are never bulk-cleaned and never auto-reviewed.
- **Deterministic**: selection is by an explicit key match, never by scanning/guessing.

### 5.2 Metadata contract (optional, additive)

New optional fields on a canonical registry record (both Worker KV metadata and Python
`EventSyncRegistry` records):

| Field | Meaning | Resolution rule |
| --- | --- | --- |
| `project_id` | Stable identifier of the active project/lineage | Use verbatim when present |
| `root_task_id` | First task id of the lineage | Use verbatim when present; else derive from parent chain; else self |
| `parent_task_id` | Immediate parent (already used by `advancement.py:200`) | Existing field, unchanged |

Resolution function (pure, fail-closed):

```
resolve_lineage(record, index):
    if record.project_id:                 return ("project", record.project_id)
    root = record.root_task_id
    if root:                              return ("root", root)
    parent = record.parent_task_id
    seen = set()
    while parent and parent not in seen and len(seen) < 64:
        seen.add(parent)
        p = index.get(parent)
        if p is None:                     break          # unknown parent -> stop, fail closed
        if p.root_task_id:                return ("root", p.root_task_id)
        if p.project_id:                  return ("project", p.project_id)
        parent = p.parent_task_id
    return ("root", record.task_id)       # singleton lineage; never cross-associate
```

Properties:
- A task with no lineage fields resolves to a **singleton lineage of itself**, so every
  historical task is its own project and can never be captured by a current project's
  scope.
- A child inherits the parent's `project_id`/`root_task_id`; if neither exists, it
  inherits `root_task_id = <parent root or parent task id>`.
- Cycles and unknown parents fail closed (no infinite walk, no cross-project guess).

### 5.3 Propagation (reuse existing dispatch edges)

- `worker/index.js:submit_task` input schema (`:2188`) gains optional `project_id` and
  `root_task_id`; `buildContract` (`:900`) and `recordTask` metadata (`:1269`) carry them
  through.
- `worker/index.js:dispatchApprovedChild` / `buildApprovedChildContract` (`:1044`,
  `:1055`) set the child's `project_id`/`root_task_id` from the **parent record** (and
  keep `parent_task_id`).
- `event_sync.py:submit_task` (`:184`) stores the same optional fields (it already
  accepts arbitrary extras via `setdefault`, `:251-255`); `advancement.py` mirrors the
  inheritance at `dispatch_approved_child` (`:135`/`:200`).
- If the caller supplies no lineage, a root submit gets `root_task_id = <its own
  task_id>` recorded at submit time so the lineage is stable without scanning.

### 5.4 Selection contract (Supervisor-facing)

- `list_pending_results(scope=None)`:
  - `scope=None` → **exactly today's behavior** (compatibility guarantee).
  - `scope={"project_id": "<id>"}` or `scope={"root_task_id": "<id>"}` → return only
    records whose `resolve_lineage` matches the scope; everything else is excluded.
- Worker MCP tool `list_pending_results` (`worker/index.js:2226`, `:2366`) gains the same
  optional inputs. `EventSyncRegistry.list_pending_results` (`event_sync.py:359`) gains
  the same optional argument and module-level wrapper (`:841`).
- Response includes an audit block:
  `{"scope": <echo>, "selected_lineage": <key>, "excluded_by_lineage": <count>}` so the
  Supervisor can prove the historical backlog was excluded, not hidden or deleted.

### 5.5 Smallest safe change set (for the follow-up implementation task, not applied here)

| File | Change |
| --- | --- |
| `src/personal_ai_execution/event_sync.py` | store lineage in `submit_task`; add `resolve_lineage`; optional `scope` in `list_pending_results`; propagate in `sync_terminal_result` |
| `src/personal_ai_execution/advancement.py` | inherit `project_id`/`root_task_id` alongside existing `parent_task_id` (`:200`) |
| `worker/index.js` | `submit_task` schema + `buildContract` + `recordTask` lineage; `listPendingResults`/`list_pending_results` optional scope; child inheritance in `buildApprovedChildContract` |
| `tests/` | focused lineage tests (see §7) |

RC-1/RC-2 are addressed by separate, distinctly-gated tasks (raise/scope the
concurrency group; harden `build_execution_result.py` upload). They are **not** bundled
here.

---

## 6. Compatibility impact

- **No new store, binding, secret, queue, cron, or migration.** Fields live on existing
  KV records and the existing D1 `task_dispatch_markers` table; Python records are the
  existing dicts.
- **Default behavior unchanged.** `list_pending_results()` and
  `EventSyncRegistry.list_pending_results()` return the same set/order as today when no
  scope is passed. All 827 existing tests pass without modification (verified this run:
  `827 passed`).
- **Historical backlog untouched.** Records without lineage resolve to singleton
  lineages; a scoped call simply excludes them (`excluded_by_lineage` reports the count).
  No `mark_reviewed`, no status change, no deletion.
- **Existing dispatch/idempotency semantics preserved.** `dispatchApprovedChild` and the
  D1 dispatch marker are unchanged except for additive lineage inheritance.
- **MCP surface is additive.** New optional inputs on `list_pending_results` and
  `submit_task`; no breaking schema change.

---

## 7. Tests

No test file was added in this task: the task's `expected_files` allowlist contains only
this report, and `scripts/scope_guard.py` (Gate 2) rejects any new file outside the
allowlist. The repository test suite was nevertheless run to prove the change is
non-breaking:

```
python -m pytest -q  →  827 passed
```

Implementation-ready test specification (for the follow-up task):

1. `test_lineage_resolver_self_roots_history` — a record with no lineage resolves to its
   own `root_task_id`; a historical `pending_review` singleton is excluded by any
   other project scope.
2. `test_child_inherits_project_lineage` — after `mark_reviewed(PASS,
   approved_next_task=...)`, the dispatched child carries the parent's
   `project_id`/`root_task_id` and `parent_task_id`.
3. `test_scoped_list_excludes_historical_backlog` — 100+ historical singleton
   `pending_review` records + one active-project record; scoped
   `list_pending_results(scope=...)` returns exactly the active record and reports
   `excluded_by_lineage == 101`.
4. `test_unscoped_list_is_backward_compatible` — default call returns the union exactly
   as before.
5. `test_unknown_parent_fails_closed` — unknown/cyclic `parent_task_id` resolves to self,
   never crosses projects.
6. Worker-level (Node, mocked KV/D1/fetch): `list_pending_results` scope filters the KV
   scan and preserves exactly-once child dispatch.

---

## 8. Safety / scope statement

- Changed exactly one file: `SUPERVISOR_LINEAGE_AND_STUCK_DISPATCH_DIAGNOSIS_V0.1.md`.
- **No** production deploy/write, Cloudflare/D1 canonical asset write, credential/OAuth/
  security/binding/workflow-secret change, `.github/workflows/` edit, destructive action,
  or UI automation.
- **No** `mark_reviewed` call and **no** mutation of the 101 historical `pending_review`
  tasks.
- **No** resubmission of `cf-9f9b621849e4` and **no** duplicate Decision Writer task
  (`cf-60656d12bd7a`).
- Read-only GitHub REST calls only; no credentials were read or used.

---

## 9. Verdict

| Question | Answer |
| --- | --- |
| Root cause / status of `cf-9f9b621849e4` | Task-level: `INSUFFICIENT_EVIDENCE`. Leading mechanism: `WORKFLOW_STUCK` (`QUEUED_RUN_CANCELLED_BY_CONCURRENCY`), i.e. dispatch accepted into KV but the Actions run was cancelled/never produced `execution_result-cf-9f9b621849e4`. |
| Was its dispatch actually accepted? | `INFERRED`, not directly verified. If KV `task:cf-9f9b621849e4.status == PENDING`, acceptance is implied by `toolSubmitTask` recording only on `dispatch.ok`. |
| Did a workflow ever start? | `INFERRED` **no completed/observable run**: no artifact, no bound run. Two repo runs were cancelled with zero jobs (never started). |
| Exact evidence | No repo/tag/branch hit; GitHub artifacts `total_count=0` for its name; concurrency group `cloud-agent-dispatch-main-writer` with `cancel-in-progress:false` (`agent-dispatch.yml:10-12`); zero-job cancelled runs `36250555025`, `36250558160`; registry never resolves without an artifact (`worker/index.js:1319-1379`). |
| Lineage/filter design | Optional `project_id`/`root_task_id`/`parent_task_id` with a fail-closed `resolve_lineage`, propagated through existing dispatch, and an **optional** `scope` on `list_pending_results`; default behavior unchanged. |
| Compatibility impact | Additive, no new store/migration/secret, all 827 tests pass, historical backlog untouched. |
| Tests | None added (scope allowlist is the single report); full suite run green; 6-test spec provided. |
| Deployment side effects | None (except this report). |

### Exactly one bounded next_action

```
next_action = SUPERVISOR_LINEAGE_FILTER_IMPL_V0.1
```

A single, bounded, LOW-risk follow-up task: add optional
`project_id`/`root_task_id`/`parent_task_id` lineage to the existing canonical Task
Registry (`worker/index.js` KV `TASK_REGISTRY` + `src/personal_ai_execution/event_sync.py`
`EventSyncRegistry`), inherit it through the existing `dispatch_approved_child` edge, and
add an optional lineage `scope` to `list_pending_results` (Worker MCP tool + Python),
with the six focused tests above. Default unscoped behavior must remain unchanged and no
Worker deploy is performed in that task; concurrency (RC-1) and result-build hardening
(RC-2) are separately gated follow-ups.

`final_status`: `DIAGNOSIS_COMPLETE`
