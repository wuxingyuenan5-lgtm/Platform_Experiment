# Platform V6 公共领域架构总览

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：公共领域模型

## 1. 文档定位

公共领域架构定义前端、后端、接口、数据库、数据导入、报表和审计共同使用的稳定业务语言。

它不描述页面布局，不等同于数据库表，也不等同于 API DTO 或 Backend Read Model。

## 2. 模型分层

```text
External / Import / Mock DTO
            ↓ Adapter
Authoritative Domain Model
            ↓ Projection
Backend Read Model
            ↓ API DTO
Frontend Adapter
            ↓
Frontend View Model / Report Model
```

- DTO 描述具体来源和传输版本。
- Domain Model 描述稳定业务身份、关系和生命周期。
- Backend Read Model 为查询场景形成可重建投影。
- View Model 描述页面格式化和交互。

## 3. 核心领域

### 3.1 Strategy

核心对象：

- StrategyDefinition。
- StrategyVersion。
- StrategyInstance。
- StrategyAccountBinding。

StrategyAccountBinding 由 Strategy 拥有，通过 `accountId` 引用 Account。

### 3.2 Market、Research 与 Content

核心对象：

- Venue。
- Instrument。
- ContractSpecification。
- QuoteSnapshot。
- FxRateSnapshot。
- ResearchObservation。
- DerivedResearchIndicator。
- ContentItem。
- CalendarEvent。

Execution Market Data、Research Data 和 Content／Calendar Data 使用不同时间、质量和修订语义。

### 3.3 Account and Capital

核心对象：

- Account。
- AccountRestriction。
- BalanceSnapshot。
- MarginSnapshot。
- CapitalAllocation。

账户主档、账户快照、策略账户绑定和策略资金分配是不同对象。

### 3.4 Position and Exposure

核心对象：

- Position。
- PositionSnapshot。
- StrategyPositionGroup。
- ExposureSnapshot。

双腿策略由多个 Position 组成；ExposureStatus 与持仓状态、执行配平状态分开。

### 3.5 Trading and Execution

核心对象：

- TradeIntent。
- TradeCommand。
- ExecutionBatch。
- LegInstruction。
- Order。
- Execution／Fill。
- ExecutionBalanceResult。
- ManualIntervention。

必须区分：

- 用户或策略想完成什么。
- 平台受理了什么命令。
- 执行批次组织哪些交易腿。
- 向外部系统提交哪些订单。
- 实际发生哪些 Fill。
- 当前是否配平以及存在何种暴露。

### 3.6 PnL and Strategy Economic Ledger

核心对象：

- EconomicEvent。
- LedgerEntry。
- PnLResult。
- PnLAttributionItem。
- ValuationSnapshot。
- AdjustmentEntry。

Strategy Economic Ledger 用于策略损益、资金变化和对账，不等于完整财务会计总账。

### 3.7 Risk

核心对象：

- RiskRule。
- RiskLimit。
- RiskSnapshot。
- RiskDecision。
- RiskEvent。
- RiskAction。
- GlobalTradingBlock。

风险规则、判断、事件和处置是不同对象。

### 3.8 Reconciliation and Data Quality

核心对象：

- ReconciliationJob。
- ReconciliationResult。
- ReconciliationDifference。
- DataQualityState。
- DataCorrectionRecord。

缺失数据不能静默转换为零，修正不能覆盖原始事实。

### 3.9 Approval and Control

核心对象：

- ApprovalPolicy。
- ApprovalRequest。
- ApprovalDecision。
- ApprovalGrant。

权限、审批、风险判断和审计不能相互替代。

### 3.10 Identity、Audit、Notification and Reporting

核心对象：

- User。
- Role。
- Capability。
- DataScope。
- AuditEvent。
- Notification。
- ReportDefinition。
- ReportVersion。

角色是能力集合；报表和通知不重新生成业务事实。

### 3.11 Backend Read Model

典型对象：

- TradingWorkspaceReadModel。
- StrategyPnlOverviewReadModel。
- StrategyCapitalOverviewReadModel。
- OpenExecutionBatchReadModel。

Read Model 服务查询，可以缓存和重建，但不接受业务写入。

## 4. 核心关系

```text
StrategyDefinition
  └─ StrategyVersion
       └─ StrategyInstance
            ├─ StrategyAccountBinding ── Account
            ├─ TradeCommand
            │    └─ ExecutionBatch
            │         ├─ LegInstruction
            │         │    └─ Order
            │         │         └─ Execution / Fill
            │         ├─ ExecutionBalanceResult
            │         └─ ManualIntervention
            ├─ Position / ExposureSnapshot
            ├─ EconomicEvent / LedgerEntry / PnLResult
            ├─ RiskSnapshot / RiskEvent
            └─ ReconciliationResult

ApprovalRequest
  └─ ApprovalDecision
       └─ ApprovalGrant ── TradeCommand / ConfigurationCommand
```

## 5. 运行上下文

必须区分：

- DeploymentEnvironment：development、testing、staging、production。
- TradingMode：demo、simulation、paper、live。
- TradingPermissionState：disabled、read_only、enabled、blocked。

`production` 不等于 `live`。

## 6. 核心身份

核心对象使用稳定业务 ID，例如：

- `strategyId`
- `strategyVersionId`
- `strategyInstanceId`
- `strategyAccountBindingId`
- `accountId`
- `instrumentId`
- `tradeCommandId`
- `executionBatchId`
- `legInstructionId`
- `orderId`
- `executionId`
- `positionId`
- `pnlResultId`
- `riskEventId`
- `approvalRequestId`
- `reconciliationResultId`

外部系统 ID 与平台 ID 分开保存。

## 7. 时间和数值

### 时间

根据业务含义区分：

- 业务日期。
- 事件发生时间。
- 外部来源时间。
- 平台接收时间。
- 计算时间。
- 更新时间。
- 数据截止时间。

### 数值

金额、价格、数量、比例和汇率保留：

- 原始数值。
- 单位和币种。
- 精度。
- 来源和时间。

页面格式化字符串不是领域原始值。

## 8. 状态语义

完整枚举和生命周期以 `status-enums-and-lifecycles.md` 为唯一来源。

至少分别使用：

- QuoteStatus。
- DataQualityStatus。
- TradeCommandStatus。
- ExecutionBatchStatus。
- OrderStatus。
- ExecutionBalanceStatus。
- ExposureStatus。
- RiskStatus。
- ReconciliationStatus。
- ApprovalStatus。

不能使用一个通用 `status` 覆盖全部对象。

## 9. 展示和数据权威

同一对象可以在多个模块展示：

- 交易平台展示当前执行和即时风险。
- 策略管理展示历史订单、持仓、资金和损益。
- 风险管理展示风险、账户、监控、审批和审计入口。

展示目的不同不代表建立多套 Order、Position、PnL 或 Risk 定义。

## 10. 建设原则

- 先统一身份、所有权和生命周期，再扩展字段。
- 不建立没有真实需求的庞大 DDD 框架。
- 外部对象通过 Adapter 转换。
- Read Model 不成为权威写模型。
- 公共领域对象不包含 Vue 组件、CSS 和页面配置。
- 策略特有损益允许差异，但使用稳定 PnLResult 和归因语义。

## 11. 详细规范

- `../domain-model-boundaries.md`
- `status-enums-and-lifecycles.md`
- `approval-and-dual-control.md`
- `../backend/query-and-read-models.md`
- `../backend/research-data-and-content-boundaries.md`

新增对象时先更新详细领域规范，再形成后端模型、API DTO 和前端 View Model。
