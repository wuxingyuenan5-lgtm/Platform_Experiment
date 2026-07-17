# Platform V6+ 总体目标架构

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：总体技术架构

配套文档：

- `README.md`
- `backend/backend-overview.md`
- `backend/service-boundaries.md`
- `integration/frontend-backend-integration.md`
- `domain/domain-overview.md`
- `2026-07-17-开源与外部能力采用矩阵-DRAFT.md`
- `decisions/ADR-005-技术架构分层.md`
- `decisions/ADR-006-后端优先采用模块化单体.md`
- `decisions/ADR-007-部署环境与交易模式分离.md`
- `decisions/ADR-008-总体逻辑分层与独立交易Runtime.md`

## 1. 文档定位

本文定义 Variable-Global 平台的正式总体目标架构，包括：

- 产品架构、架构文档视角、逻辑职责层和工程运行单元之间的关系。
- Vue 前端、模块化单体业务后端和独立交易 Runtime 的职责边界。
- Strategy、Trading、Account、Risk、Reconciliation、PnL 等业务领域的协作方式。
- MT5、Crypto 和后续 CTP 等外部交易系统的接入边界。
- Command、Event、数据权威、恢复、对账、安全和审计的总体原则。
- vn.py、CCXT、MetaTrader5、aiomql 等外部组件的采用边界。

本文不决定：

- V1 范围、工期、负责人和 Issue。
- 最终编程语言、数据库、缓存、消息中间件和云产品。
- 首个 Crypto 交易所、MT5 经纪商和 Live 账户。
- 具体风险阈值、策略参数和交易规模。
- 金融AI分析的专项需求和架构；该模块当前冻结。

## 2. 四个不同的架构维度

平台必须区分以下四个维度，不得互相替代。

### 2.1 六个一级产品模块

六个一级产品模块回答“用户从哪里进入、完成什么任务”：

1. 首页。
2. 对冲基金看板。
3. 新闻日历与理财。
4. 策略。
5. 风险管理。
6. 金融AI分析，当前冻结。

产品菜单不直接决定后端服务、数据库、进程或代码包。

### 2.2 四类架构文档视角

ADR-005 定义的四类架构视角继续有效：

1. 前端架构。
2. 后端架构。
3. 前后端协作架构。
4. 公共领域模型。

这是文档和设计观察角度，不是运行时层级。

### 2.3 六层逻辑职责

平台逻辑职责分为：

1. 产品与交互层。
2. 平台应用与控制层。
3. 核心业务领域层。
4. 交易执行与连接层。
5. 数据、账本与查询层。
6. 运行保障与基础设施层。

六层是职责和依赖方向，不代表六套服务、六个数据库、六个仓库或六支团队。

### 2.4 三个初期工程主体

初期工程和运行主体为：

```text
Variable-Global
├─ admin-risk
│  └─ Vue 前端
├─ platform-backend
│  └─ 模块化单体业务后端
└─ execution-runtime
   └─ 独立交易执行、Gateway 和 Worker 运行时
```

三个主体可以在开发或早期环境运行于同一台机器，但必须保持代码、依赖、进程、凭证和故障边界。

## 3. 总体结构

```text
Browser
  ↓ Query / Command / Subscription
admin-risk
  ↓ REST / WebSocket / SSE
Platform API / BFF
  ↓
Application Modules
  ↓
Domain Modules
  ↓ Repository / Query / Command / Event Ports
Platform Persistence and Read Models
  ↓ Reliable Runtime Command / Event Contract
Execution Runtime Main
  ├─ Crypto Gateway Worker(s)
  ├─ MT5 Worker(s)
  └─ CTP Worker(s)，后续
       ↓
Exchange / Broker / MT5 Terminal / CTP
```

关键原则：

- 浏览器不保存正式交易真相。
- Platform Backend 是业务控制和平台持久化主体。
- Execution Runtime 是外部交易执行和连接主体。
- 外部系统是外部订单、成交、余额和持仓事实来源。
- 平台通过同步、事件、对账和修正形成标准化业务事实。
- Read Model 服务查询，不形成第二套写入权威。

## 4. 六层逻辑职责

### 4.1 产品与交互层

主要由 `admin-risk` 承担。

负责：

- 页面、路由、筛选、图表、表格和交互。
- Query 展示和 Command 输入。
- 权限、环境、模式、质量和状态的可见表达。
- 实时更新以及断线后的 Query 恢复。
- 跨模块稳定 ID 和安全上下文跳转。

不负责：

- 保存交易凭证。
- 直接连接交易所、MT5 或 CTP。
- 判断外部订单最终结果。
- 维护正式 Order、Fill、Position、Balance、PnL 和 Risk 事实。
- 以定时器、Mock 或本地状态模拟真实成交。

