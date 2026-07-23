# Platform V6+ 全平台统一领域模型

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：全平台公共领域蓝图

配套约束：

- `../platform-target-architecture.md`
- `domain-overview.md`
- `../domain-model-boundaries.md`
- `status-enums-and-lifecycles.md`
- `../backend/service-boundaries.md`
- `../backend/storage-ledger-and-audit.md`
- `../backend/execution-runtime-and-gateway.md`
- `../decisions/ADR-008-总体逻辑分层与独立交易Runtime.md`
- `../decisions/ADR-009-最小基金组合层级.md`

## 1. 文档定位

本文是 Platform Backend、Execution Runtime、API、数据库、导入、报表和前端适配共同遵守的统一领域蓝图。

本文重点定义：

- 核心对象的稳定身份。
- 对象之间的正式关系。
- 每个对象的主责领域和数据权威。
- Command、Event、事实、状态、快照和派生结果的区别。
- Fund、Portfolio、Book、Strategy、Account、Trading、Risk 和 PnL 的完整链路。
- Platform Backend、Runtime、外部交易系统和 Read Model 的边界。

本文不是：

- 数据库 ERD。
- API DTO 文档。
- Vue View Model。
- 外部交易所或 MT5 对象模型。
- 完整基金行政管理和法定基金会计模型。

字段细节和状态枚举继续由专项文档负责；本文作为对象关系和所有权的最高层蓝图。

## 2. 统一领域总图

```text
LegalEntity
  ├─ manages Fund
  └─ owns / controls Account

Fund
  └─ contains Portfolio
       └─ contains Book
            ├─ grants StrategyAllocation
            └─ governs StrategyInstance

StrategyDefinition
  └─ StrategyVersion
       └─ StrategyInstance
            ├─ belongs to Book
            ├─ receives StrategyAllocation
            ├─ uses Account through StrategyAccountBinding
            ├─ produces SignalRecord，适用时
            ├─ accepts TradeIntent / TradeCommand
            ├─ owns strategy attribution context
            └─ participates in Risk / PnL / Reconciliation

Venue / Broker / ExternalSystem
  ├─ exposes Instrument through InstrumentMapping
  ├─ hosts Account
  └─ connects through GatewayRuntime

TradeIntent
  └─ TradeCommand
       └─ ExecutionBatch
            └─ ExecutionPlan
                 └─ LegInstruction
                      └─ platform Order
                           ├─ ExternalOrderReference
                           └─ Fill / Deal
                                ├─ changes Position
                                └─ creates EconomicEvent

Position / Balance / Margin / External Facts
  ├─ form ExposureSnapshot
  ├─ feed RiskSnapshot / RiskDecision
  ├─ feed ReconciliationResult
  └─ feed Valuation / PnLResult

EconomicEvent
  └─ LedgerEntry
       └─ PnLResult
            └─ PnLAttributionItem

ApprovalPolicy
  └─ ApprovalRequest
       └─ ApprovalDecision
            └─ ApprovalGrant
                 └─ authorizes target Command

RuntimeDefinition
  └─ RuntimeInstance
       └─ RuntimeSession
            └─ GatewayRuntime
                 └─ WorkerInstance
                      └─ External Session / API / Terminal

Authoritative Domain Facts
  └─ Projection
       └─ Backend Read Model
            └─ API DTO
                 └─ Frontend View Model
```

## 3. 领域分组与主责

