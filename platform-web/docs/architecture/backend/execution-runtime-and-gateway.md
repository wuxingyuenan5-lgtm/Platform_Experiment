# Platform V6+ Execution Runtime 与 Gateway 架构

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：后端与执行基础设施专项架构

上位约束：

- `../platform-target-architecture.md`
- `backend-overview.md`
- `trading-execution-reliability.md`
- `../integration/realtime-events-and-recovery.md`
- `../domain/status-enums-and-lifecycles.md`
- `../decisions/ADR-008-总体逻辑分层与独立交易Runtime.md`
- `../2026-07-17-开源与外部能力采用矩阵-DRAFT.md`

## 1. 文档定位

本文定义 `execution-runtime` 的正式职责、内部组件、进程和 Worker 模型、Platform Command／Event 契约、Gateway Port、MT5 和 Crypto 接入、后续 CTP 边界、Runtime Local Journal、启动恢复、对账输入、外部手工订单、安全、监控和测试要求。

本文不决定：

- 最终语言和框架。
- Redis Streams、RabbitMQ、NATS、Kafka 或其他传输产品。
- Runtime Journal 使用 SQLite 或其他嵌入式存储。
- 首个 Crypto 交易所和 MT5 经纪商。
- 具体 SDK 版本和许可证接受。
- Live 部署、账户规模和资金规模。

但 V1 必须明确完成两条受控外部接口验收：资费套利至少完成首家 Crypto 交易所真实 API 的模拟盘、测试盘或等价受控账户链路；跨所价差至少完成 Crypto 真实 API 模拟盘／测试盘 + MT5 Demo／Worker 跨 Runtime 链路。Fake Gateway 只是工程验证，不替代真实外部接口验收。

## 2. 核心原则

1. Execution Runtime 独立于 Platform API 进程。
2. Runtime 只接收经过平台受理和授权的执行命令。
3. Runtime 维护实时运行状态，不拥有平台业务规则和永久账本。
4. 外部组件通过 Gateway Adapter 接入，不直接暴露外部 DTO。
5. Platform 与 Runtime 采用至少一次传输和幂等处理。
6. 超时和连接中断不能直接解释为外部失败。
7. Runtime 重启后必须先同步、对账、恢复和风险确认，再进入 READY。
8. MT5、Crypto 和 CTP 可以使用不同 Worker 和依赖，但对上遵守统一契约。
9. 不假设所有 Gateway 支持相同订单、账户、Funding、Transfer 和恢复能力。
10. Runtime 内任何缓存、Journal 和外部框架数据库都不是平台永久业务权威。
11. 真实资金 Live 下单必须在真实 API 模拟盘／测试盘、MT5 Demo、恢复、对账、风控和人工处理验收完成后单独开放。

## 3. 目标结构

```text
Platform Backend
  ↓ Runtime Command Contract
Execution Runtime Main
  ├─ Command Consumer
  ├─ Command Router
  ├─ Runtime Journal
  ├─ Worker Registry
  ├─ Recovery Coordinator
  ├─ Event Normalizer
  ├─ Event Publisher
  ├─ Runtime Health
  ├─ Crypto Worker(s)
  ├─ MT5 Worker(s)
  └─ CTP Worker(s)，后续
       ↓
Gateway Adapter
       ↓
External SDK / Terminal / API
       ↓
Exchange / Broker / Trading System
```

Runtime Main 可以与 Worker 部署于同一节点，但必须允许 Worker 独立重启和故障隔离。

V1 实施前必须确定首家 Crypto Venue 和首家 MT5 Demo Broker／Account。未确定前，不并行扩展多家 Crypto 私有交易 Worker 或多家 MT5 经纪商适配。

## 4. Runtime 对象模型

### 4.1 RuntimeDefinition

描述一种可部署的 Runtime 类型和版本，至少包括：

- `runtimeDefinitionId`。
- Runtime 类型，例如 `trading-runtime`。
- 软件版本和构建身份。
- 支持的 Gateway 类型。
- 支持的 Command／Event Contract 版本。
- 运行依赖和目标操作系统。
- 当前发布状态。

### 4.2 RuntimeInstance

描述一个已注册运行实例，至少包括：