### 4.2 平台应用与控制层

由 Platform Backend 的 API 和 Application 层承担。

负责：

- 身份、Capability、Data Scope、Environment Scope 和 TradingMode Scope 校验。
- 用例编排、Command 受理、幂等和并发控制。
- Maker／Checker 和 ApprovalGrant 校验。
- StrategyInstance、账户绑定和交易许可检查。
- RiskDecision 请求和执行前检查。
- TradeCommand、ExecutionBatch 和人工干预编排。
- Query 聚合、审计上下文和结果返回。

不负责：

- 直接调用 Broker SDK 或 MetaTrader5 包。
- 在 HTTP 请求中等待外部订单最终成交。
- 代替领域对象保存长期业务规则。

### 4.3 核心业务领域层

初期在模块化单体内按稳定领域组织：

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
- Query and Read Models。

每个领域必须明确：

- 拥有的对象和稳定 ID。
- 可执行 Command。
- 对外 Query。
- 发布或消费的 Event。
- 数据权威。
- 不负责内容。
- 对其他领域的依赖方向。

### 4.4 交易执行与连接层

由 `execution-runtime` 承担。

负责：

- Runtime Main、Gateway Adapter、Worker 和外部 Session。
- 外部认证、连接、限频、重连和心跳。
- 行情订阅、合约和账户同步。
- 外部订单提交、撤销、查询和回报接收。
- Runtime 内实时 OMS 缓存。
- 低层追价、TWAP、Iceberg、Sniper 等算法能力。
- Runtime Command 去重和 Event 可靠发送。
- 外部状态、错误和 Symbol 映射。
- 启动同步、对账输入和恢复报告。

不负责：

- 用户权限和审批。
- StrategyVersion 和 StrategyAccountBinding。
- 平台 RiskRule 和 RiskDecision。
- 平台 ExecutionBatch 的最终业务生命周期。
- 策略 PnL 和 Economic Ledger。
- 以 Runtime 本地数据库替代平台永久事实。

### 4.5 数据、账本与查询层

由 Platform Backend 的持久化、计算和 Read Model 模块承担。

负责：

- 平台业务对象和交易事实持久化。
- 外部 ID 与平台 ID 映射。
- Order、Fill、Position、Balance 和 Margin 快照。
- EconomicEvent、LedgerEntry、PnLResult 和 AdjustmentEntry。
- ReconciliationResult、DataQualityStatus 和修正记录。
- Research Data、Content Data 和历史行情，按数据架构。
- Backend Read Model、报表版本和导出产物。
- 数据版本、血缘、截止时间和完整度。

原则：

- Runtime OMS 不是永久账本。
- Read Model 不是业务写入入口。
- 原始事实不因修正被无痕覆盖。
- 缺失值不得静默当作零。

### 4.6 运行保障与基础设施层

负责：

- 配置、Secret 和环境隔离。
- Runtime Registry、Supervisor 和运行控制。
- Command／Event 传输和可靠性基础。
- 日志、指标、追踪、告警和事故处理。
- 发布、回滚、备份和恢复。
- 数据库、缓存和异步任务运行。
- 依赖健康、限流、熔断和容量管理。

基础设施不得反向定义业务对象、状态和规则。

## 5. 三个工程主体

### 5.1 admin-risk

负责前端产品实现，不持有 Broker SDK、Secret 和正式业务数据库连接。

依赖方向：

```text
Router
→ Module Shell
→ Page Orchestrator
→ Use Case / Composable
→ Domain Model / View Model
→ Repository Interface
→ API Adapter
```

### 5.2 platform-backend

采用模块化单体：

```text
Platform API / BFF
→ Application Modules
→ Domain Modules
→ Repository / Event / Runtime Ports
→ Infrastructure Adapters
```

要求：

- 领域模块在代码和数据写入上保持边界。
- 同库不代表允许任意跨表写入。
- API DTO、Domain Model、ORM Model 和 Read Model 分开。
- Broker、Exchange、MT5 和 CTP SDK 不进入 Domain 层。
- 业务模块不能直接依赖 execution-runtime 内部代码。

### 5.3 execution-runtime

必须独立于 Platform API 进程运行。

候选内部结构：

```text
execution-runtime
├─ runtime-main
│  ├─ command-consumer
│  ├─ event-publisher
│  ├─ runtime-journal
│  ├─ worker-registry
│  └─ recovery-coordinator
├─ gateways
│  ├─ crypto
│  ├─ mt5
│  └─ ctp，后续
├─ workers
└─ adapters
```

