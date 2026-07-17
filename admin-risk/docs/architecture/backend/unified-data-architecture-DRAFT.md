# Platform V6+ 统一数据架构方案

状态：`draft`  
产品基线：Platform V5  
架构讨论版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：全平台数据架构讨论稿  
更新日期：2026-07-17

上位与配套约束：

- `../platform-target-architecture.md`
- `backend-overview.md`
- `service-boundaries.md`
- `storage-ledger-and-audit.md`
- `query-and-read-models.md`
- `execution-runtime-and-gateway.md`
- `../domain/domain-overview.md`
- `../domain-model-boundaries.md`
- `../domain/status-enums-and-lifecycles.md`
- `../../audit/2026-07-17-基金平台技术负责人全局审视-DRAFT.md`

> 本文用于收敛平台统一数据架构。本文不直接决定 PostgreSQL、TimescaleDB、ClickHouse、Redis、对象存储或消息中间件等具体产品；确认后的对象、权威、时间和修正规则需要同步进入 active 领域、存储和接口文档，并在必要时形成 ADR。

## 1. 文档目标

本文重点回答：

1. 平台有哪些数据域，以及每个数据域由谁拥有。
2. Fund、Portfolio／Book、Strategy、Account 和交易事实如何建立稳定关系。
3. 主数据、事实、状态、快照、经济事件、派生结果和 Read Model 如何区分。
4. 金额、数量、价格、费率、币种、单位和时间如何统一表达。
5. 外部交易系统、研究数据源、Runtime 和平台数据库之间谁拥有何种事实。
6. 数据如何进行幂等摄取、修正、重算、对账、版本、保留和归档。
7. Strategy Economic Ledger、未来 NAV 和 Finance Ledger 之间如何保持边界。
8. 初期需要哪些最小对象，哪些完整基金行政管理对象继续延后。

本文不负责：

- 定义具体策略公式，策略公式以六份策略文档为准。
- 确定 V1 范围和开发排期。
- 设计完整投资人、份额和法定基金会计系统。
- 选择数据库、云厂商和数据供应商。
- 决定金融AI分析数据产品。

## 2. 数据架构总原则

### 2.1 单一主责，多个安全读模型

- 每个核心对象只有一个主责领域和权威写入口。
- 多个页面、报表和服务可以读取同一权威事实。
- 跨领域查询通过 Query／Read Model 聚合。
- Read Model、缓存、导出文件和前端状态不形成第二套业务权威。

### 2.2 原始事实不可无痕覆盖

以下事实原则上追加保存或保留完整历史：

- Order 和外部订单状态回报。
- Fill／Deal。
- FundingSettlement、Swap、Commission 和 Fee。
- Account、Balance、Margin 和 Position 外部快照。
- 数据导入批次和原始文件。
- 审批、审计、对账和修正记录。

错误通过：

- DataCorrectionRecord。
- AdjustmentEntry。
- 替代关系。
- 版本化重算。

处理，不直接修改原始事实后假装历史从未发生。

### 2.3 外部事实、平台事实和派生结果分开

- 外部系统拥有其实际订单、成交、账户和持仓事实。
- Runtime 拥有实时连接、请求、回报和恢复位置。
- Platform 拥有标准化业务对象、策略归属和治理状态。
- PnL、风险、NAV 和报表属于版本化派生结果。

### 2.4 业务 ID 与外部 ID 分开

平台必须使用稳定业务 ID：

- `fundId`。
- `portfolioId`。
- `bookId`。
- `strategyDefinitionId`／`strategyId`。
- `strategyVersionId`。
- `strategyInstanceId`。
- `accountId`。
- `instrumentId`。
- `tradeCommandId`。
- `executionBatchId`。
- `platformOrderId`。
- `fillId`。
- `economicEventId`。

外部 ID 单独保存并明确作用域：

```text
externalSystem
+ venue / broker
+ account
+ externalObjectType
+ externalId
```

### 2.5 计算必须可重现

