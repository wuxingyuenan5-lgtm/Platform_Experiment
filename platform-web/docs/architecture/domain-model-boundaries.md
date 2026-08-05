# Platform 0.10.x 公共领域模型边界

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：公共领域模型

## 1. 文档定位

本文档定义 Platform V6 前端、后端、接口适配、数据导入、报表和审计共同使用的核心业务对象及其边界。

领域模型表达稳定业务语义，不等同于：

- 后端数据库表。
- 外部交易所或经纪商对象。
- API 请求和响应 DTO。
- 后端页面聚合 Read Model。
- Vue 页面或组件 View Model。
- Mock 文件格式。

状态枚举以 `domain/status-enums-and-lifecycles.md` 为唯一来源。

## 2. 模型分层

```text
External API DTO / Import DTO / Mock DTO
                  ↓ adapter
Authoritative Domain Model / Domain Facts
                  ↓ projection / aggregation
Backend Read Model
                  ↓ API mapping
API DTO
                  ↓ frontend adapter / selector
Frontend Domain Model / View Model / Report Model
```

### DTO

描述具体传输来源和接口版本，可以随外部系统、供应商或 API 版本变化。

### Domain Model

描述平台内部稳定身份、关系、状态和业务含义。

### Backend Read Model

为页面或查询场景形成的只读投影，不拥有新的业务事实和写入权。

### View Model／Report Model

描述图表、表格、页面交互或正式报表需要的展示结构。

禁止页面结构反向成为后端领域对象，也禁止长期让 Vue 组件直接依赖完整 API 响应。

## 3. Strategy 领域

### 3.1 StrategyDefinition

表示平台纳管的一项策略定义。

稳定字段：

- `strategyId`
- 正式名称和分类
- 产品能力范围
- 基础腿结构
- 基础账户结构

当前前端 `strategyRegistry.ts` 是静态展示和能力声明来源，不是策略运行状态的最终权威。

### 3.2 StrategyVersion

表示策略逻辑、参数口径或执行规则的版本。

稳定字段：

- `strategyVersionId`
- `strategyId`
- 版本号
- 生效时间
- 状态
- 变更摘要

### 3.3 StrategyInstance

表示某个策略版本在具体运行上下文中的实例。

稳定字段：

- `strategyInstanceId`
- `strategyId`
- `strategyVersionId`
- DeploymentEnvironment
- TradingMode
- StrategyInstanceStatus
- 参数集版本

StrategyDefinition、StrategyVersion 和 StrategyInstance 不得混为一个对象。

### 3.4 StrategyAccountBinding

表示策略实例与账户之间的用途和关系，例如主腿账户、对冲腿账户或资金账户。

稳定字段：

- `strategyAccountBindingId`
- `strategyInstanceId`
- `accountId`
- 账户角色
- 生效和失效时间
- 状态和版本

所有权规则：

- Strategy 模块拥有 StrategyAccountBinding。
- Account 模块拥有 Account 主档和账户可用状态。
- 绑定记录只引用 `accountId`，不复制账户主数据。
- 绑定变更需要验证账户存在、权限、TradingMode 和必要审批。

## 4. Market、Research 与 Content 领域

### 4.1 Venue

表示交易所、经纪商、数据源或交易环境。

稳定字段：

- `venueId`
- 名称和类型
- 市场
- 状态

### 4.2 Instrument

表示可交易或可观察的标准化标的。

稳定字段：

- `instrumentId`
- 标准代码
- 页面显示名称
- 外部 symbol 映射
- 市场和产品类型
- 计价币种和基础资产

页面显示名称和外部 symbol 不得长期混用为同一字段。

### 4.3 ContractSpecification

表示合约乘数、最小数量、价格精度、交易时段和订单规则。

### 4.4 QuoteSnapshot

表示某一时点可用于观察或执行判断的行情快照。

至少包含：

- `instrumentId`
- 报价时间
- 接收时间
- 最新价或买卖价
- 数据来源
- QuoteStatus
- DataQualityStatus

