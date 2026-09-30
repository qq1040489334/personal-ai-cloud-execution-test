# MUSE_HOME_XIAOYI_HERMES_A2A_COMPATIBILITY_AUDIT_20260930

- Task: `cf-930068863258` — `MUSE_HOME_XIAOYI_HERMES_DIRECT_A2A_COMPATIBILITY_AUDIT_V0.2`
- Risk: `LOW` — read-only protocol/source audit, one Markdown artifact only.
- Date: 2026-09-30 (UTC).
- Audited repository checkout: `personal-ai-cloud-execution-test` @ `dca542e218629844e31d8048342bd9c29e0f1273`
  (working-tree base before this report; `git rev-parse HEAD`).
- Audited Hermes upstream: `NousResearch/hermes-agent` pinned to
  `f42f579cf8bac4918ac9599bece71618afadd846` (branch `main`, committer date
  2026-09-30T04:59:14Z; top commit `Merge pull request #128011`, fetched via the
  public GitHub API during this task).
- Business outcome (this audit): **direct native compatibility = NO** (see §6).
  End-to-end Golden: **NOT RUN / PARTIAL** (no real two-sided run evidence exists).
- Scope discipline: **no** Huawei account credentials, no production config or
  write endpoint, no deployment, no invitation/whitelist change, no business
  code / architecture / workflow / worker change. The only repository change is
  this file.

## 1. Method, evidence classes and limits

Evidence is labelled on every row and claim:

- **DOCUMENTED** — stated in a first-party source (Huawei official developer docs
  on `developer.huawei.com`, or Hermes upstream source at the pinned commit).
- **OBSERVED** — directly read by this task from a checked-out tree / live public
  API response (file + line, or HTTP JSON).
- **INFERRED** — reasoned from DOCUMENTED/OBSERVED facts; explicitly not a
  vendor guarantee.
- **UNKNOWN** — not publicly readable / not available in the checked-out repo.
  No login, credential request or private-namespace access was attempted.

Read limits that produced UNKNOWN rows:

1. Several Huawei `developer.huawei.com` doc pages are JavaScript-rendered; a
   plain fetch returns only the page shell (`文档中心`). Concrete protocol text
   was obtained from the search-engine index of those same official URLs and
   from the official-doc mirror `YouniQiao/developer_hos` (secondary copy of
   `agent2agent-comments-0000002500412353.md`). Statements that could not be
   confirmed publicly (full field tables of `云A2A协议消息指令定义`, the
   `agent2agent-define-*` parameter pages, and any login-gated normative spec)
   are marked **UNKNOWN**, not guessed.
2. The current checkout contains **no** Xiaoyi/Hermes/OpenClaw/A2A POC evidence:
   `git grep -i -e hermes -e xiaoyi -e openclaw -e a2a` over the working tree and
   over visible history returns no protocol artifacts (the only `a2a` hits are the
   substring inside the unrelated commit id `0c3ac20392bf86bfecb68cbaadd77a7a2a398665`).
   Other repositories that were not checked out (the real MUSE/home deployment,
   the Hermes runtime instance, any OpenClaw host) are **UNKNOWN** by construction.

## 2. Naming caution: Huawei "A2A" is not Linux Foundation A2A v1.0

This audit deliberately does **not** equate the two protocols.

- **Huawei / HarmonyOS "A2A"** (小艺开放平台 `云A2A模式` and `端A2A模式`) is the
  *鸿蒙 Agent通信协议*: a single POST endpoint speaking "Streamable HTTP + JSON
  RPC", with its own session and authorization dialect
  (`agent-session-id`, `sessionId`, `agentLoginSessionId`, `initialize`,
  `notifications/initialized`, `clearContext`, `authorize`, `deauthorize`,
  `push`). Huawei states it is "兼容谷歌 A2A `message/stream`" at the RPC-name
  level, but the session/auth/response envelope is Huawei-defined. **DOCUMENTED.**
- **Hermes** implements the *open Agent2Agent protocol v1.0* stewarded by the
  Linux Foundation (A2A v1.0.1 research per its own PR notes), with PascalCase
  methods, A2A `Task`/`contextId` semantics, and standard bearer auth.
  **OBSERVED / DOCUMENTED.**

The only wire-level overlap is the method name `message/stream` and the use of
SSE. That overlap is necessary but not sufficient for direct compatibility (§6).

