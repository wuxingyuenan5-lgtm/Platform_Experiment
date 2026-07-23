# Platform V6+ 后端架构总览

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：后端架构

上位约束：

- `../platform-target-architecture.md`
- `../decisions/ADR-006-后端优先采用模块化单体.md`
- `../decisions/ADR-008-总体逻辑分层与独立交易Runtime.md`
- `service-boundaries.md`

## 1. 文档定位

本文定义 Platform Backend 的目标职责、内部形态、与 Execution Runtime 的边界、逻辑领域、数据权威、Command／Query／Event 原则和安全可靠性要求。

本文所称“后端”主要指 `platform-backend`，不把 `execution-runtime` 误认为模块化单体内部普通模块。

V1 后端目标不是只支撑 Mock 或 Fake Gateway，而是支撑真实外部接口的受控验证：资费套利至少跑通一条 Crypto 真实 API 模拟盘／测试盘链路，跨所价差跑通 Crypto 真实 API 模拟盘／测试盘 + MT5 Demo／Worker 跨 Runtime 链路。真实资金 Live 下单、CTP、客户侧权限体系和金融AI分析后端均暂缓。

平台总体工程主体为：

```text
admin-risk
+
platform-backend
+
execution-runtime
```

其中：

- Platform Backend 负责业务规则、业务状态、平台持久化和查询。
- Execution Runtime 负责外部交易连接、订单执行、实时 OMS 和运行恢复。
- 两者使用平台自有 Command／Event／Port 契约协作。

## 2. 目标形态

Platform Backend 初期采用模块化单体：

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
        ├─ Platform Database
        ├─ Cache / Async Tasks
        ├─ Read Model Storage
        └─ Runtime Command / Event Adapter
