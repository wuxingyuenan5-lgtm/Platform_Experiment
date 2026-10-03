# Platform API Contract

状态：`active contract`
Platform API Prefix：`/api/v1`
Runtime 根地址：`http://127.0.0.1:8100`
关联安全规则：[Secrets and Redaction](../operations/SECRETS.md)
关联实盘验收：`../operations/LIVE_ACCEPTANCE_RUNBOOK.md`

## 1. 服务边界

| 服务 | 默认地址 | 权威职责 |
|---|---|---|
| Platform API | `http://127.0.0.1:8000` | Auth、RBAC、Session、Command、Risk、Fact、Accounting、Reconciliation、EOD、Rotation Metadata |
| Platform Execution Runtime | `http://127.0.0.1:8100` | Journal、Live Safety、SecretProvider、Gateway、Venue Query、外部副作用 |
| Frontend | `http://127.0.0.1:4373` | 产品交互，不持有 Venue 凭证内容 |

公开健康探针：

```http
GET /health
```

Live 环境中除 `/health` 外的 Platform API 均进入认证与授权边界。

### 策略接口生成与查询生命周期

FastAPI 的响应模型是 Funding、Cross 和策略管理接口的唯一类型来源。`platform-api/scripts/export_strategy_openapi.py` 在不运行 lifespan、不连接数据库或外部服务的条件下导出可达合同；`docs/contracts/platform-strategy.openapi.json` 与 `platform-web/src/api/platform/generated/strategy.ts` 是派生文件，不手工维护。修改合同后运行 `corepack pnpm generate:strategy-api`，用 `corepack pnpm check:strategy-api` 检查一致性。CI 分别验证 FastAPI→JSON 与 JSON→TypeScript。

前端使用 openapi-fetch 的生成路径/类型，通过既有 Axios 发送请求。Cookie 会话、CSRF、每次调用的超时及 Axios 错误语义保留。Decimal 输入采用后端允许的精确字符串子集，响应金额和数量保持字符串；计数、时间间隔等普通数值不强行改成字符串。动态原生回执保留扩展字段，不假称所有 Venue 私有字段已有强类型定义。

TanStack Vue Query 管理 Funding 上下文、原指令状态、持仓和策略管理读取。查询键包括会话代数、用户、账户/策略和实际参数；注销或身份/权限变化会取消旧查询并清空缓存，迟到响应不得写入新会话。无持久化查询缓存、读取自动重试或 mutation 自动重放；可见页轮询只发 GET。写入成功只使相关读取失效。 Funding 执行页可见时每 3 秒更新上下文和持仓；切到分析页或隐藏页面时暂停这两项轮询。有效预览在后台刷新期间保留，输入变化、读取失败或超过 10 秒未成功更新即阻断操作；服务端派发前仍独立校验来源报价与风控。提交回执展示不等待持仓表刷新。

交易动作仍由明确操作触发，Funding 在发送前保存原指令幂等身份及所属用户；超时、刷新和重新登录只能查询原身份。登录缓存清理只移除自己的缓存键，不得清空全部浏览器存储而误删待恢复指令。准备请求体前后及收到响应后检查会话是否变化，避免跨登录派发或接收旧交易动作。

Platform→Runtime 请求统一由 `runtime_transport.py` 的进程连接池发出，保留 TLS 校验，不继承环境代理，不跟随重定向，不自动重试 POST；关闭服务时在后台任务退出后释放连接。超时继续交由指令和对账 Owner 处理，连接复用不产生新的重放规则。

管理成交列表与账户快照共用后端财务读取的成交选择和身份归属。`FillResponse` 返回完整 `orderId`、`externalOrderId`、`externalFillId`、`instructionId`、`batchId`、`origin` 和 `source`；没有对应指令的监控记录保留空关联。`fee` 与 `currency` 可空，前端不得把未知费用显示为零。策略损益的 `economicEvents` 和账户快照结算列表保留原币金额、来源及可证明的订单/指令/批次关联，供原币流水页逐笔核对。金额保持精确字符串；读取不创建成交或推进指令。

