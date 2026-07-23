# 人工阅读入口

状态：`active`  
产品基线：Platform V6  
架构版本：Platform V6 Simplified  
适用分支：`main`  
文档层级：人工阅读入口

如果你是为了“找文档”，先打开项目最外层的 `00-人工可读目录/README.md`。  
如果你是为了“快速理解当前 V1 结论”，继续读本文。  
如果你是为了“继续工程实施”，先读 `../../docs/planning/V6-交易安全加固实施计划.md`。

## 1. 当前一句话结论

当前第一阶段不是继续扩张全部平台，而是先把交易安全和两条策略闭环做实：

```text
交易安全与可靠执行底线
+
资费套利完整闭环
+
跨所价差完整闭环
+
策略管理承接资金、持仓、订单、费用、PnL 和固定时间净值
```

当前代码仍只允许 Simulation / Fake Gateway。Paper、Demo 和 Live 必须按照实施计划逐阶段验收。

海内外价差、抄底、短线交易员 L、短线交易员 W 第一阶段先保留入口、字段和占位状态。金融AI分析暂缓研发。

## 2. 先读这 9 篇

按顺序阅读：

1. `../../docs/planning/V6-交易安全加固实施计划.md`
2. `modules/一级模块定位总表.md`
3. `modules/策略-需求文档.md`
4. `modules/交易平台-需求文档.md`
5. `modules/策略管理-需求文档.md`
6. `architecture/platform-target-architecture.md`
7. `architecture/domain/domain-overview.md`
8. `architecture/reference-code-adoption-matrix.md`
9. `planning/V1-开发路线图.md`

读完这些文档，可以理解当前产品边界、V1 做什么、交易安全门禁、参考代码怎么吸收和开发顺序怎么排。

## 3. 当前工程优先级

| 优先级 | 主题 | 当前状态 |
|---|---|---|
| P0 | Fail-closed、Runtime 幂等、CI、文档留痕 | 正在实施 |
| P1 | TradeCommand 唯一写入口、`result_unknown` 恢复 | 待实施 |
| P2 | 外部事实层、合约规格、PnL/NAV 重构 | 待实施 |
| P3 | 双腿风险处置、Bybit Demo、MT5 Demo、日终对账 | 待实施 |
| P4 | 新策略和新功能扩展 | 暂缓 |

在 P0–P3 完成前，不讨论真实资金 Live 发布。

## 4. 策略模块 V1 口径

| 策略 | V1 定位 | 当前要求 |
|---|---|---|
| 资费套利 | 完整闭环 | 行情、交易准备、模拟执行、订单成交、持仓、Funding／费用、PnL、固定时间净值 |
| 跨所价差 | 完整闭环 | Crypto 腿、MT5 腿、Order／Deal 映射、持仓、Swap／费用、PnL、固定时间净值 |
| 海内外价差 | 分析／模拟／预留 | 不做正式汇率损益、CTP、国内真实交易和完整四层 PnL |
| 抄底 | 管理入口 + 占位 | 不做完整 Signal、TradeCycle 和外部订单自动归属 |
| 短线交易员 L | 管理入口 + 占位 | 不做完整违规记录、风险额度计算和正式归因 |
| 短线交易员 W | 管理入口 + 占位 | 不做完整违规记录、风险额度计算和正式归因 |

## 5. 后端 V1 最小对象

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

## 6. 交易安全底线

任何交易写路径都必须满足：

- 未知账户、未知标的、停用账户一律拒绝。
- 标的缺失 ContractSpecification 一律拒绝。
- 数量、价格不满足合约步长一律拒绝。
- Runtime 必须在 Gateway 外部副作用前原子抢占 command。
- 重复 command 不得产生第二次外部调用。
- `result_unknown` 必须先查询外部订单、成交和持仓，不能直接重试。
- Live 默认关闭，凭证只保存安全引用。

详细门槛见 `quality/release-gate.md`。

## 7. 如果你只想审需求

读：

1. `modules/策略-需求文档.md`
2. `modules/交易平台-需求文档.md`
3. `modules/策略管理-需求文档.md`
4. `strategies/资费套利.md`
5. `strategies/跨所价差.md`

## 8. 如果你只想审后端

读：

1. `../../docs/planning/V6-交易安全加固实施计划.md`
2. `architecture/platform-target-architecture.md`
3. `architecture/backend/backend-overview.md`
4. `architecture/backend/service-boundaries.md`
5. `architecture/backend/trading-execution-reliability.md`
6. `architecture/backend/execution-runtime-and-gateway.md`
7. `architecture/integration/runtime-command-event-contract.md`

## 9. 如果你只想看 V1 是否跑通

检查这些问题：

- 未知账户、标的和停用账户是否在 Runtime 前被拒绝？
- 重复 Runtime command 是否只调用一次 Gateway？
- 资费套利能否从交易准备走到订单、成交、持仓、Funding、PnL 和净值？
- 跨所价差能否同时表达 Crypto 和 MT5 两端订单、Deal、持仓、费用和 PnL？
- StrategyNavSnapshot 是否能按同一估值时间汇总全部绑定账户？
- 页面是否能区分 Simulation、Paper 和 Live？
- `result_unknown` 是否不会被当成失败后重复下单？
- 缺失值是否不会被当作零？

## 10. 如果你只想看参考代码怎么用

读：

1. `architecture/reference-code-adoption-matrix.md`
2. `architecture/2026-07-17-开源与外部能力采用矩阵-DRAFT.md`

前者是当前执行口径，后者是更完整的外部能力评估底稿。

## 11. 当前不建议大规模移动目录

当前文档很多，但已经存在引用关系。现在直接移动目录会带来路径断裂和上下文丢失。

建议顺序：

1. 先使用本文作为人工入口。
2. 按 `docs/planning/` 的实施计划稳定交易安全和 V1 口径。
3. 每次 Pull Request 同步更新 Changelog 和 Release Gate。
4. 最后再分批归档 DRAFT 和历史文档。
