# AI 公司任务状态只读投影器（Cloud Agent）

> 交付形态：可集成组件的**规范 + 参考实现 + 脱敏夹具 + 参考测试**。
> 本任务只按契约允许新增 `tools/ai-company-status-projection/README.md`，因此代码与测试以
> 可复制的参考实现形式随 README 交付；未新增服务、定时任务或第二状态库。
> 未部署、未接入现有 Windows UI、未写 Canonical、未调用真实生产写接口、未读取用户私密正文。

- task_id: `cf-0fd0bd1c2ce4`
- project_id: `ai-company-status-projection`
- risk_level: `LOW`
- 参考基线: `c9f4e05`（仓库当前 HEAD）

## 0. 结论先行

本组件解决的唯一问题是：**把既有任务接口已经返回的响应，按调用方给定的
`observed_at` / `now` / TTL 投影成 UI 可消费的最小只读状态元数据。** 它不是第二个状态库，
不是实时系统，也不是验收判定器。

已交付：

- 明确的输入/输出契约；
- `queued` / `running` / `completed` / `failed` / `blocked` / `pending_review` /
  `reviewed` / `unknown` 的语义映射；
- 新鲜度、缺时间、连接失败、重复 `task_id`、父子关系的确定性规则；
- 纯函数参考实现（仅 Python 标准库，无网络、无凭据、不读本地时钟）；
- 覆盖正常、失败、部分覆盖、重复、缺时间、过期、父子关系、结果已完未审等场景的
  脱敏合成夹具与参考测试；
- 已验证仓库接口清单与覆盖限制；
- Windows UI 的消费方式；
- 本地验证证据。

未交付 / 明确不支持：

- 全量活跃任务枚举；
- 实时推送、runner 心跳、原始日志、提示正文；
- 自动验收 PASS/FAIL 判定；
- 已接入用户页面或生产部署；
- Canonical 写入或任何生产写操作。

## 1. 目标与边界

现有 Windows UI 需要展示 Cloud Agent 任务状态，但仓库里已经存在多套状态语义：

- Worker MCP 的 `get_task_result` / `list_pending_results`；
- Python 侧 `hello.py` 的 `get_task_result` / `list_pending_results` / review 事件；
- `src/personal_ai_execution/status_contract.py` 与
  `src/personal_ai_execution/result_normalization.py` 的规范化状态契约；
- Worker / Python 各自的 registry 字段。

本组件**复用**这些模型，只做只读投影，不新增状态存储。它不修改任何现有生产文件，
也不把本地刷新时间伪装成源事件时间。

### 1.1 设计原则

1. **只读**：不调用 `submit_task`、`mark_reviewed`、`retry_task_dispatch` 等写接口。
2. **证据优先**：`completed` 只表示运行完成，不等于验收 `PASS`。
3. **失败闭合**：没有运行证据、观测时间缺失/过旧、连接失败时输出 `unknown`。
4. **调用方掌控时间**：`now` 与 `ttl_seconds` 必须由调用方传入；模块内部不读时钟。
5. **最小元数据**：不输出提示正文、密钥、原始日志、artifact 内容。
6. **幂等计数**：重复 `task_id` 只计一次；父子关系不造成父/子重复计数。

## 2. 已验证的仓库只读接口清单

以下接口是仓库中**真实存在**的，可作为投影器的输入来源。行号基于基线 `c9f4e05`。

| 接口 | 位置 | 读/写性质 | 可用字段（与本组件相关） | 覆盖限制 |
| --- | --- | --- | --- | --- |
| Worker MCP `get_task_result(task_id)` | `worker/index.js:3996`（定义）、`:4294`（分发） | 调用方视角只读；但内部 `finalizeTaskResult` / `persistTerminalExecution` 会回写 registry 并可能发完成事件 | `task_id`、`status`/`normalized_status`/`execution_status`、`terminal`、`workflow_conclusion`、`review_verdict`、`review_state`、`round`、`execution_summary`、`commit`、`tests`、`artifacts`、`execution_result_json`、`evidence` | 需要 MCP write scope；按 `task_id` 读取 artifact；无 artifact 时返回 `PENDING`；会回写终态 |
| Worker MCP `list_pending_results(scope)` | `worker/index.js:4020`（定义）、`:4297`（分发） | 调用方视角只读；内部会回写已确认终态 | 桶：`pending`、`pending_review`、`failed`、`blocked`、`unconfirmed`、`unresolved`；每条含 `status`/`execution_status`、`terminal`、`workflow_conclusion`、`result_available`、`reviewed`、`review_verdict`、`requires_review`、`project_id`/`root_task_id`/`parent_task_id`、`lineage`；另有 `counts`、`scope`、`excluded_by_lineage`、`lineage_unresolved` | **不是全量活跃列表**；只来自 registry；需要 MCP write scope；lineage 可被 scope 过滤；存在回写副作用 |
| Worker 内部 `listTasks` / `readTask` | `worker/index.js:1972` / `:2006` | 内部 KV 读 | registry 记录 | 未暴露为 MCP tool；Windows UI 不应直接依赖内部 KV 键格式 |
| Worker `buildTaskResult` / `verifiedResultStatus` | `worker/index.js:2619` / `:1610` | 纯投影/规范化 | 由 `execution_result.json` + GitHub run 结论导出执行状态 | Worker 内部函数，不是独立 API |
| Python `get_task_result(task_id)` | `hello.py:587` | 读；会读取仓库根 `execution_result.json` 并可能回写 registry | `execution_summary.task_id/status/round/summary`、`commit`、`tests`、`artifacts`、`execution_result_json`、`evidence` | 详细结果不是严格按 `task_id` 分文件；同一仓库根文件可能被多个任务复用；仅适合仓库内验证，不是多租户生产读接口 |
| Python `list_pending_results()` | `hello.py:1673` | 读；调用前会 `_sync_execution_result()`、`reconcile_registry_records()`、`ensure_auto_consumer_ran()` | 待审记录（`review_state="pending_review"`）、`requires_review`、`reviewed`、`review_verdict`、时间字段 | **只返回待审/成功类记录，不是全量活跃列表**；依赖进程内 `TASK_REGISTRY`；同步步骤有状态副作用 |
| Python `get_task_review(task_id)` | `hello.py:1784` | 只读 | 单个任务的 registry 视图（可能含 `review_verdict`、`reviewed_at`） | 进程内 registry，不是跨实例持久读 |
| Python `get_review_events(task_id)` | `hello.py:1764` | 只读 | append-only review 事件：`task_id`、`verdict`、`timestamp`、`note` | `note` 可能含人工备注；投影器不读取/输出该字段 |
| Python `classify_pending_task` / `expire_stale_pending` | `hello.py:3247` / `:3357` | 前者只读；后者可写 `timed_out` 标记 | 超时/卡住语义、`review_state` | 不是 UI 读接口；本组件只复用其“超时不得冒充成功”的语义 |
| `status_contract.py` | `src/personal_ai_execution/status_contract.py:35-121` | 纯函数/常量 | `EXECUTION_STATUSES`、`TERMINAL_STATUSES`、`REVIEW_STATES`、`WORKFLOW_CONCLUSION_TO_STATUS`、执行状态与 review verdict 分离 | 面向执行状态与 review verdict，不直接提供 UI 所需的新鲜度/去重投影 |
| `result_normalization.py` | `src/personal_ai_execution/result_normalization.py` | 纯函数 | GitHub workflow conclusion -> `PASS`/`FAIL`/`BLOCKED`/`PENDING`，fail-closed | 不包含 `queued`/`running` 的 UI 生命周期，也不做 TTL/去重 |

