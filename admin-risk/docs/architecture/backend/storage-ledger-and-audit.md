# Platform V6 数据存储、策略经济账本与审计架构

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：后端架构

## 1. 文档定位

本文档定义核心业务数据如何持久化，如何区分当前状态、历史事实、快照和派生结果，以及如何支持损益重算、对账、审批和审计。

本文中的 Ledger 指 **Strategy Economic Ledger（策略经济账本）**，用于策略损益、费用、资金变化和对账，不等于完整财务会计总账。公司会计科目、借贷记账、税务和法定财务报表需要独立架构设计。

本文不绑定具体数据库产品，但规定后续选型必须满足的业务约束。

## 2. 数据分类

### 2.1 主数据

- 用户、角色和能力权限。
- 策略定义、版本和参数集。
- 账户主档。
- 标的和合约规则。
- 风险规则。
- 审批策略。
- 报表定义。

### 2.2 交易事实

- TradeCommand。
- ExecutionBatch。
- LegInstruction。
- Order。
- Execution／Fill。
- MT5 Deal。
- 人工干预。

### 2.3 经济事实

- 成交经济影响。
- 手续费。
- 资金费和隔夜费。
- 借贷利息。
- 入金、出金和内部划转。
- 汇率折算。
- 结算。
- 已确认调整。

### 2.4 当前状态

- 当前 Order 状态。
- 当前 Position。
- 当前账户余额和保证金。
- 当前 ExecutionBatch、配平和暴露状态。
- 当前 RiskStatus 和 TradingPermissionState。
- 当前 StrategyInstanceStatus。

### 2.5 快照

- QuoteSnapshot。
- BalanceSnapshot。
- MarginSnapshot。
- PositionSnapshot。
- ExposureSnapshot。
- RiskSnapshot。
- ValuationSnapshot。
- StrategyNavSnapshot。

### 2.6 派生结果

- PnLResult。
- PnLAttribution。
- StrategyNavSnapshot、策略净值和回撤。
- 风险指标。
- 报表汇总。
- Backend Read Model。

### 2.7 治理记录

- AuditEvent。
- ApprovalRequest 和 ApprovalDecision。
- ReconciliationResult。
- DataCorrectionRecord。
- 配置变更记录。

## 3. 核心存储原则

- 所有核心对象使用稳定平台业务 ID。
- 外部 ID 与平台 ID 分开保存。
- Order 和 Fill 分开存储。
- MT5 场景下 Order、Deal 和 Position 分开存储，Deal 作为成交事实来源。
- TradeCommand 和 ExecutionBatch 分开存储。
- 当前状态和历史状态变化分开。
- 金额和数量保留精度、币种和单位。
- 时间保留事件时间、来源时间、接收时间和更新时间。
- DeploymentEnvironment 与 TradingMode 分开保存。
- 人工修正不覆盖原始事实。
- 数据删除、归档和保留策略明确。
- 敏感凭证不与普通业务数据混存。

## 4. 当前状态与历史

推荐同时保留：

1. 当前状态记录或读模型，用于快速查询。
2. 状态变化记录、领域事件或操作历史，用于追踪和恢复。

例如 Order：

- 当前状态为 `filled`。
- 历史保留 `submitted → acknowledged → partially_filled → filled`。

不得只保存最终状态而丢失过程。

## 5. TradeCommand 与 ExecutionBatch

TradeCommand 至少保存：

- `tradeCommandId`
- `requestId`
- `idempotencyKey`
- 操作人和会话
- StrategyInstance
- DeploymentEnvironment 和 TradingMode
- 命令类型、参数摘要和受理状态
- 创建、校验和受理时间
- 关联 ExecutionBatch，适用时

ExecutionBatch 至少保存：

- `executionBatchId`
- `tradeCommandId`
- 交易腿和目标关系
- ExecutionBatchStatus
- ExecutionBalanceStatus
- ExposureStatus
- 异常、人工处理和结果未知记录
- 创建、更新和完成时间