- `runtimeInstanceId`。
- RuntimeDefinitionId。
- DeploymentEnvironment。
- 节点和区域标识。
- 当前 RuntimeStatus。
- 软件和配置版本。
- 支持的 Gateway 和 Worker 摘要。
- 最近心跳、启动和停止时间。
- 当前 RecoveryStatus。
- 是否允许 Live。

### 4.3 RuntimeSession

描述某次进程生命周期：

- `runtimeSessionId`。
- RuntimeInstanceId。
- 进程启动时间和进程身份。
- 上次正常关闭或崩溃原因。
- 当前消费位置和 Event 发送位置。
- 当前配置版本。
- 结束时间和结果。

RuntimeInstance 是稳定配置和注册身份，RuntimeSession 是一次具体运行。

### 4.4 GatewayDefinition

描述某类外部接入实现：

- `gatewayDefinitionId`。
- Gateway 类型：Crypto、MT5、CTP 等。
- Venue／Broker 类型。
- Adapter 版本。
- 支持的 Capability 集合。
- 目标 SDK 或外部接口版本。
- 许可证和维护信息引用。

### 4.5 GatewayRuntime

描述某个 Gateway 在某个 Runtime 中的实际实例：

- `gatewayRuntimeId`。
- GatewayDefinitionId。
- RuntimeInstanceId。
- AccountId 或账户集合。
- WorkerInstanceId。
- 当前 GatewayStatus。
- Connectivity、Synchronization、Readiness 和 TradingCapability。
- 当前配置和 SecretReference。
- 最近心跳、错误和恢复运行。

### 4.6 WorkerDefinition 与 WorkerInstance

WorkerDefinition 描述 Worker 类型和依赖；WorkerInstance 描述当前运行进程或隔离单元。

WorkerInstance 至少包括：

- `workerInstanceId`。
- RuntimeInstanceId。
- WorkerDefinitionId。
- GatewayRuntimeId。
- AccountId 或数据源范围。
- 进程身份。
- 当前 WorkerStatus。
- 最近心跳和错误。
- 当前命令和未发送事件数量。
- 最近启动、停止和重启原因。

## 5. Runtime Main 职责

Runtime Main 负责：

- 从平台命令通道读取 RuntimeCommandEnvelope。
- 校验契约版本、过期时间和 Runtime／Gateway 目标。
- 查询 Runtime Journal 进行 Command 去重。
- 将命令分派给正确 Worker。
- 接收 Worker 原始回报。
- 标准化为 RuntimeEventEnvelope。
- 可靠保存并发送 Event。
- 维护 Runtime、Gateway 和 Worker Registry。
- 协调启动同步、恢复和对账输入。
- 上报健康、配置、能力和积压。

Runtime Main 不负责：

- 重新执行平台用户权限和 Maker／Checker 审批。
- 自行改变 StrategyVersion 和 ExecutionPlan 业务规则。
- 计算正式策略 PnL。
- 直接修改 Platform Backend 内部表。

Runtime 可以执行必要的防御性校验，例如：

- Command 是否过期。
- Gateway 是否支持目标订单类型。
- 数量和价格是否符合当前外部元数据。
- Account、Instrument 和 Gateway 映射是否存在。
- Runtime 是否 READY。

防御性校验不替代 Platform RiskDecision。

## 6. Worker 模型

### 6.1 隔离原则

Worker 按以下因素隔离：

- 外部 SDK 或 Terminal 的线程／进程限制。
- 凭证和账户安全。
- 市场和交易所故障域。
- 订单、行情和账户订阅负载。
- 重启和发布生命周期。
- 日志和对账范围。

### 6.2 MT5 Worker

默认候选原则：

```text
一个正式 MT5 Account
→ 一个 Terminal Instance
→ 一个 MT5 Worker
```

该原则需要 PoC 验证资源占用，但不得在未验证前把多个需要严格隔离的账户放入同一 Terminal Session。

MT5 Worker 负责：

- Terminal 初始化和登录。
- AutoTrading 和 Terminal 状态。
- Symbol 元数据和 Mapping。
- Quote、Account、Order、Deal、Position 和 History 查询。
- 下单、撤单、Pending Order 和部分平仓。
- Hedging／Netting 账户模式。
- Magic Number、Comment 和外部手工订单识别。
- Commission、Swap 和历史补查询。
- Terminal 重启后的重新同步。

V1 MT5 Worker 验收重点是最小闭环和恢复，不是封装高级策略框架。必须能稳定完成初始化、登录、账户读取、SymbolInfo、下单、撤单、Order／Deal／Position 历史查询、Commission／Swap 读取、断线重连、Terminal 重启恢复和错误映射。

