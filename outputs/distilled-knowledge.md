# distilled-knowledge — KNOWLEDGE_BATCH_12_EVIDENCE_ENRICHMENT_V1

- Task `cf-356d867fb663`; READONLY/RESEARCH ONLY; no promotion executed.
- Every retained knowledge point (KP) lists: **source**, **boundary of applicability**, **counterexample/risk**,
  **increment over the known Canonical assets**, and a **minimal falsification experiment**.
- "Canonical" here means the Cloudflare Canonical assets described by local repository artifacts
  (`KNOWLEDGE_TRIAGE_LAYER_V1.md`, `docs/cloudflare-obsidian-mirror.md`): a *local-execution / shared-intelligence
  architecture* principle, a *scoped-knowledge layering* principle (indexes are access mechanisms, review before
  promotion), and an *auditable AI task contract* principle. Cloudflare itself was **not read** (see
  `CANONICAL_READ_UNAVAILABLE`); increment claims below are relative to that documented local proxy, not to a
  verified live Canonical record.
- No unverified marketing metric is retained as a fact. Metrics that are self-reported are labelled
  `SELF_REPORTED` and are not distilled into principles.

## Retained knowledge points

### KP-01 — System-integrated phone-app automation is a policy-gated execution surface
- **Source**: SRC-HW-01 (Huawei 小艺帮帮忙 support page); SRC-ITHOME; SRC-DONEWS.
- **Distilled principle**: A first-party OS agent can drive third-party apps in the background and can be taught
  skills by demonstration; the capability is bounded by OS version, device family, network, non-lock-screen, and
  app-platform policy.
- **Boundary**: Huawei devices only; agent was a 众测 exploratory feature in HarmonyOS 6.0 and Huawei states it is
  **not offered on new HarmonyOS 7.0 models**; some apps (social/chat, non-native) unsupported.
- **Counterexample / risk**: App-rule/account penalties and screen-share side-effects; no lock-screen execution;
  future availability NOT guaranteed.
- **Increment over Canonical**: Adds a concrete *external execution surface* example; Canonical's local-execution
  principle is about architecture choice, not vendor GUI agents. No conflict.
- **Minimal falsification**: On a supported Huawei device with HarmonyOS 6.x, issue a multi-step background
  command and record whether it completes without foregrounding and without a lock screen. Re-check availability
  on a HarmonyOS 7.0 new model.

### KP-02 — Authorized-bug-bounty value comes from scope + quality gates, not volume
- **Source**: SRC-BUTIAN-FAQ; SRC-BUTIAN-NEW; SRC-BUTIAN-ZC; SRC-VULBOX (AI-report notice title).
- **Distilled principle**: Legitimate white-hat income is gated by an explicit authorized scope, an NDA, a
  time-boxed test window, reputation/accuracy scoring, and a pending-submission cap.
- **Boundary**: Only within a vendor's published SRC scope; crowdtest requires elite eligibility; prohibited
  methods (automated scanning, DoS, social engineering, privilege escalation) are disqualifying.
- **Counterexample / risk**: Mass AI-generated reports are now an explicit compliance concern at a peer platform;
  "passive beginner income" framing is contradicted by the reputation and accuracy rules.
- **Increment over Canonical**: Reinforces the *authorization/audit* principle with an external compliance case;
  the increment is the concrete anti-pattern (AI spam) and the reputation gate.
- **Minimal falsification**: Try to submit an AI-generated, scope-compliant report on a public SRC and record the
  accept/reject and reputation effect. Any mass submission should fail.

### KP-03 — "Vibe coding" is a prototype pattern with a measured production security gap
- **Source**: SRC-KARPATHY-VIBE; SRC-ARXIV-VIBE; SRC-VERACODE; SRC-VERACODE2; SRC-CSA; SRC-CODEQL-24.
- **Distilled principle**: Give in to the model for throwaway prototypes, but production use requires independent
  verification because LLM output is syntactically strong and security-weak.
- **Boundary**: Karpathy explicitly scoped it to "throwaway weekend projects"; security pass rates cluster ~55–56%
  (≈44–45% of tasks introduce a known vuln), vary sharply by language/CWE (Java worst; XSS/log-injection worst).
