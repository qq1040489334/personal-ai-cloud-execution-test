# HUASHU_ORANGE_BOOK_PERSONAL_AI_READONLY_EVALUATION_V1

- **Task**: `cf-ba136532196a`
- **Project**: `huashu-orange-book-evaluation`
- **Mode**: cloud read-only audit. The only repository outputs are this file and `HUASHU_EVIDENCE_INDEX_V1.json`.
- **Risk**: `LOW`
- **Audit time**: 2026-10-21T08:12:51Z (UTC)
- **Repository checkout**: `749f7e9831c9aa0ab5815fe14089fc28a8e6a742`
- **Audit execution status (workflow/agent)**: `success` — kept separate from the business result below.
- **Business `final_status`**: `PARTIAL`
- **Deliverable status**: `PASS` — both required files were produced and checked.
- **Production / Canonical write**: **NONE**
- **Third-party Skill installation**: **NONE**

> Evidence labels used throughout: **FACT** = directly observed in this run (HTTP response, file, command output, test result); **INFERENCE** = reasoned from facts, not a vendor guarantee; **AUTHOR_CLAIM** = the book/page author's self-report, not independently reproduced here; **UNKNOWN** = not observable or not tested in this environment. A green repository test is **not** evidence that an external runtime works.

---

## 0. Verdict at a glance

The four requested sources were read successfully. The repository has substantial reusable engineering — fail-closed task contracts, workflow-authoritative status normalization, advisory review, human approval, provenance, child dispatch, and a large regression suite — but it does **not** have an independent skill-scoring judge, Codex context/quota telemetry, or a reachable Hermes runtime.

| Area | Status | Meaning in this audit |
| --- | --- | --- |
| Source retrieval and version capture | **PASS** | All four URLs returned HTTP 200; page hashes, commit, byte count and access time recorded. |
| Current repository capability inventory | **PASS** | Directly read source, tests and baseline metadata; `1753 passed, 1 skipped`. |
| Harness Engineering reuse | **PARTIAL** | Five-layer checklist is conceptually reusable; the source page is metadata/table-of-contents only, not an implementation. |
| Darwin independent scoring reuse | **PARTIAL** | Rubric arithmetic and paired-majority decision are deterministic and reusable; blind judge execution and skill test prompts are missing. |
| Regression-test reuse | **PASS** | Existing pytest suite is real and green; no skill-specific evaluation set exists. |
| Codex context and quota reuse | **UNKNOWN** | No authenticated Codex run, no token/quota telemetry, and no `AGENTS.md` in this repository. Exact quota/context figures were not extracted from the source page. |
| Hermes overlap assessment | **PARTIAL** | Architectural overlap is real and the client code exists; live integration is **BLOCKED** because `runtime_present=false`. |
| Production / Canonical truth | **UNKNOWN** | The checked-in production baseline is stale relative to current `worker/index.js`; no Cloudflare production state was read. |
| Safety / no-write | **PASS** | No workflow, secret, production, Canonical, PR or deploy action. |

**Overall business result: `PARTIAL`.** The evaluation is complete and actionable, but author claims were not treated as measured PASS, and no live Codex/Hermes run was possible without credentials/runtimes that this task forbids changing.

---

## 1. Scope, method and limits

### 1.1 What was done

1. Read current repository code, tests, contracts, gates and production baseline metadata.
2. Fetched the four requested sources with plain unauthenticated HTTP and recorded HTTP status, access time, byte count and SHA-256.
3. Pinned the Darwin `SKILL.md` to its GitHub `master` commit, then read the raw file so line-level claims are attributable to a commit rather than a moving branch.
4. Cross-checked the Codex CLI and Hermes Agent version claims against public GitHub releases and npm metadata where possible.
5. Ran the existing full test suite, a live Hermes readiness probe, a deterministic Darwin-score arithmetic probe in `/tmp/opencode`, and the repository's own Gate 1 contract validator.
6. Compared the checked-in production baseline with the current Worker source instead of assuming an old report describes production today.

### 1.2 What was not done (hard boundaries)

- No repository file outside the two expected outputs was created, modified or deleted.
- No `.github/workflows/` change.
- No secret, token, OAuth scope, credential, `.env`, `.pem` or `.key` access/change.
- No Cloudflare production read/write, deployment, Worker mutation or Canonical write.
- No third-party Skill installation, no `git clone` of Darwin into the repo, no PR.
- No authenticated Codex call and no model API spend beyond normal agent execution.
- No claim that a source author's screenshots or benchmark numbers are reproduced.

### 1.3 Read limits

