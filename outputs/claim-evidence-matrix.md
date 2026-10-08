# claim-evidence-matrix — KNOWLEDGE_BATCH_12_EVIDENCE_ENRICHMENT_V1

- Task: `cf-356d867fb663`, project `personal-ai-knowledge-triage`, risk `LOW`.
- Mode: **READONLY / RESEARCH ONLY**. No Canonical/DECISION/SKILL/Cloudflare/registry write, no deploy.
- Input status: **SOURCE_BREAKDOWN_NOT_VIDEO_TRANSCRIPT** — the 12 items below are the candidate
  topics and their known talking points, **not** verbatim transcripts. All "verified_fact" cells
  are facts verified from the cited sources, which may differ from what a video said.
- Claim IDs are per-topic and traceable: `T{n}-C{k}` = candidate claim; `T{n}-V{k}` = verified fact;
  `T{n}-I{k}` = interpretation; `T{n}-X{k}` = speculation/contradiction/unknown.

Legend for verification status: `VERIFIED` (independent source confirms), `PARTIAL`
(some elements confirmed, others not), `NOT_VERIFIED` (no independent evidence found),
`UNKNOWN` (primary source unreadable / absent), `CONTRADICTED` (a source contradicts the claim).

---

## Topic 1 — 华为鸿蒙小艺帮帮忙（后台自动操作App / 录制技能 / 锁屏限制 / A2A 对接 Hermes）

Candidate claims: background automation of third-party apps; skill teaching by demonstration;
background status bar; lock-screen and OS/device constraints; can it natively A2A-connect to Hermes.

| claim_id | source_claim (as given) | verified_fact | evidence | status |
|---|---|---|---|---|
| T01-C1 | 小艺帮帮忙 can operate apps in the background for multi-step tasks | Huawei: feature exists; "任务会默认在后台执行，您可以通过点击屏幕下方彩条来查看任务详情"; supports shopping/booking/video download tasks | SRC-HW-01; SRC-ITHOME; SRC-DONEWS | VERIFIED |
| T01-C2 | Users can "record/teach" skills by one image/sentence/demonstration | Huawei: "通过一张图、一句话或一次演示…教给小艺，保存为专属技能" | SRC-HW-01 | VERIFIED |
| T01-C3 | Requires OS/device/network constraints | Huawei: HarmonyOS 6.0.0+; specific Mate/Pura/nova families; network required; agent is 众测 and **stops being offered on new HarmonyOS 7.0 models** | SRC-HW-01 | VERIFIED |
| T01-C4 | No lock-screen support | Huawei: "计划任务当前不支持在锁屏状态下自动执行"; if locked, it sends a notification instead | SRC-HW-01 | VERIFIED |
| T01-C5 | Video's "HarmonyOS 7" framing / supported-app list | Huawei support page lists the agent as a HarmonyOS **6.0** exploratory agent not offered on new 7.0 devices; "部分应用或任务无法通过小艺帮帮忙完成操作"; WeChat-type social apps unsupported | SRC-HW-01 | PARTIAL (the "7.0 feature" framing is CONTRADICTED by the vendor page) |
| T01-C6 | 小艺 can natively A2A-connect to Hermes | No first-party statement; local read-only audit scores **12 MISMATCH / 1 MATCH / 2 UNKNOWN** on the Huawei 云A2A → Hermes field matrix and concludes direct native compatibility = **NO** | SRC-LOCAL-A2A (rows 1–15); SRC-HW-03/04/05 (bodies JS-gated) | NOT_VERIFIED / direct = NO |

- `T01-I1` Interpretation: this is a **system-integrated GUI/agent capability**, not a public protocol. Its value for a Personal AI layer is as an *execution surface*, gated by vendor OS/device/policy.
- `T01-X1` Risk: task automation may violate third-party app rules/accounts (Huawei itself notes platform policy limits). `T01-X2` Unknown: whether the 众测 agent will persist past HarmonyOS 7.0 (`UNKNOWN` for future devices).
- `T01-X3` Contradiction: the candidate's implied "HarmonyOS 7 feature" conflicts with Huawei's statement that the 6.0 agent is **not offered on new 7.0 models** (personal skills/timed tasks carry over).