行情值和行情质量状态分开。

### 4.5 FxRateSnapshot

表示某一时点汇率、来源、时间和质量，用于多币种折算和损益计算。

### 4.6 ResearchObservation

表示宏观、资产、公司或研究数据的某次观察值。

至少包含：

- `researchSeriesId`
- 观察期
- 发布时间
- 数值、单位和来源
- 修订版本
- DataQualityStatus

### 4.7 DerivedResearchIndicator

表示基于研究数据形成的衍生指标，保留计算版本、参数、输入数据版本和截止时间。

### 4.8 ContentItem／CalendarEvent

表示新闻、摘要、宏观事件、理财信息或其他内容对象。原文、人工整理和 AI 摘要必须区分。

详细边界参见 `backend/research-data-and-content-boundaries.md`。

## 5. Account 与 Capital 领域

### 5.1 Account

表示交易所、券商、经纪商或其他执行环境中的账户主档。

稳定字段：

- `accountId`
- 账户名称
- 平台或机构
- 基础币种
- 账户类型
- 账户状态

策略账户页面不等于账户主档；同一个账户可以被多个策略实例引用。

### 5.2 BalanceSnapshot

表示账户某一时点的权益、余额、可用资金和冻结资金。

### 5.3 MarginSnapshot

表示账户某一时点的保证金占用、保证金率和相关风险数据。

### 5.4 CapitalAllocation

表示账户或资金池分配给策略的资金额度，不等于账户实际余额和策略实际持仓价值。

### 5.5 AccountRestriction

表示账户当前是否允许查询、下单、平仓或资金操作及其原因。

## 6. Position 与 Exposure 领域

### 6.1 Position

表示账户在某标的上的实际持仓状态。

稳定字段：

- `positionId`
- `strategyInstanceId`，适用时
- `accountId`
- `instrumentId`
- 方向和数量
- 平均价格
- 已实现和未实现损益
- 来源和更新时间

双腿或多腿策略由多个 Position 组成，不应将多条腿硬编码成单个扁平持仓对象。

### 6.2 StrategyPositionGroup

用于将多个持仓归入同一个策略组合、ExecutionBatch 或套利组合。

### 6.3 ExposureSnapshot

表示某一时点的方向、名义价值、Delta、汇率或其他未对冲暴露。

ExposureStatus 不等于 Position 状态或 ExecutionBalanceStatus。

## 7. Trading 与 Execution 领域

### 7.1 TradeIntent

表示用户或策略希望完成的业务目标，例如建立某个资费套利组合。

TradeIntent 不是外部订单，也不表示已经通过权限和风险检查。

### 7.2 TradeCommand

表示平台对一次改变交易状态请求的受理记录。

稳定字段：

- `tradeCommandId`
- `requestId`
- `idempotencyKey`
- `strategyInstanceId`
- 操作类型
- 提交人和提交时间
- DeploymentEnvironment
- TradingMode
- TradeCommandStatus

TradeCommand 只表达命令受理，不重复维护 ExecutionBatch 的执行过程。

### 7.3 ExecutionBatch

表示为完成同一业务目标而组织的一组交易腿和订单，是双腿或多腿执行的核心聚合对象。

稳定字段：

- `executionBatchId`
- `tradeCommandId`
- `strategyInstanceId`
- ExecutionBatchStatus
- ExecutionBalanceStatus
- ExposureStatus
- 目标配平关系
- 创建、更新和完成时间

### 7.4 LegInstruction

表示执行批次中的一条交易腿计划。

稳定字段：

- `legInstructionId`
- `executionBatchId`
- 腿角色
- `accountId`
- `instrumentId`
- 方向
- 目标数量或名义价值
- 订单类型和价格参数

### 7.5 Order

表示向执行环境提交的订单及其生命周期。

稳定字段：

- `orderId`
- `executionBatchId`
- `legInstructionId`
- `strategyInstanceId`
- `accountId`
- `instrumentId`
- 买卖方向和订单类型
- 数量和价格
- OrderStatus
- 外部订单 ID 和外部原始状态
- 创建、提交和更新时间