### 6.3 Crypto Worker

Crypto Worker 可以按以下方式组织，最终由 PoC 决定：

- 每交易所一个公共行情 Worker。
- 每交易所／账户一个私有交易 Worker。
- 每账户组一个 Worker，但需证明故障和限频隔离。

Crypto Worker 负责：

- Market 和 Contract 元数据。
- Ticker、OrderBook、Trades、OHLCV 和 Funding Rate。
- Account、Balance、Position 和 Margin。
- Spot 和 Perpetual 下单、撤单和查询。
- Client Order ID。
- Private WebSocket 订阅和 REST 补查询。
- FundingSettlement 和账户账本读取。
- 交易所限频、时间同步和重连。

公共行情和私有交易能力可以使用不同 Adapter 或连接，不强制同一 SDK。

V1 Crypto Worker 必须优先服务首家交易所私有链路：行情、Instrument、账户、下单、撤单、订单查询、成交去重、余额／持仓同步、FundingSettlement 或账户账本同步、WebSocket 断线补查询和限频处理。是否使用 CCXT、官方 SDK 或组合 Adapter，以恢复和对账可靠性为第一标准。

### 6.4 CTP Worker

CTP 当前可以延后，但架构预留：

- Front 和 Broker 配置。
- TradingDay 和夜盘。
- 合约、行情、委托、成交、持仓和资金。
- 开仓、平仓、平今和平昨。
- 结算确认和结算文件。
- 重连、查询和恢复。

CTP 的交易日和 Offset 语义不得被 Crypto／MT5 通用模型抹平。

## 7. Gateway Port

平台按能力定义 Port，不要求每个 Gateway 全部实现。

### 7.1 TradingGatewayPort

候选能力：

- `submitOrder`。
- `cancelOrder`。
- `replaceOrder`，支持时。
- `queryOrder`。
- `queryOpenOrders`。
- `queryFills`。
- `closePosition`，仅当外部系统需要专门语义时。

### 7.2 MarketDataGatewayPort

- `subscribeQuote`。
- `subscribeDepth`。
- `unsubscribe`。
- `queryInstrument`。
- `queryTradingSession`。
- `queryMarketStatus`。
- `queryHistoricalBars`，支持时。

### 7.3 AccountGatewayPort

- `queryAccount`。
- `queryBalances`。
- `queryMargin`。
- `queryPositions`。
- `queryAccountHistory`，支持时。

### 7.4 FundingGatewayPort

- `queryFundingRate`。
- `queryFundingSchedule`。
- `queryFundingSettlements`。

FundingRate 与 FundingSettlement 必须分开。

### 7.5 TransferGatewayPort

后续能力：

- `requestTransfer`。
- `queryTransfer`。
- `queryTransferHistory`。

Transfer 不进入普通 TradingGatewayPort。

### 7.6 BorrowGatewayPort

后续能力：

- `queryBorrowAvailability`。
- `borrow`。
- `repay`。
- `queryBorrowHistory`。

### 7.7 TerminalManagementPort

MT5 等终端型系统可以实现：

- `startTerminal`。
- `stopTerminal`。
- `restartTerminal`。
- `queryTerminalStatus`。
- `validateTerminalConfiguration`。

终端运行操作与交易业务 Command 分开授权和审计。

## 8. GatewayCapability

每个 GatewayRuntime 必须声明当前能力，而不是由页面猜测。

候选字段：

- Market Data：Quote、Depth、Kline、Historical Data。
- Order Type：Market、Limit、Stop、Stop Limit、Pending。
- Time In Force：GTC、IOC、FOK、Post Only 等。
- Reduce Only。
- Partial Fill 和 Partial Close。
- Hedging／Netting。
- Client Order ID。
- Funding Rate／Funding Settlement。
- Transfer。
- Borrow／Repay。
- Account History。
- External Manual Order Detection。
- Query by External ID。
- Query by Client Order ID。
- Replace Order。
- Trading Session／Market Status。

Capability 具有版本和更新时间。外部平台、账户模式或权限变化时，Capability 可以变化。

交易页面和 Platform Backend 必须以 Capability 决定当前可执行动作。

## 9. Runtime Command Envelope

候选最小结构：