## 3. Sources

### 3.1 Huawei first-party sources (official)

| # | Title | Official URL | Updated / version | Read status |
|---|---|---|---|---|
| H1 | 平台特性与能力体系 (端/云 A2A 接入与运行) | https://developer.huawei.com/consumer/cn/doc/service/platform-strength-0000001193466742 | n/a | DOCUMENTED (index) |
| H2 | A2A协议接入方案 | https://developer.huawei.com/consumer/cn/doc/service/agent2agent-0000002498656261 | 2026-06-12 | DOCUMENTED (index) |
| H3 | 云A2A协议技术规范 | https://developer.huawei.com/consumer/cn/doc/service/agent2agent-comments-0000002500412353 | 2026-06-12 | DOCUMENTED (index + official-doc mirror) |
| H4 | 云A2A模式 (A2A 基础配置: API URL / 会话方式 / 认证信息) | https://developer.huawei.com/consumer/cn/doc/doccenter-celia/cloud-a2a-0000002640266052 | n/a | DOCUMENTED (index) |
| H5 | 云A2A协议消息指令定义 (incl. 发起会话 `message/stream`) | https://developer.huawei.com/consumer/cn/doc/doccenter-celia/agent2agent-define-0000002467293060 ; https://developer.huawei.com/consumer/cn/doc/doccenter-celia/message-stream-0000002505761434 | n/a | DOCUMENTED (index), full field tables **UNKNOWN** |
| H6 | 云A2A协议消息指令定义 — 响应data数据结构定义 | https://developer.huawei.com/consumer/cn/doc/service/response-data-0000002505931382 | 2026-02-13 | UNKNOWN (JS-gated, not publicly readable) |
| H7 | 端A2A协议消息指令定义 | https://developer.huawei.com/consumer/cn/doc/service/agent2agent-device-commands-0000002594605828 | 2026-07-02 | UNKNOWN (JS-gated, not publicly readable) |
| H8 | A2A基础配置 | https://developer.huawei.com/consumer/cn/doc/service/a2a-basic-configuration-0000002437785686 | n/a | index only; field table **UNKNOWN** |
| H9 | OpenClaw模式 | https://developer.huawei.com/consumer/cn/doc/doccenter-celia/openclaw-0000002518410344 | n/a | DOCUMENTED (index) |
| H10 | A2A协议接入方案 (exp-other) | https://developer.huawei.com/consumer/cn/doc/service/agent2agent-exp-other-0000002660585433 | 2026-07-02 | index only |

Secondary corroboration for the Huawei wire shapes (not a first-party source, used
only to confirm the official text): 51CTO/HarmonyOS community write-up
"小艺开放平台最佳实践——云A2A智能体协同京东Agent"
(https://ost.51cto.com/posts/54751, 2026-08-04). Treated as **INFERRED** where it
goes beyond H2–H5.

### 3.2 Hermes upstream (pinned commit, first-party code)

Repo: `https://github.com/NousResearch/hermes-agent`. Pinned commit
`f42f579cf8bac4918ac9599bece71618afadd846`. All line numbers below were read from
`plugins/platforms/a2a/*` at that commit (raw.githubusercontent.com).

### 3.3 Local checkout

`personal-ai-cloud-execution-test` @ `dca542e218629844e31d8048342bd9c29e0f1273`.
No A2A/Xiaoyi/Hermes/OpenClaw POC artifact found (see §1.2).

## 4. Huawei 云A2A / 鸿蒙 Agent通信协议 — documented facts

All DOCUMENTED unless noted.

- **Transport / endpoint**: "统一一个 Endpoint，仅 POST 方法，采用 Streamable
  HTTP+JSON RPC 协议，服务器侧不用维护长链接，支持断线重连" (single endpoint,
  POST only, JSON-RPC; server holds no long-lived connection; reconnect
  supported). H2/H3.
- **RPC methods** (鸿蒙 Agent通信协议规范): `initialize`,
  `notifications/initialized`, `message/stream`, `tasks/cancel`,
  `clearContext`, `authorize`, `deauthorize`, `push`. H3.
