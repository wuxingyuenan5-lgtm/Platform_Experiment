# Platform 0.10.x+ 交易执行与可靠性架构

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：后端交易与可靠性架构

上位约束：

- `../platform-target-architecture.md`
- `backend-overview.md`
- `execution-runtime-and-gateway.md`
- `../integration/api-contract-and-versioning.md`
- `../integration/realtime-events-and-recovery.md`
- `../domain/status-enums-and-lifecycles.md`
- `../decisions/ADR-008-总体逻辑分层与独立交易Runtime.md`

## 1. 文档定位

本文定义 V1 交易接入必须具备的交易命令、执行批次、ExecutionPlan、交易腿、平台订单身份、成交、配平、暴露、Runtime 协作、幂等、结果未知、异常恢复、对账和人工处理边界。

V1 不以 Fake Gateway 作为最终验收。Fake Gateway 只用于本地工程验证；资费套利必须覆盖首个 Crypto 交易所真实 API 的模拟盘、测试网或受控账户链路，跨所价差必须覆盖首个 Crypto 交易所真实 API 模拟/测试链路和首个 MT5 Demo/Worker 链路。Live 实盘开关必须在这些链路的恢复、对账、风控和人工接管通过后单独开启。

本文不指定具体数据库、消息中间件、交易内核和 Gateway SDK。状态码和生命周期以公共状态文档为唯一来源。

## 2. 核心原则

- 用户业务目标不等于外部订单。
- Command 已受理不等于订单已提交。
- 外部订单已提交不等于已确认。
- 订单已确认不等于已成交。
- 单腿成交不等于策略组合完成。
- Platform API、浏览器和实时连接断开不影响已受理后台执行。
- platformOrderId 必须先于外部提交存在。
- 网络超时和 Event 延迟不能直接解释为外部失败。
- 结果未知必须显式记录并恢复，不能盲目重试。
- Runtime 独立运行，但不拥有平台业务批次和 PnL 权威。
- 所有高风险操作可审计、可恢复、可人工接管。
- DeploymentEnvironment、TradingMode 和 TradingPermissionState 分开。

## 3. 标准执行链路

```text
TradeIntent
→ TradeCommand
→ permission / validation / risk / approval
→ ExecutionBatch
→ ExecutionPlan
→ LegInstruction
→ pre-created platform Order
→ Runtime Command
→ External Order
→ Runtime Event
→ platform Order / Fill / Deal
→ Position / Exposure / EconomicEvent / PnL
```

### 3.1 TradeIntent

表示用户或策略希望完成的业务目标，例如：

- 建立资费套利组合。
- 建立 Crypto－MT5 黄金跨所价差。
- 平仓、减仓或重新配平。
- 发起紧急补对冲。

TradeIntent 可以来自页面、人工操作或后续受控策略，但不等于已受理命令。

### 3.2 TradeCommand

表示平台对一次改变交易状态请求的正式受理记录。

负责：

- 请求身份和幂等判断。
- 权限、范围、环境、模式和对象版本校验。
- Strategy、Account、Market Data、Risk 和 Approval 协调。
- 接受或拒绝请求。
- 创建或关联 ExecutionBatch。

TradeCommand 不重复维护 ExecutionBatch 的执行进度。

### 3.3 ExecutionBatch

表示为完成同一交易目标而组织的一组腿、订单、成交和异常处理，是双腿和多腿执行的业务聚合。

### 3.4 ExecutionPlan

描述 ExecutionBatch 如何执行，包括：

- 并行、顺序或主动腿／被动腿。
- 订单类型和价格政策。
- 最大滑点和价格保护。
- 最大裸露时间。
- 部分成交和残腿政策。
- 超时、追价、撤单和市场价回退政策。
- 重试次数和人工确认要求。
- 计划版本和修订记录。

ExecutionPlan 不等于外部订单、Runtime Worker 或 vn.py Algo 实例。

