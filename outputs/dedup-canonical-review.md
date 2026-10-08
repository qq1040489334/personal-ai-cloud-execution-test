# dedup-canonical-review — KNOWLEDGE_BATCH_12_EVIDENCE_ENRICHMENT_V1

- Task `cf-356d867fb663`; READONLY/RESEARCH ONLY.
- This file has two independent parts: **(A) cross-candidate deduplication** (by mechanism/verifiable
  behaviour, not by video title) and **(B) read-only comparison against Cloudflare Canonical**.

## A. Cross-candidate deduplication (mechanism-based)

Deduplication key = the *reusable mechanism or verifiable behaviour*, not the topic name. Candidates that
share a mechanism are grouped; overlaps with existing principles are noted in part B.

### A.1 Mechanism clusters

| Cluster | Shared mechanism | Candidates | Decision |
|---|---|---|---|
| M1 — Authorized agentic execution against external surfaces | An agent takes multi-step actions on a third-party surface, bounded by authorization/scope/policy | T1 (phone apps), T10 (chat + cloud computer), T12 (browser), T7 (calendar/email execution) | Single reference cluster "gated external execution"; keep one boundary statement, not four |
| M2 — Compile-and-maintain knowledge instead of per-query retrieval | Ingest → synthesize → maintain linked markdown; query files results back | T6 (LLM Wiki/GBrain), T7 (Living Memory as markdown), T5-adjacent (habit design not knowledge) | Merge T6+T7 memory layer into one "persistent compiled memory" mechanism; T5 not in this cluster |
| M3 — Identity/system/friction behavior design | Change environment and identity rather than rely on willpower | T5 (Atomic Habits), partially T8 (learning-loop discipline) | T5 merges with existing system-over-willpower; T8 keeps its own learning-loop entry |
| M4 — Verification-before-trust / evidence gates | Trust output only after independent verification; provenance matters | T3 (AI code security), T4 (skill provenance), T6 (citation/lint), T12 (skill provenance), T1/T10 (confirmed actions) | Keep a single cross-cutting "verify provenance and output" principle; use as a dedup filter |
| M5 — Learning transfer / structured study | Abstraction + varied practice + active recall drive transfer | T8 (10-step method), T11 (transfer theory) | Merge into one "structured learning & transfer" mechanism; T8 contributes procedure, T11 contributes the theory/boundary |
| M6 — Services/AI macro narrative | Macro statistics + policy + speculation | T9 (+ T3 for AI labor) | Keep only the official-statistics subset; drop speculative narratives |

### A.2 Pairwise duplicate findings

| Pair | Duplicate element | Distinct increment | Resolution |
|---|---|---|---|
| T1 ↔ T10 ↔ T12 ↔ T7 | All are "agent acts for the user on an external surface with confirmation" | T1 = OS/GUI surface; T10 = chat form factor + liability; T12 = browser tooling; T7 = personal memory/briefs | One shared boundary; four reference examples |
| T6 ↔ T7 | Persistent personal memory as markdown/structured store | T6 = knowledge-wiki compile loop + retrieval; T7 = user-context memory + proactive briefs | MERGE the "persistent memory" claim; KEEP T6's ingest/lint loop and T7's proactive-confirmation loop |
| T8 ↔ T11 | Structured learning and transfer | T8 = operational 10-step procedure; T11 = the transfer/cognitive-flexibility theory and far-transfer boundary | MERGE conceptually; keep both as facets of one principle |
| T8 ↔ T3 (security) | n/a | — | no dedup |
| T5 ↔ existing SYSTEM_OVER_WILLPOWER | System beats willpower | Identity layer + 4-stage design | MERGE system part, KEEP identity/friction |
| T9 ↔ T3 | AI labor/economic impact | T9 = macro services data; T3 = code security | Keep separate; cross-link only |
| T12 ↔ T4 | Third-party executable skill provenance | T12 = browser skill (open-source upstream); T4 = MATLAB skill (repo not found) | One provenance principle; T4 becomes the negative example |
| T2 ↔ T1/T10/T12 | Authorization/scope boundary | T2 = bug bounty legal scope; M4 = general verification | Cross-link under M4 |