TradeCommand 受理完成后，执行进度以 ExecutionBatch 为权威。

## 6. 订单与成交

Order 至少保存：

- 平台和外部订单 ID。
- ExecutionBatch 和 LegInstruction。
- StrategyInstance、Account 和 Instrument。
- 方向、类型、数量和价格参数。
- 当前平台状态和外部原始状态。
- 创建、提交和更新时间。

Fill／Deal 至少保存：

- 平台和外部成交 ID。
- Order ID。
- 价格、数量和费用。
- 成交时间和接收时间。
- 原始币种和费用币种。
- 来源系统、账户、Gateway、原始状态和原始记录引用。

Fill／Deal 原则上追加保存，不因订单状态变化被覆盖。MT5 Order 不能单独形成最终成交、持仓、费用或 PnL，必须通过 Deal、Position 和账户历史确认。

## 7. 持仓与暴露

当前 Position 可以来源于：

- 平台 Fill 推导。
- 外部账户同步。
- 对账后的权威结果。

必须明确来源，并同时保留：

- 当前 Position。
- 定期 PositionSnapshot。
- ExposureSnapshot。
- 影响持仓的 Fill 和调整记录。

平台推导持仓与外部持仓不一致时进入对账，不静默覆盖。

## 8. Strategy Economic Ledger

### 8.1 目标

策略经济账本用于：

- 策略损益计算和重算。
- 收益、成本和损失归因。
- 账户和策略资金变化核对。
- 报表和审计追溯。

### 8.2 EconomicEvent

每条经济事件至少包含：

- `economicEventId`
- Account 和 StrategyInstance
- 事件类型
- 金额、币种和方向
- 业务时间
- 来源对象和来源系统
- 数据质量和核对状态
- 原始事件版本

### 8.3 LedgerEntry

LedgerEntry 是 EconomicEvent 的结构化经济影响记录，可以包含：

- 资金增加或减少。
- 费用和收益分类。
- 计价币种折算。
- 关联策略归因项。
- 调整和冲销关系。

当前不要求使用完整会计科目、借贷双方和法定财务科目。若未来建设公司财务总账，应独立形成 Finance Ledger 架构，并通过明确接口接收相关业务事件。

## 9. 损益结果

PnLResult 属于派生结果，应记录：

- 计算口径和版本。
- StrategyVersion。
- 数据截止时间。
- 计价币种。
- 汇率来源和时间。
- 归因项。
- 估算或已结算状态。
- 最近重算时间。

规则变化后可以按新版本重算，但历史正式报表保留原版本。

StrategyNavSnapshot 属于固定时间策略运行净值快照，V1 公式为 `nav = equity / capitalBase`，默认计价 USDT。它不是正式 Fund NAV；未接入或未核对数据不得用前端估算静默替代。

## 10. 调整与修正

错误修正遵循：

- 不删除或覆盖原始事实。
- 创建 DataCorrectionRecord 或 AdjustmentEntry。
- 记录修正前、修正后、原因、操作人和时间。
- 对损益、风险和报表产生影响时触发重算。
- 高风险修正执行权限、审批和审计。
- 调整与原始 EconomicEvent 保持关联。

## 11. 审批和审计

以下操作必须审计，并根据策略判断是否需要审批：

- 交易提交、撤单、平仓和配平。
- 风险规则、额度和阻断修改。
- 人工覆盖风险结果。
- 实盘账户、Gateway 和 StrategyAccountBinding 修改。
- 数据导入、修正和重大对账确认。
- 报表正式版本发布。
- 权限变更。
- DeploymentEnvironment 或 TradingMode 关键配置变化。

审计至少记录：

- `auditEventId`
- 操作人、会话和能力权限
- 操作类型和目标对象
- 变更摘要
- requestId、traceId 和 ApprovalRequest，适用时
- 时间、来源 IP 或客户端信息
- 结果和失败原因