- **Counterexample / risk**: "Accept All / don't read diffs" removes the human review that catches the ~1-in-3 to
  1-in-2 insecure outputs; false confidence is itself measured (Snyk: ~80% of devs believe AI code is more secure).
- **Increment over Canonical**: Adds a *verification-before-trust* requirement with external evidence; consistent
  with the auditable-task-contract principle.
- **Minimal falsification**: For a fixed set of tasks, run generated code through SAST with and without security
  prompting and compare fail rates; the claim fails if unprompted pass rate rises near syntax pass rate.

### KP-04 — Verify a third-party "skill" by its upstream origin, license and execution reach
- **Source**: SRC-GH-API-MATLAB; SRC-GH-Samuel; SRC-MATHWORKS; SRC-MW-PLAY.
- **Distilled principle**: A named skill repo is a supply-chain artifact: confirm the repo exists, read its license,
  and know what its installed code can touch before using it.
- **Boundary**: `SamuelQQ/matlab-skills` was **not found**; the verifiable MATLAB-skill ecosystem is MathWorks'
  official toolkit plus third-party MIT/Apache repos of varying provenance.
- **Counterexample / risk**: A skill that installs an MCP server into a live MATLAB session can read/write the
  user's files (e.g., sales data). Unverified repos have unknown commit history.
- **Increment over Canonical**: Concretizes the asset-provenance principle for *executable skills*, including
  permission reach, not just textual citation.
- **Minimal falsification**: `GET /repos/<owner>/<name>` for the claimed repo; if 404, the claim is false. Then
  inspect SKILL.md tools/permissions and license.

### KP-05 — Identity-based framing is the increment over a system-over-willpower principle
- **Source**: SRC-JC-IDENTITY; SRC-JC-3STEPS; SRC-JC-ATOMIC.
- **Distilled principle**: Design behavior change at three layers — identity ("who am I"), process (habit loop:
  cue/craving/response/reward), and environment/friction — rather than relying on willpower.
- **Boundary**: Behavioral popular science; the "system > willpower" thesis overlaps an existing Canonical
  principle and is **not** new. The new parts are the identity layer and the four-stage design checklist.
- **Counterexample / risk**: Identity statements can become rigid or self-reinforcing; environment/friction
  design can be coercive if applied to others. Habit literature is largely self-report.
- **Increment over Canonical**: The **identity** and **four-law/inversion** operationalization. Dedup: MERGE the
  system-over-willpower part, KEEP the identity + friction-design part.
- **Minimal falsification**: A/B a small habit with an identity statement + tiny-win versus a willpower-only
  reminder, and measure adherence over several weeks.

### KP-06 — Compile knowledge into a maintained wiki; do not re-derive it every query
- **Source**: SRC-KARPATHY-WIKI; SRC-GBRAIN-README; SRC-GBRAIN-SCHEMA; SRC-GBRAIN-ORIGIN.
- **Distilled principle**: Keep three layers (immutable raw sources, LLM-maintained markdown wiki, schema/config)
  and four operations (ingest, query, lint, promote); file good query outputs back as pages so knowledge compounds.
- **Boundary**: Karpathy says `index.md` suffices at ~100 sources / hundreds of pages; add search/hybrid retrieval
  only as scale demands. GBrain-specific metrics and "self-evolving skills" are SELF_REPORTED and excluded.
- **Counterexample / risk**: Maintenance/consistency drift, over-association and source bias (STORM), and citation
  errors; a wiki is only as good as its lint/promote discipline. GBrain also warns of a malicious same-named npm
  package (supply-chain risk).
- **Increment over Canonical**: Strongly overlaps the scoped-knowledge / index-as-access-mechanism principle; the
  increment is the **explicit compile-vs-RAG distinction** and the **ingest→query→lint→promote loop**. Dedup: MERGE
  the layer/index parts, KEEP the loop as an operational procedure.
- **Minimal falsification**: Build a small wiki on one topic, add N sources, and test query accuracy with/without
  the compiled wiki versus naive chunk retrieval at the same corpus size.