- The Orange Book pages are marketing/table-of-contents pages; they expose metadata and chapter titles, not full book text. Claims about what individual chapters prove remain **AUTHOR_CLAIM** unless a public README/release independently confirms the version or artifact.
- The page HTML is dynamic; the recorded SHA-256 proves exactly what was served at the access time, not that it will remain unchanged.
- Exact Codex context-window sizes, plan quotas and prices are in material not exposed by the fetched page/README and would require an authenticated account. They are **UNKNOWN**, not guessed.
- Hermes runtime behavior is unobservable here: no `hermes` executable, no container, no gateway on `127.0.0.1:9900`, and no endpoint environment variable.

---

## 2. Source register: links, versions, access date, facts vs inferences

All retrieval timestamps below are UTC on **2026-10-21**. SHA-256 values are over the exact response body fetched in this run.

| ID | Source link | Version / access | Size and SHA-256 | FACT (directly observed) | INFERENCE / limit |
| --- | --- | --- | --- | --- | --- |
| **S1** | https://www.huasheng.ai/orange-books/harness/ | Page `v1.1.0`; No. 09; accessed `2026-10-21T08:10:53Z` | 65,179 B; `50c057c883d86b0d3217873eea1d3cc1eee5ddb5dc3375e0ea759d1a4f81951a` | HTTP 200. Page lists 18 chapters, 7 case studies, the five-component framework (instruction / constraint / capability / memory / orchestration), and the subtraction philosophy. | The page gives a chapter map, not chapter content; it is **not** evidence that this repository implements the framework correctly. |
| **S1-GitHub** | https://github.com/alchaincyf/harness-engineering-orange-book | Repo pushed `2026-08-23T14:18:32Z`; README/PDF `v260411`; 110 stars | README 3,713 B; `a3b9046d374d199a62224c744e0d293ee743b5ceb2442a6c06aa88e5a7af6d65` | HTTP 200 via GitHub API. Default branch `main`; repository describes “Agent = Model + Harness”, five components, and “少即是多”. | The page says `v1.1.0` while the GitHub PDF is `v260411`; the exact edition mapping is **UNKNOWN**. Do not assume they are the same artifact. |
| **S2** | https://github.com/alchaincyf/darwin-skill/blob/master/SKILL.md | `SKILL.md` v2.1, dated 2026-06-10; pinned commit `8a8b66258e3c45d6ae4aea39719468c6428fcb0a` (2026-09-18T13:16:41Z); accessed `2026-10-21T08:10:53Z` | 31,456 B; `3d57422079687a3aa641cb0c6c78ea8a5c6fa0c8645a37dfbcde4fdb870f7150` | MIT repository, 6,492 stars at read time. Defines a 9-dimension weighted rubric, independent sub-agent judging, paired same-judge comparisons with odd-N majority, git-based keep/revert, human checkpoints, test prompts, dry-run warnings and a results ledger. | The algorithm is readable and reusable. Reported accuracy/score gains are **AUTHOR_CLAIM**; they were not independently replicated. |
| **S3** | https://www.huasheng.ai/orange-books/codex/ | Page `v261020`; “CLI 0.163.0 真机实测版”; accessed `2026-10-21T08:10:53Z` | 62,915 B; `58cc5ba16d1edd534411b772caf5645c2e91abd826e797f7a148300b34ab7372` | HTTP 200. Page claims one ChatGPT account with six entry points, CLI 0.163.0, GPT-6.1 Sol / GPT-6 Astra / GPT-6 Luna, `AGENTS.md`, hooks/plugins/scheduled tasks, and Codex/Work sharing subscription and usage. | The page is a product/advertising page. The “real-machine test” screenshots and quota statements are **AUTHOR_CLAIM**, not reproduced. |
| **S3-official** | https://github.com/openai/codex/releases/latest and `npm view @openai/codex version` | Release `rust-v0.163.0`, published `2026-10-15T21:30:38Z`; npm `0.163.0` | n/a | The claimed CLI version exists publicly at the stated version. | Existence of a release does **not** verify the book's screenshots, permission presets, quota behavior or pricing. |
| **S4** | https://www.huasheng.ai/orange-books/hermes-agent/ | Page `v261020`; based on Hermes Agent `v0.22.2`; accessed `2026-10-21T08:10:53Z` | 74,647 B; `f4269ee9596935585a8faa0fe24b43c256e741db6e710ab9ca69b46209f333fb` | HTTP 200. Page claims self-improvement engines, Curator, three-layer memory, Skill creation/evolution, Kanban multi-agent orchestration, ~90 tools with on-demand exposure, MCP both directions, and a 20+ platform gateway. | These are **AUTHOR_CLAIM** feature descriptions. The page is not a runtime test of the current Personal AI. |
| **S4-official** | https://api.github.com/repos/NousResearch/hermes-agent/releases/latest | Release `v0.22.2`, published `2026-10-15T08:21:32Z` | n/a | The upstream version cited by the book exists publicly. | Confirms the version, not the book's 40 screenshots or the feature behavior in this environment. |

