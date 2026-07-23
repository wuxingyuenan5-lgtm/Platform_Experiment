# Platform V6+ 公共领域架构总览

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：公共领域模型入口

## 1. 文档定位

公共领域架构定义前端、Platform Backend、Execution Runtime、API、数据库、数据导入、报表和审计共同使用的稳定业务语言。

最高层对象关系蓝图：

- `unified-domain-model.md`

详细边界与专项规范：

- `../domain-model-boundaries.md`
- `status-enums-and-lifecycles.md`
- `approval-and-dual-control.md`
- `../backend/service-boundaries.md`
- `../backend/storage-ledger-and-audit.md`
- `../backend/execution-runtime-and-gateway.md`

统一领域模型不等于数据库表、API DTO、外部 SDK 对象、Backend Read Model 或 Vue View Model。

## 2. 模型分层

```text
External API / Import / Mock DTO
              ↓ Adapter
Authoritative Domain Model and Facts
              ↓ Projection
Backend Read Model
              ↓ API DTO
Frontend Adapter
              ↓
Frontend View Model / Report Model
```

规则：

- DTO 描述具体来源和传输版本。
- Domain Model 描述稳定身份、关系、状态和业务含义。
- Backend Read Model 是可重建查询投影。
- View Model 只负责页面展示和交互。
- 页面、Mock 和外部框架对象不能反向成为平台领域权威。

## 3. 统一领域主链

```text
LegalEntity
→ Fund
→ Portfolio
→ Book
→ StrategyInstance
→ StrategyAllocation / StrategyAccountBinding
→ Account

StrategyDefinition
→ StrategyVersion
→ StrategyInstance

TradeIntent
→ TradeCommand
→ ExecutionBatch
→ ExecutionPlan
→ LegInstruction
→ platform Order
→ Fill
→ Position / EconomicEvent
→ PnLResult / StrategyNavSnapshot
```

Runtime 链路：

```text
RuntimeDefinition
→ RuntimeInstance
→ RuntimeSession
→ GatewayRuntime
→ WorkerInstance
→ External Session / API / Terminal
```

## 4. Organization and Fund

核心对象：

- LegalEntity。
- Fund。
- Portfolio。
- Book。

正式规则：

- Fund 必须归属于管理 LegalEntity。
- Portfolio 必须归属于 Fund。
- Book 必须归属于 Portfolio。
- 每个 Portfolio 第一阶段至少建立一个 Default Book。
- 只有真实隔离需求出现时才扩展多 Book。
- StrategyInstance 必须归属于 Book 或具有明确过渡映射。
- Strategy PnL 不等于正式 Fund NAV。

完整投资人、份额、申赎和法定基金会计当前延后。

V1 可以由系统自动创建默认 LegalEntity、Fund、Portfolio 和 Book，普通用户无需理解或操作这些层级。它们只用于未来扩展和数据归属，不应把当前自营账户管理复杂化为正式基金行政系统。

## 5. Strategy

核心对象：

- StrategyDefinition。
- StrategyVersion。
- StrategyInstance。
- StrategyAllocation。
- StrategyAccountBinding。
- SignalRecord，适用时。
- ExternalExecutionProfile，适用时。

关键边界：

- StrategyDefinition 表达稳定策略定义。
- StrategyVersion 表达策略逻辑、参数、执行、风险和 PnL 口径版本。
- StrategyInstance 表达某版本在具体 Book、环境和交易模式下的实例。
- StrategyAllocation 表达资金、名义额度或风险预算。
- StrategyAccountBinding 表达策略被允许如何使用 Account。
- Account Balance、StrategyAllocation、Cash Transfer 和 StrategyAccountBinding 不得混用。

## 6. Market、Research and Content

核心对象：

- Venue。
- Instrument。
- InstrumentMapping。
- ContractSpecification。
- QuoteSnapshot。
- FxRateSnapshot。
- ResearchObservation。
- DerivedResearchIndicator。
- ContentItem。
- CalendarEvent。

关键边界：

- InstrumentId 是平台稳定标的身份。
- TradingView、交易所、MT5 和供应商 symbol 通过 InstrumentMapping 管理。
- 合约规格必须版本化。
- Execution Market Data、Research Data 和 Content Data 使用不同质量、时间和修订语义。

## 7. Account、Position and Exposure

核心对象：

