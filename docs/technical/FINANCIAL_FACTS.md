# Financial Facts and Formal Accounting

状态：`active`  
适用版本：`Platform V6 / Phase 3`  
实施计划：`../planning/V6-Phase3-金融事实与正式账务.md`

## 1. 权威边界

```text
External venue / imported statement
→ immutable FinancialFact
→ rebuildable formal Position / PnL
→ point-in-time formal NAV
```

- `financial_facts` 是外部金融事实的不可变入口。
- `formal_positions`、`formal_pnl_results`、`formal_strategy_nav_snapshots` 是可删除、可重建的投影。
- 投影不得反向修改事实。
- Phase 2 的 `positions`、`pnl_results` 和 `strategy_nav_snapshots` 暂时保留为工程兼容口径，不再作为正式核对口径扩展。

## 2. 事实身份与幂等

每条事实同时具备两套身份：

1. 客户端 `idempotencyKey`。
2. 外部身份：`source + externalId + factType + strategyInstanceId`。

服务端保存规范化载荷的 SHA-256 内容哈希：

- 身份相同且内容一致：返回原事实。
- 身份相同但内容不同：返回 `409 Conflict`。
- 不提供修改和删除事实的业务 API。

该规则用于防止网络重试、账单重复导入和 Runtime 事件重放造成重复记账。

## 3. 事实类型

| factType | 核心字段 | 当前投影用途 |
|---|---|---|
| `external_order` | Account、Instrument、外部订单身份 | 审计与后续对账预留 |
| `trade_fill` / `deal` | Side、Quantity、Price | Position、Trading PnL |
| `funding` | Amount、Currency | Funding PnL |
| `swap` | Amount、Currency | Swap PnL |
| `fee` | 带符号 Amount、Currency | Fee PnL |
| `fx` | 带符号 Amount、Currency | FX PnL |
| `balance` | Equity Amount、Currency、Available Balance | Formal NAV |
| `position` | Account、Instrument、外部仓位信息 | 后续外部仓位对账预留 |

## 4. 金融数值规则

- 金额、价格、数量、合约乘数和汇率以十进制字符串通过 API 传输。
- Trade Fact 的 `quantityUnit`、结算币种和 `contractMultiplier` 由后端 Instrument Catalog 快照确定，不接受前端覆盖。
- Monetary Fact 的 `amount` 是带符号经济贡献；费用通常传负数。
- 非策略基础币种必须提供 `fxRateToBase`。
- 缺失 FX 时事实仍然保留，但 `dataQualityState=incomplete`，不能静默按 1:1 换算。
- Stablecoin 不自动等同 USD 或其他法币。
- 缺失值与零具有不同业务含义。

## 5. 重放顺序

同一 StrategyInstance / Account / Instrument 按以下顺序重放：

```text
occurred_at → created_at → fact id
```

Position 与 Trading PnL 必须使用同一成交事实序列，避免不同排序产生不同成本价和已实现损益。

## 6. Formal Position

Trade Fill / Deal 使用带符号数量更新仓位：

- 同方向增加：按名义金额加权更新平均价。
- 反方向减少：按平仓数量确认已实现损益。
- 完全平仓：平均价清空。
- 反向开仓：剩余仓位以新成交价作为平均价。

投影保存 StrategyInstance、Account、Instrument、Net Quantity、Average Price、Quantity Unit、质量状态和更新时间。

## 7. Formal PnL

Trading PnL 计算边界：

```text
closing quantity
× (exit price - entry average price)
× position direction
× contract multiplier
× FX rate to strategy base currency
```

正式结果分项保存：

- `tradingPnl`
- `fundingPnl`
- `swapPnl`
- `feePnl`
- `fxPnl`
- `totalPnl`

任一必要 FX 缺失时，能够确认的分项继续保留，但整个 Account / Instrument 投影标记为 `incomplete`。

## 8. Formal NAV 时间语义

调用方必须明确 `valuationTime`。系统对每个 active StrategyAccountBinding：

1. 仅查询 `occurredAt <= valuationTime` 的 Balance Fact。
2. 取该账户在估值时点之前最新一条。
3. 按事实中的 FX 快照转换到策略基础币种。
4. 汇总全部可用账户。

响应必须包含：

- `requiredAccountCount`
- `includedAccountCount`
- `missingAccountIds`
- `dataQualityState`

状态定义：

- `complete`：所有 active binding 账户都有可用余额。
- `partial`：至少一个账户有余额，但覆盖不完整。
- `incomplete`：没有任何账户可以形成有效权益。

没有可用余额时，`equity` 和 `nav` 返回空值，不返回伪造的零。

## 9. 重建与审计

`POST /strategies/instances/{id}/financials/rebuild`：

- 删除指定 StrategyInstance 的 Formal Position / PnL 投影。
- 保留全部 FinancialFact。
- 按权威顺序完整重放。
- 写入重建 AuditEvent。

FinancialFact 入库和 Formal NAV 创建也必须写入 AuditEvent。

## 10. 当前限制

Phase 3 仅建立平台内部事实与核对口径，尚未完成：

- Bybit / MT5 主动查单、查成交、查仓位和自动导入。
- 外部账单文件解析器及账单签名验证。
- 双腿残留敞口自动处置和 Kill Switch。
- 正式用户认证、RBAC、双人审批和生产密钥托管。

因此 Phase 3 完成只代表 PnL/NAV 可以用于内部核对，不代表系统可以进入真实资金 Live。