### 7.6 Execution／Fill

表示订单实际成交结果。

稳定字段：

- `executionId`
- `orderId`
- 外部成交 ID
- 成交数量和价格
- 手续费和费用币种
- 成交时间和接收时间

一个 Order 可以对应多个 Fill。Order 与 Fill 必须分开。

### 7.7 ExecutionBalanceResult

表示 ExecutionBatch 的目标关系、实际关系、偏差、ExecutionBalanceStatus 和人工接受结果。

### 7.8 ManualIntervention

表示对未完成、异常或结果未知执行进行的人工撤销、补单、配平、终止或确认。

详细可靠性流程参见 `backend/trading-execution-reliability.md`。

## 8. PnL 与 Strategy Economic Ledger 领域

### 8.1 EconomicEvent

表示产生策略经济影响的原始事实，例如：

- 成交。
- 手续费。
- 资金费。
- 隔夜费。
- 利息。
- 汇率折算。
- 资金划转。
- 已确认调整。

### 8.2 LedgerEntry

表示基于 EconomicEvent 形成的策略经济账本记录，用于损益、资金变化、重算和对账。

当前 Ledger 指 Strategy Economic Ledger，不等于完整财务会计总账。公司会计科目、借贷记账和法定报表需要独立设计。

### 8.3 PnLResult

表示按明确范围和口径形成的损益结果。

稳定字段：

- `pnlResultId`
- `strategyInstanceId`
- 统计区间
- 计价币种
- 已实现和未实现损益
- 费用
- 计算版本和计算时间
- 数据截止时间
- 估算或结算状态

### 8.4 PnLAttributionItem

表示策略特有损益归因项。明细由对应策略文档定义，不强行压成完全相同结构。

### 8.5 AdjustmentEntry

表示经过授权的经济事件或损益调整。调整不得无痕覆盖原始事实。

## 9. Risk 领域

### 9.1 RiskRule

表示风险规则、指标、阈值和适用范围。

### 9.2 RiskLimit

表示账户、策略、标的或操作的额度和限制。

### 9.3 RiskSnapshot

表示某一时点风险指标和状态结果。

### 9.4 RiskDecision

表示执行前检查或人工复核形成的允许、提示、限制、禁止或待确认结果。

### 9.5 RiskEvent

表示规则触发、异常或风险状态变化。

### 9.6 RiskAction／GlobalTradingBlock

表示撤单、阻断、降低额度、人工确认或范围化交易阻断。

规则、快照、判断、事件和处置不得使用一个宽泛 Risk 对象表达。

## 10. Reconciliation 与 Data Quality 领域

### 10.1 ReconciliationJob

表示一次订单、成交、持仓、账户、损益或账本核对任务。

### 10.2 ReconciliationResult

表示核对结果、状态和数据截止时间。

### 10.3 ReconciliationDifference

表示来源之间的具体差异、金额、数量、影响范围和处理状态。

### 10.4 DataQualityState

表示数据完整、延迟、缺失、重复、冲突、未验证或无效。

缺失值不得静默转换为零。

### 10.5 DataCorrectionRecord

表示经过授权的数据修正，包含原始值、修正值、原因、操作人、审批和影响重算。

## 11. Approval 与双人复核领域

### 11.1 ApprovalPolicy

定义某类高风险操作的审批规则、适用范围、审批人数和授权有效期。

### 11.2 ApprovalRequest

表示某次待审批的高风险操作请求。

### 11.3 ApprovalDecision

表示独立审批人的批准或拒绝决定。

### 11.4 ApprovalGrant

表示审批通过后生成、与对象和参数范围绑定的短期授权。

权限、审批、RiskDecision 和 Audit 不得互相替代。详细模型参见 `domain/approval-and-dual-control.md`。

## 12. Identity、Audit、Notification 与 Reporting

### User／Role／Capability／DataScope

用户、角色、具体能力和数据范围必须区分。角色只是能力集合。