### 2.1 Author claims that are explicitly not PASS

| Claim | Source | Why it is not PASS here |
| --- | --- | --- |
| “$9 vs $200” three-agent comparison, “Stripe 1,300 PRs/week” and similar case-study numbers | S1 | Marketing summary; underlying case data was not read or reproduced. **AUTHOR_CLAIM.** |
| `SkillLens` accuracy “46.4% → 73.8%”, “+46.5 Δ”, five-judge consensus numbers | S2 | Cited by the skill author; no independent experiment, dataset or judge transcript was run here. **AUTHOR_CLAIM.** |
| “24 screenshots / real-machine test” of Codex CLI 0.163.0, exact quota behavior | S3 | The CLI release exists, but no authenticated Codex run or screenshot audit was performed. **AUTHOR_CLAIM / UNKNOWN.** |
| “40 isolated-environment screenshots”, Curator/memory/Kanban behavior | S4 | No Hermes runtime, no screenshots read, no live test. **AUTHOR_CLAIM / UNKNOWN.** |

### 2.2 Independent version checks (FACT)

- `openai/codex` latest release was `rust-v0.163.0`, published 2026-10-15T21:30:38Z; npm `@openai/codex` reported `0.163.0`.
- `NousResearch/hermes-agent` latest release was `v0.22.2`, published 2026-10-15T08:21:32Z.
- `alchaincyf/darwin-skill` default branch `master`, MIT license, 6,492 stars at read time; the pinned commit's `SKILL.md` hash is recorded above.
- These checks verify **version existence**, not author claims about behavior, quality or cost.

---

## 3. Current repository capability baseline

### 3.1 The old baseline is not the current Worker

`worker/PRODUCTION-BASELINE.json` describes a production source that does **not** match the checked-out file:

| Field | `worker/PRODUCTION-BASELINE.json` | Current `worker/index.js` |
| --- | --- | --- |
| version | `3e2fed43` | not claimed |
| SHA-256 | `8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1` | `03f781781dea349ed6155d93c6325cbbc6871e050437a8a59d647abd49488e69` |
| bytes | 55,278 | 189,957 |
| lines | 1,543 | 4,372 |

**FACT:** the baseline metadata and current source differ. **INFERENCE:** the checked-in “production baseline” is a historical capture, not proof of what is deployed now. **UNKNOWN:** the actual Cloudflare version, bindings and deployed behavior. This audit makes no production claim and did not deploy or query production.

### 3.2 Capability matrix

| Capability | Direct evidence | Status | Reuse value | Gap / limit |
| --- | --- | --- | --- | --- |
| Task-contract and scope gates | `scripts/task_contract.py`, `scripts/scope_guard.py`, `tests/test_task_contract.py`, `tests/test_scope_guard.py` | **PASS** | Reuse unchanged; readonly/write modes and forbidden-path checks are already fail-closed. | None for this audit. |
| Workflow-authoritative status | `src/personal_ai_execution/status_contract.py`, `result_normalization.py`, `tests/test_status_contract_v0_2.py`; Worker mirrors the mapping | **PASS** in repo | Reuse as the single status truth; never infer success from an artifact or narrative. | Production parity is **UNKNOWN** because the baseline is stale. |
| Advisory review assistant | `src/personal_ai_execution/review_assistant.py:96`, `tests/test_review_assistant.py` | **PASS as advisory**; **PARTIAL for independent scoring** | Reuse evidence parsing, deterministic fingerprint, fail-closed downgrade, “never auto-review”. | It is not a blind skill judge and has no paired A/B scoring. |
| Human review gate | `event_sync.py:550`, `worker/index.js:2197`, approval ledger paths/tests | **PASS** in repo | Reuse the “human final verdict” pattern for any skill promotion. | No live production approval state was read. |
| Event sync and provenance | `event_sync.py`, `provenance_contract.py`, `tests/test_runtime_provenance_v0_2.py` | **PASS** in repo | Reuse canonical provenance and read-back discipline. | Canonical store not touched. |
| Child-task advancement | `advancement.py:148`, `worker/index.js:1418`, `tests/test_autonomous_advancement.py` | **PASS** in repo | Reuse explicit pre-authorized child dispatch and D1 idempotency marker. | Deployed Worker behavior **UNKNOWN**. |
| Hermes orchestration client | `hermes_orchestration.py:245`, `:429`, `:701`; `tests/test_hermes_golden_poc.py` | **PARTIAL** | Reuse A2A client, runtime-identification honesty, Codex rejection, idempotent transport, result normalization. | **BLOCKED** for live run: `runtime_present=false`; only a gated live test is skipped. |
| Independent skill evaluation | No scoring/rubric/judge module found in `src/`, `worker/`, `tests/` | **BLOCKED** (new component) | Darwin arithmetic/paired logic reusable; existing review assistant is adjacent. | No rubric implementation, no test-prompt fixture, no judge runner, no eval ledger. |
| Codex context and quota | No `AGENTS.md`; no token/usage/quota fields in `src/`, `worker/`, `tests/`; active dispatch uses OpenCode/DeepSeek | **UNKNOWN** | Task-contract context pattern is reusable; Codex usage event schema is a design input only. | No authenticated Codex run; exact context/quota not observable. |
| Regression suite | `python -m pytest -q` | **PASS** | Reuse as the regression gate. | Green tests do not exercise a live Hermes/Codex runtime. |
| Documentation / instruction layer | 66 Markdown files; 45 at top level; no `AGENTS.md` | **PARTIAL** / **INFERENCE** | Harness “instruction layer” concept is applicable. | Volume is high; subtraction/consolidation is more valuable than adding another framework. |

