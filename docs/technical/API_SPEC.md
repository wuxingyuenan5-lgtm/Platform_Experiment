# Platform V6 API Specification

状态：`active`  
Platform API Prefix：`/api/v1`  
Platform 组合入口：`platform-backend/app/main.py`  
Runtime 根地址：`http://127.0.0.1:8100`  
当前阶段：`docs/planning/V6-Phase4D-实盘日终对账与运营门禁.md`

## 1. 服务边界

| 服务 | 默认地址 | 权威职责 |
|---|---|---|
| Platform Backend | `http://127.0.0.1:8000` | Strategy、Account、Command、Order、Risk、FinancialFact、Reconciliation、EOD Report、Formal Accounting |
| Execution Runtime | `http://127.0.0.1:8100` | Journal、Live Safety、Account Router、Venue Query、外部副作用隔离 |
| Frontend | `http://127.0.0.1:5173` | 查询、交互和命令发起 |

```http
GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8100/health
GET http://127.0.0.1:8100/status
GET http://127.0.0.1:8100/gateway/capabilities
```

## 2. Catalog

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

TradeCommand、ExecutionBatch、RiskAction、FinancialFact、Live Adapter 映射和 EOD Report 必须使用 Backend Catalog。客户端不得覆盖 Quantity Unit、Settlement Currency 和 Contract Multiplier。

## 3. TradeCommand

```http
POST /api/v1/trading/commands
GET  /api/v1/trading/commands/{tradeCommandId}
```

```json
{
  "idempotencyKey": "client-command-001",
  "strategyInstanceId": "strategy-funding-live",
  "accountId": "account-live-bybit",
  "instrumentId": "instrument-xaut-usdt",
  "symbol": "XAUTUSDT",
  "side": "buy",
  "orderType": "limit",
  "quantity": "0.01",
  "price": "2400"
}
```

服务端校验 Strategy、active Binding、Account、Instrument、ContractSpecification、数量、价格步长、Platform Live Gate 和 Kill Switch。正式 TradeCommand 将 StrategyInstance 身份传到 Runtime，以便 Runtime 独立执行 Strategy allowlist。

## 4. ExecutionBatch 与风险处置

```http
POST /api/v1/trading/execution-batches
GET  /api/v1/trading/execution-batches
GET  /api/v1/trading/execution-batches/{batchId}
GET  /api/v1/trading/execution-batches/{batchId}/risk
GET  /api/v1/trading/execution-batches/{batchId}/risk-actions
POST /api/v1/trading/execution-batches/{batchId}/risk-actions
```

执行顺序：Catalog → Kill Switch → Batch 原子认领 → Risk Policy 快照 → 每腿 TradeCommand → 腿间延迟与残留风险检查 → RiskAction。

## 5. Order、Fill 与未知结果

```http
GET  /api/v1/trading/orders
GET  /api/v1/trading/orders/{orderId}
GET  /api/v1/trading/fills
POST /api/v1/trading/orders/{orderId}/reconcile
POST /api/v1/trading/orders/{orderId}/venue-reconcile
```

- Journal Reconcile 只查询 Runtime Journal。
- Venue Reconcile 查询外部 Order 和 Fill/Deal。
- 两者都不得重新提交原订单。
- Runtime 返回 502 或网络结果不确定时，Platform 保持 `result_unknown`。
- `POST /api/v1/trading/orders` 仅为 deprecated 兼容入口。

## 6. Kill Switch 与 Execution Risk

```http
GET /api/v1/risk/kill-switches/{scopeType}/{scopeId}
PUT /api/v1/risk/kill-switches/{scopeType}/{scopeId}
GET /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
PUT /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
```

Scope：`global/*`、`strategy/{strategyInstanceId}`、`account/{accountId}`。自动平仓和替代对冲必须经过 TradeCommand。

## 7. Runtime Gateway Capability

```http
GET /gateway/capabilities
```

响应示例：

```json
{
  "gateway": "bybit_mt5",
  "environment": "live",
  "liveWriteEnabled": false,
  "adapters": [
    {
      "adapter": "bybit_live",
      "environment": "live",
      "configured": true,
      "operational": true,
      "writeEnabled": false,
      "accountIds": ["account-live-bybit"],
      "capabilities": ["order_query", "fill_query", "funding_query"],
      "missingRequirements": [],
      "checkedAt": "2026-07-23T12:00:00+00:00"
    }
  ]
}
```

