# AGENT_DISPATCH_CONTRACT_READONLY_MODE_FIX_V0.1

- goal: `AGENT_DISPATCH_CONTRACT_FIX_RELEASE_V0.2`
- task_id: `cf-182e1d4ae79a`
- risk_level: `LOW`
- mode: **release of the locally accepted `AGENT_DISPATCH_CONTRACT_READONLY_MODE_FIX_V0.1`
  contract fix, documented as the canonical source of truth for the Cloud Agent
  dispatch contract, with no workflow, Canonical, or production-Worker mutation**
- business `final_status`: `READONLY_MODE_FIX_RELEASED`
- workflow status: separate from the business outcome above
- evidence policy: every claim is tagged `OBSERVED` (directly read this run) or
  `INFERRED` (reasoned from repository evidence). Retrieval limits are stated.

---

## 0. Executive summary

1. The Cloud Agent dispatch contract was ambiguous about **which execution modes a
   task may declare** and about what the surrounding Gates (`scripts/task_contract.py`,
   `scripts/scope_guard.py`) require for each mode. The accepted
   `AGENT_DISPATCH_CONTRACT_READONLY_MODE_FIX_V0.1` fix clarifies the contract into a
   **readonly / write dual-mode** model. `OBSERVED`.
2. **Readonly mode** is a task that inspects or reports and changes no repository
   files: it is valid with `expected_files = []`. **Write mode** is a task that
   changes repository files and must therefore carry a non-empty `expected_files`
   allowlist; every changed file must match that allowlist. `OBSERVED` against
   `scripts/task_contract.py:37-48` and `scripts/scope_guard.py:64-66`.
3. The original release documented the fix and recorded the exact behavior the two
   Gates must preserve. The **Gate adaptation is now implemented** in
   `scripts/task_contract.py` and `scripts/scope_guard.py` by the bounded follow-up
   `AGENT_DISPATCH_CONTRACT_READONLY_MODE_GATE_ADAPTATION_V0.1`, so the dual-mode
   contract is live rather than documented-only. `OBSERVED`.
4. `task_contract.py` and `scope_guard.py` now accept an empty `expected_files` list
   **only** for an explicitly readonly task (`mode: readonly`), while write mode —
   and a missing `mode`, which defaults to **write** — still requires a non-empty
   allowlist. The per-entry forbidden/unsafe checks remain in force in both modes and
   an empty readonly allowlist matches no path, so any change fails closed. `OBSERVED`.
5. No Canonical mutation, no production Worker mutation, no secret/token/credential
   change, no binding or schema change, and no `.github/workflows/` edit occurred. `OBSERVED`.

---

## 1. Scope

**In scope (this task, LOW risk).**

- Release the already locally accepted `AGENT_DISPATCH_CONTRACT_READONLY_MODE_FIX_V0.1`
  contract into the repository as the canonical dispatch-contract document.
- State the readonly/write dual-mode contract and the exact Gate behavior each mode
  must preserve.
- Record the release validation and evidence so the behavior cannot silently regress.
- Add focused pytest coverage that pins the dual-mode contract.

**Out of scope (hard rules).**

- Editing `.github/workflows/` (forbidden by the task allowlist and
  `scripts/scope_guard.py`).
- Editing Personal AI Canonical records, the production Worker (`worker/index.js`),
  secrets, bindings, or schemas.
- Broadening the adaptation beyond the readonly/write mode decision: the forbidden
  prefix/substring sets, unsafe-path checks, and deletion prohibition are unchanged.
- Editing `.github/workflows/` — the Gate adaptation is confined to the two Gate
  scripts and their focused tests (§4).

---

## 2. Contract definition (readonly / write dual mode)

The Cloud Agent dispatch contract has exactly two execution modes. A task is
interpreted as one of them by its `expected_files` declaration.

| Aspect | readonly mode | write mode |
| --- | --- | --- |
| `expected_files` | **may be `[]` (empty)** | **must be a non-empty list** |
| Intent | inspect / report / plan only | change repository files |
| Gate 1 (`task_contract.py`) | accept an empty list for readonly tasks | require a non-empty list |
| Gate 2 (`scope_guard.py`) | allow **zero** changed files; block any change | require every changed file to match the allowlist |
| Deletions | none | none (deletions remain forbidden) |
| Forbidden targets | `.github/workflows/`, secret/token/credential/.env/.pem/.key | same |

### 2.1 readonly mode

- A readonly task declares `expected_files = []`.
- It is valid when and only when the task is explicitly readonly. The empty
  allowlist must never act as a wildcard that permits arbitrary writes.
- The scope guard must still fail closed on any change that appears during a readonly
  run: an empty allowlist matches no path, so every changed or new file is a
  violation.

### 2.2 write mode

- A write task declares a non-empty `expected_files` allowlist.
- Every changed or newly created file must match the allowlist.
- Readonly is the only mode allowed to leave the allowlist empty; an empty list on a
  write-classified task is invalid.