任何正式派生结果至少能够追溯：

- 输入数据版本和截止时间。
- StrategyVersion。
- 计算规则和版本。
- 计价币种和汇率。
- 日历和 businessDate。
- 数据质量和完整度。
- 生成时间和生成者。
- 替代或重算关系。

## 3. 最小基金与投资组合层级

### 3.1 推荐最小层级

为避免未来所有数据直接挂在策略展示名称和交易账户上，建议正式引入以下最小层级：

```text
LegalEntity
  ↓ owns / manages
Fund
  ↓ contains
Portfolio
  ↓ optional execution or accounting subdivision
Book
  ↓ allocates
StrategyInstance
  ↓ uses through binding
Account
```

### 3.2 LegalEntity

表示具备法律、运营或账户所有权意义的主体，例如：

- 管理公司。
- 基金主体。
- 专项投资主体。
- 其他经正式确认的账户所有者。

候选字段：

- `legalEntityId`。
- 正式名称和简称。
- 主体类型。
- 注册地或司法辖区，适用时。
- 基础币种。
- 状态。
- 生效和失效时间。

当前不在普通页面展示完整敏感注册信息。

### 3.3 Fund

Fund 表示需要独立管理、估值、风险和报告的基金或投资产品。

候选字段：

- `fundId`。
- LegalEntityId。
- 正式名称和代码。
- Fund 类型。
- Reporting Currency。
- Valuation Calendar。
- Inception Date。
- 状态。
- 管理主体、托管人、行政管理人等引用，后续。

当前可以只建立内部基金／产品主档，不建设投资人和份额系统。

### 3.4 Portfolio

Portfolio 表示 Fund 下可独立进行资产、风险、绩效和资金管理的组合。

候选字段：

- `portfolioId`。
- FundId。
- 名称和代码。
- Base／Reporting Currency。
- 组合类型。
- 当前状态。
- 资金和风险边界。

一个 Fund 可以具有一个默认 Portfolio，也可以后续扩展多个 Portfolio。

### 3.5 Book

Book 是可选的执行、核算或管理分区，例如：

- Funding Arbitrage Book。
- Gold Spread Book。
- Trader L Book。
- Trader W Book。

候选字段：

- `bookId`。
- PortfolioId。
- Book 类型和用途。
- Reporting Currency。
- 负责人或数据范围引用。
- 状态和有效期。

初期可以使用一个 StrategyInstance 对应一个 Book，或由多个策略实例共享一个 Book；具体基数由后续业务确认。

### 3.6 StrategyAllocation

StrategyAllocation 表达某个 Fund／Portfolio／Book 向 StrategyInstance 分配的资金、额度或风险预算。

它不等于：

- Account Balance。
- 实际 Cash Transfer。
- StrategyAccountBinding。
- PnL。

候选字段：

- `strategyAllocationId`。
- FundId／PortfolioId／BookId。
- StrategyInstanceId。
- 分配类型。
- 金额、币种或风险额度。
- 生效和失效时间。
- 审批和版本。

### 3.7 Account Ownership 与 StrategyAccountBinding

必须区分：

- Account Ownership：账户法律或运营归属。
- Account Purpose：账户用途。
- StrategyAccountBinding：策略实例获准如何使用账户。
- StrategyAllocation：策略预算和资金分配。

推荐关系：

```text
LegalEntity / Fund
→ owns or controls Account

Portfolio / Book
→ receives allocation

StrategyInstance
→ receives StrategyAllocation
→ uses Account through StrategyAccountBinding
```

账户可以被多个策略共享，但必须：

- 有明确额度和用途。
- 能够完成交易和经济事件归属。
- 避免重复统计余额和持仓。
- 对无法直接归属的结果进入分摊或人工处理。

## 4. 当前延后的完整基金行政管理对象

以下对象建议预留命名和边界，但当前不进入正式开发主线：