管理委托与成交返回可空的 `action`、`direction`、`instructionId` 和 `batchId`，根据原指令及已记录执行关联读取，不能从买卖方向推断开平。无明确业务动作的 MT5 监控记录可采用原生 `entryType`：进场为开仓、出场/对向平仓为平仓、反转为反向开平；缺失或冲突的历史标记不猜测，也不据此归属策略。原生 `reduceOnly=true` 明确标为平仓；其他风险处置委托标为 `risk_reduction`（异常处理），不沿用原开仓指令的动作，也不因买卖方向推断其开平。委托列表在分页前按账户、品种和原生订单身份合并历史别名；原行不修改，多个命令归属冲突返回 409，账户快照总数采用相同口径。

`FillResponse.orderConfirmedAt` 仅在同一规范订单的明确 Runtime 确认覆盖全部所选成交数量时提供，表示订单累计成交已被平台确认。它不是逐笔成交时刻。`timeQuality=source_clock_conflict` 表示原始成交时间晚于该确认超过 60 秒；MT5 缺乏确认上界时为 `source_clock_unverified`。`occurredAt` 保留原值，管理列表将冲突记录显示为带标签的订单确认时间，未核实的 MT5 时间留空并在详情保留原值；其他已分类记录使用 `venue_time` / `runtime_confirmation`，历史来源仍标为 `legacy`。委托的 `timeQuality` 区分 `platform_submission`、`venue_time` 及 `source_clock_unverified`，避免把未经核验的 MT5 原生时间称为平台提交时间。该元数据只用于管理展示，不改写财务事件时间或执行状态。

订单管理的开平记录、委托明细和逐笔成交使用同一组已归属的原生数据。每笔委托的展开详情及汇总行显示已实现盈亏、手续费、资金费、库存费和已实现净额；手续费事件按财务读模型的现金流符号转为正的成本后只计一次，原生成交已提供同类字段时不再叠加结算事件。跨币种或缺少订单/指令归属时保留原币分项并显示待核对，不以零或前端汇率补齐。逐笔成交直接展示原币手续费、已实现盈亏和库存费；这些字段只用于观察，不改变正式财务归属。

## 2. Authentication 与 RBAC

```http
Authorization: Bearer <host-injected-token>
X-Request-ID: <request-id>
```

- Live 环境必须使用 `api_key` 模式。
- Token 只通过 SHA-256 哈希匹配。
- Role：viewer、researcher、trader、risk_officer、operations、admin。
- Permission 默认拒绝。
- actor、reviewer 等身份必须匹配认证 Principal。
- `/health` 不返回业务数据。

详细合同：`AUTH_RBAC_LIVE_SESSIONS.md`。

## 3. LiveTradingSession（历史兼容）

```http
POST /api/v1/live-trading/sessions
GET  /api/v1/live-trading/sessions
POST /api/v1/live-trading/sessions/{sessionId}/approve
POST /api/v1/live-trading/sessions/{sessionId}/revoke
```

兼容接口保留早期验收记录及审计结构。2026-09-09 起，正常交易不再申请或认领 LiveTradingSession；其范围、时效、审批与额度不影响正常订单。CEO Browser Session 的正常交易权限与安全边界见 [AUTHORIZATION.md](AUTHORIZATION.md)。

## 4. Credential Rotation Metadata

```http
POST /api/v1/security/credential-rotations
GET  /api/v1/security/credential-rotations
GET  /api/v1/security/credential-rotations?credential_ref=...
```

写入示例：

```json
{
  "idempotencyKey": "rotation-bybit-20260723-01",
  "credentialRef": "secret://windows-credential-manager/bybit-live-001",
  "provider": "windows-credential-manager",
  "version": "2026-07-23.1",
  "rotatedAt": "2026-07-23T16:00:00+00:00",
  "reason": "scheduled rotation"
}
```

语义：

- POST 需要 admin 权限。
- GET 需要 audit 权限。
- Actor 来自认证 Principal。
- Provider 必须与 Reference 一致。
- `rotatedAt` 必须含时区。
- 同一幂等键或同一 Reference/Provider/Version 只允许相同载荷重放。
- 冲突返回 409。
- 只保存元数据，不保存凭证内容。

