# source-manifest — KNOWLEDGE_BATCH_12_EVIDENCE_ENRICHMENT_V1

- Task: `cf-356d867fb663`
- Project: `personal-ai-knowledge-triage`
- Risk: `LOW`
- Mode: **READONLY / RESEARCH ONLY** — no Canonical write, no Skill install, no Worker deploy, no production permission/secret/binding/schema change.
- Retrieval date (all web fetches): **2026-10-08 (UTC)** unless a source's own date is shown.
- Scope note: input is **12 candidate topics + known talking points**, **not** the 12 videos' verbatim transcripts. See `SOURCE_BREAKDOWN_NOT_VIDEO_TRANSCRIPT` and the source-gap list in `outputs/gaps-and-gates.md`.

> Provenance discipline: every row below is a URL/title actually returned by a live search or
> fetch in this session. No URL, author, date or quotation is invented. Where the primary
> source could not be read (JS-gated, login-gated, not found, or absent), the row is marked
> `SOURCE_GAP` / `UNKNOWN` and **no substitute evidence is fabricated**. "Short quote" fields
> are verbatim fragments from the fetched page or search highlight; they are kept short and
> attributed.

## 1. How evidence was collected

- Independent web searches (12 topics) plus direct `webfetch` of first-party pages / GitHub API.
- Local read-only inspection of the checked-out repository for a **local proxy** of the Cloudflare
  Canonical assets (the Cloudflare read connector is not available in this sandbox; see
  `outputs/dedup-canonical-review.md` → `CANONICAL_READ_UNAVAILABLE`).
- No Huawei/Cloudflare/Instinct account, credential or production endpoint was accessed.

## 2. Source register (machine-referenceable IDs)