## Topic 2 — 补天漏洞平台（授权白帽 SRC / 众测 / 赏金机制 / 新手 AI 辅助变现与合规边界）

| claim_id | source_claim | verified_fact | evidence | status |
|---|---|---|---|---|
| T02-C1 | Platform runs authorized white-hat SRC + crowdtest + bounty | 补天 FAQ: 公益SRC / 专属SRC / 众测 modes; "安全众包…从模拟攻击者角度发现问题" | SRC-BUTIAN-FAQ; SRC-BUTIAN-NEW | VERIFIED |
| T02-C2 | Newcomers can start | 补天: newcomers may start with 公益SRC / lower-weight vendors; new accounts capped at 5 pending vulns until first valid one | SRC-BUTIAN-NEW | VERIFIED |
| T02-C3 | Bounty ranges and payment mechanics | 通用漏洞奖励标准 tiers (low ¥200–800 / medium ¥800–3000 / high ¥3000–10000, per search excerpt); cash paid Wednesday, KB points; tax withheld | SRC-BUTIAN-PLAN; SRC-BUTIAN-FAQ | PARTIAL (tier figures from search excerpt; plan page body only partially read) |
| T02-C4 | Crowdtest access is not open to all | 补天众测 requires ≥2 of: top-300 ranking / 5+ valid high-risk SRC vulns in a year / top-3 in another SRC / elite referral; NDA + invite code; VPN + scheduled window; scan/DoS/social-engineering forbidden | SRC-BUTIAN-ZC | VERIFIED |
| T02-C5 | "AI-assisted monetization" is feasible and compliant | No 补天 first-party policy read this session. A peer platform (漏洞盒子) published a notice **restricting/standardizing AI-assisted vuln reports** (2026-06-24) | SRC-VULBOX (notice title only) | UNKNOWN / PARTIAL |
| T02-C6 | Recruitment/eligibility claims are easy money for beginners | Rules show reputation (100 start; −10/offense; ban at ≤60), accuracy ranking, and a 5-pending cap — i.e. quality-gated, not passive income | SRC-BUTIAN-FAQ; SRC-BUTIAN-NEW | PARTIAL (contradicts "easy money" framing) |

- `T02-I1`: Only **authorized, in-scope, time-boxed** testing is legitimate; the compliance boundary is the SRC's published scope + NDA, not the tool used.
- `T02-X1` Risk: AI-generated report spam is now explicitly a compliance topic (peer platform notice), so "AI 辅助变现" must be presented as *quality-assisting*, never as mass automated submission. `T02-X2` Unknown: 补天's own current AI-report policy.

## Topic 3 — Vibe Coding 2026（Karpathy 概念 / 快速原型 vs 生产工程质量安全边界 / 视频安全统计需核实）

| claim_id | source_claim | verified_fact | evidence | status |
|---|---|---|---|---|
| T03-C1 | Karpathy coined "vibe coding" | Karpathy X post (2 Feb 2025): "There's a new kind of coding I call 'vibe coding'… forget that the code even exists"; explicitly scoped to "throwaway weekend projects" | SRC-KARPATHY-VIBE; SRC-WIKI-VIBE; SRC-TOI-VIBE | VERIFIED |
| T03-C2 | Concept is about trusting the LLM and not reading diffs | Original quote: "I 'Accept All' always, I don't read the diffs anymore… the code grows beyond my usual comprehension" | SRC-KARPATHY-VIBE; SRC-ARXIV-VIBE | VERIFIED |
| T03-C3 | 2026 status: term normalized and extended | Wikipedia: Merriam-Webster "slang & trending" (Mar 2025); Collins Word of the Year 2025; Karpathy's Dec-2025 review says vibe coding "terraform software" and benefits regular people | SRC-WIKI-VIBE; SRC-BI-KARPATHY | VERIFIED |
| T03-C4 | Production-quality/security boundary is real | Multiple independent 2025–2026 studies converge: ~44–45% of AI code-gen tasks introduce a known vuln; security pass ~55–56% flat while syntax ~95%+; Java worst (~29% pass) | SRC-VERACODE; SRC-VERACODE2; SRC-CSA; SRC-CODEQL-24 | VERIFIED (aggregate pattern) |
| T03-C5 | The video's *specific* security statistic | No transcript; cannot confirm which number was cited | — | UNKNOWN (do not attribute a number to the video) |

