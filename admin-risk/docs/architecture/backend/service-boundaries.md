# Platform V6 后端模块与服务边界

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：后端架构

## 1. 文档定位

本文档定义 Platform V6 后端逻辑模块、依赖方向、数据所有权和跨模块协作方式。

当前目标形态是模块化单体，而不是立即拆分大量微服务。逻辑模块必须先在代码、数据访问和职责上保持清晰，未来只有在负载、可靠性、安全或团队协作需要时才独立部署。

## 2. 总体结构

```text
Platform API / BFF
        ↓
Application Modules
        ↓
Domain Modules
        ↓
Repository Interfaces / Event Ports
        ↓
Infrastructure Adapters
```

后端逻辑模块包括：

- IAM
- Market Data
- Research Data
- Content and Calendar
- Strategy
- Trading and Execution
- Account and Position
- PnL and Strategy Economic Ledger
- Risk
- Reconciliation and Data Quality
- Approval and Control
- Audit
- Notification
- Reporting
- Integration Gateway
- Query and Read Model

这些模块初期可以共同部署，但不得互相绕过公开边界直接写入内部数据。

## 3. 模块边界原则

- 每个核心对象只有一个主责模块。
- 模块通过公开应用服务、领域接口或事实事件协作。
- 禁止跨模块直接修改对方内部表或对象。
- 查询可以形成聚合 Read Model，但不得复制第二套权威状态。
- 同一数据库部署不代表允许任意跨表写入。
- 外部 DTO 不进入核心领域层。
- 基础设施实现不能反向决定业务边界。
- 产品菜单归属不等于后端模块归属。

## 4. IAM

拥有：

- User
- Role
- Capability
- DataScope
- Session
- CredentialPolicy

对外提供：

- 身份认证。
- 当前用户能力集合。
- 数据范围判断。
- 高风险操作二次认证结果。

不得负责：

- 交易规则。
- 风险阈值。
- 审批业务结论。
- 页面菜单结构。

## 5. Market Data

拥有：

- Venue
- Instrument
- ContractSpecification
- QuoteSnapshot
- Kline
- FundingRate
- FxRateSnapshot
- MarketDataQuality

对外提供：

- 交易执行所需实时和历史行情。
- 标的和合约标准化映射。
- 数据新鲜度、来源和质量。
- 市场数据事件。

不得负责：

- 宏观和公司研究数据的全部生命周期。
- 新闻和日历内容。
- 用户交易意图。
- 账户真实余额。
- 最终损益。

## 6. Research Data

拥有：

- ResearchSeries
- ResearchObservation
- ResearchRevision
- DerivedResearchIndicator
- ResearchDataQuality

对外提供：

- 宏观、资产、公司和行业研究数据。
- 历史修订和观察期语义。
- 研究衍生指标及计算版本。
- 看板和金融 AI 所需研究查询。

不得负责：

- 实时订单提交所需的最终 QuoteSnapshot。
- 新闻原文和内容编辑。
- 交易、账户和损益事实。

详细边界参见 `research-data-and-content-boundaries.md`。

## 7. Content and Calendar

拥有：

- ContentItem
- NewsSource
- CalendarEvent
- ProductInformation
- ContentRevision
- ReviewState

对外提供：

- 新闻、摘要、宏观事件和理财信息。
- 内容版本、审核和失效状态。
- 首页、新闻日历与理财、金融 AI 所需查询。

不得负责：

- 将自然语言内容直接转为交易命令。
- 交易行情质量判断。
- 订单和损益事实。

## 8. Strategy

拥有：

- StrategyDefinition
- StrategyVersion
- StrategyInstance
- StrategyParameterSet
- StrategyAccountBinding

对外提供：

- 策略定义和版本查询。
- 策略实例状态。
- 已确认参数。
- 策略与账户角色关系。

所有权规则：

- StrategyAccountBinding 由 Strategy 拥有。
- Account 模块拥有 Account 主档和账户状态。
- Strategy 通过 `accountId` 引用账户并验证其可用性。

不得负责：

- 直接向交易所下单。
- 保存外部订单最终状态。
- 保存账户余额最终事实。
- 用前端页面配置替代策略版本。

## 9. Trading and Execution

拥有：

- TradeIntent
- TradeCommand
- ExecutionBatch
- LegInstruction
- Order
- Execution／Fill
- ExecutionBalanceResult
- ExecutionException
- ManualIntervention

对外提供：

- 提交、撤销、平仓和配平命令。
- 执行批次、订单和成交查询。
- 执行、异常和恢复事件。

依赖：

- IAM：权限。
- Strategy：策略实例和账户绑定。
- Market Data：报价和合约规则。
- Account：余额、保证金和账户状态。
- Risk：执行前判断和阻断。
- Approval：高风险授权，适用时。
- Integration Gateway：外部订单通信。

Trading 不得自行定义账户余额、风险阈值、审批规则或损益口径。

## 10. Account and Position

拥有：

- Account
- AccountRestriction
- BalanceSnapshot
- MarginSnapshot
- Position
- PositionSnapshot
- CapitalAllocation

对外提供：

- 账户主档和状态。
- 余额、权益和保证金。
- 当前持仓和持仓快照。
- 策略账户资金视图所需事实。

Account 不拥有 StrategyAccountBinding。策略管理页面只是账户和持仓事实的管理视图。

## 11. PnL and Strategy Economic Ledger

拥有：

- EconomicEvent
- LedgerEntry
- PnLResult
- PnLAttribution
- ValuationSnapshot
- AdjustmentEntry

对外提供：

- 实际损益。
- 策略损益归因。
- 重算和结算结果。
- 策略经济事件和账本查询。
- 报表所需稳定结果。