- Investor。
- ShareClass。
- Subscription。
- Redemption。
- Transfer of Interest。
- Capital Call／Distribution，适用时。
- Fund Fee Accrual。
- Administrator Statement。
- Custodian Statement。
- Investor Statement。
- 法定 NAV 发布和份额登记。

暂缓不代表未来将这些能力塞进 Strategy、Account 或 Finance 的现有对象中。

## 5. 数据域划分

### 5.1 Identity、Permission 与 Governance

拥有：

- User。
- Role。
- Capability。
- DataScope。
- EnvironmentScope。
- TradingModeScope。
- Session。
- ApprovalPolicy／Request／Decision／Grant。
- AuditEvent。

### 5.2 Fund、Portfolio 与 Allocation

候选拥有：

- LegalEntity。
- Fund。
- Portfolio。
- Book。
- StrategyAllocation。
- AccountOwnership。

该领域是否独立为模块，需要后续 ADR；初期可以作为 Platform Backend 内独立逻辑模块。

### 5.3 Strategy

拥有：

- StrategyDefinition。
- StrategyVersion。
- StrategyInstance。
- StrategyAccountBinding。
- StrategyParameterSet。
- ExternalExecutionProfile。
- SignalRecord，适用时。

### 5.4 Market and Reference Data

拥有或治理：

- Venue。
- Broker。
- Instrument。
- InstrumentMapping。
- ContractSpecification。
- Currency。
- UnitDefinition。
- TradingCalendar。
- TradingSession。
- QuoteSnapshot。
- FundingRateSnapshot。
- FxRateSnapshot。
- MarketDataQuality。

### 5.5 Trading and Execution

拥有：

- TradeIntent。
- TradeCommand。
- ExecutionBatch。
- ExecutionPlan。
- LegInstruction。
- Order。
- Fill。
- ManualIntervention。
- ExecutionException。
- ExternalOrderReference。

### 5.6 Account and Position

拥有：

- Account 主档。
- AccountCapability／Restriction。
- BalanceSnapshot。
- MarginSnapshot。
- Position 当前状态。
- PositionSnapshot。
- CapitalFlow，若属于交易账户资金事实。

### 5.7 Risk

拥有：

- RiskRule。
- RiskLimit。
- RiskSnapshot。
- RiskDecision。
- RiskEvent。
- RiskResolution。
- GlobalTradingBlock。
- ViolationRecord。

### 5.8 Reconciliation and Data Quality

拥有：

- ReconciliationRun／Job。
- ReconciliationResult。
- ReconciliationDifference。
- DataQualityState。
- DataCorrectionRecord。
- ImportBatch。
- SourceRecordReference。

### 5.9 PnL and Strategy Economic Ledger

拥有：

- EconomicEvent。
- LedgerEntry。
- AdjustmentEntry。
- ValuationSnapshot。
- PnLResult。
- PnLAttribution。
- TradeCycle 等派生分析对象。

### 5.10 Research Data

拥有：

- ResearchSeries。
- ResearchObservation。
- ResearchRevision。
- DerivedResearchIndicator。
- ResearchDatasetVersion。
- ResearchDataQuality。

### 5.11 Content and Calendar

拥有：

- CalendarEvent。
- NewsContent。
- StoryCluster。
- WealthOpportunity。
- SourceReference。
- ContentRevision。

### 5.12 Operations and Configuration

拥有：

- RuntimeDefinition／Instance／Session 投影。
- GatewayDefinition／Runtime 投影。
- WorkerDefinition／Instance 投影。
- ConfigurationVersion。
- SecretReference。
- RecoveryRun。
- Notification。
- ReportDefinition／Run／Artifact。

Runtime 的实时内部对象仍属于 `execution-runtime`，Platform 只保存治理和查询所需的稳定记录及投影。

## 6. 数据类型统一规范

### 6.1 Money

Money 不使用已格式化字符串作为计算值。

推荐结构：

```text
amount
currency
scale / precision
```

规则：