- **Session model**:
  - Mode 1 (recommended): session state kept via server-issued
    `agent-session-id` carried in an HTTP header (analogous to MCP
    `mcp-session-id`); server MUST implement `initialize` and
    `notifications/initialized`; server must keep ≥5 concurrent session ids per
    AK/SK/APIKey/OAuth client. H3.
  - Mode 2 (simplified): stateless; every request carries the auth credential
    in the header; `initialize`/`notifications/initialized` are not required. H3.
- **Client→server request shape** (`message/stream`, H5 发起会话): POST with
  `Content-Type: application/json`, header `agent-session-id: <id>`, body
  `{"jsonrpc":"2.0","id":"<seq>","method":"message/stream","params":{"id":"<taskId>","sessionId":"...","agentLoginSessionId":"...","message":{"role":"user","parts":[{"kind":"text","text":"..."}|{"kind":"data","data":{...}}]}}}`.
- **Server→client SSE response shape** (`message/stream`, H5):
  `{"jsonrpc":"2.0","id":"<echo>","result":{"taskId":"<taskId>","kind":"status-update","final":true|false,"status":{"message":{"role":"agent","parts":[{"kind":"text","text":"..."}]},"state":"submitted|working|input-required|completed|canceled|failed|unknown"}}}`.
  Error object: `error.code` (0 success; `99911114` content non-compliant;
  `99911113` flow control). `final:true` closes the端云 task channel.
- **Auth** (`A2A基础配置`, H4/H3): AK/SK pre-shared-key signature
  (`sign=Base64(HMAC-SHA256(secretKey, ts))` with `accessKey`/`sign`/`ts`
  headers — an SDK-signature scheme, not an A2A bearer token), OAuth 2.0
  **client-credentials only**, or APIKey/header or APIKey/query. All auth
  parameters are carried in request headers (or query for the discouraged
  mode). H4, corroborated by the access-key/sign/ts field table in the related
  official `实现接口定义` page.
- **Huawei account authorization**: `authorize`/`deauthorize` + server-issued
  `agentLoginSessionId` bind a Huawei account to a third-party agent session;
  account one-click login requires a Huawei developer `appId` /
  `Client ID` registered on 小艺开放平台, and the server exchanges a Huawei
  account authorization code for a phone number. H3.
- **Discovery**: 云A2A configuration is an explicitly entered **API URL**
  ("与智能体对话时的访问接口"), plus session mode and auth config. H4. **No
  Agent Card / `.well-known/agent-card.json` discovery step is documented** for
  Huawei's cloud A2A.
- **Output**: platform renders structured "卡片" (cards) chosen by a preset
  card id (≤20 per agent); plus extension commands for session termination,
  context clearing, and offline Push. H4/H5.
- **Device/system variables** (端A2A, INFERRED): message `data` parts carry
  `variables.systemVariables` such as `device_type`, `display_version`,
  `market_name`, `push_id` (from community implementation notes; the official
  H7 page is JS-gated = UNKNOWN).

## 5. Hermes A2A inbound — observed implementation at pinned commit

All OBSERVED from `plugins/platforms/a2a/*` @
`f42f579cf8bac4918ac9599bece71618afadd846`.