```text
commandId
commandType
requestId
correlationId
causationId
idempotencyKey
payloadVersion
createdAt
expiresAt
sourceService
sourceEnvironment
tradingMode
runtimeInstanceId
 gatewayRuntimeId
workerInstanceId，适用时
strategyInstanceId
tradeCommandId
executionBatchId
legInstructionId
platformOrderId
operatorContextReference
payload
```

规则：

- Command 必须具有稳定 `commandId`。
- `idempotencyKey` 作用域必须明确。
- `expiresAt` 防止过期执行。
- Command 只传输必要业务参数和稳定引用。
- 不传输 ORM 对象、Python 类实例和 Secret。
- Runtime 不因无法识别未知可选字段而崩溃。
- 不兼容版本明确拒绝并发布结构化事件。

## 10. Runtime Event Envelope

候选最小结构：

```text
eventId
eventType
sourceRuntimeId
sourceRuntimeSessionId
sourceGatewayRuntimeId
sourceWorkerInstanceId
correlationId
causationId
commandId，适用时
strategyInstanceId，适用时
executionBatchId，适用时
legInstructionId，适用时
platformOrderId，适用时
externalReference，适用时
occurredAt
receivedAt
publishedAt
sequence，适用时
payloadVersion
dataQualityStatus
payload
```

规则：

- Event 表达已发生事实，不使用命令式命名。
- Event 可以重复、延迟、乱序和补发。
- `eventId` 用于平台 Inbox 幂等。
- 外部原始时间、Runtime 接收时间和发布时间分开。
- 外部状态和错误码在标准化字段外保留原始引用。
- Fill、FundingSettlement 等不可变事实需要稳定外部 ID 或替代去重键。

## 11. 订单身份与映射

统一身份链：

```text
platformOrderId
↔ clientOrderId / Magic / Comment / Tag
↔ externalOrderId
↔ externalFillId / DealId
```

规则：

- `platformOrderId` 在外部提交前创建。
- `clientOrderId` 由 Platform／Runtime 按外部约束生成或映射。
- 外部系统不支持 clientOrderId 时，使用 Magic、Comment、Tag、时间和账户等组合证据，但必须标记可靠等级。
- externalOrderId 和 externalFillId 按 Venue／Account／Gateway 范围唯一。
- 重启和对账必须能够从外部记录找回 platformOrderId 关系。
- 无法自动归属的订单进入 `unallocated`／`unverified` 和人工处理。

## 12. Runtime Local Journal

Runtime Journal 用于运行可靠性，不是平台业务数据库。

至少保存：

- 已接收和已处理 commandId。
- Command payload 哈希和处理结果摘要。
- 待发送 Runtime Event。
- Event 发送尝试和确认位置。
- platformOrderId 与外部引用映射缓存。
- RuntimeSession 和恢复位置。
- Worker 最近已知同步位置。
- 必要的外部请求证据和错误摘要。

要求：

- 写入顺序支持崩溃恢复。
- 重复 Command 不重复提交外部订单。
- Event 通道不可用时先持久化再重试。
- Journal 损坏或不可用时不能无提示进入 READY。
- Journal 中的敏感数据最小化并加密或受操作系统保护。
- 具有清理、保留、备份或重建政策。

平台数据库仍保存正式业务对象和事件处理结果。

## 13. Command 处理流程

```text
收到 Command
→ 验证 Envelope 和版本
→ 验证目标 Runtime／Gateway／Worker
→ 检查 expiresAt
→ Runtime Journal 幂等检查
→ 检查 Runtime 和 Gateway 是否允许当前动作
→ 写入 command_received
→ 分派 Worker
→ Worker 执行或拒绝
→ 保存结果和待发送 Event
→ 发布 Event
→ 更新 Journal 状态
```

对交易 Command：

- Runtime 不因 Event 发布失败重复外部下单。
- Worker 崩溃时先查询外部状态再决定后续动作。
- 无法确认外部结果时发布 `result_unknown` 相关事件。

## 14. Worker 回报和 Event 流程

```text
External Callback / Query Result
→ Worker Raw Event
→ Normalize and Map
→ Runtime Journal persist
→ Runtime Event publish
→ Platform Event Inbox
→ Domain processing
→ Platform Persistence and Read Model
```

Runtime 标准化必须：

