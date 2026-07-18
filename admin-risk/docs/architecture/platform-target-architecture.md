# Platform V6 简化目标架构

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6 Simplified  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：总体技术架构唯一入口

## 1. 目标

本架构只服务一个近期目标：

> 将当前以页面和 Mock 为主的平台，逐步升级为可连接真实交易账户、可记录订单与成交、可计算策略收益、可进行基础风险控制和对账的内部投资研究与交易平台。

第一阶段不建设完整基金行政管理系统，不追求微服务、事件平台、数据湖或复杂账本。

设计原则：

```text
必要的金融正确性
+
最小可运行结构
+
未来可扩展但不提前实现
```

复杂度控制遵循：

- `decisions/ADR-012-初期架构简化与复杂度控制.md`

## 2. 三个工程主体

初期只保留三个工程主体：

```text
admin-risk
+
platform-backend
+
execution-runtime
```

### 2.1 admin-risk

Vue 前端，负责：

- 页面、图表、表格和交互。
- 发起查询与交易命令。
- 展示策略、账户、订单、持仓、收益和风险状态。
- 展示 Runtime 是否可用、受限或异常。

不负责：

- 直接连接交易所或 MT5。
- 保存交易凭证。
- 判断订单最终结果。
- 保存正式订单、成交和持仓事实。

### 2.2 platform-backend

模块化单体后端，负责：

- 用户、权限和基础配置。
- Strategy、Account、Instrument 主数据。
- TradeCommand、ExecutionBatch、Order、Fill。
- Position、Balance 快照。
- EconomicEvent 和 PnLResult。
- 基础风险检查、对账和审计。
- 向前端提供 REST API；必要时提供 WebSocket 或 SSE。
- 向 Execution Runtime 发送命令并接收事件。

第一阶段使用一个关系型数据库，不拆微服务。

### 2.3 execution-runtime

独立交易执行进程，负责：

- 连接 Crypto Exchange 和 MT5。
- 提交、撤销和查询外部订单。
- 接收成交、持仓、余额和账户回报。
- 维护短期运行状态和本地可靠 Journal。
- 将标准化事件回传 Platform Backend。

Runtime 不负责：

- 用户权限和审批。
- 策略配置。
- 平台风险规则。
- 长期订单、持仓和 PnL 权威。

## 3. 总体结构

```text
Browser
  ↓ REST / WebSocket
admin-risk
  ↓
platform-backend
  ├─ Strategy
  ├─ Trading
  ├─ Account & Position
  ├─ Risk
  ├─ PnL
  └─ Query
  ↓ Runtime Command / Event
execution-runtime
  ├─ Fake Gateway
  ├─ Crypto Gateway
  └─ MT5 Gateway
       ↓
External Trading Systems
```

开发初期三个主体可以运行在同一台机器上，但 `platform-backend` 与 `execution-runtime` 必须保持独立进程。

## 4. 最小业务对象

第一阶段只实现以下对象。

### 4.1 组织与策略

```text
Fund
→ Default Portfolio
→ Default Book
→ StrategyInstance
→ Account
```

规则：

- Fund 创建时自动创建默认 Portfolio 和 Default Book。
- 普通页面不要求用户操作 Portfolio 和 Book。
- 不实现 Investor、ShareClass、申赎和完整基金会计。
- Strategy PnL 不等于正式 Fund NAV。

### 4.2 标的

```text
Instrument
InstrumentMapping
ContractSpecification
```

只解决：

- 平台统一标的。
- TradingView、交易所和 MT5 Symbol 映射。
- 合约乘数、数量单位、最小下单量和价格步长。

### 4.3 账户与持仓

```text
Account
BalanceSnapshot
PositionSnapshot
```

不建设复杂账户树、子账簿或托管账户体系。

### 4.4 交易

```text
TradeCommand
→ ExecutionBatch
→ Order
→ Fill
```

第一阶段不强制实现复杂 ExecutionPlan、LegInstruction 和算法交易对象；需要多腿策略时，可以先在 ExecutionBatch 内用简单 leg 列表表达。

### 4.5 收益

```text
EconomicEvent
→ PnLResult
→ PnLAttributionItem
```

公共归因只保留：

- trading_pnl。
- funding_pnl。
- swap_pnl。
- fees。
- fx_pnl。
- other_adjustment。

策略专项可以保留更细归因，但不扩大公共领域模型。

## 5. 最小交易链路