| 领域 | 核心对象 | 主责 |
|---|---|---|
| Organization and Fund | LegalEntity、Fund、Portfolio、Book | Fund／Portfolio Domain |
| Strategy | StrategyDefinition、StrategyVersion、StrategyInstance、StrategyAllocation、StrategyAccountBinding | Strategy Domain |
| Market and Instrument | Venue、Instrument、ContractSpecification、InstrumentMapping、QuoteSnapshot、FxRateSnapshot | Execution Market Data |
| Account and Position | Account、AccountOwnership、AccountPurpose、BalanceSnapshot、MarginSnapshot、Position、PositionSnapshot | Account and Position |
| Trading and Execution | TradeIntent、TradeCommand、ExecutionBatch、ExecutionPlan、LegInstruction、Order、Fill、Deal、ManualIntervention | Trading and Execution |
| Runtime and Gateway | RuntimeDefinition、RuntimeInstance、RuntimeSession、GatewayDefinition、GatewayRuntime、WorkerInstance | Execution Runtime／Runtime Coordination |
| Risk | RiskRule、RiskLimit、RiskSnapshot、RiskDecision、RiskEvent、GlobalTradingBlock | Risk |
| Approval | ApprovalPolicy、ApprovalRequest、ApprovalDecision、ApprovalGrant | Approval and Control |
| Reconciliation | ReconciliationJob、ReconciliationResult、ReconciliationDifference、DataCorrectionRecord | Reconciliation and Data Quality |
| Economic Ledger and PnL | EconomicEvent、LedgerEntry、ValuationSnapshot、PnLResult、PnLAttributionItem、AdjustmentEntry | PnL and Strategy Economic Ledger |
| IAM and Governance | User、Role、Capability、DataScope、AuditEvent、ConfigurationVersion | IAM／Audit／Configuration |
| Query and Reporting | Backend Read Model、ReportDefinition、ReportVersion | Query and Read Models／Reporting |

## 4. Organization、Fund、Portfolio 与 Book

### 4.1 LegalEntity

表示具有法律、运营、管理或账户所有权意义的主体。

稳定身份：

- `legalEntityId`。

主要关系：

- 管理一个或多个 Fund。
- 拥有或控制一个或多个 Account。
- 作为权限、数据范围和报表归属引用。

不负责：

- 保存交易所余额。
- 表达策略版本。
- 直接承载交易订单。

### 4.2 Fund

表示需要独立管理、风险汇总、绩效归属和报告的基金或内部投资产品。

稳定身份：

- `fundId`。

主要关系：

- 由 LegalEntity 管理。
- 包含一个或多个 Portfolio。
- 定义 Reporting Currency 和 Valuation Calendar。
- 作为基金级风险、绩效和报表聚合边界。

当前边界：

- Fund 是正式主档。
- 当前不包含 Investor、ShareClass、Subscription 和 Redemption。
- 未建立完整估值和份额流程前，不产生正式 Fund NAV。

### 4.3 Portfolio

表示 Fund 下可独立进行资产、资金、风险和绩效管理的组合。

稳定身份：

- `portfolioId`。

主要关系：

- 必须属于一个 Fund。
- 包含一个或多个 Book。
- 拥有 Reporting Currency、风险边界和资金边界。
- 可以形成 Portfolio 级 Exposure、PnL 和报表。

初期每个 Fund 至少建立一个默认 Portfolio。

### 4.4 Book

表示 Portfolio 下的执行、核算或管理分区。

稳定身份：

- `bookId`。

主要关系：

- 必须属于一个 Portfolio。
- 管理一个或多个 StrategyInstance。
- 承载 StrategyAllocation、风险预算和绩效归属上下文。

第一阶段规则：

- 每个 Portfolio 默认一个 Default Book。
- 只有出现真实隔离需求时才新增独立 Book。
- 不提前建设复杂 Book 间资金划转和会计合并。

## 5. Strategy 领域

### 5.1 StrategyDefinition

表示平台纳管的一项稳定策略定义。

稳定身份：

- `strategyId`。

表达：

- 正式名称。
- 策略分类。
- 平台执行或外部执行类型。
- 单腿、双腿或多腿结构。
- 产品能力范围。

不表达：

- 当前运行状态。
- 当前账户余额。
- 当前参数版本。

### 5.2 StrategyVersion

表示策略逻辑、参数口径、执行规则、PnL 规则和风险规则的正式版本。

稳定身份：

- `strategyVersionId`。

规则：

- 历史交易始终关联交易发生时的 StrategyVersion。
- 新版本不得无痕重解释历史结果。
- 版本有生效时间、失效时间、状态和替代关系。