| Evidence ID | Title / source | URL | Author / publisher | Date (source) | Fetch / read status |
|---|---|---|---|---|---|
| SRC-HW-01 | 小艺帮帮忙服务功能介绍 | https://consumer.huawei.com/cn/support/content/zh-cn16073021/ | Huawei (first-party support doc) | undated (versioned) | Read (primary) |
| SRC-HW-02 | 自动任务功能介绍 | https://consumer.huawei.com/cn/support/content/zh-cn16071005/ | Huawei (first-party support doc) | undated (versioned) | Read (primary) |
| SRC-HW-03 | A2A协议接入方案 (小艺开放平台) | https://developer.huawei.com/consumer/cn/doc/service/agent2agent-0000002498656261 | Huawei (first-party) | 2026-06-12 | Index only; body JS-gated (`UNKNOWN`) |
| SRC-HW-04 | 云A2A协议技术规范 | https://developer.huawei.com/consumer/cn/doc/service/agent2agent-comments-0000002500412353 | Huawei (first-party) | 2026-06-12 | Index only; body JS-gated (`UNKNOWN`) |
| SRC-HW-05 | 云A2A协议消息指令定义 | https://developer.huawei.com/consumer/cn/doc/doccenter-celia/agent2agent-define-0000002467293060 | Huawei (first-party) | undated | Index only; field tables `UNKNOWN` |
| SRC-LOCAL-A2A | MUSE_HOME_XIAOYI_HERMES_A2A_COMPATIBILITY_AUDIT_20260930 | `docs/audits/MUSE_HOME_XIAOYI_HERMES_A2A_COMPATIBILITY_AUDIT_20260930.md` (local repo) | prior task `cf-930068863258` | 2026-09-30 | Read (local, read-only) |
| SRC-ITHOME | “小艺帮帮忙”适配华为 Pura 80 系列机型 | https://www.ithome.com/0/891/582.htm | IT之家 (归泷) | 2025-10-22 | Read (secondary) |
| SRC-DONEWS | 华为HarmonyOS 6推“小艺帮帮忙”支持多任务操作 | https://www.donews.com/news/detail/4/6201563.html | DoNews | 2025-10-22 | Read (secondary) |
| SRC-FENGLIKA | 华为小艺：藏器于身，待时而动｜AI 器物志 | http://fenglika.blogspot.com/2026/06/ai_0718765780.html | Fenghuan/风里卡 (blog) | 2026-06-15 | Read (secondary/opinion) |
| SRC-PCONLINE | 华为小艺：藏器于身，待时而动 | https://www.pconline.com.cn/focus/2165/21650112.html | 太平洋科技 (zhangyaru_gz, liyicun_gz) | 2026-06-05 | Read (secondary) |
| SRC-BUTIAN-FAQ | 补天帮助/FAQ | https://www.butian.net/Help/faq | 补天漏洞响应平台 (first-party) | undated | Read (primary) |
| SRC-BUTIAN-PLAN | 补天奖励计划 | https://www.butian.net/Reward/plan | 补天漏洞响应平台 (first-party) | undated | Read (primary, partial) |
| SRC-BUTIAN-ZC | 补天众测说明 | https://zhongce.butian.net/Help.html | 补天众测 (first-party) | undated | Read (primary) |
| SRC-BUTIAN-NEW | 补天新手指引 | https://www.butian.net/newneed | 补天漏洞响应平台 (first-party) | undated | Read (primary) |
| SRC-VULBOX | 关于规范 AI 辅助漏洞报告提交标准的公告 | https://www.vulbox.com/news/notice | 漏洞盒子 (first-party notice list) | 2026-06-24 (entry date) | Read (secondary notice title only; body not read) |
| SRC-KARPATHY-VIBE | Karpathy “vibe coding” tweet | https://archive.ph/yNSTA (mirror of X post) | Andrej Karpathy / archive | 2025-02-03 (archived) | Read (archived primary quote) |
| SRC-WIKI-VIBE | Vibe coding (encyclopedia) | https://en.wikipedia.org/wiki/Vibe_coding | Wikipedia contributors | 2025-03-03 (page created) | Read (tertiary; cites primaries) |
| SRC-ARXIV-VIBE | Vibe coding: programming through conversation… | https://arxiv.org/html/2506.23253v1 | arXiv (Karpathy canon analysis) | 2025-06-29 | Read (peer-style preprint) |
| SRC-BI-KARPATHY | The Guy Who Coined 'Vibe Coding' Has a New Prediction | https://www.businessinsider.com/andrej-karpathy-coined-vibecoding-ai-prediction-2025-12 | Business Insider (Henry Chandonnet) | 2025-12-23 | Read (secondary) |
| SRC-TOI-VIBE | What is ‘vibe coding’? | https://timesofindia.indiatimes.com/technology/tech-news/…/articleshow/118659724.cms | Times of India | 2025-03-02 | Read (secondary) |
| SRC-CODEQL-24 | Security Vulnerabilities in AI-Generated Code | https://arxiv.org/abs/2510.26103 | arXiv | 2025 (2510.26103) | Read (preprint) |
| SRC-VERACODE | Spring 2026 GenAI Code Security Update | https://www.veracode.com/blog/spring-2026-genai-code-security/ | Veracode (Felix Brombacher) | 2026-03-24 | Read (vendor research) |
| SRC-VERACODE2 | 2026 GenAI Code Security Report | https://www.veracode.com/blog/2026-genai-code-security-report-ai-risk/ | Veracode (Natalie Tischler) | 2026-07-28 | Read (vendor research) |
| SRC-CSA | Vibe Coding's Security Debt: AI-Generated CVE Surge | https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-generated-code-vulnerability-surge-2026/ | Cloud Security Alliance | 2026-04-04 | Read (industry research note) |
| SRC-NORMA26 | qualityclouds/state-of-ai-code-2026- | https://github.com/qualityclouds/state-of-ai-code-2026- | Norma / qualityclouds | 2026-07 (published) | Read (open dataset, self-corrected) |
| SRC-GH-API-MATLAB | GitHub search: `matlab-skills` | https://api.github.com/search/repositories?q=matlab-skills | GitHub REST API | fetched 2026-10-08 | Read (live API) |
| SRC-GH-Samuel | GitHub user `SamuelQZQ` | https://github.com/SamuelQZQ | GitHub | fetched 2026-10-08 | Read (live page) |
| SRC-MATHWORKS | MATLAB Agentic Toolkit (official) | https://github.com/matlab/matlab-agentic-toolkit | MathWorks (matlab org) | fetched 2026-10-08 | Read (primary) |
| SRC-MW-PLAY | matlab/agent-skills-playground | https://github.com/matlab/agent-skills-playground | MathWorks (matlab org) | fetched 2026-10-08 | Read (primary) |
| SRC-17GOLANG | 豆包AI如何分析数据并生成图表 | https://www.17golang.com/article/535395.html | 17golang | 2026-03-18 | Read (secondary/SEO) |
| SRC-JC-IDENTITY | Identity-Based Habits | https://jamesclear.com/identity-based-habits | James Clear (author) | undated | Read (primary author page) |
| SRC-JC-3STEPS | How To Start New Habits That Actually Stick | https://jamesclear.com/three-steps-habit-change | James Clear (author) | undated | Read (primary author page) |
| SRC-JC-ATOMIC | Atomic Habits (book page) | https://jamesclear.com/atomic-habits | James Clear / publisher | 2018-05-25 | Read (primary author page) |
| SRC-GBRAIN-README | garrytan/gbrain README | https://github.com/garrytan/gbrain | Garry Tan | fetched 2026-10-08 | Read (primary) |
| SRC-GBRAIN-SCHEMA | gbrain/docs/GBRAIN_RECOMMENDED_SCHEMA.md | https://github.com/garrytan/gbrain/blob/master/docs/GBRAIN_RECOMMENDED_SCHEMA.md | Garry Tan / contributors | fetched 2026-10-08 | Read (primary) |
| SRC-GBRAIN-ORIGIN | gbrain/docs/ethos/ORIGIN.md | https://github.com/garrytan/gbrain/blob/master/docs/ethos/ORIGIN.md | Garry Tan / contributors | fetched 2026-10-08 | Read (primary) |
| SRC-KARPATHY-WIKI | LLM Wiki (idea file) | https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f | Andrej Karpathy | 2026-04-02/04 | Read (primary gist) |
| SRC-KWIKI-DOCS | Karpathy's LLM Wiki Pattern (docs) | https://ronancodes.github.io/llm-wiki/docs/research/karpathy/ | ronancodes (third-party) | fetched 2026-10-08 | Read (secondary) |
| SRC-TODAY-HOME | Today · 真正懂你的 AI 个人助理 | https://today.ai/articles/zh-Hans | Today (first-party) | undated | Read (vendor page) |
| SRC-TODAY-BLOG | 我们为什么做 Today：记忆、主动、执行 | https://today.ai/articles/zh-Hans/blog/meet-today | Junyuan (first-party) | 2026-08-03 | Read (vendor page) |
| SRC-TODAY-AITNT | Today AI 国内版上线，齐俊元想做一个… | https://www.aitntnews.com/newDetail.html?newId=29892 | aitntnews | 2026-09-30 | Read (secondary review) |
| SRC-TODAY-AIXQ | Today AI，试图读懂属于你的数字世界 | https://www.aixq.cc/61994.html | AI星球 | 2026-08-13 | Read (secondary) |
| SRC-TODAY-BAAI | 豆包PC端前负责人，创业Agent操作系统 | https://hub.baai.ac.cn/view/58269 | 智源社区 | 2026-09-25 | Read (secondary) |
| SRC-WORKBUDDY-10X | ai-10x-learning skill (authors' own description) | https://www.cnblogs.com/laoluo2025/p/21936935 | 老羅 (author) | 2026-07-26 | Read (author page) |
| SRC-WEREAD-10X | 用Claude、Codex、Workbuddy 10倍速学习任何知识 | https://weread.qq.com/web/reader/552323d0813abbc5cg01570e | 微信读书 (book listing) | undated | Read (book listing) |
| SRC-EINKCN-10X | 用 Claude/Codex/Workbuddy 10倍速学习任何知识 | https://einkcn.com/html/product_6a5b8cde37ed91961.html | einkCN | 2026-07-18 | Read (secondary) |
| SRC-STANFORD-STORM | Stanford STORM (referenced by the 10-step method) | (referenced, not separately fetched) | Stanford | — | `UNKNOWN` (not fetched this session) |
| SRC-NBS-2025 | 服务业经济稳定增长 转型升级步伐加快 | https://www.stats.gov.cn/sj/sjjd/202601/t20260119_1962335.html | 国家统计局 (NBS) | 2026-01-19 | Read (official statistics) |
| SRC-NBS-145 | “十四五”经济社会发展成就系列报告之十一 | https://www.stats.gov.cn/sj/sjjd/202606/t20260604_1963887.html | 国家统计局 (NBS) | 2026-06-04 | Read (official statistics) |
| SRC-36KR-SVC | 100万亿服务业：美国走过了繁荣… | https://www.36kr.com/p/3778990116811273 | 36氪 | 2026-04-23 | Read (secondary analysis) |
| SRC-XINHUA-SVC | 开放合作 提升服务业国际竞争力影响力 | https://www.news.cn/politics/20260426/b53a37849c2b4047ae435c562082237a/c.html | 新华网 | 2026-04-26 | Read (official commentary) |
| SRC-GUANCHA | 外媒称中国民众对AI乐观度远高于美国 | https://www.guancha.cn/GongSi/2026_08_25_828527.shtml | 观察者网 | 2026-08-25 | Read (secondary) |
| SRC-WIRED-INSTINCT | I Think I Found an AI Agent Worth the Risk | https://www.wired.com/story/i-finally-found-an-ai-agent-worth-the-risk/ | WIRED (Zoë Schiffer) | 2026-09-24 | Read (journalism) |
| SRC-FORBES-INSTINCT | AI Assistant Instinct Hits $2.5 Billion Valuation… | https://www.forbes.com/sites/iainmartin/2026/08/26/… | Forbes (Iain Martin) | 2026-08-26 | Read (journalism) |
| SRC-MLQ-INSTINCT | Instinct raises $250M… | https://mlq.ai/news/instinct-raises-250-million-for-private-beta-ai-assistant-at-25-billion-valuation/ | MLQ News | 2026-08-27 | Read (secondary) |
| SRC-YAHOO-40 | 40% of users hand their credit card to AI assistant Instinct… | https://finance.yahoo.com/technology/ai/articles/40-users-hand-credit-card-090000206.html | Yahoo Finance (Victoria Vesovski) | 2026-10-01 | Read (interview reporting) |
| SRC-TBPN-INSTINCT | How Instinct Hit $1B in Transaction Volume in Six Months | https://www.thepodcastsummary.com/episodes/bDVLnSIbrlU/… | TBPN summary (John Coogan claims) | 2026-10-04 | Read (podcast summary) |
| SRC-TRAVEL-INSTINCT | Travel Makes Up Half of Instinct's $1 Billion AI Transaction Volume | https://traveltradedesk.com/articles/… | Travel Trade Desk | 2026-09-28 | Read (secondary) |
| SRC-INFER-INSTINCT | The first number behind Instinct's $10 billion mark | https://theinference.org/article/… | The Inference | 2026-09-30 | Read (secondary) |
| SRC-SVTR-INSTINCT | Instinct · SVTR | https://svtr.ai/orgs/instinct?lang=en | SVTR | fetched 2026-10-08 | Read (database) |
| SRC-EDU-CSTOL | 促进认知迁移的在线学习课程设计与实证研究 | https://statics.scnu.edu.cn/pics/smartlearning/2021/0508/1620471183109051.pdf | 华南师范大学 (CNKI PDF) | 2021-05-08 | Read (academic) |
| SRC-EDU-COGN | 认知心理学视角下学习迁移与能力生成研究 | https://pdf.hanspub.org/ae2025151_1711168463.pdf | 蔡朝阳，周黎婧 (Hanspub) | 2025 | Read (academic) |
| SRC-CHINADAILY-TRANSFER | 课堂要实现有效的学习迁移 | https://column.chinadaily.com.cn/a/202411/12/WS6732fc8ca310b59111da2fcf.html | 中国日报网 (吴艳鹏) | 2024-11-12 | Read (commentary) |
| SRC-SKILLHUB-AB | agent-browser skill on SkillHub | https://skillhub.cn/skills/agent-browser | SkillHub | undated | Read (registry listing) |
| SRC-WORKBUDDY-AB | Agent Browser · WorkBuddy docs | https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/WorkBuddy-Zero-Cost-Skill-Top-10/Agent-Browser | WorkBuddy (first-party docs) | undated | Read (first-party docs) |
| SRC-VERCEL-AB | vercel-labs/agent-browser SKILL.md | https://github.com/vercel-labs/agent-browser/blob/main/skill-data/core/SKILL.md | Vercel Labs | fetched 2026-10-08 | Read (primary) |
| SRC-SKILLSMP-AB | Agent Browser (skill metadata) | https://skillsmp.com/creators/zhouxiumin/zxm-skills/skills-agent-browser-skill | skillsmp (zhouxiumin) | 2026-03-30 (modified) | Read (third-party registry) |
| SRC-TC-AB | How to Use WorkBuddy Agent Browser Skill | https://www.tencentcloud.com/techpedia/144335 | Tencent Cloud | 2026-07-31 | Read (secondary) |

## 3. Per-candidate source coverage

Legend: **P** = primary/first-party read; **S** = secondary read; **X** = attempted but blocked;
**N** = not found.

| # | Candidate | Primary (P) | Secondary (S) | Gaps |
|---|---|---|---|---|
| 1 | 华为鸿蒙小艺帮帮忙 | SRC-HW-01, SRC-HW-02 | SRC-ITHOME, SRC-DONEWS, SRC-FENGLIKA, SRC-PCONLINE; local SRC-LOCAL-A2A | A2A/Hermes wire spec JS-gated (`SRC-HW-03/04/05` body `UNKNOWN`); no Huawei account; no device run. |
| 2 | 补天漏洞平台 | SRC-BUTIAN-FAQ, SRC-BUTIAN-ZC, SRC-BUTIAN-NEW | SRC-BUTIAN-PLAN, SRC-VULBOX | No public per-user earnings proof; no "AI 辅助变现" first-party policy page read. |
| 3 | Vibe Coding 2026 | SRC-KARPATHY-VIBE | SRC-WIKI-VIBE, SRC-ARXIV-VIBE, SRC-BI-KARPATHY, SRC-TOI-VIBE; security stats SRC-VERACODE/2, SRC-CODEQL-24, SRC-CSA, SRC-NORMA26 | The video's specific security statistic is unknown (no transcript); only the general corpus is verified. |
| 4 | 豆包工作 MATLAB skills | SRC-GH-API-MATLAB, SRC-MATHWORKS, SRC-MW-PLAY, SRC-GH-Samuel | SRC-17GOLANG | `SamuelQQ/matlab-skills` **not found** (GitHub API 404 on user; specific repo `N`). Video's "豆包工作" attribution `UNKNOWN`. |
| 5 | 《原子习惯》 | SRC-JC-IDENTITY, SRC-JC-3STEPS, SRC-JC-ATOMIC | — | Chinese-translation specifics / page numbers not read. |
| 6 | GBrain/LLM Wiki | SRC-GBRAIN-README, SRC-GBRAIN-SCHEMA, SRC-GBRAIN-ORIGIN, SRC-KARPATHY-WIKI | SRC-KWIKI-DOCS | Vendor metrics (155,795 pages; +31.4 P@5; "十万页"; "Skill 自进化") are self-reported; no independent benchmark read. |
| 7 | Today AI | SRC-TODAY-HOME, SRC-TODAY-BLOG | SRC-TODAY-AITNT, SRC-TODAY-AIXQ, SRC-TODAY-BAAI | No independent hands-on benchmark; feature lists are vendor/reviewer claims. |
| 8 | WorkBuddy 十步速学 | SRC-WORKBUDDY-10X (author repo page) | SRC-WEREAD-10X, SRC-EINKCN-10X | `SRC-STANFORD-STORM` not fetched; "10x" and "25% memory" claims have no primary study; video date 2026-11-09 is in the future. |
| 9 | AI服务业改革开放2.0 | SRC-NBS-2025, SRC-NBS-145, SRC-XINHUA-SVC | SRC-36KR-SVC, SRC-GUANCHA | "AI红利推测/注意力退化不可逆/名人子女电子产品限制" — no first-party source read for these specific assertions. |
| 10 | Instinct AI | SRC-WIRED-INSTINCT, SRC-INFER-INSTINCT | SRC-FORBES-INSTINCT, SRC-MLQ-INSTINCT, SRC-YAHOO-40, SRC-TBPN-INSTINCT, SRC-TRAVEL-INSTINCT, SRC-SVTR-INSTINCT | GMV/take-rate not audited; "推理成本" not disclosed; privacy incidents reported second-hand. |
| 11 | 触类旁通 | SRC-EDU-CSTOL, SRC-EDU-COGN | SRC-CHINADAILY-TRANSFER | No single canonical "触类旁通" paper; mechanism synthesized from transfer/cognitive-flexibility literature. |
| 12 | WorkBuddy agent-browser | SRC-VERCEL-AB, SRC-WORKBUDDY-AB | SRC-SKILLHUB-AB, SRC-SKILLSMP-AB, SRC-TC-AB | "并行3任务" as an official limit not confirmed; permission audit scoped to the open-source CLI skill only. |

## 4. Explicit non-claims

- No Huawei HarmonyOS device test was performed; no official statement is asserted beyond the
  quoted support pages.
- No Cloudflare Canonical record was read (no connector/credential); see
  `CANONICAL_READ_UNAVAILABLE`.
- No Instinct, Today, gbrain or WorkBuddy account was used; all product metrics are as reported
  by the cited parties, not independently measured.
- No URL in this manifest is invented; the only non-navigable reference is
  `SRC-STANFORD-STORM`, which is explicitly marked `UNKNOWN` (not fetched).