- `T03-I1`: Karpathy's own framing is explicitly **prototype/throwaway**, so using it as justification for production code is a category error.
- `T03-X1` Contradiction: the claim "vibe coding is fine for production" contradicts the measured ~1-in-3-to-1-in-2 vulnerable-output rate. `T03-X2` caveat: security statistics vary by language/vuln class/model; cite ranges, not one number.
- `T03-X3` Speculation (flagged as such by sources): headline "10x"/"terraform software" language is opinion, not measurement.

## Topic 4 — 豆包工作 MATLAB skills（SamuelQQ/matlab-skills 真实性 / license / 权限风险 / 销售数据处理）

| claim_id | source_claim | verified_fact | evidence | status |
|---|---|---|---|---|
| T04-C1 | A repo `SamuelQQ/matlab-skills` exists | GitHub API: `GET /repos/SamuelQQ/matlab-skills` → **404**; GitHub user `SamuelQQ` not found. A similarly named user `SamuelQZQ` exists but is an unrelated Web3/Chromium developer | SRC-GH-API-MATLAB; SRC-GH-Samuel | NOT_VERIFIED / likely CONTRADICTED |
| T04-C2 | MATLAB agent "skills" repos are a real ecosystem | GitHub search returns many: `matlab/matlab-agentic-toolkit`, `matlab/agent-skills-playground`, `zhnnky329/MathModeling-skills`, `wzyn20051216/matlab-agent-skills`, etc. | SRC-GH-API-MATLAB | VERIFIED (ecosystem), NOT this repo |
| T04-C3 | Official MATLAB skills exist with a license | MathWorks `matlab/agent-skills-playground` = license `NOASSERTION` (repo-specific); other third-party repos listed MIT/Apache-2.0; the official toolkit installs an MCP server + curated skills | SRC-MATHWORKS; SRC-MW-PLAY; SRC-GH-API-MATLAB | VERIFIED |
| T04-C4 | Install = permission risk | Official path auto-installs an MCP server with MATLAB session access; third-party skills execute code in the MATLAB session | SRC-MATHWORKS | VERIFIED (capability risk exists) |
| T04-C5 | MATLAB is better than Python/Excel for sales-data automation | No head-to-head evidence found; a secondary article shows Doubao can produce Python/Matplotlib code as output, not a MATLAB-vs-Python benchmark | SRC-17GOLANG | NOT_VERIFIED |

- `T04-I1`: The verifiable "MATLAB skills" story is the **MathWorks official agentic toolkit**, not the named repo. Treat the specific repo as not found.
- `T04-X1` Risk: an unvetted third-party skill that executes code inherits the user's MATLAB/Python filesystem+sales data; license and commit provenance matter. `T04-X2` Unknown: the exact repo the video referenced.

## Topic 5 — 《原子习惯》（身份习惯 / 提示-渴望-反应-奖励 / 环境摩擦）与已有 SYSTEM_OVER_WILLPOWER 去重

| claim_id | source_claim | verified_fact | evidence | status |
|---|---|---|---|---|
| T05-C1 | Identity-based habits precede behavior change | Clear: "The key to building lasting habits is focusing on creating a new identity first… Every action is a vote for the type of person you wish to become." Two steps: decide the type of person; prove it with small wins | SRC-JC-IDENTITY; SRC-JC-ATOMIC | VERIFIED |
| T05-C2 | Habit loop = cue → craving → response → reward | Clear (excerpt): "cue triggers a craving, which motivates a response, which provides a reward, which satisfies the craving and… becomes associated with the cue"; problem phase / solution phase | SRC-JC-3STEPS | VERIFIED |
| T05-C3 | Four Laws / inversion | Create: obvious, attractive, easy, satisfying. Break: invisible, unattractive, difficult, unsatisfying | SRC-JC-3STEPS | VERIFIED |
| T05-C4 | Environment/friction design | Clear: "Design your environment to make success easier"; response depends on motivation × friction × ability | SRC-JC-ATOMIC; SRC-JC-3STEPS | VERIFIED |
| T05-C5 | This is new relative to a "SYSTEM_OVER_WILLPOWER" Canonical principle | "You do not rise to the level of your goals. You fall to the level of your systems" is the **same underlying principle** (system > willpower), i.e. overlap, not increment | SRC-JC-ATOMIC | OVERLAP (see dedup review) |