### 2.3 Mode classification

A task's mode is determined by its `expected_files` declaration together with an
explicit mode signal (for example a `mode: readonly` contract field):

- explicit `readonly` (or an empty `expected_files` on an explicitly readonly task)
  → readonly mode;
- a non-empty `expected_files` allowlist → write mode;
- no explicit readonly signal and an empty `expected_files` → invalid (fail closed),
  because an unlabeled empty allowlist would be an unbounded write grant.

---

## 3. Gate behavior that must be preserved

### 3.1 Gate 1 — `scripts/task_contract.py` (task contract validation)

- The six required fields (`task_id`, `goal`, `instructions`, `risk_level`,
  `expected_files`, `acceptance`) remain mandatory. `OBSERVED` `:13`.
- `instructions` and `acceptance` must each remain a non-empty list. `OBSERVED` `:50-53`.
- `risk_level` must remain in `{LOW, MEDIUM}`. `OBSERVED` `:12`, `:33-35`.
- For **write** mode, `expected_files` must remain a non-empty list and every entry
  must pass the existing forbidden-prefix / forbidden-substring / unsafe-path checks.
  `OBSERVED` `:37-48`.
- For **readonly** mode, an empty `expected_files` list is accepted. The fix is
  additive: no forbidden or unsafe entry is ever accepted merely because the list is
  empty.

### 3.2 Gate 2 — `scripts/scope_guard.py` (modification scope enforcement)

- The guard resolves the allowlist through `resolve_allowlist`, which honors an empty
  allowlist **only** for `mode: readonly`; write mode (and a missing mode) raises
  `expected_files must be a non-empty list for write mode`. `OBSERVED`.
- For a readonly contract the empty allowlist is honored: the guard runs, sees zero
  allowlisted patterns, and passes only when the diff contains **no changed files**;
  any changed or new file is reported as
  `modification outside task allowlist` / `new file outside task allowlist`.
- Write-mode behavior is unchanged: a non-empty allowlist is required and every
  changed file must match it.
- Deletions and forbidden/unsafe paths remain violations in both modes.
  `OBSERVED` `:89-107`.

### 3.3 Release validation

- `release task contract validation PASS` — the release task contract validates under
  the existing Gate 1 rules (non-empty `expected_files`, LOW risk, non-empty
  instructions and acceptance). `OBSERVED`.
- `readonly/write contract 行为保持测试通过` — the pinned pytest coverage in §5 proves
  the dual-mode behavior. `OBSERVED`.

---

## 4. Gate adaptation for full readonly support (implemented)

The dual-mode contract above is the accepted fix. The bounded follow-up
`AGENT_DISPATCH_CONTRACT_READONLY_MODE_GATE_ADAPTATION_V0.1` implements the
fail-closed adaptation:

| File | Required change | Status |
| --- | --- | --- |
| `scripts/task_contract.py` | `task_mode()` resolves an explicit mode with missing/empty defaulting to write; an empty `expected_files` is accepted **only** for readonly mode, while write mode keeps the non-empty requirement. Per-entry forbidden/unsafe checks are never skipped when entries are present. | Implemented |
| `scripts/scope_guard.py` | `task_mode()` / `resolve_allowlist()` accept an empty allowlist for an explicitly readonly contract and otherwise require a non-empty one; the diff scan then runs with zero matched patterns so any change fails closed. | Implemented |

Both changes remain inside the non-workflow Gate scripts: they cannot relax the
`.github/workflows/` prohibition, the forbidden-target checks, or the deletion
prohibition. Readonly is never an unbounded write grant.

---

## 5. Acceptance tests (pinned)

The following behavior is pinned by pytest so the contract cannot silently regress.
The tests load and execute the **production Gate modules** (`scripts/task_contract.py`
in `tests/test_task_contract.py`, `scripts/scope_guard.py` in
`tests/test_scope_guard.py`) and additionally drive the scope guard end-to-end inside
scratch git repositories, so they fail if the Gates diverge from the released contract.

1. Gate 1 requires all six fields and rejects non-`LOW`/`MEDIUM` risk.
2. Gate 1 readonly mode accepts `expected_files = []` (including mode aliases).
3. Gate 1 write mode — and a missing mode, which defaults to write — rejects an empty
   `expected_files`.
4. Gate 1 still rejects `.github/workflows/`, secret-class, unsafe absolute, and `..`
   expected files in both modes.
5. Gate 2 readonly mode with an empty allowlist passes only when no file changes, and
   blocks any changed or newly created file (readonly is not an unbounded write grant).
6. Gate 2 write mode (and a missing mode) rejects an empty allowlist and blocks
   modifications outside the non-empty allowlist.
7. The forbidden-prefix and forbidden-substring sets, and the deletion prohibition,
   are preserved by both Gates.

---

## 6. Safety / scope statement

- Gate adaptation released **only** in `scripts/task_contract.py`,
  `scripts/scope_guard.py`, their focused tests (`tests/test_task_contract.py`,
  `tests/test_scope_guard.py`), and this document — exactly the task allowlist.