第一阶段只需要跑通：

```text
前端发起模拟下单
→ platform-backend 创建 TradeCommand
→ 基础权限与风险检查
→ 创建 ExecutionBatch 和 Order
→ Runtime Command
→ Fake Gateway 执行
→ Runtime Event
→ 更新 Order
→ 创建 Fill
→ 更新 PositionSnapshot
→ 生成 EconomicEvent
→ 更新 PnLResult
→ 前端查询结果
```

这条链路跑通之前，不继续扩展新的领域对象。

## 6. 数据与存储

第一阶段采用：

```text
一个关系型数据库
+
execution-runtime 本地 Journal
```

平台数据库保存：

- 主数据。
- 策略和账户。
- 命令、订单和成交。
- 余额和持仓快照。
- EconomicEvent 和 PnLResult。
- 风险结果、对账结果和审计记录。

暂不引入：

- Kafka。
- ClickHouse。
- 数据湖。
- Event Sourcing。
- 复杂 CQRS 基础设施。
- 分布式事务。

查询性能出现真实瓶颈后，再增加缓存或专用 Read Model。

## 7. Platform 与 Runtime 通信

语义遵循：

- 至少一次传输。
- Command 使用幂等键。
- Runtime 执行前写本地 Journal。
- Platform 和 Runtime 都进行重复消息去重。
- 无法确认执行结果时使用 `result_unknown`。
- `result_unknown` 必须先查询外部订单、成交和持仓，再决定是否重试。

第一阶段传输技术可以简单选择数据库轮询、Redis Streams 或轻量消息队列之一；不因架构文档提前固定复杂中间件。

## 8. 状态展示简化

领域内部可以保留必要状态，但前端默认只展示五类运行状态：

```text
可用
处理中
受限
异常
未知
```

Gateway 的连接、认证、同步和交易能力不能在后端语义中混为一谈，但普通用户页面不需要同时展示全部细分状态。

## 9. 金融正确性底线

即使简化，也必须保留：

- 金融数值使用 Decimal，不使用浮点数保存正式金额和数量。
- Money 带 Currency。
- Quantity 带 Unit。
- ContractSpecification 负责 LOT、CONTRACT 与底层资产数量换算。
- Stablecoin 不自动等同 USD。
- occurredAt、receivedAt 和 businessDate 分开。
- 缺失值不自动当零。
- 外部订单、成交和持仓差异不能无痕覆盖。

## 10. 初期不做

以下内容明确延后：

- 完整基金行政管理和 NAV 会计。
- 投资人、份额、申购和赎回。
- 复杂多 Portfolio／多 Book 管理。
- 微服务拆分。
- Kubernetes 和复杂云原生体系。
- 完整 Event Sourcing。
- 通用工作流引擎。
- 通用归因树引擎。
- 高频交易和复杂算法交易平台。
- CTP 接入。
- 金融 AI 分析模块。

## 11. 工程落地顺序

```text
1. platform-backend 工程骨架
2. execution-runtime 工程骨架
3. 数据库最小表结构
4. Fake Gateway
5. 模拟下单闭环
6. 前端接入真实 API
7. Crypto Paper Trading PoC
8. MT5 Demo Account PoC
9. 基础风险与对账
10. 根据真实需求继续扩展
```

## 12. 第一阶段完成标准

满足以下条件即可视为架构第一阶段落地：

- 前端不再依赖交易核心 Mock。
- Fake Gateway 下单链路完整可运行。
- Order、Fill、Position 和 PnL 可以持久化并查询。
- Runtime 重启后可以恢复未完成命令。
- 重复命令不会产生重复订单。
- `result_unknown` 可以进入查询和人工处理流程。
- Crypto Paper 或 MT5 Demo 至少一个真实外部连接 PoC 跑通。
- 不需要依赖微服务、Kafka 或复杂账本才能运行。

## 13. 主要配套文档

近期开发优先阅读：

1. `platform-target-architecture.md`。
2. `decisions/ADR-012-初期架构简化与复杂度控制.md`。
3. `domain/instrument-minimum-model.md`。
4. `domain/account-position-minimum-model.md`。
5. `domain/economic-event-pnl-minimum-model.md`。
6. `integration/runtime-command-event-contract.md`。
7. `domain/status-enums-and-lifecycles.md`，仅在需要具体状态时查阅。

其他较完整架构文档作为参考，不作为第一阶段必须全部实现的范围。