# GBrain Architecture Learning Experiment V1

- Task: `cf-e99d73352c64` — `GBrain_ARCHITECTURE_LEARNING_EXPERIMENT_V1`
- Project: `personal-ai-knowledge-triage`; Risk: `LOW`; Mode: **READONLY / RESEARCH ONLY**
- Research object (fixed): the **GBrain architecture**. This experiment does **not** evaluate
  GBrain's marketing/promotion, and it does **not** judge whether GBrain is a good product.
- Experiment objective: test whether the **WorkBuddy ten-step structured-learning method**
  (`T08`) improves *real knowledge absorption* on a fixed technical topic, compared with a
  plain-reading baseline. The learning *process* is the unit under test; GBrain is only the
  study material.
- Hard constraints (honoured, see §9): no Canonical `KNOWLEDGE`/`SKILL`/`DECISION` write, no
  GBrain install, no production write, no deploy, no permission/secret/credential change.

## 0. What this experiment is and is not

| | In scope | Out of scope |
|---|---|---|
| Does | Apply the 10-step loop to GBrain; separate source facts from AI inference; emit a learning ladder, self-tests, cheat sheet, skill/archive triage | Evaluating GBrain quality, running GBrain, benchmarking GBrain |
| Does | Test whether the *loop* produces a better personal artifact than plain reading | Recruiting participants or measuring delayed retention (that is `batch12-v3-learning-experiment.md`, arm N2) |
| Does | Produce a reusable report | Creating any canonical knowledge, skill, or decision |

This is a **single-operator, artifact-level** run of the method. It exercises steps 1–7 and 10 of
`T08` and leaves step 8/9 (spaced active test / Feynman-to-novice with a second human) as a
declared gap, because those require a second person and cannot be automated without destroying
the active-recall effect (`T08-X1`).

## 1. Step 1 — Multi-perspective collection (五视角 / STORM)

Five deliberately different vantage points were collected, and each source is labelled by its
credibility class. Dates are capture dates; the GBrain README was re-fetched during this run
(2026-10-08) and is the current first-party text.

| # | Perspective | Source anchor | Class |
|---|---|---|---|
| P1 | **Vendor self-description / product intent** | `SRC-GBRAIN-README` (github.com/garrytan/gbrain, README, re-read 2026-10-08) | primary, self-reported |
| P2 | **Architecture / schema docs** | `SRC-GBRAIN-SCHEMA` (`docs/GBRAIN_RECOMMENDED_SCHEMA.md`), `SRC-GBRAIN-ORIGIN` (`docs/ethos/ORIGIN.md`) | primary, self-reported |
| P3 | **Upstream pattern theory** | `SRC-KARPATHY-WIKI` (Karpathy "LLM Wiki" idea file, 2026-04) | primary, independent |
| P4 | **Third-party reading** | `SRC-KWIKI-DOCS` (ronancodes LLM-Wiki docs) | secondary |
| P5 | **Prior in-repo evidence** | `outputs/claim-evidence-matrix.md` (T06-C1..C6, T06-I1, T06-X1..X3), `outputs/distilled-knowledge.md` (KP-06), `outputs/batch12-canonical-inventory-v2.md` (K08/K16/S01) | internal, already triaged |

Deliberate gaps recorded up front: no GBrain install, no first-hand benchmark run, no access to
GBrain's private deployment. Every performance number therefore stays `SELF_REPORTED`.

## 2. Step 2 — Core contradiction map (核心矛盾)

The learning target is **not** "is GBrain good" but the design tension the architecture resolves.
Three contradictions, each stated as *traditional answer vs GBrain answer*:

