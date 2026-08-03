# Variable-Global 交易平台总体架构方案

状态：`draft`  
产品基线：Platform V5  
架构讨论版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：交易平台总体架构讨论稿  
更新日期：2026-07-17

> 本文用于讨论 Variable-Global 自有交易平台的目标架构。本文不是实施计划，不代表技术选型、组件采用、数据库、通信中间件、部署拓扑或实盘范围已经确认。
>
> vn.py、aiomql、Freqtrade、rotki、NautilusTrader、PyTrader、交易所 SDK 和其他外部项目仅作为能力来源、设计参考或组件候选。平台产品结构、业务流程、领域模型、数据权威、风险、账本和运行治理由 Variable-Global 自行定义。

## 1. 文档目标

本文重点回答：

1. Variable-Global 自有交易平台应如何分层。
2. 产品、业务控制、领域模型、执行基础设施和数据账本如何协作。
3. MT5、Crypto、CTP 等外部交易系统如何接入。
4. 人工交易、半自动交易和后续自动策略如何使用同一套平台能力。
5. 交易命令、多腿执行、订单、成交、持仓、风险、对账和损益如何保持一致。
6. 外部项目的能力如何被选择性复用、封装、Fork、自建或仅参考。
7. 哪些架构结论仍需讨论、验证和形成 ADR。

本文当前不负责：

- 制定开发优先级、工期和负责人。
- 确认首个实盘策略和实盘账户。
- 决定具体数据库、消息队列和云部署产品。
- 直接开始后端或交易系统开发。
- 开发金融AI分析模块。

## 2. 真实业务背景

平台现有一级产品模块保持为：

1. 首页。
2. 对冲基金看板。
3. 新闻日历与理财。
4. 策略。
5. 风险管理。
6. 金融AI分析。

交易平台当前正式产品范围包括：

- 资费套利。
- 跨所价差。
- 海内外价差。

策略管理纳管范围包括：

- 资费套利。
- 跨所价差。
- 海内外价差。
- 抄底。
- 短线交易员 L。
- 短线交易员 W。

主要外部交易环境包括：

- Crypto：Binance、OKX、Bybit 及后续交易所。
- MT5：不同经纪商、账户和终端实例。
- CTP／国内期货：上期所黄金及后续其他品种。

平台需要支持的执行形态可能包括：

- 人工提交交易命令。
- 带执行辅助的半自动交易。
- 多腿价差执行。
- 算法执行。
- 后续受控自动策略。
- 外部订单、人工订单和历史数据导入。

## 3. 平台自有架构原则

### 3.1 平台优先

Variable-Global 自行定义：

- 产品入口和用户任务。
- 权限和审批。
- 策略、账户和交易关系。
- TradeIntent、TradeCommand 和 ExecutionBatch。
- 风险判断和交易阻断。
- 对账、数据质量和人工干预。
- 策略经济账本和 PnL 归因。
- 审计、监控和运行治理。

任何外部项目都不直接成为平台的产品架构或最终业务模型。

### 3.2 按能力采用，不按项目整体采用

每项能力独立判断：

- 自建。
- 直接复用。
- 通过 Adapter 封装复用。
- Fork 后维护。
- 只参考设计。
- 暂缓。

同一项目的不同模块可以采用不同策略。

### 3.3 外部组件通过平台契约接入

统一结构：

```text
External Component / Broker SDK / Open-source Module
                         ↓
                      Adapter
                         ↓
               Platform Contract / Port
                         ↓
                  Platform Domain
```

页面、应用服务和领域模型不直接依赖外部框架 DTO、状态码和进程对象。

### 3.4 业务状态与运行状态分开

- 平台业务状态描述策略、命令、执行批次、配平和风险。
- 执行运行状态描述进程、Gateway、Worker、连接和实时 OMS。
- 外部状态描述交易所或经纪商的真实订单、成交、余额和持仓。
- 账本状态描述经济事件、计算版本和数据完整度。

不得使用一个通用状态字段表达上述全部含义。

### 3.5 运行与产品界面分离

- 浏览器关闭不影响交易运行。
- Vue 页面不维护正式订单和持仓真相。
- Platform API 重启不应导致外部订单自动消失。
- 交易执行进程必须能够独立恢复、对账和报告状态。