- `T05-I1`: Net *increment* over a system-over-willpower principle is the **identity layer** and the **four-stage decomposition** as an operational design checklist, not the system-vs-willpower thesis itself.
- `T05-X1` Boundary: it is behavioral-popular-science, not a clinical protocol; "1%" framing is illustrative. No counterexample is denied by Clear but placebo/self-report bias in habit literature is a known limitation (`T05-X2`, general domain caution).

## Topic 6 — GBrain / LLM Wiki（garrytan/gbrain / Karpathy LLM wiki / Markdown 编译 / hybrid retrieval/RRF/graph/引用/夜间整理 / 十万页与 Skill 自进化宣传）

| claim_id | source_claim | verified_fact | evidence | status |
|---|---|---|---|---|
| T06-C1 | Karpathy's LLM Wiki pattern exists | Karpathy gist "LLM Wiki" (Apr 2026): 3 layers (raw sources / wiki / schema); 4 ops (ingest, query, lint, promote); "wiki is a persistent, compounding artifact"; Obsidian=IDE, LLM=programmer | SRC-KARPATHY-WIKI | VERIFIED |
| T06-C2 | garrytan/gbrain exists and implements it | GBrain README: "This is Karpathy's LLM wiki pattern, but extended from research notes into a full operational knowledge base"; built by Garry Tan | SRC-GBRAIN-README; SRC-GBRAIN-SCHEMA | VERIFIED (repo + self-description) |
| T06-C3 | Markdown-compiled wiki, hybrid retrieval, graph, citations, overnight maintenance | README/docs describe: markdown pages, self-wiring knowledge graph via entity extraction with "zero LLM calls", multi-hop `graph-query`, citation self-repair, overnight consolidation, cron jobs | SRC-GBRAIN-README; SRC-GBRAIN-ORIGIN | PARTIAL (self-reported in docs; not independently benchmarked) |
| T06-C4 | The "155,795 pages / 24,589 people / 5,340 companies / +31.4 P@5 / 十万页" claims | Appear only in the vendor's own README/docs | SRC-GBRAIN-README; SRC-GBRAIN-SCHEMA | NOT_VERIFIED (self-reported metric) |
| T06-C5 | RRF / hybrid retrieval specifics | README mentions hybrid retrieval and "qmd" BM25/vector + LLM re-rank as an option (via Karpathy gist); no first-party corpus benchmark read showing RRF params | SRC-KARPATHY-WIKI; SRC-GBRAIN-README | PARTIAL / UNKNOWN for exact RRF claim |
| T06-C6 | "Skill 自进化" (self-evolving skills) | GBrain docs describe skillpacks and agent operator contracts, but no evidence of autonomous skill self-evolution with measured results | SRC-GBRAIN-README | NOT_VERIFIED |

- `T06-I1`: The **reusable, source-backed principle** is Karpathy's compile-not-retrieve wiki loop (ingest→query→lint→promote) with a schema file; GBrain is one implementation + vendor claims.
- `T06-X1` Risk: vendor metrics cannot be promoted as facts. `T06-X2` Unknown: independent reproduction of the graph lift or scale numbers.
- `T06-X3` Note: GBrain warns the npm package `gbrain` is unrelated (supply-chain caution) — useful provenance signal.

## Topic 7 — Today AI（齐俊元 / 此间无限 / 长期记忆 / 主动简报 / 招聘截图日历能力 / 实际可用性）