| # | Contradiction | Traditional RAG / plain notes | GBrain's architectural answer |
|---|---|---|---|
| C1 | **Retrieve vs compile** | Re-derive meaning on every query by retrieving top-k chunks; the artifact never improves between queries | Maintain a persistent, compounding artifact (`gbrain think` synthesis + written pages) so query output feeds back into the store |
| C2 | **Stateless chunks vs sourced, correctable facts** | Chunks are opaque vectors; no notion of "this fact is wrong, withdraw it" | Explicit facts kept **with sources**, plus **corrections and withdrawal** as first-class operations |
| C3 | **Model-judgment vs deterministic structure** | Ranking/extraction is model-driven and hard to audit | Typed knowledge graph auto-links via entity extraction with **"zero LLM calls"** (self-reported), and a bounded set of retrieval mechanisms (keyword → hybrid → RRF → reranker) |

- `T06-I1` (reused): the reusable, source-backed principle is **compile-not-retrieve**: a
  three-layer store (raw sources / maintained wiki / schema) with four ops
  (`ingest → query → lint → promote`). GBrain is one implementation of that principle plus
  vendor claims.
- Boundary: C1/C2/C3 are **architectural distinctions**; whether they *cause* better retrieval is
  unproven here (no independent benchmark read → `T06-C4` stays `NOT_VERIFIED`).

## 3. Step 3 — One-minute brief (一分钟简报)

> GBrain is a persistent memory/brain layer that you attach to an existing agent over MCP. Its
> core bet is **"give the agent a memory you control"**: store explicit facts *with their
> sources*, allow **corrections and withdrawal**, and share durable preferences/facts across
> agents while keeping transient task state local. Retrieval is layered and opt-in: keyless
> keyword first, then semantic, then **hybrid = vector + keyword + RRF + source-tier boost +
> reranker**. On top sits a **synthesis layer** (`gbrain think`) that returns an **answer with
> citations plus an explicit gap analysis** rather than a list of chunks. Structure is provided by
> **schema packs** (a 15-type DRY/MECE taxonomy, user-authorable, seven-tier resolution), and by a
> **typed knowledge graph** whose local auto-linking claims to use **no LLM calls**. A 24/7
> **dream cycle / daemon** ingests, enriches, consolidates, and self-repairs citations overnight.
> **Skills live beside knowledge** (skillpacks; `skillopt` treats a `SKILL.md` as a trainable
> parameter gated by a benchmark). Access is a control plane: MCP server, OAuth scopes
> (`read`/`write`/`admin`/`agent`), visibility filters, and shared brains across agents. The
> reusable engineering ideas are: **compile-not-retrieve, sourced+withdrawable memory, typed
> schema as config, deterministic graph linking, and gap-aware synthesis.** The reusable
> *claims* to reject are the scale/quality multipliers, which remain self-reported.
>
> Read in one breath: *facts with provenance → typed schema → layered retrieval → synthesized,
> gap-flagged answer → skills beside knowledge → shared over MCP.*

## 4. Step 4 — Adversarial review: fact vs inference vs decision candidate (主动挑刺)

This section is the required three-layer separation. Nothing from `AI_ABSTRACTION` may be
promoted to `SOURCE_FACT`, and nothing in `DECISION_CANDIDATE` auto-executes.

### 4.1 SOURCE_FACT — stated by the repository / official docs (source-anchored)

