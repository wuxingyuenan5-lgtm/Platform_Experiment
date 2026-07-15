# Platform V6 公共领域模型边界

状态：`active`  
适用分支：`refactor/frontend-architecture-v6`  
架构层级：公共领域模型

## 1. 文档定位

本文档定义 Platform V6 前端、后端、接口适配、数据导入和报表共同使用的核心业务对象及其边界。

领域模型用于表达稳定业务语义，不等同于：

- 后端数据库表。
- 外部交易所或经纪商对象。
- API 请求和响应结构。
- Vue 页面或组件数据结构。
- Mock 文件格式。

总览参见 `domain/domain-overview.md`。

## 2. 模型分层

```text
External API DTO / Import DTO / Mock DTO
                  ↓ adapter
Domain Model
                  ↓ mapper / selector
View Model / Report Model
```

### API／Import／Mock DTO

描述具体数据来源的原始结构，可以随外部系统和接口版本变化。

### Domain Model

描述平台内部稳定的身份、关系、状态和业务含义。

### View Model／Report Model

描述页面、图表、表格或报表需要的展示结构。

禁止 Vue 组件长期直接依赖完整后端响应，也禁止让页面卡片结构反向成为后端领域对象。

## 3. Strategy 领域

### 3.1 StrategyDefinition

表示平台纳管的一项策略定义。

稳定字段：

- `strategyId`
- 正式名称
- 策略分类
- 能力范围
- 基础腿结构
- 基础账户结构

当前前端 `strategyRegistry.ts` 是 StrategyDefinition 的静态展示与能力声明来源，不是未来策略运行状态的最终权威。

### 3.2 StrategyVersion

表示策略逻辑、参数口径或执行规则的版本。

稳定字段：

- `strategyVersionId`
- `strategyId`
- 版本号
- 生效时间
- 状态

### 3.3 StrategyInstance

表示某个策略版本在具体账户、环境和参数下的运行实例。

稳定字段：

- `strategyInstanceId`
- `strategyId`
- `strategyVersionId`
- 运行环境
- 运行状态
- 关联账户

StrategyDefinition、StrategyVersion 和 StrategyInstance 不得混为一个对象。

## 4. Market 与 Instrument 领域

### 4.1 Venue

表示交易所、经纪商或交易环境。

稳定字段：

- `venueId`
- 名称
- 类型
- 市场
- 状态

### 4.2 Instrument

表示可交易或可观察的市场标的。

稳定字段：

- `instrumentId`
- 标准代码
- 页面显示名称
- 外部 symbol 映射
- 市场
- 产品类型
- 计价币种
- 基础资产

页面显示名称和外部接口 symbol 不得长期混用为同一字段。

### 4.3 ContractSpecification

表示合约乘数、最小数量、价格精度和交易规则。

### 4.4 QuoteSnapshot

表示某一时点的行情快照。

至少包含：

- `instrumentId`
- 报价时间
- 接收时间
- 最新价或买卖价
- 数据来源
- QuoteStatus

行情值和行情质量状态必须分开。

### 4.5 FxRateSnapshot

表示某一时点的汇率及其来源，用于多币种折算和损益计算。

## 5. Account 与 Capital 领域

### 5.1 Account

表示交易所、券商、经纪商或其他执行环境中的资金账户主档。

稳定字段：

- `accountId`
- 账户名称
- 平台或机构
- 基础币种
- 账户类型
- 账户状态

策略账户视图不等于账户主数据；同一个账户可以被不同策略引用。

### 5.2 StrategyAccountBinding

表示策略实例与账户之间的用途和关系，例如主腿账户、对冲腿账户或资金账户。

### 5.3 BalanceSnapshot

表示账户某一时点的权益、余额、可用资金和冻结资金。

### 5.4 MarginSnapshot

表示账户某一时点的保证金占用、保证金率和相关风险数据。

### 5.5 CapitalAllocation

表示某账户或资金池分配给某策略的资金额度，不等于账户实际余额。

## 6. Position 与 Exposure 领域

### 6.1 Position

表示账户在某标的上的实际持仓状态。

稳定字段：

- `positionId`
- `strategyInstanceId`
- `accountId`
- `instrumentId`
- 方向
- 数量
- 平均价格
- 已实现损益
- 未实现损益
- 更新时间

双腿或多腿策略由多个 Position 组成，不应将多条腿硬编码成一个扁平持仓对象。

### 6.2 StrategyPositionGroup

用于将多个实际持仓归入同一个策略组合、执行批次或套利组合。

### 6.3 ExposureSnapshot

表示某一时点的方向、名义价值、Delta、汇率或其他未对冲暴露。

暴露状态不等同于持仓状态。

## 7. Trading 与 Execution 领域

### 7.1 TradeIntent

表示用户或策略希望完成的业务目标，例如建立某个资费套利组合。

TradeIntent 不是外部交易所订单。

### 7.2 TradeCommand

表示平台正式受理的交易命令。

稳定字段：

- `tradeCommandId`
- `strategyInstanceId`
- 操作类型
- 提交人
- 提交时间
- 幂等键
- 命令状态

### 7.3 ExecutionBatch

表示为完成同一交易目标而组织的一组交易腿和订单，是双腿或多腿执行的核心聚合对象。

稳定字段：

- `executionBatchId`
- `tradeCommandId`
- `strategyInstanceId`
- 执行批次状态
- 目标配平关系
- 创建时间
- 完成时间

### 7.4 LegInstruction

表示执行批次中的一条交易腿指令。

稳定字段：

- `legInstructionId`
- `executionBatchId`
- 腿角色
- `accountId`
- `instrumentId`
- 方向
- 目标数量
- 订单类型
- 价格参数

### 7.5 Order