| Aspect | Fact | File:line |
|---|---|---|
| Plugin kind / version | platform plugin `a2a-platform`, `version: 1.0.0`, protocol v1.0 | `plugin.yaml:1,4,6` |
| Enable | `register()` registers inbound platform + outbound tools; enabled via `gateway.platforms.a2a.enabled` or scoped `A2A_PORT` | `__init__.py:87-106`; `__init__.py:35-47`; `README.md:14-21` |
| Default port / bind | port `9900`; host `127.0.0.1`; only widens to `0.0.0.0` when a token is set **and** `A2A_HOST` given | `adapter.py:35,273`; `security.py:71,76-84` |
| Agent Card discovery | `GET /.well-known/agent-card.json` and legacy `/.well-known/agent.json` | `adapter.py:195-202`; `protocol.py:59-79` |
| Card contents | `name, description, url, version 1.0.0, supportedInterfaces[{url,protocolBinding:JSONRPC,protocolVersion:1.0}], capabilities{streaming,pushNotifications}, defaultInputModes/OutputModes: text/plain, skills[]`; `securitySchemes: http bearer` when remote | `protocol.py:65-79` |
| JSON-RPC methods | v1.0 PascalCase + legacy aliases: `SendMessage`/`message/send`, `SendStreamingMessage`/`message/stream`, `GetTask`/`tasks/get`, `ListTasks`/`tasks/list`, `CancelTask`/`tasks/cancel`, `SubscribeToTask`/`tasks/subscribe`, push-config CRUD | `adapter.py:47-63` |
| Methods **not** implemented | `initialize`, `notifications/initialized`, `clearContext`, `authorize`, `deauthorize` → JSON-RPC `-32601 method not found` | `adapter.py:242` (no table entry in `:47-63`) |
| Request format | `params.message.parts[]` (`text`/`url`/`file.fileWithUri`/`raw`/`data`), `contextId` inside the message (legacy top-level tolerated); body `params` must be an object; optional `A2A-Version: 1.0` | `protocol.py:155-182`; `adapter.py:229-238` |
| Auth | `Authorization: Bearer <token>` only; per-peer tokens `A2A_PEER_TOKENS` or shared `A2A_BEARER_TOKEN`; else localhost-only. No HMAC/AK-SK signature scheme. | `security.py:86-100`; `security.py:67-84` |
| Session semantics | state keyed by A2A `contextId`; no `agent-session-id` header, no `sessionId`, no `agentLoginSessionId` | `adapter.py:528-572`; `protocol.py:179-182` |
| Task lifecycle states | `TASK_STATE_SUBMITTED/WORKING/INPUT_REQUIRED/COMPLETED/FAILED/CANCELED/REJECTED` | `protocol.py:24-28`; `protocol.py:185-207` |
| Task query (long tasks) | `GetTask`, `ListTasks` (paged), `SubscribeToTask` (SSE reconnect) | `adapter.py:719-754` |
| Completion / failure | future resolved by live session `send()` or `on_processing_complete`; terminal task built with `status.message` + `artifacts` | `adapter.py:612-625,828-860`; `protocol.py:185-193` |
| Stream | `message/stream` → `text/event-stream`; each frame is a JSON-RPC envelope containing a v1.0 `StreamResponse`: `{"task":…}` then `{"statusUpdate":…}`/`{"artifactUpdate":…}`; closure as SSE comment `: done`; **no `kind`, no `final`, states are SCREAMING_SNAKE** | `adapter.py:697-717`; `protocol.py:196-219` |
| Push | outbound webhook POST with `X-A2A-Signature` HMAC-SHA256; push-config CRUD | `adapter.py:775-826`; `security.py:108-113` |
| Timeout | reply window `A2A_REPLY_TIMEOUT` (default 300s); orphan sweep floor 300s / ceiling 86400s | `adapter.py:66-76`; `adapter.py:363-367` |
| Cancel | `tasks/cancel` marks `TASK_STATE_CANCELED`, resets the anti-loop turn counter | `adapter.py:756-766` |
| Live gateway session | inbound task → `MessageEvent` → `handle_message` on the gateway loop; the reply returns through `adapter.send()` fulfilling the per-context future — same agent, memory and tools as other channels | `adapter.py:558-572`; `adapter.py:828-836` |
| Network reachability | remote requires bearer token + `A2A_HOST`; behind a proxy set `A2A_PUBLIC_URL` or rely on `X-Forwarded-Host`/`Proto` | `security.py:76-84`; `adapter.py:185-193` |
| Outbound peers | lists "OpenClaw" among A2A-compliant peers (Linux-Foundation A2A sense) | `plugin.yaml:12`; `README.md:5` |

## 6. Field-level compatibility matrix (Huawei 云A2A client → Hermes inbound)

Legend: M = MATCH, X = MISMATCH, ? = UNKNOWN. Each row cites evidence.