### 2.1 明确不作为输入/调用的接口

- `submit_task`（`worker/index.js:3978`、`hello.py:1637`）：写接口，不使用。
- `mark_reviewed`（`worker/index.js:4089`、`hello.py:1725`）：写接口，不使用。
- `retry_task_dispatch` / `submit_task` 等真实生产写路径：不调用。
- `expire_stale_pending(apply=True)`：会写 registry，不使用。
- 任何微信读取、Canonical 写入、部署命令：不涉及。

### 2.2 重要安全事实

`get_task_result` 与 `list_pending_results` 虽然对调用方表现为“读”，但 Worker 实现会在
确认终态时调用 `persistTerminalExecution`，Python `list_pending_results` 也会先做同步/对账。
因此：

- 本组件**只消费调用方已经拿到的响应**，不自行调用这些接口；
- Windows UI 若通过现有代理调用，应继续遵守现有 MCP scope 与写回语义；
- 投影器本身无网络、无凭据、无写操作。

## 3. API 不能提供的字段与能力

必须在 UI / 产品层明确这些限制，不能通过猜造填补：

| 能力 / 字段 | 为什么不能提供 |
| --- | --- |
| 全量活跃任务列表 | `list_pending_results` 只返回待审/失败/阻塞等桶，不是 registry 全量，更不是所有正在运行的任务 |
| 实时状态 / 推送 / WebSocket | 现有接口是请求-响应；没有事件流契约 |
| runner 心跳、当前步骤、实时耗时 | `get_task_result` 不返回实时 heartbeat；`execution_summary` 是结果摘要，不是运行遥测 |
| 原始执行日志 / stdout / stderr | 不在投影输入中；本组件禁止输出原始日志 |
| 提示正文、instructions、acceptance 文本 | 可能含用户私密内容；本组件只投影状态元数据 |
| 密钥、token、凭据、artifact 内容 | 禁止读取/输出 |
| 验收 `PASS` / `FAIL` 结论 | `completed` 只代表运行完成；验收结论需要既有 `review_verdict` 或人工评审，本组件不推导 |
| review verdict 的自动判定 | 只有 `mark_reviewed` 产生；本组件只透传已有字段 |
| 精确源事件时间 | 只能使用接口给出的 `updated_at` / `completed_at` / `last_update_at`；不能拿本地刷新时间代替 |
| 未注册任务 | registry 不存在的任务无法从这些接口得到 |
| 完整 lineage | Worker metadata 可能被截断/压缩；`list_pending_results` 会给出 `unresolved`，不能把缺失当成“无父任务” |
| 跨项目全量视图 | `list_pending_results` 可被 project/root lineage scope 过滤；未给 scope 时也不等于全平台 |
| `queued` / `running` 的权威真值 | 现有 registry 生命周期值是 advisory；没有运行证据时只能按 advisory 标注或输出 `unknown` |

## 4. 输入契约

投影器接收“既有任务接口响应中的记录数组”以及显式的观测时间。调用方应把响应原样映射为
下列最小信封；缺失字段保持缺失，不要补默认值。

```json
{
  "source": "worker.list_pending_results",
  "observed_at": "2026-10-17T12:00:00Z",
  "now": "2026-10-17T12:01:00Z",
  "ttl_seconds": 300,
  "connection_error": null,
  "records": [
    {
      "task_id": "cf-...",
      "parent_task_id": "cf-...",
      "project_id": "ai-company",
      "root_task_id": "cf-...",
      "status": "PASS",
      "execution_status": "PASS",
      "normalized_status": "PASS",
      "workflow_conclusion": "success",
      "run_status": "completed",
      "run_conclusion": "success",
      "terminal": true,
      "result_available": true,
      "requires_review": true,
      "reviewed": false,
      "review_state": "pending_review",
      "review_verdict": null,
      "updated_at": "2026-10-17T11:58:00Z",
      "completed_at": "2026-10-17T11:57:30Z"
    }
  ]
}
```

字段含义：

| 字段 | 必需性 | 说明 |
| --- | --- | --- |
| `source` | 必须由调用方给出 | 建议使用已验证接口名，如 `worker.get_task_result` / `worker.list_pending_results` / `python.list_pending_results` / `python.get_task_result` |
| `observed_at` | 必须 | 调用方**观测到该响应**的时间；不是任务源事件时间，也不能用其覆盖 `updated_at` |
| `now` | 必须 | 调用方评估时间；用于 TTL 判断 |
| `ttl_seconds` | 必须 | 调用方新鲜度预算；建议 UI 轮询 120–300 秒，但由调用方决定 |
| `connection_error` | 可选 | 传输失败时传 truthy；此时所有任务必须是 `unknown`，不能显示为 0 个任务或空队列 |
| `records` | 必须 | 既有接口返回的记录数组；允许部分覆盖 |

记录中可被消费的字段全部来自既有接口，不要求新增生产字段：

- 状态：`status`、`execution_status`、`normalized_status`、`workflow_conclusion`、
  `run_status`、`run_conclusion`、`terminal`、`result_available`；
- review：`reviewed`、`review_state`、`review_verdict`、`requires_review`；
- lineage：`task_id`、`parent_task_id`、`project_id`、`root_task_id`；
- 时间：`updated_at`、`completed_at`、`last_update_at`、`created_at`；
- dispatch：`dispatch_state`、`recommended_action`（仅用于识别明确阻塞）。

