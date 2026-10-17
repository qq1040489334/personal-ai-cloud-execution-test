# AI 公司任务状态只读投影器（Cloud Agent）

> 交付形态：可集成组件的**规范 + 可导入实现 + 脱敏夹具 + 定向测试**。
> 本任务按契约在 `tools/ai-company-status-projection/` 下交付以下实际文件：
>
> | 文件 | 作用 |
> | --- | --- |
> | `projector.py` | 纯函数投影器（仅标准库；无网络、无凭据、不读本地时钟） |
> | `fixtures.json` | 脱敏合成夹具（合成 ID 与时间） |
> | `test_projector.py` | 定向 pytest 测试 |
> | `README.md` | 本规范与使用说明 |
>
> 未新增服务、定时任务或第二状态库；未部署、未接入现有 Windows UI、未写 Canonical、
> 未调用真实生产写接口、未读取用户私密正文。

- task_id: `cf-5a9f4321fa50`（父任务 `cf-0fd0bd1c2ce4`）
- project_id: `ai-company-status-projection`
- risk_level: `LOW`
- 参考基线: `c44ba47`（父任务 README 基线）

## 0. 结论先行

本组件解决的唯一问题是：**把既有任务接口已经返回的响应，按调用方给定的
`observed_at` / `now` / TTL 投影成 UI 可消费的最小只读状态元数据。** 它不是第二个状态库，
不是实时系统，也不是验收判定器。

已交付：

- 明确的输入/输出契约；
- `queued` / `running` / `completed` / `failed` / `blocked` / `pending_review` /
  `reviewed` / `unknown` / `conflict` 的语义映射；
- 新鲜度、缺时间、连接失败、重复 `task_id`、父子关系的确定性规则；
- workflow conclusion 成功但 execution status 失败时保留失败或显式冲突，不伪装绿灯；
- runtime 证据与 review 证据独立合并，新审查结论不会被旧 workflow-success 记录覆盖；
- 同等级同时间冲突不再按词典序挑 `completed`；考虑 sequence / run identity，缺序时输出冲突；
- 拒绝 NaN / Inf / 负 TTL；未来 source event 不参与去重排序；
- 明确 `coverage` / `scope`，区分“本批次处理完成”与“全量任务覆盖”；
- 可导入的纯函数实现 `projector.py`（仅 Python 标准库，无网络、无凭据、不读本地时钟）；
- 覆盖正常、失败、部分覆盖、重复、缺时间、过期、父子关系、结果已完未审等场景的
  脱敏合成夹具 `fixtures.json` 与定向测试 `test_projector.py`；
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
  "batch_complete": true,
  "scope": "pending_results_subset",
  "full_task_coverage": false,
  "coverage": {
    "scope": "pending_results_subset",
    "full_task_coverage": false,
    "batch_complete": true,
    "task_count": 1,
    "empty_response_is_full_idle": false,
    "reason": "list_pending_results returns only pending/failed/blocked buckets, not the full active-task set"
  },
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
| `review_state` | `pending_review` / `reviewed` / `not_applicable` / `blocked_awaiting_inspection` / `legacy_orphan` / `unknown` / `conflict`；与运行状态分离 |
| `blocker` | 明确阻塞原因代码；无阻塞为 `null`。不是验收结论 |
| `review_blocker` | 仅在 review 证据冲突时出现，例如 `conflicting_review_evidence` |
| `conflicts` | 去重/合并时发现的确定性冲突说明；没有冲突时不输出 |
| `last_source_event_at` | 源记录中的 `updated_at` / `completed_at` 等，**绝不是** `now` 或本地刷新时间；未来事件不参与去重 |
| `evidence` | 运行状态依据：`conflict` / `workflow_conclusion` / `execution_status` / `workflow_run` / `result_available` / `advisory_lifecycle` / `none` |
| `freshness` | `fresh` / `stale` / `missing` / `invalid`；连接失败时批次 `batch_blocker` 为 `connection_failure` |
| `last_known_runtime_state` | 仅在非 fresh 且此前有运行证据时出现；表示“上次已知”，不是当前状态 |
| `review_verdict` | 仅当源记录已有 verdict 时透传（`PASS` / `FAIL` / `BLOCKED`）；冲突时不透传 |
| `duplicate_count` | 同一 `task_id` 的原始记录数；任务本身只计一次 |
| `counts.total_unique_tasks` | **唯一任务数**；父子关系不会让父/子重复计数 |
| `complete` / `batch_complete` | **仅表示本批次处理完成**；缺时间/过期/连接失败/跳过非法记录时为 `false`。不代表全量任务覆盖 |
| `scope` | 数据源覆盖范围：`pending_results_subset` / `single_task` / `full_task_set` / `unknown` |
| `full_task_coverage` | 是否覆盖全量任务；`list_pending_results` 与 `get_task_result` 恒为 `false` |
| `coverage.empty_response_is_full_idle` | 只有在声明为全量来源、批次完整且任务数为 0 时才为 `true`；空 `list_pending_results` 不得宣称全量空闲 |