### 3.6 恢复优先于继续运行

连接恢复不等于可以交易。

运行实例必须经过：

```text
连接
→ 同步
→ 对账
→ 恢复未完成执行
→ 检查残腿和未知订单
→ 风险确认
→ READY
```

状态不一致时不得自动进入可新增风险状态。

## 4. 目标总体分层

```text
Variable-Global Platform
├─ 1. 产品与交互层
├─ 2. 平台应用与控制层
├─ 3. 核心业务领域层
├─ 4. 交易执行与连接层
├─ 5. 数据、账本与查询层
└─ 6. 运行保障与基础设施层
```

### 4.1 产品与交互层

由现有 Vue 平台承担：

- 行情分析。
- 交易执行。
- 策略损益。
- 账户资金。
- 订单信息。
- 风险管理。
- 平台运行和数据质量展示。
- 审批、人工处理和审计查看。

前端不负责：

- 持有交易凭证。
- 直接连接交易所或 MT5。
- 判定外部订单最终状态。
- 本地修改正式持仓。
- 以定时器模拟真实成交。
- 以页面状态作为交易真相。

### 4.2 平台应用与控制层

负责组织用户操作和业务用例：

- 身份、权限和数据范围。
- Maker／Checker 审批。
- 策略实例控制。
- TradeCommand 受理。
- 执行前检查。
- 风险判断。
- 幂等和并发控制。
- 人工干预。
- 查询聚合。
- 操作审计。

该层协调领域模块，但不直接实现经纪商连接。

### 4.3 核心业务领域层

建议继续以模块化领域组织：

- Strategy。
- Trading and Execution。
- Account and Position。
- Risk。
- Reconciliation and Data Quality。
- PnL and Strategy Economic Ledger。
- IAM and Approval。
- Audit and Notification。
- Reporting and Read Models。

平台核心对象候选：

```text
StrategyDefinition
StrategyVersion
StrategyInstance
StrategyAccountBinding
TradeIntent
TradeCommand
ExecutionBatch
ExecutionPlan
LegInstruction
Order
Fill
Position
ExposureSnapshot
RiskDecision
ReconciliationResult
EconomicEvent
LedgerEntry
PnLResult
```

### 4.4 交易执行与连接层

负责把平台执行意图转换为外部交易动作：

- Runtime 实例。
- Gateway Adapter。
- 行情订阅。
- 合约和账户同步。
- 订单发送和撤单。
- 实时 OMS。
- 多腿执行工具。
- 算法执行工具。
- 外部状态映射。
- Worker 和终端管理。
- Runtime Event 转换。

这一层可以组合使用 vn.py、自建代码、官方 SDK、aiomql 或其他组件，但对上只暴露平台 Port 和 Event Contract。

### 4.5 数据、账本与查询层

负责：

- 权威交易事实持久化。
- 历史订单和成交。
- 账户和持仓快照。
- EconomicEvent。
- Strategy Economic Ledger。
- PnL 归因和计算版本。
- Reconciliation 和 Data Quality。
- Backend Read Model。
- 报表版本。
- Research Data 和 Content Data，适用时。

Runtime OMS 不是永久账本，页面 Read Model 也不是新的业务权威。

### 4.6 运行保障与基础设施层

负责：

- Runtime Control Plane。
- Runtime Registry。
- Worker Supervisor。
- 配置和密钥。
- 命令和事件通道。
- 日志、指标、追踪和告警。
- 启动恢复。
- 故障隔离。
- 备份和灾难恢复。
- 发布、回滚和版本管理。

## 5. 总体协作链路

### 5.1 命令链路

```text
Vue Frontend
    ↓ REST Command
Platform API
    ↓
Application Use Case
    ↓
TradeCommand
    ↓
ExecutionBatch
    ↓
ExecutionPlan
    ↓
LegInstruction
    ↓ Platform Execution Port
Execution Adapter / Runtime
    ↓
Gateway / Broker SDK
    ↓
External Trading System
```

### 5.2 回报链路

```text
External Order / Fill / Position / Account Update
    ↓
Gateway or SDK Event
    ↓
Runtime Adapter
    ↓
Platform Runtime Event
    ↓
Trading / Account / Reconciliation
    ↓
Database and Read Models
    ↓ WebSocket / Query
Vue Frontend
```