## 5. Secret Reference Contract

```text
secret://environment/<secret-name>
secret://windows-credential-manager/<secret-name>
```

Legacy `secret://<secret-name>` 仅保留迁移兼容，并标记 `legacyReference=true`。

Runtime Inspection 可返回 Credential Reference、Provider、Secret Name、Version、Configured、Available/Missing Fields、Legacy 标记和 Environment Provider 的 Env Prefix；不得返回值、长度、摘要、前后缀或其他可推断信息。

`resolve` 不是公共 API，只在 Runtime Gateway 内部使用。

## 6. Catalog

```http
GET /api/v1/strategies/definitions
GET /api/v1/strategies/instances
GET /api/v1/strategies/instances/{strategyInstanceId}
GET /api/v1/strategies/instances/{strategyInstanceId}/accounts
GET /api/v1/accounts
GET /api/v1/accounts/{accountId}
GET /api/v1/instruments
GET /api/v1/instruments/{instrumentId}
```

客户端不得覆盖 Quantity Unit、Settlement Currency、Contract Multiplier 或后端 ID 绑定。

## 7. TradeCommand

```http
POST /api/v1/trading/commands
GET  /api/v1/trading/commands/{tradeCommandId}
```

```json
{
  "idempotencyKey": "client-command-001",
  "strategyInstanceId": "strategy-id",
  "accountId": "account-id",
  "instrumentId": "instrument-id",
  "symbol": "XAUTUSDT",
  "side": "buy",
  "orderType": "limit",
  "quantity": "0.01",
  "price": "2400"
}
```

Live Command 依次通过 Authentication、RBAC/CEO 权限、Catalog 与账户绑定、Platform Live Gate、Kill Switch/对账风险、Order Insert 和 Runtime Live Gate；不再认领验收会话。

发往 Runtime V1 的订单命令由 Platform 从合约目录补入 `instrument_type`，客户端不能自行覆盖。Runtime 将它与原命令一同持久化，保证同名现货和永续的提交及后续原生读取始终使用正确市场；旧 V1 命令省略该可空字段仍可读取。双端字段及序列化样例由 `runtime-v1.json`、`runtime-v1-golden.json` 共同约束，具体 Bybit 行为见 [Venue Adapter](VENUE_ADAPTERS.md)。

## 8. ExecutionBatch 与风险

```http
POST /api/v1/trading/execution-batches
GET  /api/v1/trading/execution-batches
GET  /api/v1/trading/execution-batches/{batchId}
GET  /api/v1/trading/execution-batches/{batchId}/risk
GET  /api/v1/trading/execution-batches/{batchId}/risk-actions
POST /api/v1/trading/execution-batches/{batchId}/risk-actions
```

每条 Leg 生成独立 TradeCommand。Kill Switch、腿间延迟、残留敞口和 RiskAction 均可审计、幂等并 fail-closed。

## 9. Order、Fill 与未知结果

```http
GET  /api/v1/trading/orders
GET  /api/v1/trading/orders/{orderId}
GET  /api/v1/trading/fills
POST /api/v1/trading/orders/{orderId}/reconcile
POST /api/v1/trading/orders/{orderId}/venue-reconcile
```

- Journal Reconcile 请求 Runtime 核对原订单证据并读取持久化 Journal；Runtime 可能执行原生只读查询，不重提订单。
- Venue Reconcile 查询外部 Order 与 Fill/Deal。
- 两者都不得重提原订单。
- 两种恢复使用 `reconciliation:review`；CEO 可执行，浏览器 CSRF 及订单缺失接受的独立管理边界保持有效。
- 网络结果不确定时保持 `result_unknown`。
- Runtime HTTP 错误、截断/非 JSON 回执、无效事件和回执落库失败均不能证明未下单。已经分配订单时，TradeCommand 的异常状态以订单证据为准，不得把未知订单标成确定拒绝；重放只返回原身份。对已终结订单调用 Journal Reconcile 时同步其 TradeCommand 状态，不再访问 Runtime。迟到 ACK 不得把部分成交降级为已受理，成交自带的原生订单 ID 必须保存。
- Deprecated `POST /api/v1/trading/orders` 不得用于 Live。