**绝不输出**：`acceptance`、`acceptance_status`、`verdict`（本组件不判定）、
`instructions`、`prompt`、`logs`、`raw_log`、`secret`、`token`、artifact 正文。

## 6. 状态语义映射

| 输入证据 | `runtime_state` | `review_state` | 说明 |
| --- | --- | --- | --- |
| `status` 为 `queued` / `submitted` / `created` / `dispatched` / `accepted` / `pending_dispatch` 等 | `queued` | `not_applicable` | advisory 生命周期；不是运行证明 |
| `status` / `run_status` 为 `running` / `in_progress` / `started` | `running` | `not_applicable` | 仍在进行；没有结果可审 |
| `workflow_conclusion=success` 且无相反执行证据，或 `execution_status=PASS`，或 `run_conclusion=success` | `completed` | 有可审结果且未审 -> `pending_review`，已审 -> `reviewed` | **`completed` ≠ 验收 `PASS`** |
| `workflow_conclusion=success` 但 `execution_status` / `normalized_status` / `status` 明确为 `FAIL` | `failed` | 按结果可审性决定 | `evidence=conflict`，`blocker=workflow_success_execution_failure`；不得绿灯 |
| `workflow_conclusion=success` 但执行证据明确为 `BLOCKED` | `blocked` | 按结果可审性决定 | `evidence=conflict`，`blocker=workflow_success_execution_blocked` |
| 同等级同时间的重复记录分别给出成功与失败，且没有 sequence / run identity 足以排序 | `unknown` | 由独立 review 证据决定 | `evidence=conflict`，`blocker=conflicting_runtime_evidence`；不猜 |
| `workflow_conclusion` 为 `failure` / `startup_failure` / `error`，或 `execution_status=FAIL` | `failed` | 有可审结果且未审 -> `pending_review`，否则 `not_applicable` | 失败是运行结果，不是验收结论 |
| `workflow_conclusion` 为 `cancelled` / `timed_out` / `action_required` / `stale` / `neutral` / `skipped`，或 `execution_status=BLOCKED` | `blocked` | 有可审结果且未审 -> `pending_review`，否则 `not_applicable` | `blocker` 给出 `workflow_<conclusion>` 或 `execution_blocked` |
| 源记录明确 `review_state=pending_review` / `status=pending_review`，或 `result_available=true` 且未审 | 由运行证据决定；若运行证据为终态则对应 `completed`/`failed`/`blocked` | `pending_review` | “结果已完但未审”场景 |
| 源记录 `reviewed=true` / `review_verdict` 存在 / `review_state=reviewed` | 由运行证据决定 | `reviewed` | 人工 verdict 与运行状态分离；较新的 review 证据独立合并 |
| 同一时间/序列上出现互相冲突的 review 状态或 verdict | 由运行证据决定 | `conflict` | `review_blocker=conflicting_review_evidence`，不输出猜测的 verdict |
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
2. `now` 与 `ttl_seconds` 必须由调用方传入；`projector.py` 内部没有 `datetime.now()` /
   `Date.now()`。
3. `last_source_event_at` 只取响应里的 `updated_at` / `last_update_at` / `completed_at` /
   `created_at`；**禁止**用本地刷新时间填充。
4. `now - observed_at > ttl_seconds` -> 所有任务 `runtime_state=unknown`，
   `blocker=stale_observation`，`complete=false`。
