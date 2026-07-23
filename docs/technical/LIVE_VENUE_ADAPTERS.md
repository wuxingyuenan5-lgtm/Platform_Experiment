# Controlled Live Venue Adapters

状态：`active / engineering acceptance pending`  
适用阶段：`Platform V6 / Phase 4C`  
实施计划：`../planning/V6-Phase4C-受控实盘适配器.md`

## 1. 设计原则

- Live Query 与 Live Command 分离。
- 查询失败不等于零仓位或零余额。
- 同步 ACK 不等于最终成交。
- 明确拒绝与结果未知必须区分。
- 所有外部副作用必须位于 Platform 幂等、Kill Switch、Runtime 幂等和 Live Gate 之后。
- 凭证、密码、API Secret 不进入数据库响应、日志或审计 JSON。

## 2. Runtime 模块

| 模块 | 职责 |
|---|---|
| `bybit_live_adapter.py` | Bybit V5 实盘 Query、受控 Submit/Cancel、Funding/Fee 映射 |
| `mt5_live_adapter.py` | MT5 Terminal Query、受控 order_check/order_send、Swap/Fee 映射 |
| `bybit_mt5_gateway.py` | 根据 Account 确定性选择适配器 |
| `live_safety.py` | Environment、双重写开关、allowlist、单笔限额校验 |
| `live_route_store.py` | 外部 client identity、Order Route、日累计名义金额幂等认领 |
| `secret_resolver.py` | 从 `secret://...` 映射的环境变量读取凭证 |

## 3. Bybit 映射

### 外部身份

```text
Platform Order ID
→ SHA-256 派生 orderLinkId
→ Bybit orderId
→ Execution execId
```

- `orderLinkId` 不超过 Bybit 限制并保持确定性。
- place-order 返回后只生成 `order_acknowledged`。
- 最终状态通过 Open Orders、Order History、Executions 或后续 WebSocket 确认。
- Execution `execId` 用作 Fill 与 FinancialFact 的自然身份。

### Query

- `get_open_orders`
- `get_order_history`
- `get_executions`
- `get_positions`
- `get_wallet_balance`
- `get_transaction_log`

Funding 和 Fee 分别映射为带符号经济贡献。Fee 以负值写入。

## 4. MT5 映射

### 外部身份

```text
Platform Order ID
→ SHA-256 派生 Comment
+ 固定 Magic Number
→ Order Ticket
→ Deal Ticket
→ Position Ticket
```

- 下单前执行 `order_check`。
- 写入使用 `order_send`。
- Order 查询使用 `orders_get` 与 `history_orders_get`。
- Deal 查询使用 `history_deals_get`。
- Position 与账户查询使用 `positions_get`、`account_info`。
- Deal Ticket 用作 Fill、Swap、Commission/Fee 的自然身份。

MT5 非 Windows、Terminal 未连接、登录账号不匹配或交易权限不足时必须 fail-closed。

## 5. Live Safety Gate

Runtime 配置：

```text
VG_RUNTIME_ENVIRONMENT=live
VG_RUNTIME_LIVE_WRITE_ENABLED=false
VG_RUNTIME_LIVE_ACCOUNT_ALLOWLIST=...
VG_RUNTIME_LIVE_STRATEGY_ALLOWLIST=...
VG_RUNTIME_LIVE_SYMBOL_ALLOWLIST=...
VG_RUNTIME_LIVE_MAX_ORDER_NOTIONAL=...
VG_RUNTIME_LIVE_MAX_DAILY_NOTIONAL=...
```

写命令校验顺序：

1. Runtime Environment 必须是 live。
2. Runtime Live Write 必须显式开启。
3. Account、StrategyInstance 和 Symbol 位于 allowlist。
4. 取得正数 Reference Price。
5. 单笔 Notional 不超限。
6. 在 SQLite `BEGIN IMMEDIATE` 事务中原子认领 Command 与日累计 Notional。
7. 重复 Command 载荷一致时复用认领；载荷冲突拒绝。
8. 通过后才调用 Venue API。

Platform 原有 `liveTradingEnabled` 与 Kill Switch 仍然必须先通过；Runtime Gate 是第二道独立防线。

## 6. 凭证

### Bybit

Credential Ref 示例：`secret://bybit-live-001`

对应环境变量：

```text
VG_SECRET_BYBIT_LIVE_001_API_KEY
VG_SECRET_BYBIT_LIVE_001_SECRET
```

### MT5

Credential Ref 示例：`secret://mt5-live-001`

对应环境变量：

```text
VG_SECRET_MT5_LIVE_001_LOGIN
VG_SECRET_MT5_LIVE_001_PASSWORD
VG_SECRET_MT5_LIVE_001_SERVER
```

`/gateway/capabilities` 仅返回字段是否齐全、适配器能力和缺失要求，不返回任何值。

## 7. Account 与 Instrument 路由

配置示例：

```text
VG_RUNTIME_BYBIT_ACCOUNT_IDS=account_bybit_live
VG_RUNTIME_MT5_ACCOUNT_IDS=account_mt5_live
VG_RUNTIME_BYBIT_INSTRUMENT_MAP=XAUTUSDT=instrument_xaut_usdt
VG_RUNTIME_MT5_INSTRUMENT_MAP=XAUUSD+=instrument_xauusd_mt5
```

约束：

- 一个 Account 只能属于一个 Adapter。
- 未映射 Account 拒绝查询和写入。
- 未映射 Symbol 的 Position、Deal 或 Economic Event 不进入 complete 事实。
- Instrument ID 必须与 Backend Catalog 一致。

## 8. Result Unknown

以下情况视为 `result_unknown`，不能视为拒绝：

- HTTP/Terminal 调用期间异常，无法证明请求未到 Venue。
- Bybit 返回成功但缺少 orderId。
- MT5 order_send 返回空结果或缺少 Order/Deal Ticket。
- 查询接口自身结果不确定。

Runtime 返回 502，Platform 保留 Order 并标记 `result_unknown`，随后调用 Phase 4B Venue Reconcile。禁止以相同业务意图重新创建另一笔订单。

## 9. Economic Event

Runtime：

```http
GET /venue/economic-events?accountId=...&instrumentId=...&eventType=...
```

Platform：

```http
POST /api/v1/ops/live-economic-events/import
```

支持 `funding`、`swap`、`fee`。导入操作本身和每条 FinancialFact 都具有独立幂等身份。

## 10. 验收边界

CI 只能证明：

- Provider 字段映射。
- 路由、门禁、限额与幂等。
- 凭证不进入响应。
- Economic Event 可以进入 FinancialFact。
- 既有 Backend、Runtime 和 Frontend 回归不受破坏。

CI 不能证明真实 Broker 权限、交易品种、最小手数、订单模式和外部稳定性。真实账户运营验收必须独立记录，且默认使用最小允许仓位。