Capability 不返回 Secret 值。`configured=true` 只表示必需配置完整；`operational=true` 还要求依赖和运行环境可用；`writeEnabled=true` 还要求 Runtime Live Write 显式打开。

## 8. Runtime Venue Query

```http
GET /venue/orders/by-platform/{platformOrderId}
GET /venue/orders/{externalOrderId}
GET /venue/fills?accountId=...&externalOrderId=...&platformOrderId=...
GET /venue/positions?accountId=...
GET /venue/balances?accountId=...
GET /venue/economic-events?accountId=...&instrumentId=...&eventType=...
POST /venue/orders/{externalOrderId}/cancel
```

Snapshot 必须包含 source、外部身份、Account、Instrument（适用时）、时间和数据质量。查询失败与空结果不同；Runtime 不可用不得被解释为空仓或零余额。

## 9. Runtime Command Contract

```http
POST /commands/orders
```

```json
{
  "command_id": "trade-command-id",
  "platform_order_id": "platform-order-id",
  "strategy_instance_id": "strategy-instance-id",
  "account_id": "account-id",
  "instrument_id": "instrument-id",
  "symbol": "XAUTUSDT",
  "side": "buy",
  "order_type": "market",
  "quantity": "0.01",
  "price": null,
  "reduce_only": false
}
```

Runtime 在调用 Venue 前检查 Command Journal 和 Live Safety。确定性门禁或 Venue 拒绝返回 `order_rejected`；可能已到 Venue 但无法确认时返回 502，使 Platform 进入 `result_unknown`。

## 10. Runtime Live Safety 配置

正式模板：`execution-runtime/.env.live.example`

```text
VG_RUNTIME_ENVIRONMENT=live
VG_RUNTIME_GATEWAY_NAME=bybit_mt5
VG_RUNTIME_JOURNAL_PATH=./data/live_runtime_journal.db
VG_RUNTIME_LIVE_WRITE_ENABLED=false
VG_RUNTIME_LIVE_ACCOUNT_ALLOWLIST=
VG_RUNTIME_LIVE_STRATEGY_ALLOWLIST=
VG_RUNTIME_LIVE_SYMBOL_ALLOWLIST=
VG_RUNTIME_LIVE_MAX_ORDER_NOTIONAL=0
VG_RUNTIME_LIVE_MAX_DAILY_NOTIONAL=0
```

Bybit：

```text
VG_RUNTIME_BYBIT_CREDENTIAL_REF=secret://bybit-live-001
VG_RUNTIME_BYBIT_ACCOUNT_IDS=
VG_RUNTIME_BYBIT_INSTRUMENT_MAP=
VG_RUNTIME_BYBIT_DEMO_MODE=false
VG_SECRET_BYBIT_LIVE_001_API_KEY=...
VG_SECRET_BYBIT_LIVE_001_API_SECRET=...
```

MT5：

```text
VG_RUNTIME_MT5_CREDENTIAL_REF=secret://mt5-live-001
VG_RUNTIME_MT5_ACCOUNT_IDS=
VG_RUNTIME_MT5_INSTRUMENT_MAP=
VG_RUNTIME_MT5_TERMINAL_PATH=
VG_SECRET_MT5_LIVE_001_LOGIN=...
VG_SECRET_MT5_LIVE_001_PASSWORD=...
VG_SECRET_MT5_LIVE_001_SERVER=...
```

Secret 值不得写入仓库、日志、审计、Markdown、截图或 API 响应。

## 11. Bybit Live 语义

- V5 Unified Trading API。
- Platform Order ID 确定性派生唯一 `orderLinkId`。
- Place-order ACK 只生成 `order_acknowledged`，不直接生成 Fill。
- 最终状态通过 Open Orders、Order History 和 Executions 查询。
- Execution `execId` 用作 Fill 自然身份。
- Transaction Log 映射 Funding 和 Fee。
- Account、Category、Symbol、Instrument 映射必须显式。

## 12. MT5 Live 语义

- 仅支持 Windows Terminal 或测试注入 Provider。
- 下单前 `order_check`，写入使用 `order_send`。
- 查询使用 `orders_get`、`history_orders_get`、`history_deals_get`、`positions_get`、`account_info`。
- Magic、Comment、Order Ticket、Deal Ticket 和 Position Ticket 用于追溯。
- Deal 中 Swap、Commission 和 Fee 进入 Economic Event。
- Terminal 未连接、登录账号不匹配或权限不足时 fail-closed。

