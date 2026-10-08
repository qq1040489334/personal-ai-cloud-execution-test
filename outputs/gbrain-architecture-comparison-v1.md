# GBrain Architecture Comparison V1 — GBrain vs Personal AI

- Task: `cf-e99d73352c64` — `GBrain_ARCHITECTURE_LEARNING_EXPERIMENT_V1`
- Project: `personal-ai-knowledge-triage`; Risk: `LOW`; Mode: **READONLY / RESEARCH ONLY**
- Companion to: `outputs/gbrain-learning-experiment-v1.md`
- Purpose: extract GBrain's **core architecture model** and diff it against the **existing Personal
  AI architecture** using the already-audited Canonical inventory
  (`outputs/batch12-canonical-inventory-v2.md`, 18 KNOWLEDGE + 2 SKILL + 0 DECISION, 2026-10-08).
- Scope guard: title/metadata-level comparison only. The prior audit is
  `FULL_CANONICAL_DEDUP_BLOCKED` (19/20 asset bodies unread), so **no** row below may be claimed
  as a full-text semantic dedup. This was explicitly forbidden by the parent audit.
- Hard boundary: this is an architecture study. GBrain is **not** proposed as a second knowledge
  base and is not installed (`DECISION_CANDIDATE DC-6`, rejected-by-policy).

## 1. GBrain core architecture model (six planes)

Derived from `SOURCE_FACT`s SF-1..SF-9 in the companion file; each plane cites its anchor.

```
            +--------------------------------------------------------------+
            |  P6  INTEROP / GOVERNANCE PLANE                              |
            |  MCP server (stdio + HTTP/OAuth 2.1), scopes read/write/     |
            |  admin/agent, visibility filters, shared brains across agents|
            |  (SF-9)                                                      |
            +--------------------------------------------------------------+
                        ^ consumes memory via                         | publishes
                        |                                             v
+----------------------+----------------------+   +-------------------------------+
| P3 SYNTHESIS PLANE                          |   | P4 STRUCTURE PLANE            |
| `think`: retrieval + cited answer + GAP     |<--| schema packs (base-v2 = 15    |
| ANALYSIS ("what the brain doesn't know")    |   | types; 7-tier resolution);    |
| (SF-4)                                      |   | typed graph, local auto-link  |
+----------------------+----------------------+   | "without LLM calls" (SF-5,6) |
                       ^                          +-------------------------------+
                       | top-k / hybrid                    ^ indexes into
                       |                                   |
+----------------------+----------------------+   +-------+-----------------------+
| P2 RETRIEVAL PLANE                          |   | P5 UPKEEP PLANE               |
| keyless keyword -> semantic -> HYBRID       |   | 24/7 daemon / dream cycle:    |
| (vector + keyword + RRF + source-tier +     |   | ingest -> enrich ->           |
|  reranker) (SF-3)                           |   | consolidate -> citation       |
+----------------------+----------------------+   | self-repair (SF-7)            |
                       ^                          +-------------------------------+
                       |
+----------------------+---------------------------------------------------+
| P1 FACT / MEMORY PLANE                                                   |
| explicit FACT + SOURCE; correctable; withdrawable; durable facts shared,  |
| transient task/harness state local (SF-2)                                |
+--------------------------------------------------------------------------+
```

| Plane | Mechanism | What problem it solves | Maturity signal in sources |
|---|---|---|---|
| P1 Fact/memory | explicit facts + source, corrections, withdrawal | provenance and error lifecycle | stated in first-party README (SF-2) |
| P2 Retrieval | keyword → semantic → hybrid (RRF + source-tier + reranker) | recall + ranking | described; exact params `UNKNOWN` (`T06-C5`) |
| P3 Synthesis | cited answer + **gap analysis** | turns retrieval into an answer + freshness audit | first-party README (SF-4) |
| P4 Structure | schema packs + typed graph (deterministic linking) | generality + auditability | first-party README (SF-5, SF-6) |
| P5 Upkeep | dream cycle / cron enrichment + citation self-repair | keeps the brain fresh without a live agent | first-party README (SF-7) |
| P6 Interop/Governance | MCP server, OAuth scopes, visibility, shared brains | multi-agent distribution + access control | first-party README (SF-9) |

The distinguishing design bet is the **closed feedback loop** across P3→P1/P4/P5: synthesis
output, graph edges, citation repairs and consolidation all write back into the same store
(`AI_ABSTRACTION AB-2`). Plain chunk-RAG has no such write-back.

## 2. The existing Personal AI architecture (diff baseline)

Baseline is the audited Canonical inventory plus the active in-repo architecture documents. Only
title-level knowledge is claimed for 19/20 assets.