### 3.5 LegInstruction

表示某一交易腿的目标：

- AccountId。
- InstrumentId。
- 腿角色。
- 方向。
- 目标数量或名义价值。
- 订单和价格政策。
- 目标 Gateway／Runtime。

LegInstruction 不等于 Order。

## 4. TradeCommand 要求

正式命令至少包含：

- `tradeCommandId`。
- `requestId`。
- `correlationId`。
- `idempotencyKey`。
- StrategyInstanceId。
- StrategyVersionId。
- 操作类型。
- 操作人和 OperatorContext 引用。
- 目标账户和标的。
- Command payload 和 payloadVersion。
- 客户端提交时间和服务端受理时间。
- DeploymentEnvironment。
- TradingMode。
- 对象版本和预期状态。
- ApprovalGrantId，适用时。

TradeCommand 状态只表达受理流程；后续执行读取 ExecutionBatch、Order 和 Runtime 状态。

## 5. 幂等和并发控制

以下操作必须支持幂等：

- 提交交易。
- 撤单、改单和取消执行批次。
- 平仓、减仓和重新配平。
- 紧急补对冲。
- 确认结果未知和外部订单归属。
- 使用 ApprovalGrant 执行高风险动作。
- 对账修正和人工处理。

同一幂等键和业务作用域重复提交时：

- 不创建重复 Command、ExecutionBatch 或外部订单。
- 返回原受理结果或当前权威状态。
- 记录重复请求。
- 相同幂等键但不同 payload 返回冲突。

并发控制至少覆盖：

- StrategyInstance 当前版本。
- Account 和 TradingPermissionState。
- ExecutionBatch 当前状态。
- Order 当前版本。
- ApprovalGrant 是否已使用或失效。

前端可以生成请求级幂等键，但作用域、有效期、payload 哈希和冲突判断由后端维护。

## 6. 执行前校验

至少包括：

- 用户身份、Capability 和 Data Scope。
- DeploymentEnvironment、TradingMode 和 TradingPermissionState。
- StrategyDefinition、StrategyVersion 和 StrategyInstance。
- StrategyAccountBinding。
- Account 状态、权限和用途。
- Instrument、Symbol Mapping 和 ContractSpecification。
- Quote、Funding、FX 和 MarketStatus 的来源、新鲜度和质量。
- 价格、数量、精度、最小数量和最小名义价值。
- Balance、Margin 和 Position。
- 双腿方向、目标比例、统一单位和名义价值。
- RiskRule、RiskLimit、RiskDecision 和 GlobalTradingBlock。
- GatewayCapability、RuntimeStatus 和 GatewayStatus。
- 冲突中的 ExecutionBatch、Order 和 Position。
- ApprovalGrant 的目标、参数、有效期和使用状态。

校验形成结构化 ValidationResult、RiskDecision 和 TradingPermissionState，不只返回自然语言。

## 7. ExecutionBatch 要求

至少记录：

- `executionBatchId`。
- TradeCommandId。
- StrategyInstanceId 和 StrategyVersionId。
- 业务操作：open、close、adjust、rebalance、emergency hedge 等。
- 目标组合和 LegInstruction 列表。
- 目标基础数量、名义价值和配平关系。
- ExecutionPlan 和 planVersion。
- ExecutionBatchStatus。
- ExecutionBalanceStatus。
- ExposureStatus。
- 已成交数量和剩余数量。
- 当前单腿暴露、金额和持续时间。
- Runtime、Gateway 和 Worker 引用。
- 异常和 ManualIntervention 状态。
- 创建、更新、完成和最后对账时间。

ExecutionBatchStatus、ExecutionBalanceStatus、ExposureStatus 和 ReconciliationStatus 分别保存。

## 8. ExecutionPlan 版本

ExecutionPlan 可以初期作为 ExecutionBatch 内版本化值对象，但必须：