- 保留外部原始 ID、状态和错误。
- 映射稳定 InstrumentId、AccountId 和 platformOrderId。
- 区分 Order、Fill、Position、Balance、Funding 和 Service Status。
- 不在 Adapter 内计算策略 PnL。

## 15. Runtime 状态

状态枚举最终进入公共状态文档。当前候选：

### 15.1 RuntimeStatus

- `starting`。
- `connecting`。
- `synchronizing`。
- `reconciling`。
- `recovering`。
- `risk_confirming`。
- `ready`。
- `degraded`。
- `read_only`。
- `blocked`。
- `stopping`。
- `stopped`。
- `failed`。

### 15.2 GatewayStatus

至少分别表达：

- Liveness。
- Connectivity。
- Authentication。
- Synchronization。
- Readiness。
- TradingCapability。
- MarketDataCapability。
- RecoveryStatus。

禁止只使用一个 `connected` 表示全部能力。

### 15.3 WorkerStatus

- `starting`。
- `running`。
- `degraded`。
- `restarting`。
- `stopped`。
- `failed`。

## 16. 启动、同步和恢复

正式流程：

```text
Runtime start
→ load Runtime Journal
→ register Runtime and Workers
→ load configuration and Secret references
→ connect Gateway
→ synchronize capabilities and instruments
→ synchronize accounts, balances and margins
→ synchronize positions
→ synchronize open orders and recent fills
→ compare with platform recovery scope
→ recover unfinished ExecutionBatch
→ inspect unknown and manual external orders
→ identify residual legs and exposure
→ report Reconciliation input
→ platform Risk confirmation
→ READY / READ_ONLY / BLOCKED
```

恢复期间：

- 禁止无条件新增风险。
- 允许的撤单、减仓和紧急对冲动作由平台政策定义。
- 连接成功不等于 READY。
- 无法完成同步时明确进入 Degraded 或 Read Only。

## 17. 对账协作

Runtime 提供外部事实和查询能力；Platform Reconciliation 拥有正式差异对象和处理流程。

Runtime 至少支持：

- 查询活动和历史 Order。
- 查询 Fill／Deal。
- 查询 Position。
- 查询 Balance 和 Margin。
- 查询 Funding、Commission、Swap 和账户账本，支持时。
- 返回外部原始状态、时间和 ID。

Platform 负责：

- 创建 ReconciliationRun 和 Difference。
- 判断影响策略、账户、执行批次和 PnL。
- 决定阻断、重新同步、自动修复或人工确认。
- 通过 AdjustmentEntry 或正式修正处理差异。

Runtime 不直接接受“覆盖平台记录”的通用命令。

## 18. 外部手工订单和未归属记录

外部系统可能出现：

- 人工下单。
- 其他系统下单。
- 旧系统历史订单。
- Magic／Comment 缺失或冲突。
- 外部持仓与平台 ExecutionBatch 无法对应。

处理规则：

1. Runtime 如实摄取外部事实。
2. 保留 Account、Instrument、外部 ID、时间和原始来源。
3. 尝试根据 clientOrderId、Magic、Comment、Tag、Subaccount 和配置映射归属。
4. 无法确认时标记 `unallocated`／`unverified`。
5. Platform 创建对账差异或人工归属任务。
6. 人工归属必须有权限、证据和审计。
7. 不得因无法归属而丢弃真实成交和持仓。

## 19. MT5 专项要求

### 19.1 Symbol 和合约规格

每个 Broker 的 Symbol Mapping 至少读取：

- Symbol Name 和后缀。
- Contract Size。
- Tick Size 和 Tick Value。
- Digits 和 Point。
- Volume Min、Max 和 Step。
- Margin Currency 和 Profit Currency。
- Trade Mode 和 Session。
- Swap Long、Swap Short 和三倍库存费日，适用时。

不得假设 `XAUUSD` 在不同 Broker 完全相同。

### 19.2 订单和成交

必须区分：

- MT5 Order。
- Deal。
- Position。
- Pending Order。
- Hedging 与 Netting。
- Partial Close。

平台 Order、Fill 和 Position 通过 Adapter 映射，但保留 MT5 ticket 和原始字段。

### 19.3 Magic Number 和 Comment

- 使用受控 Registry 分配 Magic Number 范围。
- Comment 不是唯一可靠归属手段。
- 手工订单和其他 EA 订单必须可识别。
- 冲突和缺失进入对账与人工确认。

