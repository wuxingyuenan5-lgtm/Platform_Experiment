# Platform V6 API Specification

状态：`active`  
Platform API Prefix：`/api/v1`  
Platform 组合入口：`platform-backend/app/main.py`  
Runtime 根地址：`http://127.0.0.1:8100`  
当前阶段：`docs/planning/V6-Phase4B-外部查询与对账差异.md`

## 1. 服务边界

| 服务 | 默认地址 | 权威职责 |
|---|---|---|
| Platform Backend | `http://127.0.0.1:8000` | Strategy、Account、Command、Order、Risk、FinancialFact、Reconciliation、Formal Accounting |
| Execution Runtime | `http://127.0.0.1:8100` | Gateway、Runtime Journal、Venue Query、外部执行隔离 |
| Frontend | `http://127.0.0.1:5173` | 查询、交互和命令发起 |

健康检查：

```http
GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8100/health
GET /api/v1/system/info
GET /api/v1/system/runtime-readiness
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

前端、TradeCommand、ExecutionBatch、RiskAction 和 FinancialFact 必须使用 Backend Catalog。客户端不得覆盖 Quantity Unit、Settlement Currency 和 Contract Multiplier。

## 3. TradeCommand

```http
POST /api/v1/trading/commands
GET  /api/v1/trading/commands/{tradeCommandId}
```

请求：

```json
{
  "idempotencyKey": "client-command-001",
  "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
  "accountId": "account_sim_usdt",
  "instrumentId": "instrument_btc_usdt",
  "symbol": "BTCUSDT",
  "side": "buy",
  "orderType": "limit",
  "quantity": "0.01",
  "price": "65000"
}
```

服务端校验 Strategy、active Binding、Account、Instrument、ContractSpecification、数量、价格步长和 Live 门禁。同一幂等键不同业务载荷返回 `409 Conflict`。

## 4. ExecutionBatch

```http
POST /api/v1/trading/execution-batches
GET  /api/v1/trading/execution-batches
GET  /api/v1/trading/execution-batches/{batchId}
```

请求：

```json
{
  "idempotencyKey": "funding-batch-001",
  "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
  "accountId": "account_sim_usdt",
  "strategyKey": "funding_arbitrage",
  "direction": "collect",
  "legs": [
    {
      "role": "spot",
      "instrumentId": "instrument_btc_usdt",
      "symbol": "BTCUSDT",
      "side": "buy",
      "orderType": "market",
      "quantity": "0.01"
    },
    {
      "role": "perp",
      "instrumentId": "instrument_btc_usdt_perp",
      "symbol": "BTCUSDT-PERP",
      "side": "sell",
      "orderType": "market",
      "quantity": "0.01"
    }
  ]
}
```

执行顺序：Catalog 校验 → Kill Switch → Batch 原子认领 → Risk Policy 快照 → 每腿 TradeCommand → 腿间时间与残留风险检查 → 风险处置。

## 5. Order、Fill 与 Journal 恢复

```http
GET  /api/v1/trading/orders
GET  /api/v1/trading/orders/{orderId}
GET  /api/v1/trading/fills
POST /api/v1/trading/orders/{orderId}/reconcile
```

`/reconcile` 只查询 Runtime Journal，不重下原订单。Runtime 无事件时保持 `result_unknown`。

Deprecated：

```http
POST /api/v1/trading/orders
```

新业务不得使用该入口。

## 6. Kill Switch 与 Execution Risk

```http
GET /api/v1/risk/kill-switches/{scopeType}/{scopeId}
PUT /api/v1/risk/kill-switches/{scopeType}/{scopeId}
GET /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
PUT /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
GET  /api/v1/trading/execution-batches/{batchId}/risk
GET  /api/v1/trading/execution-batches/{batchId}/risk-actions
POST /api/v1/trading/execution-batches/{batchId}/risk-actions
```

Kill Switch Scope：`global/*`、`strategy/{strategyInstanceId}`、`account/{accountId}`。

RiskAction：

- `hold_and_escalate`
- `flatten_filled_legs`
- `cancel_open_legs`
- `substitute_hedge`

自动平仓和替代对冲必须经过 TradeCommand。

## 7. Runtime Venue Query

### 7.1 Order

```http
GET /venue/orders/by-platform/{platformOrderId}
GET /venue/orders/{externalOrderId}
```

Order Snapshot 核心字段：

```json
{
  "source": "fake",
  "externalOrderId": "FAKE-platform-order-id",
  "platformOrderId": "platform-order-id",
  "commandId": "trade-command-id",
  "accountId": "account_sim_usdt",
  "instrumentId": "instrument_btc_usdt",
  "symbol": "BTCUSDT",
  "side": "buy",
  "orderType": "limit",
  "quantity": "1",
  "price": "100",
  "status": "filled",
  "filledQuantity": "1",
  "averageFillPrice": "100",
  "occurredAt": "2026-07-23T12:00:00+00:00",
  "asOf": "2026-07-23T12:00:01+00:00",
  "dataQualityState": "complete"
}
```

### 7.2 Fill、Position、Balance

```http
GET /venue/fills?accountId=...&externalOrderId=...&platformOrderId=...
GET /venue/positions?accountId=...
GET /venue/balances?accountId=...
```

每个 Snapshot 必须返回 `source`、外部身份、Account、Instrument（适用时）、时间和数据质量。

### 7.3 Cancel

```http
POST /venue/orders/{externalOrderId}/cancel
```

```json
{
  "idempotencyKey": "cancel-001",
  "reason": "risk action"
}
```

响应状态：

- `canceled`
- `already_final`
- `not_found`
- `unsupported`
- `unknown`

相同幂等键不同载荷返回 409。`already_final` 不等同于新取消成功。

## 8. Venue Order Reconciliation

```http
POST /api/v1/trading/orders/{orderId}/venue-reconcile
```

流程：

1. 对 `result_unknown` 先调用 Journal Reconcile。
2. 查询 External Order by Platform Order ID。
3. 查询 External Fills。
4. 导入 `external_order` 和 `trade_fill` FinancialFact。
5. External Fill ID 作为本地 Fill Event ID。
6. 同步 Order 与 TradeCommand。
7. 创建状态或数量 Difference。

响应：

```json
{
  "orderId": "...",
  "commandId": "...",
  "source": "fake",
  "externalOrderId": "FAKE-...",
  "statusBefore": "result_unknown",
  "statusAfter": "filled",
  "recovered": true,
  "importedFactIds": ["..."],
  "differenceIds": [],
  "reconciledAt": "2026-07-23T12:00:02+00:00"
}
```

该接口不得调用 Runtime `POST /commands/orders`。

## 9. Account Venue Reconciliation

```http
POST /api/v1/ops/venue-reconciliation/runs
GET  /api/v1/ops/venue-reconciliation/runs/{runId}
GET  /api/v1/ops/venue-reconciliation/runs/{runId}/differences
```

请求：

```json
{
  "idempotencyKey": "reconciliation-run-001",
  "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
  "accountId": "account_sim_usdt",
  "actor": "operations"
}
```

系统查询 Position 与 Balance，将其写入不可变 FinancialFact，并与本地 Formal/兼容投影比较。

Run 返回：

- source
- status
- Order / Fill / Position / Balance Count
- Fact Count
- Difference Count
- startedAt / completedAt

相同幂等键不同请求载荷返回 409。

## 10. Reconciliation Difference

```http
POST /api/v1/ops/venue-reconciliation/differences/{differenceId}/resolve
```

请求：

```json
{
  "status": "accepted",
  "actor": "risk-officer",
  "reason": "expected bootstrap difference"
}
```

Difference Type：

- `missing_local`
- `missing_external`
- `quantity_mismatch`
- `price_mismatch`
- `currency_mismatch`
- `status_mismatch`

Difference Status：`open`、`resolved`、`accepted`。首次处置后重复调用返回原结果，不覆盖第一处置记录。

## 11. FinancialFact

```http
POST /api/v1/financial-facts
GET  /api/v1/financial-facts
```

支持：`external_order`、`trade_fill`、`deal`、`funding`、`swap`、`fee`、`balance`、`position`、`fx`。

规则：

- 客户端幂等键和外部身份双重去重。
- 身份相同载荷不同返回 409。
- Trade Fact 的 Currency、Quantity Unit、Contract Multiplier 来自 Catalog。
- 非基础币种缺少 FX 时标记 incomplete。
- Stablecoin 不自动等同 USD。
- 不提供修改或删除事实的业务 API。

## 12. Formal Position、PnL 与 NAV

```http
POST /api/v1/strategies/instances/{strategyInstanceId}/financials/rebuild
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-positions
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-pnl
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots/run?valuationTime=...
```

- Position/PnL 可以从 FinancialFact 完整重建。
- PnL 分为 Trading、Funding、Swap、Fee、FX 和 Total。
- NAV 对全部 active binding 使用同一 valuationTime。
- 缺失账户和 FX 不补零。

## 13. Audit 与运维

```http
GET /api/v1/ops/reconciliation-summary
GET /api/v1/ops/audit-events
GET /api/v1/security/trading-safety
GET /api/v1/security/credential-references
GET /api/v1/security/exchange-connectivity
GET /api/v1/security/exchange-venue-readiness
```

Phase 4B 新增审计事件：

- `venue_order_reconciled`
- `venue_reconciliation_completed`
- `reconciliation_difference_resolved`

## 14. 通用规则

- JSON 金融数值使用十进制字符串。
- 时间使用带时区 ISO 8601。
- Query 与 Command 分离。
- `result_unknown` 与失败不同。
- Batch Status 与 Risk Status 不同。
- 缺失值与零不同。
- 外部与本地冲突必须形成 Difference。
- 当前只允许 Simulation / Fake Gateway；Bybit Demo、MT5 Demo 和 Live 均未获批。