- 保存 planVersion。
- 保存创建时间和创建原因。
- 保存执行模式和所有风险相关参数。
- 执行中修改产生新版本或修订记录。
- 历史 Order 能关联实际生效计划版本。
- 不允许页面无痕修改已执行计划。

后续只有出现独立审批、复用或复杂生命周期需求时，再评审独立聚合和独立表。

## 9. 平台 Order 预创建

外部提交前必须创建平台 Order：

```text
LegInstruction
→ create platformOrderId
→ Order.status = submission_requested
→ write Runtime Command Outbox
→ Runtime consume
→ external submit
→ externalOrderId
→ Order acknowledged / rejected / unknown
```

Order 预创建至少保存：

- platformOrderId。
- ExecutionBatchId 和 LegInstructionId。
- AccountId 和 InstrumentId。
- 方向、订单类型、价格和数量。
- clientOrderId／Magic／Comment／Tag 计划映射。
- Runtime、Gateway 和 Worker 目标。
- CommandId 和 idempotencyKey。
- 当前状态和版本。

该机制用于：

- Runtime 在外部提交后崩溃时找回订单。
- 通过 clientOrderId、Magic、Comment 或历史查询恢复。
- 避免 Event 延迟时平台完全没有订单记录。
- 支持结果未知和对账。

## 10. Runtime Command 和 Event

Platform Backend：

- 在平台事务中保存 TradeCommand、ExecutionBatch、LegInstruction、Order 和 Command Outbox。
- 不在业务事务中直接调用外部 SDK。

Execution Runtime：

- 至少一次消费 Runtime Command。
- 使用 commandId 和 idempotencyKey 去重。
- 在 Runtime Journal 保存处理状态。
- 执行外部操作。
- 可靠保存并发送 Runtime Event。

Platform Event Inbox：

- 使用 eventId 幂等。
- 映射至 Trading、Account、Market Data、Reconciliation 和 PnL。
- 保留外部原始状态和证据。

具体 Envelope 见 `execution-runtime-and-gateway.md`。

## 11. Order 与 Fill

平台 Order 状态与外部状态码分开。

规则：

- 一张 Order 可以产生多笔 Fill。
- Fill 是不可变交易事实，不因订单状态变化被覆盖。
- Fill 至少保留价格、数量、费用、成交时间和外部成交 ID。
- Order Cancel 不删除已发生 Fill。
- Runtime Adapter 映射外部状态并保留原始状态码。
- Position 变化依据 Fill 或经 Reconciliation 确认的外部持仓事实生成。
- externalOrderId、externalFillId／DealId 按 Venue、Account 和 Gateway 范围唯一。
- 重复和乱序回报由 Event Inbox 和对象版本处理。

MT5 场景下，Deal 是成交事实的核心来源。Order 只表达委托生命周期，不能单独生成最终 Fill、Position、EconomicEvent 或 PnL；必须通过 Deal 历史、Position 和账户记录确认。

## 12. 配平与暴露

ExecutionBatch 独立计算：

- 目标配平比例。
- 实际成交比例。
- 目标和实际基础数量。
- 名义价值偏差。
- Delta 或方向暴露。
- 汇率暴露，适用时。
- 暴露持续时间。
- 残腿数量和补对冲需求。

ExecutionBalanceStatus 不表示 Account Balance。

ExecutionBatch 可以已经完成订单提交，但仍然：

- 未配平。
- 存在暴露。
- 等待撤单。
- 等待对账。
- 结果未知。

## 13. 策略专项执行

### 13.1 资费套利

关注：

- Spot 和 Perpetual 双腿。
- Funding Rate 和实际 FundingSettlement 分开。
- V1 必须选定首个 Crypto Venue，跑通真实 API 模拟盘、测试网或受控账户的市场、账户、下单、撤单、成交、余额、持仓和恢复链路。
- 资金费收入只按实际 FundingSettlement、账户账本或交易所结算记录入账，不用预估 Funding Rate 当作已实现收益。
- 两腿名义价值。
- 单腿暴露和 Funding 反转。
- 不设置配平误差一级 PnL。

