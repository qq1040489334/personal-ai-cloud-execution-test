# batch12-dedup-review-v2 — KNOWLEDGE_BATCH_12_CANONICAL_DEDUP_V2

- Task: `cf-2a25d30bcd65` (parent `cf-356d867fb663`)
- Project: `personal-ai-knowledge-triage`; Risk: `LOW`; Mode: **READONLY / RESEARCH ONLY**.
- Baseline (read for real, not via execution_result summary): `outputs/source-manifest.md`,
  `outputs/claim-evidence-matrix.md`, `outputs/distilled-knowledge.md`,
  `outputs/dedup-canonical-review.md`, `outputs/gaps-and-gates.md` at commit
  `945bdf40d347e84347b9d4f9e55a463ef774274d`. Those files are **not modified**.
- Canonical scope: the real 20-asset inventory in `batch12-canonical-inventory-v2.md`.
- **Global status: `FULL_CANONICAL_DEDUP_BLOCKED`** — 19/20 asset bodies unread; only
  `knowledge-agent-permission-action-governance` is available at principles level.

## 0. Two comparison layers, strictly separated

| Layer | What is compared | Coverage | Result |
|---|---|---|---|
| **L1 — Title/metadata overlap screening** | candidate topic ↔ real asset title/type | 20/20 assets | performed (`batch12-canonical-inventory-v2.md` §5) |
| **L2 — Full-text semantic comparison** | candidate mechanism ↔ actual normative clauses | 1/20 assets | **not performed (BLOCKED)** except K13 principles |

No statement in this file may be read as an L2 pass for any asset whose body was not read.
All "MERGE" decisions below are **risk-based recommendations pending L2**, except where K13/K12
full-text/K12-topic evidence specifically supports them.

## 1. Explicit dedup of known Canonical assets

### 1.1 `knowledge-agent-permission-action-governance` (K13, full-text principles available)

Provided v1.0 principles: (a) autonomous READ/RESEARCH; (b) low-risk reversible ACTION
pre-authorized within scope; (c) important production/Canonical **WRITE requires Human Gate**;
(d) sensitive-permission & irreversible actions require a **strong Gate**; (e) approval binds
**actor / action / target / risk / time**; (f) audit must **distinguish draft from real
execution**.

**Dedup rule for this batch:** the permission-boundary theses raised by T01, T02, T07, T10, T12
are **already subsumed**. They must **NOT** be re-added as new principles. Only the following
per-surface *implementation increments* survive into the candidate set, and even those require
an L2 body read before any MERGE-fit is finalized:

| Topic | Permission claim in candidate | Disposition |
|---|---|---|
| T01 小艺帮帮忙 | OS may act on third-party apps; lock-screen limit; vendor policy gate | MERGE (no new principle). Increment candidate: concrete OS/device/policy bound list + lock-screen exception — implementation detail only. |
| T02 补天 | authorized-scope + NDA + time-box + reputation gate | MERGE into K13 (authorization/audit). Increment candidate: anti-pattern "mass AI-generated reports" as a concrete audit failure example. |
| T07 Today AI | confirm-before-send/calendar; memory visible/editable | MERGE into K13 + K17. Increment candidate: "wrong-memory cost scales with proactivity" as a failure mode. |
| T10 Instinct | broad ToS appoints agent; liability cap; data retention after disconnect | MERGE into K13. Increment candidate: concrete retention/liability-cap audit checklist. |
| T12 agent-browser | executable skill stores auth state on disk; upload sends files | MERGE into K13 (+ S02 computer_use_guard). Increment candidate: credential-state-on-disk check. |

> **Net effect:** T01/T02/T07/T10/T12 contribute **zero new permission principles**; they may
> contribute implementation/test detail only, and never duplicate K13's clauses.

### 1.2 `knowledge-ai-era-computational-thinking-review` (K12, title = "AI编程验证") — T03

T03 (Vibe Coding 2026) is directly in scope of K12. The candidate's "prototype vs production;
verify AI-generated code" thesis is **not new**. Disposition:

- **MERGE** the principle into K12.
- Retain as *increment evidence* only: the **measured production security-gap corpus**
  (~44–45% of tasks introduce a known vuln; syntax ~95%+ vs security ~55–56%; Java worst) and
  the **falsification test** (SAST pass-rate with/without security prompting). This is
  quantitative evidence, not a new principle → `REFERENCE`.
- Do **not** attribute any specific statistic to the source video (first-round `T03-C5 = UNKNOWN`).

### 1.3 Other title-level overlaps flagged for L2

K05/K01/K17 (T01/T07/T10), K14/S02 (T04/T12), K16/K08/S01 (T06), K15 (T03/T07/T12),
K10 (T02/T09), K04/K07 (T03), K02/S01 (T08/T11). Each is a **duplication risk**, not a finding;
bodies must be read (see inventory §6).

## 2. Per-topic T01–T12 incremental audit

Evidence grades: **A** = independent non-vendor evidence for the retained mechanism;
**B** = useful but material elements self-reported/unread; **C** = blocked/not found/unevidenced.
A trailing `†` marks a decision that additionally depends on the blocked L2 body read.