```

Execution Runtime 独立运行：

```text
Runtime Main
├─ Command Consumer
├─ Event Publisher
├─ Runtime Journal
├─ Worker Registry
├─ Crypto Worker(s)
├─ MT5 Worker(s)
└─ CTP Worker(s)，后续
```

禁止：

- 在 Platform API 进程中直接加载 MetaTrader5、Broker 或 Exchange SDK。
- 在业务边界尚未稳定前拆分大量微服务。
- 让 Runtime 直接修改 Platform Backend 内部业务表。
- 让浏览器、Runtime OMS 或外部组件数据库成为平台最终业务权威。

## 3. Platform Backend 分层

### 3.1 API／BFF 层

负责：

- HTTP、WebSocket 或 SSE 接入。
- 请求和响应 DTO。
- 身份和会话解析。
- 请求级校验、错误映射和追踪上下文。
- 页面需要的 Query 和 Command 入口。

不负责：

- 直接编写交易业务规则。
- 直接调用 Broker SDK。
- 在请求中等待外部订单最终成交。
- 返回“已受理”时表示“已成交”。

### 3.2 Application 层

负责：

- 用例编排。
- Capability、Data Scope、Environment 和 TradingMode 校验。
- 幂等、对象版本和并发控制。
- ApprovalGrant 和 RiskDecision 协调。
- TradeCommand、ExecutionBatch、人工干预和数据修正流程。
- 跨领域 Query 聚合请求。
- 审计和事件上下文。

Application 层可以协调多个领域，但不得直接修改其他模块内部表。

### 3.3 Domain 层

负责：

- 业务对象、规则、不变量和生命周期。
- 领域 Command、Decision 和 Event。
- 稳定业务 ID 和对象关系。
- 领域服务和策略专项口径。

Domain 层不得依赖：

- FastAPI 等 Web 框架。
- ORM 具体实现。
- Redis、消息队列和数据库客户端。
- vn.py、CCXT、MetaTrader5、aiomql 和交易所 SDK。
- Runtime 进程内部类。

### 3.4 Infrastructure 层

负责：

- Repository 实现。
- ORM、数据库、缓存和任务系统。
- 外部数据源和内容接口 Adapter。
- Runtime Command／Event 传输 Adapter。
- 文件、报表和对象存储。
- Secret 引用和基础设施配置。

基础设施实现不得反向定义领域对象和业务状态。

### 3.5 Query and Read Model

负责：

- 聚合多个领域的只读结果。
- 为页面和报表形成稳定投影。
- 缓存、失效、重建和数据截止时间。
- 数据质量、来源和计算版本展示。

Read Model：

- 不接受业务写入。
- 不替代领域 Repository。
- 不作为恢复和对账的最终权威。
- 必须能通过稳定 ID 穿透至源对象。

## 4. 逻辑领域

### 4.1 IAM and Permission

负责 User、Role、Capability、DataScope、EnvironmentScope、TradingModeScope、Session 和安全策略。

### 4.2 Strategy

负责：

- StrategyDefinition。
- StrategyVersion。
- StrategyInstance。
- StrategyParameterSet。
- StrategyAccountBinding。
- ExternalExecutionProfile。
- SignalRecord 的策略身份和版本关系，适用时。

### 4.3 Trading and Execution

负责：

- TradeIntent。
- TradeCommand。
- ExecutionBatch。
- 版本化 ExecutionPlan。
- LegInstruction。
- 平台 Order 身份和状态。
- Fill 标准化记录。
- ExecutionBalanceStatus、ExposureStatus 和 ManualIntervention。
- 结果未知、幂等和业务恢复状态。

Trading 不直接连接外部系统，而是通过 Runtime Port 发出命令。

### 4.4 Account and Position

负责：

- Account 主档和状态。
- AccountCapability。
- BalanceSnapshot。
- MarginSnapshot。
- Position 和 PositionSnapshot。
- CapitalAllocation，范围确认后。

StrategyAccountBinding 不归 Account。

### 4.5 Execution Market Data

负责：

- Venue、Instrument 和 ContractSpecification。
- Symbol Mapping。
- Quote、Depth、Kline 和 MarketStatus。
- FundingRate、FxRate 和交易时段。
- 数据来源、新鲜度和 MarketDataQuality。

执行行情不能由页面图表数据或 Research Data 无提示替代。

### 4.6 Research Data

负责宏观、资产、行业、公司和研究衍生数据及其版本、修订、血缘和质量。

### 4.7 Content and Calendar

负责新闻、StoryCluster、CalendarEvent、WealthOpportunity、内容版本、来源和审核状态。

### 4.8 Risk

负责：

- RiskMetric。
- RiskRule。
- RiskLimit。
- RiskSnapshot。
- RiskDecision。
- RiskEvent 和 RiskResolution。
- GlobalTradingBlock。
- ViolationRecord 的风险判断，适用时。

Risk 可以读取 Trading、Account、Position 和 PnL，但不拥有这些事实。

### 4.9 Approval and Control

负责 ApprovalPolicy、ApprovalRequest、ApprovalDecision、ApprovalGrant 和 Maker／Checker。

审批通过不等于目标 Command 已执行成功。

### 4.10 Reconciliation and Data Quality

负责：

- ReconciliationRun／Job。
- ReconciliationResult。
- ReconciliationDifference。
- DataQualityStatus。
- DataCorrectionRecord。
- 对订单、成交、持仓、余额、费用、EconomicEvent 和 PnL 的核对。

不得无痕覆盖其他领域的原始事实。

### 4.11 PnL and Strategy Economic Ledger

负责：

- EconomicEvent。
- LedgerEntry。
- PnLResult 和 PnLAttributionItem。
- StrategyNavSnapshot。
- ValuationSnapshot。
- AdjustmentEntry。
- 版本化重算和数据完整度。

Strategy Economic Ledger 不等于完整财务会计总账。

V1 中，PnL 领域优先承接资费套利和跨所价差两条完整闭环，至少支持 PnLResult、PnLAttributionItem 和固定时间 StrategyNavSnapshot。海内外价差复杂四层 PnL、抄底 TradeCycle、短线交易员违规归因和正式 Fund NAV 均延后。

StrategyNavSnapshot 的 V1 默认口径为 `nav = equity / capitalBase`，当前以 USDT 为主要计价口径。它是策略运营净值，不是正式 Fund NAV。

### 4.12 Finance and Treasury

在正式业务范围确认后负责公司经营资金、资金任务、划拨、收支和财务协作。

不得用策略 PnL 或交易账户余额拼接替代法定财务总账。

### 4.13 Reporting

负责 ReportDefinition、ReportRun、ReportVersion、ReportArtifact 和访问记录。

### 4.14 Audit

负责 AuditEvent、OperatorContext、ChangeRecord 和 SecurityEvent。

### 4.15 Notification

负责 Notification、DeliveryAttempt、ReadState 和 NotificationPreference。

通知不重新判断源事件的业务严重度。

### 4.16 Configuration

负责 ConfigDefinition、ConfigVersion、FeatureFlag、SecretReference 和激活记录。

系统设置页面不形成万能配置模型。

### 4.17 Query and Read Models

负责跨领域只读聚合，不拥有源业务事实。

### 4.18 金融AI分析

金融AI分析当前冻结：

- 不建立当前专项 AI Orchestration 模块。
- 不完善 AI 专属领域对象和部署。
- 不作为其他领域的前置依赖。
- 继续保留禁止交易、风险、账户、审批和数据修正写入的通用边界。

## 5. Platform Backend 与 Execution Runtime

### 5.1 Platform Backend 对 Runtime 提供

- Runtime Command Envelope。
- 稳定 commandId、requestId、correlationId 和 idempotencyKey。
- StrategyInstance、ExecutionBatch、LegInstruction 和 platformOrderId 引用。
- 已通过权限、风险和审批校验的执行参数。
- Command 过期时间和 payloadVersion。

### 5.2 Runtime 向 Platform Backend 提供

- Runtime Event Envelope。
- 外部订单、成交、账户、持仓和费用更新。
- Gateway、Runtime 和 Worker 状态。
- 外部 ID、原始状态和错误映射。
- 同步、恢复和对账输入。
- 结果未知和人工处理所需证据。

### 5.3 禁止依赖

Platform Backend 不得：

- 直接引用 Runtime 内部 Worker 类。
- 直接访问 Runtime Local Journal。
- 通过共享内存控制外部交易 Session。
- 把 Runtime 日志当作业务数据库。

Runtime 不得：

- 直接调用 Platform Domain 内部 Repository。
- 直接修改 Strategy、Risk、PnL 和 Approval 数据。
- 自行创建第二套 ExecutionBatch。
- 自行决定策略损益归因。

## 6. Command、Query 和 Event

### 6.1 Query

- 可以重复调用。
- 可以缓存。
- 不改变核心业务事实。
- 返回数据时间、来源、质量和版本。
- 支持稳定分页、筛选和权限范围。

### 6.2 Command

- 请求改变业务状态。
- 需要权限、范围、对象版本、风险、审批和幂等检查，适用时。
- 返回 accepted、rejected 或当前业务状态。
- accepted 不等于外部执行完成。
- 高风险 Command 形成审计和追踪上下文。

### 6.3 Event

- 表达已经发生的事实或状态变化。
- 可以重复、延迟、乱序和补发。
- 消费者必须幂等。
- Event 不是跨模块任意修改对象的命令。
- 实时 Event 不是页面恢复的唯一来源。

## 7. 交易可靠性

交易链路：

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
→ platform Order / Fill / Position
```