## 10. Kill Switch

```http
GET /api/v1/risk/kill-switches/{scopeType}/{scopeId}
PUT /api/v1/risk/kill-switches/{scopeType}/{scopeId}
GET /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
PUT /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
```

Scope：global、strategy、account。修改需要 risk_officer/admin，Body Actor 必须匹配 Principal。

## 11. Runtime Capability、History 与 Account Risk

```http
GET /gateway/capabilities
GET /gateway/connectivity
GET /gateway/venue-readiness
GET /venue/orders
GET /venue/order-history
GET /venue/orders/by-platform/{platformOrderId}
GET /venue/orders/{externalOrderId}
GET /venue/fills
GET /venue/fill-history
GET /venue/positions
GET /venue/balances
GET /venue/account-risk
GET /venue/instruments/{symbol}
GET /venue/economic-events
POST /venue/orders/{externalOrderId}/cancel
```

History Query：

```http
GET /venue/order-history?accountId=...&symbol=...&startTime=...&endTime=...&limit=50&scope=closed&cursor=...
GET /venue/fill-history?accountId=...&symbol=...&startTime=...&endTime=...&limit=50&cursor=...
```

- 单次历史窗口不超过七天。
- 单页不超过 100 条。
- Bybit 使用交易所 `nextPageCursor`。
- MT5 在固定窗口内使用确定性整数偏移续页。
- Query 失败不得解释为空仓、零余额或“没有历史”。
- Query API 不得隐式执行订单。

Cross-spread 聚合只读接口：

```http
GET /api/v1/trading/cross-spread/observability?historyHours=24&limit=20
```

该接口分别读取 Bybit 与 MT5 的 Account Risk、Position、Active Order、Recent Order 和 Recent Fill。每个区块都有独立状态，部分失败返回 `partial`，不伪造零值。

完整字段和数据质量语义见 `LIVE_ACCOUNT_OBSERVABILITY.md`。

`GET /api/v1/trading/cross-spread/snapshot` 的 `positionOverview` 返回当前活动组的剩余浮盈亏：`groups` 按 `planId`、`planUpdatedAt` 与 `quantityOz` 关联 Exit Plan，包含双腿入场价、`bybitPnlUsdt`、`mt5PnlUsdt`、`totalPnlUsdt`、`openTime`、质量及缺失原因；总览携带同名汇总、质量和 `asOf`。金额为精确 Decimal 字符串或 null。费用、已实现及结算不混入该字段，计算边界由 [Cross 合同](CROSS_SPREAD_EXECUTION.md) 维护。Snapshot 的 Venue Position 保留 `accountId`、`currency` 与 `asOf`，用于核对原生票据、币种及新鲜度。

`GET /api/v1/trading/cross-spread/trading-rules` 返回当前绑定 Bybit/MT5 账户的两腿合约规格和会话状态。MT5 规则额外返回 `marketStatus`（`open`、`closed`、`buffer`、`unknown`）、`tradingHours`、`tradingTimezone`、`automaticExitAllowed`、`automaticExitBlockReason` 和 `automaticExitGuardMinutes`。`buffer` 只表示后台自动 TP/SL 暂停，人工开平仍由 `openAllowed`/`closeAllowed` 单独控制；`closed` 或 `unknown` 时正常双腿执行 fail-closed。MT5 周期性维护和节假日日期覆盖由 Runtime 配置维护，不能在前端生成或写死。

`positionOverview.unattributedPositions` 保留没有归属的 MT5 Ticket 和 Bybit 净仓差额，返回 Venue、账户、Symbol、原生有符号数量及可证明的原生字段，不生成虚构组合或交易操作。Exit Plan 的可选 `originLabel` 来自恢复审计，供持仓和退出入口识别恢复的误单。

### 11.1 Cross-spread synthetic lifecycle