5. `observed_at` 缺失/非法 -> `runtime_state=unknown`，`blocker=missing_observed_at` /
   `invalid_observed_at`，`complete=false`。
6. `observed_at` 比 `now` 超前超过 60 秒 -> 视为 `invalid`（`observed_at_in_future`）。
   超前不超过 60 秒的时钟抖动被容忍为 `fresh`。
7. `ttl_seconds` 必须是有限数字且 `>= 0`；NaN、Inf、-Inf 与负数一律抛 `ValueError`。
8. 源事件时间晚于 `observed_at` 超过 60 秒时，不参与去重排序，不能靠未来时间赢得合并。
9. 连接失败 -> 不返回“0 个任务”的正常视图；批次 `batch_blocker=connection_failure`，
   所有已知任务 `runtime_state=unknown`，`review_state=unknown`。
10. 过期时保留 `last_known_runtime_state` 仅供 UI 灰显“上次已知”，并明确标注不是当前状态。

建议：UI 轮询 120–300 秒时使用 `ttl_seconds` 略大于轮询间隔；如果响应延迟或网络抖动，
宁可显示 `unknown`，也不要显示过期状态。

## 8. 去重与父子关系

### 8.1 重复 `task_id`

- 按 `task_id` 分组；同一 `task_id` 只输出一条任务、只计一次。
- **runtime 与 review 分开选择证据**。runtime 选择“证据最强”的记录，优先级：
  `conflict` > `workflow_conclusion` > `execution_status` > `workflow_run` >
  `result_available` > `advisory_lifecycle` > `none`；同等级按有效源事件时间、再按
  sequence、最后按稳定序列化排序保证确定性。
- review 证据独立按有效时间 / sequence / 证据强度选择：较新的 `reviewed` + verdict 不会被
  旧的 `pending_review` 覆盖；较新的明确 review 结论优先于旧结论。
- 同等级同时间出现成功/失败等不同 runtime 状态时，不再用 JSON 词典序挑一个；若无
  sequence 或可排序的 run identity，输出 `unknown` + `blocker=conflicting_runtime_evidence`。
- 同一时间/序列出现不同 review 状态或 verdict 时，输出 `review_state=conflict` 与
  `review_blocker=conflicting_review_evidence`，不输出猜测的 verdict。
- workflow-success 完成与执行失败并列时：更新的执行失败会保留；同一时间/序列则输出冲突，
  不允许 `completed` 绿灯掩盖失败。
- 晚于 `observed_at` 超过 60 秒的未来源事件不能赢得去重排序。
- `duplicate_count` 记录原始条数；`counts.duplicate_records` 记录被合并掉的重复条数。
- 重复记录中 `parent_task_id` / `project_id` / `root_task_id` 冲突时，输出 `null` 并写入
  `warnings`，不猜造。
- 重复记录不会让 `counts.total_unique_tasks` 增加。

### 8.2 覆盖范围不是全量结论

- `complete` / `batch_complete` 只说明本批次是否被完整处理，不说明已看到全公司所有任务。
- `scope` 与 `coverage` 明确数据源覆盖限制；`list_pending_results` 是
  `pending_results_subset`，`get_task_result` 是 `single_task`。
- 空 `list_pending_results` 只在 `batch_complete=true` 意义上成功，`full_task_coverage=false`，
  `empty_response_is_full_idle=false`，不能宣称“全量空闲”。
- 只有调用方明确声明全量任务列表来源（例如 `list_tasks`）时，才可能
  `full_task_coverage=true`。

### 8.3 父子关系

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
- `review_state=pending_review` 显示“待审核”徽标；`reviewed` 显示已有 verdict（若提供）；
  `review_state=conflict` 显示“审查证据冲突”，不要选一个 verdict 展示为事实。