## 13. Live Economic Event Import

```http
POST /api/v1/ops/live-economic-events/import
```

```json
{
  "idempotencyKey": "economic-import-20260723",
  "strategyInstanceId": "strategy-funding-live",
  "accountId": "account-live-bybit",
  "eventType": "funding",
  "actor": "operations"
}
```

- Runtime Query 返回 Funding、Swap、Fee。
- External Event ID 用作 FinancialFact 自然身份。
- 重复 Import 返回原结果。
- 相同 Import 幂等键不同载荷返回 409。
- 缺 Instrument 映射的事件进入 `skippedExternalIds`，不伪装为完整导入。

## 14. Venue Reconciliation

```http
POST /api/v1/ops/venue-reconciliation/runs
GET  /api/v1/ops/venue-reconciliation/runs/{runId}
GET  /api/v1/ops/venue-reconciliation/runs/{runId}/differences
POST /api/v1/ops/venue-reconciliation/differences/{differenceId}/resolve
```

Difference Type：`missing_local`、`missing_external`、`quantity_mismatch`、`price_mismatch`、`currency_mismatch`、`status_mismatch`。差异不得无痕覆盖，首次处置记录不可被重复请求改写。

`accepted` 只表示风险被人工接受，不表示数据已经一致。Open 与 Accepted Difference 均阻断扩大实盘。

## 15. EOD Reconciliation

```http
POST /api/v1/ops/eod-reconciliation/reports
GET  /api/v1/ops/eod-reconciliation/reports
GET  /api/v1/ops/eod-reconciliation/reports/{reportId}
POST /api/v1/ops/eod-reconciliation/reports/{reportId}/review
```

创建请求：

```json
{
  "idempotencyKey": "eod-20260723-strategy-account",
  "businessDate": "2026-07-23",
  "timezone": "Asia/Shanghai",
  "valuationTime": "2026-07-23T23:59:00+08:00",
  "strategyInstanceId": "strategy-funding-live",
  "accountId": "account-live-bybit",
  "actor": "eod-runner",
  "owner": "operations-owner",
  "dueAt": "2026-07-24T10:00:00+08:00"
}
```

约束：

- `timezone` 必须为有效 IANA 时区。
- `businessDate` 必须与 `valuationTime` 的本地日期一致。
- 相同幂等键或自然身份、相同载荷返回原报告。
- 相同身份不同载荷返回 409。
- 订单范围为业务日期窗口，加上估值时点仍未终结的历史订单。
- 编排 Position、Balance、Funding、Swap、Fee、FinancialFact、Formal PnL 和 Formal NAV。
- 外部失败进入 errors，不能生成虚假 complete。
- 报告状态：`complete`、`completed_with_differences`、`partial`、`failed`。
- SLA：`pending`、`met`、`breached`、`overdue`。
- Scale Gate：`blocked`、`eligible_for_review`、`approved_same_limits`、`needs_remediation`、`rejected`。
- `approved_same_limits` 只允许继续现有小资金限额，不自动提高限额或启用写入。

人工复核：

```json
{
  "decision": "needs_remediation",
  "reviewer": "risk-reviewer",
  "reason": "resolve position mismatch before the next live session"
}
```

复核使用不可变首写语义。只有清洁报告才能被标记 `approved_same_limits`。

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

FinancialFact 支持 `external_order`、`trade_fill`、`deal`、`funding`、`swap`、`fee`、`balance`、`position`、`fx`。Formal PnL 分为 Trading、Funding、Swap、Fee、FX 和 Total。

## 17. 审计与通用规则

Phase 4 新增审计：

- `live_economic_events_imported`
- `venue_order_reconciled`
- `venue_reconciliation_completed`
- `reconciliation_difference_resolved`
- `eod_reconciliation_completed`
- `eod_reconciliation_reviewed`

通用规则：

- JSON 金融数值使用十进制字符串。
- 时间使用带时区 ISO 8601。
- Query 与 Command 分离。
- ACK 与 Fill 分离。
- `result_unknown` 与失败不同。
- 缺失值与零不同。
- Stablecoin 不自动等同法币。
- 外部与本地冲突形成 Difference。
- Runtime Live Write 默认关闭。
- EOD Report 不自动修改外部仓位、解决差异、提高限额或开启写入。
- 工程验收不等于真实账户运营验收。