- 数据库存储使用定点 Decimal／Numeric 语义。
- API 通过字符串传输高精度数值，避免浮点损失，具体规范后续确认。
- 正负号规则由业务对象定义。
- 展示格式由前端 View Model 决定。

### 6.2 Price

至少包含：

- 数值。
- Quote Currency。
- Pricing Unit。
- InstrumentId。
- Price Type：bid、ask、mid、mark、index、settlement、close 等。
- asOfTime。
- source。
- quality。

### 6.3 Quantity

至少包含：

- 数值。
- Quantity Unit。
- InstrumentId。
- 合约数量、基础资产数量、lot 或名义数量类型。

必须避免直接比较：

- BTC 数量与合约张数。
- Crypto 合约数量与金衡盎司。
- MT5 lot 与黄金盎司。
- SHFE 手数与克。

所有比较先经过 ContractSpecification 和 UnitConversion。

### 6.4 Rate

用于：

- Funding Rate。
- Interest Rate。
- Return。
- Fee Rate。
- FX Change。

至少记录：

- 数值。
- 比例或百分比语义。
- 周期。
- 年化方法，适用时。
- 来源时间。

禁止只保存展示后的 `8.5%` 字符串。

### 6.5 Currency 与 FX

Currency 使用稳定 CurrencyCode。

FxRateSnapshot 至少包含：

- baseCurrency。
- quoteCurrency。
- rate。
- direction。
- bid／ask／mid／fixing／settlement。
- source。
- asOfTime 和 receivedAt。
- quality。

USDT／USD 不默认永久固定 1:1，策略可以配置简化口径，但必须记录版本和适用范围。

### 6.6 UnitDefinition 与 UnitConversion

统一管理：

- gram。
- troy ounce。
- kilogram。
- tonne。
- contract。
- lot。
- share／coin／token。

转换规则必须具有：

- conversionRuleId。
- 来源和常量版本。
- 生效时间。
- 舍入规则。
- 适用 Instrument。

## 7. 时间和业务日期模型

### 7.1 时间字段分类

核心事实按需要同时保留：

- `occurredAt`：业务或外部事实实际发生时间。
- `sourceTimestamp`：来源系统给出的时间。
- `receivedAt`：平台或 Runtime 接收时间。
- `recordedAt`：平台持久化时间。
- `publishedAt`：事件发布时间。
- `updatedAt`：当前记录更新时间。
- `asOfTime`：快照或估值适用时间。

### 7.2 时区

- 所有绝对时间保存 UTC 或带偏移 ISO-8601。
- 同时保留原始市场／Broker 时区，适用时。
- 用户展示时区由用户偏好决定。
- MT5 Server Time、交易所时间和北京时间不可混为一体。

### 7.3 businessDate、tradingDay 和 valuationDate

必须区分：

- Calendar Date：自然日。
- businessDate：平台统计和业务归属日期。
- tradingDay：交易所定义交易日。
- settlementDate：结算日期。
- valuationDate：估值和 NAV 日期。

夜盘、跨时区、Funding 结算和 MT5 日界线均需要明确映射规则。

## 8. 数据形态

### 8.1 主数据

相对低频、受治理的对象：

- Fund、Portfolio、Book。
- StrategyDefinition／Version。
- Account。
- Instrument／ContractSpecification。
- RiskRule。
- ConfigurationVersion。

### 8.2 不可变或追加事实

- Fill。
- FundingSettlement。
- Swap／Commission／Fee。
- CapitalFlow。
- ApprovalDecision。
- AuditEvent。
- 原始外部记录。

### 8.3 可变当前状态

- Order 当前状态。
- Position 当前状态。
- Account 当前可用状态。
- StrategyInstanceStatus。
- Runtime／Gateway 当前状态。
- Current Risk Status。

当前状态必须能够由历史事实、外部查询或快照恢复和核对。

### 8.4 快照

- QuoteSnapshot。
- BalanceSnapshot。
- MarginSnapshot。
- PositionSnapshot。
- ExposureSnapshot。
- RiskSnapshot。
- ValuationSnapshot。