## 5. 输出契约

```json
{
  "source": "worker.list_pending_results",
  "observed_at": "2026-10-17T12:00:00Z",
  "projected_at": "2026-10-17T12:01:00Z",
  "ttl_seconds": 300.0,
  "complete": true,
  "batch_blocker": null,
  "tasks": [
    {
      "task_id": "cf-...",
      "source": "worker.list_pending_results",
      "observed_at": "2026-10-17T12:00:00Z",
      "runtime_state": "completed",
      "review_state": "pending_review",
      "blocker": null,
      "parent_task_id": null,
      "last_source_event_at": "2026-10-17T11:58:00Z",
      "evidence": "workflow_conclusion",
      "freshness": "fresh",
      "duplicate_count": 1,
      "observed_age_seconds": 60.0
    }
  ],
  "counts": {
    "raw_records": 1,
    "total_unique_tasks": 1,
    "duplicate_records": 0,
    "runtime_state": {
      "queued": 0,
      "running": 0,
      "completed": 1,
      "failed": 0,
      "blocked": 0,
      "unknown": 0
    },
    "review_state": {
      "pending_review": 1,
      "reviewed": 0,
      "not_applicable": 0,
      "blocked_awaiting_inspection": 0,
      "legacy_orphan": 0,
      "unknown": 0
    }
  },
  "duplicates": [],
  "warnings": []
}
```

字段说明：

| 字段 | 语义 |
| --- | --- |
| `runtime_state` | `queued` / `running` / `completed` / `failed` / `blocked` / `unknown`，只描述运行生命周期 |
| `review_state` | `pending_review` / `reviewed` / `not_applicable` / `blocked_awaiting_inspection` / `legacy_orphan` / `unknown`；与运行状态分离 |
| `blocker` | 明确阻塞原因代码；无阻塞为 `null`。不是验收结论 |
| `last_source_event_at` | 源记录中的 `updated_at` / `completed_at` 等，**绝不是** `now` 或本地刷新时间 |
| `evidence` | 运行状态依据：`workflow_conclusion` / `execution_status` / `workflow_run` / `result_available` / `advisory_lifecycle` / `none` |
| `freshness` | `fresh` / `stale` / `missing` / `invalid`；连接失败时批次 `batch_blocker` 为 `connection_failure` |
| `last_known_runtime_state` | 仅在非 fresh 且此前有运行证据时出现；表示“上次已知”，不是当前状态 |
| `review_verdict` | 仅当源记录已有 verdict 时透传（`PASS` / `FAIL` / `BLOCKED`） |
| `duplicate_count` | 同一 `task_id` 的原始记录数；任务本身只计一次 |
| `counts.total_unique_tasks` | **唯一任务数**；父子关系不会让父/子重复计数 |
| `complete` | 本批次是否可用于“当前完整视图”；缺时间/过期/连接失败/跳过非法记录时为 `false` |

**绝不输出**：`acceptance`、`acceptance_status`、`verdict`（本组件不判定）、
`instructions`、`prompt`、`logs`、`raw_log`、`secret`、`token`、artifact 正文。

## 6. 状态语义映射

| 输入证据 | `runtime_state` | `review_state` | 说明 |
| --- | --- | --- | --- |
| `status` 为 `queued` / `submitted` / `created` / `dispatched` / `accepted` / `pending_dispatch` 等 | `queued` | `not_applicable` | advisory 生命周期；不是运行证明 |
| `status` / `run_status` 为 `running` / `in_progress` / `started` | `running` | `not_applicable` | 仍在进行；没有结果可审 |
| `workflow_conclusion=success`，或 `execution_status=PASS`，或 `run_conclusion=success` | `completed` | 有可审结果且未审 -> `pending_review`，已审 -> `reviewed` | **`completed` ≠ 验收 `PASS`** |
| `workflow_conclusion` 为 `failure` / `startup_failure` / `error`，或 `execution_status=FAIL` | `failed` | 有可审结果且未审 -> `pending_review`，否则 `not_applicable` | 失败是运行结果，不是验收结论 |
| `workflow_conclusion` 为 `cancelled` / `timed_out` / `action_required` / `stale` / `neutral` / `skipped`，或 `execution_status=BLOCKED` | `blocked` | 有可审结果且未审 -> `pending_review`，否则 `not_applicable` | `blocker` 给出 `workflow_<conclusion>` 或 `execution_blocked` |
| 源记录明确 `review_state=pending_review` / `status=pending_review`，或 `result_available=true` 且未审 | 由运行证据决定；若运行证据为终态则对应 `completed`/`failed`/`blocked` | `pending_review` | “结果已完但未审”场景 |
| 源记录 `reviewed=true` / `review_verdict` 存在 / `review_state=reviewed` | 由运行证据决定 | `reviewed` | 人工 verdict 与运行状态分离 |
| 只有自报 `status=success` / `completed`，没有 workflow conclusion / run 证据 / result 证据 | `unknown` | `not_applicable` | `blocker=unverified_self_report`，不把自报成功升级为完成 |
| 没有任何运行证据 | `unknown` | `not_applicable` | `blocker=no_run_evidence` |
| `observed_at` 缺失 | `unknown` | 未审 -> `unknown`；已审保留 `reviewed` | `blocker=missing_observed_at` |
| 观测超过 TTL | `unknown` | 未审 -> `unknown`；已审保留 `reviewed` | `blocker=stale_observation`；保留 `last_known_runtime_state` |
| 连接失败 | `unknown` | `unknown` | `blocker=connection_failure`；批次 `complete=false` |

补充规则：

- **`pending_review` 不是运行时状态**：它进入 `review_state`，运行状态仍然由运行证据决定。
- **`completed` 不等于验收 PASS**：UI 不得把绿色“已完成”渲染成“验收通过”。
- **待审列表不等于全量活跃列表**：`list_pending_results` 的桶不能用于“当前所有任务”计数。
- **失败/阻塞结果也可能待审**：只要 `result_available=true` 且未审，`review_state=pending_review`。
- **review verdict 只透传**：投影器不产生、不推断 verdict。

## 7. 新鲜度与时间规则

1. `observed_at` 必须由调用方在拿到响应时记录，并原样传入。
2. `now` 与 `ttl_seconds` 必须由调用方传入；参考实现内部没有 `datetime.now()` / `Date.now()`。
3. `last_source_event_at` 只取响应里的 `updated_at` / `last_update_at` / `completed_at` /
   `created_at`；**禁止**用本地刷新时间填充。
