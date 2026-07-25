# Venue Query and Reconciliation

状态：`active`  
适用版本：`Platform V6 / Phase 4B–4C`  
实施计划：`../planning/V6-Phase4B-外部查询与对账差异.md`  
当前扩展：`Issue #96 / PR #97`

## 1. 权威边界

```text
Execution Runtime
= 外部 Venue 查询、受控撤单和执行适配边界

Platform Backend
= Platform Order、FinancialFact、Formal Accounting、Difference 权威
```

Runtime 返回外部事实快照，不直接修改 Platform Backend 数据库。Backend 负责验证 Platform 身份、导入不可变事实、更新本地投影并创建差异。

## 2. 查询不等于命令

以下 Runtime API 是只读查询：

```http
GET /venue/orders?accountId=...&symbol=...&limit=50
GET /venue/orders/by-platform/{platformOrderId}
GET /venue/orders/{externalOrderId}
GET /venue/fills
GET /venue/positions
GET /venue/balances
GET /venue/instruments/{symbol}?accountId=...
```

它们不得：

- 重发订单。
- 自动撤单。
- 修改外部仓位。
- 生成新的 External Fill。

Cancel Order 是单独命令，必须有幂等键：

```http
POST /venue/orders/{externalOrderId}/cancel
```

## 3. Route Store 不是读取前提

Runtime `live_order_routes` 保存 Platform Order、Command、Account、Instrument、External Client ID 和 External Order ID 的映射。该 Store 用于提高数据质量与确定 Adapter，但不能作为读取真实订单的唯一来源。

### 3.1 有 Route

- Platform Order ID 可确定性定位 Adapter 和 Venue Order。
- Snapshot 使用真实 Platform Order ID 与 Command ID。
- `dataQualityState=complete`。

### 3.2 无 Route

以下订单仍必须可读：

- Runtime 启动前已经存在的订单。
- 人工或其他受控工具创建的订单。
- Runtime 重启或 Route Store 丢失后的订单。

无 Route 时：

- Bybit 直接按 `orderId` 或 bounded Active/History list 查询。
- MT5 按 Order Ticket 或 Deal Ticket 查询并恢复关联 Order Ticket。
- Snapshot 使用 `external:{source}:{externalOrderId}` 合成 Platform／Command Identity。
- `dataQualityState=external_only`。
- External-only Snapshot 可以用于发现与对账，但不得伪装为已完成 Platform 映射。

## 4. MT5 Ticket 语义

```text
Order Ticket = 订单身份
Deal Ticket = 成交事件身份
Position Ticket = 当前持仓身份
```

规则：

- `history_orders_get(ticket=...)` 查询 Order Ticket。
- `history_deals_get(ticket=...)` 可查询 Deal Ticket；Deal 的 `order` 字段用于恢复 Order Ticket。
- Deal Ticket 用作 Fill ID。
- Position Ticket 用于 reduce-only close。
- Order／Deal Ticket 不得作为 Position Ticket 下发。

## 5. Snapshot 身份

### Order Snapshot

Order 状态可能变化，因此导入 FinancialFact 时使用：

```text
source + externalOrderId + asOf
```

保留每个状态时点，而不是改写原 External Order Fact。

### Fill Snapshot

Fill 是自然不可变事件：

```text
source + externalFillId
```

External Fill ID 同时用于本地 Fill Event ID，保证账务事实和执行事件重放具有同一去重边界。

### Position Snapshot

Position 是时点快照：

```text
source + externalPositionId + asOf
```

Position Fact 当前用于外部仓位对账，不直接替代由 Trade Fill 重建的 Formal Position。

### Balance Snapshot

Balance 使用 Venue 提供的 Snapshot ID；没有天然 ID 的适配器必须由 Account、Currency、asOf 确定性生成。

### Instrument Specification Snapshot

规格是时点事实：

```text
source + accountId + symbol + asOf
```

实盘写入使用当前规格；数据库 Seed 仅用于 Catalog、Simulation 和历史参考，不能替代当前 Venue 规格。

## 6. Fake Venue 持久化

Fake Gateway 使用 Runtime Journal SQLite 保存外部视角状态。它用于：