## 12. 数据库事务与事件发布

- 单模块强一致写入使用本地事务。
- 跨模块不建立大范围数据库事务。
- 写入核心事实和待发布事件可使用 Outbox 等可靠发布模式。
- 外部交易结果不属于本地数据库事务。
- 状态变化能够应对重复消息和重放。
- Read Model 投影失败不回滚已经发生的权威事实，应支持重建。

## 13. 并发控制

关键对象使用：

- 版本号或乐观锁。
- 唯一约束。
- 幂等键。
- 有序序列或更新时间。

重点防止：

- 重复交易命令和重复订单。
- 同一 ExecutionBatch 被重复完成。
- 旧事件覆盖新状态。
- 两人同时确认同一对账差异。
- 风险、审批和账户绑定并发修改丢失。
- 同一 ApprovalGrant 被重复使用。

## 14. 缓存和 Read Model

可以缓存：

- 标的基础信息。
- 策略静态定义。
- 历史统计和报表 Read Model。
- 高频查询的只读投影。
- 短期行情和状态摘要。

缓存不得成为以下数据的唯一来源：

- TradeCommand、ExecutionBatch、Order、Fill、Deal、EconomicEvent、StrategyNavSnapshot 和 PnLResult。
- 账户余额和 Position。
- 风险规则和审批授权。
- 权限和审计记录。

Read Model 规则参见 `query-and-read-models.md`。

## 15. 数据保留和归档

后续按类型制定保留周期：

- 订单、成交、策略经济账本、审批和审计：长期保留。
- 行情 Tick：按业务价值和成本分层保存。
- K 线和聚合指标：长期或可重建保存。
- 研究数据：保留修订版本和来源。
- 临时导入文件：完成核对后归档或清理。
- 日志：按安全、运维和审计要求区分周期。

归档不得破坏历史报表、损益重算、对账和审计查询。

## 16. 备份与恢复

至少明确：

- 备份频率。
- RPO 和 RTO。
- 核心数据库和对象存储备份。
- 配置和密钥恢复方式。
- 恢复演练。
- 恢复后订单、持仓、账户、账本和审计对账。

交易、账户、策略经济账本、审批和审计数据优先保障。

## 17. 数据安全

- 密钥和交易凭证使用专用密钥管理或加密存储。
- 日志和审计不输出完整密钥。
- 敏感账户信息按最小权限访问。
- 测试和实盘数据隔离。
- 导出文件具有权限、有效期和访问记录。
- 数据库账号按模块和 DeploymentEnvironment 隔离。

## 18. 技术选型评估标准

数据库和存储方案至少评估：

- 事务能力。
- 数值精度。
- 时间序列查询。
- 写入吞吐。
- 历史追踪和审计能力。
- 备份恢复。
- 运维复杂度。
- 团队掌握程度。
- 与部署环境兼容性。

不因某项技术流行而提前引入过多存储系统。

## 19. 唯一来源

- 公共对象：`../domain-model-boundaries.md`。
- 状态枚举：`../domain/status-enums-and-lifecycles.md`。
- 审批模型：`../domain/approval-and-dual-control.md`。
- Read Model：`query-and-read-models.md`。
- 财务与资金产品边界：对应模块需求和后续 Finance 专项架构。

## 20. 验收标准

- 原始事实、当前状态、快照、Read Model 和派生结果明确分开。
- TradeCommand、ExecutionBatch、Order、Fill 和策略经济账本可追溯。
- MT5 Deal、资金费结算、费用、Swap 和账户账本可追溯。
- 固定时间 StrategyNavSnapshot 可追溯来源、截止时间和质量状态。
- 损益可以基于稳定事实重算。
- 人工修正不会覆盖原始数据。
- Strategy Economic Ledger 不与完整财务会计总账混淆。
- 关键操作具有审批和审计记录，适用时。
- 数据具备备份、恢复和长期归档方案。