### 5.3 数据关系

- 外部交易场所拥有外部订单、成交、余额和持仓事实。
- 平台拥有标准化对象、策略归属、执行批次关系和持久化业务记录。
- Runtime 维护实时连接、实时 OMS 和运行状态。
- Strategy Economic Ledger 拥有策略经济结果和归因版本。
- Reconciliation 负责发现和处理各层差异。

## 6. 交易编排与 ExecutionPlan

### 6.1 领域链路

建议链路：

```text
TradeIntent
→ TradeCommand
→ ExecutionBatch
→ ExecutionPlan
→ LegInstruction
→ Order
→ Fill
```

### 6.2 ExecutionPlan 定位

ExecutionPlan 描述一次执行批次如何落地，不等于外部订单，也不等于算法进程。

候选字段：

- executionMode。
- activeLegId 和 passiveLegId。
- sequential／parallel。
- orderTypePolicy。
- maxSlippage。
- maxExposureTime。
- maxRepriceCount。
- timeoutPolicy。
- residualPolicy。
- rollbackPolicy。
- allowMarketFallback。
- approvalRequirement。
- planVersion。

### 6.3 平台编排与底层执行工具分工

平台负责：

- 交易业务目标。
- 两腿或多腿目标关系。
- ExecutionBatch 生命周期。
- 配平要求。
- 最大裸露和残腿政策。
- 业务风险和审批。
- 人工干预政策。

底层执行工具负责：

- 具体订单发送。
- 撤单和重报。
- 追价。
- TWAP、Iceberg、Sniper 等算法。
- 实际成交量驱动的对冲订单。
- Runtime 内部实时状态。

底层工具不得自行形成第二套平台 ExecutionBatch 和策略损益事实。

## 7. 执行基础设施契约

建议按能力拆分 Port，而不是假设所有 Gateway 能力相同。

### 7.1 TradingGatewayPort

- submitOrder。
- cancelOrder。
- replaceOrder，支持时。
- queryOrder。
- queryOpenOrders。
- queryFills。

### 7.2 MarketDataGatewayPort

- subscribeQuote。
- subscribeDepth。
- queryContract。
- queryTradingSession。
- queryMarketStatus。

### 7.3 AccountGatewayPort

- queryAccount。
- queryBalance。
- queryMargin。
- queryPositions。

### 7.4 FundingGatewayPort

- queryFundingRate。
- queryFundingHistory。
- queryFundingSettlement。

### 7.5 TransferGatewayPort

- queryTransferCapability。
- transferFunds。
- queryTransferStatus。

### 7.6 BorrowGatewayPort

- queryBorrowRate。
- borrow。
- repay。
- queryBorrowStatus。

### 7.7 TerminalManagementPort

- queryTerminalHealth。
- queryBrokerConnection。
- queryAutoTradingStatus。
- startWorker。
- stopWorker。
- restartWorker。

GatewayCapability 用于声明每个 Runtime／Gateway 实现了哪些 Port 和订单能力。

## 8. 外部交易系统接入

### 8.1 MT5

MT5 候选结构：

```text
MT5 Runtime Supervisor
├─ MT5 Worker A
│  └─ Terminal A / Account A
├─ MT5 Worker B
│  └─ Terminal B / Account B
└─ MT5 Worker C
   └─ Terminal C / Account C
```

候选原则：

- 一个账户对应一个终端实例和独立 Worker。
- Worker 使用稳定 GatewayRuntimeId。
- 账户、终端、Worker 和 StrategyAccountBinding 分开管理。
- 单 Worker 故障不影响其他账户。
- 终端重启后必须同步、对账和恢复。
- 手工订单、Magic Number、Hedging／Netting 和部分平仓必须可识别。

可研究：

- 官方 MetaTrader5 Python 包。
- aiomql 的异步封装、重试、Session 和查询设计。
- PyTrader 的远程节点和 EA 桥接设计，作为备用路径。

### 8.2 Crypto

Crypto 接入除了标准交易外，还可能包含：

- Spot。
- USDT 本位和币本位永续。
- Funding Rate 和结算。
- Mark／Index Price。
- Hedge／Netting Mode。
- Reduce Only 和 Post Only。
- 统一账户和资金账户。
- 资金划转。
- 借币和还币。

