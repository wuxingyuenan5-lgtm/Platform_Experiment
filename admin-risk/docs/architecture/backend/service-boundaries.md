# Platform V6+ 后端模块与服务边界

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：后端架构

上位约束：

- `../platform-target-architecture.md`
- `backend-overview.md`
- `execution-runtime-and-gateway.md`
- `../decisions/ADR-006-后端优先采用模块化单体.md`
- `../decisions/ADR-008-总体逻辑分层与独立交易Runtime.md`

## 1. 文档定位

本文定义 Platform Backend 的逻辑模块、对象所有权、依赖方向、公开协作方式和数据写入边界，并明确 Execution Runtime 不属于模块化单体内部普通业务模块。

当前架构：

```text
admin-risk
↓
platform-backend：模块化单体
↓ Runtime Command / Event Contract
execution-runtime：独立进程
↓
MT5 / Crypto / CTP，后续
```

逻辑模块可以初期共同部署并使用同一平台数据库，但不得互相绕过公开边界直接修改内部数据。

## 2. 总体结构

```text
Platform API / BFF
        ↓
Application Modules
        ↓
Domain Modules
        ↓
Repository / Query / Event / Runtime Ports
        ↓
Infrastructure Adapters
```

Platform Backend 逻辑模块包括：

- IAM and Permission。
- Strategy。
- Trading and Execution。
- Account and Position。
- Execution Market Data。
- Research Data。
- Content and Calendar。
- Risk。
- Approval and Control。
- Reconciliation and Data Quality。
- PnL and Strategy Economic Ledger。
- Finance and Treasury，范围确认后。
- Reporting。
- Audit。
- Notification。
- Configuration。
- Runtime Coordination and Integration Contract。
- Query and Read Models。

Execution Runtime 独立包括：

- Runtime Main。
- Runtime Journal。
- Gateway Adapter。
- Crypto Worker。
- MT5 Worker。
- CTP Worker，后续。

金融AI分析当前冻结，不建立当前专项后端模块。

V1 后端服务边界以资费套利和跨所价差闭环为优先：Crypto 真实 API 模拟盘／测试盘和 MT5 Demo／Worker 必须通过 Execution Runtime 接入；Platform Backend 只处理业务规则、持久化、查询、风险、对账和 PnL。真实资金 Live、CTP、客户侧权限体系和金融AI分析后端暂缓。

## 3. 模块边界原则

- 每个核心对象只有一个主责模块。
- 模块通过公开 Application Service、Domain Port、Query 或 Event 协作。
- 禁止跨模块直接写入对方内部表和对象。
- 同一数据库不代表允许任意跨表写入。
- 查询可以聚合 Read Model，但不能复制第二套业务权威。
- API DTO、Domain Model、ORM Model 和 Read Model 分开。
- 外部 DTO、SDK 对象和 Runtime 内部对象不进入 Domain 层。
- 基础设施实现不能反向决定业务边界。
- 产品菜单归属不等于后端模块归属。
- Runtime Event 是外部事实输入，不允许绕过领域规则直接覆盖状态。
- 跨模块事务优先围绕单一聚合；跨领域流程通过 Application 编排、Outbox／Inbox 或事实 Event 协作。

## 4. IAM and Permission

### 拥有

- User。
- Role。
- Capability。
- DataScope。
- EnvironmentScope。
- TradingModeScope。
- RoleAssignment。
- DirectGrant／TemporaryGrant。
- Session。
- CredentialPolicy。
- AuthenticationFactor 元数据。

### 对外提供

- 身份认证和会话校验。
- 当前用户 Effective Permission。
- Query、Command、字段和数据范围判断。
- 高风险操作二次认证结果。
- 用户和授权状态事件。

### 不负责

- 交易规则和订单执行。
- 风险阈值和 RiskDecision。
- Approval 业务结论。
- 产品菜单结构。
- Broker、Exchange 和账户凭证内容。

## 5. Strategy

### 拥有

- StrategyDefinition。
- StrategyVersion。
- StrategyInstance。
- StrategyParameterSet。
- StrategyAccountBinding。
- StrategyCapability。
- ExternalExecutionProfile。
- SignalRecord 的策略身份和版本关系，适用时。

### 对外提供

- 策略定义、版本和实例 Query。
- 当前已生效参数和策略能力。
- 策略实例运行和管理状态。
- 策略与 Account 的用途和额度关系。
- 外部执行归属配置。

