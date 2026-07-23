# 人工阅读入口

状态：`active`  
产品基线：Platform V6  
架构版本：Platform V6 Simplified  
适用分支：`main`  
当前状态：Phase 3 已完成；Phase 4 待实施  
文档层级：人工阅读入口

找文档先看项目根目录 `00-人工可读目录/README.md`。  
继续工程实施先看：

1. `../../docs/planning/V6-交易安全加固实施计划.md`
2. `../../docs/planning/V6-Phase3-金融事实与正式账务.md`
3. `../../docs/technical/FINANCIAL_FACTS.md`
4. `quality/release-gate.md`

## 1. 当前一句话结论

```text
Phase 1：交易输入 fail-closed + Runtime command 原子抢占，已完成
+
Phase 2：TradeCommand 正式入口 + result_unknown 恢复 + 动态 Catalog，已完成
+
Phase 3：不可变事实 + 可重建 Position/PnL + 统一估值 NAV，已完成
+
Phase 4：双腿风险处置、Bybit Demo、MT5 Demo 和日终对账，尚未开始
```

当前系统仍只允许 Simulation / Fake Gateway。Phase 3 完成只代表 PnL/NAV 可以用于内部核对，不代表可以进入 Paper、Demo 或 Live。

## 2. 先读这 12 篇

1. `../../docs/planning/V6-交易安全加固实施计划.md`
2. `../../docs/planning/V6-Phase3-金融事实与正式账务.md`
3. `../../docs/technical/FINANCIAL_FACTS.md`
4. `../../docs/technical/API_SPEC.md`
5. `../../docs/planning/V6-Phase2-命令入口与结果恢复.md`
6. `modules/一级模块定位总表.md`
7. `modules/策略-需求文档.md`
8. `modules/交易平台-需求文档.md`
9. `modules/策略管理-需求文档.md`
10. `architecture/platform-target-architecture.md`
11. `architecture/domain/domain-overview.md`
12. `planning/V1-开发路线图.md`

## 3. 当前工程优先级

| 顺序 | 主题 | 状态 |
|---|---|---|
| 1 | Fail-closed、Runtime 幂等、CI、文档留痕 | 已完成 |
| 2 | TradeCommand、ExecutionBatch 幂等、`result_unknown` 恢复、动态 Catalog | 已完成 |
| 3 | 不可变事实、ContractSpecification、正式 PnL 与统一估值 NAV | 已完成 |
| 4 | 残腿处置、Bybit Demo、MT5 Demo、日终对账 | 待实施 |
| 5 | 新策略和新功能扩展 | 暂缓 |

## 4. 当前正式交易入口

单腿：

```http
POST /api/v1/trading/commands
```

双腿：

```http
POST /api/v1/trading/execution-batches
```

结果未知恢复：

```http
POST /api/v1/trading/orders/{orderId}/reconcile
```

`POST /api/v1/trading/orders` 仅为 deprecated 兼容入口，新代码不得继续使用。

## 5. Phase 3 正式核对入口

不可变事实：

```http
POST /api/v1/financial-facts
GET  /api/v1/financial-facts
```

重建与查询：

```http
POST /api/v1/strategies/instances/{strategyInstanceId}/financials/rebuild
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-positions
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-pnl
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots/run
```

旧 `/pnl` 与 `/nav-snapshots` 仍是工程兼容口径；内部金融核对必须使用 `formal-*`。

## 6. 命令与恢复底线

- TradeCommand 必须有 `idempotencyKey`。
- ExecutionBatch 必须有 `idempotencyKey` 与 `strategyInstanceId`。
- 每条 Batch Leg 必须通过独立 TradeCommand。
- StrategyInstance 必须 active 且属于 V1 closed-loop。
- Account 必须 active 且与 StrategyInstance 存在 active binding。
- Instrument 和 ContractSpecification 必须存在。
- Runtime event 的 command_id 和 platform_order_id 必须与本地记录一致。
- 相同 Fill event 重放不得重复改变 Phase 2 投影。
- `result_unknown` 只能查询恢复，不得重新下单。
- Runtime 没有事件时必须继续保持未知。

