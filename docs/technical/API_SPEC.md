# Platform V6 API Specification

状态：`active`  
API Prefix：`/api/v1`  
组合入口：`platform-backend/app/main.py`  
原有业务路由：`platform-backend/app/application.py`  
Phase 3 路由：`platform-backend/app/financial_facts.py`  
当前阶段：`docs/planning/V6-Phase3-金融事实与正式账务.md`

## 1. 本地服务

| 服务 | 地址 | 权威职责 |
|---|---|---|
| Platform Backend | `http://127.0.0.1:8000` | Strategy、Account、Command、Order、FinancialFact、Formal Position/PnL/NAV 权威 |
| Execution Runtime | `http://127.0.0.1:8100` | Gateway、Runtime Journal、外部执行隔离 |
| Frontend | `http://127.0.0.1:5173` | 查询、交互和命令发起 |

健康检查：

```http
GET /health
GET /api/v1/system/info
GET /api/v1/system/runtime-readiness
```

## 2. Catalog 查询

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

交易前端和金融事实入口必须从这些接口获取 StrategyInstance、StrategyAccountBinding、Account、Instrument 和 ContractSpecification，不得硬编码正式 ID，不得由前端覆盖后端合约乘数和单位。

## 3. 正式单腿写入口

```http
POST /api/v1/trading/commands
```

最小请求：