### 所有权规则

- StrategyAccountBinding 由 Strategy 拥有。
- Account 模块拥有 Account 主档和账户状态。
- Strategy 通过 AccountId 引用账户，不复制账户余额和连接事实。
- StrategyVersion 是历史规则解释依据，不能用当前版本无痕重解释历史交易。

### 不负责

- 直接连接外部交易系统。
- 外部订单最终状态。
- Account Balance 和 Margin 最终事实。
- 平台正式 PnL 计算。
- 页面本地配置。

## 6. Trading and Execution

### 拥有

- TradeIntent。
- TradeCommand。
- ExecutionBatch。
- 版本化 ExecutionPlan。
- LegInstruction。
- platformOrderId 和平台 Order。
- Fill 标准化交易事实。
- ExecutionBalanceStatus。
- ExposureStatus。
- ExecutionException。
- ManualIntervention。
- 结果未知和业务恢复状态。

### 对外提供

- 提交、撤销、平仓、调整、配平和紧急对冲 Command。
- TradeCommand、ExecutionBatch、Order 和 Fill Query。
- 执行、异常、暴露、人工处理和恢复 Event。
- 向 Runtime Coordination 生成可靠执行命令。

### 依赖

- IAM：Capability 和 Data Scope。
- Strategy：StrategyInstance 和 StrategyAccountBinding。
- Execution Market Data：Quote 和 ContractSpecification。
- Account：Account、Balance、Margin 和 Position。
- Risk：RiskDecision 和 GlobalTradingBlock。
- Approval：ApprovalGrant，适用时。
- Runtime Coordination：GatewayCapability 和 Runtime 可用性。

### 不负责

- 账户余额和保证金规则权威。
- RiskRule 和 RiskLimit。
- ApprovalPolicy。
- 策略损益归因。
- 直接调用 Broker、Exchange、MetaTrader5 和 CTP SDK。
- 直接读取 Runtime Journal。

## 7. Account and Position

### 拥有

- Account。
- AccountStatus。
- AccountCapability 的业务视图。
- AccountRestriction。
- BalanceSnapshot。
- MarginSnapshot。
- Position。
- PositionSnapshot。
- ExposureSnapshot，账户和持仓维度。
- CapitalAllocation，范围确认后。

### 对外提供

- Account 主档和状态。
- Balance、Equity、Available、Margin 和 Position Query。
- Account 和 Position Event。
- Strategy、Trading、Risk、PnL 和 Reconciliation 所需账户事实。

### 规则

- StrategyAccountBinding 不归 Account。
- 外部账户事实通过 Runtime Event、同步和对账进入。
- 页面不得根据订单自行推算正式余额。
- 无法归属策略的 Position 保留 `unallocated`／`unverified`。

### 不负责

- 策略账户用途和策略版本。
- 订单业务生命周期。
- 风险阈值。
- 正式策略 PnL。

## 8. Execution Market Data

### 拥有

- Market。
- Venue。
- Instrument。
- ContractSpecification。
- SymbolMapping。
- TradingSession。
- QuoteSnapshot。
- DepthSnapshot。
- Kline／HistoricalBar，执行用途。
- FundingRateSnapshot。
- FxRateSnapshot。
- MarketStatus。
- MarketDataQuality。

### 对外提供

- 交易执行所需实时和历史行情。
- Instrument 和外部 Symbol 映射。
- 合约乘数、精度、数量和订单规则。
- Funding、汇率、交易时段和数据质量。

### 不负责

- Research Data 完整生命周期。
- 新闻、日历和内容。
- 用户交易意图。
- Account Balance。
- FundingSettlement 和最终 PnL。

## 9. Research Data

### 拥有

- ResearchSeries。
- ResearchObservation。
- ResearchRevision。
- Dataset／DatasetVersion。
- DerivedResearchIndicator。
- ResearchDataQuality。
- 数据血缘和计算版本。

### 对外提供

- 宏观、资产、行业、公司、ETF 和研究衍生数据。
- 历史修订和首次发布值。
- 看板、首页和策略研究背景 Query。

### 不负责

- 正式交易使用的最终 QuoteSnapshot。
- 新闻内容编辑。
- Order、Account、Position 和 PnL。

## 10. Content and Calendar

### 拥有