```http
POST /api/v1/trading/cross-spread/lifecycle/open
PATCH /api/v1/trading/cross-spread/exit-plans/{planId}
POST /api/v1/trading/cross-spread/exit-plans/{planId}/close
GET  /api/v1/trading/cross-spread/exit-plans
POST /api/v1/trading/cross-spread/exit-plans/evaluate
```

Market Open 请求：

```json
{
  "direction": "LONG_SPREAD",
  "quantityOz": "1",
  "takeProfitSpread": "0",
  "stopLossSpread": "-3",
  "executionMode": "market",
  "takeProfitExecutionMode": "market",
  "stopLossExecutionMode": "market"
}
```

FOK Limit Open 请求：

```json
{
  "direction": "LONG_SPREAD",
  "quantityOz": "1",
  "takeProfitSpread": "0",
  "stopLossSpread": "-3",
  "executionMode": "limit",
  "limitStrategy": "fok",
  "limitSpread": "-0.8",
  "takeProfitExecutionMode": "limit",
  "takeProfitLimitStrategy": "fok",
  "stopLossExecutionMode": "market",
  "stopLossLimitStrategy": "fok"
}
```

PostOnly Chase Open 请求使用同一 Limit 合同：

```json
{
  "direction": "LONG_SPREAD",
  "quantityOz": "1",
  "takeProfitSpread": "0",
  "stopLossSpread": "-3",
  "executionMode": "limit",
  "limitStrategy": "post_only_chase",
  "limitSpread": "-0.8",
  "takeProfitExecutionMode": "market",
  "stopLossExecutionMode": "market"
}
```

人工 Close 请求：

```json
{
  "quantityOz": "0.5",
  "executionMode": "limit",
  "limitStrategy": "post_only_chase",
  "limitSpread": "-1.1"
}
```

`quantityOz` 可省略；省略表示平掉该 Exit Plan 的全部剩余量，提供时表示本次部分平仓量，必须大于零且不超过计划剩余量。平台不把 1 盎司作为产品上限；实际可下数量仍由 Venue 规格、保证金和风险门控决定。

请求约束：

- `executionMode=limit` 必须提供 `limitSpread`。
- `executionMode=market` 不得提供 `limitSpread`，并忽略 Limit Strategy。
- `limitStrategy` 允许 `fok` 或 `post_only_chase`；缺省值为 `fok`。
- TP/SL 分别持久化 Execution Mode 与 Limit Strategy。
- 自动 TP/SL 使用 Exit Plan 保存的 Mode/Strategy，并使用原子 Claim 保存的 `triggerSpread` 作为 Limit Spread。
- 自动 Limit 不静默回退到 Market。
- Limit 请求先校验当前可成交价差；不满足限制时返回 `409`，不创建 Batch。
- PostOnly Chase 还受 Runtime 独立禁用开关约束，默认关闭。

Open 和 Close 响应包含标准化意图：

```json
{
  "orderIntent": {
    "action": "OPEN_LONG_SPREAD",
    "executionType": "LIMIT",
    "triggerReason": "MANUAL",
    "direction": "LONG_SPREAD",
    "isOpen": true
  }
}
```

Limit 响应同时附加 Platform 定价证据：

```json
{
  "limitExecution": {
    "direction": "BUY_BYBIT_SELL_MT5",
    "limitStrategy": "post_only_chase",
    "limitSpread": "-0.8",
    "executableSpread": "-0.9",
    "mt5ReferencePrice": "2501.0",
    "hedgeReserve": "0",
    "bybitTickSize": "0.1",
    "rawBybitLimitPrice": "2500.2",
    "bybitLimitPrice": "2500.2",
    "currentlyExecutable": true,
    "timeInForce": "PostOnly"
  }
}
```

权威语义：

