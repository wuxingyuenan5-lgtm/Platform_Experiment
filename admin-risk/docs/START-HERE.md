# 人工阅读入口

状态：`active`  
产品基线：Platform V6  
架构版本：Platform V6 Simplified  
适用分支：`main`  
当前实施：Phase 4A 双腿执行风险、Kill Switch 与残腿处置  
文档层级：人工阅读入口

找文档先看项目根目录 `00-人工可读目录/README.md`。  
继续工程实施先看：

1. `../../docs/planning/V6-交易安全加固实施计划.md`
2. `../../docs/planning/V6-Phase4A-执行风险与Kill-Switch.md`
3. `../../docs/technical/EXECUTION_RISK_CONTROLS.md`
4. `quality/release-gate.md`

## 1. 当前一句话结论

```text
Phase 1：交易输入 fail-closed + Runtime command 原子抢占，已完成
+
Phase 2：TradeCommand 正式入口 + result_unknown 恢复 + 动态 Catalog，已完成
+
Phase 3：不可变事实 + 可重建 Position/PnL + 统一估值 NAV，已完成
+
Phase 4A：Kill Switch + 残留敞口 + 幂等风险处置，正在验收
+
Phase 4B–4D：外部查询、Demo 执行和日终对账，尚未完成
```

当前系统仍只允许 Simulation / Fake Gateway。Phase 4A 完成也不代表可以进入 Bybit Demo、MT5 Demo 或 Live。

## 2. 优先阅读

1. `../../docs/planning/V6-交易安全加固实施计划.md`
2. `../../docs/planning/V6-Phase4A-执行风险与Kill-Switch.md`
3. `../../docs/technical/EXECUTION_RISK_CONTROLS.md`
4. `../../docs/planning/V6-Phase3-金融事实与正式账务.md`
5. `../../docs/technical/FINANCIAL_FACTS.md`
6. `../../docs/technical/API_SPEC.md`
7. `quality/release-gate.md`
8. `architecture/platform-target-architecture.md`
9. `architecture/domain/domain-overview.md`
10. `modules/策略-需求文档.md`
11. `modules/交易平台-需求文档.md`
12. `planning/V1-开发路线图.md`

## 3. 当前工程优先级

| 顺序 | 主题 | 状态 |
|---|---|---|
| 1 | Fail-closed、Runtime 幂等、CI、文档留痕 | 已完成 |
| 2 | TradeCommand、ExecutionBatch 幂等、`result_unknown` 恢复、动态 Catalog | 已完成 |
| 3 | 不可变事实、正式 PnL 与统一估值 NAV | 已完成 |
| 4 | Kill Switch、腿间延迟、残留敞口和风险处置 | 实现完成，验收中 |
| 5 | 外部 Venue 查询与 FinancialFact 自动导入 | 待实施 |
| 6 | Bybit Demo、MT5 Demo 和日终对账 | 待实施 |
| 7 | 新策略和金融AI功能 | 暂缓 |

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

## 5. Phase 4A 执行风险入口

Kill Switch：

```http
GET /api/v1/risk/kill-switches/{scopeType}/{scopeId}
PUT /api/v1/risk/kill-switches/{scopeType}/{scopeId}
```

支持：

- `global / *`
- `strategy / {strategyInstanceId}`
- `account / {accountId}`

风险策略：

```http
GET /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
PUT /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
```

Batch 风险和处置：

```http
GET  /api/v1/trading/execution-batches/{batchId}/risk
GET  /api/v1/trading/execution-batches/{batchId}/risk-actions
POST /api/v1/trading/execution-batches/{batchId}/risk-actions
```

## 6. 执行风险底线