| # | Topic | Existing Canonical synonym (by title) | Verifiable unique increment | Evidence | Classification | Executable test | Owner |
|---|---|---|---|---|---|---|---|
| T01 | 小艺帮帮忙 | K05 operit-mobile-agent-runtime; K01 mobile-entry; K13 governance; S02 guard | OS/device/policy bound list incl. the *not-offered-on-HarmonyOS-7.0* and *no-lock-screen* exceptions | B | **REFERENCE** (MERGE permission part; no new principle) | On supported device, issue multi-step background task; assert no foregrounding and no lock-screen execution; re-check on 7.0 | Agent probes + human device run |
| T02 | 补天 | K13 governance; K10 evidence-vs-expected-value | "Authorized-scope + reputation gate makes it quality-gated, not passive income"; AI-report-spam anti-pattern | A | **MERGE** (into K13) | Submit one scope-compliant AI-assisted report on a public SRC; observe accept/reject + reputation; mass submission must fail | Human (legal/scope) + Agent logging |
| T03 | Vibe coding | K12 AI编程验证 | Measured security-gap corpus + SAST falsification protocol | A | **MERGE** (K12) + **REFERENCE** (corpus) | Fixed task set: SAST pass-rate with vs without security prompting; claim fails if unprompted rate approaches syntax rate | Agent execution |
| T04 | MATLAB skills | K14 local-execution-interface; S02 guard; K13 | Skill-provenance checklist: repo existence, license, MCP/session execution reach; `SamuelQQ/matlab-skills` = 404 negative case | B | **REFERENCE** (named repo **REJECT**/`ARCHIVE` as not-found) | `GET /repos/{owner}/{repo}` → 404 falsifies; then diff SKILL.md permissions before install | Agent execution |
| T05 | 原子习惯 | K03 可控变量 (weak, unconfirmed) | Identity layer + four-stage design checklist as operationalization over system-over-willpower | A (primary author pages) | **MERGE** (system part) + **keep increment** identity/friction | A/B identity-statement+tiny-win vs willpower reminder; measure adherence over weeks | Human learning |
| T06 | LLM Wiki/GBrain | K16 scoped-knowledge-layers; K08 Obsidian; S01 distillation-promotion | compile-vs-RAG distinction + ingest→query→lint→promote loop (op procedure) | B (pattern A; vendor metrics C) | **MERGE** (layers/index) + **REFERENCE** (loop); vendor metrics **ARCHIVE** | Small wiki vs naive chunk retrieval at equal corpus size; compare query accuracy | Agent execution |
| T07 | Today AI | K17 local-execution-shared-intelligence; K09 voice; K06 structured-data; K13 | memory→proactive-brief→confirmed-execution loop + "wrong-memory cost scales with proactivity" failure mode | B (vendor/reviewer, no benchmark) | **MERGE** (permission part) + **REFERENCE** (loop) | Seed a known false memory; measure correction latency after user edit | Agent + human review |
| T08 | 十步速学 | K02 intent-clarification; S01 distillation | Structured learning loop (multi-perspective→contradiction→compress→active-test→compress) with human-in-the-loop gates | B (structure real; multipliers C) | **REFERENCE** (structure) + **REJECT** ("10x"/"25%"/"20小时"/future date) | Pre/post + delayed retention: method vs plain reading on one topic | Human learning |
| T09 | AI服务业 | K10 evidence-vs-expected-value | Data-hygiene rule: official-statistic vs speculation vs self-reported separation (NBS 57.7%; 100万亿 target) | A (stats) / C (speculation) | **REFERENCE** (stats) + **ARCHIVE** (cognitive-decline / celebrity-device claims) | Re-pull NBS series + policy doc; attempt to locate a peer-reviewed cognition source; absence falsifies strong version | Agent execution |
| T10 | Instinct | K01 mobile-entry; K17; K13; S02 | chat-thread form-factor adoption vs liability checklist (retention, ToS training, $100 cap) | B (form factor verified; GMV/40% self-reported C) | **MERGE** (governance) + **REFERENCE** (liability checklist); metrics **ARCHIVE** | Disconnect integration; data-subject deletion verification; audit ToS retention/training/liability clauses | Agent + human legal |
| T11 | 触类旁通 | K02 intent-clarification (weak) | transfer-training principle: near transfer via schema/varied practice; explicit far-transfer boundary | A (academic) | **REFERENCE** + **MERGE-adjacent** to T08 learning loop | Train structured set; test near vs far variants; large near-vs-far gap falsifies general transfer | Human learning |
| T12 | agent-browser | K14 local-execution-interface; S02 computer_use_guard; K13 | accessibility-snapshot `@eN` deterministic control; credential-state-on-disk exposure surface | B (upstream docs A; SkillHub provenance partial) | **REFERENCE** + **MERGE** (guard/governance) | Diff installed skill vs upstream; `state save` then inspect file for tokens; attempt out-of-scope action | Agent execution |

### 2.1 Decision distribution (avoids keeping all 12)