### KP-07 — A personal agent's risk scales with memory accuracy, not feature count
- **Source**: SRC-TODAY-HOME; SRC-TODAY-BLOG; SRC-TODAY-AITNT; SRC-TODAY-AIXQ; SRC-TODAY-BAAI.
- **Distilled principle**: Long-term memory + proactive briefs + confirmed multi-step execution is the useful
  personal-agent shape; memory must be user-visible, editable, deletable, and corrected.
- **Boundary**: Vendor and reviewer descriptions, not an independent benchmark. Confirmation-before-action is a
  stated design line (no send/calendar change without explicit confirmation).
- **Counterexample / risk**: Reviewer observed wrong memory inferences; the more proactive the agent, the larger
  the cost of a wrong memory. Over-notification causes muting.
- **Increment over Canonical**: Adds an **operational personal-agent loop** (memory → proactive brief → confirmed
  execution) with an explicit failure mode; compatible with the auditable-task-contract principle.
- **Minimal falsification**: Seed a known false memory, then measure whether subsequent proactive suggestions are
  corrected after user edit within a bounded time.

### KP-08 — Learning methods: keep the structure, drop the multipliers
- **Source**: SRC-WORKBUDDY-10X; SRC-WEREAD-10X; SRC-EINKCN-10X.
- **Distilled principle**: Force multiple perspectives, surface contradictions, compress into a briefing, curate
  ≤5 resources, ladder the difficulty, actively test (retrieval practice), and compress again (Feynman/one-pager).
- **Boundary**: The method is an author-designed workflow; the underlying mechanisms (testing effect, Feynman,
  ZPD) are named but their effect sizes are not established here. "10x" is the author's own marketing caveat.
- **Counterexample / risk**: Steps 8–9 only work if the human answers/explains; automating them removes the active
  recall benefit. "25% memory improvement" and "20小时" are unverified / likely mislabels.
- **Increment over Canonical**: Adds a reusable *learning-loop procedure* with explicit human-in-the-loop gates.
- **Minimal falsification**: Pre/post test two groups (method vs. plain reading) on the same topic; the claim fails
  if there is no significant learning gain and no gain in delayed retention.

### KP-09 — Services-share facts are solid; AI-dividend and cognitive-decline narratives are not
- **Source**: SRC-NBS-2025; SRC-NBS-145; SRC-XINHUA-SVC; SRC-36KR-SVC; SRC-GUANCHA.
- **Distilled principle**: Use official statistics (China services = 57.7% of GDP in 2025; policy target 100万亿 by
  2030) and treat derived AI-dividend/cognition claims as hypotheses requiring evidence.
- **Boundary**: Nominal-GDP service shares are distorted by price levels; cross-country comparisons must control for
  this. NBS is primary for China; the US/Japan/Germany shares are secondary.
- **Counterexample / risk**: "Irreversible attention/ability decline" and "celebrity-children device limits" were
  not found in any read source; promoting them would be fabrication.
- **Increment over Canonical**: Adds a *data-hygiene rule*: distinguish official statistics from speculation when
  building economic narratives.
- **Minimal falsification**: Re-pull the NBS series and the policy document; attempt to locate a peer-reviewed
  source for any cognition claim; absence falsifies the strong version.

### KP-10 — Text-thread form factor drives adoption; broad ToS drive the risk
- **Source**: SRC-WIRED-INSTINCT; SRC-INFER-INSTINCT; SRC-MLQ-INSTINCT; SRC-SVTR-INSTINCT; SRC-YAHOO-40; SRC-TRAVEL-INSTINCT.
- **Distilled principle**: Meeting users inside existing chat apps (iMessage/WhatsApp) plus a cloud computer is a
  strong adoption pattern; the same breadth creates retention, liability, and privacy exposure.
- **Boundary**: Invite-only beta; all growth/GMV/credit-card figures are SELF_REPORTED (founder/podcast) and the GMV
  calculation is undisclosed/unaudited.
- **Counterexample / risk**: Inbox copies retained after disconnect, broad model-training ToS, $100 liability cap,
  API-hammering that got a user banned, and user-borne losses (e.g., a $64 cancellation).