```json
{
  "idempotencyKey": "client-generated-unique-key",
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

服务端校验：

- StrategyInstance 存在、active，且对应策略属于 V1 closed-loop。
- Account 与 StrategyInstance 存在 active binding。
- Account active。
- Instrument 和 ContractSpecification 存在。
- 数量、数量步长、价格步长和 Live 门禁通过。
- `idempotencyKey` 重复且载荷一致时返回已有 TradeCommand。
- 相同 `idempotencyKey` 携带不同业务载荷时返回 `409 Conflict`。

查询：

```http
GET /api/v1/trading/commands/{tradeCommandId}
```

## 4. 正式双腿写入口

```http
POST /api/v1/trading/execution-batches
```

最小请求：

```json
{
  "idempotencyKey": "funding-batch-unique-key",
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

语义：

- `idempotencyKey` 与 `strategyInstanceId` 必填。
- `strategyKey` 必须与 StrategyInstance 一致。
- 所有 Leg 在第一条腿执行前完成 Catalog 预校验。
- 每条 Leg 创建独立 TradeCommand。
- Leg 幂等键为 `<batch-idempotency-key>:<role>`。
- 重复且载荷一致的请求返回已有 Batch。
- 相同 Batch 幂等键对应不同载荷时返回 `409 Conflict`。

查询：

```http
GET /api/v1/trading/execution-batches
GET /api/v1/trading/execution-batches/{batchId}
```

## 5. 订单、成交和恢复

```http
GET  /api/v1/trading/orders
GET  /api/v1/trading/orders/{orderId}
GET  /api/v1/trading/fills
POST /api/v1/trading/orders/{orderId}/reconcile
```

恢复语义：

1. 只对 `result_unknown` 执行恢复。
2. 通过 Runtime `GET /commands/{commandId}/events` 查询已持久化事件。
3. 不重新提交原订单。
4. 校验 Runtime event 的 `command_id` 和 `platform_order_id`。
5. Runtime 无事件或不可用时继续保持 `result_unknown`。
6. Fill event 按 `event_id` 去重；首次插入成功后才更新 Phase 2 投影。
7. 恢复完成后同步 Order 与 TradeCommand 状态。

当前只支持 Runtime Journal 恢复。外部交易所／MT5 主动查单、成交和持仓恢复尚未实现。

## 6. Deprecated 兼容入口

```http
POST /api/v1/trading/orders
```

该接口仅为旧测试和兼容调用保留：

- 新前端和新业务逻辑不得调用。
- 它不提供业务级 `strategyInstanceId` 和客户端幂等键。
- 后续版本应转为内部接口或删除。

## 7. Phase 2 工程兼容查询

```http
GET  /api/v1/accounts/{accountId}/balances/latest
GET  /api/v1/accounts/{accountId}/positions
GET  /api/v1/accounts/{accountId}/positions/{instrumentId}
GET  /api/v1/accounts/{accountId}/pnl/{instrumentId}
GET  /api/v1/strategies/instances/{strategyInstanceId}/pnl
GET  /api/v1/strategies/instances/{strategyInstanceId}/nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/nav-snapshots/run
```

这些端点继续用于 Phase 2 工程兼容，不得标记为正式投资账务。内部金融核对使用下面的 FinancialFact 与 `formal-*` 接口。

## 8. 不可变 FinancialFact

### 8.1 写入事实

```http
POST /api/v1/financial-facts
```

Trade Fill 示例：

```json
{
  "idempotencyKey": "bybit-fill-123",
  "factType": "trade_fill",
  "source": "bybit-demo",
  "externalId": "123",
  "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
  "accountId": "account_sim_usdt",
  "instrumentId": "instrument_btc_usdt",
  "side": "buy",
  "quantity": "0.01",
  "price": "65000",
  "occurredAt": "2026-07-23T08:00:00+00:00",
  "payload": {}
}
```

Balance 示例：

```json
{
  "idempotencyKey": "balance-20260723-0800",
  "factType": "balance",
  "source": "simulation-ledger",
  "externalId": "balance-20260723-0800",
  "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
  "accountId": "account_sim_usdt",
  "amount": "100000",
  "availableBalance": "90000",
  "currency": "USDT",
  "occurredAt": "2026-07-23T08:00:00+00:00"
}
```

支持的 `factType`：

- `external_order`
- `trade_fill`
- `deal`
- `funding`
- `swap`
- `fee`
- `balance`
- `position`
- `fx`

事实规则：

- `idempotencyKey` 必填。
- 外部身份为 `source + externalId + factType + strategyInstanceId`。
- 重复且规范化载荷一致时返回原事实。
- 身份相同但载荷不同返回 `409 Conflict`。
- 不提供事实修改或删除 API。
- Trade Fact 的结算币种、Quantity Unit 和 Contract Multiplier 由 Instrument Catalog 确定。
- 非基础币种 Monetary Fact 必须提供 `fxRateToBase`；缺失时事实保留但状态为 `incomplete`。
- Stablecoin 不自动等同 USD。

### 8.2 查询事实

```http
GET /api/v1/financial-facts
GET /api/v1/financial-facts?strategyInstanceId=...
GET /api/v1/financial-facts?strategyInstanceId=...&factType=funding
```

## 9. Formal Position 与 PnL

```http
POST /api/v1/strategies/instances/{strategyInstanceId}/financials/rebuild
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-positions
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-pnl
```

规则：

- Formal Position 和 PnL 只由 FinancialFact 生成。
- `financials/rebuild` 清空投影后从不可变事实完整重放。
- 重建不修改或删除任何事实。
- Trading PnL 使用成交数量、成交价、仓位方向、Contract Multiplier 和必要 FX。
- PnL 分项返回 `tradingPnl`、`fundingPnl`、`swapPnl`、`feePnl`、`fxPnl` 和 `totalPnl`。
- 缺失必要 FX 时保留可确认金额，但整体 `dataQualityState=incomplete`。

## 10. Formal NAV

```http
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots/run?valuationTime=...
```

规则：

- `valuationTime` 使用带时区 ISO 8601。
- 所有 active binding 账户使用同一估值时点。
- 每个账户取 `occurredAt <= valuationTime` 的最新 Balance Fact。
- 返回 `requiredAccountCount`、`includedAccountCount` 和 `missingAccountIds`。
- 全部账户齐全为 `complete`；部分齐全为 `partial`；全部缺失为 `incomplete`。
- 没有任何有效余额时，`equity` 和 `nav` 返回空值，不伪装为零。

## 11. 运维、安全和对账

```http
GET /api/v1/security/trading-safety
GET /api/v1/security/credential-references
GET /api/v1/security/exchange-connectivity
GET /api/v1/security/exchange-venue-readiness
GET /api/v1/ops/reconciliation-summary
GET /api/v1/ops/audit-events
```

FinancialFact 入库、Formal 投影重建和 Formal NAV 创建都会写入 AuditEvent。

## 12. Runtime 内部接口

```http
GET  http://127.0.0.1:8100/health
GET  http://127.0.0.1:8100/status
POST http://127.0.0.1:8100/commands/orders
GET  http://127.0.0.1:8100/commands/{commandId}/events
```

Runtime 规则：

- 在调用 Gateway 前通过数据库原子抢占 `command_id`。
- 重复 command 返回已持久化事件。
- 已被抢占但尚无事件时返回 409，不重复调用 Gateway。

## 13. 通用数据规则

- JSON 金融数值使用十进制字符串传递。
- 时间使用带时区 ISO 8601。
- `result_unknown` 与失败不同。
- 缺失值与零不同。
- Currency、Quantity Unit、Contract Multiplier 和 FX 必须显式。
- API 返回的 Account、Instrument 和 Strategy ID 作为正式调用依据。
- Live 默认关闭，当前版本只允许 Simulation / Fake Gateway。