- **MERGE-heavy (permission/verification duplicate):** T01, T02, T03, T07, T10 (governance/verification parts) — no new principle.
- **KEEP as REFERENCE (implementation/operational):** T04, T06, T08, T12 (+ REFERENCE portions of T01/T03/T07/T09/T10).
- **KEEP with genuinely new domain increment:** T05 (identity/friction), T11 (transfer boundary).
- **ARCHIVE / REJECT:** T04 named repo; T08 multipliers + future date; T09 cognitive-decline & celebrity claims; T06 vendor metrics; T10 GMV/card-ratio metrics; T03 video-specific stat.
- **No topic is promoted; no topic is retained unchanged.**

## 3. High-value new mechanisms (small set) + validation plans

Only **three** mechanisms survive as candidate *new* knowledge (each still requires an L2 body
read against K01–K18 to confirm novelty, and none is promoted):

### N1 — Behavior-change design layer (identity + process + environment)
- **Increment over Canonical:** identity-as-first-move and a four-stage (cue/craving/response/
  reward) + four-law/inversion design checklist. No Canonical title evidences this domain.
- **Evidence:** A (James Clear primary author pages); popular-science boundary.
- **Validation plan:** controlled A/B over 4–8 weeks: identity statement + tiny-win vs generic
  reminding; primary metric = adherence rate; secondary = self-reported identity strength.
- **Falsifiable if:** no adherence difference (or worse) vs control.

### N2 — Structured learning & transfer loop with human-in-the-loop gates
- **Increment over Canonical:** a concrete operational loop (multi-perspective → contradictions
  → compress → ≤5 curated resources → difficulty ladder → active recall → Feynman/one-pager)
  plus an explicit **far-transfer boundary** (near transfer works; far transfer is not
  automatic). Distinct from K02 (intent clarification) and S01 (distillation promotion).
- **Evidence:** B (author workflow) + A (transfer literature, T11).
- **Validation plan:** pre/post on one topic, method vs plain reading, with **delayed retention**
  (1–2 weeks) and near/far transfer items.
- **Falsifiable if:** no significant gain in retention or in near transfer.

### N3 — Evidence/data-hygiene rule for macro & self-reported narratives
- **Increment over Canonical:** a single rule that classifies every quantitative statement as
  `OFFICIAL_STATISTIC` / `INDEPENDENT_RESEARCH` / `SELF_REPORTED` / `SPECULATION` and forbids
  promotion of the last two. Applies to T09 (macro), T10 (GMV/card-ratio), T06 (page counts),
  T08 (multipliers).
- **Evidence:** A for official statistics (NBS), C for the excluded narratives.
- **Validation plan:** per claim, re-pull the primary source; if only vendor/founder/podcast
  sources exist, the claim stays `SELF_REPORTED` and is excluded.
- **Falsifiable if:** an independent measurement aligns the self-reported figure.

## 4. Priority practical tests (maximum 3)

| Priority | Test | Cost | Risk | Falsifiable condition |
|---|---|---|---|---|
| **P1** | **Skill provenance + credential-state audit** for `agent-browser` / third-party skills: diff installed skill vs upstream; `state save` then scan file for tokens; enumerate allow-tools; attempt one out-of-scope action and confirm guard blocks | Low (local sandbox) | Low (isolated session, dummy creds only) | PASS only if no token leakage and out-of-scope action is blocked; otherwise the reuse recommendation is falsified |
| **P2** | **Learning-loop A/B** (N2): method vs plain reading, pre/post + delayed retention + near/far transfer items | Low–Med (time; needs participants) | Low | Falsified if retention/near-transfer gain is not significant |
| **P3** | **AI-code verification protocol** (T03/K12 increment): fixed task set, SAST pass-rate with vs without security prompting | Low (automated) | Low | Falsified if unprompted pass rate approaches syntax pass rate (i.e., security gap absent) |

*(Not selected: bug-bounty live submission — compliance/legal risk too high; Huawei device run —
hardware unavailable in this environment.)*

## 5. De-noising: what this batch removes

- **Promotional/unverifiable data:** "10x"/"25% memory"/"20小时" (T08), GBrain page/P@5 counts
  (T06), Instinct GMV / "40% share card" / retention (T10), "AGI/Jarvis" framing (T01/T06/T07/T10).
- **Repeated slogans:** duplicate "user needs are king / knowledge compounds" refrains across
  T06/T07/T12 are collapsed to one statement and not re-added as principles.
- **Unevidenced claims:** T09 irreversible-cognitive-decline and celebrity-children device limits;
  T03 video-specific security statistic; T01 "HarmonyOS 7 feature" framing (contradicted by K05 scope).
- **Invalid dates:** T08's `2026-11-09` (future relative to retrieval).

## 6. Dedup status

- `knowledge-agent-permission-action-governance` (K13): **deduped at principles level** — T01/T02/T07/T10/T12 add no new permission principle.
- `knowledge-ai-era-computational-thinking-review` (K12): **deduped at title+principle level** — T03 principle merged; security corpus retained as reference evidence only.
- All other K-assets: **title-level screen only**; body read pending → `FULL_CANONICAL_DEDUP_BLOCKED`.
- Business outcome remains `PARTIAL` (see `batch12-evidence-gates-v2.md`); no promotion, no write.