| # | Field / concern | Huawei side (DOCUMENTED) | Hermes side (OBSERVED) | Verdict | Evidence |
|---|---|---|---|---|---|
| 1 | Discovery / Agent Card | Explicit **API URL** configured on 小艺开放平台; no Agent Card discovery documented | Serves `/.well-known/agent-card.json` + `agent.json`; also accepts direct POST to `/` | **X** | H4 vs `adapter.py:195-202`; Hermes card is unnecessary to Huawei and Huawei does not read it |
| 2 | Auth signature | AK/SK `accessKey`+`sign=Base64(HMAC-SHA256(sk,ts))`+`ts`, or OAuth2 client-credentials, or APIKey header/query; all in headers | Bearer token only (`Authorization: Bearer …`); no HMAC/AK-SK verifier | **X** (default) / **?** (coercible) | H4; `security.py:86-100`. If APIKey/Header mode is configured to emit `Authorization: Bearer <A2A_BEARER_TOKEN>`, auth *could* pass — INFERRED, not a documented Huawei guarantee |
| 3 | Request method set | `initialize`, `notifications/initialized`, `message/stream`, `tasks/cancel`, `clearContext`, `authorize`, `deauthorize`, `push` | v1.0 Pascal + legacy aliases; **no** `initialize`/`notifications/initialized`/`clearContext`/`authorize`/`deauthorize` | **X** | H3 vs `adapter.py:47-63,242`. Mode 1 (recommended) always fails at `initialize`; Mode 2 skips it |
| 4 | Request payload shape | `params.{id, sessionId, agentLoginSessionId, message:{role,parts[{kind,text|data}]}}` | `params.message.parts[]`; ignores `params.id`/`sessionId`/`agentLoginSessionId`; `contextId` preferred | **X** | H5 vs `protocol.py:155-182`. Text extraction is tolerant, but session/context identity is lost |
| 5 | Session / task state | `agent-session-id` header (Mode 1), `sessionId`, `agentLoginSessionId`; `clearContext` to reset | A2A `contextId`; no header/session id; no `clearContext` | **X** | H3/H5 vs `adapter.py:528-572`, `protocol.py:179-182` |
| 6 | Task state vocabulary | lowercase hyphen: `submitted\|working\|input-required\|completed\|canceled\|failed\|unknown` | `TASK_STATE_SUBMITTED\|…\|TASK_STATE_REJECTED` (SCREAMING_SNAKE) | **X** | H5 vs `protocol.py:24-28` |
| 7 | Streaming response envelope | SSE `result.{taskId,kind:"status-update",final,status:{state,message}}` | SSE JSON-RPC envelope `result.{task\|statusUpdate\|artifactUpdate}`; **no `kind`, no `final`**; closure is `: done` | **X** | H5 vs `adapter.py:687-717`, `protocol.py:196-219` (explicit "no `kind`/`final`") |
| 8 | Long-task query | No documented `tasks/get`/`tasks/list`/`tasks/subscribe`; extension `push` + card output instead | `GetTask`, `ListTasks`, `SubscribeToTask` | **X** | H3 vs `adapter.py:719-754`. (Huawei param pages for these = UNKNOWN; `tasks/get` is simply not in the documented method list) |
| 9 | Cancel | `tasks/cancel` (blocking, by Huawei task/session) | `tasks/cancel` exists; expects `params.taskId`/`id` | **?** | Method name M (H3 vs `adapter.py:756-766`), but Huawei `tasks/cancel` payload/session key is **UNKNOWN** (JS-gated), so end-to-end is unproven |
| 10 | Timeout / connectivity | "服务器侧不用维护长链接，支持断线重连"; `final` closes the channel; reconnect via `message/stream` | 300s reply window; orphan sweep; `SubscribeToTask` reconnect | **X** | H3/H5 vs `adapter.py:66-76,719-732`; different reconnect contract |
| 11 | Push / long-task completion | Huawei `push` = server→client PUSH via Huawei Push Kit (`push_id`), plus card id output | Outbound webhook POST to a registered URL, HMAC `X-A2A-Signature`; no Huawei Push | **X** | H4/H5 vs `adapter.py:802-826`. Requires a Huawei Push integration that Hermes does not have |
| 12 | Result presentation | Structured 卡片 (preset card id, ≤20) rendered by the platform; text markdown/图片/data parts | Returns plain-text A2A `Task`/`Artifact` + text Parts; no Huawei card ids | **X** | H4 vs `protocol.py:185-207` |
| 13 | Output states / errors | `error.code` 0 / 99911114 / 99911113; `status.state` set above | A2A/JSON-RPC codes `-32001…-32052`; no 99911xxx | **X** | H5 vs `protocol.py:36-38`, `adapter.py:218-248` |
| 14 | Live agent session | n/a (client is 小艺) | Inbound tasks are injected into the **live** gateway session, same agent/memory/tools; reply fulfils the HTTP future | **M (Hermes-side property)** | `adapter.py:558-572,828-836`; README `:51-54`. This is a Hermes strength, not a bridge |
| 15 | Reachability (remote) | 小艺 platform calls the configured HTTPS API URL | Requires a bearer token AND `A2A_HOST=0.0.0.0` AND a routable `A2A_PUBLIC_URL`; else localhost-only | **X** (default) / **?** (configurable) | H4 vs `security.py:76-84`, `adapter.py:185-193`. Configuration is possible; the wire dialect still fails rows 3–7 |