每家交易所可以使用不同实现，但必须映射到平台统一 Port、对象和事件。

### 8.3 CTP／国内期货

需要处理：

- 合约和交易日。
- 夜盘。
- 平今和平昨。
- 涨跌停。
- 保证金和手续费。
- 结算数据。
- 合约换月。
- 节假日和交易日历。

vn.py CTP Gateway 可以作为优先复用候选，但平台仍通过 Adapter 进行对象、状态和错误映射。

## 9. Runtime 与进程架构

### 9.1 逻辑统一、物理可隔离

平台拥有统一 Runtime Contract，但不要求所有 Gateway 和账户运行在同一进程。

候选结构：

```text
Execution Runtime System
├─ Runtime-Crypto
├─ Runtime-CTP
├─ Runtime-MT5-A
├─ Runtime-MT5-B
└─ Runtime-Sandbox
```

初期可以简化部署，但架构应支持：

- 单 Gateway 或单账户重启。
- Runtime 版本独立升级。
- 故障域隔离。
- Demo／Paper／Live 隔离。
- 不同凭证和网络隔离。

### 9.2 Runtime Control Plane

负责：

- RuntimeDefinition。
- RuntimeInstance。
- GatewayDefinition。
- GatewayRuntime。
- Worker 注册和心跳。
- 配置版本。
- 启停和重启请求。
- 健康状态。
- 恢复进度。
- 版本、日志和资源信息。

Control Plane 不直接修改外部订单事实。

### 9.3 Runtime Supervisor

负责：

- 启动和停止子进程。
- 心跳检测。
- 异常重启策略。
- 资源限制。
- 日志位置。
- 配置注入。
- 进程版本。
- 故障隔离。

## 10. Platform 与 Runtime 通信

### 10.1 同步交互

适合：

- 健康检查。
- 能力查询。
- 配置读取。
- 当前快照查询。
- 管理性诊断。

### 10.2 可靠命令

交易相关动作应具有：

- commandId。
- requestId。
- correlationId。
- idempotencyKey。
- operatorId／strategyInstanceId。
- payloadVersion。
- createdAt。
- expiry／timeoutPolicy，适用时。

一次网络超时不能直接解释为命令失败。

### 10.3 Runtime Event

事件至少包含：

- eventId。
- eventType。
- sourceRuntimeId。
- sourceGatewayId。
- externalReference。
- occurredAt。
- receivedAt。
- sequence／version，适用时。
- correlationId。
- payloadVersion。

消费者必须能够处理重复、延迟、乱序和恢复后的补发事件。

### 10.4 技术方案待定

通信实现可进一步评估：

- RPC。
- Redis Streams。
- RabbitMQ。
- NATS JetStream。
- Kafka。
- 数据库 Outbox／Inbox。
- 其他可靠消息方案。

架构先确定命令和事件语义，不在本文直接确定中间件。

## 11. 状态和权威模型

### 11.1 外部系统权威

- 外部订单和成交。
- 外部余额和持仓。
- 外部费用、Funding 和隔夜费。
- 经纪商或交易所账户状态。

### 11.2 Runtime 权威

- 当前连接状态。
- 当前进程内 OMS。
- Gateway 和 Worker 健康。
- 当前订阅和运行会话。
- 尚未持久化完成的运行时上下文。

### 11.3 平台领域权威

- StrategyInstance 和账户用途绑定。
- TradeCommand 受理记录。
- ExecutionBatch 和 LegInstruction 关系。
- Order、Fill 的平台标准化记录。
- ExecutionBalanceStatus 和 ExposureStatus。
- RiskDecision、ManualIntervention 和 ReconciliationResult。

### 11.4 策略经济账本权威

- EconomicEvent。
- LedgerEntry。
- 费用、资金费、隔夜费和汇率影响。
- PnLResult 和 PnLAttribution。
- 计算版本和完整度。

### 11.5 一致性原则

各层权威通过：

- 事件摄取。
- 定时同步。
- 启动对账。
- 手工确认。
- AdjustmentEntry。
- 审计记录。

保持一致，不能通过覆盖原始事实伪造一致。

## 12. 两级及策略专项风控