| Ref | Asset (id / doc) | Domain it covers |
|---|---|---|
| K02 | `knowledge-ai-intent-clarification-pattern` | 反向提问 / intent clarification |
| K08 | `knowledge-obsidian-agent-interface-capabilities` | Obsidian interface to knowledge |
| K10 | `knowledge-evidence-vs-expected-value` | evidence strength vs action priority |
| K13 | `knowledge-agent-permission-action-governance` | permission & action governance (full text) |
| K16 | `knowledge-architecture-scoped-knowledge-layers` | layered/scoped knowledge |
| K15 | `knowledge-workflow-auditable-task-contract` | auditable task contract |
| K17 | `knowledge-architecture-local-execution-shared-intelligence` | local execution / shared intelligence |
| S01 | `knowledge-distillation-canonical-promotion` | knowledge distillation → Canonical promotion |
| S02 | `skill:computer_use_guard` | computer-use guard |
| L1 | `KNOWLEDGE_TRIAGE_LAYER_V1.md` | `SOURCE_FACT` / `AI_ABSTRACTION` / `DECISION_CANDIDATE` triage; evidence levels A/B/C/UNKNOWN; Golden gate |
| L2 | `HERMES_REALITY_DAILY_SYNC_BINDING_V0.1.md`, `REALITY_*` docs | daily reality capture → canonical pipeline |

## 3. Difference table — GBrain mechanism vs Personal AI

Legend for "Verdict": `REAL_INCREMENT` (adds a capability Personal AI does not have) ·
`PARTIAL_INCREMENT` (same goal, missing a property) · `ALREADY_COVERED` (Canonical already does it)
· `REPACKAGE` (new words, same mechanism) · `ARCHIVE` (vendor metric / not architecture).

| # | GBrain mechanism | Closest Personal AI asset | Verdict | Why (increment or overlap) |
|---|---|---|---|---|
| 1 | Fact + source + **corrections + withdrawal** lifecycle (SF-2) | L1 `SOURCE_FACT` requires locator/provenance; K10 evidence-vs-value | **PARTIAL_INCREMENT** | Sourcing already exists; **withdrawal/retraction as a first-class op** is the genuine gap |
| 2 | **Gap analysis** in synthesis: stale/uncited/contradicted/unknown (SF-4) | L1 has `missing_information`, but only at capture time; K10 | **REAL_INCREMENT** | No existing asset emits a per-answer "what we don't know" contract |
| 3 | Hybrid retrieval = vector + keyword + **RRF** + source-tier + reranker (SF-3) | K16 scoped layers; index-as-access | **PARTIAL_INCREMENT** | Scoping exists; the explicit **rank-fusion + source-tier** recipe is an implementation detail not evidenced in Canonical |
| 4 | **Schema packs** + seven-tier resolution, user-authorable (SF-6) | K16 `knowledge-architecture-scoped-knowledge-layers` | **PARTIAL_INCREMENT** | Layering overlaps; **user-authored schema-as-config with tiered resolution** is more general |
| 5 | **Typed graph**, deterministic local auto-linking "without LLM calls" (SF-5) | K06 structured-data/low-code; K16 | **REAL_INCREMENT** | No Canonical asset evidences an entity/relationship graph with deterministic extraction |
| 6 | **Compile-not-retrieve loop** `ingest→query→lint→promote` (T06-I1) | S01 distillation→promotion | **REPACKAGE (mostly covered)** | Same lifecycle; GBrain's specific value = the explicit **query→write-back** compounding step |
| 7 | 24/7 **dream cycle** enrichment + citation self-repair (SF-7) | L2 `REALITY_*` daily sync pipeline; S01 | **PARTIAL_INCREMENT** | A daily pipeline exists; **citation self-repair** as an automated maintenance op is not evidenced |
| 8 | **Skills beside knowledge**; `skillopt` benchmark-gated `SKILL.md` edits (SF-8) | S01 promotion; K13 governance | **PARTIAL_INCREMENT** | Skill catalog exists; **benchmark-gated optimization of a skill file** is a distinct procedure |
| 9 | MCP control plane + OAuth scopes `read/write/admin/agent` + visibility (SF-9) | K13 permission/action governance (full text) | **ALREADY_COVERED** | Scoped, auditable permission governance is exactly K13's domain; do not duplicate |
| 10 | Shared durable facts across agents; transient state local (SF-2, SF-9) | K17 local execution / shared intelligence | **ALREADY_COVERED** | The shared-vs-local split is K17's core distinction |
| 11 | Fours ops on raw/wiki/schema layers (Karpathy) (`T06-C1`) | K16 layers + K08 Obsidian interface | **ALREADY_COVERED** | Layered knowledge + markdown/IDE interface already canonical |
| 12 | Scale/quality headline numbers (155K pages, P@5) (SF-7, SF-12) | — | **ARCHIVE** | Vendor self-reported; not architecture; no independent reproduction |
| 13 | "Self-evolving skills" wording (SF-8) | — | **ARCHIVE** | Overclaim vs documented benchmark-gated `skillopt` (`T06-C6`) |
| 14 | Recommendation to adopt GBrain as a second brain | — | **ARCHIVE / REJECT** | Forbidden by task policy; duplicates K13/K16/S01 governance |