4. `now - observed_at > ttl_seconds` -> 所有任务 `runtime_state=unknown`，
   `blocker=stale_observation`，`complete=false`。
5. `observed_at` 缺失/非法 -> `runtime_state=unknown`，`blocker=missing_observed_at` /
   `invalid_observed_at`，`complete=false`。
6. `observed_at` 比 `now` 超前超过 60 秒 -> 视为 `invalid`（`observed_at_in_future`）。
7. 连接失败 -> 不返回“0 个任务”的正常视图；批次 `batch_blocker=connection_failure`，
   所有已知任务 `runtime_state=unknown`，`review_state=unknown`。
8. 过期时保留 `last_known_runtime_state` 仅供 UI 灰显“上次已知”，并明确标注不是当前状态。

建议：UI 轮询 120–300 秒时使用 `ttl_seconds` 略大于轮询间隔；如果响应延迟或网络抖动，
宁可显示 `unknown`，也不要显示过期状态。

## 8. 去重与父子关系

### 8.1 重复 `task_id`

- 按 `task_id` 分组；同一 `task_id` 只输出一条任务、只计一次。
- 选择“证据最强”的记录作为主记录，优先级：
  `workflow_conclusion` > `execution_status` > `workflow_run` > `result_available` >
  `advisory_lifecycle` > `none`；同等级按源事件时间更新者优先，再按稳定序列化排序保证确定性。
- `duplicate_count` 记录原始条数；`counts.duplicate_records` 记录被合并掉的重复条数。
- 重复记录中 `parent_task_id` / `project_id` / `root_task_id` 冲突时，输出 `null` 并写入
  `warnings`，不猜造。
- 重复记录不会让 `counts.total_unique_tasks` 增加。

### 8.2 父子关系

- `parent_task_id` 只作为元数据输出，不展开、不递归计数。
- 父任务和子任务各自是唯一任务，各计一次；不会因为父子关系重复计数。
- 父任务可能不在当前响应中（例如已完成/已审），**不能据此推断“孤儿”**。
- 自指父任务（`parent_task_id == task_id`）输出 `null`，避免 UI 形成自环。
- Worker lineage metadata 可能被截断/压缩；若 `list_pending_results` 给出 `unresolved`，
  UI 应把 lineage 显示为未知，而不是“无父任务”。

## 9. Windows UI 接入方式

推荐数据流：

1. UI 的现有 Cloud Agent 代理按原方式调用已验证接口（继续遵守现有 scope）。
2. 代理在收到响应时记录 `observed_at`（响应观测时间），并读取调用方时钟作为 `now`，
   选择 `ttl_seconds`。
3. 将响应的记录数组、`source`、`observed_at`、`now`、`ttl_seconds` 传入本投影器。
4. UI 只消费投影后的 `tasks`、`counts`、`complete`、`batch_blocker`、`warnings`。
5. 不要调用 `mark_reviewed` / `submit_task` / `retry_task_dispatch`；需要人工审核时仍走既有界面与权限。

UI 渲染建议：

- `runtime_state` 决定运行态颜色：`queued` 灰蓝、`running` 蓝、`completed` 绿、`failed` 红、
  `blocked` 橙、`unknown` 灰。
- `review_state=pending_review` 显示“待审核”徽标；`reviewed` 显示已有 verdict（若提供）。
- `completed` 不得显示为“验收 PASS”；验收/评审结论只来自 `review_verdict` 与既有 review 流程。
- `freshness != fresh` 或 `complete=false` 时，顶部显示“状态未知/可能过期”，不要把旧状态当实时。
- `blocker` 显示为原因代码或文案映射；未知 blocker 原样显示代码，不要猜。
- 列表计数使用 `counts.total_unique_tasks`，不要对原始 `records` 直接 `len()`。
- 父子任务用 `parent_task_id` 建立轻量缩进/链接；父任务缺失时显示“父任务不在当前范围”。

伪代码（JavaScript，仅适配层示意，不是生产实现）：

```js
// observedAt 必须在收到响应时记录；不要把本地刷新时间写进 updated_at。
const observedAt = new Date().toISOString();
const now = new Date().toISOString();
const projected = projectTasks(responseRecords, {
  source: "worker.list_pending_results",
  observed_at: observedAt,
  now,
  ttl_seconds: 300,
  connection_error: transportError,
});
if (!projected.complete) {
  renderUnknownBanner(projected.batch_blocker);
}
renderTasks(projected.tasks);
renderCounts(projected.counts);
```

## 10. 参考实现（Python，标准库，纯函数）

将以下代码保存为 `projector.py`（在允许新增代码文件时）即可复用。它不访问网络、不读凭据、
不写文件、不读本地时钟。

