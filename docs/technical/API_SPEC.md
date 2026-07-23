# Platform V6 API Specification

状态：`active`  
API Prefix：`/api/v1`  
组合入口：`platform-backend/app/main.py`  
业务路由：`platform-backend/app/application.py`  
正式账务路由：`platform-backend/app/financial_facts.py`  
执行风险路由：`platform-backend/app/execution_risk.py`  
当前阶段：`docs/planning/V6-Phase4A-执行风险与Kill-Switch.md`

## 1. 本地服务

| 服务 | 地址 | 权威职责 |
|---|---|---|
| Platform Backend | `http://127.0.0.1:8000` | Strategy、Account、Command、Order、Execution Risk、FinancialFact、Formal Position/PnL/NAV |
| Execution Runtime | `http://127.0.0.1:8100` | Gateway、Runtime Journal、外部执行隔离 |
| Frontend | `http://127.0.0.1:5173` | 查询、交互和命令发起 |

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

前端、TradeCommand、ExecutionBatch、RiskAction 和 FinancialFact 必须使用 Backend Catalog。客户端不得覆盖 Quantity Unit、Settlement Currency 和 Contract Multiplier。

## 3. 正式单腿写入口

```http
POST /api/v1/trading/commands
GET  /api/v1/trading/commands/{tradeCommandId}
```

请求示例：

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

服务端校验：

- StrategyInstance active 且属于 closed-loop。
- Account active 且存在 active StrategyAccountBinding。
- Instrument 与 ContractSpecification 存在。
- 数量、数量步长和价格步长合法。
- Live 门禁通过。
- 重复幂等键同载荷返回原 Command。
- 重复幂等键不同载荷返回 `409 Conflict`。

## 4. 正式双腿写入口

```http
POST /api/v1/trading/execution-batches
GET  /api/v1/trading/execution-batches
GET  /api/v1/trading/execution-batches/{batchId}
```

请求示例：

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

执行顺序：

1. 校验 Strategy、Account Binding、Account、Instrument、ContractSpecification。
2. 检查 Global、Strategy、全部 Account Kill Switch。
3. 原子认领 ExecutionBatch。
4. 快照 ExecutionRiskPolicy。
5. 每条 Leg 创建独立 TradeCommand，幂等键为 `<batch-key>:<role>`。
6. 第一腿成交后记录 firstFillAt 和残留敞口。
7. 第二腿前再次检查 Kill Switch、最大腿间延迟和残留敞口阈值。
8. 两腿完成后只有 Risk Status 为 `clear` 才标记 `hedged`。

相同 Batch 幂等键不同载荷返回 409。

## 5. Kill Switch

### 5.1 查询

```http
GET /api/v1/risk/kill-switches/{scopeType}/{scopeId}
```

作用域：

| scopeType | scopeId |
|---|---|
| `global` | `*` |
| `strategy` | StrategyInstance ID |
| `account` | Account ID |

未配置时返回安全默认状态：`enabled=false`、`version=0`、`actor=system-default`。

### 5.2 修改

```http
PUT /api/v1/risk/kill-switches/{scopeType}/{scopeId}
```

```json
{
  "idempotencyKey": "kill-global-on-001",
  "enabled": true,
  "reason": "incident drill",
  "actor": "risk-officer"
}
```

语义：

- 写操作幂等。
- 相同幂等键不同载荷返回 409。
- 每次实际变化增加 `version`。
- 命中 Kill Switch 的新 Batch 返回 `423 Locked`。
- 开关变化写入 AuditEvent。
- Kill Switch 阻止新增风险，不删除历史订单、成交和事实。

## 6. ExecutionRiskPolicy

```http
GET /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
PUT /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
```

请求示例：

```json
{
  "idempotencyKey": "risk-policy-001",
  "maxLegDelaySeconds": 10,
  "maxResidualNotional": "50000",
  "failureAction": "auto_flatten",
  "actor": "risk-officer"
}
```

支持的 `failureAction`：

- `hold_and_escalate`
- `auto_flatten`

默认策略：

```json
{
  "maxLegDelaySeconds": 10,
  "maxResidualNotional": "100000",
  "failureAction": "hold_and_escalate",
  "source": "default"
}
```

Batch 创建时固化策略快照。后续策略修改不改变历史 Batch。

## 7. ExecutionBatch Risk

```http
GET /api/v1/trading/execution-batches/{batchId}/risk
```

核心响应字段：

```json
{
  "batchId": "...",
  "strategyInstanceId": "...",
  "maxLegDelaySeconds": 10,
  "maxResidualNotional": "50000",
  "failureAction": "auto_flatten",
  "riskStatus": "residual_exposure",
  "residualExposureNotional": "100",
  "residualCurrency": "USDT",
  "dataQualityState": "complete",
  "firstFillAt": "2026-07-23T10:00:01+00:00",
  "lastLegAt": "2026-07-23T10:00:01+00:00",
  "riskReason": "..."
}
```

`riskStatus`：

- `clear`
- `residual_exposure`
- `disposition_in_progress`
- `resolved`
- `escalated`

残留敞口：

```text
Fill Quantity × Fill Price × Contract Multiplier
```

同一 Settlement Currency 按买入正、卖出负净额计算。多币种没有风险 FX 快照时返回 `MIXED / incomplete` 和保守绝对值合计。

## 8. ExecutionRiskAction

```http
GET  /api/v1/trading/execution-batches/{batchId}/risk-actions
POST /api/v1/trading/execution-batches/{batchId}/risk-actions
```

### 8.1 人工升级