当前模块建设的是 Strategy Economic Ledger，不等于完整财务会计总账。

不得：

- 通过覆盖历史结果修正错误。
- 仅依赖页面聚合数据作为账本来源。
- 在没有正式会计需求时擅自扩展为法定财务总账。

## 12. Risk

拥有：

- RiskRule
- RiskLimit
- RiskSnapshot
- RiskDecision
- RiskEvent
- RiskResolution
- GlobalTradingBlock

对外提供：

- 执行前风险判定。
- 当前风险状态。
- 风险规则和限制。
- 风险事件和处置结果。

Risk 可以读取账户、持仓、订单和损益，但不成为这些对象的权威来源。

## 13. Reconciliation and Data Quality

拥有：

- ReconciliationJob
- ReconciliationResult
- ReconciliationDifference
- DataQualityState
- DataCorrectionRecord

对外提供：

- 订单、成交、持仓、余额、损益和账本核对。
- 数据完整性、延迟、冲突和差异状态。
- 人工确认和修正流程。

不得无痕修改其他模块原始事实。修正通过授权命令、调整记录和重算完成。

## 14. Approval and Control

拥有：

- ApprovalPolicy
- ApprovalRequest
- ApprovalDecision
- ApprovalGrant

对外提供：

- 某项操作是否需要审批。
- 审批请求和决定。
- Maker／Checker 约束。
- 与目标对象、参数、环境和有效期绑定的短期授权。

Approval 不负责：

- 用户基础权限。
- 风险业务判断。
- 目标命令执行。
- 审计记录的最终持久化。

详细模型参见 `../domain/approval-and-dual-control.md`。

## 15. Audit

拥有：

- AuditEvent
- OperatorContext
- ChangeRecord
- SecurityEvent

关键命令、审批、风险覆盖、数据修正、配置变更和人工干预必须形成审计记录。

Audit 接收其他模块事实，不参与普通业务流程决策。

## 16. Notification

拥有：

- Notification
- DeliveryAttempt
- ReadState
- NotificationPreference

通知来源可以是 Risk、Trading、Approval、Data Quality 和 Reporting，但 Notification 不重新判断业务严重程度。

## 17. Reporting

拥有：

- ReportDefinition
- ReportJob
- ReportVersion
- ExportArtifact

Reporting 读取权威领域数据或稳定 Read Model，不重新计算第二套交易事实、损益口径或风险规则。

## 18. Integration Gateway

负责：

- 连接交易所、经纪商、MT5、CTP 或其他外部系统。
- 认证和连接管理。
- 外部协议转换。
- 外部状态、symbol 和 ID 映射。
- 限频、重试和连接健康。

Gateway 不负责：

- 策略业务判断。
- 平台风险规则。
- 审批规则。
- 完整损益归因。
- 页面接口编排。

## 19. Query and Read Model

负责：

- 聚合多个领域的只读结果。
- 为页面、报表和查询场景形成稳定 Read Model。
- 管理查询投影、缓存、失效和重建。
- 表达数据时间、来源版本和 DataQualityStatus。

Query 层不得：

- 接受领域写入命令。
- 成为订单、账户、持仓、损益或风险的新权威。
- 在聚合过程中重新实现业务规则。

详细规范参见 `query-and-read-models.md`。

## 20. 允许的依赖方向

```text
Platform API
  → Application Services
  → Domain Modules
  → Ports
  → Infrastructure Adapters
```

领域模块之间优先通过：

1. 只读应用接口。
2. 明确领域服务。
3. 已发生事实事件。
4. ApprovalGrant，适用于受控高风险操作。

禁止：

- Trading 直接更新 Account 内部表。
- Risk 直接修改 Order 状态。
- Reporting 直接写入 PnLResult。
- Gateway 直接生成页面 View Model。
- Query Read Model 接受业务写入。
- Content 模块直接生成交易命令。

## 21. 聚合查询

Platform API／BFF 可以聚合多个模块，例如交易执行工作台读取：

- StrategyInstance。
- QuoteSnapshot。
- BalanceSnapshot 和 MarginSnapshot。
- RiskDecision。
- TradingPermissionState。
- 当前 ExecutionBatch。

聚合层只负责读取和组装。复杂稳定查询可以通过 Backend Read Model 提供。

## 22. 事务边界

- 单模块内强一致写入使用本地事务。
- 跨模块流程通过命令、事件和补偿完成。
- 交易命令受理、订单提交和外部成交不是同一个事务。
- 写入核心事实与待发布事件可使用 Outbox 等可靠发布模式。
- 不为表面上的单次请求建立超大跨领域事务。

## 23. 未来拆分条件

只有满足以下条件之一才考虑独立部署：

- 独立扩缩容。
- 故障隔离。
- 独立安全边界。
- 生命周期和发布节奏明显不同。
- 外部连接需要独立进程。
- 异步计算量显著增大。

拆分服务不得改变稳定领域 ID 和接口语义。

## 24. 唯一来源

- 公共对象：`../domain-model-boundaries.md`。
- 状态枚举：`../domain/status-enums-and-lifecycles.md`。
- 研究数据边界：`research-data-and-content-boundaries.md`。
- 查询和 Read Model：`query-and-read-models.md`。
- 审批模型：`../domain/approval-and-dual-control.md`。

## 25. 验收标准

- 每个核心对象具有唯一主责模块。
- StrategyAccountBinding 归属 Strategy，Account 主档归属 Account。
- 交易行情、研究数据和内容数据分开。
- 查询聚合不形成第二套权威事实。
- 外部 Gateway 与业务规则分离。
- 权限、审批、风险、审计和命令执行职责分开。
- 后续技术选型可以在不推翻模块边界的情况下进行。
