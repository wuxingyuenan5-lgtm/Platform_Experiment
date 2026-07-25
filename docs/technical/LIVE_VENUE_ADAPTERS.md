# Controlled Live Venue Adapters

状态：`active / engineering acceptance pending`  
适用阶段：`Platform V6 / Phase 4C`  
实施计划：`../planning/V6-Phase4C-受控实盘适配器.md`  
当前工程：`Issue #96 / PR #97`

## 1. 设计原则

- Live Query 与 Live Command 分离。
- 查询失败不等于零仓位或零余额。
- 同步 ACK 不等于最终成交。
- 明确拒绝与结果未知必须区分。
- Route Store 用于补充 Platform 身份，不得成为读取真实订单的前提。
- MT5 Order Ticket、Deal Ticket 和 Position Ticket 是不同身份，不得互相替代。
- 实盘数量必须由 Venue 当前规格证明，不以数据库 Seed 作为写入依据。
- 所有外部副作用必须位于 Platform 幂等、Kill Switch、Runtime 幂等和 Live Gate 之后。
- 凭证、密码、API Secret 不进入数据库响应、日志或审计 JSON。

## 2. Runtime 模块

| 模块 | 职责 |
|---|---|
| `bybit_live_adapter.py` | Bybit V5 基础 Query、受控 Submit/Cancel、Funding/Fee 映射 |
| `bybit_fill_confirming_adapter.py` | Market 提交、reduce-only close、bounded terminal-fill confirmation |
| `bybit_acceptance_adapter.py` | 无 Route Order／Fill 读取、bounded order list、实时规格和 API Key readiness |
| `mt5_live_adapter.py` | MT5 Terminal 基础 Query、受控 order_check/order_send、Swap/Fee 映射 |
| `mt5_position_closing_adapter.py` | Position Ticket 绑定的 reduce-only close |
| `mt5_acceptance_adapter.py` | 无 Route Order／Deal 读取、Order/Deal Ticket 纠错、实时 Symbol/Terminal 规格 |
| `strict_live_acceptance_adapters.py` | Runtime 独立的 1 oz 上限、实时 step／contract size／权限校验和单仓限制 |
| `bybit_mt5_gateway.py` | 根据 Account 确定性选择适配器，并提供跨 Adapter 只读查询 |
| `live_safety.py` | Environment、双重写开关、allowlist、单笔限额校验 |
| `live_route_store.py` | 外部 client identity、Order Route、日累计名义金额幂等认领 |
| `secret_resolver.py` | 从 `secret://...` 映射的环境变量读取凭证 |

## 3. Bybit 映射

### 3.1 外部身份

```text
Platform Order ID
→ SHA-256 派生 orderLinkId
→ Bybit orderId
→ Execution execId
```

- `orderLinkId` 不超过 Bybit 限制并保持确定性。
- place-order 返回后先生成 `order_acknowledged`。
- Market Order 通过 bounded polling 等待 terminal state。
- Execution `execId` 用作 Fill 与 FinancialFact 的自然身份。
- Route 缺失时仍可按 `orderId` 读取；结果标记 `external_only` 并使用合成 Platform Identity。

### 3.2 Query

- `get_open_orders`
- `get_order_history`
- `get_executions`
- `get_positions`
- `get_wallet_balance`
- `get_transaction_log`
- `get_instruments_info`
- `get_api_key_information`

Funding 和 Fee 分别映射为带符号经济贡献。Fee 以负值写入。

### 3.3 Market Fill 规则

```text
place_order ACK
→ Active Order / Order History polling
→ terminal Filled
   or terminal Canceled with confirmed partial fill
→ emit order_filled(actual quantity)
```

- `New` 或非终态 `PartiallyFilled` 到达超时后保持 unresolved，不提交 MT5。
- 终态部分成交只对冲实际成交量。
- 终态无成交取消或拒绝才属于 definitive failure。

## 4. MT5 映射

### 4.1 外部身份

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
- 市价成交若 `order_send` 主要返回 Deal Ticket，读取层必须通过 Deal 的 `order` 字段恢复 Order Ticket。
- Close 必须使用真实 Position Ticket；Deal Ticket 或 Order Ticket 不能充当 Position Ticket。

MT5 非 Windows、Terminal 未连接、登录账号不匹配或交易权限不足时必须 fail-closed。

### 4.2 实时规格

Runtime 读取：

- `volume_min`
- `volume_step`
- `volume_max`
- `trade_contract_size`
- `trade_mode`
- `filling_mode`
- `account_info.login`
- Account `trade_allowed`
- Terminal `trade_allowed`

MT5 Command 数量单位是 Lot。Runtime 必须先计算：

```text
requestedOunces = requestedLots × trade_contract_size
```

再应用临时 1 oz 上限。不能把 `1 lot` 误认为 `1 oz`。

## 5. Route-independent Order Query

Runtime 提供：

```http
GET /venue/orders?accountId=...&symbol=...&limit=50
GET /venue/orders/by-platform/{platformOrderId}
GET /venue/orders/{externalOrderId}
GET /venue/fills?accountId=...&externalOrderId=...&platformOrderId=...
```

读取顺序：