初期需要支持 Crypto 和 MT5；CTP 接入可以延后，但 Port、Instrument 和交易日语义不能被 Crypto 或 MT5 特性锁死。

## 6. Platform Backend 与 Runtime 的正式边界

### 6.1 Platform Backend 拥有

- 用户身份、Capability 和数据范围。
- StrategyDefinition、StrategyVersion 和 StrategyInstance。
- StrategyAccountBinding。
- TradeIntent 和 TradeCommand。
- ExecutionBatch 和版本化 ExecutionPlan。
- LegInstruction 和平台 Order 身份。
- RiskDecision、ApprovalGrant 和 GlobalTradingBlock。
- 平台标准化 Order、Fill、Position 和账户快照。
- Reconciliation、EconomicEvent、PnLResult 和 Audit。

### 6.2 Runtime 拥有

- RuntimeInstance、RuntimeSession 和 WorkerSession 的实时状态。
- Gateway 连接、外部订阅和当前能力状态。
- 当前活动订单、成交缓存和外部请求状态。
- 已处理 Command、待发送 Event 和恢复位置的本地运行记录。
- 外部 API 原始错误、返回和映射上下文。

### 6.3 Runtime 不得成为的权威

- Strategy 和账户绑定权威。
- 平台永久 Order／Fill 数据库。
- PnL 和账本权威。
- 用户权限、审批和风险规则权威。
- 报表和策略管理 Read Model 权威。

## 7. 统一交易链路

### 7.1 命令受理

```text
User Input
→ Frontend Command DTO
→ Platform API
→ Permission / Scope / Version Check
→ Strategy / Account / Risk / Approval Check
→ TradeCommand accepted or rejected
```

`accepted` 只表示平台已经可靠受理，不表示外部订单成功。

### 7.2 执行编排

```text
TradeCommand
→ ExecutionBatch
→ ExecutionPlan
→ LegInstruction
→ pre-created platform Order
→ Runtime Command
```

平台 Order 身份必须先于外部提交存在，以支持结果未知、重启恢复和对账。

### 7.3 外部执行

```text
Runtime Command
→ Worker / Gateway Adapter
→ Broker or Exchange
→ externalOrderId / broker status
→ Runtime Event
```

### 7.4 平台回报处理

```text
Runtime Event
→ Event Inbox / Idempotency
→ Trading / Account / Reconciliation
→ Platform Persistence
→ EconomicEvent / PnL / Read Model
→ Query or realtime update
```

### 7.5 语义

采用：

```text
至少一次传输
+
幂等处理
+
结果未知状态
+
主动查询和对账恢复
```

不追求通过单次网络调用保证严格 Exactly Once。

## 8. 数据权威

| 数据类型 | 权威来源／主责 |
|---|---|
| 用户、Capability、Data Scope | IAM |
| 策略定义、版本、实例和账户绑定 | Strategy |
| 平台交易命令、批次、腿和平台订单 | Trading and Execution |
| 外部订单、成交、余额和持仓事实 | 外部交易系统；平台标准化并持久化 |
| 账户主档、余额、保证金和持仓视图 | Account and Position |
| 风险规则、判断、事件和阻断 | Risk |
| 对账、差异和质量状态 | Reconciliation and Data Quality |
| EconomicEvent、策略账本和 PnL | PnL and Strategy Economic Ledger |
| Runtime、Gateway 和 Worker 实时状态 | Execution Runtime |
| 页面聚合结果 | Query and Read Models，非写入权威 |
| 审计证据 | Audit |

外部系统与平台记录冲突时，不直接选择一方覆盖另一方；通过 ReconciliationDifference、重新同步、人工确认和 AdjustmentEntry 处理。

## 9. 外部组件采用边界

外部组件只能通过 Adapter／Port 接入。

### 9.1 可优先 PoC 的能力

- vn.py EventEngine、MainEngine 和 OmsEngine。
- vn.py CTP Gateway。
- vn.py SpreadTrading 和 AlgoTrading 的低层能力。
- vn.py RiskManager 的底层订单检查能力。
- MetaTrader5 官方 Python 包。
- CCXT 的 Crypto 公共行情、元数据和部分私有接口。
- Binance、OKX、Bybit 官方 API／SDK。
- aiomql 的异步、Session 和重试设计。

### 9.2 只做设计参考

- NautilusTrader：状态机、幂等、恢复、结果未知和降级。
- rotki：EconomicEvent、账本、缺失数据和重算。
- Freqtrade：StrategyInstance 运营、Signal、Trade 和绩效分析。

### 9.3 禁止越界

外部组件不得直接拥有：