快照必须记录 asOfTime、source、quality 和 version。

### 8.5 派生结果

- PnLResult。
- PnLAttribution。
- Strategy NAV／NetValue。
- Risk Metrics。
- Research Indicator。
- Report Artifact。
- Backend Read Model。

派生结果可重建，不覆盖输入事实。

## 9. 数据权威矩阵

| 数据 | 事实来源 | 平台主责 | 说明 |
|---|---|---|---|
| 外部订单和成交 | Exchange／Broker／MT5／CTP | Trading 标准化并持久化 | 外部事实与平台状态均保留 |
| 账户余额和持仓 | 外部账户 | Account | 平台可推导，但必须对账 |
| TradeCommand 和 ExecutionBatch | Platform | Trading | 外部组件不拥有 |
| StrategyVersion 和绑定 | Platform | Strategy | 版本不可无痕修改历史 |
| FundingRate | 市场数据源 | Market Data | 预计费率，不是结算事实 |
| FundingSettlement | 账户账本／外部记录 | PnL／Ledger 摄取 | 进入 EconomicEvent |
| Swap 和 Commission | Broker／账户历史 | PnL／Ledger 摄取 | 与 Order／Position 关联 |
| 风险判断 | Platform | Risk | 外部风控只提供输入或底层拒绝 |
| 对账差异 | Platform 计算 | Reconciliation | 不覆盖来源事实 |
| PnLResult | Platform 计算 | PnL | 带版本和完整度 |
| Fund／Portfolio 主档 | Platform 治理 | Fund／Portfolio | 外部系统可提供参考但非默认权威 |
| NAV | 未来平台或行政管理人 | 待确认 | 不与策略 PnL 自动等同 |
| Research Data | 数据供应商／公开源 | Research Data | 保存来源、修订和计算版本 |

## 10. 交易数据摄取

### 10.1 Platform Command

Platform 写入：

- TradeCommand。
- ExecutionBatch。
- ExecutionPlan。
- LegInstruction。
- 预创建 Order。
- Command Outbox。

### 10.2 Runtime 和外部回报

Runtime 产生标准 Runtime Event：

- OrderSubmissionResult。
- OrderStatusChanged。
- FillReceived。
- PositionSnapshotReceived。
- BalanceSnapshotReceived。
- FundingSettlementReceived。
- GatewayStatusChanged。

Platform 通过 Event Inbox 幂等处理。

### 10.3 外部或人工执行

抄底、Trader L／W 和未接入国内 Gateway 的执行可以通过：

- API 同步。
- Scheduled Sync。
- ImportBatch。
- Manual Confirmation。

进入平台。

所有来源必须保存：

- sourceType。
- sourceSystem。
- importBatchId／syncRunId。
- sourceRecordId。
- sourceHash。
- receivedAt。
- qualityState。
- attributionState。

## 11. EconomicEvent 与账本

### 11.1 EconomicEvent 类型候选

- TradeFillEconomicImpact。
- TradingFee。
- Commission。
- FundingSettlement。
- Swap／OvernightFee。
- BorrowInterest。
- FinancingCost。
- Deposit。
- Withdrawal。
- InternalTransfer。
- FXConversion。
- ValuationChange。
- ManualAdjustment。

### 11.2 资金流与 PnL 分开

- Deposit、Withdrawal 和内部资金划转通常不是交易 PnL。
- TradingFee、Funding、Swap 和价格变化可以进入策略 PnL。
- Fund Subscription／Redemption 未来属于基金资本和份额领域，不直接进入策略收益。
- StrategyAllocation 不是 EconomicEvent，除非实际发生资金或会计影响。

### 11.3 LedgerEntry

LedgerEntry 用于将 EconomicEvent 映射为：

- 策略归因项。
- 账户经济影响。
- 原始币种和统一计价币种。
- 调整和冲销关系。

当前不要求完整借贷会计科目。

### 11.4 Strategy PnL、Portfolio PnL 与 NAV