### 3.1 Roll-up

| Bucket | Count | Items |
|---|---|---|
| `REAL_INCREMENT` | 2 | gap analysis (#2), typed deterministic graph (#5) |
| `PARTIAL_INCREMENT` | 5 | fact withdrawal (#1), hybrid RRF recipe (#3), schema packs (#4), citation self-repair (#7), skillopt (#8) |
| `REPACKAGE` | 1 | compile-not-retrieve loop (#6; S01 already covers most) |
| `ALREADY_COVERED` | 3 | permission governance (#9), shared/local split (#10), layered wiki (#11) |
| `ARCHIVE` | 3 | vendor metrics (#12), self-evolution wording (#13), second-brain adoption (#14) |

## 4. Direct answers to the required questions

**Q-A. Which GBrain mechanisms give Personal AI a real increment?**
Only two are unambiguously new: (1) the **gap analysis** in synthesis — a per-answer statement of
stale/uncited/contradicted/unknown (`#2`); and (2) a **typed knowledge graph with deterministic,
auditable entity linking** (`#5`). Five more are partial increments: fact **withdrawal** (`#1`),
the explicit **hybrid RRF + source-tier** recipe (`#3`), **schema-as-config** (`#4`), automated
**citation self-repair** (`#7`), and **benchmark-gated skill optimization** (`#8`).

**Q-B. Which are already covered by existing Canonical?**
Permission/action governance (K13) covers MCP scopes/visibility (`#9`); the shared-vs-local
execution split (K17) covers "shared durable facts, local task state" (`#10`); layered knowledge
(K16) + Obsidian interface (K08) cover the Karpathy raw/wiki/schema layers (`#11`); distillation →
promotion (S01) substantially covers the compile loop (`#6`, repackage).

**Q-C. Which are merely repackaging?**
The **compile-not-retrieve loop** (`#6`) is largely a rename of the existing distillation/promotion
lifecycle; its only genuinely new element is the explicit *query output written back as a page*
compounding step. The layered-wiki story (`#11`) is repackaging of K16+K08.

**Q-D. What must not be imported?**
The **scale/quality multipliers** (`#12`), the **"self-evolving skills"** wording (`#13`), and any
**adoption of GBrain as a second knowledge base** (`#14`).

## 5. Decision candidates (proposals only, `auto_executed: false`)

| id | Proposal | Evidence | Gate |
|---|---|---|---|
| DC-1 | Add **fact withdrawal/retraction** to the existing SOURCE_FACT lifecycle (not a new store) | difference table #1; L1 | human review |
| DC-2 | Add a mandatory **gap-analysis block** to any synthesized answer/record | #2 | human review |
| DC-3 | Make the knowledge **schema pack-configurable** with tiered resolution, on top of existing scoped layers | #4; K16 | human review |
| DC-4 | Add an **auditable entity-relationship graph** with deterministic linking; document recall limits | #5 | human review |
| DC-5 | Encode the **compile loop** as a procedure, checking against S01 to avoid duplication | #6; T06-I1 | human review + blocked full-text dedup |
| DC-6 | **Do not** install GBrain or stand up a second knowledge base | task policy | rejected-by-policy |
| DC-7 | Keep all vendor **metrics and self-evolution claims archived** | #12, #13; T06-C4/C6 | human review |

## 6. Skill-candidate vs archive summary (architecture view)

- **Skill candidates** (procedures to *learn from* GBrain, not copy the product):
  `compile-not-retrieve-knowledge-loop` (dedup vs S01 first), `gap-aware-synthesis`,
  `source-anchored-fact-lifecycle` (adds withdrawal), `schema-pack-as-config`.
- **Archive**: vendor scale/P@5 numbers, "self-evolving skills" wording, GBrain-as-second-brain.

## 7. Honest limitations and boundary

- Comparison is **title/metadata-level** for 19/20 Canonical assets; the source audit is
  `FULL_CANONICAL_DEDUP_BLOCKED`. Any `REAL_INCREMENT` row is provisional pending body-level review.
- GBrain evidence is **first-party and self-reported** except the upstream Karpathy pattern and the
  repo's own supply-chain warning; no independent benchmark was read.
- No GBrain install, no execution, no Canonical write, no production write, no deploy, no
  permission/secret change. Only the two allow-listed `outputs/gbrain-*.md` files were created.
