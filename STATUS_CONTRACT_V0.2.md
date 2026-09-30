# PERSONAL_AI_STATUS_CONTRACT_V0.2

One authoritative production task-status contract shared across GitHub workflow
truth, Python result normalization, Worker responses, EVENT_SYNC and the Task
Registry.

- Task id: `cf-70c12f3174b1`
- Risk level: `LOW`
- Canonical Python module: `src/personal_ai_execution/status_contract.py`
- Normative terminal mapping: `src/personal_ai_execution/result_normalization.py`
- Worker semantics: `worker/index.js`

## 1. Execution status vs. review verdict

Two concepts are deliberately never conflated:

| Concept | Owner | Values | Field |
| --- | --- | --- | --- |
| Execution status | workflow / normalization / EVENT_SYNC | `PENDING`, `PASS`, `FAIL`, `BLOCKED` | `status`, `normalized_status`, `execution_status` |
| Review verdict | human (`mark_reviewed`) | `PASS`, `FAIL`, `BLOCKED` | `review_verdict` |

`PENDING` is the only non-terminal execution status. `PASS` / `FAIL` /
`BLOCKED` are terminal. `mark_reviewed` records a verdict on the separate
`review_verdict` field and never rewrites the execution status.

## 2. Lifecycle

```
submitted / queued / in-progress / running / unknown
        │  (advisory registry status -> PENDING, never success)
        ▼
     PENDING ── workflow conclusion ──▶ PASS | FAIL | BLOCKED (terminal)
                                             │
                                             ▼
                              review verdict (separate field)
```

Advisory lifecycle values (`submitted`, `pending`, `queued`, `created`,
`dispatched`, `started`, `in_progress`, `running`, `unknown`) normalize to
`PENDING`. Unknown work is never promoted to success.

## 3. Authoritative workflow-conclusion mapping

The GitHub Actions workflow conclusion is the execution terminal truth when
available. Artifact content, self-reported status and commit presence can never
override it.

| Workflow conclusion | Execution status | Terminal | Authoritative |
| --- | --- | --- | --- |
| `success` (+ matching result) | `PASS` | yes | yes |
| `success` but expected files missing | `FAIL` | yes | yes |
| `success` but result self-reports failure | `FAIL` | yes | yes |
| `failure`, `startup_failure`, `error` | `FAIL` | yes | yes |
| `cancelled`, `canceled` | `BLOCKED` | yes | yes |
| `timed_out` | `BLOCKED` | yes | yes |
| `action_required`, `stale`, `neutral`, `skipped` | `BLOCKED` | yes | yes |
| unrecognized / missing conclusion | `BLOCKED` | yes | yes (fail-closed) |
| no conclusion, task still in flight | `PENDING` | no | no |

The same table is exported as `WORKFLOW_CONCLUSION_TO_STATUS` in
`status_contract.py` and as `WORKFLOW_CONCLUSION_STATUS` in `worker/index.js`;
a regression test asserts the two dictionaries are identical.

## 4. `get_task_result` agreement

`get_task_result` always reports the workflow-authoritative execution status as
its top-level `status` / `execution_status`; the raw self-report is exposed only
as `execution_result_status`. For a `success` / `failure` / `cancelled`
conclusion the overall execution status can never disagree with the conclusion.

Reading a result with an authoritative conclusion also writes the terminal
execution state back onto the Task Registry record, so the registry can never
stay stale as `submitted` after a terminal workflow result has been observed.
A task with no authoritative conclusion yet is reported as non-terminal
`PENDING`, even when a self-reported artifact exists.

## 5. Worker-facing semantics

`worker/index.js` implements the same contract:

| Worker surface | Behaviour |
| --- | --- |
| `verifiedResultStatus(raw, run)` | `PENDING` until `run.status == "completed"`; otherwise canonical `PASS` / `FAIL` / `BLOCKED` for the conclusion. |
| `buildTaskResult(...)` | emits `status`, `normalized_status`, `execution_status`, `terminal`, `workflow_conclusion` and a separate `review_verdict`. |
| `list_pending_results` | computes the canonical status, then persists the terminal execution state (`persistTerminalExecution`) so the KV registry is not stale. |
| `get_task_result` | persists terminal state and returns the review verdict on a separate field. |
| `mark_reviewed` | fail-closed: rejects non-terminal or result-less tasks; stores `review_verdict` without touching the execution status. |
| `submit_task` | records the task as canonical `PENDING` with `result_available: false`, `reviewed: false`. |

## 6. Historical reconciliation (fail-closed)

`reconcile_historical_tasks` classifies pre-EVENT_SYNC records without deleting
any audit data:

- authoritative conclusion -> `completed_with_result` / `failed_with_result` /
  `blocked_awaiting_inspection`;
- explicitly discovered result without a conclusion -> terminal discovery;
- **ambiguous stored self-report** (a legacy `execution_result.json` with no
  authoritative workflow conclusion) -> `blocked_awaiting_inspection` with
  `ambiguous = True`, `terminal = False`, and no promotion to success;
- result-less blocked / stale / fresh records -> inspection / orphan /
  in-progress, never success.

Reconciliation stays idempotent and preserves review events, evidence and
commits.

## 7. Status matrix

| Scenario | Workflow conclusion | Execution status | Terminal | Review verdict separate |
| --- | --- | --- | --- | --- |
| workflow success + matching result | `success` | `PASS` | yes | yes |
| workflow failure (any self-report) | `failure` | `FAIL` | yes | yes |
| workflow cancelled / canceled | `cancelled` | `BLOCKED` | yes | yes |
| timed_out / action_required / stale / neutral / skipped | `timed_out` | `BLOCKED` | yes | yes |
| success conclusion but expected files missing | `success` | `FAIL` | yes | yes |
| unknown / unrecognized conclusion | `unrecognized` | `BLOCKED` | yes | yes |
| no conclusion recorded (in flight) | `None` | `PENDING` | no | yes |

## 8. Tests

- `tests/test_status_contract_v0_2.py` (23 tests): conclusion mapping, lifecycle,
  status matrix, registry write-back, execution/review separation, Worker source
  contract, Worker↔Python exact mapping equality, and real Node execution of the
  Worker status function, review gate and write-back.
- `tests/test_task_registry_reconciliation.py`: fail-closed ambiguous
  self-report coverage.
- Full regression suite: `790 passed`.

Command: `python -m pytest -q`

## 9. Changed files

- `src/personal_ai_execution/status_contract.py` (new)
- `src/personal_ai_execution/event_sync.py`
- `src/personal_ai_execution/reconciliation.py`
- `src/personal_ai_execution/__init__.py`
- `worker/index.js`
- `tests/test_status_contract_v0_2.py` (new)
- `tests/test_task_registry_reconciliation.py`
- `STATUS_CONTRACT_V0.2.md`

## 10. Scope / no weakening

- No change to `.github/workflows/`, secret/token/credential paths, or the
  authentication / scope / expected-files gates.
- The hardened V0.2 `mark_reviewed` gate (Python) is preserved and mirrored in
  the Worker.
- Reconciliation remains additive and idempotent; no history is deleted.

## 11. Commit / evidence

- Implementation commit: `0c3ac20392bf86bfecb68cbaadd77a7a2a398665`
- Verification: `python -m pytest -q` -> `790 passed`
- Status matrix: sections 3 and 7 above.

## Verdict: PASS

There is now one documented canonical status contract, implemented consistently
in Python and the Worker, where success / failure / cancelled conclusions cannot
disagree with `get_task_result`, terminal execution state is written back to the
Task Registry, execution status and review verdict stay separate, and historical
reconciliation is fail-closed for ambiguous records.