- Account。
- AccountOwnership。
- AccountPurpose。
- AccountRestriction。
- BalanceSnapshot。
- MarginSnapshot。
- Position。
- PositionSnapshot。
- StrategyPositionGroup。
- ExposureSnapshot。

关键边界：

- Account 表示外部账户主档，不等于 Fund 或 StrategyInstance。
- AccountOwnership 与 StrategyAccountBinding 分开。
- Position 可以由 Fill 推导、外部同步或对账确认，但必须记录来源。
- 平台推导持仓与外部持仓不一致时进入 Reconciliation。
- Position、ExecutionBalanceStatus 和 ExposureStatus 分开。

## 8. Trading and Execution

核心对象：

- TradeIntent。
- TradeCommand。
- ExecutionBatch。
- ExecutionPlan。
- LegInstruction。
- Order。
- ExternalOrderReference。
- Fill／Deal。
- ManualIntervention。

统一链路：

```text
TradeIntent
→ TradeCommand
→ ExecutionBatch
→ ExecutionPlan
→ LegInstruction
→ pre-created platform Order
→ Runtime Command
→ External Order
→ Runtime Event
→ Fill
```

关键边界：

- TradeCommand accepted 不等于交易完成。
- ExecutionBatch 组织多腿业务关系。
- ExecutionPlan 描述如何执行，不等于 Runtime 算法进程。
- platformOrderId 在外部提交前创建。
- 一张 Order 可以产生多笔 Fill。
- 结果未知不是失败终态。

## 9. Runtime and Gateway

核心对象：

- RuntimeDefinition。
- RuntimeInstance。
- RuntimeSession。
- GatewayDefinition。
- GatewayRuntime。
- GatewayCapability。
- WorkerDefinition。
- WorkerInstance。
- RuntimeCommandEnvelope。
- RuntimeEventEnvelope。
- Runtime Journal。

关键边界：

- Runtime 独立于 Platform API 进程。
- Runtime 拥有实时连接、Worker、OMS 缓存和恢复位置。
- Platform Backend 拥有业务控制和永久交易事实。
- Runtime Journal 不成为平台业务数据库。
- Gateway connected 不代表可交易；必须分别表达 Connectivity、Synchronization、Readiness 和 TradingCapability。

## 10. Risk、Approval and Governance

Risk 核心对象：

- RiskRule。
- RiskLimit。
- RiskSnapshot。
- RiskDecision。
- RiskEvent。
- GlobalTradingBlock。

Approval 核心对象：

- ApprovalPolicy。
- ApprovalRequest。
- ApprovalDecision。
- ApprovalGrant。

IAM 和治理对象：

- User。
- Role。
- Capability。
- DataScope。
- EnvironmentScope。
- TradingModeScope。
- AuditEvent。
- ConfigurationVersion。

规则：

- Role 是 Capability 集合，不是最终授权模型。
- RiskDecision、ApprovalDecision、Capability 和 AuditEvent 不能互相替代。
- DataScope 应支持 Fund、Portfolio、Book、StrategyInstance 和 Account。

## 11. Reconciliation and Data Quality

核心对象：

- ReconciliationJob。
- ReconciliationResult。
- ReconciliationDifference。
- DataQualityState。
- DataCorrectionRecord。

规则：

- 订单、成交、持仓、余额、费用、EconomicEvent 和 PnL 均可对账。
- 缺失不能静默当零。
- 差异不能无痕覆盖原始事实。
- 修正通过 DataCorrectionRecord、AdjustmentEntry 和版本化重算完成。

## 12. Economic Ledger and PnL

核心对象：

- EconomicEvent。
- LedgerEntry。
- ValuationSnapshot。
- PnLResult。
- PnLAttributionItem。
- StrategyNavSnapshot。
- AdjustmentEntry。
- RecalculationRun。

关键边界：

- EconomicEvent 表示已发生的经济事实。
- Strategy Economic Ledger 用于策略收益、成本、资金变化和对账。
- Strategy Economic Ledger 不等于完整 Finance Ledger。
- PnLResult 是版本化派生结果，必须可重现。
- StrategyNavSnapshot 是策略实例固定时间运营净值快照，不是正式 Fund NAV。
- 三类套利可以具有不同归因树，但统一归入 PnLResult。
- 未建立估值政策、费用、现金、份额和复核流程前，不产生正式 Fund NAV。

## 13. Backend Read Model and Reporting

典型 Read Model：