推荐关系：

```text
EconomicEvent
→ Strategy PnLResult
→ Book / Portfolio Aggregation
→ Portfolio ValuationResult
→ future Fund NAV process
```

规则：

- Strategy PnLResult 不自动等于 Fund NAV。
- Fund NAV 还可能包含基金费用、现金、应收应付、估值调整和份额变动。
- 当前可以提供内部 Strategy／Portfolio NetValue，但必须标记口径和非正式 NAV 属性。

## 12. 对账架构

### 12.1 对账层级

至少包括：

1. Order 对账。
2. Fill／Deal 对账。
3. Position 对账。
4. Balance／Margin 对账。
5. Fee／Funding／Swap 对账。
6. EconomicEvent 完整度对账。
7. PnL 输入完整度和核对关系。
8. Portfolio／Fund 层资金和估值对账，后续。

### 12.2 Difference

ReconciliationDifference 至少表达：

- 对象类型和稳定 ID。
- Platform Value。
- External Value。
- 差异类型和数量／金额。
- 首次发现和最近确认时间。
- 影响账户、策略、Book、Portfolio 和 Fund。
- 严重度。
- 是否阻断新增风险。
- 当前处理状态。
- 修正或接受结果。

### 12.3 修复原则

- 自动补查询优先于自动覆盖。
- 可以确认缺失事实时追加摄取。
- 不能确认时进入人工复核。
- 接受差异必须有权限、原因和审计。
- 影响 PnL 时触发版本化重算。

## 13. Data Quality

### 13.1 质量维度

至少包括：

- Completeness。
- Freshness。
- Validity。
- Consistency。
- Uniqueness。
- Source Availability。
- Reconciliation Status。
- Calculation Status。

### 13.2 状态候选

- `complete`。
- `partial`。
- `delayed`。
- `stale`。
- `conflicted`。
- `unverified`。
- `missing`。
- `invalid`。
- `reconciling`。
- `corrected`。

状态最终进入公共枚举文档。

### 13.3 缺失不能等于零

以下情形必须区分：

- 实际值为零。
- 尚未发布。
- 数据源未返回。
- 接口失败。
- 尚未核对。
- 不适用。

## 14. Research、Content 与交易数据隔离

### 14.1 Execution Market Data

用于：

- 交易报价。
- 合约规则。
- 订单合法性。
- 风险和执行。

要求更严格的新鲜度、时间和来源。

### 14.2 Research Data

用于：

- 宏观和跨资产研究。
- 历史分析。
- 看板和衍生指标。

需要保留：

- observationDate。
- releaseDate。
- revision。
- calculationVersion。

### 14.3 Content and Calendar

用于：

- 新闻。
- 日历。
- 理财信息。

不直接成为交易事实和风险阻断输入，除非经过正式数据和规则转换。

## 15. 逻辑存储分层

本文不决定产品，但建议逻辑上分为：

### 15.1 Core Relational Store

保存：

- Fund、Portfolio、Book、Strategy 和 Account 主数据。
- TradeCommand、ExecutionBatch、Order、Fill。
- Risk、Approval、Reconciliation。
- EconomicEvent、LedgerEntry 和 PnL 元数据。
- Audit、Configuration、Outbox 和 Inbox。

### 15.2 Time-Series／Analytical Store

候选保存：

- Kline。
- 大量 Quote／OrderBook。
- Research Observation。
- 长区间指标和计算结果。

初期可由关系数据库承载有限数据，后续按规模拆分。

### 15.3 Object Store

保存：

- 原始导入文件。
- 外部报表和结算文件。
- 报表产物。
- 大型历史数据文件。
- 对账证据。

### 15.4 Cache and Read Model

保存：

- 可重建查询投影。
- 短期行情摘要。
- 会话和限频状态，适用时。

不得成为核心交易事实唯一来源。

### 15.5 Runtime Local Journal

由 Execution Runtime 保存：