### A.3 Items removed by dedup / de-noising

- Duplicate AI-capability hype statements repeated across T1/T6/T7/T10 (e.g., "AGI/Jarvis" framing) — **removed** (no evidence).
- T3's headline multiplier framing and T8's "10x"/"25%" — **removed** (self-reported/unverifiable).
- T9's "irreversible cognitive decline" and "celebrity-children device limits" — **removed** (no source).
- T6's vendor page/scale metrics — **removed as facts**, retained only as labelled SELF_REPORTED.
- T4's named repo — **removed** (not found).

## B. Read-only Canonical comparison

### B.1 Access result

**`CANONICAL_READ_UNAVAILABLE`.**

- No Cloudflare Canonical read connector, credential, account, or `cloud_asset_read_get_asset` tool was available
  in this execution environment. `env` contained no `cloudflare`/`canonical`/asset token variables; the repo's
  `scripts/cloud_asset_obsidian_mirror.py` **consumes** an asset record from stdin but holds no credentials and
  has no read path to Cloudflare.
- The task's Canonical assets are described **locally** (KNOWLEDGE: the local-execution/shared-intelligence
  architecture note, the scoped-knowledge layering note, the auditable AI task contract note) via
  `docs/cloudflare-obsidian-mirror.md` and `KNOWLEDGE_TRIAGE_LAYER_V1.md`. The task also names a
  `SYSTEM_OVER_WILLPOWER` principle. These are treated as a **local documented proxy**, not as verified live
  Canonical records.
- **No claim is made that the live Cloudflare Canonical store was read, queried, or compared.** Doing so would
  require the read-only connector and appropriate permission, which is out of scope for this LOW-risk task.

### B.2 Read-only comparison against the documented local proxy (explicitly provisional)

| Candidate mechanism | Likely Canonical proximity (proxy) | Classification | Confidence |
|---|---|---|---|
| M2 compiled knowledge wiki (T6/T7 memory) | Scoped-knowledge layering: "indexes are access mechanisms rather than additional sources of truth"; "review before promotion" | **DUPLICATE (high overlap)** — the compile loop is an operationalization, not a new principle | Medium (proxy only) |
| M4 verification-before-trust (T1/T3/T4/T10/T12) | Auditable AI task contract: "completion is not inferred from an Agent narrative alone"; verify outputs/read-back | **DUPLICATE (high overlap)** — T3/T4/T12 add concrete verification techniques | Medium (proxy only) |
| M1 gated external execution (T1/T7/T10/T12) | Local-execution / shared-intelligence architecture: local execution is appropriate when an environment requires it, not universally mandatory | **PARTIAL overlap / INCREMENT** — adds external *surface* and *authorization* dimensions | Medium (proxy only) |
| M3 behavior design (T5) | `SYSTEM_OVER_WILLPOWER` principle (named in task) | **DUPLICATE (system part) / INCREMENT (identity layer + friction design + 4-stage checklist)** | Medium (proxy only) |
| M5 learning & transfer (T8/T11) | No matching Canonical asset identified in the local proxy | **INCREMENT (new domain)** — structured learning + transfer boundary | Low–Medium (proxy only) |
| M6 services/AI macro (T9) | No matching Canonical asset identified in the local proxy | **INCREMENT (data-hygiene rule)** but most narrative claims unevidenced | Low (proxy only) |

### B.3 Explicit uncertainty statement

Because live Canonical was **not** read, the comparison above is **provisional** and cannot be used to justify
promotion. Per the task contract, an unconfirmed/incomplete dedup result is a **blocker**, not an approval.
The local proxy is narrow: it documents only three KNOWLEDGE notes (plus the triage layer and status contracts),
so absence of a match for M5/M6 in the proxy does **not** prove novelty in the real Canonical store.

### B.4 What would be required to complete part B

1. An authorized, read-only Cloudflare Canonical read (the existing Cloud Asset Read connector) for the four
   named assets, especially KNOWLEDGE, SKILL and DECISION.
2. Passing the exact returned records to a read-only comparator (no write) keyed by mechanism, not title.
3. Re-running this dedup with the real corpus before any KEEP/MERGE decision is finalized.