| claim_id | source_claim | verified_fact | evidence | status |
|---|---|---|---|---|
| T07-C1 | Founder 齐俊元, company 此间无限 | Multiple sources: Teambition founder (acquired by Alibaba ~$100M in 2019), later 阿里云盘 / 飞书 VP / 豆包 PC lead, left ByteDance Nov 2025, then founded Today; company 此间无限; backed by 阶跃星辰, IDG, 红杉, 五源 | SRC-TODAY-AITNT; SRC-TODAY-AIXQ; SRC-TODAY-BAAI | VERIFIED |
| T07-C2 | Living Memory of people/projects/preferences | First-party: "围绕你的日程、人物、项目和目标构建个人知识图谱；有版本记录、可编辑，也可以由你决定遗忘"; memory stored as `profile.md`, `work.md`, `lifestyle.md`, `tools.md`, `goals.md`, `routine.md`, `character.md` (per review) | SRC-TODAY-HOME; SRC-TODAY-AIXQ | VERIFIED (vendor description) |
| T07-C3 | Proactive morning/evening briefs | First-party: 晨间简报/晚间简报; proactive but "无你的明确确认，Today 不发邮件、不挪日历、不向任何人发消息" | SRC-TODAY-HOME; SRC-TODAY-BLOG | VERIFIED (vendor description) |
| T07-C4 | Screenshot / calendar / recruiting capabilities | Reviewer confirms connectors to email/Feishu/calendar and a cloud computer; "招聘" specifically not confirmed; independent review notes memory inferences were sometimes wrong | SRC-TODAY-AITNT; SRC-TODAY-AIXQ | PARTIAL |
| T07-C5 | Actually usable / reliable | Independent review: proactive cards "可能只是它根据有限信息作出的推断", wrong-memory cost scales with proactivity; recommends long-term verification | SRC-TODAY-AITNT | PARTIAL (not independently benchmarked) |

- `T07-I1`: The verifiable pattern is **memory + proactive brief + confirmed multi-step execution**, with the reviewer's caveat that wrong memory is the main risk.
- `T07-X1` Unknown: recruiting-specific feature; production reliability metrics; pricing beyond "免费基础版 + 1亿 tokens 试用". `T07-X2` Risk: over-proactivity → notification fatigue (vendor itself acknowledges).

## Topic 8 — WorkBuddy 十步速学（五视角/矛盾清单/合成简报/挑刺/资料/学习阶梯/20小时/考试/费曼/速查表；10倍速与25%记忆提升未验证；视频标注2026-11-09未来日期）

| claim_id | source_claim | verified_fact | evidence | status |
|---|---|---|---|---|
| T08-C1 | A 10-step AI learning method exists | Author repo page lists exactly: 五视角STORM, 矛盾图谱, 综合简报, 同行评审自检, 资源筛选, 学习阶梯, 2小时啃核心20%, 考到崩溃, 费曼循环, 一页速查表; generalizes across WorkBuddy/Claude Code/Codex/Cursor | SRC-WORKBUDDY-10X; SRC-WEREAD-10X; SRC-EINKCN-10X | VERIFIED (method as authored) |
| T08-C2 | It fuses STORM + a "four-element" learning path + Feynman | Author states it fuses X blogger Rahul's method and the Stanford STORM multi-perspective paper | SRC-WORKBUDDY-10X; SRC-EINKCN-10X | VERIFIED (attribution as stated) |
| T08-C3 | "10x speed" | Author's own page: "『10 倍速』是营销话术…别期待字面 10 倍" | SRC-WORKBUDDY-10X | CONTRADICTED (by the author's own caveat) |
| T08-C4 | "25% memory improvement" | Not found in any read source; no primary study | — | NOT_VERIFIED |
| T08-C5 | The method has real underlying mechanisms | Author names testing effect, Feynman, ZPD, STORM; explicitly warns STORM has source bias/over-association and AI self-eval cannot be fully trusted | SRC-WORKBUDDY-10X | VERIFIED (mechanism names); effect size NOT_VERIFIED |
| T08-C6 | "20小时" / 2-hour core-20% | Step 7 is "2小时" in the author text, not "20小时"; the widely-cited "20小时" figure comes from unrelated popular lore | SRC-WORKBUDDY-10X | PARTIAL / possible mislabel |
| T08-C7 | Video labelled 2026-11-09 | That date is in the future relative to retrieval (2026-10-08) | — | CONTRADICTED as a real event date (likely a mis-label / scheduled post) |

