# Platform V6 公共领域架构总览

状态：`active`  
适用分支：`refactor/frontend-architecture-v6`

## 1. 文档定位

公共领域架构定义前端、后端、接口、数据库和数据导入共同使用的业务语言。它不描述页面布局，也不等同于数据库表结构。

目标是让“策略、账户、订单、成交、持仓、损益、风险”等概念在不同模块中保持同一含义。

## 2. 三类模型必须分开

```text
External API DTO / Import DTO
            ↓ adapter
Domain Model
            ↓ mapper / selector
View Model / Report Model
```

### API／Import DTO

描述外部接口或文件实际提供的字段。

### Domain Model

描述平台稳定业务语义、身份和生命周期。

### View Model

描述某个页面、图表或报表需要的展示结构。

禁止：

- 把后端响应字段直接长期作为页面模型。
- 把页面卡片结构当作领域对象。
- 把数据库表一比一暴露给前端。

## 3. 核心领域

### 3.1 Strategy

表示平台纳管的策略身份、版本和能力。

核心对象：

- StrategyDefinition。
- StrategyVersion。
- StrategyInstance。
- StrategyAccountBinding。

前端静态注册表属于 StrategyDefinition 的展示能力声明，不代表真实运行实例。

### 3.2 Market and Instrument

核心对象：

- Venue。
- Instrument。
- ContractSpecification。
- QuoteSnapshot。
- MarketDataSeries。
- FxRateSnapshot。

必须区分页面显示名称、标准标识和外部接口 symbol。

### 3.3 Account and Capital

核心对象：

- Account。
- BalanceSnapshot。
- MarginSnapshot。
- CapitalAllocation。
- AccountStatus。

账户主档、账户某时点余额和策略资金分配是不同对象。

### 3.4 Position

核心对象：

- Position。
- PositionSnapshot。
- StrategyPositionGroup。
- ExposureSnapshot。

双腿策略由多个 Position 组成，不把两腿硬编码为一个扁平持仓对象。

### 3.5 Trading and Execution

核心对象：

- TradeIntent。
- TradeCommand。
- ExecutionBatch。
- LegInstruction。
- Order。
- Execution／Fill。
- Allocation／HedgeResult。

必须区分：

- 用户或策略想做什么。
- 后端受理了什么命令。
- 执行批次包含哪些交易腿。
- 向外部系统提交了哪些订单。
- 实际发生了哪些成交。

### 3.6 PnL and Economic Event

核心对象：

- EconomicEvent。
- PnLResult。
- PnLAttributionItem。
- ValuationSnapshot。
- AdjustmentRecord。

损益结果必须具有统计范围、时间、币种和计算版本。

### 3.7 Risk

核心对象：

- RiskRule。
- RiskSnapshot。
- RiskEvent。
- RiskDecision。
- RiskAction。
- LimitUsage。

风险状态、规则触发和处置动作是不同对象。

### 3.8 Reconciliation and Data Quality

核心对象：

- ReconciliationTask。
- ReconciliationResult。
- ReconciliationDifference。
- DataQualityState。
- ManualConfirmation。

缺失数据不能静默转换为零值。

### 3.9 Identity, Audit and Notification

核心对象：

- User。
- Role。
- PermissionCapability。
- AuditRecord。
- Notification。

角色是权限集合，不能替代具体操作能力。

## 4. 核心关系

```text
StrategyDefinition
  └─ StrategyInstance
       ├─ AccountBinding ── Account
       ├─ TradeCommand
       │    └─ ExecutionBatch
       │         ├─ LegInstruction
       │         │    └─ Order
       │         │         └─ Execution / Fill
       │         └─ ExposureSnapshot
       ├─ Position
       ├─ PnLResult
       └─ RiskSnapshot
```

订单、成交、持仓和损益通过稳定 ID 和业务关联建立联系，不依赖显示名称或表格行号。

## 5. 身份和版本

核心对象应使用稳定业务 ID：

- `strategyId`
- `strategyInstanceId`
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

需要重算或历史追溯的对象应保留版本、计算时间和来源。

## 6. 时间语义

根据对象区分：

- 业务日期。
- 事件发生时间。
- 外部系统时间。
- 平台接收时间。
- 计算时间。
- 更新时间。

不能只使用一个通用 `time` 字段表达全部含义。

## 7. 数值语义

金额、价格、数量、比例和汇率必须保留：

- 原始数值。
- 单位。
- 币种。
- 精度。
- 来源。
- 时间。

页面格式化后的 `+1,234.56 USDT` 不是领域模型中的原始金额。

## 8. 状态语义

不同对象使用独立状态：

- QuoteStatus。
- TradeCommandStatus。
- ExecutionBatchStatus。
- OrderStatus。
- PositionStatus。
- RiskStatus。
- ReconciliationStatus。
- DataQualityStatus。

不能使用一个通用 `status` 枚举覆盖全部对象。

## 9. 领域模型与模块展示

同一对象可以在多个模块展示：

- 交易平台展示当前执行批次和即时风险。
- 策略管理展示完整历史订单、持仓和损益。
- 风险管理展示风险摘要、事件和处置。

展示目的不同不代表建立三套 Order、Position 或 Risk 定义。

## 10. 建设原则

- 先统一对象身份和边界，再扩充字段。
- 不一次性建立庞大 DDD 框架。
- 只为真实业务关系建立对象。
- 策略特有损益明细保留差异，不强制压成完全相同结构。
- 外部系统对象通过 Adapter 转换，不直接成为平台领域对象。
- 公共领域对象不得包含 Vue 组件、CSS 或页面配置。

## 11. 详细规范

详细对象定义和当前实施顺序参见：

- `../domain-model-boundaries.md`

后续新增具体对象时，应优先更新详细规范，再形成前端类型、后端模型和接口契约。