1. 有 Platform Order ID 时优先使用 Route Store 确定 Adapter 和外部身份。
2. 有 External Order ID 且 Route 存在时使用对应 Adapter。
3. Route 不存在时直接查询 Venue：
   - 非纯数字 ID 优先 Bybit；
   - 纯数字 Ticket 查询 MT5；
   - Account-specific list 始终由 Account Route 确定 Adapter。
4. 无 Route 的结果标记 `dataQualityState=external_only`。
5. 查询不得创建、撤销或重发订单。

## 6. Instrument Specification Query

```http
GET /venue/instruments/{symbol}?accountId=...
```

返回：

- `minQuantity`
- `quantityStep`
- `maxMarketQuantity`
- `contractSize`
- `trade_mode`
- `filling_mode`
- `accessChecks`
- `asOf`

Platform 跨所价差写入前必须分别查询 Bybit 与 MT5；任一查询失败、规格无效或权限不满足时拒绝开仓。

## 7. 临时 1 盎司 Acceptance Gate

Runtime 配置：

```text
VG_RUNTIME_LIVE_ACCEPTANCE_MAX_ORDER_QUANTITY=1
VG_RUNTIME_LIVE_ACCEPTANCE_MAX_POSITIONS_PER_SYMBOL=1
```

该 Gate 不授权写入，只在已有 Live Write 授权之后继续收紧：

### Bybit

- Command Quantity 必须不超过 1 oz。
- Quantity 必须满足当前 `minOrderQty` 和 `qtyStep`。
- Symbol 必须处于 Trading／Available。
- API Key 不能是 read-only。
- API Key 必须绑定固定 IP。
- ContractTrade 必须包含 Order 与 Position 权限。
- 非 reduce-only Open 前目标 Symbol 不得已有活动仓位。

### MT5

- `lots × contractSize` 必须不超过 1 oz。
- Lot 必须满足当前 `volume_min`、`volume_step` 和 `volume_max`。
- Account Login 必须与配置一致。
- Account 与 Terminal 均必须允许交易。
- 非 reduce-only Open 前目标 Symbol 不得已有活动仓位。
- Bybit 终态部分成交可生成小于 1 oz 的 MT5 对冲，只要数量精确满足 MT5 当前规格。

## 8. Live Safety Gate

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
8. 通过临时 Acceptance Gate 的数量、权限、规格与持仓校验。
9. 通过后才调用 Venue API。

Platform 原有 `liveTradingEnabled` 与 Kill Switch 仍然必须先通过；Runtime Gate 是第二道独立防线。

## 9. 凭证

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

`/gateway/capabilities` 和 Instrument Specification 只返回字段是否齐全、权限布尔值、适配器能力和缺失要求，不返回任何凭证值。

## 10. Account 与 Instrument 路由

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
- Route Store 丢失不阻止 External Order 只读查询，但会降低为 `external_only`。

## 11. Result Unknown

以下情况视为 `result_unknown`，不能视为拒绝：

- HTTP/Terminal 调用期间异常，无法证明请求未到 Venue。
- Bybit 返回成功但缺少 orderId。
- MT5 `order_send` 返回空结果或缺少 Order/Deal Ticket。
- 查询接口自身结果不确定。
- Bybit Market Order 在 bounded confirmation deadline 内仍处于 New／PartiallyFilled。

Runtime 返回 502，Platform 保留 Order 并标记 `result_unknown`，随后调用 Venue Reconcile。禁止以相同业务意图重新创建另一笔订单。

对于跨所价差：

- MT5 definitive rejection／failure 才允许一次幂等 Bybit reduce-only rollback。
- MT5 `accepted`、`processing`、`acknowledged` 或 `result_unknown` 禁止自动 rollback。

## 12. Economic Event

Runtime：

```http
GET /venue/economic-events?accountId=...&instrumentId=...&eventType=...
```

Platform：

```http
POST /api/v1/ops/live-economic-events/import
```

支持 `funding`、`swap`、`fee`。导入操作本身和每条 FinancialFact 都具有独立幂等身份。

## 13. 验收边界

CI 可以证明：

- Route-independent Order／Fill 映射。
- MT5 Order／Deal Ticket 纠错。
- 当前规格模型和权限布尔值映射。
- 1 oz Runtime 独立数量限制。
- Bybit 终态部分成交的精确 MT5 对冲边界。
- definitive failure 与 result_unknown 的不同处置。
- 路由、门禁、限额与幂等。
- 凭证不进入响应。
- 既有 Backend、Runtime 和 Frontend 回归不受破坏。

CI 不能证明：

- 真实 Bybit API Key 权限和 IP 白名单生效。
- 真实 Broker 的 `trade_contract_size`、最小手数和 filling mode。
- Windows MT5 Terminal 长时间稳定性。
- 实盘网络中断、滑点、部分成交和外部账单一致性。
- 真实 TP／SL exactly-once close。

真实账户运营验收必须按 `../operations/V6-小资金实盘验收手册.md` 独立记录。

## 14. 临时限制解除

1 oz、单活动仓位、Market-only 和自动监控关闭属于临时运营限制。只有 Issue #39 形成重复真实验收证据后，才允许通过独立 Issue／PR 逐项放宽；禁止直接修改环境变量绕过复审。ACK／Fill 区分、result_unknown 禁止盲重试、双重写门禁、Position Ticket close 和凭证隔离属于永久安全原则，不随放量删除。
