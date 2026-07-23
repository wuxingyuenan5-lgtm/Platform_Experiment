# 人工阅读入口

状态：`active`  
产品基线：Platform V6  
架构版本：Platform V6 Simplified  
适用分支：`main`  
当前实施：Phase 4C Bybit 与 MT5 受控实盘适配器  
文档层级：人工阅读入口

继续工程实施先看：

1. `../../docs/planning/V6-交易安全加固实施计划.md`
2. `../../docs/planning/V6-Phase4C-受控实盘适配器.md`
3. `../../docs/technical/LIVE_VENUE_ADAPTERS.md`
4. `quality/release-gate.md`

## 1. 当前一句话结论

```text
Phase 1：交易输入 fail-closed + Runtime command 原子抢占，已完成
+
Phase 2：TradeCommand + result_unknown Journal 恢复，已完成
+
Phase 3：不可变事实 + 可重建 Position/PnL + 统一估值 NAV，已完成
+
Phase 4A：Kill Switch + 残留敞口 + 幂等风险处置，已完成
+
Phase 4B：外部查询 + FinancialFact 导入 + Difference，已完成
+
Phase 4C：Bybit/MT5 真实账户只读、影子核对和受控写入，工程验收中
+
Phase 4D：日终调度、SLA、报告和连续运行验收，尚未完成
```

Bybit 与 MT5 使用真实账户，不再把 Demo 当作主要验收环境。但 Runtime Live Write 默认关闭；真实账户运营验收未完成前，不得开启自动写入。

## 2. 优先阅读

1. `../../docs/planning/V6-Phase4C-受控实盘适配器.md`
2. `../../docs/technical/LIVE_VENUE_ADAPTERS.md`
3. `../../docs/planning/V6-交易安全加固实施计划.md`
4. `../../docs/planning/V6-Phase4B-外部查询与对账差异.md`
5. `../../docs/technical/VENUE_RECONCILIATION.md`
6. `../../docs/planning/V6-Phase4A-执行风险与Kill-Switch.md`
7. `../../docs/technical/EXECUTION_RISK_CONTROLS.md`
8. `../../docs/technical/FINANCIAL_FACTS.md`
9. `../../docs/technical/API_SPEC.md`
10. `quality/release-gate.md`
11. `architecture/platform-target-architecture.md`
12. `modules/交易平台-需求文档.md`

## 3. 当前工程优先级

| 顺序 | 主题 | 状态 |
|---|---|---|
| 1 | Fail-closed、Runtime 幂等、CI、文档留痕 | 已完成 |
| 2 | TradeCommand、ExecutionBatch、Journal 恢复、Catalog | 已完成 |
| 3 | FinancialFact、正式 PnL 与统一估值 NAV | 已完成 |
| 4 | Kill Switch、残留敞口和风险处置 | 已完成 |
| 5 | Venue Query、事实导入和 Difference | 已完成 |
| 6 | Bybit/MT5 只读实盘与受控写入 | 工程验收中 |
| 7 | 真实账户运营验收与最小仓位演练 | 待人工执行 |
| 8 | 日终调度、SLA 和连续运行 | 待实施 |
| 9 | 新策略和金融AI功能 | 暂缓 |

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

`POST /api/v1/trading/orders` 仅为 deprecated 兼容入口。正式 TradeCommand 必须携带 StrategyInstance 并将其传到 Runtime。

## 5. Runtime Live 入口

```http
GET /gateway/capabilities
GET /venue/orders/by-platform/{platformOrderId}
GET /venue/orders/{externalOrderId}
GET /venue/fills
GET /venue/positions
GET /venue/balances
GET /venue/economic-events
POST /venue/orders/{externalOrderId}/cancel
```

Platform：

```http
POST /api/v1/trading/orders/{orderId}/venue-reconcile
POST /api/v1/ops/venue-reconciliation/runs
GET  /api/v1/ops/venue-reconciliation/runs/{runId}/differences
POST /api/v1/ops/live-economic-events/import
```