### 13.2 跨所价差

关注：

- Crypto 与 MT5 跨 Runtime／Worker。
- V1 必须跑通首个 Crypto Venue 真实 API 模拟/测试链路和首个 MT5 Demo/Worker 链路。
- XAUTUSDT.P 和 XAUUSD 单位、币种和合约规格。
- USDT／USD。
- 主动腿、被动腿和最大裸露时间。
- MT5 侧以 Deal、Position 和账户历史作为成交、持仓和费用事实来源。
- Platform API、Crypto Runtime 和 MT5 Worker 任一重启后，都必须能恢复未完成 ExecutionBatch、单腿暴露和结果未知状态。
- 不设置配平误差一级 PnL。

### 13.3 海内外价差

关注：

- 国内和海外腿。
- 汇率、合约乘数、交易日和时段。
- MT5、后续 CTP 和外部记录模式。
- 理论配平、实际持仓和正式配平误差 PnL。
- 平今／平昨和换月，接入 CTP 后。

海内外价差不是 V1 完整闭环验收对象。V1 只保留分析、模拟、字段和管理入口，不接入 CTP，不做正式人民币汇率 PnL、平今/平昨、换月和结算级对账。

策略专项口径以 `docs/strategies/` 为唯一来源。

## 14. 异常类型

至少包括：

- Quote 过期、数据质量不足或时钟偏差。
- Account 不可用、Balance／Margin 不足。
- Runtime、Worker 或 Gateway 不 READY。
- Gateway 连接、认证或限频异常。
- Command 过期或不兼容。
- 外部提交超时。
- Order 拒绝。
- 单腿成交、部分成交和残腿。
- 撤单、改单或平仓结果未知。
- Event 重复、延迟、乱序或序列缺口。
- 外部手工订单或未归属订单。
- Position、Balance 和平台记录不一致。
- Risk、Approval、Account 或 Capability 在执行中变化。
- 合约、单位、汇率和 Symbol Mapping 错误。
- Runtime Journal 或 Platform Inbox 异常。

异常必须关联：

- ExecutionBatch。
- LegInstruction。
- Order 或 Fill。
- Runtime／Gateway／Worker。
- 当前配平和暴露。
- 处理动作、操作人、时间和原因码。

## 15. 结果未知

网络超时、Worker 崩溃或 Event 丢失风险出现时，不得直接标记失败并重新下单。

处理顺序：

1. 标记 TradeCommand、ExecutionBatch、Order 或外部操作为 unknown／result_unknown。
2. 暂停自动重复提交。
3. 使用 commandId、idempotencyKey、clientOrderId、Magic、Comment、externalOrderId 查询。
4. 同步活动订单、历史订单、Fill、Position 和 Account。
5. 使用平台 Order 预创建记录和 Runtime Journal 证据恢复。
6. 创建 ReconciliationDifference，适用时。
7. 无法自动确认时进入 ManualIntervention。

结果未知是待恢复状态，不是普通失败终态。

## 16. 重试原则

可以自动重试：

- 只读 Query。
- 明确未到达外部系统的幂等 Command。
- Event 发布和 Inbox 消费。
- 具有稳定幂等身份且结果可确认的操作。

不得盲目自动重试：

- 结果未知的下单、划转和平仓。
- 外部系统无幂等能力且可能已执行的请求。
- 可能扩大单腿暴露的动作。
- Risk、Approval、Account、Capability 或 TradingPermissionState 已变化的命令。
- 使用新 clientOrderId 规避原结果未知的操作。

## 17. Runtime 重启与恢复

Runtime 启动：

```text
STARTING
→ CONNECTING
→ SYNCHRONIZING
→ RECONCILING
→ RECOVERING
→ RISK_CONFIRMING
→ READY
```

必须：