### 3.3 Test evidence from this run

```text
$ python -m pytest -q
1753 passed, 1 skipped in 65.47s (0:01:05)
```

The single skip is the explicitly gated real-Hermes golden test:

```text
SKIPPED tests/test_hermes_golden_poc.py:370:
set HERMES_GOLDEN_RUNTIME=1 and provide a real Hermes gateway
```

Targeted run:

```text
$ python -m pytest -q -rs tests/test_hermes_golden_poc.py
53 passed, 1 skipped
```

This is a **FACT** about the repository test suite. It is **not** a PASS for a live Hermes integration.

---

## 4. Reuse assessment by source

### 4.1 Harness Engineering (S1)

**What is reusable**

- The five-layer decomposition — instruction, constraint, feedback/capability, memory, orchestration — maps cleanly to existing repository concerns:
  - instruction: task contract + workflow prompt;
  - constraint: `task_contract.py`, `scope_guard.py`, secret guard;
  - feedback: pytest, result normalization, review assistant;
  - memory: Canonical assets, provenance, EVENT_SYNC;
  - orchestration: Worker dispatch, child-task advancement.
- “犯错就加一条规则” is already the repository's pattern: failures become pytest regressions and fail-closed gates.
- “少即是多” is actionable as a **subtraction** rule, not as a reason to add another abstraction layer.

**What is missing**

- There is no `AGENTS.md` instruction layer and no explicit context-budget policy. The task contract provides context, but it is not a durable repository-level instruction map.
- There is no periodic “harness health” review that asks which rules are stale. The audit found 66 Markdown files and 45 top-level docs; that is an **INFERENCE** of possible documentation sprawl, not a measured defect.
- The source page itself is only a chapter map; it cannot be used as proof that a given harness design works.

**Decision:** reuse the five-layer checklist as an audit rubric; do not add a new framework. Any consolidation or `AGENTS.md` addition needs its own task allowlist and review.

**Priority:** P1 (low risk, documentation/process only). **Benefit:** clearer instruction context and less duplicated guidance. **Risk:** adding more prose instead of removing stale prose.

### 4.2 Darwin Skill (S2)

**What is genuinely deterministic and reusable**

The `SKILL.md` contains enough specification to implement a deterministic core without calling a model:

- 9 dimensions and weights: `7 + 12 + 12 + 6 + 18 + 4 + 12 + 23 + 6 = 100`.
- Total score = `Σ(dimension_score × weight) / 10`, with dimension scores 1–10.
- Absolute total is **triage only**. Keep/revert uses paired comparison with the same judge seeing both versions, odd `N` (default 3, extend to 5 on a close call), majority `better` vs `worse`; ties count toward keep.
- A `dry_run` ratio above 30% triggers the source's “evaluation invalid” warning.
- Human checkpoints are mandatory.
- Revert uses `git revert`, never `git reset --hard`.
- A results ledger records `timestamp`, `commit`, `skill`, `old_score`, `new_score`, `status`, `dimension`, `note`, `eval_mode`.
- File-size guard: optimized `SKILL.md` should not exceed 150% of the original.
- Runtime-neutrality scan is a gate.

This audit executed a small pure-Python probe of the arithmetic/decision core:

```text
PASS skill-eval arithmetic probe
weights_sum=100 equal_score_total=50.0 paired_3_2_1=keep paired_1_2=revert
dry_run_ratio_gt_30pct=warn full_test_majority=no_warn
```

Probe SHA-256: `3606e7e60dbef8fa0f6701dfe5275285c1d5a1e303bb956a4fefdfb82f4a8d1a`. This proves the **formula and majority rule are implementable and testable**. It does **not** prove any skill's quality, because no test prompts were run and no independent judge was called.