## 6. 受控实盘底线

- Platform Live Gate 与 Runtime Live Gate 是两道独立门禁。
- Runtime `liveWriteEnabled` 默认 false。
- Account、StrategyInstance、Symbol 必须位于 allowlist。
- 单笔和单日名义金额必须显式配置且大于零。
- Bybit 使用确定性 orderLinkId；MT5 使用 Magic、Comment 与 Ticket。
- 同步 ACK 不等于成交。
- 无法确认请求结果时标记 `result_unknown`，不得重下。
- 真实凭证只通过 `secret://...` 引用读取。
- 缺凭证、依赖、Terminal、Account 映射或 Instrument 映射时 fail-closed。
- Query 失败不得展示为空仓或零余额。
- 运营验收前保持自动写入关闭。

## 7. Venue Query 与对账底线

- Query 与 Command 分离。
- External Fill/Deal ID 作为稳定事实身份。
- Order、Fill/Deal、Position、Balance、Funding、Swap、Fee 进入 FinancialFact 或 Difference。
- Position Snapshot 用于对账，不覆盖由 Fill 重建的 Formal Position。
- 本地与外部冲突必须形成 Difference。
- Difference 处置保留操作人、原因和时间，不可无痕改写。

## 8. FinancialFact 与账务底线

- FinancialFact 只新增。
- 客户端幂等键和外部事实身份双重去重。
- Contract Multiplier、Quantity Unit 和 Settlement Currency 来自 Catalog。
- Stablecoin 不自动等同 USD。
- 缺少 FX 或 Instrument 映射时标记 incomplete 或 skipped。
- Formal Position/PnL 必须可重建。
- Formal NAV 对全部 active binding 使用同一 valuationTime。

## 9. 前端与产品界面规则

- 前端从 Backend 获取 Strategy、Binding、Account、Instrument 和 ContractSpecification。
- Simulation 与 Live 必须明确区分。
- Catalog 或 Live Capability 不完整时禁用提交并显示简短原因。
- 缺失 Position、PnL、Risk、Venue 或账务数据展示 `—` 或未知。
- 产品页面只展示完成任务所需的信息；开发说明进入 Markdown。

## 10. 当前最小对象

- StrategyDefinition / StrategyVersion / StrategyInstance。
- StrategyAccountBinding / Account。
- Instrument / ContractSpecification。
- TradeCommand / ExecutionBatch / Order / Fill / Deal。
- KillSwitch / ExecutionRiskPolicy / ExecutionRiskAction。
- VenueOrder/Fill/Position/Balance/EconomicEvent Snapshot。
- LiveOrderRoute / LiveWriteClaim。
- VenueReconciliationRun / ReconciliationDifference。
- FinancialFact / Formal Position / Formal PnL / Formal NAV。
- AuditEvent。

## 11. 审视当前版本时必须问

- Live Write 是否默认关闭并有双重门禁？
- Account、Strategy、Symbol 和名义限额是否 fail-closed？
- 同步 ACK 是否被错误当成成交？
- `result_unknown` 是否只查询恢复而不重下？
- 外部事实重放是否保持幂等？
- Funding、Swap 和 Fee 是否使用自然外部身份？
- 未映射 Instrument 是否被显式暴露？
- 本地与外部差异是否留痕？
- Kill Switch 与人工接管是否演练通过？
- 真实账户是否完成只读、最小仓位和连续日终验收？

前八项属于工程验收；最后两项属于运营验收和 Phase 4D。

## 12. 文档治理

- 每个阶段必须有 Issue、分支、PR、计划、技术设计、CI 和回滚说明。
- 代码变化同步更新 API Spec、Release Gate、README、START-HERE 和 Changelog。
- 真实凭证、账户密码、API Key 和 Secret 不得进入仓库或对话记录。