### 19.4 组件候选

- 官方 MetaTrader5 Python 包：基础访问优先候选。
- aiomql：异步、Session、重试和查询模式参考或局部复用。
- vn.py Gateway 模式：Adapter 和 Engine 设计参考。
- PyTrader／EA Bridge：当前备用，不进入主路径。

## 20. Crypto 专项要求

### 20.1 产品和账户差异

必须区分：

- Spot。
- Linear Perpetual。
- 其他 Derivative，正式启用后。
- 统一账户、经典账户或子账户。
- One-way 与 Hedge Position Mode。
- Balance、Available、Equity、Margin 和 Wallet 语义。

### 20.2 Funding

必须分别处理：

- 上一期 Funding Rate。
- 当前或预计 Funding Rate。
- 下一结算时间。
- Funding Interval。
- 实际 FundingSettlement。

只有实际结算进入正式 EconomicEvent 和 PnL。

### 20.3 CCXT 与官方接口

CCXT 适合统一公共行情、Market 元数据和部分私有接口，但关键链路必须逐交易所验证：

- createOrder 和最终订单状态。
- Client Order ID。
- Private WebSocket 重连。
- Position Mode 和账户字段。
- FundingSettlement。
- 账户账本和历史范围。
- 交易所特殊参数和错误码。

Binance、OKX 和 Bybit 可以采用 CCXT＋官方 SDK 的组合 Adapter，不要求所有能力来自同一库。

### 20.4 限频和时间同步

- 每个交易所和账户维护独立限频状态。
- 处理服务器时间偏差和签名时间窗口。
- WebSocket 中断后使用 REST 补查询。
- 不因公共行情正常就认为私有交易通道 READY。

## 21. CTP 专项预留

后续 CTP 接入优先评估 vn.py CTP Gateway，但必须通过 Platform Port 封装。

专项要求包括：

- TradingDay、ActionDay、夜盘和自然日分开。
- Open、Close、CloseToday 和 CloseYesterday。
- 合约乘数、价格 Tick 和保证金。
- OrderSysID、OrderRef 和 TradeID 映射。
- 结算确认和结算数据。
- 重连后的订单、成交、持仓和资金恢复。
- 换月属于策略规则，不属于通用 Gateway 自动决定。

## 22. vn.py 采用边界

优先 PoC：

- EventEngine：Runtime 内部事件循环。
- MainEngine：Gateway 和 Engine 宿主。
- OmsEngine：实时 OMS 缓存。
- CTP Gateway：国内期货接入。
- SpreadTrading：同 Runtime 低层腿工具和主动／被动腿参考。
- AlgoTrading：TWAP、Iceberg、Sniper 等低层算法。
- RiskManager：底层订单检查。

必须保留的平台边界：

- Runtime EventEngine 不替代平台 Event Contract。
- OmsEngine 不替代平台永久 Order／Fill。
- SpreadTrading 不替代 ExecutionBatch／ExecutionPlan。
- RiskManager 不替代 RiskDecision。
- vn.py 数据库不替代 Platform Database 和 Economic Ledger。
- 跨 Crypto、MT5 和 CTP 编排仍由平台负责。

## 23. 安全

- Secret 通过 SecretReference 注入 Worker，不进入 Command payload。
- 不在日志中记录 API Key、密码、完整 Token 和敏感签名材料。
- Runtime、Gateway 和 Worker 按 Environment 和 TradingMode 隔离。
- Live Worker 需要明确账户白名单和服务端启用状态。
- 运行控制、重启、配置和 Secret 变更独立授权和审计。
- 外部 API 权限遵循最小权限；只读和交易权限分开。
- 提现、Transfer 和 Borrow 权限默认不与普通交易 Key 共用。

## 24. 可观测性

至少监控：

- Runtime、Gateway 和 Worker Liveness／Readiness。
- Command 接收、去重、处理和失败数量。
- Command 延迟和过期数量。
- Event 待发送、重试和积压。
- Journal 写入和恢复状态。
- 外部连接和认证状态。
- 行情、订单和成交回报延迟。
- 未知订单和结果未知数量。
- 外部手工订单和未归属对象数量。
- 对账差异和恢复运行。
- 单腿暴露和持续时间。
- 限频、错误码和外部拒单。
- Worker 重启次数和原因。

日志至少贯穿：