**What is missing for real reuse**

| Darwin element | Current repository | Classification |
| --- | --- | --- |
| 9-dimension rubric schema | No implementation | **New component** |
| Independent sub-agent judge | Review assistant is deterministic evidence review, not a blind quality judge | **Missing adapter** |
| Test prompts (`2–3` per skill) | No skill test-prompt fixtures | **New component** |
| Paired same-judge majority | No judge runner; logic is trivial and reusable | **Missing adapter** |
| Git ratchet / revert | Git and pytest exist; no eval ledger | **Reusable + new ledger** |
| Human checkpoint | Existing human review/approval gate | **Reusable** |
| `results.tsv` history | No equivalent | **New component** (could be JSON/TSV evidence) |

**Important honesty boundary**

The source's claims that adding meta-skill dimensions raised LLM-judge accuracy from 46.4% to 73.8%, or that particular skills improved by `+10.85` / `+14.9` / `+16.5`, are **AUTHOR_CLAIM**. The audit did not reproduce them. The source itself warns that absolute LLM-judge scores have roughly ±8 noise and that fine-grained differences are not trustworthy — so any future implementation must use paired majority and human review, not a single absolute score.

**Decision:** **PARTIAL** reuse. Build only the deterministic rubric/ledger core first; any actual judge call is a separate, budgeted, credentialed task. Do not install Darwin Skill into the repo.

**Priority:** P0 for the deterministic core; P1 for a real independent judge. **Benefit:** repeatable skill-quality evidence and regression ratchet. **Risk:** LLM judge noise, prompt injection in evaluated skills, cost, and false confidence from a single score.

### 4.3 Codex (S3)

**Source facts vs product claims**

- FACT: page `v261020` says CLI `0.163.0`; official release `rust-v0.163.0` and npm `0.163.0` exist.
- AUTHOR_CLAIM: “one account, six entry points”, GPT-6 model names, `--full-auto`/`--api-key` removal, 24 real-machine screenshots, shared Work/Codex subscription usage.
- UNKNOWN: exact context window, token quota, reset policy, overage price and plan entitlement. These are not on the fetched page/README and would require an authenticated account.

**Current repository reality**

- `.github/workflows/agent-dispatch.yml` runs `opencode run --standalone --auto --model opencode-go/deepseek-v4.1-flash`, not Codex.
- There is no `AGENTS.md`.
- A scoped grep over `src/`, `worker/`, `tests/` and `scripts/` found no `prompt_tokens`, `completion_tokens`, `total_tokens`, `context_window`, model quota or usage ledger. The only `quota` matches in the broader repository belong to the ServerChan push ledger in `hello.py`, not model billing.
- The Hermes module explicitly rejects a Codex executor on its golden path (`CODEX_MARKERS`, `:621`), which is a deliberate architecture choice, not a Codex integration.

**Reuse decision**

| Codex idea | Reuse | Classification |
| --- | --- | --- |
| `AGENTS.md` as durable instruction map | Applicable, but currently absent | **New documentation component** |
| Context layering / compaction | Task contract already supplies explicit context; no compaction policy | **Partial / new design** |
| `/usage` and quota awareness | No telemetry or preflight budget gate | **Missing adapter** |
| Permission presets / auto-review | Existing explicit gates are stricter | **Not needed / do not weaken** |
| Cloud tasks | Current GitHub Actions + Worker dispatch already covers the need | **Reuse existing** |

**Decision:** **UNKNOWN/PARTIAL**. Do not adopt Codex merely because the book documents it. If a future task needs Codex, add a read-only usage parser and a fail-closed quota preflight behind an explicit approval; never hardcode a quota number from an author's page.

**Priority:** P1 only if a concrete Codex use case appears; otherwise P2. **Benefit:** better context discipline and cost visibility. **Risk:** subscription/quota consumption, credential exposure, and duplicating the existing OpenCode path.

### 4.4 Hermes (S4)

**What overlaps**

| Area | Hermes Agent (author claims) | Current Personal AI | Overlap / decision |
| --- | --- | --- | --- |
| Orchestration | A2A/gateway, delegate_task, Kanban, eight collaboration modes | Task contract, Worker dispatch, child-task advancement, Hermes A2A client | High overlap; reuse the boundary, do not add a second orchestrator. |
| Memory | Three-layer memory, session search | Canonical assets, provenance, EVENT_SYNC task memory | Conceptual overlap; current Canonical store must remain authoritative. |
| Skills | `/learn`, Skill creation/evolution, Curator | `write_skill_candidate`, review/promotion gate, no evaluator | Partial; borrow the Curator “gate before learning” idea, not the runtime. |
| Tools/MCP | ~90 tools, on-demand exposure, MCP both directions | Worker MCP tool surface, approval ledger | Partial; current surface is narrower and more auditable. |
| Multi-agent | Kanban, delegation | Parent/child dispatch + lineage | Partial; no Kanban/scheduler UI. |
| Gateway/platforms | 20+ messaging platforms | None (GitHub/Cloudflare path only) | Not needed; high complexity and new attack surface. |
| Safety | OS boundary, Promptware defense | Fail-closed gates, secret guard, provenance, human gate | Current design is stronger for Canonical safety; keep it. |