| id | Fact (as stated) | Anchor | Evidence |
|---|---|---|---|
| SF-1 | GBrain repo exists; self-described as "Garry's Opinionated OpenClaw/Hermes Agent Brain"; MIT; built by Garry Tan | `SRC-GBRAIN-README`; `T06-C2` | primary, verified existence |
| SF-2 | Stores **explicit facts with their sources; supports corrections and withdrawal**; makes the same memory available across agents | `SRC-GBRAIN-README` (2026-10-08) | primary, self-reported |
| SF-3 | Retrieval ladder: keyless keyword → optional semantic → **hybrid = vector + keyword + RRF + source-tier boost + reranker** | `SRC-GBRAIN-README`; `T06-C3`/`T06-C5` | primary, self-reported |
| SF-4 | `gbrain think` = synthesis with citations **and an explicit "what the brain doesn't know" gap note**; `gbrain search` = raw top pages | `SRC-GBRAIN-README` | primary, self-reported |
| SF-5 | **Typed knowledge graph**; local page writes "extract supported references **without LLM calls** when auto-linking is enabled"; remote `put_page` does not extract inline (stdio/HTTP differ) | `SRC-GBRAIN-README`; `T06-C3` | primary, self-reported |
| SF-6 | **Schema packs**: `gbrain-base-v2` = 15-type DRY/MECE taxonomy (14 canonical + `note`); packs user-authorable; seven-tier resolution chain | `SRC-GBRAIN-README`; `SRC-GBRAIN-SCHEMA` | primary, self-reported |
| SF-7 | **24/7 daemon / dream cycle**: ingests, enriches, consolidates, fixes its own citations overnight; `155,795 pages, 24,589 people, 5,340 companies`, `66 cron jobs` | `SRC-GBRAIN-README`; `T06-C4` | primary; **numbers self-reported** |
| SF-8 | **Skills beside knowledge**: skillpacks; `skillopt` treats `SKILL.md` as a trainable parameter with benchmark-gated edits | `SRC-GBRAIN-README` | primary, self-reported (`T06-C6` for "self-evolving" wording) |
| SF-9 | **MCP control plane** with OAuth 2.1, scopes `read`/`write`/`admin`/`agent`, visibility filters (`visibility: private`), shared brain across agents | `SRC-GBRAIN-README` | primary, self-reported |
| SF-10 | **Supply-chain warning**: npm package `gbrain` is unrelated and can shadow the real binary; install only via `bun install -g github:garrytan/gbrain` or clone | `SRC-GBRAIN-README`; `T06-X3` | primary, verified warning |
| SF-11 | Upstream idea is Karpathy's **LLM Wiki** pattern: 3 layers (raw / wiki / schema) and 4 ops (ingest, query, lint, promote) | `SRC-KARPATHY-WIKI`; `T06-C1` | primary, independent |
| SF-12 | Headline benchmark numbers (e.g. graph adapter `P@5 0.3421, R@5 0.9791` vs `0.1917 / 0.6874` plain hybrid) come only from the vendor's own `gbrain-evals` | `SRC-GBRAIN-README`; `T06-C4` | primary, **self-reported** |

### 4.2 AI_ABSTRACTION — architecture understanding produced by this experiment (never evidence)

