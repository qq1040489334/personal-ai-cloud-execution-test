# PERSONAL_AI_DECISION_INGESTION_CONTRACT_V0.1

Read-only DECISION normalization/ingestion contract: one canonical DECISION
record shape assembled from the decision evidence the platform already
produces, with **no production write, no Worker change, no credential change,
no second state store and no PersonOS resurrection**.

- Task id: `cf-b9bacc9718ea`
- Risk level: `LOW`
- Canonical Python module: `src/personal_ai_execution/decision_contract.py`
- Focused tests: `tests/test_decision_contract.py`

## 1. Canonical DECISION record shape

`normalize_decision(record)` maps a Task Registry record, an append-only review
event, a dispatch marker, an ASSET_PROVENANCE_V0.2 provenance record -- or any
combined mapping -- into this single shape:

| Field | Meaning | Required |
| --- | --- | --- |
| `decision_id` | stable decision identity (defaults to `task_id`) | no |
| `task_id` | the task the decision belongs to | no |
| `review_verdict` | the human review verdict (`PASS` / `FAIL` / `BLOCKED`) | yes |
| `dispatch_outcome` | exactly-once dispatch-marker outcome (`PENDING` / `DISPATCHED` / `FAILED`) | yes |
| `promotion_decision` | provenance promotion decision (e.g. `PROMOTE`) | yes |
| `promotion_event` | append-only promotion event id | no |
| `user_choice` | explicit human choice attached to the decision | yes |
| `user_outcome` | observed outcome of that choice | yes |
| `decided_at` | when the decision was recorded | no |

Every field is resolved through the alias table below; the first meaningful
alias wins, so historical records that are flat, nested or legacy-named are read
without inventing duplicate metadata.

## 2. Field alias / mapping from existing records

| Canonical field | Reused source | Aliases |
| --- | --- | --- |
| `review_verdict` | Task Registry `review_verdict`, review event `verdict` | `review_verdict`, `review.verdict`, `review_event.verdict`, `verdict` |
| `dispatch_outcome` | Python `review_dispatch.dispatch_state`, Worker `task_dispatch_markers.dispatch_state` | `review_dispatch.dispatch_state`, `review_dispatch.state`, `task_dispatch_marker.dispatch_state`, `dispatch_marker.dispatch_state`, `dispatch_outcome`, `dispatch.state`, `dispatch_state` |
| `promotion_decision` | ASSET_PROVENANCE_V0.2 `promotion.decision` | `promotion_decision`, `promotion.decision`, `provenance.promotion.decision`, plus the provenance aliases (`decision`, ...) |
| `promotion_event` | ASSET_PROVENANCE_V0.2 `promotion.event_id` | `promotion_event`, `promotion.event_id`, `provenance.promotion.event_id`, plus the provenance aliases |
| `user_choice` | explicit human input | `user_choice`, `user.choice`, `decision.user_choice`, `reviewer_choice` |
| `user_outcome` | explicit human input | `user_outcome`, `user.outcome`, `decision.user_outcome`, `reviewer_outcome` |
| `decided_at` | review / dispatch / promotion timestamps | `decided_at`, `decision.decided_at`, `reviewed_at`, `dispatch.dispatched_at`, `promotion.decided_at` |

The provenance aliases are imported **directly** from
`PROVENANCE_FIELD_ALIASES` in
`src/personal_ai_execution/provenance_contract.py` and the dispatch vocabulary
from `src/personal_ai_execution/advancement.py`; a test asserts the reuse so the
contract can never silently diverge from the existing vocabulary.

## 3. Fail-closed decision matrix

| Scenario | Required fields | Status | Verified |
| --- | --- | --- | --- |
| complete decision evidence | all present | `VERIFIED` | yes |
| review verdict never recorded | `review_verdict` absent | `INCOMPLETE` | no |
| dispatch outcome never recorded | `dispatch_outcome` absent | `INCOMPLETE` | no |
| promotion decision never recorded | `promotion_decision` absent | `INCOMPLETE` | no |
| user choice never captured | `user_choice` absent | `INCOMPLETE` | no |
| user outcome never captured | `user_outcome` absent | `INCOMPLETE` | no |
| unrecognized verdict or dispatch value | present but not a known vocabulary value | `INCOMPLETE` | no |

Rules:

- A record missing any required field is `INCOMPLETE` and is **never**
  `VERIFIED`; the exact missing field list is returned in `missing`.
- An unrecognized `review_verdict` (not one of `REVIEW_VERDICTS`) or
  `dispatch_outcome` (not one of `DISPATCH_STATES`) is reported in `invalid` and
  is never `VERIFIED`.
- No metadata is fabricated: only fields actually present are echoed back, and
  the input mapping is never mutated.
- The contract only reads and normalizes; it writes no production state and does
  not call `mark_reviewed`, `submit_task`, dispatch a workflow or touch D1.

## 4. Return value

`normalize_decision` returns:

```
{
  "contract": "PERSONAL_AI_DECISION_INGESTION_V0.1",
  "status":   "VERIFIED" | "INCOMPLETE",
  "complete": bool,
  "verified": bool,
  "missing":  [ ...exact missing fields... ],
  "invalid":  [ ...unrecognized fields... ],
  "fields":   { ...resolved raw values... },
  "record":   { ...canonical DECISION shape... },
  "reason":   "human readable explanation",
}
```

`build_decision(...)` builds a canonical, structurally complete input record
using the existing nested shapes (`review_dispatch`, `promotion`) that
round-trips through `normalize_decision` to `VERIFIED`.

## 5. What is deliberately not changed

- No production write, deploy or Cloudflare canonical / D1 mutation.
- No credential, secret or OAuth change.
- No `.github/workflows/` change and no workflow dispatch.
- No `mark_reviewed` call and no second state store: the contract is read-only
  and lives entirely under `src/personal_ai_execution/`.
- No `worker/index.js` change; the Worker dispatch-marker fields are consumed
  as-is.

## 6. Tests and evidence

Focused suite: `tests/test_decision_contract.py` covering:

- importability and the documented fail-closed vocabulary;
- complete record -> `VERIFIED`;
- each required field missing -> `INCOMPLETE`, never verified, exact list;
- choice-missing and outcome-missing records;
- blank strings and unrecognized verdict / dispatch values;
- flat legacy aliases and nested existing record shapes;
- the real Python registry review/dispatch record normalizing end to end;
- alias-table reuse of the provenance vocabulary and Worker dispatch-marker
  columns against `worker/migrations/0002_dispatch_idempotency.sql`.

Command: `python -m pytest -q`

## 7. Changed files

- `src/personal_ai_execution/decision_contract.py` (new)
- `tests/test_decision_contract.py` (new)
- `DECISION_INGESTION_CONTRACT_V0.1.md` (new)

## Verdict: PASS

A read-only, fail-closed DECISION ingestion contract now exists. Complete
decision evidence normalizes to one canonical `VERIFIED` DECISION record, and
incomplete evidence is explicitly `INCOMPLETE` with the exact missing fields and
is never reported verified.
