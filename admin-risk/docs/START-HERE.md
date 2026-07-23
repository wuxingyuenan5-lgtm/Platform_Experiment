# 人工阅读入口

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6 Simplified  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：人工阅读入口

如果你是为了“找文档”，先打开项目最外层的 `00-人工可读目录/README.md`。  
如果你是为了“快速理解当前 V1 结论”，继续读本文。

## 1. 当前一句话结论

当前第一阶段不是重做全部平台，而是先把策略模块做实：

```text
资费套利完整闭环
+
跨所价差完整闭环
+
策略管理承接资金、持仓、订单、费用、PnL 和固定时间净值
```

海内外价差、抄底、短线交易员 L、短线交易员 W 第一阶段先保留入口、字段和占位状态。金融AI分析暂缓研发。

## 2. 先读这 8 篇

按顺序阅读：

1. `modules/一级模块定位总表.md`
2. `modules/策略-需求文档.md`
3. `modules/交易平台-需求文档.md`
4. `modules/策略管理-需求文档.md`
5. `architecture/platform-target-architecture.md`
6. `architecture/domain/domain-overview.md`
7. `architecture/reference-code-adoption-matrix.md`
8. `planning/V1-开发路线图.md`

读完这 8 篇，基本能理解当前产品边界、V1 做什么、暂缓什么、参考代码怎么吸收、开发顺序怎么排。

## 3. 策略模块 V1 口径

| 策略 | V1 定位 | 当前要求 |
|---|---|---|
| 资费套利 | 完整闭环 | 行情、交易准备、模拟执行、订单成交、持仓、Funding／费用、PnL、固定时间净值 |
| 跨所价差 | 完整闭环 | Crypto 腿、MT5 腿、Order／Deal 映射、持仓、Swap／费用、PnL、固定时间净值 |
| 海内外价差 | 分析／模拟／预留 | 不做正式汇率损益、CTP、国内真实交易和完整四层 PnL |
| 抄底 | 管理入口 + 占位 | 不做完整 Signal、TradeCycle 和外部订单自动归属 |
| 短线交易员 L | 管理入口 + 占位 | 不做完整违规记录、风险额度计算和正式归因 |
| 短线交易员 W | 管理入口 + 占位 | 不做完整违规记录、风险额度计算和正式归因 |

## 4. 后端 V1 最小对象

优先理解这些对象：

- StrategyDefinition
- StrategyVersion
- StrategyInstance
- StrategyAccountBinding
- Account
- Instrument
- ContractSpecification
- TradeCommand
- ExecutionBatch
- Order
- Fill / Deal
- PositionSnapshot
- BalanceSnapshot
- EconomicEvent
- PnLResult
- PnLAttributionItem
- StrategyNavSnapshot

暂时不用深入：

- Investor
- ShareClass
- Subscription / Redemption
- 正式 Fund NAV
- 完整 Finance Ledger
- CTP
- 金融AI分析后端

## 5. 如果你只想审需求

读：

1. `modules/策略-需求文档.md`
2. `modules/交易平台-需求文档.md`
3. `modules/策略管理-需求文档.md`
4. `strategies/资费套利.md`
5. `strategies/跨所价差.md`

## 6. 如果你只想审后端

读：

1. `architecture/platform-target-architecture.md`
2. `architecture/backend/backend-overview.md`
3. `architecture/backend/service-boundaries.md`
4. `architecture/backend/trading-execution-reliability.md`
5. `architecture/backend/execution-runtime-and-gateway.md`
6. `architecture/integration/runtime-command-event-contract.md`

## 7. 如果你只想看 V1 是否跑通

检查这些问题：

- 资费套利能否从交易准备走到订单、成交、持仓、Funding、PnL 和净值？
- 跨所价差能否同时表达 Crypto 和 MT5 两端订单、Deal、持仓、费用和 PnL？
- StrategyNavSnapshot 是否能按固定时间生成？
- 页面是否能区分 Simulation、Paper 和 Live？
- `result_unknown` 是否不会被当成失败后重复下单？
- 缺失值是否不会被当作零？

## 8. 如果你只想看参考代码怎么用

读：

1. `architecture/reference-code-adoption-matrix.md`
2. `architecture/2026-07-17-开源与外部能力采用矩阵-DRAFT.md`

前者是当前执行口径，后者是更完整的外部能力评估底稿。

## 9. 当前不建议大规模移动目录

当前文档很多，但已经存在引用关系。现在直接移动目录会带来路径断裂和上下文丢失。

建议顺序：

1. 先使用本文作为人工入口。
2. 把 V1 口径稳定下来。
3. 使用 `docs/planning/` 专门沉淀执行计划。
4. 最后再分批归档 DRAFT 和历史文档。