### 12.1 平台业务风控

回答：

> 这次策略业务操作是否允许发生？

包括：

- 用户和数据范围。
- 策略实例状态。
- 账户和资金状态。
- 交易模式。
- 数据质量。
- 最大仓位和杠杆。
- 最大残腿和裸露时间。
- 策略专项限制。
- ApprovalGrant。
- GlobalTradingBlock。

### 12.2 底层订单检查

回答：

> 这张具体订单能否提交到外部系统？

包括：

- 合约合法性。
- 价格和数量步进。
- 最小和最大数量。
- 订单类型能力。
- 活动订单上限。
- 报撤单限制。
- Gateway 状态。
- 账户可用资金和经纪商规则。

底层拒绝必须回写平台执行和风险记录。

### 12.3 策略专项风控

由对应策略文档定义，例如：

- 资费套利：资金费率反转、双腿配平、借贷和强平距离。
- 跨所价差：双端延迟、USDT／USD、Crypto-MT5 残腿和双账户保证金。
- 海内外价差：汇率、MT5-CTP 残腿、涨跌停、平今平昨和交易时段错位。

## 13. 对账与恢复

### 13.1 对账范围

- 平台订单与外部订单。
- 平台成交与外部成交。
- 平台持仓与外部持仓。
- ExecutionBatch 腿关系与真实腿仓。
- 平台账户快照与外部账户。
- Funding、费用、隔夜费和资金划转。
- 策略经济账本与外部结算事实。

### 13.2 启动恢复流程

```text
Runtime 启动
→ 注册 Gateway
→ 连接外部系统
→ 同步合约和能力
→ 同步账户和持仓
→ 同步活动订单和近期成交
→ 与平台数据库对账
→ 恢复未完成 ExecutionBatch
→ 检查未知订单和残腿
→ 恢复行情订阅
→ 风险确认
→ READY
```

### 13.3 恢复状态

建议后续评审是否增加独立：

- RuntimeStatus。
- RecoveryStatus。
- GatewayStatus。

这些状态与 OrderStatus、ExecutionBatchStatus、RiskStatus 分开。

### 13.4 恢复结果

每次恢复形成 RecoveryRun，至少记录：

- 运行实例。
- 起止时间。
- 同步步骤。
- 外部快照版本或时间。
- 发现差异。
- 未完成执行。
- 人工决定。
- 最终是否允许交易。

## 14. 数据、账本和损益

处理链路候选：

```text
Order / Fill / Funding / Fee / Overnight / Borrow / Transfer / FX
                              ↓
                         EconomicEvent
                              ↓
                          LedgerEntry
                              ↓
                         PnL Calculation
                              ↓
                   PnLResult / Attribution / Report
```

原则：

- Runtime 和 Gateway 只提供输入事实，不计算最终策略归因。
- 策略损益口径以对应策略文档为准。
- 新计算版本不覆盖旧版本。
- 缺失行情、汇率、Funding 或费用不能静默当作零。
- 人工修正产生 AdjustmentEntry，不覆盖外部原始事实。
- 策略经济账本不等于公司财务会计总账。

## 15. 开源和外部项目能力参考

### 15.1 vn.py

可研究或候选复用：

- EventEngine。
- MainEngine。
- Gateway 抽象。
- OmsEngine。
- CTP Gateway。
- RiskManager。
- SpreadTrading。
- AlgoTrading。
- RPC Service。
- 数据录制工具。

不能直接决定：

- 平台产品结构。
- 平台领域模型。
- TradeCommand／ExecutionBatch。
- 策略经济账本和 PnL 归因。
- 用户权限和审批。
- 平台最终数据权威。

### 15.2 aiomql

可研究：

- MT5 初始化和登录。
- 异步调用封装。
- 连接重试。
- Session 管理。
- Account、Symbol、Order、Position 和 History 查询。
- Margin 和 Profit 计算接口。

不默认采用其 Bot、Strategy、Trader、RAM 和 SQLite 账本。

### 15.3 Freqtrade

主要参考：

- 策略实例生命周期。
- 启动、暂停、恢复和有序停止。
- 禁止新开仓。
- 配置版本。
- 运行日志。
- Web 控制面设计。

### 15.4 rotki

主要参考：