### 5.3 StrategyInstance

表示某个 StrategyVersion 在具体 Fund／Portfolio／Book、环境、交易模式和账户上下文中的实例。

稳定身份：

- `strategyInstanceId`。

必须关联：

- StrategyDefinition。
- StrategyVersion。
- Book。
- DeploymentEnvironment。
- TradingMode。

可以关联：

- StrategyAllocation。
- StrategyAccountBinding。
- ExternalExecutionProfile。
- Runtime／Gateway 执行目标。

StrategyInstance 不等于进程实例，也不等于交易账户。

### 5.4 StrategyAllocation

表示 Portfolio／Book 向 StrategyInstance 分配的资金、名义额度或风险预算。

稳定身份：

- `strategyAllocationId`。

不等于：

- Account Balance。
- 真实 Cash Transfer。
- StrategyAccountBinding。
- Position 或 PnL。

### 5.5 StrategyAccountBinding

表示 StrategyInstance 被允许如何使用某个 Account。

稳定身份：

- `strategyAccountBindingId`。

至少表达：

- AccountId。
- 账户角色。
- 允许的 Instrument 和动作。
- 额度和 TradingMode。
- 生效和失效时间。
- 审批和审计引用，适用时。

Strategy 拥有绑定关系；Account 拥有账户主档。

### 5.6 SignalRecord

表示策略观察、候选机会或正式信号。

SignalRecord 不等于 TradeCommand、Order、Fill 或 Position。

适用于抄底等信号与执行分离的策略。

### 5.7 ExternalExecutionProfile

表示外部交易终端、Broker、账户、Magic Number、Tag、日界线、费用和归属规则。

适用于抄底、短线交易员 L 和短线交易员 W。

不保存完整 Secret 或密码。

## 6. Market、Venue 与 Instrument

### 6.1 Venue

表示交易所、Broker、市场或外部执行场所的稳定身份。

稳定身份：

- `venueId`。

Venue 不等于 GatewayRuntime；同一 Venue 可以通过不同 GatewayDefinition 和 Runtime 接入。

### 6.2 Instrument

表示平台标准化的可交易或可观察标的。

稳定身份：

- `instrumentId`。

至少表达：

- 基础资产和计价资产。
- 产品类型。
- 交易币种和结算币种。
- 标准单位。
- 生命周期和可交易状态。

页面名称、TradingView symbol、MT5 symbol 和交易所 symbol 均不是 InstrumentId。

### 6.3 InstrumentMapping

表示 Instrument 与某个 Venue、Broker、Gateway 或数据源 symbol 的映射。

至少包含：

- InstrumentId。
- ExternalSystem／Venue。
- 外部 symbol。
- 市场类型。
- 作用范围和版本。
- 生效时间。

### 6.4 ContractSpecification

表达合约乘数、Contract Size、Lot Step、Tick Size、数量精度、价格精度、交易时段和订单限制。

合约规格必须版本化，不能假设所有 XAUUSD 或永续合约相同。

### 6.5 QuoteSnapshot 与 FxRateSnapshot

QuoteSnapshot 表示某一时点的行情事实；FxRateSnapshot 表示汇率事实。

二者均必须保留：

- 来源时间。
- 接收时间。
- 来源。
- 质量状态。
- 精度和单位。

## 7. Account、Ownership、Balance 与 Position

### 7.1 Account

表示外部交易所、Broker、经纪商或托管环境中的稳定账户主档。

稳定身份：

- `accountId`。

Account 不等于 StrategyInstance，也不等于 Fund。

### 7.2 AccountOwnership

表示账户由哪个 LegalEntity 或 Fund 拥有、控制或管理。

必须与 StrategyAccountBinding 分开。

### 7.3 AccountPurpose

表示账户用途，例如：

- trading。
- hedge。
- settlement。
- custody。
- observation_only。

### 7.4 BalanceSnapshot 与 MarginSnapshot

表示外部账户某一时点的余额、权益、可用资金、冻结资金和保证金事实。

快照必须保留外部来源和质量状态。

