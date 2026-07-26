# Platform V6 API Specification

状态：`active`  
Platform API Prefix：`/api/v1`  
Runtime 根地址：`http://127.0.0.1:8100`  
当前阶段：`docs/planning/V6-Production-Gate-密钥托管与脱敏.md`  
当前技术合同：`docs/technical/SECRET_PROVIDER_AND_REDACTION.md`

## 1. 服务边界

| 服务 | 默认地址 | 权威职责 |
|---|---|---|
| Platform Backend | `http://127.0.0.1:8000` | Auth、RBAC、Session、Command、Risk、Fact、Accounting、Reconciliation、EOD、Rotation Metadata |
| Execution Runtime | `http://127.0.0.1:8100` | Journal、Live Safety、SecretProvider、Gateway、Venue Query、外部副作用 |
| Frontend | `http://127.0.0.1:5173` | 产品交互，不持有 Venue 凭证内容 |

公开健康探针：

```http
GET /health
```

Live 环境中除 `/health` 外的 Platform API 均进入认证与授权边界。

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

## 3. LiveTradingSession

```http
POST /api/v1/live-trading/sessions
GET  /api/v1/live-trading/sessions
POST /api/v1/live-trading/sessions/{sessionId}/approve
POST /api/v1/live-trading/sessions/{sessionId}/revoke
```

申请范围固定 StrategyInstance、Account、Symbol、Side、Order Type、时间窗口、单笔/单日限额和只读证据。Applicant 与 Approver 必须不同。

Live Command 在写入 Order 和调用 Runtime 前，内部执行唯一 Approved Session 的原子额度认领。

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

Live Command 依次通过 Authentication、RBAC、Catalog、Platform Live Gate、Kill Switch、LiveTradingSession Claim、Order Insert 和 Runtime Live Gate。

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

- Journal Reconcile 只查 Runtime Journal。
- Venue Reconcile 查询外部 Order 与 Fill/Deal。
- 两者都不得重提原订单。
- 网络结果不确定时保持 `result_unknown`。
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

### 11.1 Cross-spread synthetic lifecycle

```http
POST /api/v1/trading/cross-spread/lifecycle/open
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
  "executionMode": "limit",
  "limitStrategy": "post_only_chase",
  "limitSpread": "-1.1"
}
```

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