表示向执行环境提交的订单意图及生命周期。

稳定字段：

- `orderId`
- `executionBatchId`
- `legInstructionId`
- `strategyInstanceId`
- `accountId`
- `instrumentId`
- 买卖方向
- 订单类型
- 数量
- 价格
- OrderStatus
- 创建时间
- 更新时间

Order 与 Execution／Fill 必须区分。

### 7.6 Execution／Fill

表示订单实际成交结果。

稳定字段：

- `executionId`
- `orderId`
- 成交数量
- 成交价格
- 手续费
- 成交时间

一个 Order 可以对应多个 Execution／Fill。

### 7.7 Allocation／HedgeResult

表示执行批次的实际配平关系、剩余暴露和人工处理结果。

## 8. PnL 与 Economic Event 领域

### 8.1 EconomicEvent

表示产生经济影响的原始事实，例如：

- 成交。
- 手续费。
- 资金费。
- 隔夜费。
- 利息。
- 汇率变动。
- 资金划转。
- 人工调整。

### 8.2 PnLResult

表示按照明确统计范围和口径形成的损益结果。

稳定字段：

- `pnlResultId`
- `strategyInstanceId`
- 统计开始和结束时间
- 计价币种
- 已实现损益
- 未实现损益
- 费用
- 计算版本
- 计算时间

### 8.3 PnLAttributionItem

表示策略特有的损益归因项。

不同策略的明细由对应策略文档定义，不应强行压成完全相同结构。

### 8.4 AdjustmentRecord

表示经过授权的损益或数据调整。调整不得无痕覆盖原始经济事件。

## 9. Risk 领域

### 9.1 RiskRule

表示风险规则、指标、阈值和适用范围。

### 9.2 RiskSnapshot

表示某一时点的风险状态和指标结果。

### 9.3 RiskEvent

表示规则触发、异常或风险状态变化。

### 9.4 RiskDecision

表示执行前检查或人工复核形成的允许、提示、限制、禁止或待确认结果。

### 9.5 RiskAction

表示撤单、阻断、降低额度、人工确认等处置动作。

规则、快照、事件、判断和动作不得使用同一个宽泛 Risk 对象表达。

## 10. Reconciliation 与 Data Quality 领域

### 10.1 ReconciliationTask

表示一次订单、成交、持仓、账户或损益核对任务。

### 10.2 ReconciliationResult

表示核对结果和完成状态。

### 10.3 ReconciliationDifference

表示来源之间的具体差异、金额、数量和处理状态。

### 10.4 DataQualityState

表示数据完整、延迟、缺失、重复、来源冲突或计算异常。

缺失值不得静默转换为零。

### 10.5 ManualConfirmation

表示人工核对、确认或修正行为，应包含操作人、时间、原因和结果。

## 11. Identity、Audit 与 Notification 领域

### User／Role／PermissionCapability

用户、角色和具体操作能力必须区分。角色是能力集合，不是前端按钮权限的唯一判断字段。

### AuditRecord

记录关键命令、配置变化、数据修正、人工干预和权限操作。

### Notification

表示由风险、数据、交易或系统事件产生的通知及阅读状态。

## 12. 核心关系

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
            │         └─ Allocation / HedgeResult
            ├─ Position / ExposureSnapshot
            ├─ PnLResult / AttributionItem
            └─ RiskSnapshot / RiskEvent
```

## 13. 时间、数值和状态

### 时间

根据业务含义区分：

- 业务日期。
- 事件发生时间。
- 外部系统时间。
- 平台接收时间。
- 计算时间。
- 更新时间。

### 数值

金额、价格、数量、比例和汇率必须保留原始数值、单位、币种、精度、来源和时间。

### 状态

至少独立定义：

- QuoteStatus。
- TradeCommandStatus。
- ExecutionBatchStatus。
- OrderStatus。
- PositionStatus。
- RiskStatus。
- ReconciliationStatus。
- DataQualityStatus。

不得使用一个通用状态枚举覆盖全部对象。

## 14. 前端、后端和接口使用规则

### 前端

- Domain Model 转换为 View Model 后再展示。
- 不通过格式化字符串推断核心业务状态。
- 不把页面本地 Mock 作为最终业务事实。

### 后端

- 领域对象不等同于数据库表。
- 业务规则围绕领域身份和生命周期执行。
- 核心状态变化形成可追溯记录。

### 接口

- API DTO 可以适配具体客户端需求。
- 查询、命令和事件使用相同业务 ID。
- 外部系统对象必须通过 Adapter 转换。

## 15. 实施顺序

1. 保持统一策略 ID 和注册表。
2. 统一 Instrument、Account、Position、Order 和 Execution 身份。
3. 建立 TradeCommand、ExecutionBatch 和 LegInstruction。
4. 建立金额、币种、时间和状态的结构化类型。
5. 建立 PnL、Risk、Reconciliation 和 DataQuality 对象。
6. 再形成具体后端模型、API DTO 和前端 View Model。

## 16. 禁止事项

- 不在没有真实需求时建立庞大 DDD 框架。
- 不提前定义大量无法验证的字段。
- 不把页面卡片结构直接当作领域对象。
- 不把 Order 和 Execution 合并。
- 不把账户主档、余额快照和策略资金分配混为一体。
- 不把前端注册表当作真实策略运行状态。
- 不因字段名称相似就认定业务含义相同。

## 17. 验收标准

- 相同业务对象在前端、后端和接口中使用相同稳定身份。
- 页面展示字段可以变化，但领域身份和语义保持稳定。
- 订单、成交、执行批次、持仓和损益边界明确。
- Mock 或外部接口可以通过适配器转换为领域模型。
- 后续接入后端时，不需要因接口字段变化重写所有页面组件。
