# Platform V6 API Specification

状态：`active`  
API Prefix：`/api/v1`  
当前实现：`platform-backend/app/main.py`  
当前阶段：`docs/planning/V6-Phase2-命令入口与结果恢复.md`

## 1. 本地服务

| 服务 | 地址 | 权威职责 |
|---|---|---|
| Platform Backend | `http://127.0.0.1:8000` | Strategy、Account、Command、Order、Fill、Position、PnL 权威 |
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

交易前端必须从这些接口获取 StrategyInstance、StrategyAccountBinding、Account、Instrument 和 ContractSpecification，不得硬编码正式 ID。

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
- `idempotencyKey` 唯一；重复请求返回已有 TradeCommand，不创建第二个外部订单。

响应核心字段：

```json
{
  "tradeCommandId": "...",
  "idempotencyKey": "...",
  "strategyInstanceId": "...",
  "accountId": "...",
  "instrumentId": "...",
  "platformOrderId": "...",
  "status": "filled"
}
```

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
- 重复 Batch 请求返回已有 Batch，不生成新的 Command、Order 或 Runtime 调用。

查询：

```http
GET /api/v1/trading/execution-batches
GET /api/v1/trading/execution-batches/{batchId}
```

## 5. 订单、成交和恢复

查询：

```http
GET /api/v1/trading/orders
GET /api/v1/trading/orders/{orderId}
GET /api/v1/trading/fills
```

恢复未知结果：

```http
POST /api/v1/trading/orders/{orderId}/reconcile
```

恢复语义：

1. 只对 `result_unknown` 执行恢复。
2. 通过 Runtime `GET /commands/{commandId}/events` 查询已持久化事件。
3. 不重新提交原订单。
4. 校验 Runtime event 的 `command_id` 和 `platform_order_id`。
5. Runtime 无事件或不可用时继续返回 `result_unknown`。
6. Fill event 按 `event_id` 去重；只有首次插入成功才更新 Position、EconomicEvent 和 PnL。
7. 恢复完成后同步 Order 与 TradeCommand 状态。

当前只支持 Runtime Journal 恢复。外部交易所／MT5 主动查单、成交和持仓恢复尚未实现。

## 6. Deprecated 兼容入口

```http
POST /api/v1/trading/orders
```

该接口在 OpenAPI 中标记为 deprecated，仅为旧测试和兼容调用保留：

- 新前端和新业务逻辑不得调用。
- 它不提供业务级 `strategyInstanceId` 和客户端幂等键。
- 后续版本应转为内部接口或删除。

## 7. 账户、持仓和 PnL 查询

```http
GET /api/v1/accounts/{accountId}/balances/latest
GET /api/v1/accounts/{accountId}/positions
GET /api/v1/accounts/{accountId}/positions/{instrumentId}
GET /api/v1/accounts/{accountId}/pnl/{instrumentId}
GET /api/v1/strategies/instances/{strategyInstanceId}/pnl
GET /api/v1/strategies/instances/{strategyInstanceId}/nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/nav-snapshots/run
```

限制：当前 PnL/NAV 尚未完整纳入 Contract Multiplier、Funding、Swap、Fee、FX、Currency／Unit 和统一估值时间，只能用于工程演示。

## 8. 运维、安全和对账

```http
GET /api/v1/security/trading-safety
GET /api/v1/security/credential-references
GET /api/v1/security/exchange-connectivity
GET /api/v1/security/exchange-venue-readiness
GET /api/v1/ops/reconciliation-summary
GET /api/v1/ops/audit-events
```

## 9. Runtime 内部接口

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

## 10. 通用数据规则

- JSON 金融数值使用十进制字符串传递。
- 时间使用带时区 ISO 8601。
- `result_unknown` 与失败不同。
- 缺失值与零不同。
- API 返回的 Account、Instrument 和 Strategy ID 作为正式调用依据。
- Live 默认关闭，当前版本只允许 Simulation / Fake Gateway。