- `T08-I1`: Keep the **structure** (force multiple perspectives → contradictions → compress → test → compress again). Drop the unverifiable multipliers.
- `T08-X1` Risk: "考到崩溃" and Feynman require the human to actually answer; automation removes the active-recall benefit. `T08-X2` Unknown: measured learning outcomes.

## Topic 9 — AI 服务业改革开放 2.0（中美服务业 GDP 占比 / AI 红利推测 / 注意力退化不可逆 / 名人子女电子产品限制等需严审）

| claim_id | source_claim | verified_fact | evidence | status |
|---|---|---|---|---|
| T09-C1 | China's service share of GDP | NBS: 2025 服务业增加值 808,879亿元; **57.7%** of GDP; contribution to growth 61.4% | SRC-NBS-2025; SRC-NBS-145 | VERIFIED |
| T09-C2 | US service share of GDP | Secondary analysis: US ~78% (2024, per World Bank), Japan ~70%, Germany ~65%; China ~57.7% (2025) rising to ~61.7% (2026Q1, secondary) | SRC-36KR-SVC; SRC-XINHUA-SVC | VERIFIED (with source caveat: 36氪 is secondary; NBS is primary for China) |
| T09-C3 | A policy to expand services to 100万亿 by 2030 | 新华网 / 多家: 国务院《关于推进服务业扩能提质的意见》targets 100万亿元 by 2030; emphasizes productive services + manufacturing-services integration + "人工智能+" procurement | SRC-XINHUA-SVC; SRC-36KR-SVC | VERIFIED |
| T09-C4 | AI dividend speculation ("红利") | Analytical commentary, not measurement; no first-party causal estimate read | SRC-36KR-SVC | NOT_VERIFIED (speculation) |
| T09-C5 | "注意力/能力退化不可逆" | No source read supports "irreversible"; a 观察者网 piece discusses attention/spread of AI anxiety but not irreversibility | SRC-GUANCHA | NOT_VERIFIED / likely overclaim |
| T09-C6 | "名人子女电子产品限制" | Not found in any read source | — | UNKNOWN |
| T09-C7 | Chinese vs US AI optimism gap | 观察者网 (citing Stanford AI Index): 84% of Chinese respondents excited vs 38% US; ~80% of US workers in services vs ~46% China | SRC-GUANCHA | PARTIAL (secondary reporting of a survey) |

- `T09-I1`: The hard, citable facts are the NBS shares and the 100万亿 policy target; the "irreversible cognitive decline" and "celebrity kids" claims are not evidenced and must not be promoted.
- `T09-X1` Boundary: services share comparisons must control for **price levels** (nominal-GDP distortion noted by sources). `T09-X2` Unknown: named-attention research and any causal AI-dividend estimate.

## Topic 10 — Instinct AI（iMessage/WhatsApp 入口 / 交易闭环 / 增长·融资·GMV·信用卡授权比例 / 隐私安全事故 / 推理成本）