- FundOverviewReadModel。
- PortfolioRiskReadModel。
- TradingWorkspaceReadModel。
- StrategyPnlOverviewReadModel。
- StrategyCapitalOverviewReadModel。
- OpenExecutionBatchReadModel。

Read Model 可以缓存和重建，但不接受业务写入。

ReportDefinition 和 ReportVersion 读取权威事实或稳定投影，不重新形成第二套交易、PnL 或风险规则。

## 14. 稳定业务 ID

核心 ID 包括：

- `legalEntityId`。
- `fundId`。
- `portfolioId`。
- `bookId`。
- `strategyId`。
- `strategyVersionId`。
- `strategyInstanceId`。
- `strategyAllocationId`。
- `strategyAccountBindingId`。
- `accountId`。
- `venueId`。
- `instrumentId`。
- `tradeCommandId`。
- `executionBatchId`。
- `legInstructionId`。
- `platformOrderId`。
- `fillId`。
- `positionId`。
- `economicEventId`。
- `pnlResultId`。
- `riskEventId`。
- `approvalRequestId`。
- `reconciliationResultId`。
- `runtimeInstanceId`。
- `gatewayRuntimeId`。
- `workerInstanceId`。

外部 ID 与平台 ID 必须分开并记录作用域。

## 15. 标准值与时间

金额、价格、数量和费率使用 Decimal 和明确单位，不使用页面格式化字符串作为领域值。

至少区分：

- Money。
- Price。
- Quantity。
- Rate。
- Currency。
- Unit。

时间至少区分：

- occurredAt。
- externalTime。
- receivedAt。
- processedAt。
- businessDate。
- tradingDay。
- settlementDate。
- valuationDate。
- dataAsOf。

## 16. 核心不变量

1. 每个核心对象只有一个主责领域。
2. Fund、Portfolio、Book、StrategyInstance 和 Account 分开。
3. StrategyAllocation 不等于 Account Balance。
4. StrategyAccountBinding 不等于 AccountOwnership。
5. StrategyVersion 不无痕重解释历史交易。
6. TradeCommand accepted 不等于交易完成。
7. Order、Fill、Position、Exposure、Risk 和 PnL 分开。
8. platformOrderId 在外部提交前创建。
9. Runtime OMS 和 Journal 不形成平台永久权威。
10. 外部 DTO 不进入核心领域。
11. 缺失数据不静默当零。
12. 修正不覆盖原始事实。
13. PnLResult 版本化并可重现。
14. Strategy PnL 不等于 Fund NAV。
15. Read Model 和前端状态不接受业务写入。
16. 权限、审批、风险和审计不能相互替代。

## 17. 初期最小实现对象

后端与 Fake Gateway 首阶段至少实现：

```text
LegalEntity
Fund
Portfolio
Book
StrategyDefinition
StrategyVersion
StrategyInstance
StrategyAllocation
StrategyAccountBinding
Venue
Instrument
ContractSpecification
Account
TradeCommand
ExecutionBatch
ExecutionPlan
LegInstruction
Order
Fill
Position
BalanceSnapshot
EconomicEvent
PnLResult
StrategyNavSnapshot
RiskDecision
ReconciliationResult
RuntimeInstance
GatewayRuntime
WorkerInstance
AuditEvent
```

V1 完整闭环优先覆盖：

- 资费套利：Crypto 现货／永续、真实 API 模拟盘／测试盘、Funding、费用、持仓、PnL 和 StrategyNavSnapshot。
- 跨所价差：Crypto 真实 API 模拟盘／测试盘、MT5 Demo／Worker、Order／Deal 映射、Swap／费用、持仓、PnL 和 StrategyNavSnapshot。

海内外价差、抄底、短线交易员 L 和短线交易员 W 第一阶段只保留管理入口、字段和占位状态，不要求完整交易闭环和完整 PnL。

当前延后：

- Investor。
- ShareClass。
- Subscription／Redemption。
- 完整 Fund NAV。
- 完整 Finance Ledger。
- 复杂多 Book 管理。
- 金融AI分析专项对象。

## 18. 建设原则

- 先统一身份、关系、所有权和生命周期，再扩展字段。
- 不为了形式建立庞大 DDD 框架。
- Platform Backend、Runtime 和 Frontend 通过契约协作，不共享内部对象。
- 数据库物理模型服从领域边界，但可以按事务和查询需求拆分。
- 新增对象时先检查是否形成重复语义或第二套权威。
- 实质领域变更同步更新统一模型、详细边界、状态、模块所有权和契约。