### 7.5 Position

表示 Account 在 Instrument 上的当前标准化持仓状态。

稳定身份：

- `positionId`。

Position 可以由：

- Fill 推导。
- 外部同步。
- 对账后确认。

必须记录来源。平台推导与外部持仓不一致时进入 Reconciliation，不静默覆盖。

### 7.6 PositionSnapshot 与 StrategyPositionGroup

PositionSnapshot 保存某时点持仓事实。

StrategyPositionGroup 将多个 Position 归入同一套利组合、TradeCycle 或 ExecutionBatch，但不形成新的外部持仓。

## 8. Trading 与 Execution

### 8.1 标准链路

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
→ Position / EconomicEvent
```

### 8.2 TradeIntent

表示用户或策略希望完成的业务目标。

例如：建立一组资费套利头寸。

TradeIntent 可以在命令受理前存在，不代表已经获准执行。

### 8.3 TradeCommand

表示平台对改变交易状态请求的受理记录。

稳定身份：

- `tradeCommandId`。

负责：

- 幂等。
- 权限。
- 参数。
- 风险和审批检查。
- 接受或拒绝。
- 创建或关联 ExecutionBatch。

TradeCommand accepted 不等于外部交易成功。

### 8.4 ExecutionBatch

表示为完成同一业务目标组织的一组交易腿、订单和异常处理。

稳定身份：

- `executionBatchId`。

拥有：

- ExecutionBatchStatus。
- ExecutionBalanceStatus。
- ExposureStatus。
- ManualIntervention。
- 结果未知和恢复上下文。

### 8.5 ExecutionPlan

表示 ExecutionBatch 如何执行。

至少可以表达：

- parallel／sequential。
- activeLeg／passiveLeg。
- orderTypePolicy。
- maxSlippage。
- maxExposureTime。
- timeoutPolicy。
- residualPolicy。
- fallbackPolicy。
- planVersion。

ExecutionPlan 是业务执行计划，不是 Runtime 算法进程。

### 8.6 LegInstruction

表示单条交易腿的目标指令。

稳定身份：

- `legInstructionId`。

包含 AccountId、InstrumentId、方向、数量、价格政策和目标 Gateway。

### 8.7 Order

表示平台创建并跟踪的一张标准化订单。

稳定身份：

- `platformOrderId`。

规则：

- 外部提交前必须预创建。
- 平台 OrderStatus 与外部状态分开。
- 一张 Order 可以产生多笔 Fill。
- 结果未知不能被直接标记失败后重新下单。
- MT5 场景下 Order 不等于 Deal，不能单独形成成交、持仓和 PnL。

### 8.8 ExternalOrderReference

建立：

```text
platformOrderId
↔ clientOrderId / Magic / Comment / Tag
↔ externalOrderId
```

必须记录作用域、可靠等级和映射证据。

### 8.9 Fill／Deal

表示已经发生的外部成交事实。

稳定身份：

- `fillId`。
- `dealId`，适用于 MT5 或其他以 Deal 为核心事实的外部系统。

规则：

- 原则上追加保存。
- 不因 Order 状态变化而覆盖。
- 保留外部成交 ID、价格、数量、费用、发生时间和接收时间。
- MT5 Deal 必须保留 Broker server time、Account、Gateway、Position 关联、Commission、Swap 和原始记录引用。

### 8.10 ManualIntervention

记录人工确认、补单、撤单、接受偏差、关联外部订单、终止执行和紧急减险。

所有人工操作必须权限校验、理由码、审批和审计，适用时。

## 9. Runtime 与 Gateway

### 9.1 RuntimeDefinition、Instance 与 Session

- RuntimeDefinition：可部署 Runtime 类型和版本。
- RuntimeInstance：稳定注册和配置身份。
- RuntimeSession：一次具体进程生命周期。

StrategyInstance 不等于 RuntimeInstance。

### 9.2 GatewayDefinition 与 GatewayRuntime

- GatewayDefinition：某类 Adapter、SDK 和能力定义。
- GatewayRuntime：某 Gateway 在某 Runtime 中的实际运行实例。

GatewayRuntime 必须声明 GatewayCapability，不能仅使用 connected 表达全部能力。

### 9.3 WorkerInstance

表示 MT5、Crypto 或后续 CTP 的具体隔离运行单元。

Worker 负责外部 Session、订单发送、回报、查询和同步，不拥有 Strategy、Risk 和 PnL 业务模型。

### 9.4 Runtime Command 与 Event

Platform Backend 与 Runtime 通过稳定 Envelope 协作：

- 至少一次传输。
- Command 幂等。
- Event Inbox 去重。
- 允许重复、延迟、乱序和补发。
- 不以 HTTP／RPC 超时判断外部失败。

### 9.5 Runtime Journal

Runtime Journal 保存 Command 去重、待发送 Event、外部引用和恢复位置。

Runtime Journal 不是平台永久业务数据库。

## 10. Exposure 与 Risk

### 10.1 ExposureSnapshot

表示某时点的方向、名义价值、Delta、汇率、集中度或残腿暴露。

可以按：

- Fund。
- Portfolio。
- Book。
- StrategyInstance。
- Account。
- Instrument。

形成聚合。

### 10.2 RiskRule 与 RiskLimit

- RiskRule 定义判断逻辑。
- RiskLimit 定义阈值、作用范围和版本。

作用范围必须使用稳定 ID，不能只按页面名称配置。

### 10.3 RiskSnapshot

表示某时点的风险指标和输入数据状态。

### 10.4 RiskDecision

表示针对某个 Command、对象或当前状态的结构化风险判断。

RiskDecision 不等于 ApprovalDecision，也不等于权限判断。

### 10.5 RiskEvent 与 GlobalTradingBlock

RiskEvent 表示已发生的风险事实。

GlobalTradingBlock 表示平台、环境、模式、Gateway、账户、策略或标的级新增风险阻断。

阻断默认禁止扩大风险，不等于自动平仓。

## 11. Approval、Permission 与 Audit

### 11.1 User、Role、Capability 与 DataScope

- User 表示用户身份。
- Role 是 Capability 的集合。
- Capability 表示可执行动作。
- DataScope 表示可访问 Fund、Portfolio、Book、StrategyInstance 和 Account 的范围。

还必须区分 EnvironmentScope 和 TradingModeScope。

### 11.2 ApprovalPolicy、Request、Decision 与 Grant

- ApprovalPolicy：什么操作需要审批。
- ApprovalRequest：针对具体目标和参数的申请。
- ApprovalDecision：审批人的决定。
- ApprovalGrant：在对象、参数、环境、模式和有效期内可执行的授权。

ApprovalGrant 不替代 Capability、RiskDecision 或 AuditEvent。

### 11.3 AuditEvent

记录谁在什么上下文对什么对象执行了什么操作，以及结果如何。

关键对象必须通过 requestId、traceId、correlationId 和 causationId 串联。

## 12. Reconciliation 与 Data Quality

### 12.1 ReconciliationJob

定义一次对账范围、时间和数据来源。

### 12.2 ReconciliationResult 与 Difference

可以核对：

- Order。
- Fill。
- Deal。
- Position。
- Balance。
- Margin。
- Funding／Swap／Fee。
- EconomicEvent。
- PnL。

差异不直接覆盖原始事实。

### 12.3 DataCorrectionRecord

记录修正前、修正后、原因、操作者、审批和影响范围。

### 12.4 DataQualityState

至少表达：

- complete。
- partial。
- delayed。
- stale。
- conflicting。
- missing。
- not_connected。
- unavailable。
- unverified。

缺失不能静默当零。

## 13. EconomicEvent、Ledger 与 PnL

### 13.1 EconomicEvent

表示已经发生并影响资金、持仓、费用或策略经济结果的业务事实。

稳定身份：

- `economicEventId`。

事件类型包括：

- Fill economic effect。
- Fee／Commission。
- FundingSettlement。
- Swap。
- Borrow Interest。
- Deposit／Withdrawal。
- Transfer。
- FX Revaluation。
- Settlement。
- Adjustment。

### 13.2 LedgerEntry

表示 EconomicEvent 对策略经济账本的结构化影响。

当前 Strategy Economic Ledger 不等于完整 Finance Ledger。

### 13.3 ValuationSnapshot

表示某个估值时点的价格、汇率、持仓和估值结果。

必须保留：

- valuationDate／valuationTime。
- 价格来源和质量。
- FX 来源。
- 计算版本。

### 13.4 PnLResult

表示按正式规则计算的版本化派生结果。

可以按：

- StrategyInstance。
- Book。
- Portfolio。
- Fund，只有具备适用数据和规则时。

计算。

必须关联：

- StrategyVersion。
- CalculationVersion。
- 数据截止时间。
- Reporting Currency。
- FX 来源。
- DataQualityState。
- RecalculationRun。

### 13.5 PnLAttributionItem

表示策略专项收益、成本和损失归因。

三类套利可以拥有不同归因树，但都归入统一 PnLResult。

### 13.6 AdjustmentEntry

通过追加调整和冲销修正经济结果，不无痕覆盖 EconomicEvent。

### 13.7 Fund NAV 边界

正式 Fund NAV 还需要：

- 估值政策。
- 现金和应计费用。
- 份额和申赎。
- 复核和锁定。
- 发布和替代流程。

当前 Strategy PnL、Book PnL 和 Portfolio Performance 不能自动视为 Fund NAV。

### 13.8 StrategyNavSnapshot

表示 StrategyInstance 在固定时间生成的策略运行净值快照。

V1 默认公式：

```text
nav = equity / capitalBase
```

规则：

- 默认计价 USDT。
- 必须保留 snapshotTime、valuationDate、dataAsOf、generatedAt、source 和 DataQualityState。
- 资费套利和跨所价差优先落地。
- 海内外价差、抄底、短线交易员 L/W 在数据未接入或未核对时只显示 estimated、missing、not_connected 或 unverified。
- StrategyNavSnapshot 不等于正式 Fund NAV。

## 14. Query、Read Model 与 Report

### 14.1 Backend Read Model

为页面和查询形成可重建投影，例如：

- FundOverviewReadModel。
- PortfolioRiskReadModel。
- TradingWorkspaceReadModel。
- StrategyPnlOverviewReadModel。
- OpenExecutionBatchReadModel。
- AccountCapitalOverviewReadModel。

Read Model 不接受领域写入。

### 14.2 ReportDefinition 与 ReportVersion

正式报表读取权威事实或稳定 Read Model。

报表版本必须保留数据截止时间、口径和生成版本，不覆盖历史正式版本。

## 15. 标准值对象

### 15.1 Money

```text
amount: Decimal
currency: CurrencyCode
```

### 15.2 Price

```text
value: Decimal
quoteCurrency: CurrencyCode
unit: PriceUnit
precision: integer
```

### 15.3 Quantity

```text
value: Decimal
unit: QuantityUnit
precision: integer
```

### 15.4 Rate

```text
value: Decimal
rateType
period / interval，适用时
```

### 15.5 TimeContext

根据业务含义分别保存：

- occurredAt。
- externalTime。
- receivedAt。
- processedAt。
- businessDate。
- tradingDay。
- settlementDate。
- valuationDate。
- dataAsOf。

页面格式化字符串不能作为领域原始值。

## 16. 数据权威矩阵

| 数据 | 权威主体 |
|---|---|
| LegalEntity、Fund、Portfolio、Book | Fund／Portfolio Domain |
| StrategyDefinition、Version、Instance、Allocation、Binding | Strategy Domain |
| Instrument、ContractSpecification、Mapping | Execution Market Data |
| 平台 TradeCommand、ExecutionBatch、Plan、Order、Fill、Deal | Trading and Execution |
| 外部订单、成交、余额和持仓原始事实 | External System；平台保存标准化事实 |
| Runtime、Gateway、Worker 实时状态 | Execution Runtime；平台保存控制面投影 |
| Account 主档、Balance、Margin、Position | Account and Position |
| RiskRule、Decision、Event、Block | Risk |
| Approval | Approval and Control |
| Reconciliation 和 Data Quality | Reconciliation and Data Quality |
| EconomicEvent、LedgerEntry、PnLResult、StrategyNavSnapshot | PnL and Strategy Economic Ledger |
| AuditEvent | Audit |
| Backend Read Model | Query and Read Models，可重建 |
| Frontend State | 非权威 |
| Mock | 非权威测试来源 |

## 17. 关键不变量

1. 每个核心对象只有一个主责领域。
2. Fund、Portfolio、Book、StrategyInstance 和 Account 不得混为一个对象。
3. StrategyAllocation 不等于 Account Balance。
4. StrategyAccountBinding 不等于 Account Ownership。
5. StrategyVersion 不得无痕重解释历史交易。
6. TradeCommand accepted 不等于交易完成。
7. ExecutionBatchStatus、ExecutionBalanceStatus 和 ExposureStatus 分开。
8. platformOrderId 在外部提交前创建。
9. 一张 Order 可以有多笔 Fill；MT5 Order 不等于 Deal。
10. Fill、Deal、FundingSettlement 和 Swap 等事实原则上追加保存。
11. Runtime OMS 和 Journal 不成为平台永久权威。
12. 外部 DTO 不进入核心领域。
13. 缺失数据不静默当零。
14. 修正不覆盖原始事实。
15. PnLResult 必须版本化并可重现。
16. Strategy PnL 不等于 Fund NAV。
17. Read Model 和前端状态不接受业务写入。
18. 权限、审批、风险和审计不能互相替代。

## 18. 初期最小实现集

V1 最小实现集需要支持 Fake Gateway、首个 Crypto 真实 API 模拟/测试链路，以及首个 MT5 Demo/Worker 链路。以下对象用于验证资费套利和跨所价差主链路：

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
Deal
Position
BalanceSnapshot
PositionSnapshot
EconomicEvent
PnLResult
StrategyNavSnapshot
RiskDecision
ReconciliationRun
ReconciliationDifference
RecoveryRun
RuntimeInstance
GatewayRuntime
WorkerInstance
AuditEvent
```