**Live readiness**

This run called the repository's own probe:

```json
{
  "runtime_present": false,
  "runtime_kind": null,
  "endpoint": null,
  "credential_source": null,
  "checked": [
    "executable:hermes",
    "executable:hermes-agent",
    "executable:hermes-gateway",
    "env:HERMES_GATEWAY_URL",
    "env:HERMES_A2A_URL",
    "env:HERMES_A2A_ENDPOINT",
    "agent_card:http://127.0.0.1:9900/.well-known/agent-card.json"
  ],
  "missing_dependency": "reachable_real_hermes_runtime",
  "next_action": "Provide/start a real Hermes gateway (A2A platform enabled, routable endpoint + bearer token) or point HERMES_A2A_URL at it; no runtime exists in this environment to integrate against"
}
```

**Status:** code path **PARTIAL/PASS in tests**, live integration **BLOCKED**. The honest outcome is not PASS.

**Prior MUSE audit caution:** `docs/audits/MUSE_HOME_XIAOYI_HERMES_A2A_COMPATIBILITY_AUDIT_20260930.md` found that Huawei 云A2A and Hermes's Linux Foundation A2A v1.0 are **not** directly compatible; protocol names overlap but session/auth/envelope dialects differ. That audit is about a different peer, not a verdict on Hermes quality, but it reinforces that “Hermes” is not a drop-in universal adapter.

**Decision:** reuse the existing Hermes **client** and its honesty/fail-closed contract. Do not replace Personal AI with Hermes, do not create a second state store, and do not adopt the 20+ platform gateway. If a real runtime is approved later, run the already-gated A2A smoke test first.

**Priority:** P2 for live integration; P0 for documenting the boundary. **Benefit:** replaceable executors without changing Canonical truth. **Risk:** duplicate state, credential handling, promptware, and operational complexity.

---

## 5. Priority, benefit, risk and approval

| ID | Action | Priority | Benefit | Main risk | Approval needed? |
| --- | --- | --- | --- | --- | --- |
| **P0-A** | Maintain this evidence index as the source pin for Huashu material (URL + commit + SHA-256 + access time). | P0 | Reproducible provenance; no more “old report = current truth”. | Pages are dynamic; hash must be refreshed. | No — done in this task. |
| **P0-B** | Implement the deterministic Darwin rubric arithmetic + paired-majority core and a test-prompt fixture schema in an isolated read-only task. | P0 | Turns a prose method into testable code without model spend. | Mis-scoring if rubric semantics are guessed. | No, if no external judge and no skill install. |
| **P0-C** | Reuse existing pytest as the regression ratchet for any evaluation harness; add a small JSON/TSV result ledger. | P0 | Prevents silent quality regressions. | Ledger can become a new source of truth if not marked advisory. | No, within a new allowlist. |
| **P1-A** | Codex usage/context adapter: parse a recorded usage event, record tokens/quota, fail closed when unknown. | P1 | Cost/context visibility. | Consumes quota; credential risk. | **Yes** — authenticated Codex run and model budget. |
| **P1-B** | Hermes live A2A smoke test against an approved gateway with a non-Codex executor. | P1 | Converts BLOCKED to measured PARTIAL/PASS. | Endpoint/token, network exposure, promptware. | **Yes** — runtime endpoint and credential. |
| **P1-C** | Independent blind judge (paired, odd-N majority) for skill-quality evaluation. | P1 | Reduces self-evaluation bias. | Judge noise, cost, data leakage, prompt injection. | **Yes** — external model, budget, data policy. |
| **P2-A** | Curator-like “learn only after human gate” skill loop. | P2 | Safer skill evolution. | Could automate bad learning; Canonical risk. | **Yes** — Canonical/skill write and third-party Skill policy. |
| **P2-B** | Hermes memory/Kanban/gateway adoption. | P2 / defer | Feature breadth. | Duplicate state, operational complexity, security surface. | **Yes** — architecture change. |
| **P2-C** | `AGENTS.md` / instruction-layer consolidation. | P2 | Clearer context, less doc drift. | More prose; scope creep. | Task allowlist approval, low risk. |

**Recommended order:** P0-A (done) → P0-B → P0-C → decide whether P1-A/P1-C has a real use case → only then P1-B → defer P2-B.