| id | Abstraction | Derived from | Confidence |
|---|---|---|---|
| AB-1 | GBrain is best modelled as **six planes**: (1) fact/memory plane, (2) retrieval plane, (3) synthesis plane, (4) structure plane (schema + graph), (5) upkeep plane (dream cycle), (6) interop/governance plane (MCP/skills) | SF-1..SF-9 | medium |
| AB-2 | The real differentiator over a chunk-RAG is **not** any single retriever but the **closed feedback loop**: synthesis output, citation repair and consolidation all write back into the store | SF-2, SF-4, SF-7; `T06-I1` | medium |
| AB-3 | The "**no LLM calls** for graph linking" is an *auditability/cost* property more than an accuracy property: deterministic extraction is easier to reproduce, but its recall depends entirely on the extractor's rules | SF-5 | low–medium |
| AB-4 | **Schema-as-config** (packs + seven-tier resolution) is the mechanism that lets one architecture serve personal, company and code brains without a fixed layout | SF-6 | medium |
| AB-5 | The **gap analysis** in synthesis ("what the brain doesn't know yet") is the piece that changes user behaviour: it converts a retriever into a *freshness/staleness auditor* | SF-4 | medium |
| AB-6 | GBrain's governance model (scopes `read`/`write`/`admin`/`agent`, visibility, shared vs local) is a **distribution** answer; it is orthogonal to the memory-quality answer | SF-2, SF-9 | medium |
| AB-7 | The 150K-page / P@5 numbers are a **scale story**, not evidence of a mechanism; nothing in the read material shows an independent reproduction | SF-7, SF-12 | high (that it's self-reported) |

### 4.3 DECISION_CANDIDATE — proposals only; `auto_executed: false`

| id | Candidate | Rationale | Gate |
|---|---|---|---|
| DC-1 | Adopt **source-anchored, correctable/withdrawable fact records** as a first-class memory primitive in Personal AI | Matches the existing `SOURCE_FACT` discipline but adds explicit **withdrawal** as a lifecycle op | human review |
| DC-2 | Add a **gap analysis / "what we don't know" field** to every synthesized answer | Cheap, observable, improves user trust; increment over pure retrieval | human review |
| DC-3 | Treat **schema as configurable packs with tiered resolution** rather than a fixed note taxonomy | Generalises the existing scoped-knowledge layering | human review |
| DC-4 | Prefer **deterministic, auditable entity linking** over an extra LLM pass for graph edges, where rules suffice | Reproducibility, lower cost; record recall limits | human review |
| DC-5 | Mirror the **compile-not-retrieve loop** (`ingest → query → lint → promote`) as an operational procedure | Already `T06-I1`; the loop is the transferable part | human review |
| DC-6 | **Do NOT** import GBrain as a second knowledge base. Study the architecture only. | Explicit task instruction; a second store duplicates governance and provenance | rejected-by-policy |

## 5. Step 5 — Learning ladder (学习阶梯)

Ordered from "must know" to "nice to know", each rung with a self-check.

| Rung | Level | Must be able to explain | Self-check |
|---|---|---|---|
| L1 | Vocabulary | fact-with-source, withdrawal, hybrid retrieval, RRF, schema pack, gap analysis | Can define all six without notes |
| L2 | Mechanism | why compile-not-retrieve ≠ per-query RAG; what `gbrain think` adds over `gbrain search` | Draw both flows from memory |
| L3 | Structure | the six planes and where schema packs / graph / dream cycle sit | Place each component on a blank diagram |
| L4 | Trade-off | accuracy vs auditability of deterministic graph linking; cost of enrichment vs keyless start | State one downside per mechanism |
| L5 | Transfer | map each GBrain mechanism to a Personal AI Canonical asset; name the increment | Pass §4 of the comparison file |
| L6 | Criticism | separate vendor metric from mechanism; name which numbers are unverifiable | Answer Q9–Q11 below |

## 6. Step 6 — Self-test (≥10 questions) with verified answers

Answers are verified against the anchors in §4. `[F]` = checkable against a source; `[I]` = an
inference this experiment draws (not a fact); `[T]` = trap/marketing-awareness item.

**Q1 [F].** What is the single-sentence design bet in GBrain's README?
**A1.** "Give the agent you already use a memory you control" — i.e. portable, explicit,
source-backed memory attached to the user's existing agent (`SRC-GBRAIN-README`).

**Q2 [F].** Name the four operations of the upstream LLM-Wiki pattern GBrain extends.
**A2.** `ingest → query → lint → promote` (with three layers: raw sources / wiki / schema);
`SRC-KARPATHY-WIKI`, `T06-C1`.

**Q3 [F].** Contrast `gbrain search` and `gbrain think`.
**A3.** `search` returns top retrieved pages by hybrid score (raw material, no answer call);
`think` runs the same retrieval then composes a **cited synthesis with an explicit gap analysis**
(`SRC-GBRAIN-README`).

**Q4 [F].** List the components combined in the hybrid retrieval score.
**A4.** vector + keyword + **RRF** + source-tier boost + reranker (`SRC-GBRAIN-README`; note
`T06-C5` marks exact RRF parameters as unread/unknown in the prior audit).

**Q5 [F].** What are the first-class lifecycle operations GBrain claims for stored facts?
**A5.** Explicit facts **with sources**, plus **corrections and withdrawal** (`SF-2`).

**Q6 [F].** How many types are in the default `gbrain-base-v2` schema pack, and how is it
resolved?
**A6.** A 15-type DRY/MECE taxonomy (14 canonical + `note`), resolved through a **seven-tier
chain** (call flag → env → per-source DB → brain-wide DB → `gbrain.yml` → `~/.gbrain/config.json`
→ default) (`SF-6`).

**Q7 [F].** What exactly does GBrain claim about the knowledge graph and LLM calls?
**A7.** Local page writes "extract supported references **without LLM calls** when auto-linking
is enabled"; remote `put_page` does **not** extract edges inline (stdio uses best-effort sweeps,
HTTP needs explicit maintenance / authorized `add_link`) (`SF-5`). *Note the scope limit — do not
generalise it to "the graph never uses an LLM".*