- `action` 只表示开多、平多、开空或平空。
- `executionType` 只表示 `MARKET` 或 `LIMIT`。
- `triggerReason` 表示人工、策略、止盈、止损、Kill Switch 或风险降低来源。
- TP/SL 不是独立订单类型，而是触发普通 Close Action。
- 四类动作继续映射为 `OPEN_LONG / CLOSE_LONG / OPEN_SHORT / CLOSE_SHORT`。
- FOK 只有终态精确全成交才允许 MT5；零成交失败不提交 MT5，人工 Close 可恢复 `active`。
- PostOnly Chase 只有去重后的累计成交量精确等于请求量才允许 MT5。
- PostOnly 部分成交、私有流断线、事件序列/身份异常或 REST 不一致不提交 MT5，并进入对账／人工介入。
- `limitExecution` 是提交前 Platform 定价证据，不等于 Venue 成交证据。
- 详细公式、状态机和限制见 `CROSS_SPREAD_SYNTHETIC_EXECUTION.md`。

## 12. Runtime Command

Runtime 对重复 `command_id` 在 Journal 事务内校验原有业务字段：账户、平台订单、标的、方向、数量、价格、执行方式、减仓和仓位目标等必须一致；冲突返回 409 且不调用 Gateway。等值 Decimal 和新请求的 `received_at` 不构成业务变化。适配器未分类异常或执行证据保存失败后保留原认领并标记 `result_unknown`，不能重新派单；错误响应不暴露适配器异常正文。

```http
POST /commands/orders
```

Runtime V1 Command 在原有字段上增加：

```text
execution_policy = default | fok | post_only_chase
```

约束：

- `fok` 和 `post_only_chase` 仅允许 `order_type=limit`。
- `default` 保持旧 Market 和普通 Limit 兼容行为。
- Runtime 在 Gateway 副作用前原子抢占 Command，并独立检查 Environment、Live Write、Account/Strategy/Symbol Allowlist、单笔/单日限额和 Credential Reference。
- 任一条件失败不得回退 Fake Gateway。

### Funding 执行方式与恢复

`PATCH /api/v1/trading/funding/exit-plans/{open_instruction_id}` 保存该组一次性价差退出设置：`expectedRevision`、`enabled`、可空十进制 `takeProfitSpread` / `stopLossSpread`。首次 revision 为 0；并发版本或已触发冲突返回 409，阈值无效返回 422。需要 CEO 交易权限及浏览器 CSRF。`GET /funding/positions` 的 `exitPlan` 返回版本、阈值、触发证据、原平仓指令及暂停原因；无设置为 null。成交规则归资金费率产品合同及执行风险合同。此配置接口不派单、不打开 Live Write；后台触发仍受原交易准入约束。


执行上下文和开、平仓 POST 的 `quantity` 均为永续目标数量。`openSizing` 返回永续数量、反推现货毛量、买入基础币费率、预计净到账、取整余量及有效性；按手续费和原生现货步长选择最接近目标的合法现货数量，实际微小余差如实保留。名义金额只用于建议数量，不替代提交的永续目标。页面提交冻结的 `expectedPerpetualQuantity` 时须与目标一致。两腿数量和费率冻结在计划中，幂等重放读取原计划，不重算历史计划。现货累计释放按冻结两腿数量比例向下量化，最终全成交可释放完整现货上限。

Funding 持仓返回 `isAbnormal`、`abnormalReason`、`abnormalAction`、`remainingPerpetualQuantity`、`remainingSpotHolding` 和 `netDeltaQuantity`；实际持仓与扣除预约后的可交易数量分离。已完成但实际净现货少于永续，或正敞口达到一个永续步进的活动组标记异常；已结束组退出异常区。Cross 组合返回其归属腿数量、方向及 MT5 Ticket，管理页不得回退到全账户仓位分配。

`POST /api/v1/trading/funding/instructions` 接受 `executionPolicy: market | fok | post_only_chase`，以及仅 FOK 必填的正有限十进制字符串 `perpetualLimitPrice`。省略执行方式仍保持既有 PostOnly Chase 合同，页面新指令默认市价；默认字段规范化不得改变既有幂等指纹。执行方式与价格属于不可变计划，同一幂等键更改它们返回冲突。