---

## 6. Reproducible deterministic checks and sandbox plan

### 6.1 Checks executed in this run

| ID | Check | Command / method | Actual result | Status |
| --- | --- | --- | --- | --- |
| T1 | Fetch all four sources and pin hashes | `curl -L` + `sha256sum` | 4/4 HTTP 200; hashes in §2 | **PASS** |
| T2 | Repository regression | `python -m pytest -q` | `1753 passed, 1 skipped in 65.47s` | **PASS** |
| T3 | Hermes readiness | `PYTHONPATH=src python -c "from personal_ai_execution.hermes_orchestration import probe_hermes_runtime; ..."` | `runtime_present=false`; missing `reachable_real_hermes_runtime` | **BLOCKED** (honest absence) |
| T4 | Darwin arithmetic / paired majority | `/tmp/opencode/skill_eval_probe.py` | `PASS`; weights 100; paired 2:1 keep; 1:2 revert; dry-run >30% warn | **PASS** |
| T5 | Task-contract Gate 1 | `python scripts/task_contract.py /tmp/opencode/task.json` | `PASS: structured task contract valid` | **PASS** |
| T6 | Scope guard | `python scripts/scope_guard.py <base> /tmp/opencode/task.json` | Only the two expected outputs; no deletions | **PASS** (see §6.2) |
| T7 | Production baseline parity | Compare `worker/PRODUCTION-BASELINE.json` with `sha256sum`/`wc` of `worker/index.js` | SHA, bytes and line count do not match | **PASS (mismatch confirmed)**; production state **UNKNOWN** |
| T8 | No-write / no-Canonical check | `git status --short`, `git diff --name-status` | Only the two expected files; no production/canonical path | **PASS** |

### 6.2 Exact evidence commands

```bash
# Source capture (read-only)
curl -sS -L -o /tmp/opencode/harness.html https://www.huasheng.ai/orange-books/harness/
sha256sum /tmp/opencode/harness.html
curl -sS -L -o /tmp/opencode/darwin_SKILL.md \
  https://raw.githubusercontent.com/alchaincyf/darwin-skill/8a8b66258e3c45d6ae4aea39719468c6428fcb0a/SKILL.md
sha256sum /tmp/opencode/darwin_SKILL.md

# Repository truth
git rev-parse HEAD
sha256sum worker/index.js
python -m pytest -q

# Hermes readiness (read-only; no credential values printed)
PYTHONPATH=src python - <<'PY'
from personal_ai_execution.hermes_orchestration import probe_hermes_runtime
p = probe_hermes_runtime()
print({k: p[k] for k in ("runtime_present", "missing_dependency", "next_action")})
PY

# Contract / scope gates
python scripts/task_contract.py /tmp/opencode/task.json
python scripts/scope_guard.py <base> /tmp/opencode/task.json
```

### 6.3 Sandbox test plan for the next tasks

| Plan ID | Test | Preconditions | Expected | If unavailable |
| --- | --- | --- | --- | --- |
| **S-1** | Rubric arithmetic and paired majority on a synthetic fixture | Pure Python, no network | Exact totals, keep/revert, dry-run warning | Not applicable; deterministic. |
| **S-2** | Score a repository-owned skill document with a **human-authored** rubric | 2–3 test prompts; no external model | Evidence packet with per-dimension reasons, `advisory=true` | **UNKNOWN** if no agreed prompts. |
| **S-3** | Blind A/B with independent judges | Approved model, budget, same judge sees both versions, odd N | Majority decision + margin + reasons; no absolute-score ratchet | **BLOCKED** without approval. |
| **S-4** | Codex usage parser against a recorded `--json` event | Approved real Codex run or redacted fixture | Token/usage record, unknown fields marked null | **UNKNOWN** if no event. |
| **S-5** | Hermes A2A `SendMessage` smoke test | Real gateway, bearer token, non-Codex executor, allowlisted prompt | Terminal task, executor identity, normalized evidence | **BLOCKED** without runtime. |
| **S-6** | Canonical safety regression | Existing gates + scope guard | No write outside allowlist; no secret | **PASS** by construction in tests; production unverified. |

**Important:** all of S-1/S-2 can run without user intervention; S-3/S-4/S-5 need explicit approvals. S-2's “human-authored” prompts can be drafted by the agent but must be reviewed before being treated as a quality benchmark.

---

## 7. Safety statement: no production or Canonical write