- **Increment over Canonical**: Provides a concrete *adoption vs. liability* trade-off, reinforcing the
  authorization/consent and audit principles.
- **Minimal falsification**: Disconnect an integration and verify by data-subject request whether indexed data is
  actually deleted; audit the ToS for retention/training and liability caps.

### KP-11 — Transfer is real but bounded; teach abstraction and varied practice, not analogy
- **Source**: SRC-EDU-CSTOL; SRC-EDU-COGN; SRC-CHINADAILY-TRANSFER.
- **Distilled principle**: Near transfer is achievable via schema induction and multiple-representation practice;
  far transfer requires recognizing/abstracting/associating the *deep structure*, not surface analogy.
- **Boundary**: Transfer is not automatic; depends on prior knowledge and deep-structure similarity; the reviewed
  material supports near transfer strongly and far transfer weakly.
- **Counterexample / risk**: Superficial cross-domain analogy is exactly the over-association failure warned about;
  claiming guaranteed "触类旁通" overclaims the evidence.
- **Increment over Canonical**: Adds a *training-design* principle (varied practice + abstraction) with an explicit
  far-transfer boundary.
- **Minimal falsification**: Train on a structured set; test on both near and far variants; a large near-vs-far gap
  falsifies claims of general transfer.

### KP-12 — Accessibility-snapshot browser automation is auditable but stores state
- **Source**: SRC-VERCEL-AB; SRC-WORKBUDDY-AB; SRC-SKILLHUB-AB; SRC-SKILLSMP-AB.
- **Distilled principle**: Snapshot-and-ref (`@eN`) browser control is deterministic and token-efficient; re-snapshot
  after every page change; use isolated sessions for parallel work.
- **Boundary**: Upstream is a Vercel Labs open-source CLI; WorkBuddy exposes it as a SkillHub skill and runs an
  install-time scan (claim). "Parallel 3 tasks" exact number unverified (multi-session is verified).
- **Counterexample / risk**: `state save/load` can persist auth cookies/tokens on disk; `upload` sends local files;
  third-party repackagers have unclear provenance.
- **Increment over Canonical**: Concretizes the asset-provenance and read-back principles for an executable browser
  skill, including the stored-credential surface.
- **Minimal falsification**: Diff the installed skill against upstream; run `state save` then inspect the file for
  tokens; attempt an action outside the documented capability.

## Distillation decisions per topic

| # | Topic | Retain? | Basis |
|---|---|---|---|
| 1 | 小艺帮帮忙 | KEEP_AS_REFERENCE | Vendor facts solid; execution-surface value; A2A/Hermes unproven |
| 2 | 补天 | MERGE | Rules belong under an existing authorization/compliance principle |
| 3 | Vibe coding | KEEP_AS_REFERENCE | Primary quote + independent security studies |
| 4 | MATLAB skills | REJECT (as named) + RESEARCH_BLOCKED | Named repo not found; retention only as provenance case (KP-04) |
| 5 | 原子习惯 | MERGE (system part) + KEEP (identity/friction) | Overlaps system-over-willpower; identity is increment |
| 6 | GBrain/LLM Wiki | KEEP_AS_REFERENCE (pattern) / REJECT (metrics) | Pattern citable; vendor metrics self-reported |
| 7 | Today AI | KEEP_AS_REFERENCE | Useful agent shape; no independent benchmark |
| 8 | 十步速学 | KEEP_AS_REFERENCE (structure) / REJECT (multipliers) | Structure reusable; 10x/25% unverified |
| 9 | 服务业2.0 | MERGE (NBS facts) / REJECT (unevidenced claims) | Official stats citable; cognitive claims unevidenced |
| 10 | Instinct | KEEP_AS_REFERENCE | Form factor + risk reported by credible outlets; metrics self-reported |
| 11 | 触类旁通 | MERGE / KEEP_AS_REFERENCE | Maps onto transfer-training principle |
| 12 | agent-browser | KEEP_AS_REFERENCE | Open-source docs solid; registry provenance partial |

> Nothing in this file is a promotion proposal. All KPs are advisory (`auto_executed: false` semantics); see
> `outputs/gaps-and-gates.md` for the blocking gates.