- 加载 Runtime Journal。
- 注册 Runtime、Gateway 和 Worker。
- 同步 Instrument 和 Capability。
- 同步 Account、Balance、Margin 和 Position。
- 查询活动 Order 和近期 Fill。
- 恢复未完成 ExecutionBatch。
- 识别 unknown、外部手工订单和残腿。
- 向 Platform Reconciliation 提供外部事实。
- 完成 Risk 确认。

不能确认一致时进入 Degraded、Read Only 或 Blocked，不静默 READY。

Platform API 重启后：

- 通过平台数据库恢复 Command、ExecutionBatch、Order 和 Inbox。
- 重新查询 Runtime、Account、Risk 和 Reconciliation 状态。
- 不要求 Runtime 和外部 Session 同步重启。

## 18. 对账

至少核对：

- 平台 Order 与外部 Order。
- 平台 Fill 与外部 Fill／Deal。
- Platform Position 与外部 Position。
- Platform Balance／Margin 与外部账户。
- Funding、Swap、Commission、Fee 和账户账本。
- EconomicEvent 和 PnLResult 的底层完整度。

发现差异时：

- 不直接覆盖原始记录。
- 创建 ReconciliationRun 和 Difference。
- 标记影响 StrategyInstance、Account、ExecutionBatch 和 PnL。
- 必要时禁止新增风险。
- 进入重新同步、自动修复、人工复核或 accepted_difference。
- 正式修正通过 DataCorrectionRecord、AdjustmentEntry 和版本化重算。

## 19. 外部手工订单和归属

外部系统出现平台外订单时：

- Runtime 如实摄取。
- 依据 Account、clientOrderId、Magic、Comment、Tag、Subaccount 和时间范围尝试归属。
- 无法确认时标记 unallocated／unverified。
- 不因无法归属而丢弃 Fill 和 Position。
- 创建 ReconciliationDifference 或人工归属任务。
- 人工归属具有权限、证据和 AuditEvent。

ExternalExecutionProfile 由 Strategy 拥有；Runtime 只执行映射和报告。

## 20. 人工处理与审批

ManualIntervention 可以包括：

- 确认外部订单真实状态。
- 关联 externalOrderId 或 Fill。
- 选择撤单、补单、减仓或紧急对冲。
- 暂停或终止 ExecutionBatch。
- 接受已知差异。
- 处理未归属订单和持仓。
- 请求重新同步或对账。
- 添加证据和处理备注。

高风险动作按 Approval Policy 执行 Maker／Checker。

所有人工动作：

- 服务端权限校验。
- 绑定当前对象版本。
- 使用幂等键。
- 保留原因、证据和 AuditEvent。

## 21. GlobalTradingBlock 和 Kill Switch

支持范围：

- 全平台。
- DeploymentEnvironment。
- TradingMode。
- Runtime、Gateway 或 Worker。
- Account。
- StrategyInstance。
- Instrument 或市场。

默认语义：禁止新增风险。

可以单独允许：

- 撤销活动订单。
- 减仓和平仓。
- 紧急补对冲。
- 重新同步和对账。

Kill Switch 触发不等于所有外部动作成功，撤单和平仓结果仍需查询和对账。

## 22. 可观测性

至少监控：

- Command 受理、拒绝、重复和过期。
- ExecutionBatch 创建、完成、异常和积压。
- Runtime Command Outbox 和 Event Inbox 积压。
- Runtime Journal 和待发送 Event。
- Gateway 提交成功率、确认延迟和错误码。
- Order 结果未知数量和持续时间。
- 单腿暴露数量、金额和持续时间。
- ReconciliationDifference。
- Runtime、Gateway 和 Worker 状态。
- 外部手工订单和未归属对象。
- ManualIntervention 和 Approval 积压。

日志贯穿：

