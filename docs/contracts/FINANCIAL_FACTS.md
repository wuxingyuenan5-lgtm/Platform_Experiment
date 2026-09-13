# Financial Facts and Formal Accounting Contract

状态：`active contract`

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
- `positions`、`pnl_results` 和 `strategy_nav_snapshots` 保留为运营兼容投影，不作为正式核对口径扩展。

## 2. 当前正式口径

- FinancialFact 是不可变事实；正式 Position、PnL 与 NAV 是可重建投影。
- 外部订单、成交、Funding、Swap、Fee、Balance、Position 与 FX 事实使用稳定外部身份和内容哈希去重。
- 正式投影只能从 FinancialFact 重放，不能读取 Operational projection 作为计算输入。
- 缺失必要 FX 或账户余额时保留可确认事实并显式标记 `partial` / `incomplete`，不得伪造 1:1 汇率或零权益。
- 重建必须保留全部事实、按确定顺序重放并写入 AuditEvent；同一事实集合应产生稳定结果。
- 当前正式账务可用于内部核对，但外部账单签名、生产数据导入与真实资金验收仍由生产门禁保护。

## 2. 事实身份与幂等

每条事实同时具备两套身份：

1. 客户端 `idempotencyKey`。
2. 外部身份：`source + externalId + factType + strategyInstanceId`。

服务端保存规范化载荷的 SHA-256 内容哈希：

- 身份相同且内容一致：返回原事实。
- 身份相同但内容不同：返回 `409 Conflict`。
- 不提供修改和删除事实的业务 API。

该规则用于防止网络重试、账单重复导入和 Runtime 事件重放造成重复记账。

### Bybit Funding 结算归属

账户原生快照先持久化不可变 Venue 事件，再由 Platform API 的 Funding 账务服务核对并写入 FinancialFact；读取页面不写账，Runtime 不决定策略归属。

- 只处理完整历史范围内的 Bybit linear 原生资金费。金额、币种和结算时刻取真实回执，不用预估费率计算金额。
- 原生交易的成交后持仓与带方向成交量可证明成交前或成交后为零；该零点之前的已知逻辑持仓组也必须归零，不能把不同组相互抵消的账户净零当成新起点。
- 从该零点到结算的每笔原生交易必须匹配实际成交 ID、订单、命令及指令批次；逐笔数量、方向、时间和原生持仓变化均须一致。历史品种别名沿既有原生身份映射解析。
- 仅剩一个 Funding 持仓组且其净数量等于结算数量时，写入带 `batchId`、`instructionId`、原生结算及数量证据的 funding 事实。指定原开仓指令的平仓仍归回原组。多组、未归属成交、缺失历史或同毫秒顺序不明时保留未归属事件，不按账户、当前仓位或比例分摊。
- 稳定幂等键包含账户、来源和原生事件身份；相同事实并发写入串行核对，只创建一条事实及入库审计。事实提交后投影中断时，重复读取触发的相同入账重试会完成投影重建。
- 资金费是独立损益分项；其他币种费用缺少 FX 不隐藏已确认的基础币种资金费，但相关费用与净损益仍保留缺失状态。

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

当前合同建立平台内部事实与正式核对口径。外部 Provider、账单、账户、生产数据导入和真实资金状态仍需独立环境证据；缺少这些证据时，PnL/NAV 只能证明仓库内计算与重建语义，不能证明真实资金 Live 就绪。
