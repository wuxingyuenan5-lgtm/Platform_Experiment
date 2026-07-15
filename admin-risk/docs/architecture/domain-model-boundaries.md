# 前端领域模型边界

状态：`active`  
适用基线：Platform V5

## 1. 目的

在后端和真实数据接入之前，先统一平台核心业务对象及其边界，避免未来每个页面根据接口字段自行定义订单、账户、持仓和损益。

本规范只定义稳定公共语义，不提前设计完整后端协议。

## 2. 建议领域对象

未来可逐步建立：

```text
src/domain/
├─ strategy.ts
├─ account.ts
├─ instrument.ts
├─ position.ts
├─ order.ts
├─ execution.ts
├─ pnl.ts
└─ risk.ts
```

当前不要求立即完成全部文件。

## 3. 对象边界

### Strategy

表示平台纳管的一项策略身份和基础能力。

稳定字段：

- `strategyId`
- 正式名称
- 策略分类
- 能力范围

策略的唯一基础定义来自策略注册表。

### Account

表示交易所、券商或其他执行环境中的资金账户。

稳定字段建议：

- `accountId`
- 账户名称
- 平台或机构
- 币种
- 账户状态

策略账户视图不等于账户主数据；同一个账户可被不同策略引用。

### Instrument

表示可交易或可观察的市场标的。

稳定字段建议：

- `instrumentId`
- symbol
- market
- productType
- currency

页面显示名称和接口 symbol 不应长期混用为同一个字段。

### Position

表示账户在某标的上的实际持仓状态。

稳定字段建议：

- `positionId`
- `strategyId`
- `accountId`
- `instrumentId`
- direction
- quantity
- averagePrice
- unrealizedPnl

双腿策略由多个 Position 组成，不应把双腿硬编码成一个扁平持仓对象。

### Order

表示向执行环境提交的订单意图及生命周期。

稳定字段建议：

- `orderId`
- `strategyId`
- `accountId`
- `instrumentId`
- side
- orderType
- quantity
- price
- status
- createdAt

订单与成交必须区分。

### Execution / Fill

表示订单实际成交结果。

稳定字段建议：

- `executionId`
- `orderId`
- filledQuantity
- filledPrice
- fee
- executedAt

一个订单可以对应多个成交记录。

### PnL

表示按照明确统计范围和口径形成的损益结果。

至少区分：

- realizedPnl
- unrealizedPnl
- fees
- fundingOrCarry
- fxPnl（适用时）
- attributionItems

不同策略的损益细分通过策略级文档定义，不应强行压成完全相同的明细结构。

### Risk

表示规则、风险状态或风险事件。

应区分：

- RiskRule：风险规则。
- RiskSnapshot：某时点风险状态。
- RiskEvent：规则触发或异常事件。
- RiskAction：限制、阻断或人工处理。

当前 V5 风控页中的风险记录、服务状态和通知不应长期使用同一个宽泛对象表达。

## 4. 页面模型、领域模型和接口模型

三者应分开：

- API DTO：外部接口返回结构。
- Domain Model：平台内部稳定业务语义。
- View Model：某个页面需要的展示结构。

建议数据流：

```text
API DTO / Mock DTO
        ↓ adapter
Domain Model
        ↓ selector / mapper
View Model
```

不得让 Vue 组件长期直接依赖后端返回的全部字段。

## 5. 当前实施顺序

1. 保持策略注册表作为 Strategy 基础定义。
2. 在真正需要跨模块复用时建立公共类型。
3. 先统一 Order、Execution、Position 三者边界。
4. 再统一 Account 和 Risk。
5. 损益细分保留策略差异，不提前过度抽象。

## 6. 禁止事项

- 不在没有真实需求时建立庞大 DDD 框架。
- 不提前定义几十个可能永远不用的字段。
- 不把页面卡片结构直接当作领域对象。
- 不把 Order 和 Execution 合并。
- 不把账户主数据和策略账户统计混为一体。
- 不因字段名称相似就认定业务含义相同。

## 7. 验收标准

- 相同业务对象在不同模块中使用相同核心语义。
- 页面展示字段可以变化，但领域身份保持稳定。
- 将来接入后端时，只需新增适配层，不需要重写所有组件类型。
