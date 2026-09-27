# PERSONAL_AI_MARK_REVIEWED_GATE_V0.2

Production-hardening of the canonical `mark_reviewed` gate so a human review
cannot bypass task completion or the validated-result requirement.

- Task id: `cf-4fb0cb4c964c`
- Risk level: `LOW`
- Canonical module: `src/personal_ai_execution/event_sync.py`
- Builds on the verified truthful terminal-state semantics in
  `src/personal_ai_execution/result_normalization.py`
  (`PASS` / `FAIL` / `BLOCKED` are authoritative and fail-closed).

## What changed

`EventSyncRegistry.mark_reviewed` now runs a fail-closed eligibility check
(`review_eligibility`) before it records a verdict. Review closure is allowed
only when **all** of the following hold:

1. The task exists (otherwise `KeyError`).
2. The verdict is one of `PASS` / `FAIL` / `BLOCKED` (otherwise `ValueError`).
3. The record has an authoritative terminal execution state:
   `terminal is True` and `normalized_status` is a terminal status.
4. A validated result is available (`result_available is True`) and the stored
   canonical `task_result` has a `task_id` equal to the task's `task_id`.
5. The validated result is terminal and agrees with the registry's normalized
   status.

A successful review preserves `verdict`, `note`, `reviewed_at`, a
`review_reason` / `review_reason_code` on the record, and an append-only
immutable review event carrying the verdict, note, timestamp, reason code,
reviewed status and matching result `task_id`. An identical repeated verdict is
idempotent; a conflicting verdict is rejected and leaves the original event
untouched.

Reusable helpers `review_eligibility(record)` and `validated_review_result(record)`
are exported from the package for callers and tests.

## Gate decision matrix

| Task state | Review outcome | Reason code |
| --- | --- | --- |
| submitted / pending / in-progress / queued / running / unknown | rejected | `NON_TERMINAL` |
| terminal but non-terminal normalized status | rejected | `NON_TERMINAL_STATUS` |
| terminal but no result available | rejected | `RESULT_UNAVAILABLE` |
| terminal but no stored `task_result` | rejected | `MISSING_RESULT` |
| stored result `task_id` != task `task_id` | rejected | `RESULT_TASK_ID_MISMATCH` |
| stored result status not terminal | rejected | `NON_TERMINAL_RESULT` |
| stored result status != registry status | rejected | `RESULT_STATUS_MISMATCH` |
| unknown task | rejected | `KeyError` |
| invalid verdict | rejected | `ValueError` |
| terminal `PASS` / `FAIL` / `BLOCKED` + validated matching result | accepted for any `PASS` / `FAIL` / `BLOCKED` verdict | `ELIGIBLE` |

## Idempotency / conflict

| Retry | Outcome |
| --- | --- |
| identical verdict | `idempotent = True`, no new event |
| conflicting verdict | `ValueError`, original verdict/event preserved |

## Scope / no weakening

- No change to `.github/workflows/`, secret/token/credential paths, authentication
  or any other gate.
- `list_pending_results`, `sync_terminal_result`, reconciliation and normalization
  contracts are unchanged.
- `worker/index.js` was intentionally **not** modified: its legacy KV records do
  not persist `terminal`, `normalized_status`, or `evidence.task_result`, and the
  repository has no JavaScript test harness, so changing the deployed MCP gate
  without execution evidence would introduce unverified production risk.

## Tests

New focused suite: `tests/test_mark_reviewed_gate.py` (28 tests) covering every
rejection path, all verdicts on eligible terminal tasks, audit reason
preservation, idempotency, conflict fail-closed, non-mutation on rejection, and
the module-level default-registry flow.

Full regression suite:

```
380 passed in 57.24s
```

Command: `python -m pytest -q`

## Changed files

- `src/personal_ai_execution/event_sync.py`
- `src/personal_ai_execution/__init__.py`
- `tests/test_mark_reviewed_gate.py`
- `MARK_REVIEWED_GATE_V0.2.md`

## Verdict: PASS

Review closure can no longer occur for submitted / pending / in-progress /
unknown / missing-result / mismatched-result / non-terminal tasks; only eligible
terminal validated tasks can be reviewed, with the verdict, note, timestamp and
auditable reason preserved.