- Command 去重。
- 待发送 Event。
- 外部映射缓存。
- 恢复位置。

不是 Platform 数据库。

## 16. 事务、事件和一致性

### 16.1 本地事务

单个主责模块的强一致写入使用本地事务。

例如：

```text
创建 TradeCommand
+ 创建 ExecutionBatch
+ 预创建 Order
+ 写 Command Outbox
```

需要在明确事务边界内完成，具体聚合和拆分后续确认。

### 16.2 跨模块一致性

- 不使用覆盖全平台的大事务。
- 通过稳定 ID、事实事件和幂等消费者协作。
- Read Model 投影失败不回滚权威事实。
- 失败投影支持重放和重建。

### 16.3 Outbox／Inbox

交易和重要治理命令优先采用：

- Transactional Outbox。
- Event／Command Inbox。
- 唯一约束和 payload hash。
- 重试、Dead Letter 和人工处理。

### 16.4 事件版本

事件至少具有：

- eventId。
- eventType。
- payloadVersion。
- occurredAt。
- receivedAt。
- correlationId。
- causationId。
- source。
- entityId，适用时。

## 17. 导入、修正和重算

### 17.1 ImportBatch

ImportBatch 至少记录：

- 原始文件或任务身份。
- 文件 Hash。
- 数据来源。
- 覆盖业务范围。
- 总数、成功、失败、重复和冲突数量。
- 校验版本。
- 确认、回滚和归档状态。
- 操作人和审计。

### 17.2 DataCorrectionRecord

记录事实或主数据修正：

- 原值和新值。
- 修正原因。
- 证据。
- 影响范围。
- 审批。
- 生效时间。

### 17.3 AdjustmentEntry

用于不修改原始经济事实的正式经济调整。

### 17.4 RecalculationRun

建议增加：

- `recalculationRunId`。
- 目标策略、Book、Portfolio 或日期范围。
- 输入数据版本。
- 计算规则版本。
- 原 PnLResult 和新 PnLResult。
- 触发原因。
- 运行结果和错误。

## 18. 数据安全分类

建议至少分为：

- Public／External Public。
- Internal。
- Confidential。
- Restricted Trading。
- Restricted Financial。
- Secret／Credential。

示例：

- 公开行情可以是 External Public，但内部衍生研究可能是 Internal。
- 账户余额、持仓和订单属于 Restricted Trading／Financial。
- API Key、密码和 Token 属于 Secret。
- Audit 导出可能包含 Restricted 信息。

数据分类影响：

- 查询权限。
- 导出。
- 日志脱敏。
- 缓存。
- 备份和保留。
- 非生产环境复制。

## 19. 保留、归档和删除

需要形成正式矩阵，至少区分：

| 数据类型 | 推荐方向 |
|---|---|
| Order、Fill、EconomicEvent、PnL、Approval、Audit | 长期保留 |
| Account／Position Snapshot | 按频率和业务价值分层保留 |
| Tick／OrderBook | 按策略、合规和成本决定 |
| Kline 和 Research Data | 长期或可重建保存 |
| Runtime Journal | 短中期保留并支持安全清理 |
| 原始导入和结算文件 | 核对后归档，按政策保留 |
| Read Model 和 Cache | 可重建，按性能需求清理 |
| Secret | 仅保存安全引用和必要历史 |

删除必须遵守：

- 审计要求。
- 报表可重现。
- PnL 重算。
- 数据供应商许可。
- 安全和隐私要求。

## 20. 备份和恢复

统一数据架构必须支持：

- 核心关系数据库备份。
- 对象存储版本和备份。
- 配置和 SecretReference 恢复。
- Schema 和迁移版本恢复。
- Outbox／Inbox 恢复。
- 恢复后的 Order、Fill、Position、Account、EconomicEvent、PnL、Approval 和 Audit 对账。

恢复完成不等于服务启动成功；需要数据一致性和交易风险确认。

## 21. 初期最小对象建议

即使 V1 只聚焦策略模块，建议最小数据骨架包含：