- Linux CI。
- Runtime 重启演练。
- Query API 契约测试。
- FinancialFact 重复导入测试。
- Reconciliation Difference 金样本。

Fake Store 不是正式交易账本，也不进入 Platform Backend 权威数据库。

## 7. result_unknown 恢复顺序

```text
Platform Order = result_unknown
→ 查询 Runtime Journal
→ 若仍未知，查询 Venue Order by Platform Order ID
→ 若 Route 缺失，按 External Order ID 或 bounded order list 查 Venue
→ 查询 External Fills / MT5 Deals
→ 导入 External Order / Trade Fill Facts
→ 应用稳定 Fill Event
→ 同步 Order / TradeCommand
→ 比较状态与数量
→ 创建 Difference
```

严禁在该流程内调用 `POST /commands/orders`。

跨所价差额外规则：

- MT5 definitive failure 才允许一次幂等 Bybit reduce-only rollback。
- MT5 `accepted`、`processing`、`acknowledged` 或 `result_unknown` 禁止自动 rollback。
- 外部 Position 未核对前不得把生命周期标记为 healthy／closed。

## 8. Difference 模型

Difference 表示“两个权威视角暂时不一致”，不是一个可以随意覆盖的临时错误字符串。

每个 Difference 保存：

- 稳定 Difference Key。
- 类型与 Entity Type。
- Local / External Reference。
- Local / External Value JSON。
- 状态。
- 处置人、原因和时间。

处置状态：

- `open`：待核实。
- `resolved`：通过补事实、修复投影或外部处置解决。
- `accepted`：确认差异合理，保留为已解释差异。

已处置 Difference 的后续重复请求返回原结果，不无痕改写第一处置记录。

## 9. 差异类型

| 类型 | 解释 |
|---|---|
| `missing_local` | 外部存在，本地缺少对应实体或投影 |
| `missing_external` | 本地存在，外部查询不到 |
| `quantity_mismatch` | 成交量、持仓量或权益数值不一致 |
| `price_mismatch` | 成交价或平均价不一致 |
| `currency_mismatch` | Currency 不一致 |
| `status_mismatch` | Order 状态不一致 |
| `identity_mismatch` | Order／Deal／Position Ticket 或 Platform Route 不一致 |
| `specification_mismatch` | Platform 参考规格与当前 Venue 规格不一致 |

Phase 4D 将继续加入差异严重度、责任人、SLA 和日终汇总。

## 10. 幂等规则

| 操作 | 幂等身份 |
|---|---|
| Runtime Order submit | command_id |
| Runtime Cancel | idempotencyKey |
| Cross-spread rollback | `cross-spread-rollback:{openBatchId}:bybit` |
| Order venue reconcile | External Order / Fill identities |
| Account reconciliation run | idempotencyKey + payload hash |
| FinancialFact import | FinancialFact dual identity |
| Difference create | run_id + difference_key |
| Difference resolve | 首次非 open 状态固定 |

## 11. 数据质量

- Snapshot 缺少外部身份、时间、Account 或 Instrument 时不得导入 complete Fact。
- Query 404 与 Runtime 不可用不同。
- 空 Position/Balance 列表表示查询成功但无结果；网络错误表示查询失败。
- 外部状态与本地不一致时创建 Difference，不选择任一方静默覆盖。
- Stablecoin 与法币不自动等价。
- `external_only` 是可解释的发现状态，不等于 complete Platform identity。
- External-only Order 在补齐 Route 前不得自动关联到任意本地 Order。
- 当前规格不可用、过期或无效时，实盘命令必须 fail-closed。

## 12. 当前限制

- Bybit Market Fill 仍使用 bounded synchronous REST polling，不是最终 private WebSocket 架构。
- Live order list 是 bounded read surface，不是完整历史数据仓库。
- Backend Account Snapshot Run 当前按调用触发，尚无日终调度器。
- Position Snapshot 只用于对账和实盘生命周期验证，不成为 Formal Position 的计算来源。
- Difference 尚未完整接入严重度、负责人和 SLA。
- 1 oz、单活动生命周期和 Market-only 属于临时验收限制；解除条件见 `../operations/V6-小资金实盘验收手册.md`。
- Platform 与 Runtime Live Write、自动 Exit Monitor 仍默认关闭。