提交完成账户/规格/数量及当前实盘准入校验，原子持久化冻结计划和批次后立即返回原指令状态，不等待场所下单或成交。`accepted` 只表示耐久受理；已有 Funding 后台执行器负责推进和重启恢复，GET 返回实际进度。同键 POST 仅核对原载荷并读取原指令，不额外驱动执行。实盘准入关闭时在发布前拒绝，不能留下等待以后开闸的休眠指令。

开仓与指定组合的部分/全部平仓共用该请求及原执行主链。永续市价和 FOK 只尝试一次；FOK 使用原生全成全撤并要求精确全成交后才释放现货，非 FOK 延续按已证明成交增量释放现货的合同。平仓永续为 reduce-only，现货按净到账及步长量化。

Funding 的报价、执行上下文及计划采用同一活动绑定，实盘 primary、模拟 local_test，校验账户环境和写权限。实盘计划冻结对应账户、symbol、Spot/Perpetual 类别的原生合约规格；缺失、类别不符、数量或价格不符合精度时创建失败。

`GET /api/v1/trading/funding/instructions/{instructionId}` 及按 `idempotencyKey` 查询把持久化 `rejected` 映射为终态 `failed`。零敞口拒单仅进入历史，不占活动持仓。前端在超时或未知时只查询原指令；明确拒绝且查询确认无指令后才能解除旧草稿。原生终态零成交须检查所有本地订单、成交及现货释放证据后才能释放预约。

`POST /api/v1/trading/funding/instructions/{instruction_id}/recover-close` 仅接受 CEO 会话及服务端提供的 `idempotencyKey`。原平仓永续已全成、现货存在确定未完成量且所有既有结果明确时，持仓返回 `abnormalAction=finish_close`、`recoveryCloseInstructionId`、`recoveryIdempotencyKey`、`recoverySpotQuantity`。确认后沿原账户、原批次，仅提交剩余现货卖单；须核对原生订单、成交、手续费、永续仓位、现货余额及当前交易准入。拒单历史保持不可变；未知、过期余额、归属或绑定冲突拒绝派发。

恢复子单存在后，同键请求仅核对原单，不重复派发；最终核对中断保留异常入口及原键，`recoverySpotQuantity=0` 表示只核对已有恢复请求。证据完整且原冻结两腿数量全部完成后，原指令结束并释放资源。永续仍未完成的其他失败平仓保留人工核对，不能用反向开仓冒充平仓恢复。

## 13. Bybit 与 MT5

### Bybit

- V5 Unified Trading API。
- Platform Order ID 确定性派生 Order Link 前缀；PostOnly 子单使用唯一子编号。
- Place ACK 不生成虚假 Fill。
- Market Order 使用有界终态成交确认。
- FOK 使用 `timeInForce=FOK`，并要求终态精确全成交。
- PostOnly 使用 `timeInForce=PostOnly`，通过 disabled-by-default Private Order/Execution Stream 驱动有界 Chase。
- PostOnly 受 TTL、最小改单 Tick、最大变更次数和冷却约束。
- Amend 被拒绝后，只有终态 Cancel 事件确认才允许 Repost。
- Execution ID 去重；部分成交、断线或状态不一致不放行 MT5。
- REST 只用于有界终态恢复/对账，不授权盲目重复提交。
- Position 强平价只使用交易所返回的有限 `liqPrice`。

### MT5

- Windows Terminal 或注入测试 Provider。
- 下单前 `order_check`，写入使用 `order_send`。
- Magic、Comment、Order/Deal/Position Ticket 可追溯。
- MT5 只在 Bybit 主腿满足对应策略的确认合同后提交。
- Swap、Commission、Fee 来自外部 Deal。
- Python Position API 不提供权威单仓强平价；风险使用 Account Margin Level、Margin Call 与 Stop Out。

## 14. Venue Reconciliation

```http
POST /api/v1/ops/venue-reconciliation/runs
GET  /api/v1/ops/venue-reconciliation/runs/{runId}
GET  /api/v1/ops/venue-reconciliation/runs/{runId}/differences
POST /api/v1/ops/venue-reconciliation/differences/{differenceId}/resolve
POST /api/v1/ops/live-economic-events/import
```

外部与本地冲突形成 Difference。`accepted` 不代表一致，Open 与 Accepted 均阻断批准和扩大实盘。