- Kill Switch 在 Batch 认领前和每条 Leg 执行前检查。
- Kill Switch 命中返回 423，不能继续产生新的 TradeCommand 或 Runtime 副作用。
- 每个 Batch 固化 `maxLegDelaySeconds`、`maxResidualNotional` 和 `failureAction`。
- 第一腿成交后必须显式记录 `firstFillAt` 和残留敞口。
- 残留敞口优先使用 Fill、Contract Multiplier 和 Settlement Currency。
- 多币种且没有风险 FX 快照时标记 `MIXED / incomplete`，不能判断为安全。
- Batch `failed` 不代表风险已经解除；必须同时检查 Risk Status。
- 只有 Risk Status 为 `clear` 才能把正常双腿 Batch 标记为 `hedged`。
- 自动平仓必须生成反向 TradeCommand，不能直接插入 Order。
- 风险动作必须有幂等键、操作人、原因、结果和 AuditEvent。
- 已存在外部 Order 的真实撤单尚未完成，不能伪装为成功取消。

## 7. Phase 3 正式核对入口

```http
POST /api/v1/financial-facts
GET  /api/v1/financial-facts
POST /api/v1/strategies/instances/{strategyInstanceId}/financials/rebuild
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-positions
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-pnl
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots/run
```

旧 `/pnl` 与 `/nav-snapshots` 仍是工程兼容口径；内部金融核对必须使用 `formal-*`。

## 8. FinancialFact 与账务底线

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

## 9. 前端 Catalog 与产品界面规则

交易页面不得硬编码正式账户、策略实例和 Instrument UUID。前端必须从 Backend 获取 StrategyInstance、StrategyAccountBinding、Account、Instrument 和 ContractSpecification。

Catalog 不完整时禁用提交并显示短而准确的原因。缺失 Position、PnL、行情、风险或账务事实显示 `—` 或未知，不能显示伪造的零。

产品页面只展示完成业务任务需要的信息、操作和状态。开发说明、实现解释、跳转机制和联调备注进入 Markdown，不放在正式页面主要视觉层。

## 10. 策略模块 V1 口径

| 策略 | V1 定位 | 当前要求 |
|---|---|---|
| 资费套利 | 完整闭环 | 命令、双腿风险、FinancialFact、Funding／费用、Formal PnL、统一时点 NAV |
| 跨所价差 | 完整闭环 | Crypto／MT5 双腿风险、Order／Deal、Swap／费用、Formal PnL、NAV |
| 海内外价差 | 分析／模拟／预留 | 不做正式 CTP 与完整四层损益闭环 |
| 抄底 | 管理入口 + 占位 | 暂不做完整 Signal、TradeCycle 和自动执行 |
| 短线交易员 L/W | 管理入口 + 占位 | 暂不做完整违规记录、风险额度和正式归因 |

金融AI分析暂缓研发。

## 11. 当前最小对象

- StrategyDefinition / StrategyVersion / StrategyInstance。
- StrategyAccountBinding / Account。
- Instrument / ContractSpecification。
- TradeCommand / ExecutionBatch / Order / Fill / Deal。
- TradingKillSwitch / ExecutionRiskPolicy / ExecutionBatchRisk / ExecutionRiskAction。
- FinancialFact。
- Formal Position / Formal PnL / Formal Strategy NAV Snapshot。
- AuditEvent。

Phase 2 的 Position、PnLResult 和 StrategyNavSnapshot 暂时保留为兼容投影，不继续作为正式口径扩展。

## 12. 审视当前版本时必须问

- 所有业务下单和风险平仓是否经过 TradeCommand？
- Kill Switch 是否在新增风险产生前 fail-closed？
- 第一腿成交后残留敞口和腿间时间是否显式？
- 重复 RiskAction 是否不会重复下单？
- Batch failed、manual_intervention、Risk escalated 是否被正确区分？
- `result_unknown` 是否只恢复而不重下？
- FinancialFact、Formal PnL 和 NAV 是否可重建、可核对？
- Bybit/MT5 是否真正跑过 Demo，而非只存在接口壳？
- 日终是否仍存在未解释差异？

前七项属于 Phase 1–4A；最后两项仍属于 Phase 4B–4D。

## 13. 文档与目录治理

- 每个阶段必须有 Issue、分支、PR、实施计划、技术设计、CI 记录和回滚说明。
- 代码变化同步更新 API Spec、Release Gate、README、START-HERE 和 Changelog。
- 当前不要大规模移动运行目录。
- DRAFT 和历史文件最后再分批归档，不能在业务口径未稳定时大规模移动。