## 7. FinancialFact 与账务底线

- FinancialFact 只新增，不提供更新和删除业务 API。
- 客户端幂等键和外部事实身份都必须去重。
- 相同身份不同载荷必须返回 409。
- Quantity Unit、Settlement Currency 和 Contract Multiplier 来自后端 Catalog。
- Stablecoin 不自动等同 USD。
- 非基础币种缺失 FX 时标记 incomplete，不按 1:1 换算。
- Formal Position 与 PnL 必须能从事实清空后重建。
- PnL 分项保存 Trading、Funding、Swap、Fee、FX 和 Total。
- Formal NAV 对全部 active binding 账户使用同一 valuationTime。
- 账户缺失必须返回 missingAccountIds，不能静默补零。

## 8. 前端 Catalog 与产品界面规则

交易页面不得硬编码正式账户、策略实例和 Instrument UUID。资费套利面板必须从 Backend 获取：

- StrategyInstance。
- StrategyAccountBinding。
- Account。
- Instrument。
- ContractSpecification。

如果当前资产没有完整 Catalog，按钮必须禁用并显示缺失原因。缺失持仓、PnL、行情和账务事实显示 `—` 或未知，不能显示伪造的零。

产品页面只展示完成业务任务需要的信息、操作和状态。开发说明、实现解释、跳转机制和联调备注进入 Markdown，不放在正式页面主要视觉层。

## 9. 策略模块 V1 口径

| 策略 | V1 定位 | 当前要求 |
|---|---|---|
| 资费套利 | 完整闭环 | 行情、命令、订单、成交、FinancialFact、Funding／费用、Formal PnL、统一时点 NAV |
| 跨所价差 | 完整闭环 | Crypto 腿、MT5 腿、Order／Deal、FinancialFact、Swap／费用、Formal PnL、NAV |
| 海内外价差 | 分析／模拟／预留 | 不做正式汇率损益、CTP 和完整四层 PnL |
| 抄底 | 管理入口 + 占位 | 暂不做完整 Signal、TradeCycle 和订单自动归属 |
| 短线交易员 L/W | 管理入口 + 占位 | 暂不做完整违规记录、风险额度和正式归因 |

金融AI分析暂缓研发。

## 10. V1 最小对象

当前优先对象：

- StrategyDefinition / StrategyVersion / StrategyInstance。
- StrategyAccountBinding / Account。
- Instrument / ContractSpecification。
- TradeCommand / ExecutionBatch / Order / Fill / Deal。
- FinancialFact。
- Formal Position / Formal PnL / Formal Strategy NAV Snapshot。
- AuditEvent。

Phase 2 的 Position、PnLResult 和 StrategyNavSnapshot 暂时保留为兼容投影，不继续作为正式口径扩展。

暂缓 Investor、ShareClass、申赎、正式 Fund NAV、完整 Finance Ledger、CTP 和金融AI后端。

## 11. 审视当前版本时必须问

- 所有业务下单是否经过 TradeCommand？
- 重复命令、事实和事件是否真正幂等？
- `result_unknown` 是否只恢复而不重下？
- 账户、标的、单位和合约乘数是否来自 Catalog？
- Formal PnL 是否使用合约乘数、币种、单位、Funding、Swap、Fee 和 FX？
- Formal Position/PnL 是否能从不可变事实重建？
- NAV 是否按同一估值时点汇总全部 active binding 账户？
- 缺失账户和汇率是否明确标记，而不是补零？
- 单腿失败后是否有自动处置和 Kill Switch？
- Bybit/MT5 是否真正跑过 Demo，而非只存在接口壳？

当前前八项属于 Phase 1–3 验收；最后两项仍属于 Phase 4。

## 12. 文档与目录治理

- 当前不要大规模移动运行目录。
- 每个阶段必须有 Issue、分支、PR、实施计划、技术设计、CI 记录和回滚说明。
- 代码变化同步更新 API Spec、Release Gate、README、START-HERE 和 Changelog。
- DRAFT 和历史文件最后再分批归档，不能在业务口径未稳定时大规模移动。