- NewsContent／ContentItem。
- StoryCluster。
- SourceReference。
- CalendarEvent。
- CalendarRevision。
- WealthOpportunity。
- ContentRevision。
- ReviewState。

### 对外提供

- 新闻、摘要、宏观事件和理财信息。
- 来源、版本、审核、撤回、失效和生命周期。
- 首页和新闻日历与理财 Query。

### 不负责

- 将自然语言内容直接转为 TradeCommand。
- 交易行情质量。
- RiskDecision。
- 订单和 PnL。

## 11. Risk

### 拥有

- RiskMetric。
- RiskRule。
- RiskLimit。
- RiskSnapshot。
- RiskDecision。
- RiskEvent。
- RiskResolution。
- GlobalTradingBlock。
- RiskOverride。
- ViolationRule／ViolationRecord，适用时。

### 对外提供

- 执行前 RiskDecision。
- 当前 RiskStatus、限制和阻断。
- RiskEvent 和处置结果。
- 风险降低动作允许范围。

### 规则

- Risk 可以读取 Trading、Account、Position、PnL、Market Data 和 Data Quality。
- Risk 不拥有上述源事实。
- 未验证指标可以为观察或警告，不自动成为强制阻断。
- GlobalTradingBlock 默认禁止新增风险，不无条件自动平仓。

## 12. Approval and Control

### 拥有

- ApprovalPolicy。
- ApprovalRequest。
- ApprovalDecision。
- ApprovalGrant。
- Maker／Checker 关系。

### 对外提供

- 某 Command 是否需要审批。
- 审批请求、决定和短期授权。
- 与目标对象、payload 哈希、环境、模式和有效期绑定的 Grant。

### 不负责

- 用户基础 Capability。
- RiskDecision。
- 目标 Command 执行。
- AuditEvent 的最终持久化。

审批通过不等于目标操作执行成功。

## 13. Reconciliation and Data Quality

### 拥有

- ReconciliationRun／Job。
- ReconciliationResult。
- ReconciliationDifference。
- DataQualityStatus／State。
- DataQualityIncident。
- DataCorrectionRecord。
- 差异确认和接受状态。

### 对外提供

- Order、Fill、Position、Balance、Margin、Funding、Swap、Fee、EconomicEvent 和 PnL 核对。
- 数据完整、延迟、重复、冲突和差异状态。
- 重新同步、修正和人工确认流程。

### 规则

- 不得无痕修改其他模块原始事实。
- 缺失外部事实优先重新同步和补查询。
- 正式修正通过目标领域 Command、DataCorrectionRecord、AdjustmentEntry 和版本化重算。
- DataQualityStatus 与 ReconciliationStatus 分开。

## 14. PnL and Strategy Economic Ledger

### 拥有

- EconomicEvent。
- LedgerEntry。
- PnLResult。
- PnLAttributionItem。
- StrategyNavSnapshot。
- ValuationSnapshot。
- AdjustmentEntry。
- PnL 计算定义和版本。

### 对外提供

- 实际和估算损益，状态明确。
- 策略专属归因。
- 重算、核对、结算和完整度结果。
- 策略管理和 Reporting 的稳定结果。

### 规则

- EconomicEvent 来源于 Fill、Fee、FundingSettlement、Swap、FX、资金流和 Adjustment。
- 缺失数据不能静默当零。
- 新计算版本不无痕覆盖旧版本。
- Strategy Economic Ledger 不等于完整财务会计总账。
- V1 优先支持资费套利和跨所价差的 PnLResult、最小归因和固定时间 StrategyNavSnapshot。
- 海内外价差复杂四层 PnL、抄底 TradeCycle、短线交易员违规归因和正式 Fund NAV 不属于 V1。

## 15. Finance and Treasury

### 当前状态

正式范围待业务和会计规则确认。

### 候选拥有

- TreasuryAccount。
- TreasuryBalanceSnapshot。
- CashFlowRecord。
- FundingAllocation。
- TransferRequest／TransferRecord。
- ExpenseRecord。
- FinanceImportBatch。

### 边界

- Account Balance、Strategy Allocation、Strategy Economic Ledger、Treasury Cash 和 Finance Record 分开。
- 不用策略 PnL 和交易账户余额拼接法定财务总账。
- 真实资金操作启用后需要权限、审批、幂等、结果未知、对账和审计。

## 16. Reporting

### 拥有

