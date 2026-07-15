# Platform V6 后端模块与服务边界

状态：`active`  
适用分支：`refactor/frontend-architecture-v6`  
架构层级：后端架构

## 1. 文档定位

本文档定义 Platform V6 后端的逻辑模块、依赖方向和数据所有权。

当前目标形态是模块化单体，而不是立即拆分大量微服务。逻辑模块必须先在代码、数据访问和职责上保持清晰，未来只有在负载、可靠性或团队协作需要时才独立部署。

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

后端内部建议至少包含：

- IAM
- Market Data
- Strategy
- Trading and Execution
- Account and Position
- PnL and Ledger
- Risk
- Reconciliation and Data Quality
- Audit
- Notification
- Reporting
- Integration Gateway

## 3. 模块边界原则

- 每个核心对象只有一个主责模块。
- 模块只能通过公开应用服务、领域接口或事件协作。
- 禁止跨模块直接修改对方内部表或对象。
- 查询可以形成聚合视图，但不得复制第二套权威状态。
- 同一数据库部署不代表允许任意跨表写入。
- 外部系统 DTO 不进入核心领域层。
- 基础设施实现不能反向决定业务模块边界。

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
- 数据范围判定。
- 高风险操作二次认证结果。

不得负责：

- 交易规则。
- 风险阈值。
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

- 实时和历史行情查询。
- 标的标准化映射。
- 数据新鲜度和来源。
- 市场数据事件。

不得负责：

- 用户交易意图。
- 账户真实余额。
- 最终损益。

## 6. Strategy

拥有：

- StrategyDefinition
- StrategyVersion
- StrategyInstance
- StrategyParameterSet
- StrategyAccountBinding

对外提供：

- 策略定义和版本查询。
- 策略实例状态。
- 已确认参数和账户关系。

不得负责：

- 直接向交易所下单。
- 保存交易所订单最终状态。
- 以页面配置代替策略版本。

## 7. Trading and Execution

拥有：

- TradeIntent
- TradeCommand
- ExecutionBatch
- LegInstruction
- Order
- Execution／Fill
- ExecutionException
- ManualIntervention

对外提供：

- 提交、撤销、平仓和配平命令。
- 执行批次状态。
- 订单和成交查询。
- 执行事件。

依赖：

- IAM：权限。
- Strategy：策略实例和账户绑定。
- Market Data：报价和合约规则。
- Account：资金和保证金快照。
- Risk：执行前检查。
- Integration Gateway：外部订单通信。

Trading 不得自行定义账户余额、风险阈值或损益口径。

## 8. Account and Position

拥有：

- Account
- BalanceSnapshot
- MarginSnapshot
- Position
- PositionSnapshot
- CapitalAllocation

对外提供：

- 账户主档和状态。
- 余额、权益和保证金。
- 当前持仓。
- 策略账户资金视图所需数据。

账户模块负责记录外部账户事实；策略管理页面只是这些事实的管理视图。

## 9. PnL and Ledger

拥有：

- EconomicEvent
- LedgerEntry
- PnLResult
- PnLAttribution
- ValuationSnapshot
- AdjustmentEntry

对外提供：

- 实际损益。
- 损益归因。
- 重算和结算结果。
- 报表数据。

不得：

- 通过覆盖历史结果修正错误。
- 仅依赖页面聚合数据作为账本来源。

## 10. Risk

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
- 风险事件和处置。

Risk 可以读取账户、持仓、订单和损益，但不成为这些对象的权威来源。

## 11. Reconciliation and Data Quality

拥有：

- ReconciliationJob
- ReconciliationResult
- ReconciliationDifference
- DataQualityState
- DataCorrectionRecord

对外提供：

- 订单、成交、持仓、余额和损益核对。
- 数据完整性和差异状态。
- 人工确认和修正记录。

不得直接无痕修改其他模块的原始事实。

## 12. Audit

拥有：

- AuditEvent
- OperatorContext
- ChangeRecord
- SecurityEvent

关键命令、风险覆盖、数据修正、配置变更和人工干预必须形成审计记录。

Audit 接收其他模块事件，不参与普通业务流程的决策。

## 13. Notification

拥有：

- Notification
- DeliveryAttempt
- ReadState
- NotificationPreference

通知来源可以是 Risk、Trading、Data Quality 和 Reporting，但通知模块不重新判断业务严重程度。

## 14. Reporting

拥有：

- ReportDefinition
- ReportJob
- ReportVersion
- ExportArtifact

报表读取权威领域数据或稳定读模型，不在报表模块重新计算一套交易事实。

## 15. Integration Gateway

负责：

- 连接交易所、经纪商、MT5、CTP 或其他外部系统。
- 认证和连接管理。
- 外部协议转换。
- 外部状态码和 symbol 映射。
- 限频、重试和连接健康。

Gateway 不负责：

- 策略业务判断。
- 平台风险规则。
- 完整损益归因。
- 页面接口编排。

## 16. 允许的依赖方向

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

禁止：

- Trading 直接更新 Account 内部表。
- Risk 直接修改 Order 状态。
- Reporting 直接写入 PnL 结果。
- Gateway 直接生成页面 View Model。

## 17. 聚合查询

面向前端的复杂页面可以由 Platform API／BFF 聚合多个模块数据，例如交易执行页组合：

- StrategyInstance。
- QuoteSnapshot。
- BalanceSnapshot。
- RiskDecision。
- ExecutionBatch。

聚合层只负责读取和组装，不拥有这些对象的业务规则。

## 18. 事务边界

- 单模块内的强一致更新可以使用本地事务。
- 跨模块流程通过命令、事件和补偿完成。
- 不为了实现表面上的一次请求而建立超大跨领域事务。
- 交易命令受理、订单提交和外部成交不是同一个事务。

## 19. 未来拆分条件

只有满足以下条件之一才考虑独立服务部署：

- 需要独立扩缩容。
- 需要故障隔离。
- 存在独立安全边界。
- 生命周期和发布节奏明显不同。
- 外部连接需要独立进程。
- 异步计算量显著增大。

拆分服务不得改变稳定领域 ID 和接口语义。

## 20. 验收标准

- 每个核心对象有唯一主责模块。
- 菜单归属不被误作后端服务边界。
- 模块之间不直接修改对方内部数据。
- 外部 Gateway 与业务规则分离。
- 聚合查询不形成第二套权威事实。
- 后续技术选型可以在不推翻模块边界的情况下进行。