**Q8 [F].** Which supply-chain hazard does the repo itself flag?
**A8.** The npm package named `gbrain` is unrelated and can shadow the real binary; install only
from the GitHub repo via Bun/clone (`SF-10`, `T06-X3`).

**Q9 [T].** Are the headline figures (155,795 pages; 24,589 people; the `P@5 0.3421` graph result)
verifiable facts?
**A9.** No. They appear only in the vendor's README/`gbrain-evals`. They are `SELF_REPORTED` and
`NOT_VERIFIED` here (`T06-C4`, `SF-12`). Correct framing: "vendor-reported".

**Q10 [T].** Does the README claim "self-evolving skills" that improve themselves autonomously?
**A10.** Be careful. The repo describes **skillpacks** and `skillopt`, which treats `SKILL.md` as a
*benchmark-gated trainable parameter* with a human keeping only higher-scoring edits. That is
**measured, gated optimization**, not autonomous unverified self-evolution; prior audit marked the
"self-evolving" wording `NOT_VERIFIED` (`T06-C6`).

**Q11 [I].** Why is "zero LLM calls for graph linking" only a *partial* advantage?
**A11.** Inference (`AB-3`): it helps reproducibility and cost, but accuracy/recall depends wholly
on the extraction rules; the README itself notes remote paths do **not** extract inline, so graph
freshness varies by transport (`SF-5`).

**Q12 [I].** Which single element most changes user behaviour, and why?
**A12.** Inference (`AB-5`): the **gap analysis** — it tells the user what is stale, uncited,
contradicted, or missing, converting retrieval into a freshness/staleness audit.

**Q13 [F/I].** Name three mechanisms that are genuinely transferable to Personal AI and one that
is not.
**A13.** Transferable: source-anchored+withdrawable facts (`DC-1`), gap analysis (`DC-2`),
schema-as-config (`DC-3`), deterministic linking (`DC-4`), compile loop (`DC-5`). Not
transferable, by policy: importing GBrain as a second knowledge base (`DC-6`).

**Q14 [T].** A reader says "GBrain proved a 31.4-point P@5 lift, so its graph is objectively
better." What is the error?
**A14.** It treats a vendor self-reported number as independent evidence and generalises a
system-level result to a graph-only claim. The README itself phrases it as a *whole-system*
result "not a graph-only lift or a general guarantee" (`SF-12`, `T06-C4`).

## 7. Step 7 — One-page cheat sheet (一页速查表)

```
GBRAIN IN ONE PAGE
Purpose   : give your existing agent a portable, source-backed, shared memory it controls
Primitive : explicit FACT + SOURCE, correctable, withdrawable; durable facts shared, task state local
Retrieval : keyword (keyless) -> semantic -> HYBRID(vector + keyword + RRF + source-tier + reranker)
Synthesis : think = same retrieval + cited answer + GAP ANALYSIS ("what the brain doesn't know")
Structure : SCHEMA PACKS (base-v2 = 15 types; 7-tier resolution) + TYPED GRAPH (local auto-link, no LLM calls)
Upkeep    : 24/7 dream cycle: ingest -> enrich -> consolidate -> citation self-repair
Skills    : skillpacks beside knowledge; skillopt = benchmark-gated edits to SKILL.md
Interop   : MCP server; OAuth scopes read/write/admin/agent; visibility filters; shared brains
Upstream  : Karpathy LLM Wiki: 3 layers (raw/wiki/schema), 4 ops (ingest/query/lint/promote)
Reject    : scale + P@5 multipliers (SELF_REPORTED); "autonomous self-evolution" wording
Reuse     : compile-not-retrieve; sourced+withdrawable facts; gap analysis; schema-as-config;
            deterministic linking; gap-aware synthesis
Do NOT    : install GBrain or make it a second knowledge base (policy)
```