```json
{
  "idempotencyKey": "risk-hold-001",
  "action": "hold_and_escalate",
  "actor": "risk-officer",
  "reason": "retain exposure for controlled investigation"
}
```

### 8.2 反向平仓

```json
{
  "idempotencyKey": "risk-flatten-001",
  "action": "flatten_filled_legs",
  "actor": "risk-officer",
  "reason": "remove residual exposure"
}
```

对每个已成交原始 Leg 生成反向 Market TradeCommand。Leg 命令幂等键为 `<risk-action-key>:<leg-role>`。

### 8.3 本地取消未提交腿

```json
{
  "idempotencyKey": "risk-cancel-001",
  "action": "cancel_open_legs",
  "actor": "risk-officer"
}
```

仅能确认取消尚未形成外部 Order 的 pending/submitting Leg。已有 accepted／processing／result_unknown Order 在外部撤单能力完成前返回 `action_required`。

### 8.4 替代对冲

```json
{
  "idempotencyKey": "risk-substitute-001",
  "action": "substitute_hedge",
  "actor": "risk-officer",
  "replacementAccountId": "account_sim_usdt",
  "replacementInstrumentId": "instrument_btc_usdt_perp",
  "replacementSymbol": "BTCUSDT-PERP",
  "replacementSide": "sell",
  "replacementQuantity": "0.01"
}
```

替代 Leg 必须完整，并经过 TradeCommand 全部安全校验。

所有 RiskAction：

- 必须提供幂等键和操作人。
- 同一幂等键不同载荷返回 409。
- 返回生成的 Platform Order ID。
- 写入 AuditEvent。
- 只有风险降低命令全部 filled 才能标记 resolved。

## 9. 订单、成交和恢复

```http
GET  /api/v1/trading/orders
GET  /api/v1/trading/orders/{orderId}
GET  /api/v1/trading/fills
POST /api/v1/trading/orders/{orderId}/reconcile
```

当前恢复流程：

1. 只处理 `result_unknown`。
2. 查询 Runtime Journal。
3. 不重新提交原订单。
4. 校验 command_id 和 platform_order_id。
5. Fill event 去重后更新投影。
6. Runtime 无事件时保持未知。

外部 Venue 主动查单、撤单和恢复仍属于 Phase 4B／4C。

## 10. Deprecated 兼容入口

```http
POST /api/v1/trading/orders
```

只为旧测试和兼容调用保留。新前端、新业务和风险动作不得调用。

## 11. Phase 2 工程兼容查询

```http
GET  /api/v1/accounts/{accountId}/balances/latest
GET  /api/v1/accounts/{accountId}/positions
GET  /api/v1/accounts/{accountId}/positions/{instrumentId}
GET  /api/v1/accounts/{accountId}/pnl/{instrumentId}
GET  /api/v1/strategies/instances/{strategyInstanceId}/pnl
GET  /api/v1/strategies/instances/{strategyInstanceId}/nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/nav-snapshots/run
```

这些端点不是正式投资账务口径。

## 12. 不可变 FinancialFact

```http
POST /api/v1/financial-facts
GET  /api/v1/financial-facts
```

支持：`external_order`、`trade_fill`、`deal`、`funding`、`swap`、`fee`、`balance`、`position`、`fx`。

规则：

- 客户端幂等键和外部身份双重去重。
- 身份相同载荷不同返回 409。
- Trade Fact 的结算币种、Quantity Unit 和 Contract Multiplier 来自 Catalog。
- 非基础币种缺少 `fxRateToBase` 时保留事实但标记 incomplete。
- Stablecoin 不自动等同 USD。
- 不提供事实修改或删除业务 API。

## 13. Formal Position、PnL 与 NAV

```http
POST /api/v1/strategies/instances/{strategyInstanceId}/financials/rebuild
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-positions
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-pnl
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots/run?valuationTime=...
```

- Position/PnL 可以从 FinancialFact 完整重建。
- PnL 分为 Trading、Funding、Swap、Fee、FX 和 Total。
- Trading PnL 使用 Contract Multiplier 和必要 FX。
- NAV 对全部 active binding 账户使用同一 valuationTime。
- 返回账户覆盖数和 missingAccountIds。
- 缺失事实不补零。

## 14. 运维、安全和审计

```http
GET /api/v1/security/trading-safety
GET /api/v1/security/credential-references
GET /api/v1/security/exchange-connectivity
GET /api/v1/security/exchange-venue-readiness
GET /api/v1/ops/reconciliation-summary
GET /api/v1/ops/audit-events
```

AuditEvent 当前覆盖 Command、恢复、FinancialFact、投影重建、Formal NAV、Kill Switch、风险策略、风险状态和 RiskAction。

## 15. Runtime 内部接口

```http
GET  http://127.0.0.1:8100/health
GET  http://127.0.0.1:8100/status
POST http://127.0.0.1:8100/commands/orders
GET  http://127.0.0.1:8100/commands/{commandId}/events
```

Runtime 在 Gateway 副作用前原子抢占 command。重复 command 返回持久化事件；已认领但尚无事件时返回 409。

## 16. 通用数据规则

- JSON 金融数值使用十进制字符串。
- 时间使用带时区 ISO 8601。
- `result_unknown` 与失败不同。
- Batch 业务状态与 Risk 状态不同。
- 缺失值与零不同。
- Currency、Quantity Unit、Contract Multiplier 和 FX 必须显式。
- API 返回的 Account、Instrument 和 Strategy ID 作为正式调用依据。
- 当前只允许 Simulation / Fake Gateway；Demo 和 Live 均未获批。