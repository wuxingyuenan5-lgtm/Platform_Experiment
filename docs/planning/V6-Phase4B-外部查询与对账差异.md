# V6 Phase 4B：外部查询、事实导入与对账差异

状态：`completed / merge pending`  
实施分支：`hardening/v6-phase4b-venue-reconciliation`  
跟踪 Issue：`#16 V6 Phase 4B：外部 Venue 查询、事实导入与对账差异`  
Pull Request：`#17 Implement V6 Phase 4B venue reconciliation`  
上级计划：Issue `#12`、`V6-交易安全加固实施计划.md`  
最终验收：`Platform CI #228 / run 30005369314`  
更新时间：`2026-07-23`

## 1. 阶段目标

Phase 4B 在不接真实 Bybit/MT5 凭证的前提下，建立通用外部状态查询、不可变事实导入和差异留痕：

```text
Platform Order / result_unknown
→ Runtime Journal 快速恢复
→ Venue 主动查询
→ External Order / Fill / Position / Balance Snapshot
→ FinancialFact
→ Formal Position / PnL / NAV
→ Reconciliation Difference
```

当前发布边界仍为 Simulation / Fake Gateway。Bybit Demo 和 MT5 Demo 属于 Phase 4C。

## 2. Runtime 查询契约

ExecutionGateway 新增：

- `get_order`
- `list_fills`
- `list_positions`
- `list_balances`
- `cancel_order`

Runtime API：

```http
GET  /venue/orders/by-platform/{platformOrderId}
GET  /venue/orders/{externalOrderId}
GET  /venue/fills
GET  /venue/positions
GET  /venue/balances
POST /venue/orders/{externalOrderId}/cancel
```

所有快照包含：

- `source`
- 外部身份
- Platform 身份（适用时）
- Account / Instrument
- `occurredAt` 或 `asOf`
- `dataQualityState`

查询操作不得产生新订单副作用。

## 3. Persistent Fake Venue

Fake Gateway 不再只返回瞬时随机事件，而是将外部状态保存到 Runtime Journal 同一 SQLite：

- `fake_venue_orders`
- `fake_venue_fills`
- `fake_venue_positions`
- `fake_venue_balances`
- `fake_venue_cancel_commands`

外部 ID 由 Platform Order ID 确定性派生：

```text
FAKE-{platformOrderId}
FAKE-FILL-{platformOrderId}
```

重复 Command、重复查询和 Runtime TestClient 重启不会产生第二套外部事实。

Fake Cancel 使用独立幂等键；同一幂等键不同载荷返回 409。已经 filled、rejected 或 canceled 的订单返回 `already_final`，不得伪装成新取消成功。

## 4. result_unknown 外部恢复

正式入口：

```http
POST /api/v1/trading/orders/{orderId}/venue-reconcile
```

顺序：

1. 如果本地仍为 `result_unknown`，先查询 Runtime Journal。
2. Journal 未恢复时，通过 Platform Order ID 查询外部 Order。
3. 查询外部 Fill。
4. External Order 写入 `external_order` FinancialFact。
5. 每个 Fill 写入 `trade_fill` FinancialFact。
6. Fill 使用稳定 External Fill ID 作为事件 ID，重放不重复更新本地 Fill 和投影。
7. 同步 Platform Order 与 TradeCommand 状态。
8. 对仍不一致的状态和数量创建 Reconciliation Difference。

整个流程只查询和导入，不重新提交原订单。

## 5. Account Snapshot Reconciliation

入口：

```http
POST /api/v1/ops/venue-reconciliation/runs
GET  /api/v1/ops/venue-reconciliation/runs/{runId}
GET  /api/v1/ops/venue-reconciliation/runs/{runId}/differences
```

请求必须提供：

- `idempotencyKey`
- `strategyInstanceId`
- `accountId`
- `actor`

系统校验 Account 与 StrategyInstance 的 active binding，然后查询 Position 与 Balance Snapshot。

导入规则：

- Position Snapshot → `position` FinancialFact。
- Balance Snapshot → `balance` FinancialFact。
- External Snapshot Identity 与 `asOf` 共同组成不可变事实身份。
- 重复 Run 幂等返回原结果，不重复写入事实。

## 6. Reconciliation Difference

差异对象不直接覆盖本地或外部状态，而是保存：

- Run ID
- Difference Key
- Difference Type
- Entity Type
- Local / External Reference
- Local / External Value JSON
- `open / resolved / accepted`
- Resolution Actor / Reason / Time

当前类型：

- `missing_local`
- `missing_external`
- `quantity_mismatch`
- `price_mismatch`
- `currency_mismatch`
- `status_mismatch`

处置入口：

```http
POST /api/v1/ops/venue-reconciliation/differences/{differenceId}/resolve
```

首次处置后不可由后续重复请求无痕改写。

## 7. FinancialFact 关系

Phase 4B 复用 Phase 3 不可变事实层：

- External Order Snapshot 使用 `source + externalOrderId + asOf`。
- Fill 使用稳定 External Fill ID。
- Position 使用 External Position ID + asOf。
- Balance 使用 External Balance ID。

同一身份不同载荷仍返回 409。差异不能通过修改 FinancialFact 消失，只能通过新增事实、重建投影和显式 Difference Resolution 关闭。

## 8. 审计事件

新增：

- `venue_order_reconciled`
- `venue_reconciliation_completed`
- `reconciliation_difference_resolved`

审计记录包含来源、外部身份、导入 Fact ID、Difference ID、操作人和结果。

## 9. 金样本

1. TradeCommand 因 Runtime timeout 进入 `result_unknown`。
2. Runtime Journal 返回 404。
3. Venue Order 查询返回 filled，并返回一个 External Fill。
4. Reconcile 后 Order 与 TradeCommand 进入 filled。
5. 相同 reconcile 再执行，Fill 总数和 FinancialFact 总数不增加。
6. Formal Position 由 External Fill 形成。
7. Account Snapshot Run 导入 Position 与 Balance。
8. 外部 Position 在本地不存在时生成 `missing_local`。
9. Difference 首次 accepted 后，后续重复 resolve 不覆盖原处置。
10. Reconciliation idempotencyKey 不同载荷返回 409。
11. Fake Venue 状态跨 Runtime TestClient 重启仍可查询。
12. filled Fake Order 的 cancel 返回 `already_final`，重复取消幂等。

## 10. 验收记录

最终验收：`Platform CI #228 / run 30005369314`

| 检查 | 结果 |
|---|---|
| Platform Backend Phase 4 strict Ruff Gate | 通过 |
| Platform Backend 全量 Ruff 与 Pytest | 通过，49 项测试 |
| Execution Runtime strict Ruff、全量 Ruff 与 Pytest | 通过 |
| Frontend frozen install、type-check、production build | 通过 |
| result_unknown Journal + Venue 两级恢复 | 通过 |
| External Fill 重放与 FinancialFact 导入幂等 | 通过 |
| Formal Position 由 External Fill 形成 | 通过 |
| Position / Balance Snapshot 导入 | 通过 |
| Reconciliation Difference 创建与首次处置固定 | 通过 |
| Fake Venue 持久化与取消幂等 | 通过 |
| README、START-HERE、API Spec、技术设计、Release Gate、Changelog | 已同步 |

## 11. 明确延期

Phase 4B 不完成：

- Bybit Demo API 下单、撤单与查询。
- MT5 Demo Order／Deal、持仓、余额和 Swap 查询。
- Demo 凭证实际验证。
- 日终定时调度、连续运行和全账户零未解释差异验收。
- Live 发布审批、认证、RBAC、双人审批和生产密钥托管。

以上进入 Phase 4C–4D。