## 8. Step 10 — Skill candidates vs archive (哪些值得形成 Skill / 哪些应归档)

### 8.1 Worth forming as **Skill candidates** (reusable procedure, not vendor claims)

| Candidate | Working name | Why it is a skill (procedure) | Gate / preconditions |
|---|---|---|---|
| SC-1 | `compile-not-retrieve-knowledge-loop` | The `ingest → query → lint → promote` loop with human lint gate is operational and already theorised (`T06-I1`, KP-06) | Must not duplicate existing `knowledge-distillation-canonical-promotion` (S01); full-text dedup still blocked |
| SC-2 | `gap-aware-synthesis` | An explicit "what we don't know / stale / uncited / contradicted" block is a concrete, testable output contract | Needs a defined schema + evaluation of false gaps |
| SC-3 | `source-anchored-fact-lifecycle` | add facts with source + **correct/withdraw** as first-class ops | Overlaps existing SOURCE_FACT discipline; increment = withdrawal lifecycle |
| SC-4 | `schema-pack-as-config` | Detect → suggest → review-candidates → use; a bounded human-gated procedure | Depends on a taxonomy decision that is not yet made |

Each candidate above is a **procedure**, not the product. None is created in this task.

### 8.2 Should be **ARCHIVED** (not promoted)

| Item | Why archive |
|---|---|
| 155,795 pages / 24,589 people / 5,340 companies / 66 cron jobs | Vendor self-reported scale; not independently verifiable (`T06-C4`) |
| `P@5 0.3421 / R@5 0.9791` graph benchmark | Vendor `gbrain-evals`, no independent reproduction (`SF-12`) |
| "self-evolving skills" wording | Overclaim relative to the documented benchmark-gated `skillopt` (`T06-C6`) |
| "10x"-style product framing / recommendation to adopt GBrain | Out of scope: this is an architecture study, not a product endorsement |
| Any instruction to install GBrain or mirror it as a second store | Explicitly forbidden (`DC-6`) |

### 8.3 Already covered by existing Canonical (do not re-create)

K08 `knowledge-obsidian-agent-interface-capabilities`, K16
`knowledge-architecture-scoped-knowledge-layers`, S01 `knowledge-distillation-canonical-promotion`,
K10 `knowledge-evidence-vs-expected-value`, K13 `knowledge-agent-permission-action-governance`
(per `batch12-canonical-inventory-v2.md` §5). Full-text dedup remains
`FULL_CANONICAL_DEDUP_BLOCKED`, so this is title-level screening only.

## 9. Method-effectiveness self-assessment (honest, unfaked)

- The 10-step loop was **useful** for compression (steps 2/3/7 forced the six-plane model and the
  one-minute brief) and for **bias control** (step 4 cleanly quarantined vendor metrics before they
  could leak into conclusions).
- The loop did **not** measure learning outcomes. There are **no measured gains** here, and none is
  claimed (`T08-X2`). Steps 8–9 (spaced active recall + Feynman to a second human) were **not**
  executed; they cannot be automated without removing the effect (`T08-X1`).
- Therefore this run supports, at most, the claim **"the method produces a reusable, well-labelled
  artifact"** — *not* "the method improves retention." The quantitative test is pre-registered,
  unexecuted, in `outputs/batch12-v3-learning-experiment.md`.

## 10. Read-only guarantees (hard boundary)

- **No** `KNOWLEDGE`, `SKILL`, or `DECISION` was created, modified, promoted, or archived.
- **No** GBrain package was installed, cloned, or executed; **no** second knowledge base was added.
- **No** production write, deployment, binding, schema migration, secret, credential, or permission
  change was performed.
- **No** file outside the two allow-listed `outputs/gbrain-*.md` paths was modified by this task.
- The only network action was read-only retrieval of GBrain's public README to refresh `P1`.