```python
"""Read-only projection of existing AI Company task responses.

Pure functions only. This module performs no network I/O, reads no
credentials, touches no filesystem state and never reads the local clock.
The caller must supply:

* ``observed_at`` -- when the source API response was observed;
* ``now`` -- the caller's evaluation time;
* ``ttl_seconds`` -- the caller's freshness budget.

It never writes a second state store and never derives an acceptance verdict.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

QUEUED = "queued"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
BLOCKED = "blocked"
UNKNOWN = "unknown"
RUNTIME_STATES = (QUEUED, RUNNING, COMPLETED, FAILED, BLOCKED, UNKNOWN)

PENDING_REVIEW = "pending_review"
REVIEWED = "reviewed"
NOT_APPLICABLE = "not_applicable"
REVIEW_UNKNOWN = "unknown"
REVIEW_STATES = (
    PENDING_REVIEW,
    REVIEWED,
    NOT_APPLICABLE,
    "blocked_awaiting_inspection",
    "legacy_orphan",
    REVIEW_UNKNOWN,
)

FRESH = "fresh"
STALE = "stale"
MISSING = "missing"
INVALID = "invalid"
CONNECTION_ERROR = "connection_error"

_SUCCESS_CONCLUSIONS = frozenset({"success"})
_FAILURE_CONCLUSIONS = frozenset({"failure", "startup_failure", "error"})
_QUEUED_STATUSES = frozenset(
    {
        "queued",
        "pending",
        "submitted",
        "created",
        "dispatched",
        "accepted",
        "pending_dispatch",
        "requested",
        "waiting",
    }
)
_RUNNING_STATUSES = frozenset({"running", "in_progress", "in-progress", "started", "start"})
_TERMINAL_EXECUTION = {"PASS": COMPLETED, "FAIL": FAILED, "BLOCKED": BLOCKED}
_RESULT_STATES = frozenset({COMPLETED, FAILED, BLOCKED})
_DISPATCH_BLOCKERS = {
    "DISPATCH_FAILED": "dispatch_failed",
    "EXHAUSTED": "dispatch_exhausted",
}
_SELF_REPORTED_SUCCESS = frozenset(
    {"completed", "complete", "success", "succeeded", "pass", "passed", "ok"}
)
_SELF_REPORTED_FAILURE = frozenset(
    {"failure", "failed", "fail", "error", "errored", "blocked", "timed_out"}
)
_ALLOWED_CLOCK_SKEW_SECONDS = 60

_EVIDENCE_RANK = {
    "workflow_conclusion": 5,
    "execution_status": 4,
    "workflow_run": 3,
    "result_available": 2,
    "advisory_lifecycle": 1,
    "none": 0,
}


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _lower(value: Any) -> str:
    return _text(value).lower()


def _upper(value: Any) -> str:
    return _text(value).upper()


def _parse_iso(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_now(now: Any) -> datetime | None:
    if isinstance(now, datetime):
        parsed = now
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return _parse_iso(now)


def _source_event_at(record: Mapping[str, Any]) -> str | None:
    for key in ("updated_at", "last_update_at", "completed_at", "created_at"):
        parsed = _parse_iso(record.get(key))
        if parsed is not None:
            return _iso(parsed)
    return None


def _evidence(record: Mapping[str, Any]) -> str:
    if _text(record.get("workflow_conclusion")):
        return "workflow_conclusion"
    if _upper(record.get("execution_status")) in _TERMINAL_EXECUTION:
        return "execution_status"
    if _upper(record.get("normalized_status")) in _TERMINAL_EXECUTION:
        return "execution_status"
    if _text(record.get("run_status")) or _text(record.get("run_conclusion")):
        return "workflow_run"
    if record.get("result_available") is True:
        return "result_available"
    status = _lower(record.get("status"))
    if (
        status in _QUEUED_STATUSES
        or status in _RUNNING_STATUSES
        or _text(record.get("dispatch_state"))
    ):
        return "advisory_lifecycle"
    return "none"


def _derive_runtime(record: Mapping[str, Any]) -> tuple[str, str, str | None]:
    conclusion = _lower(record.get("workflow_conclusion"))
    if conclusion:
        if conclusion in _SUCCESS_CONCLUSIONS:
            return COMPLETED, "workflow_conclusion", None
        if conclusion in _FAILURE_CONCLUSIONS:
            return FAILED, "workflow_conclusion", None
        return BLOCKED, "workflow_conclusion", f"workflow_{conclusion}"

    execution = _upper(record.get("execution_status"))
    if execution not in _TERMINAL_EXECUTION:
        execution = _upper(record.get("normalized_status"))
    if execution in _TERMINAL_EXECUTION:
        state = _TERMINAL_EXECUTION[execution]
        blocker = "execution_blocked" if state == BLOCKED else None
        return state, "execution_status", blocker

    run_status = _lower(record.get("run_status"))
    run_conclusion = _lower(record.get("run_conclusion"))
    if run_conclusion:
        if run_conclusion in _SUCCESS_CONCLUSIONS:
            return COMPLETED, "workflow_run", None
        if run_conclusion in _FAILURE_CONCLUSIONS:
            return FAILED, "workflow_run", None
        return BLOCKED, "workflow_run", f"workflow_{run_conclusion}"
    if run_status in {"completed", "complete"}:
        return BLOCKED, "workflow_run", "workflow_conclusion_missing"
    if run_status in _RUNNING_STATUSES:
        return RUNNING, "workflow_run", None
    if run_status in _QUEUED_STATUSES:
        return QUEUED, "workflow_run", None

    if record.get("result_available") is True:
        return COMPLETED, "result_available", None

    dispatch = _upper(record.get("dispatch_state"))
    if dispatch in _DISPATCH_BLOCKERS:
        return BLOCKED, "advisory_lifecycle", _DISPATCH_BLOCKERS[dispatch]
    if _lower(record.get("recommended_action")) == "inspect":
        return BLOCKED, "advisory_lifecycle", "inspect_required"

    status = _lower(record.get("status"))
    if status in _QUEUED_STATUSES:
        return QUEUED, "advisory_lifecycle", None
    if status in _RUNNING_STATUSES:
        return RUNNING, "advisory_lifecycle", None
    if status in _SELF_REPORTED_SUCCESS or status in _SELF_REPORTED_FAILURE:
        return UNKNOWN, "none", "unverified_self_report"
    return UNKNOWN, "none", "no_run_evidence"


def _derive_review(
    record: Mapping[str, Any], runtime: str
) -> tuple[str, str | None]:
    verdict = _upper(record.get("review_verdict")) or None
    if record.get("reviewed") is True or (verdict in {"PASS", "FAIL", "BLOCKED"}):
        return REVIEWED, verdict
    raw_review = _lower(record.get("review_state"))
    if raw_review in {
        "reviewed",
        PENDING_REVIEW,
        "blocked_awaiting_inspection",
        "legacy_orphan",
    }:
        return raw_review, verdict
    status = _lower(record.get("status"))
    if status == "reviewed":
        return REVIEWED, verdict
    if status == PENDING_REVIEW:
        return PENDING_REVIEW, verdict
    if (
        runtime in _RESULT_STATES
        and record.get("result_available") is True
    ) or (
        runtime in _RESULT_STATES
        and record.get("requires_review") is True
    ):
        return PENDING_REVIEW, verdict
    return NOT_APPLICABLE, verdict


def _stable(record: Mapping[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, default=str, ensure_ascii=False)


def _rank(record: Mapping[str, Any]) -> tuple[int, float, str]:
    parsed = _parse_iso(_source_event_at(record))
    stamp = parsed.timestamp() if parsed is not None else float("-inf")
    return (_EVIDENCE_RANK.get(_evidence(record), 0), stamp, _stable(record))


def _merge_duplicates(
    task_id: str, records: list[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
    merged = dict(max(records, key=_rank))
    warnings: list[str] = []
    for field in ("parent_task_id", "project_id", "root_task_id"):
        values = {
            _text(record.get(field))
            for record in records
            if _text(record.get(field))
        }
        chosen = _text(merged.get(field))
        if len(values) > 1:
            merged[field] = None
            warnings.append(f"{task_id}: conflicting {field}; omitted")
        elif not chosen and len(values) == 1:
            merged[field] = next(iter(values))
    return merged, warnings


def _freshness(
    observed_at: Any, now_dt: datetime, ttl: float
) -> tuple[str, str | None, str | None, float | None]:
    if observed_at is None or not _text(observed_at):
        return MISSING, None, "missing_observed_at", None
    observed = _parse_iso(observed_at)
    if observed is None:
        return INVALID, None, "invalid_observed_at", None
    age = (now_dt - observed).total_seconds()
    if age < -_ALLOWED_CLOCK_SKEW_SECONDS:
        return INVALID, _iso(observed), "observed_at_in_future", age
    if age > ttl:
        return STALE, _iso(observed), "stale_observation", age
    return FRESH, _iso(observed), None, max(0.0, age)


def _project_one(
    task_id: str,
    record: Mapping[str, Any],
    *,
    source: str,
    observed_iso: str | None,
    freshness: str,
    freshness_blocker: str | None,
    age_seconds: float | None,
    connection_error: bool,
    duplicate_count: int,
) -> dict[str, Any]:
    runtime, evidence, blocker = _derive_runtime(record)
    review, verdict = _derive_review(record, runtime)
    last_known = None
    if connection_error:
        runtime, blocker, evidence = UNKNOWN, "connection_failure", "none"
        review = REVIEW_UNKNOWN
    elif freshness != FRESH:
        if runtime != UNKNOWN:
            last_known = runtime
        runtime = UNKNOWN
        blocker = freshness_blocker
        if review != REVIEWED:
            review = REVIEW_UNKNOWN

    parent = _text(record.get("parent_task_id")) or None
    if parent == task_id:
        parent = None

    projected: dict[str, Any] = {
        "task_id": task_id,
        "source": source,
        "observed_at": observed_iso,
        "runtime_state": runtime,
        "review_state": review,
        "blocker": blocker,
        "parent_task_id": parent,
        "last_source_event_at": _source_event_at(record),
        "evidence": evidence,
        "freshness": freshness,
        "duplicate_count": duplicate_count,
    }
    if last_known is not None:
        projected["last_known_runtime_state"] = last_known
    if verdict is not None:
        projected["review_verdict"] = verdict
    for field in ("project_id", "root_task_id"):
        value = _text(record.get(field))
        if value:
            projected[field] = value
    if age_seconds is not None:
        projected["observed_age_seconds"] = round(age_seconds, 3)
    return projected


def project_tasks(
    records: Iterable[Mapping[str, Any]],
    *,
    source: str,
    observed_at: Any,
    now: Any,
    ttl_seconds: Any,
    connection_error: Any = None,
) -> dict[str, Any]:
    """Project an existing task-API response into read-only status metadata.

    ``records`` is the raw response list. ``source`` names the verified
    interface that produced it. ``observed_at`` is the explicit source
    observation time; ``now`` and ``ttl_seconds`` are supplied by the caller.
    ``connection_error`` is truthy when the transport failed.
    """
    record_list = list(records or [])
    source_name = _text(source) or "unknown"
    warnings: list[str] = []
    if source_name == "unknown":
        warnings.append("source missing; reported as unknown")
    connection_failed = bool(connection_error)
    now_dt = _coerce_now(now)
    if now_dt is None:
        raise ValueError("now must be a datetime or ISO-8601 string")
    if ttl_seconds is None:
        raise ValueError("ttl_seconds is required and must be caller-supplied")
    ttl = float(ttl_seconds)
    if ttl < 0:
        raise ValueError("ttl_seconds must be >= 0")
    freshness, observed_iso, freshness_blocker, age_seconds = _freshness(
        observed_at, now_dt, ttl
    )

    groups: dict[str, list[Mapping[str, Any]]] = {}
    for record in record_list:
        if not isinstance(record, Mapping):
            warnings.append("non-object record skipped")
            continue
        task_id = _text(record.get("task_id"))
        if not task_id:
            warnings.append("record without task_id skipped")
            continue
        groups.setdefault(task_id, []).append(record)

    tasks: list[dict[str, Any]] = []
    duplicate_notes: list[dict[str, Any]] = []
    for task_id, group in groups.items():
        merged, merge_warnings = _merge_duplicates(task_id, group)
        warnings.extend(merge_warnings)
        if len(group) > 1:
            duplicate_notes.append(
                {"task_id": task_id, "records": len(group)}
            )
        record_source = _text(merged.get("source")) or source_name
        tasks.append(
            _project_one(
                task_id,
                merged,
                source=record_source,
                observed_iso=observed_iso,
                freshness=freshness,
                freshness_blocker=freshness_blocker,
                age_seconds=age_seconds,
                connection_error=connection_failed,
                duplicate_count=len(group),
            )
        )

    runtime_counts = {state: 0 for state in RUNTIME_STATES}
    review_counts = {state: 0 for state in REVIEW_STATES}
    for task in tasks:
        runtime_counts[task["runtime_state"]] += 1
        review_counts[task["review_state"]] += 1

    complete = (
        freshness == FRESH
        and not connection_failed
        and not any(
            warning.startswith(("record without task_id", "non-object record"))
            for warning in warnings
        )
    )
    batch_blocker = None
    if connection_failed:
        batch_blocker = "connection_failure"
    elif freshness != FRESH:
        batch_blocker = freshness_blocker

    return {
        "source": source_name,
        "observed_at": observed_iso,
        "projected_at": _iso(now_dt),
        "ttl_seconds": ttl,
        "complete": complete,
        "batch_blocker": batch_blocker,
        "tasks": sorted(tasks, key=lambda item: item["task_id"]),
        "counts": {
            "raw_records": len(record_list),
            "total_unique_tasks": len(tasks),
            "duplicate_records": sum(
                note["records"] - 1 for note in duplicate_notes
            ),
            "runtime_state": runtime_counts,
            "review_state": review_counts,
        },
        "duplicates": duplicate_notes,
        "warnings": warnings,
    }
```