- requestId。
- correlationId。
- commandId。
- executionBatchId。
- legInstructionId。
- platformOrderId。
- externalOrderId。
- runtimeInstanceId。
- gatewayRuntimeId。
- workerInstanceId。

## 25. 测试和 PoC

### 25.1 契约测试

- Command 和 Event 版本兼容。
- 未知可选字段。
- 不兼容版本拒绝。
- 重复 Command 和 Event。
- 乱序、延迟和补发。

### 25.2 Gateway 合约测试

每个 Gateway 使用统一测试集验证：

- Instrument 和 Capability。
- 下单、撤单和查询。
- 部分成交和多笔 Fill。
- 外部拒单和错误映射。
- Client Order ID。
- Account、Position 和 Margin。
- Funding／Swap／Commission，适用时。
- 断线、重连和历史补查询。

### 25.3 故障测试

- Command 接收后 Runtime 崩溃。
- 外部下单后 Event 发布失败。
- Worker 下单后崩溃。
- 网络超时但外部订单已存在。
- Gateway 重连后迟到回报。
- Runtime Journal 不可用或损坏。
- Platform Event Inbox 暂时不可用。
- 部分成交期间重启。
- 外部手工订单出现。
- Capability 在运行中变化。

### 25.4 发布前测试

- Fake Gateway 完整链路。
- 首家 Crypto 真实 API 模拟盘、测试盘或等价受控账户。
- MT5 Demo／Worker。
- 重启和对账演练。
- 结果未知人工处理。
- 权限、审批、Live Block 和 Kill Switch。

V1 发布前测试必须覆盖三类链路：Fake Gateway、Crypto 真实 API 模拟盘／测试盘、MT5 Demo／Worker。只通过 Fake Gateway 不得视为交易平台 V1 完成。

## 26. 当前已确认与待确认

### 26.1 已确认

- Runtime 独立于 Platform API 进程。
- Runtime Main 与 Worker 分层。
- MT5 和 Crypto 属于初期目标能力。
- CTP 可以延后。
- Port 和 GatewayCapability 按能力设计。
- platformOrderId 在外部提交前存在。
- Runtime 需要本地可靠 Journal。
- 至少一次传输、幂等和结果未知是正式语义。
- Runtime OMS 和 Journal 不成为平台业务权威。
- vn.py、CCXT 和其他组件通过 Adapter 接入。
- V1 必须跑通首家 Crypto 真实 API 模拟盘／测试盘链路。
- V1 跨所价差必须跑通 MT5 Demo／Worker 跨 Runtime 链路。
- CTP 延后，不阻塞资费套利和跨所价差 V1。

### 26.2 待确认

- Runtime 最终语言和进程框架。
- Command／Event 传输产品。
- Journal 存储技术和保留政策。
- MT5 Worker 与 Terminal 的实际资源模型。
- Crypto Worker 的交易所和账户拆分方式。
- CCXT、官方 SDK 或组合 Adapter。
- Runtime Registry 和 Control Plane 的实现位置。
- Worker 自动重启、人工确认和熔断政策。
- Command／Event Envelope 正式 Schema。
- Live 节点网络、安全和 Secret 管理。

其中首家 Crypto Venue、首家 MT5 Demo Broker／Account、私有链路 Adapter 方案和 Runtime 恢复验收样板是 V1 前置决策，不应长期停留在普通待确认状态。

## 27. 验收标准

- Runtime、Gateway、Worker 和 Session 对象边界清晰。
- Platform Backend 与 Runtime 不共享内部对象和业务表。
- MT5、Crypto 和后续 CTP 可通过能力 Port 接入。
- GatewayCapability 可以准确限制页面和 Command 行为。
- Command 和 Event 支持版本、幂等、重复、乱序和结果未知。
- platformOrderId、clientOrderId、externalOrderId 和 Fill 身份可追溯。
- Journal 可以避免 Event 通道故障导致事实丢失，并支持重启恢复。
- Runtime 连接成功不会直接进入 READY。
- 外部手工订单和未归属对象不会被丢弃。
- vn.py、CCXT 和外部 SDK 不形成第二套平台领域和数据权威。
- PoC 覆盖下单、部分成交、重启、对账、结果未知和故障隔离。
- V1 PoC 覆盖 Fake Gateway、首家 Crypto 真实 API 模拟盘／测试盘和 MT5 Demo／Worker，而不是只覆盖本地模拟。