- **No** `.github/workflows/` edit; **no** Personal AI Canonical mutation; **no**
  production Worker change; **no** secret/token/credential change; **no** binding or
  schema change; **no** deletion.
- The readonly/write dual-mode constraint is preserved: readonly allows
  `expected_files = []`; write still requires a changed-files allowlist.
- `release task contract validation PASS`; the release contract itself satisfies the
  existing Gate 1 rules.

---

## 7. Verdict

| Question | Answer |
| --- | --- |
| Released fix | `AGENT_DISPATCH_CONTRACT_READONLY_MODE_FIX_V0.1` |
| Gate adaptation | `AGENT_DISPATCH_CONTRACT_READONLY_MODE_GATE_ADAPTATION_V0.1` — implemented in `scripts/task_contract.py` / `scripts/scope_guard.py`. `OBSERVED` |
| Dual mode | readonly allows `expected_files = []`; write requires a non-empty allowlist. `OBSERVED` |
| Gate 1 requirement | Empty allowlist accepted only for explicit readonly (`mode: readonly`); write and missing mode require a non-empty allowlist. `OBSERVED` |
| Gate 2 requirement | Empty readonly allowlist passes only with no changes and fails closed on any change; write and missing mode require and enforce a non-empty allowlist. `OBSERVED` |
| Canonical mutation | None. |
| Production Worker change | None. |
| Workflow mutation | None. |
| Tests | Focused dual-mode contract coverage in `tests/test_task_contract.py` and `tests/test_scope_guard.py`. |
| Deployment / production side effects | None. |

### Exactly one bounded next_action

```
next_action = NONE
```

The readonly/write Gate adaptation is complete: both Gates are mode-aware, fail
closed on any change under an empty readonly allowlist, and keep the non-empty
changed-files allowlist for write mode.

`final_status`: `READONLY_MODE_GATE_ADAPTATION_RELEASED`

---

## 8. Addendum — submit_task mode passthrough adapter (V0.1)

- goal: `CLOUD_AGENT_SUBMIT_TASK_MODE_PASSTHROUGH_ADAPTER_V0.1`
- task_id: `cf-e38d97dd7f75`
- risk_level: `LOW`
- business `final_status`: `SUBMIT_TASK_MODE_PASSTHROUGH_ADAPTER_RELEASED`
- workflow status: separate from the business outcome above

The released Gate mode resolver above already consumes a `mode` field. This
bounded, non-production follow-up carries that field from the MCP
`submit_task` surface through the `repository_dispatch` task payload into the
Gate resolver. `OBSERVED`.

### 8.1 Behavior

- `worker/index.js` `buildContract()` now resolves a `mode` argument with
  `resolveMode()`: `readonly` / `read_only` / `read-only` canonicalize to
  `readonly`; `write` / `readwrite` / `read_write` / `read-write` canonicalize
  to `write`; a missing, `null`, or empty mode defaults to **write**. Any other
  value resolves to `null`, is written verbatim into the contract, and
  `validateContract()` fails closed with `mode not acceptable`. `OBSERVED`.
- The resolved mode is emitted on the task contract as `mode`, so it is carried
  in the `client_payload.task` of the outbound `repository_dispatch` request and
  persisted alongside `dispatch_contract`. `OBSERVED`.
- A `readonly` submit with no explicit `expected_files` defaults to an empty
  allowlist, so readonly is never an unbounded write grant; write (including a
  missing mode) keeps the backwards-compatible default allowlist. `OBSERVED`.
- The approved-child dispatch path (`buildApprovedChildContract`) passes
  `approvedNextTask.mode` through the same `buildContract()` resolver, so the
  same bounded mode rules apply to an explicitly approved child. `OBSERVED`.

### 8.2 Focused tests

`tests/test_submit_task_mode_passthrough.py` executes the production Worker
source under Node, captures the dispatched `client_payload.task`, and runs the
**real** Gate 1 evaluator (`scripts/task_contract.py`) against it. It pins:
`mode=readonly` reaches the Gate, `mode=write` reaches the Gate, a missing mode
is dispatched as `write`, and an unknown mode is rejected before any dispatch.
`OBSERVED`.

### 8.3 Safety / scope statement

- Changed paths: `worker/index.js`, `tests/test_submit_task_mode_passthrough.py`,
  and this document — exactly within the task allowlist.
- **No** `.github/workflows/` edit; **no** Personal AI Canonical mutation; **no**
  production Worker deployment; **no** secret/token/credential/OAuth/permission/
  binding/schema change; **no** deletion.
- The existing `expected_files` and changed-files safety behavior is unchanged:
  the Gate still enforces forbidden/unsafe checks and the changed-files
  allowlist in both modes.

### Bounded next_action

```
next_action = NONE
```

The submit_task mode passthrough is complete: the submit surface, dispatched
task payload, and Gate mode resolver agree on the readonly/write contract, and
unknown modes fail closed.
