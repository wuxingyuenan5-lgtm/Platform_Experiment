# 人工阅读入口

状态：`active`  
产品基线：Platform V6  
架构版本：Platform V6 Simplified  
适用分支：`main`  
当前实施：Phase 4B 外部 Venue 查询、事实导入与对账差异  
文档层级：人工阅读入口

继续工程实施先看：

1. `../../docs/planning/V6-交易安全加固实施计划.md`
2. `../../docs/planning/V6-Phase4B-外部查询与对账差异.md`
3. `../../docs/technical/VENUE_RECONCILIATION.md`
4. `quality/release-gate.md`

## 1. 当前一句话结论

```text
Phase 1：交易输入 fail-closed + Runtime command 原子抢占，已完成
+
Phase 2：TradeCommand 正式入口 + result_unknown Journal 恢复，已完成
+
Phase 3：不可变事实 + 可重建 Position/PnL + 统一估值 NAV，已完成
+
Phase 4A：Kill Switch + 残留敞口 + 幂等风险处置，已完成
+
Phase 4B：外部查询 + FinancialFact 导入 + Difference，正在验收
+
Phase 4C–4D：Bybit/MT5 Demo 与日终连续运行验收，尚未完成
```

当前系统仍只允许 Simulation / Fake Gateway。通用 Venue Query 契约完成不代表 Bybit Demo、MT5 Demo 或 Live 已获批。

## 2. 优先阅读

1. `../../docs/planning/V6-交易安全加固实施计划.md`
2. `../../docs/planning/V6-Phase4B-外部查询与对账差异.md`
3. `../../docs/technical/VENUE_RECONCILIATION.md`
4. `../../docs/planning/V6-Phase4A-执行风险与Kill-Switch.md`
5. `../../docs/technical/EXECUTION_RISK_CONTROLS.md`
6. `../../docs/planning/V6-Phase3-金融事实与正式账务.md`
7. `../../docs/technical/FINANCIAL_FACTS.md`
8. `../../docs/technical/API_SPEC.md`
9. `quality/release-gate.md`
10. `architecture/platform-target-architecture.md`
11. `architecture/domain/domain-overview.md`
12. `modules/交易平台-需求文档.md`

## 3. 当前工程优先级

| 顺序 | 主题 | 状态 |
|---|---|---|
| 1 | Fail-closed、Runtime 幂等、CI、文档留痕 | 已完成 |
| 2 | TradeCommand、ExecutionBatch、Journal 恢复、动态 Catalog | 已完成 |
| 3 | FinancialFact、正式 PnL 与统一估值 NAV | 已完成 |
| 4 | Kill Switch、腿间延迟、残留敞口和风险处置 | 已完成 |
| 5 | Venue Query、事实自动导入和 Difference | 实现完成，验收中 |
| 6 | Bybit Demo 与 MT5 Demo | 待实施 |
| 7 | 日终调度、故障演练和连续运行 | 待实施 |
| 8 | 新策略和金融AI功能 | 暂缓 |

## 4. 正式交易与风险入口

```http
POST /api/v1/trading/commands
POST /api/v1/trading/execution-batches
POST /api/v1/trading/orders/{orderId}/reconcile
GET  /api/v1/risk/kill-switches/{scopeType}/{scopeId}
PUT  /api/v1/risk/kill-switches/{scopeType}/{scopeId}
GET  /api/v1/trading/execution-batches/{batchId}/risk
POST /api/v1/trading/execution-batches/{batchId}/risk-actions
```

`POST /api/v1/trading/orders` 仅为 deprecated 兼容入口，新代码不得继续使用。

## 5. Phase 4B Venue Query 入口

Runtime：

```http
GET  /venue/orders/by-platform/{platformOrderId}
GET  /venue/orders/{externalOrderId}
GET  /venue/fills
GET  /venue/positions
GET  /venue/balances
POST /venue/orders/{externalOrderId}/cancel
```

Platform Backend：

```http
POST /api/v1/trading/orders/{orderId}/venue-reconcile
POST /api/v1/ops/venue-reconciliation/runs
GET  /api/v1/ops/venue-reconciliation/runs/{runId}
GET  /api/v1/ops/venue-reconciliation/runs/{runId}/differences
POST /api/v1/ops/venue-reconciliation/differences/{differenceId}/resolve
```