### 21.1 治理和组织

- LegalEntity。
- Fund。
- Portfolio。
- Book，允许一个默认 Book。
- User／Capability／Scope。

### 21.2 策略和主数据

- StrategyDefinition。
- StrategyVersion。
- StrategyInstance。
- StrategyAllocation。
- StrategyAccountBinding。
- Account。
- Venue／Broker。
- Instrument／ContractSpecification／Mapping。
- Currency／Unit／Calendar。

### 21.3 交易与账户

- TradeCommand。
- ExecutionBatch。
- ExecutionPlan，作为值对象或独立对象由后续 ADR 确认。
- LegInstruction。
- Order。
- Fill。
- Position。
- Balance／Margin／Position Snapshot。

### 21.4 可靠性和治理

- Command Outbox。
- Event Inbox。
- ReconciliationRun／Difference。
- RecoveryRun。
- RiskDecision。
- ApprovalGrant。
- AuditEvent。
- ImportBatch。

### 21.5 经济结果

- EconomicEvent。
- AdjustmentEntry。
- PnLResult。
- PnLAttribution。
- RecalculationRun。

## 22. 不建议初期建设

- 完整 Investor 和 ShareClass 系统。
- 完整 Subscription／Redemption 工作流。
- 完整 Fund Accounting 总账。
- 复杂数据湖和实时流计算平台。
- 全量永久 Tick／OrderBook 保存。
- 多数据库强行按领域拆分。
- 为每个领域单独建设微服务数据库。
- 未有真实数据量前引入复杂分布式计算。

## 23. 需要形成的后续 ADR

本文确认后，建议至少形成或评审：

1. Fund／Portfolio／Book 最小层级是否正式采用。
2. ExecutionPlan 是版本化值对象还是独立持久化对象。
3. 核心关系数据库选型。
4. 时间序列和研究数据存储策略。
5. Runtime Command／Event 通道和 Outbox／Inbox。
6. Runtime Local Journal 存储。
7. Money、Decimal 和 API 数值传输规范。
8. 数据保留、归档、RPO 和 RTO。
9. Strategy Economic Ledger 与未来 Fund NAV／Finance Ledger 的接口。

## 24. 验收标准

本文进入 active 架构前，应满足：

- Fund、Portfolio、Book、Strategy、Account 的关系无歧义。
- Account Ownership、StrategyAllocation 和 StrategyAccountBinding 分开。
- 主数据、事实、状态、快照和派生结果分开。
- Money、Price、Quantity、Rate、Currency 和 Unit 具有统一语义。
- 时间、businessDate、tradingDay、settlementDate 和 valuationDate 分开。
- 外部事实、Runtime 状态、平台事实和 Read Model 权威清楚。
- FundingRate 与 FundingSettlement 分开。
- Capital Flow 与 PnL 分开。
- Strategy PnL 与 Fund NAV 分开。
- 修正、调整、重算和对账不会无痕覆盖事实。
- 初期逻辑存储和后续扩展路径明确。
- 数据安全分类、保留和恢复具有正式后续任务。

## 25. 当前建议

从技术负责人审视结果出发，建议采用本文的大方向：

```text
LegalEntity
→ Fund
→ Portfolio
→ Book
→ StrategyInstance
→ StrategyAllocation / StrategyAccountBinding
→ Account / Trading Facts
→ EconomicEvent / PnL
```

但在同步进入 active 架构前，需要重点审阅：

- 一个 Fund 是否只需要一个默认 Portfolio。
- Book 是否作为第一阶段正式对象，还是先由 StrategyInstance 承担。
- 账户是否存在跨 Fund 或跨 Portfolio 共享。
- 当前内部净值是否需要命名为 Portfolio NetValue，而避免称为正式 Fund NAV。
- Finance and Treasury 的业务范围。

在这些问题确认前，本文保持 draft；其余已确定的数据分类、精度、时间、事实不可覆盖、对账和修正规则可以逐步同步到 active 文档。