正式原则：

- platformOrderId 在外部提交前创建。
- 采用至少一次传输和幂等消费。
- 网络超时不等于外部失败。
- `result_unknown` 不是可直接重试的失败终态。
- 外部结果通过 clientOrderId、externalOrderId、历史查询和对账确认。
- Platform API、Runtime 和 Gateway 重启后都必须能够恢复。
- V1 的恢复验收必须覆盖 Fake Gateway、首家 Crypto 真实 API 模拟盘／测试盘和 MT5 Demo／Worker；不能只验证本地 Fake Gateway。

## 8. 数据权威

| 数据 | 主责／权威 |
|---|---|
| 用户、角色、权限和范围 | IAM |
| 标的、合约和执行行情 | Execution Market Data |
| 宏观和研究数据 | Research Data |
| 新闻、日历和理财内容 | Content and Calendar |
| 策略版本、实例和账户绑定 | Strategy |
| 平台命令、执行批次、腿和平台订单 | Trading and Execution |
| 外部订单、成交、余额和持仓事实 | 外部交易系统；平台标准化并持久化 |
| 账户、余额、保证金和持仓视图 | Account and Position |
| 实际损益和策略经济记录 | PnL and Strategy Economic Ledger |
| 风险规则、判断和事件 | Risk |
| 对账和数据质量 | Reconciliation and Data Quality |
| 审批 | Approval and Control |
| 审计 | Audit |
| Runtime、Gateway 和 Worker 实时状态 | Execution Runtime |
| 页面聚合 | Query and Read Models，非写入权威 |