- This audit added exactly two files: `HUASHU_REUSE_AUDIT_V1.md` and `HUASHU_EVIDENCE_INDEX_V1.json`.
- No existing file was modified or deleted.
- No `.github/workflows/`, secret/token/credential/.env/.pem/.key path was read or changed.
- No Cloudflare Worker, D1, KV, binding, deployment, OAuth scope or Canonical asset was written.
- No PR, no merge, no deploy, no third-party Skill install.
- The Hermes probe only performed a local read-only resolution/HTTP attempt; no credential value was printed.
- The “production baseline mismatch” is reported as a repository inconsistency, not as a production incident claim.

`git status --short` after this run contains only the two expected untracked files; `git diff --name-status` is empty until they are committed.

---

## 8. Acceptance mapping

| Acceptance criterion | Where satisfied | Status |
| --- | --- | --- |
| List each source link, version or access date, and separate fact from inference | §2 source register, §2.1 author claims, JSON `sources` | **PASS** |
| Compare with existing repository capabilities and include at least one reproducible deterministic check; mark UNKNOWN if untestable | §3 matrix, §4, §6 checks; Codex quota and production state marked **UNKNOWN** | **PASS** (with honest UNKNOWNs) |
| Classify results PASS/PARTIAL/BLOCKED/UNKNOWN and state a next step that can continue without user intervention | §0, §5, §6.3, §9 | **PASS** |
| No production or Canonical write | §7; only two expected files | **PASS** |

---

## 9. Next step that can continue without user intervention

**NEXT-A (no approval): build the deterministic evaluation core in an isolated task.**

Scope proposal for the next allowlisted task:

- Add a pure-Python `skill_eval` core with:
  - the 9 dimension weights,
  - score validation (1–10),
  - `paired_decision(votes)` majority,
  - `eval_mode` and `dry_run` ratio guard,
  - a JSON evidence schema matching `HUASHU_EVIDENCE_INDEX_V1.json`.
- Add 2–3 **locally authored** test prompts as fixtures; do not call a model.
- Add pytest tests for arithmetic, ties, invalid scores, and dry-run threshold.
- Run only on a repository-owned document or a synthetic skill; write evidence to a non-Canonical report.
- Do **not** install Darwin Skill, do not call an external judge, do not write Canonical.

**NEXT-B (no approval): re-run the read-only source/version/hash refresh** before any future evaluation, because the Orange Book pages are dynamic and may change.

**NEXT-C (no approval): run the existing Hermes readiness probe** on any future cloud runner and record `runtime_present`, endpoint source and missing dependency; this keeps integration status honest without credentials.

**Blocked until approval:** any live Codex run, any external judge call, any Hermes gateway connection, any Canonical SKILL write, any production deploy. See §10.

---

## 10. Explicit pending approvals

| Approval ID | Action requiring approval | Why it cannot be done now | Safe default until approved |
| --- | --- | --- | --- |
| **PA-1** | Call an external LLM judge for paired skill evaluation | Model choice, budget, data-retention and prompt-injection policy | Use deterministic rubric core only; mark judge dimensions `UNKNOWN`. |
| **PA-2** | Authenticated Codex CLI run and quota consumption | Requires account credential and may consume paid/shared quota | Do not run; keep Codex status `UNKNOWN`. |
| **PA-3** | Start/connect a real Hermes A2A gateway | Requires routable endpoint + bearer token, possibly network exposure | Keep `runtime_present=false`; no live test. |
| **PA-4** | Install or vendor Darwin Skill / any third-party Skill | Supply-chain and prompt-code risk; explicitly forbidden in this task | Read the public source only; no install. |
| **PA-5** | Write/promote a SKILL to Canonical | Canonical mutation and human approval ledger requirement | No write; evaluation output is advisory. |
| **PA-6** | Deploy Worker changes to Cloudflare production | Production mutation and separate deploy gate | No deploy; production state `UNKNOWN`. |
| **PA-7** | Add `AGENTS.md` or other new repository guidance | Out of this task's two-file allowlist | Defer to a dedicated task with its own scope. |

---

## 11. Final conclusion

- **PASS:** source retrieval, version pinning, repository test baseline, deterministic arithmetic probe, contract gate, scope/no-write discipline.
- **PARTIAL:** Harness reuse, Darwin method reuse, Hermes architecture overlap. The reusable parts are real; the evidence does not justify claiming a full production integration.
- **BLOCKED:** live Hermes integration, real independent judge, third-party Skill installation, any Canonical/production change.
- **UNKNOWN:** actual Cloudflare production version, exact Codex context/quota/pricing, and author-reported benchmark/screenshot claims.

The strongest reusable asset is not any single Huashu book. It is the repository's existing **fail-closed evidence discipline**: workflow-authoritative status, explicit gates, human review, provenance, and regression tests. The correct next move is to add a small deterministic evaluation core around that discipline — not to import a third-party Skill runtime or a second orchestration stack.

**Business outcome:** `PARTIAL`
**Deliverable:** `PASS`
**Canonical/production writes:** `0`