- ReportDefinition。
- ReportParameterSchema。
- ReportRun。
- ReportVersion／ReportArtifact。
- ReportAccessRecord。
- ReportSchedule，后续。

### 规则

- Reporting 读取权威领域数据或稳定 Read Model。
- 不重新计算第二套交易事实、PnL 和 RiskRule。
- 正式版本不无痕覆盖。
- 生成、查看、下载和发布分别授权。

## 17. Audit

### 拥有

- AuditEvent。
- OperatorContext。
- ChangeRecord。
- SecurityEvent。

### 规则

- 关键 Command、Approval、RiskOverride、数据修正、配置、资金、运行操作和人工干预必须审计。
- Audit 接收其他模块事实，不参与普通业务决策。
- 审计页面只查询，不修改源业务对象。
- 敏感值脱敏或使用安全引用。

## 18. Notification

### 拥有

- Notification。
- NotificationTemplate。
- DeliveryAttempt／NotificationDelivery。
- ReadState。
- NotificationPreference。

### 规则

- Notification 消费源领域 Event。
- 不重新判断 RiskEvent、Order、ReportRun 和服务健康事实。
- 无权限用户不能通过通知泄露敏感对象。
- 阅读和归档状态不修改源业务事实。

## 19. Configuration

### 拥有

- ConfigDefinition。
- ConfigValue／ConfigVersion。
- FeatureFlag。
- SecretReference。
- ConfigurationChangeRequest。
- ConfigurationActivationRecord。

### 规则

- 每项配置具有主责领域、类型、范围、版本和生效状态。
- 系统设置页面不成为万能配置模型。
- Secret 内容不与普通配置保存在同一通用模型中。
- Live 高风险配置需要审批和审计。
- 前端保存成功不等于目标 Runtime／Worker 已激活成功。

## 20. Runtime Coordination and Integration Contract

该模块位于 Platform Backend，负责平台与 Execution Runtime 的业务协调记录和契约，不直接执行外部订单。

### 拥有

- RuntimeDefinition 的平台注册记录。
- RuntimeInstance 的配置和注册身份。
- GatewayDefinition。
- GatewayRuntime 的平台配置和能力投影。
- WorkerDefinition／WorkerInstance 的平台投影。
- RuntimeCommand Outbox。
- RuntimeEvent Inbox。
- Runtime Capability Snapshot。
- RecoveryRun 的平台侧协调记录。

### 对外提供

- Runtime 和 Gateway 定义、配置、能力和健康 Query。
- Runtime Command 发布 Port。
- Runtime Event 消费入口。
- Worker、Gateway、恢复和积压摘要。
- TradingPermissionState 所需运行条件。

### 与 Runtime 的边界

Platform Backend 拥有稳定注册、配置、Command、Inbox 和业务投影；Execution Runtime 拥有进程、Session、连接、实时 OMS 和 Local Journal。

### 不负责

- 直接调用 Broker SDK。
- 维护真实外部 Session。
- 直接下单和撤单。
- 以 Runtime 心跳自动解除 Risk Block。
- 访问 Runtime Journal 内部表。

## 21. Query and Read Models

### 拥有

- 页面和报表使用的只读投影定义。
- 投影版本、数据截止时间和重建状态。
- 缓存和失效策略。
- 跨领域稳定 ID 关联。

### 规则

- 允许跨领域聚合读取。
- 不接受业务写入。
- 不复制第二套生命周期和规则。
- 不作为恢复、对账和审计的最终权威。
- 汇总和明细可以相互穿透。

## 22. Execution Runtime

Execution Runtime 是独立工程和进程，不属于 Platform Backend 模块化单体。

### Runtime 拥有

- RuntimeSession。
- Gateway 和 Worker 实时 Session。
- 外部连接、订阅和限频状态。
- 当前活动订单和成交缓存。
- 已处理 Command、待发送 Event 和恢复位置的 Local Journal。
- 外部原始状态、错误和 ID 映射上下文。

### Runtime 对外提供

- 订单提交、撤销、查询和回报。
- Market Data、Account、Funding 和其他 Capability。
- RuntimeEventEnvelope。
- 连接、同步、恢复和 READY 状态。

### Runtime 不负责

- StrategyDefinition／Version／Instance。
- 平台 ExecutionBatch 和 PnL。
- IAM、Approval 和 RiskRule。
- 平台永久 Order／Fill 数据库。
- Reporting 和 Read Model。