前端缓存、Mock、Runtime OMS、页面表格和原始导入文件均不是平台最终业务权威。

## 9. 数据存储原则

- 核心对象使用稳定平台业务 ID。
- 外部 ID 与平台 ID 分开。
- Order 与 Fill 分开。
- 当前状态、历史 Event 和审计记录分开。
- 金额保留币种、单位和精度。
- 时间保留业务时间、外部时间、接收时间和更新时间。
- 汇率记录来源、价格类型和时间。
- 原始事实与 AdjustmentEntry 分开。
- DataQualityStatus 与 ReconciliationStatus 分开。
- Secret 与普通业务数据分开。
- Runtime Local Journal 与平台业务数据库分开。

## 10. 实时与异步

适合实时更新：

- Quote 和 MarketDataQuality。
- TradeCommand、ExecutionBatch、Order 和 Fill 状态。
- Account、Position、Exposure 和 Risk 状态。
- Gateway、Runtime 和 Worker 状态。

适合后台异步：

- 历史数据同步。
- PnL 重算。
- Reconciliation。
- 报表生成。
- 大批量导入和修正。
- Read Model 重建。

实时通道断开不能终止后台交易和任务。

## 11. 安全与可靠性

Platform Backend 至少具备：

- 服务端 Capability 和 Data Scope 校验。
- DeploymentEnvironment、TradingMode 和 TradingPermissionState 分离。
- Sensitive Field 最小返回。
- Secret 加密、隔离和引用管理。
- Command 幂等和对象版本控制。
- 结果未知、重试和人工处理边界。
- Gateway 和账户故障隔离。
- 高风险审批和 Maker／Checker。
- 关键操作审计。
- 数据备份、恢复和 Reconciliation。
- 未完成 ExecutionBatch 和未知订单恢复。

前端禁用按钮、Runtime connected 和 Gateway heartbeat 不能替代后端安全控制。

## 12. 模块化单体演进原则

初期：

- 领域模块共同部署。
- 通过代码、Repository、Command、Query 和 Event 保持边界。
- 不因同库部署而跨模块任意写入。
- Execution Runtime 独立进程。

只有出现以下证据时评审模块拆分：

- 明显独立扩缩容。
- 严格安全、合规或故障隔离。
- 发布生命周期显著不同。
- 单体成为真实性能或可用性瓶颈。
- 团队已经形成独立维护责任。

## 13. 待专项确认

- 后端语言和 Web 框架。
- ORM、数据库、缓存和消息传输。
- Platform Backend 与 Runtime 的 Envelope 字段。
- Outbox／Inbox 和 Runtime Journal 技术。
- MT5、Crypto 和后续 CTP Adapter 实现。
- 首家 Crypto 真实 API 模拟盘／测试盘 Adapter 和首个 MT5 Demo／Worker Adapter 的验收样板。
- 数据库 Schema 和迁移策略。
- 历史行情和时序数据存储。
- 数据保存、归档、RPO 和 RTO。
- 正式部署拓扑和 Live 安全方案。

上述事项分别进入专项架构、PoC 和 ADR，不由页面或临时代码决定。

## 14. 验收标准

- Platform Backend 与 Execution Runtime 的职责和依赖方向明确。
- Broker、Exchange、MetaTrader5 和 CTP SDK 不进入 Domain 层。
- 每个核心对象只有一个主责领域。
- Platform Backend 保持模块化单体，不提前拆分大量微服务。
- Runtime 独立进程不会形成第二套 Order、Position、Risk 和 PnL 权威。
- Query、Command 和 Event 语义分开。
- 交易链路支持预创建平台订单、幂等、结果未知、恢复和对账。
- 金融AI分析冻结不会阻塞当前后端架构完整性。
