# 人工阅读入口

状态：`active`  
产品基线：Platform V6  
架构版本：Platform V6 Simplified  
适用分支：`main`  
当前实施：Phase 4D 实盘日终对账、报告与运营门禁  
文档层级：人工阅读入口

继续工程实施先看：

1. `../../docs/planning/V6-交易安全加固实施计划.md`
2. `../../docs/planning/V6-Phase4D-实盘日终对账与运营门禁.md`
3. `../../docs/technical/EOD_RECONCILIATION.md`
4. `../../docs/operations/V6-小资金实盘验收手册.md`
5. `quality/release-gate.md`

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
Phase 4C：Bybit/MT5 真实账户适配器与受控写入，工程实现已完成
+
Phase 4D：实盘日终编排 + SLA + 报告 + Scale Gate，工程验收中
```

Bybit 与 MT5 的最终测试使用真实账户的小资金和最小允许仓位，不再把 Demo 当作主要验收环境。但 Runtime Live Write 默认关闭；真实账户运营验收、连续清洁 EOD 和权限治理未完成前，不得扩大实盘。

## 2. 优先阅读

1. `../../docs/planning/V6-Phase4D-实盘日终对账与运营门禁.md`
2. `../../docs/technical/EOD_RECONCILIATION.md`
3. `../../docs/operations/V6-小资金实盘验收手册.md`
4. `../../docs/planning/V6-Phase4C-受控实盘适配器.md`
5. `../../docs/technical/LIVE_VENUE_ADAPTERS.md`
6. `../../docs/planning/V6-Phase4B-外部查询与对账差异.md`
7. `../../docs/technical/VENUE_RECONCILIATION.md`
8. `../../docs/planning/V6-Phase4A-执行风险与Kill-Switch.md`
9. `../../docs/technical/EXECUTION_RISK_CONTROLS.md`
10. `../../docs/technical/FINANCIAL_FACTS.md`
11. `../../docs/technical/API_SPEC.md`
12. `quality/release-gate.md`

## 3. 当前工程优先级

| 顺序 | 主题 | 状态 |
|---|---|---|
| 1 | Fail-closed、Runtime 幂等、CI、文档留痕 | 已完成 |
| 2 | TradeCommand、ExecutionBatch、Journal 恢复、Catalog | 已完成 |
| 3 | FinancialFact、正式 PnL 与统一估值 NAV | 已完成 |
| 4 | Kill Switch、残留敞口和风险处置 | 已完成 |
| 5 | Venue Query、事实导入和 Difference | 已完成 |
| 6 | Bybit/MT5 受控实盘适配器 | 工程实现已完成 |
| 7 | EOD Report、SLA、历史差异阻断和 Scale Gate | 工程验收中 |
| 8 | 真实账户只读、最小仓位和连续 EOD | 待人工执行 |
| 9 | 认证、RBAC、双人审批、密钥托管和告警 | 待实施 |
| 10 | 新策略和金融AI功能 | 暂缓 |

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

## 6. Phase 4D EOD 入口

```http
POST /api/v1/ops/eod-reconciliation/reports
GET  /api/v1/ops/eod-reconciliation/reports
GET  /api/v1/ops/eod-reconciliation/reports/{reportId}
POST /api/v1/ops/eod-reconciliation/reports/{reportId}/review
```

PowerShell：

```powershell
.\scripts\live-readonly-preflight.ps1
.\scripts\run-live-eod-reconciliation.ps1 ...
```

EOD Report 聚合当日订单、历史未终结订单、外部 Position/Balance、Funding/Swap/Fee、FinancialFact、Formal PnL/NAV 和 Difference。报告不会自动下单、平仓、解决差异、提高限额或打开 Live Write。

## 7. 受控实盘底线

- Platform Live Gate 与 Runtime Live Gate 是两道独立门禁。
- Runtime `liveWriteEnabled` 默认 false。
- Account、StrategyInstance、Symbol 必须位于 allowlist。
- 单笔和单日名义金额必须显式配置且大于零。
- Bybit 使用确定性 orderLinkId；MT5 使用 Magic、Comment 与 Ticket。
- 同步 ACK 不等于成交。
- 无法确认请求结果时标记 `result_unknown`，不得重下。
- 真实凭证只通过 `secret://...` 引用读取。
- 缺凭证、依赖、Terminal、Account 映射或 Instrument 映射时 fail-closed。
- Query 失败不得展示为空仓、零余额或 clean EOD。
- 运营验收前保持自动写入关闭。