- 平台产品架构。
- StrategyDefinition／Version／Instance。
- TradeCommand 和 ExecutionBatch。
- 平台持久化 Order、Fill、Position。
- RiskDecision。
- EconomicEvent、LedgerEntry 和 PnLResult。
- 用户权限、审批和审计。

最终采用必须经过 PoC、许可证、安全、恢复和对账评审，并按需要形成 ADR。

## 10. 状态分层

至少区分：

- 业务状态：Strategy、TradeCommand、ExecutionBatch、Order、Risk 等。
- 运行状态：Runtime、Gateway、Worker、连接和同步。
- 外部状态：Broker／Exchange 原始订单、成交、持仓和账户状态。
- 数据质量状态：Fresh、Stale、Partial、Conflict、Invalid 等。
- 对账状态：Pending、Matched、Difference、Accepted Difference 等。
- 账本状态：估算、已核对、已结算、待重算等。
- 权限状态：Allowed、Read Only、Blocked、Pending Approval 等。

禁止使用一个“在线／异常”或“成功／失败”字段覆盖上述状态。

## 11. 恢复和 READY

Runtime 或 Gateway 连接成功后不能立即允许新增风险。

正式恢复顺序：

```text
STARTING
→ CONNECTING
→ SYNCHRONIZING
→ RECONCILING
→ RECOVERING
→ RISK_CONFIRMING
→ READY
```

至少完成：

- 合约和 Capability 同步。
- 账户、余额、保证金和持仓同步。
- 活动订单和近期成交同步。
- 未完成 ExecutionBatch 恢复。
- 未知订单、外部手工订单和残腿检查。
- 平台与外部差异识别。
- 风险确认。

不能确认一致时进入 Degraded、Read Only 或 Blocked，而不是静默 READY。

## 12. 安全和审计

- Secret、API Key、密码和 MFA 信息不得进入前端、普通日志和业务表。
- Demo、Simulation、Paper 和 Live 分开。
- DeploymentEnvironment、TradingMode 和 TradingPermissionState 分开。
- Live 需要用户能力、账户、Runtime、Gateway、Risk 和 Approval 等多重条件。
- 高风险 Command 具有 requestId、correlationId、idempotencyKey 和对象版本。
- 外部操作结果未知时不得用新幂等身份盲目重复。
- 关键交易、风险覆盖、配置、资金、数据修正和运行操作必须审计。

## 13. 部署与演进原则

初期：

- 业务后端采用模块化单体。
- Execution Runtime 独立进程。
- Worker 可以按账户、市场和故障域隔离。
- 可以部署于同一机器，但不合并为同一进程。
- 不引入大量微服务和 Kubernetes 作为前置要求。

未来只有在以下证据出现时评审拆分：

- 明显独立扩缩容需求。
- 安全或合规隔离要求。
- 故障域必须进一步分离。
- 发布生命周期显著不同。
- 单体成为真实性能或可用性瓶颈。
- 团队具备独立模块维护能力。

## 14. 当前已确认与待确认

### 14.1 已确认

- 六层是逻辑职责，不是六个服务。
- 初期采用三个工程主体。
- Platform Backend 采用模块化单体。
- Execution Runtime 独立于 Platform API 进程。
- Platform Backend 与 Runtime 使用平台自有 Command／Event 契约。
- 外部组件按能力通过 Adapter 接入。
- 平台数据库和领域对象保持业务权威。
- Runtime OMS 和 Read Model 不形成第二套权威。
- Crypto 与 MT5 属于初期接入目标；CTP 可以延后。
- 金融AI分析当前冻结。

### 14.2 待专项确认

- 后端和 Runtime 的最终语言与框架。
- 数据库、缓存、时序库和消息传输。
- Runtime Local Journal 技术。
- MT5 Worker 进程和终端管理方式。
- Crypto 使用 CCXT、官方 SDK 或组合适配。
- Runtime Command／Event Envelope 详细字段。
- ExecutionPlan 的持久化结构。
- 数据保存、归档、RPO 和 RTO。
- 正式部署拓扑和 Live 安全方案。

## 15. 验收标准

- 六个产品模块、四类架构视角、六层逻辑职责和三个工程主体不会被混为一谈。
- Platform Backend 和 Execution Runtime 的拥有对象、依赖和禁止事项明确。
- 浏览器、Read Model、Runtime OMS 和外部组件均不会成为平台业务权威。
- 平台交易链路支持命令受理、预创建订单、幂等、结果未知、恢复和对账。
- MT5、Crypto 和 CTP 可通过统一 Port 接入，但允许能力差异。
- vn.py、CCXT 和其他组件不会反向定义平台领域模型。
- 独立 Runtime 不被误解为必须立即采用微服务或多机部署。
- 未决技术选型保持显式，不由页面或临时代码硬编码决定。
