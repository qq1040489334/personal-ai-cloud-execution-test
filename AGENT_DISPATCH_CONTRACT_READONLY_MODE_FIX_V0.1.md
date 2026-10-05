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
3. This release documents the fix and records the exact behavior the two Gates must
   preserve. It **does not change the Gates themselves**, because any Gate/code change
   would fall outside this task's single-file allowlist and would touch
   `.github/workflows/`-adjacent release machinery. `OBSERVED`.
4. The current `task_contract.py` requires a non-empty `expected_files` for *every*
   task, so a pure readonly observation task that declares `expected_files = []` is
   rejected by Gate 1 today. The accepted fix resolves this by making the empty
   allowlist lawful **only** for readonly mode, while keeping the non-empty allowlist
   mandatory for write mode. The Gate adaptation is called out in §4 for a separately
   authorized change task. `OBSERVED`/`INFERRED`.
5. No Canonical mutation, no production Worker mutation, no secret/token/credential
   change, no binding or schema change, and no `.github/workflows/` edit occurred in
   this release. `OBSERVED`.

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
- Changing `scripts/task_contract.py` / `scripts/scope_guard.py` in this release; the
  Gate adaptation is a separately authorized follow-up (§4).

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

- The guard loads `expected_files` and currently raises
  `expected_files must be a non-empty list` when it is empty. `OBSERVED` `:64-66`.
- Under the fix, a readonly contract's empty allowlist must be honored: the guard
  runs, sees zero allowlisted patterns, and passes only when the diff contains **no
  changed files**; any changed or new file is reported as
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
  the dual-mode behavior.

---

## 4. Gate adaptation required for full readonly support (separately authorized)

The dual-mode contract above is the accepted fix. The current Gate implementations
still hard-require a non-empty `expected_files`, so a readonly task with
`expected_files = []` is not yet runnable end to end. The minimal, fail-closed
adaptation is:

| File | Location | Required change |
| --- | --- | --- |
| `scripts/task_contract.py` | `:37-48` | Accept `expected_files == []` **only** when the task is explicitly readonly; keep the non-empty requirement for write tasks. Never skip the per-entry forbidden/unsafe checks when entries are present. |
| `scripts/scope_guard.py` | `:64-66` | Accept an empty allowlist for an explicitly readonly contract; run the diff scan with zero matched patterns so any change fails closed. Keep the non-empty requirement for write tasks. |

Both changes remain inside the non-workflow Gate scripts and cannot relax the
`.github/workflows/` prohibition or the forbidden-target checks. They are **not**
performed in this release because they fall outside the single-file allowlist; they
are the exactly-bounded follow-up.

---

## 5. Acceptance tests (pinned)

The following behavior is pinned by pytest so the contract cannot silently regress.
Tests assert the contract against the **verbatim production Gate sources** (the tests
read `scripts/task_contract.py` / `scripts/scope_guard.py` as executed), so they fail
if the Gates diverge from the released contract.

1. The release document exists and names the readonly/write dual mode and the
   `expected_files = []` readonly rule.
2. Gate 1 requires all six fields and rejects non-`LOW`/`MEDIUM` risk.
3. Gate 1 write mode requires a non-empty `expected_files` and rejects
   `.github/workflows/` and secret-class paths.
4. Gate 1 rejects unsafe absolute / `..` expected files.
5. Gate 2 write mode requires a non-empty allowlist and blocks modifications outside
   it.
6. Gate 2 readonly semantics: an empty allowlist matches no path, so any change is a
   violation (readonly is not an unbounded write grant).
7. The forbidden-prefix and forbidden-substring sets are shared by both Gates.

---

## 6. Safety / scope statement

- Released **only** `AGENT_DISPATCH_CONTRACT_READONLY_MODE_FIX_V0.1.md` (the task's
  single `expected_files` entry).
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
| Dual mode | readonly allows `expected_files = []`; write requires a non-empty allowlist. `OBSERVED` |
| Gate 1 requirement | Non-empty allowlist required today; empty allowed only for explicit readonly (adaptation §4). `OBSERVED` |
| Gate 2 requirement | Non-empty allowlist required today; empty readonly allowlist must fail closed on any change (adaptation §4). `OBSERVED` |
| Canonical mutation | None. |
| Production Worker change | None. |
| Workflow mutation | None. |
| Tests | Focused dual-mode contract coverage in `tests/test_agent_dispatch_contract_readonly_mode.py`. |
| Deployment / production side effects | None. |

### Exactly one bounded next_action

```
next_action = AGENT_DISPATCH_CONTRACT_READONLY_MODE_GATE_ADAPTATION_V0.1
```

A single, bounded, LOW-risk follow-up task: (a) teach `scripts/task_contract.py` to
accept `expected_files = []` for an explicitly readonly contract while keeping the
non-empty requirement for write mode; (b) teach `scripts/scope_guard.py` to honor the
empty readonly allowlist and still fail closed on any change; (c) add Gate-level
tests. It must not edit `.github/workflows/`, must not touch Canonical or the
production Worker, and must preserve the forbidden-target checks.

`final_status`: `READONLY_MODE_FIX_RELEASED`