## 8. Venue Query 与对账底线

- Query 与 Command 分离。
- External Fill/Deal ID 作为稳定事实身份。
- Order、Fill/Deal、Position、Balance、Funding、Swap、Fee 进入 FinancialFact 或 Difference。
- Position Snapshot 用于对账，不覆盖由 Fill 重建的 Formal Position。
- 本地与外部冲突必须形成 Difference。
- Difference 处置保留操作人、原因和时间，不可无痕改写。
- Open 和 Accepted Difference 均阻断扩大实盘。

## 9. EOD 与 Scale Gate 底线

- Business Date、IANA Timezone、Valuation Time 和 Due At 必须显式。
- 同一自然身份、同一载荷重复请求返回原报告。
- 订单范围包括业务日期窗口和历史未终结订单。
- 外部失败必须形成 partial/failed 和 errors，不能补零。
- Skipped Event、Missing Account、Incomplete PnL、Open/Accepted Difference 均导致 blocked。
- 只有完整报告进入 eligible_for_review。
- 人工复核不可变。
- `approved_same_limits` 只批准继续现有小资金限额，不代表可以扩大规模。
- 每个真实测试日必须形成报告并归档 JSON。

## 10. FinancialFact 与账务底线

- FinancialFact 只新增。
- 客户端幂等键和外部事实身份双重去重。
- Contract Multiplier、Quantity Unit 和 Settlement Currency 来自 Catalog。
- Stablecoin 不自动等同 USD。
- 缺少 FX 或 Instrument 映射时标记 incomplete 或 skipped。
- Formal Position/PnL 必须可重建。
- Formal NAV 对全部 active binding 使用同一 valuationTime。

## 11. 前端与产品界面规则

- 前端从 Backend 获取 Strategy、Binding、Account、Instrument 和 ContractSpecification。
- Simulation 与 Live 必须明确区分。
- Catalog 或 Live Capability 不完整时禁用提交并显示简短原因。
- 缺失 Position、PnL、Risk、Venue、EOD 或账务数据展示 `—` 或未知。
- 产品页面只展示完成任务所需的信息；开发说明进入 Markdown。

## 12. 当前最小对象

- StrategyDefinition / StrategyVersion / StrategyInstance。
- StrategyAccountBinding / Account。
- Instrument / ContractSpecification。
- TradeCommand / ExecutionBatch / Order / Fill / Deal。
- KillSwitch / ExecutionRiskPolicy / ExecutionRiskAction。
- VenueOrder/Fill/Position/Balance/EconomicEvent Snapshot。
- LiveOrderRoute / LiveWriteClaim。
- VenueReconciliationRun / ReconciliationDifference。
- EodReconciliationReport / EodReview / ScaleGateStatus。
- FinancialFact / Formal Position / Formal PnL / Formal NAV。
- AuditEvent。

## 13. 审视当前版本时必须问

- Live Write 是否默认关闭并有双重门禁？
- Account、Strategy、Symbol 和名义限额是否 fail-closed？
- 同步 ACK 是否被错误当成成交？
- `result_unknown` 是否只查询恢复而不重下？
- 外部事实重放是否保持幂等？
- Funding、Swap 和 Fee 是否使用自然外部身份？
- 未映射 Instrument 是否被显式暴露？
- 本地与外部差异是否留痕？
- Open/Accepted Difference 是否阻断 Scale Gate？
- 外部失败是否能被错误标记成 clean EOD？
- Kill Switch 与人工接管是否演练通过？
- 真实账户是否完成只读、最小仓位和连续日终验收？

前十项属于工程验收；最后两项属于真实账户运营验收。

## 14. 文档治理

- 每个阶段必须有 Issue、分支、PR、计划、技术设计、CI 和回滚说明。
- 代码变化同步更新 API Spec、Release Gate、README、START-HERE 和 Changelog。
- 真实凭证、账户密码、API Key 和 Secret 不得进入仓库、Markdown、截图或对话记录。