- EconomicEvent 思路。
- 原始事实与派生结果分离。
- 缺失数据表达。
- 账本重算。
- 报告版本。
- 数据来源和完整度。

### 15.5 NautilusTrader

主要参考：

- Command／Event 分离。
- 状态机。
- 幂等。
- 对账和恢复。
- 结果未知。
- 降级和故障隔离。

### 15.6 PyTrader

主要参考：

- 远程 MT4／MT5 节点。
- EA 桥接。
- 跨机器连接。

当前作为备用能力研究，不进入主路径结论。

### 15.7 官方 SDK 和交易接口

对 Crypto、MT5 和其他接入，官方 SDK、协议和经纪商接口始终是重要候选来源，不因研究开源框架而被排除。

## 16. 金融AI分析边界

金融AI分析继续完善信息和接口设计，但当前不进入交易系统开发范围。

未来只通过受控 Query 和 Backend Read Model 读取：

- Research Data。
- Content and Calendar Data。
- 策略、订单、成交和执行摘要。
- PnL 和风险摘要。
- 对账和数据质量。
- Runtime 健康摘要。

金融AI分析不得：

- 直接连接 Runtime、EventEngine 或 Gateway。
- 访问交易凭证。
- 提交 TradeCommand。
- 修改风险规则和交易阻断。
- 修改账户、订单、持仓、账本和损益事实。
- 进入当前交易架构 PoC 和开发计划。

## 17. 与现有 active 架构的关系

本文不预设现有 active 架构不可修改。

讨论结果可能导致后续调整：

- 后端总体分层。
- Trading and Execution 服务边界。
- 公共领域模型。
- Runtime、Gateway 和 Recovery 状态。
- 前后端命令和事件契约。
- 数据权威和对账规则。
- 安全、部署和运维架构。

任何确定调整应：

1. 先在本 DRAFT 或专项方案中完成讨论。
2. 形成明确决策和影响分析。
3. 适用时创建 ADR。
4. 再同步修改 active 架构文档。
5. 最后进入规划和实施。

## 18. 待讨论问题

### 18.1 平台分层

- 是否接受六层总体分层。
- Application、Domain、Execution Infrastructure 的代码边界如何划分。
- Runtime Control Plane 属于业务后端模块还是独立服务。

### 18.2 执行模型

- ExecutionPlan 是否成为正式领域对象。
- 平台多腿编排与底层 Spread／Algo 的具体边界。
- 人工、半自动和自动执行是否共用相同 ExecutionBatch。

### 18.3 Runtime 和 Gateway

- vn.py 各模块分别采用何种方式。
- MT5 是否一个账户一个 Worker。
- Crypto Gateway 使用社区实现、官方 SDK 还是自研。
- CTP Gateway 的封装边界。

### 18.4 通信

- 同步查询和可靠命令分别使用何种通道。
- Outbox／Inbox 是否作为基础机制。
- Runtime Event 的顺序、重放和保留策略。

### 18.5 存储

- 交易事实、事件、账本、时序行情和 Read Model 的存储划分。
- 是否需要独立时序数据库。
- Runtime 本地持久化和平台数据库的关系。

### 18.6 恢复和对账

- 恢复进入 READY 的检查条件。
- 未知外部订单的自动和人工处理规则。
- 差异是否阻断全部交易或只阻断相关范围。

### 18.7 安全和部署

- Demo、Paper、Live 的进程和凭证隔离。
- Runtime 和 Worker 的部署位置。
- MT5 远程节点何时需要。
- Kill Switch 的实际执行通道和失败处理。

## 19. 本 DRAFT 的验收标准

在进入正式架构确认前，本文至少应做到：

- 平台主体和外部组件角色明确。
- 产品、应用、领域、执行、数据和运行保障边界明确。
- 交易命令和回报链路可解释。
- 多腿执行不存在两套业务编排真相。
- Runtime OMS、平台记录和策略经济账本明确区分。
- MT5、Crypto 和 CTP 接入具有统一契约，同时允许专项能力。
- 对账和恢复是核心架构能力。
- 外部项目按能力评审，不整体绑定。
- 金融AI分析完成信息边界预留但明确暂不开发。
- 所有未确认技术结论明确标记为待讨论或候选。