## 11. 脱敏合成夹具

以下 fixture 全部为合成 ID 与时间，不含任何真实任务、提示、密钥或私密正文。

```json
{
  "source": "worker.list_pending_results",
  "observed_at": "2026-10-17T12:00:00Z",
  "now": "2026-10-17T12:01:00Z",
  "ttl_seconds": 300,
  "records": [
    {
      "task_id": "cf-completed-unreviewed",
      "parent_task_id": null,
      "status": "PASS",
      "execution_status": "PASS",
      "normalized_status": "PASS",
      "workflow_conclusion": "success",
      "result_available": true,
      "reviewed": false,
      "requires_review": true,
      "updated_at": "2026-10-17T11:58:00Z",
      "completed_at": "2026-10-17T11:57:30Z"
    },
    {
      "task_id": "cf-reviewed",
      "status": "PASS",
      "execution_status": "PASS",
      "workflow_conclusion": "success",
      "result_available": true,
      "reviewed": true,
      "review_verdict": "PASS",
      "review_state": "reviewed",
      "updated_at": "2026-10-17T11:59:00Z"
    },
    {
      "task_id": "cf-running",
      "status": "running",
      "dispatch_state": "CONFIRMED",
      "run_status": "in_progress",
      "updated_at": "2026-10-17T11:59:30Z"
    },
    {
      "task_id": "cf-queued",
      "status": "queued",
      "dispatch_state": "ACCEPTED",
      "updated_at": "2026-10-17T11:59:45Z"
    },
    {
      "task_id": "cf-failed",
      "status": "FAIL",
      "execution_status": "FAIL",
      "workflow_conclusion": "failure",
      "result_available": true,
      "reviewed": false,
      "updated_at": "2026-10-17T11:56:00Z"
    },
    {
      "task_id": "cf-blocked",
      "status": "BLOCKED",
      "execution_status": "BLOCKED",
      "workflow_conclusion": "timed_out",
      "result_available": false,
      "updated_at": "2026-10-17T11:55:00Z"
    },
    {
      "task_id": "cf-unverified-self-report",
      "status": "success",
      "updated_at": "2026-10-17T11:54:00Z"
    },
    {
      "task_id": "cf-duplicate",
      "status": "running",
      "dispatch_state": "CONFIRMED",
      "updated_at": "2026-10-17T11:53:00Z"
    },
    {
      "task_id": "cf-duplicate",
      "status": "PASS",
      "execution_status": "PASS",
      "workflow_conclusion": "success",
      "result_available": true,
      "reviewed": false,
      "updated_at": "2026-10-17T11:58:30Z"
    },
    {
      "task_id": "cf-parent",
      "status": "PASS",
      "execution_status": "PASS",
      "workflow_conclusion": "success",
      "result_available": true,
      "reviewed": true,
      "review_verdict": "PASS",
      "updated_at": "2026-10-17T11:50:00Z"
    },
    {
      "task_id": "cf-child",
      "parent_task_id": "cf-parent",
      "root_task_id": "cf-parent",
      "status": "FAIL",
      "execution_status": "FAIL",
      "workflow_conclusion": "failure",
      "result_available": true,
      "reviewed": false,
      "updated_at": "2026-10-17T11:52:00Z"
    },
    {
      "note": "this record has no task_id and must be skipped"
    }
  ]
}
```