Score: 1 MATCH (a Hermes-only property, row 14), 12 MISMATCH, 2 UNKNOWN/conditional.
No row is a clean two-sided MATCH.

## 7. Verdict: can native 小艺云 A2A connect directly to Hermes A2A?

**Direct compatibility: NO.**

Reasoning (INFERRED from the fields above):

1. The Huawei client is documented to speak its **own** session/response dialect.
   Even in the "simplified" Mode 2 (no `initialize`), Huawei sends
   `params.sessionId` / `params.agentLoginSessionId` and expects SSE frames of
   the form `result.kind == "status-update"`, `result.final`, and lowercase
   `status.state` (rows 4–7, 13). Hermes emits A2A v1.0 `statusUpdate` /
   `artifactUpdate` members with SCREAMING_SNAKE states and no `kind`/`final`
   (OBSERVED, `protocol.py:196-219`). A conforming Huawei client strict-parses
   the response; it will not accept Hermes's envelope, and vice-versa.
2. In the **recommended** Mode 1, Huawei first calls `initialize` /
   `notifications/initialized` and carries `agent-session-id`. Hermes returns
   `-32601 method not found` for both (OBSERVED, `adapter.py:47-63,242`), so the
   session cannot even be established.
3. Authentication is a second, independent blocker: Huawei defaults to AK/SK
   HMAC signatures / OAuth client-credentials / APIKey (headers), while Hermes
   authenticates only `Authorization: Bearer` (OBSERVED, `security.py:86-100`).
   The APIKey/header mode *might* be coerced to a bearer header, but that would
   be a **thin adapter/configuration**, not native compatibility — and it would
   not fix rows 3–7.
4. There is no Huawei-side Agent Card discovery and no Huawei Push mapping, so
   the two "discovery" and "long-task completion" planes also differ.

Therefore: native OOB (out-of-the-box) 小艺云 A2A → Hermes = **NO**. A
configuration-only partial handshake may be possible in Mode 2 with header-bearer
auth, but the response contract is still incompatible, so this is at best
**PARTIAL** and untested. It is not a PASS.

## 8. Next minimal path (only because direct = NO)

Compared as requested; no rewriting of the base, no implementation here.

### Option A — native 云A2A configuration (no Hermes change)
Not viable alone. It can satisfy auth (row 2, if Header/APIKey mode is used) and
reachability (row 15), but cannot satisfy the missing `initialize` /
`notifications/initialized` (Mode 1) or the response envelope (rows 3–7). It
would require the **third-party agent server itself** to implement the Huawei
dialect — which is exactly a Hermes-side adapter. **DOCUMENTED/INFERRED.**
Verdict: insufficient.

### Option B — thin Hermes adapter (keep Hermes as the base)
Smallest viable change surface (INFERRED, not implemented):
add a Huawei-compat shim in front of / beside
`plugins/platforms/a2a/adapter.py` that:
(a) serves a second route accepting the Huawei single-endpoint JSON-RPC;
(b) implements `initialize` / `notifications/initialized` returning
`agentSessionId`/`agentSessionTtl` and honours `agent-session-id`;
(c) maps `params.sessionId` → A2A `contextId` and ignores `agentLoginSessionId`
(or maps it to a peer identity) for Mode 2;
(d) translates the A2A v1.0 stream to Huawei's `result.kind:"status-update"` +
`final` + lowercase states, and maps terminal `final:true` / `tasks/cancel`;
(e) optionally maps `clearContext` to turn-tracker reset and `push` to a Huawei
Push call.
This is a compatibility **translation layer**, not a base replacement. It needs
Hermes-side code and tests, and real device validation. Verdict: plausible, the
recommended engineering direction; out of this audit's scope.