暂不要求实现：

- Investor。
- ShareClass。
- Subscription／Redemption。
- 完整 Fund NAV。
- 完整 Finance Ledger。
- 复杂多 Book 管理。
- CTP、国内真实交易、平今/平昨、换月和结算级对账。
- 客户/投资者权限、客户门户和份额系统。
- 金融AI分析专项对象。

## 19. 从领域模型到工程

### Platform Backend

每个领域模块至少建立：

```text
module
├─ domain
├─ application
├─ ports
├─ infrastructure
└─ api / projection
```

不要求为了形式建立复杂 DDD 框架，但必须保持对象所有权和依赖方向。

### Execution Runtime

只实现 Runtime、Gateway、Worker、Journal、Command 和 Event 契约，不复制 Platform Domain。

### Frontend

前端通过 Repository Interface 和 Adapter 使用 API DTO，不直接依赖数据库对象或 Runtime DTO。

### Database

数据库表根据本模型设计，但允许为了事务、索引和查询进行物理拆分；物理表不反向决定领域边界。

## 20. 变更规则

新增或改变核心对象时必须检查：

- 是否已有主责领域。
- 是否与现有对象语义重复。
- 是否形成第二套权威。
- 是否需要新状态或生命周期。
- 是否影响 Fund／Portfolio／Book／Strategy／Account 关系。
- 是否影响 API、Runtime Contract、对账、PnL、Risk 和 Audit。
- 是否需要 ADR。

对本模型的实质变更必须同步更新：

- `domain-overview.md`。
- `../domain-model-boundaries.md`。
- `status-enums-and-lifecycles.md`，适用时。
- `../backend/service-boundaries.md`。
- API／Runtime Contract，适用时。