| claim_id | source_claim | verified_fact | evidence | status |
|---|---|---|---|---|
| T10-C1 | iMessage/WhatsApp/phone entry, cloud computer, no app required | SVTR, WIRED, GadgetsNow: users text/call via iMessage/WhatsApp; runs its own cloud computer with browser+stored logins; invite-only beta | SRC-SVTR-INSTINCT; SRC-WIRED-INSTINCT | VERIFIED |
| T10-C2 | Company = Spear Street Technology, founder Noah Shinn | MLQ, SVTR, Forbes: operating entity Spear Street Technology Inc.; founder Noah Shinn, ex-Sierra; first author of Reflexion (NeurIPS 2023) | SRC-MLQ-INSTINCT; SRC-SVTR-INSTINCT; SRC-FORBES-INSTINCT | VERIFIED |
| T10-C3 | Funding/valuation trajectory | MLQ/Forbes: $50M → $500M → $2.5B (Aug 2026, $250M Series B led by Index+Benchmark; total ~$350M); later reported $1B raise at $10B (DealBook, Sep 2026) | SRC-MLQ-INSTINCT; SRC-FORBES-INSTINCT; SRC-INFER-INSTINCT | PARTIAL (reported; final $1B/$10B per secondary) |
| T10-C4 | GMV / transaction volume | Founder claim via podcast: approaching **$1B annualized** transaction volume, >50% travel; company "has not explained how it calculates the figure"; not audited | SRC-TBPN-INSTINCT; SRC-TRAVEL-INSTINCT; SRC-INFER-INSTINCT | NOT_VERIFIED (founder claim) |
| T10-C5 | Credit-card authorization ratio | Founder on "Invest Like the Best": "Three weeks in, there's a 40% chance that the user has shared a personal credit card"; 80% retention among users sharing sensitive info | SRC-YAHOO-40; SRC-TBPN-INSTINCT | PARTIAL (self-reported founder stat) |
| T10-C6 | Privacy/security incidents | WIRED: users reported inbox copies retained after disconnect; one VC banned from Resy after ~200 API pings/hour; another said it would be trivial to phish; $64 DoorDash loss from an unauthorized-feeling cancel; ToS allow training + appoint Instinct as agent for transactions | SRC-WIRED-INSTINCT; SRC-MLQ-INSTINCT | VERIFIED (reported accounts) |
| T10-C7 | Inference cost | "Compute demand doubling roughly every week" (podcast claim); no per-task cost disclosed | SRC-TBPN-INSTINCT | UNKNOWN |

- `T10-I1`: The verifiable *pattern* is form-factor (text thread) + cloud computer + confirmed actions. The verifiable *risk* is data retention, broad ToS, and liability caps (terms cap at greater of $100 or fees; user bears losses).
- `T10-X1` Contradiction: headline "$1B transaction volume" vs "founder claim, not audited". `T10-X2` Unknown: take rate, repeat-booking rate, average transaction value, inference cost.

## Topic 11 — 触类旁通（图式归纳 / 远迁移 / 认知灵活性 / 非典型组合 / 跨域迁移边界与实际验证）

| claim_id | source_claim | verified_fact | evidence | status |
|---|---|---|---|---|
| T11-C1 | "触类旁通" = transfer of learning | Learning-transfer literature: "一种学习对另一种学习的影响"; transfer is the key link from knowledge/skill to ability | SRC-CHINADAILY-TRANSFER; SRC-EDU-COGN | VERIFIED (construct) |
| T11-C2 | Schema induction supports transfer | 图式理论: humans generalize experience into schemas; rigid schemas fail on variation; graded (variation) training perturbs schemas and builds flexible transfer | SRC-EDU-COGN; SRC-EDU-CSTOL | VERIFIED (theory-level) |
| T11-C3 | Cognitive-flexibility theory / ill-structured domains | Spiro's Cognitive Flexibility Theory cited: complex/ill-structured knowledge requires multiple perspectives and re-entry; hypertext case design supports it | SRC-EDU-CSTOL | VERIFIED (cited literature) |
| T11-C4 | Far transfer to unrelated domains is reliable | Sources distinguish **near** vs **far** transfer and warn transfer is not automatic; recognizing/abstracting/associating are prerequisites; strong far transfer is hard | SRC-CHINADAILY-TRANSFER; SRC-EDU-COGN | PARTIAL (near transfer supported; far transfer bounded) |
| T11-C5 | Non-typical combinations are a verified method | No single canonical study; treated as a design heuristic in the reviewed material, not a validated intervention | — | NOT_VERIFIED |

- `T11-I1`: The reusable mechanism is **abstraction at the right grain + varied practice across contexts** (识别/抽象/关联); "触类旁通" as a guaranteed outcome is an overclaim.
- `T11-X1` Boundary: transfer depends on learner prior knowledge and similarity of deep structure. `T11-X2` Risk: superficial "cross-domain analogy" is exactly the over-association failure STORM warns about.

## Topic 12 — WorkBuddy agent-browser（元素编号快照 / 点击·上传·截图·会话保留 / 并行3任务 / 是否官方 SkillHub / 权限审计）