### Option C — OpenClaw
OpenClaw is a **separate, first-party Huawei mode** (`OpenClaw模式`), not the
cloud/端 A2A protocol. Huawei documents:
`openclaw plugins install @ynhcj/xiaoyi@latest`, an `openclaw.json` `channels.xiaoyi`
block with `ak`/`sk`/`agentId`, `openclaw gateway restart`, and the log marker
`info sent claw_bot_init` (H9, DOCUMENTED). That is an OpenClaw **channel
plugin**, with its own AK/SK + `agentId` binding — not evidence that OpenClaw
speaks Huawei's A2A dialect, and not evidence about Hermes.

Important non-sequitur to avoid: Hermes's `plugin.yaml`/`README.md` list
"OpenClaw" only as an example of a peer that is A2A-compliant in the
**Linux-Foundation A2A** sense (`plugin.yaml:12`, `README.md:5`). That does
**not** mean OpenClaw implements Huawei's 云A2A dialect, and it certainly does
not mean Hermes direct-connects to 小艺. Huawei supporting OpenClaw through its
own plugin does **not** imply Hermes's direct A2A is compatible.
Verdict: OpenClaw is a distinct fallback integration that would move the base,
so it is **not** selected here; Hermes remains the preferred base and Option B is
the preferred next step.

## 9. Shortest true-device Golden path — NOT RUN / PARTIAL

Status: **NOT RUN / PARTIAL**. No real two-sided run log exists; this audit had
no device, no Huawei credentials, no production endpoint and no authorization to
run. Per the contract, this is **not PASS**.

Shortest verifiable Golden (to be executed by an authorized operator, not by this
audit):

1. **Nonce**: choose a fresh random string, e.g. `golden-<utc-YYYYmmddHHMMSS>-<8 hex>`.
   It must be generated once and used in the user query text.
2. **Server side (Hermes base)**: start the gateway with the A2A platform
   enabled on a routable HTTPS endpoint and a bearer token
   (`gateway.platforms.a2a.enabled`, `A2A_HOST=0.0.0.0`, `A2A_BEARER_TOKEN`,
   `A2A_PUBLIC_URL`); capture Hermes gateway logs plus
   `~/.hermes/a2a_audit.jsonl` and the per-`contextId` persisted conversation.
3. **Client side (小艺开放平台)**: create a `云A2A模式` Agent whose API URL is the
   Step-2 endpoint; pick the session mode and auth; send the voice/text query
   containing the nonce.
4. **Assertion**: the exact nonce appears in (a) 小艺's rendered reply and
   (b) Hermes's `a2a_audit.jsonl` inbound record, with the same task/context.
5. Repeat one long task and one cancel, and one reconnect.

Expected blocker set (from §6): `initialize`/`notifications/initialized` (Mode 1)
and the SSE envelope/`kind`/`final`/state-vocabulary mismatch (rows 3–7, 13) —
i.e., a direct run is expected to fail until Option B (or equivalent) exists.
Because of this, the honest Golden result is **NOT RUN / PARTIAL → not PASS**.

## 10. Scope, safety and provenance statement

- Files changed in the repository by this task: **exactly one** —
  `docs/audits/MUSE_HOME_XIAOYI_HERMES_A2A_COMPATIBILITY_AUDIT_20260930.md`.
  Expected `scope_guard` result: PASS (no deletions, no forbidden paths, no
  changes outside the allowlist).
- **Not** accessed: Huawei account credentials, `appId`/`Client ID`, AK/SK, OAuth
  secrets; no 小艺开放平台 login; no production configuration, write endpoint or
  deployment; no real bilateral execution.
- **Not** changed: business source, existing architecture, workflows, worker,
  configuration, production state.
- End-to-end status: **NOT PASS** (no real two-sided evidence). Direct native
  compatibility: **NO**. Recommended next step: Option B (thin Hermes
  compatibility adapter), keeping Hermes as the base.

### Repeatable check summary (OBSERVED this task)

- `git rev-parse HEAD` (base) = `dca542e218629844e31d8048342bd9c29e0f1273`.
- Hermes pinned commit = `f42f579cf8bac4918ac9599bece71618afadd846`.
- Local suite: `python -m pytest -q` → **790 passed** (no test files added or
  modified; the task allowlist permits only the report path).
- Repo A2A/Xiaoyi/Hermes/OpenClaw POC evidence: none found (UNKNOWN / absent).