- requestId。
- correlationId。
- commandId。
- tradeCommandId。
- executionBatchId。
- legInstructionId。
- platformOrderId。
- externalOrderId。
- runtimeInstanceId。
- gatewayRuntimeId。
- workerInstanceId。

## 23. 测试场景

至少覆盖：

- 正常单腿和双腿执行。
- 重复 TradeCommand 和 Runtime Command。
- 相同幂等键不同 payload。
- 部分成交和多笔 Fill。
- 单腿成交和补对冲。
- 外部拒单。
- 下单超时但外部订单成功。
- Runtime 外部提交后崩溃。
- Event 通道失败和补发。
- Platform Event Inbox 暂时不可用。
- Runtime Journal 不可用或损坏。
- Platform API 重启。
- Runtime、Worker 和 Gateway 重启。
- Fill 与 Order Event 乱序。
- 外部手工订单。
- Account、Position 和 Balance 对账差异。
- Risk 或 Approval 在执行中变化。
- GlobalTradingBlock 和 Kill Switch。
- Crypto 测试网或受控账户 WebSocket 中断后通过 REST 回补订单、成交、余额和持仓。
- Crypto FundingSettlement 或账户账本进入 EconomicEvent 和 PnL。
- MT5 Demo 下单、撤单、Order、Deal、Position、Commission、Swap 和账户历史查询。
- MT5 Terminal 或 Worker 重启后通过 Deal 历史和 Position 恢复。
- Platform API、Crypto Runtime 和 MT5 Worker 同时或分别重启后不重复下单。

V1 验收必须同时覆盖 Fake Gateway、首个 Crypto 真实 API 模拟/测试链路和首个 MT5 Demo/Worker 链路。Fake-only 不构成 V1 交易能力完成。

## 24. 分阶段启用原则

交易能力按安全等级逐步启用：

1. Fake Gateway。
2. 后端 Simulation。
3. 首个 Crypto Venue 模拟盘／测试网／受控账户。
4. 首个 MT5 Demo／Worker。
5. 只读真实账户同步。
6. 小资金、单账户、单策略受控 Live。
7. 扩展策略、账户和 Gateway。

V1 排期必须先确定首个 Crypto Venue、首个 MT5 Demo Broker/Account 和对应适配方案；不在早期并行铺开多个交易所和多个券商。

## 25. 唯一来源

- 总体目标：`../platform-target-architecture.md`。
- Runtime 与 Gateway：`execution-runtime-and-gateway.md`。
- 状态枚举：`../domain/status-enums-and-lifecycles.md`。
- 领域对象：`../domain-model-boundaries.md`。
- API 与幂等：`../integration/api-contract-and-versioning.md`。
- 前端实时恢复：`../integration/realtime-events-and-recovery.md`。
- 审批：`../domain/approval-and-dual-control.md`。
- 策略专项：`../../strategies/`。

## 26. 验收标准

- TradeCommand 只表达命令受理，不重复表达 ExecutionBatch 进度。
- ExecutionPlan 和 LegInstruction 分开。
- platformOrderId 在外部提交前创建。
- Platform Backend 不在业务事务中调用外部 SDK。
- Runtime Command 和 Event 支持至少一次、幂等和补发。
- Order 和 Fill 分开保存。
- MT5 场景下 Order、Deal 和 Position 分开保存，Deal 作为成交事实。
- ExecutionBatchStatus、ExecutionBalanceStatus、ExposureStatus 和 ReconciliationStatus 分开。
- 结果未知不会被误判为失败并重复下单。
- Platform API、Runtime 和 Worker 重启后可以恢复。
- 外部手工订单和未归属事实不会被丢弃。
- 对账差异、人工处理和高风险审批可审计。
- 前端断线不会中止后台执行。
- 资费套利完成首个 Crypto 真实 API 模拟/测试链路闭环，资金费按实际结算或账户账本入账。
- 跨所价差完成首个 Crypto 真实 API 模拟/测试链路和首个 MT5 Demo/Worker 链路闭环。