- `completed` 不得显示为“验收 PASS”；验收/评审结论只来自 `review_verdict` 与既有 review 流程。
- `runtime_state=unknown` 且 `evidence=conflict` 时显示“证据冲突/无法判定”，不要按旧状态点亮。
- `freshness != fresh` 或 `batch_complete=false` 时，顶部显示“状态未知/可能过期”，不要把旧状态当实时。
- `coverage.full_task_coverage=false` 时，不要把当前列表渲染成“全公司任务总览”或“全部空闲”。
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
if (!projected.batch_complete) {
  renderUnknownBanner(projected.batch_blocker);
}
if (!projected.coverage.full_task_coverage) {
  renderPartialCoverageBanner(projected.coverage.reason);
}
renderTasks(projected.tasks);
renderCounts(projected.counts);
```

## 10. 模块使用（`projector.py`）

`projector.py` 只依赖 Python 标准库，是纯函数模块，可直接导入。由于本目录名含连字符且
没有 `__init__.py`，不能作为包名 `tools.ai_company_status_projection` 导入；应把目录加入
`sys.path` 后 `import projector`，或从该目录内运行。

```python
import sys
sys.path.insert(0, "tools/ai-company-status-projection")

from projector import project_tasks

projected = project_tasks(
    response_records,            # 既有接口返回的记录数组
    source="worker.list_pending_results",
    observed_at=observed_at,     # 调用方拿到响应时记录的时间
    now=now,                     # 调用方评估时间（字符串或 datetime）
    ttl_seconds=300,             # 调用方新鲜度预算
    connection_error=None,       # 传输失败时传 truthy
)
```

公开 API：

| 名称 | 说明 |
| --- | --- |
| `project_tasks(records, *, source, observed_at, now, ttl_seconds, connection_error=None)` | 唯一公开入口。返回第 5 节的输出字典 |
| `QUEUED` / `RUNNING` / `COMPLETED` / `FAILED` / `BLOCKED` / `UNKNOWN` | `runtime_state` 常量 |
| `PENDING_REVIEW` / `REVIEWED` / `NOT_APPLICABLE` / `REVIEW_UNKNOWN` / `REVIEW_CONFLICT` | `review_state` 常量 |
| `RUNTIME_STATES` / `REVIEW_STATES` | 合法取值元组（用于计数键） |

约束：

- 调用方必须提供 `now` 与 `ttl_seconds`；缺失时 `project_tasks` 抛 `ValueError`。
- 模块内部不读时钟、不访问网络、不读写文件、不读取凭据，也不产生验收 verdict。

## 11. 脱敏合成夹具（`fixtures.json`）

`fixtures.json` 为第 4 节输入信封的脱敏合成实例，全部为合成 ID 与时间，不含任何真实任务、
提示、密钥或私密正文。它覆盖以下场景：

- 正常完成但未审（`completed` + `pending_review`）；
- 已审（`reviewed` + verdict）；
- 运行中 / 排队中；
- 失败 / 阻塞；
- 部分覆盖（只有自报成功，无运行证据 -> `unknown`）；
- 重复 `task_id`（权威记录胜出，只计一次）；
- 缺 `task_id` 的非法记录（跳过并告警，不伪造）；
- 父子关系（父/子各计一次）；
- 结果已完但未审。

`fixtures.json` 含 12 条原始记录，其中 1 条无 `task_id`、1 个重复 `task_id`，因此
`total_unique_tasks = 10`、`duplicate_records = 1`。缺 `observed_at`、过期、连接失败、
workflow-success 与执行失败冲突、review 证据冲突、同时间重复冲突、未来 source event、
非法 TTL、coverage 边界等变体由测试在运行时通过 override 覆盖，不固化在夹具里。

## 12. 定向测试（`test_projector.py`）

测试与 `projector.py`、`fixtures.json` 同目录。运行：

```bash
python -m pytest -q tools/ai-company-status-projection/test_projector.py
```

覆盖范围：

- 运行状态与 review 状态语义映射；
- `completed` 与验收 PASS 的分离；
- **freshness**：恰好等于 TTL 为 `fresh`、刚超过 TTL 为 `stale`、缺 `observed_at`、
  未来时间拒绝、60 秒内时钟抖动容忍、源事件时间不被本地 `now` 替代、缺源事件时间不猜造；
- **非法 TTL**：NaN、Inf、-Inf、负数一律拒绝；未来 source event 不能赢得去重；
- **去重**：重复 `task_id` 只计一次、证据最强记录胜出、同证据等级时较新源事件胜出；
  同时间/序列的 runtime 冲突输出 `unknown` + conflict，同时间 review 冲突输出 `conflict`；
- **矛盾状态**：`workflow_conclusion=success` 与 `execution_status=FAIL` / `BLOCKED` 冲突时
  保留实际失败/阻塞或显式冲突，不再输出 `completed`；重复记录中冲突的 `parent_task_id`
  被置空并告警；
- **review / runtime 独立合并**：旧 workflow-success pending-review + 新 reviewed FAIL
  不丢失新 verdict；缺排序证据的 review 冲突不猜；
- **review / runtime 分离**：失败任务可已审、`review_verdict` 存在不会把无运行证据的任务
  升级为完成、缺 `observed_at` 时已审 verdict 仍保留；
- **覆盖范围**：空 `list_pending_results` 仅批次完成，不是全量空闲；声明全量来源才可
  声称全量覆盖；
- 连接失败、缺 `task_id` 跳过、自指父任务、空响应、`now`/TTL 必填。

## 13. 本地验证证据

在仓库当前基线执行组件定向测试与语法检查，未部署、未联网、未读写真实私有数据：

- `python -m py_compile tools/ai-company-status-projection/projector.py tools/ai-company-status-projection/test_projector.py` -> 通过；
- `python -c "json.load(open('tools/ai-company-status-projection/fixtures.json'))"` -> 通过；
- **agent 手跑组件定向测试**：`python -m pytest -q tools/ai-company-status-projection/test_projector.py`
  -> `37 passed`；
- **工作流自动全仓测试**（本次也按交付步骤执行）：`python -m pytest -q`
  -> `1745 passed, 1 skipped`；
- 独立语义探针确认未来+120s 为 `invalid`、未来+30s 为 `fresh`、过期/缺时间/连接失败均为
  `unknown` 且 `complete=false`、workflow-success 与执行失败冲突不再绿灯、review 证据
  独立合并、未来 source event 不赢去重、非法 TTL 被拒绝、空 pending 列表不宣称全量空闲。

本组件**未部署、未接入 Windows UI、未实现实时能力**，产出是可集成组件与规范，不是已上线功能。

## 14. 变更清单与执行报告

基线：`02e1c4b8174b459b96bd73a6e7c84976860181fe`。本任务只修改以下四个文件：

- `projector.py`：修复 workflow-success 掩盖执行失败、runtime/review 独立合并、
  同等级同时间冲突、未来 source event 排序、非法 TTL、coverage/scope 输出；
- `test_projector.py`：为上述每项增加复现与修复后回归，并更新旧的错误断言；
- `fixtures.json`：保持脱敏合成数据不变（新增边界场景由测试 override）；
- `README.md`：同步新语义、覆盖范围、测试证据与限制。

未修改该目录以外的任何文件，未删除文件，未新增部署/定时任务，未触碰
`.github/workflows/`、secret/token/credential/`.env`/`.pem`/`.key` 路径。

执行报告（`/home/runner/work/_temp/agent_result.json`）包含：

- `task_id` / `project_id` / `final_status`；
- commit hash；
- 组件定向测试的原始输出；
- 变更清单；
- 明确声明：未部署、未写 Canonical、未读用户私密正文、未调用真实生产写接口。

## 15. 已知限制与下一步

1. 本组件仍需 Windows UI 增加一个薄适配层：记录 `observed_at`、处理连接失败、选择 TTL、
   按 `runtime_state` / `review_state` 渲染。
2. 若要支持“全量活跃任务”，必须先有一个真正的全量只读接口；不能把
   `list_pending_results` 的桶或 `counts.total` 当作全量。
3. 若要支持实时，需要新增事件流契约与背压/断线语义；本组件不声称实时。
4. 若要自动验收，必须复用既有 review/verification 流程；本组件永远不输出验收 PASS。
5. 重复记录冲突只有在存在可排序的时间、sequence 或 run identity 时才能收敛；证据不足时
   输出 `unknown` / `conflict`，需要上游补齐关联信息。
6. `full_task_coverage` 只在调用方明确声明全量任务列表来源时为 `true`；现有
   `list_pending_results` / `get_task_result` 都不能提供全量覆盖。