| claim_id | source_claim | verified_fact | evidence | status |
|---|---|---|---|---|
| T12-C1 | Snapshot with numbered element refs (`@eN`) | vercel-labs SKILL.md: accessibility-tree snapshots with compact `@eN` refs; `snapshot -i` for interactive elements; refs are stale after page change → re-snapshot | SRC-VERCEL-AB | VERIFIED |
| T12-C2 | click / fill / type / select / upload / screenshot / session state | Documented commands: `click @e1`, `fill`, `type`, `select`, `upload @e5 file1.pdf`, `screenshot`, `state save/load`, isolated `--session`, `--pin-tab` | SRC-VERCEL-AB; SRC-SKILLSMP-AB | VERIFIED |
| T12-C3 | Parallel / multi-session | SKILL.md: each `--session` is an isolated browser with own cookies/tabs/refs; multi-user flows and parallel scraping; `--pin-tab` for shared CDP Chrome | SRC-VERCEL-AB; SRC-SKILLSMP-AB | VERIFIED (multi-session); "并行3任务" exact number NOT_VERIFIED |
| T12-C4 | Is it on official SkillHub? | WorkBuddy docs list install name `agent-browser`, repo source `SkillHub`; SkillHub page exists; WorkBuddy runs "a security scan before installation" | SRC-WORKBUDDY-AB; SRC-SKILLHUB-AB; SRC-TC-AB | PARTIAL (SkillHub listing + WorkBuddy docs confirmed; "official" ownership not proven) |
| T12-C5 | Permission/security audit | Upstream is Vercel Labs open-source CLI (Rust/Chrome via CDP); skill is markdown + shell allowed-tools `Bash(agent-browser:*)`; third-party repackagers exist (skillsmp, 321skill) | SRC-VERCEL-AB; SRC-SKILLSMP-AB | PARTIAL (upstream clear; repackager trust unclear) |
| T12-C6 | Upload/screenshot/session handling risk | Upload sends local files; state files may persist auth cookies/tokens on disk — a credential-exposure surface | SRC-VERCEL-AB | VERIFIED (capability risk) |

- `T12-I1`: The mechanism is accessibility-snapshot + refs (token-efficient, deterministic), which is more auditable than raw CSS. But the trust boundary is the npm/GitHub provenance and the `state` files.
- `T12-X1` Unknown: whether SkillHub's version is byte-identical to upstream and whether WorkBuddy's scan is verifiable. `T12-X2` Risk: running a browser skill that stores session state can leave credentials on disk.

---

## Cross-topic claim summary

| # | Topic | Highest status achieved | Dominant blocker |
|---|---|---|---|
| 1 | 小艺帮帮忙 | VERIFIED (vendor docs) | A2A/Hermes spec unreadable; no device run |
| 2 | 补天 | VERIFIED (first-party rules) | No first-party AI-report policy read |
| 3 | Vibe coding | VERIFIED (primary quote + studies) | Video's exact stat unknown |
| 4 | MATLAB skills | VERIFIED ecosystem | Named repo not found |
| 5 | 原子习惯 | VERIFIED (author pages) | Overlaps existing principle |
| 6 | GBrain/LLM Wiki | VERIFIED pattern | Vendor metrics self-reported |
| 7 | Today AI | VERIFIED (vendor/reviews) | No independent benchmark |
| 8 | 十步速学 | VERIFIED method | Multipliers unverifiable; future date |
| 9 | 服务业2.0 | VERIFIED (NBS/policy) | Several claims unevidenced |
| 10 | Instinct | VERIFIED (form factor/risk) | GMV/ratio self-reported |
| 11 | 触类旁通 | VERIFIED (transfer theory) | Far-transfer overclaim |
| 12 | agent-browser | VERIFIED (open-source docs) | SkillHub provenance partial |

> No cell in this matrix asserts a fact that was not read in a cited source. Unreadable or
> absent primary material is marked `UNKNOWN` / `NOT_VERIFIED` / `SOURCE_GAP`; no URL or quote
> was synthesized.