### AuditEvent

记录关键命令、配置变化、审批、数据修正、人工干预和权限操作。

### Notification

表示由风险、数据、交易、审批或系统事件生成的通知及阅读状态。通知不重新判断业务事实。

### ReportDefinition／ReportVersion

表示报表定义、生成任务和正式版本。报表读取权威事实或稳定 Read Model，不形成第二套交易事实。

## 13. Backend Read Model

Backend Read Model 为页面查询形成只读投影，例如：

- TradingWorkspaceReadModel。
- StrategyPnlOverviewReadModel。
- StrategyCapitalOverviewReadModel。
- OpenExecutionBatchReadModel。
- RiskAndDataQualitySummaryReadModel。

规则：

- 不拥有独立写入入口。
- 不重新定义损益、风险或订单规则。
- 可以缓存和预计算。
- 必须包含数据时间、来源版本和 DataQualityStatus。
- 可以从权威事实重建。

详细规范参见 `backend/query-and-read-models.md`。

## 14. 核心关系

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

## 15. 时间、数值和状态

### 时间

根据业务含义区分：

- 业务日期。
- 事件发生时间。
- 外部来源时间。
- 平台接收时间。
- 计算和更新时间。
- 数据截止时间。

### 数值

金额、价格、数量、比例和汇率保留：

- 原始数值。
- 单位和币种。
- 精度。
- 来源和时间。

正式金融计算不得依赖 JavaScript 二进制浮点数完成最终结果。

### 状态

各对象状态以 `domain/status-enums-and-lifecycles.md` 为唯一来源。至少独立定义：

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
- DeploymentEnvironment。
- TradingMode。
- TradingPermissionState。

## 16. 前端、后端和接口使用规则

### 前端

- DTO 通过 Adapter 转为 Domain Model 或 View Model。
- 不通过格式化字符串推断业务状态。
- 不把页面 Mock 和本地缓存作为最终事实。

### 后端

- 领域对象不等同于数据库表。
- 业务规则围绕领域身份、所有权和生命周期执行。
- 核心状态变化可追溯。
- 模块通过应用接口、领域服务和事件协作。

### 接口

- API DTO 可以适配客户端需求。
- 查询、命令和事件使用相同稳定业务 ID。
- 外部系统对象通过 Adapter 转换。
- Backend Read Model 与命令写模型分开。

## 17. 唯一来源

| 内容 | 唯一来源 |
|---|---|
| 状态枚举 | `domain/status-enums-and-lifecycles.md` |
| 审批和 Maker／Checker | `domain/approval-and-dual-control.md` |
| 后端 Read Model | `backend/query-and-read-models.md` |
| 研究与交易数据分类 | `backend/research-data-and-content-boundaries.md` |
| 模块所有权 | `backend/service-boundaries.md` |
| 交易可靠性 | `backend/trading-execution-reliability.md` |

## 18. 禁止事项

- 不在没有真实需求时建立庞大 DDD 框架。
- 不提前定义大量无法验证的字段。
- 不把页面卡片结构直接当作领域对象。
- 不把 Order 和 Fill 合并。
- 不把 TradeCommand 和 ExecutionBatch 生命周期合并。
- 不把 Account、BalanceSnapshot、StrategyAccountBinding 和 CapitalAllocation 混为一体。
- 不把前端注册表当作真实策略运行状态。
- 不把 Backend Read Model 当作数据权威或写入入口。
- 不把 Strategy Economic Ledger 误作完整财务会计总账。

## 19. 验收标准

- 相同业务对象在前端、后端和接口中使用稳定身份。
- StrategyAccountBinding 由 Strategy 拥有并引用 Account。
- 订单、成交、执行批次、持仓、暴露和损益边界明确。
- DeploymentEnvironment、TradingMode 和交易权限结果分开。
- Backend Read Model 与 Domain Model、API DTO 和 View Model 分开。
- Mock 或外部接口可以通过 Adapter 转换。
- 权限、审批、风险和审计各自具有明确职责。