覆盖场景：

- 正常完成但未审（`completed` + `pending_review`）；
- 已审（`reviewed` + verdict）；
- 运行中 / 排队中；
- 失败 / 阻塞；
- 部分覆盖（只有自报成功，无运行证据 -> `unknown`）；
- 重复 `task_id`（权威记录胜出，只计一次）；
- 缺 `observed_at`（整批 `unknown`）；
- 过期（整批 `unknown`，保留上次已知）；
- 父子关系（父/子各计一次）；
- 结果已完但未审；
- 缺 `task_id` 的非法记录（跳过并告警，不伪造）；
- 连接失败（另行通过 `connection_error` 覆盖）。

## 12. 参考测试

将以下代码保存为 `test_projector.py`，与 `projector.py` 和 `fixtures.json` 同目录：

```python
import json
from pathlib import Path

import pytest

from projector import (
    BLOCKED,
    COMPLETED,
    FAILED,
    NOT_APPLICABLE,
    PENDING_REVIEW,
    QUEUED,
    REVIEWED,
    RUNNING,
    UNKNOWN,
    project_tasks,
)

FIXTURE = json.loads(Path(__file__).with_name("fixtures.json").read_text())


def run(records=None, **overrides):
    payload = dict(FIXTURE)
    payload.update(overrides)
    if records is not None:
        payload["records"] = records
    return project_tasks(
        payload["records"],
        source=payload["source"],
        observed_at=payload["observed_at"],
        now=payload["now"],
        ttl_seconds=payload["ttl_seconds"],
        connection_error=payload.get("connection_error"),
    )


def by_id(result):
    return {task["task_id"]: task for task in result["tasks"]}


def test_runtime_and_review_state_semantics():
    tasks = by_id(run())
    assert tasks["cf-completed-unreviewed"]["runtime_state"] == COMPLETED
    assert tasks["cf-completed-unreviewed"]["review_state"] == PENDING_REVIEW
    assert tasks["cf-reviewed"]["runtime_state"] == COMPLETED
    assert tasks["cf-reviewed"]["review_state"] == REVIEWED
    assert tasks["cf-reviewed"]["review_verdict"] == "PASS"
    assert tasks["cf-running"]["runtime_state"] == RUNNING
    assert tasks["cf-running"]["review_state"] == NOT_APPLICABLE
    assert tasks["cf-queued"]["runtime_state"] == QUEUED
    assert tasks["cf-failed"]["runtime_state"] == FAILED
    assert tasks["cf-failed"]["review_state"] == PENDING_REVIEW
    assert tasks["cf-blocked"]["runtime_state"] == BLOCKED
    assert tasks["cf-blocked"]["blocker"] == "workflow_timed_out"


def test_completed_is_not_acceptance_pass():
    task = by_id(run())["cf-completed-unreviewed"]
    assert task["runtime_state"] == COMPLETED
    assert "acceptance" not in task
    assert "status" not in task
    assert task["review_state"] == PENDING_REVIEW


def test_missing_run_evidence_is_unknown():
    task = by_id(run())["cf-unverified-self-report"]
    assert task["runtime_state"] == UNKNOWN
    assert task["blocker"] == "unverified_self_report"
    assert task["review_state"] == NOT_APPLICABLE


def test_duplicate_task_id_is_counted_once_and_authoritative_record_wins():
    result = run()
    tasks = by_id(result)
    duplicate = tasks["cf-duplicate"]
    assert duplicate["runtime_state"] == COMPLETED
    assert duplicate["review_state"] == PENDING_REVIEW
    assert duplicate["duplicate_count"] == 2
    assert result["counts"]["duplicate_records"] == 1
    assert result["counts"]["total_unique_tasks"] == 10
    assert [d["task_id"] for d in result["duplicates"]] == ["cf-duplicate"]


def test_parent_child_does_not_double_count():
    result = run()
    tasks = by_id(result)
    assert tasks["cf-child"]["parent_task_id"] == "cf-parent"
    assert tasks["cf-child"]["runtime_state"] == FAILED
    assert tasks["cf-parent"]["runtime_state"] == COMPLETED
    assert result["counts"]["total_unique_tasks"] == 10
    assert sum(result["counts"]["runtime_state"].values()) == 10


def test_missing_task_id_is_skipped_not_invented():
    result = run()
    assert "record without task_id skipped" in result["warnings"]
    assert result["complete"] is False
    assert result["counts"]["raw_records"] == 12
    assert result["counts"]["total_unique_tasks"] == 10


def test_stale_observation_forces_unknown_but_keeps_last_known():
    result = run(observed_at="2026-10-17T10:00:00Z", now="2026-10-17T12:01:00Z")
    tasks = by_id(result)
    task = tasks["cf-completed-unreviewed"]
    assert result["complete"] is False
    assert result["batch_blocker"] == "stale_observation"
    assert task["runtime_state"] == UNKNOWN
    assert task["last_known_runtime_state"] == COMPLETED
    assert task["freshness"] == "stale"
    assert task["observed_at"] == "2026-10-17T10:00:00Z"
    assert tasks["cf-reviewed"]["review_state"] == REVIEWED
    assert tasks["cf-completed-unreviewed"]["review_state"] == UNKNOWN


def test_missing_observed_at_forces_unknown_without_using_now():
    result = run(observed_at=None)
    tasks = by_id(result)
    assert result["complete"] is False
    assert result["batch_blocker"] == "missing_observed_at"
    assert result["observed_at"] is None
    assert all(task["runtime_state"] == UNKNOWN for task in tasks.values())
    assert all(task["observed_at"] is None for task in tasks.values())


def test_connection_failure_is_unknown():
    result = run(connection_error={"code": "CONNECTION_FAILED"})
    assert result["complete"] is False
    assert result["batch_blocker"] == "connection_failure"
    assert all(task["runtime_state"] == UNKNOWN for task in result["tasks"])
    assert all(task["blocker"] == "connection_failure" for task in result["tasks"])
    assert all(task["review_state"] == UNKNOWN for task in result["tasks"])


def test_future_observation_is_invalid():
    result = run(observed_at="2026-10-18T00:00:00Z", now="2026-10-17T12:01:00Z")
    assert result["complete"] is False
    assert result["batch_blocker"] == "observed_at_in_future"
    assert all(task["runtime_state"] == UNKNOWN for task in result["tasks"])


def test_source_event_time_is_never_the_local_now():
    task = by_id(run())["cf-completed-unreviewed"]
    assert task["last_source_event_at"] == "2026-10-17T11:58:00Z"
    assert task["observed_at"] == "2026-10-17T12:00:00Z"
    assert task["observed_at"] != task["last_source_event_at"]


def test_conflicting_parent_in_duplicates_is_omitted():
    records = [
        {
            "task_id": "cf-x",
            "parent_task_id": "cf-a",
            "workflow_conclusion": "success",
            "execution_status": "PASS",
            "updated_at": "2026-10-17T11:58:00Z",
        },
        {
            "task_id": "cf-x",
            "parent_task_id": "cf-b",
            "status": "running",
            "updated_at": "2026-10-17T11:59:00Z",
        },
    ]
    result = run(records=records)
    task = result["tasks"][0]
    assert task["parent_task_id"] is None
    assert any("conflicting parent_task_id" in w for w in result["warnings"])


def test_self_parent_is_not_reported_as_lineage():
    records = [
        {
            "task_id": "cf-self",
            "parent_task_id": "cf-self",
            "status": "queued",
            "updated_at": "2026-10-17T11:59:00Z",
        }
    ]
    task = run(records=records)["tasks"][0]
    assert task["parent_task_id"] is None


def test_empty_fresh_response_is_complete():
    result = run(records=[])
    assert result["complete"] is True
    assert result["counts"]["total_unique_tasks"] == 0
    assert result["batch_blocker"] is None


def test_now_and_ttl_are_required():
    with pytest.raises(ValueError):
        project_tasks([], source="worker.list_pending_results", observed_at="2026-10-17T12:00:00Z", now=None, ttl_seconds=300)
    with pytest.raises(ValueError):
        project_tasks([], source="worker.list_pending_results", observed_at="2026-10-17T12:00:00Z", now="2026-10-17T12:01:00Z", ttl_seconds=None)
```