详细见 `execution-runtime-and-gateway.md`。

## 23. 模块协作方式

### 23.1 Query

- 可以跨模块读取公开 Query。
- 可以聚合 Read Model。
- 不通过 Query 修改事实。
- 返回来源、时间、质量、版本和权限范围。

### 23.2 Command

- 由拥有目标对象的模块处理。
- Application 层协调多个前置判断。
- 具有权限、幂等、对象版本和审计上下文。
- 跨模块不能以数据库 UPDATE 代替 Command。

### 23.3 Event

- 表达已经发生的事实。
- 消费者幂等。
- 可以重复、延迟和乱序。
- Event 不授予消费者任意修改源对象的权限。

### 23.4 Runtime Command／Event

- Platform Backend 通过 Outbox 发布 Runtime Command。
- Runtime 去重、执行并通过 Journal 可靠发布 Event。
- Platform Event Inbox 幂等消费。
- 网络超时不等于外部失败。
- 结果未知通过查询、同步和对账恢复。

## 24. 依赖方向

推荐依赖：

```text
API
→ Application
→ Domain
→ Port
← Infrastructure Adapter
```

领域依赖原则：

- Trading 引用 Strategy、Account、Market Data、Risk 和 Approval 的公开接口或快照。
- Risk 读取 Trading、Account、Position、PnL 和 Data Quality，不拥有源事实。
- PnL 消费 Trading、Account 和 EconomicEvent，不修改源 Order／Fill。
- Reconciliation 读取和比较多个领域，通过正式 Command 发起修正。
- Reporting 和 Query Read Models 只读聚合。
- Runtime Coordination 不反向拥有 Trading 业务状态。

禁止循环依赖以共享 ORM Entity 解决。

## 25. 数据访问边界

即使初期使用一个数据库：

- 每张核心表具有明确主责模块。
- 其他模块不得直接 UPDATE／DELETE。
- 跨模块读优先通过 Query、Repository Port、稳定视图或 Read Model。
- 数据修正由主责模块 Command 执行。
- 迁移脚本按模块归属管理。
- Runtime 不直接连接平台业务数据库执行写入。
- Read Model 可以重建，不成为唯一备份。

## 26. 产品模块与后端领域

| 产品入口 | 主要后端领域 |
|---|---|
| 首页 | Query and Read Models、各领域摘要 |
| 对冲基金看板 | Research Data、部分 Execution Market Data |
| 新闻日历与理财 | Content and Calendar |
| 交易平台 | Strategy、Trading、Market Data、Account、Risk、Runtime Coordination |
| 策略管理 | PnL、Account、Position、Trading、Reconciliation、Read Models |
| 风险管理 | Risk、Account、Finance、Observability、Reporting、Audit、IAM、Configuration、Notification |
| 金融AI分析 | 当前冻结，不建立当前专项领域 |

前端菜单不等于后端服务边界。

## 27. 未来独立服务拆分条件

只有出现以下证据时才评审：

- 明显独立扩缩容。
- 严格安全、合规或故障隔离。
- 发布生命周期显著不同。
- 模块化单体成为真实性能或可用性瓶颈。
- 团队已经形成独立维护责任。
- 数据权威、接口和事件边界已经稳定。

Execution Runtime 已经因外部连接和恢复需求独立进程，但不意味着所有业务领域都需要拆分服务。

## 28. 验收标准

- 每个核心对象只有一个主责模块。
- Platform Backend 与 Execution Runtime 的边界明确。
- Crypto 真实 API 模拟盘／测试盘和 MT5 Demo／Worker 的接入均通过 Execution Runtime，不由 Platform Backend 或前端直接连接。
- Integration 不再被误解为 Platform Backend 直接连接 Broker SDK。
- StrategyAccountBinding 归 Strategy，Account 主档归 Account。
- Trading 不直接连接外部交易系统。
- Runtime 不拥有平台 ExecutionBatch、Risk 和 PnL。
- Query and Read Models 不形成第二套业务写入入口。
- Finance、Account、Strategy Ledger 和 PnL 不混为一体。
- 同库部署不会导致跨模块任意写入。
- 金融AI冻结不阻塞当前模块边界完整性。
- 客户侧权限和客户门户不作为当前服务边界验收项，等用户系统完成后再展开。