## 15. EOD

```http
POST /api/v1/ops/eod-reconciliation/reports
GET  /api/v1/ops/eod-reconciliation/reports
GET  /api/v1/ops/eod-reconciliation/reports/{reportId}
POST /api/v1/ops/eod-reconciliation/reports/{reportId}/review
```

EOD 编排 Order、Fill/Deal、Position、Balance、Funding、Swap、Fee、FinancialFact、Formal PnL 和 Formal NAV。外部调用失败进入 errors，不生成虚假 complete。

## 16. FinancialFact 与 Formal Accounting

```http
POST /api/v1/financial-facts
GET  /api/v1/financial-facts
POST /api/v1/strategies/instances/{strategyInstanceId}/financials/rebuild
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-positions
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-pnl
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots/run
```

## 17. Redaction 与审计

Backend 与 Runtime Redactor 处理嵌套敏感键、Bearer Token、私钥块、受控字段赋值、URL 认证信息和 Exception Message，统一替换为 `[REDACTED]`。

Rotation、Authentication、Session、Kill Switch、RiskAction、Difference、EOD 等操作均记录非敏感审计元数据。

## 18. 通用规则

- 金融数值使用十进制字符串。
- 时间使用带时区 ISO 8601。
- Query 与 Command 分离。
- ACK 与 Fill 分离。
- `result_unknown` 与失败不同。
- 缺失值与零不同。
- Stablecoin 不自动等同法币。
- Platform 与 Runtime Live Write 默认关闭。
- PostOnly Chase 默认关闭。
- 工程验收不等于真实账户运营验收。

## 账户资金历史的总资产字段

策略账户快照的 `equityHistory[]` 保留 `equity` 的交易账户权益语义，并增加可空 Decimal 字段 `totalAssets`，以字符串或 null 输出。该值来自同一账户、币种和历史快照的 `account_risk_snapshots.total_assets`；无记录时为 null，不能用 equity 代替。历史时间仍为带时区时间。统一交易账户总资产曲线仅使用非空 totalAssets；当前摘要使用 accountRisk.totalAssets。生成的 OpenAPI 与前端类型同步维护。

Strategy account history includes nullable decimal-string `equityDrawdown` and `totalAssetsDrawdown` percentages, with corresponding `*DrawdownQuality` fields. `estimated` is a cash-flow-adjusted Modified Dietz estimate; `baseline`, missing coverage/valuation, unknown classification, invalid capital and downstream gaps do not contain a percentage. Runtime's read-only `/venue/capital-flows?accountId=&startTime=&endTime=` returns account/window identity, covered scopes and deduplicated native movements; seven-day bounds and full pagination apply. Monitoring methodology is owned by `LIVE_ACCOUNT_OBSERVABILITY.md`.

The account snapshot accepts optional `includeDetails=false` for a lightweight management read. This keeps balances, risk, equity history and current venue-synced positions, but omits orders, fills and the historical `finance` payload. The default remains `true` for callers that need the full account and audit detail.

The management capital tab requests this summary mode. Non-Cross PnL and order tabs request full details with a distinct query key, so a summary cannot satisfy a detail read. Cross account charts always use summaries; its strategy PnL and orders have separate reads, and the capital tab does not wait for strategy PnL. Overlapping refreshes reuse an in-flight request for the same section; results from an old section or unmounted page cannot overwrite the current view.


## Pretrade strategy research

The generated strategy OpenAPI includes `/api/v1/research/strategies/` catalog, collection status, single-venue funding board, pair latest/series/distribution, cashflow scenario, persistent experiments/events/replay/cancel and private parameter drafts. Responses preserve source, clock basis, received/published watermarks, coverage, quality warnings and method/data/parameter versions. Detailed scope, numeric and temporal semantics belong to [Research Data](RESEARCH_DATA.md#strategy-pretrade-research-v1); permissions belong to [Authorization](AUTHORIZATION.md#strategy-research-request-permissions). Runtime's separate `market-events.v1` read-only batch transport cannot submit orders or mutate the Platform database.