## 6. Venue Query 与对账底线

- Query 与 Command 分离；查询不得重发订单或改变外部仓位。
- `result_unknown` 先查 Runtime Journal，再查 Venue Order / Fill。
- 外部快照必须有来源、外部 ID、Account、Instrument、时间和数据质量。
- External Fill ID 同时作为本地 Fill Event ID，重复查询不能重复记账。
- External Order、Fill、Position、Balance 必须转换为不可变 FinancialFact。
- Position Snapshot 用于对账，不直接替代由 Fill 重建的 Formal Position。
- 本地与外部冲突必须形成 Difference，不允许无痕覆盖。
- Difference 必须保留 local/external value、操作人、原因和处置时间。
- 首次处置后的 Difference 不能被后续重复请求无痕改写。
- Fake Venue 只用于 Simulation/CI，不得包装成真实 Demo。
- Bybit/MT5 返回 unsupported 时必须如实展示，不伪装为空仓或零余额。

## 7. Execution Risk 底线

- Kill Switch 在 Batch 认领前和每条 Leg 执行前检查。
- 每个 Batch 固化 `maxLegDelaySeconds`、`maxResidualNotional` 和 `failureAction`。
- 残留风险先净 Contract Delta，再折算未匹配名义金额。
- Batch `failed` 不代表风险已经解除；必须同时检查 Risk Status。
- 自动平仓必须生成反向 TradeCommand。
- 风险动作必须有幂等键、操作人、原因、结果和 AuditEvent。

## 8. FinancialFact 与账务底线

```http
POST /api/v1/financial-facts
POST /api/v1/strategies/instances/{strategyInstanceId}/financials/rebuild
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-positions
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-pnl
POST /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots/run
```

- FinancialFact 只新增，不提供更新和删除业务 API。
- 客户端幂等键和外部事实身份双重去重。
- Quantity Unit、Settlement Currency 和 Contract Multiplier 来自 Catalog。
- Stablecoin 不自动等同 USD。
- 非基础币种缺失 FX 时标记 incomplete。
- Formal Position/PnL 必须能从事实重建。
- Formal NAV 对全部 active binding 使用同一 valuationTime。

## 9. 前端与产品界面规则

- 前端必须从 Backend 获取 Strategy、Binding、Account、Instrument 和 ContractSpecification。
- Catalog 不完整时禁用提交并显示短而准确的原因。
- 缺失 Position、PnL、Risk、Venue 或账务数据展示 `—` 或未知。
- Simulation、Demo、Live 必须明确区分。
- 产品页面只展示完成业务任务需要的信息、操作和状态；开发说明、跳转机制和联调备注进入 Markdown。

## 10. 当前最小对象

- StrategyDefinition / StrategyVersion / StrategyInstance。
- StrategyAccountBinding / Account。
- Instrument / ContractSpecification。
- TradeCommand / ExecutionBatch / Order / Fill / Deal。
- TradingKillSwitch / ExecutionRiskPolicy / ExecutionBatchRisk / ExecutionRiskAction。
- VenueOrderSnapshot / VenueFillSnapshot / VenuePositionSnapshot / VenueBalanceSnapshot。
- VenueReconciliationRun / ReconciliationDifference。
- FinancialFact / Formal Position / Formal PnL / Formal Strategy NAV Snapshot。
- AuditEvent。

## 11. 审视当前版本时必须问

- 外部 Query 是否可能产生新订单副作用？
- `result_unknown` 是否只查询恢复而不重下？
- 外部 Fill 重放是否保持幂等？
- 本地与外部差异是否显式留痕？
- Difference 处置是否可审计且不可无痕改写？
- Kill Switch 与 RiskAction 是否区分新增风险和降低风险？
- Formal Position/PnL/NAV 是否可重建、可核对？
- Bybit/MT5 是否真正跑过 Demo，而非只存在接口壳？
- 日终是否仍存在未解释差异？

前七项属于 Phase 1–4B；最后两项属于 Phase 4C–4D。

## 12. 文档与目录治理

- 每个阶段必须有 Issue、分支、PR、实施计划、技术设计、CI 记录和回滚说明。
- 代码变化同步更新 API Spec、Release Gate、README、START-HERE 和 Changelog。
- 当前不要大规模移动运行目录。
- DRAFT 和历史文件最后再分批归档。