运行：

```bash
python -m pytest -q
```

参考测试覆盖状态语义、`completed` 与验收 PASS 的分离、缺证据/缺时间/过期/连接失败、
重复 `task_id`、父子计数、确定性去重、源事件时间不被本地时间替代，以及 `now`/TTL 必填。

## 13. 验证证据

本 README 的参考实现与参考测试在仓库外的临时目录中执行，未创建仓库内额外文件：

- 命令：`python -m pytest -q`
- 结果：`15 passed`
- 环境：Python 标准库；无网络、无凭据、无生产写调用。

仓库既有测试另行执行（见执行报告）。本组件**未部署、未接入 Windows UI、未实现实时能力**，
产出是可集成组件与规范，不是已上线功能。

## 14. 变更清单与执行报告

本任务在仓库内只新增：

- `tools/ai-company-status-projection/README.md`

未修改任何现有生产文件，未删除文件，未触碰 `.github/workflows/`、secret/token/credential/
`.env`/`.pem`/`.key` 路径。

执行报告（`/home/runner/work/_temp/agent_result.json`）包含：

- `task_id` / `project_id` / `final_status`；
- commit hash；
- `python -m pytest -q` 的仓库测试输出与参考测试输出；
- 变更清单；
- 明确声明：未部署、未写 Canonical、未读用户私密正文、未调用真实生产写接口。

## 15. 已知限制与下一步

1. 由于本任务 `expected_files` 只允许 `README.md`，参考实现与测试以可复制代码块交付；
   若后续契约允许，应拆分为 `projector.py`、`fixtures.json`、`test_projector.py`，
   由 Windows UI 以模块方式导入，而不是从 README 复制。
2. Windows UI 需要增加一个薄适配层：记录 `observed_at`、处理连接失败、选择 TTL、
   按 `runtime_state` / `review_state` 渲染。
3. 若要支持“全量活跃任务”，必须先有一个真正的全量只读接口；不能把
   `list_pending_results` 的桶或 `counts.total` 当作全量。
4. 若要支持实时，需要新增事件流契约与背压/断线语义；本组件不声称实时。
5. 若要自动验收，必须复用既有 review/verification 流程；本组件永远不输出验收 PASS。

