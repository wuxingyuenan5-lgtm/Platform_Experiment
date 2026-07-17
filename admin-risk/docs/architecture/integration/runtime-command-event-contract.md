# Platform V6+ Runtime Command 与 Event 契约

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：Platform Backend 与 Execution Runtime 协作契约

上位与配套约束：

- `../platform-target-architecture.md`
- `../backend/execution-runtime-and-gateway.md`
- `../backend/trading-execution-reliability.md`
- `api-contract-and-versioning.md`
- `realtime-events-and-recovery.md`
- `../domain/unified-domain-model.md`
- `../domain/status-enums-and-lifecycles.md`
- `../decisions/ADR-008-总体逻辑分层与独立交易Runtime.md`

## 1. 文档定位

本文定义 Platform Backend 与独立 Execution Runtime 之间的正式 Command、Event、Envelope、版本、幂等、顺序、确认、过期、结果未知、Outbox／Inbox、Runtime Journal 和恢复契约。

本文是以下内容的唯一协作语义来源：

- Platform Backend 如何向 Runtime 发送执行命令。
- Runtime 如何报告命令受理、外部订单、成交、账户、持仓、Funding、Swap 和运行状态。
- 至少一次传输下如何避免重复外部下单和重复业务副作用。
- 传输超时、Worker 崩溃和外部结果未知时如何恢复。
- Command／Event 版本如何兼容和演进。

本文不决定：

- Redis Streams、RabbitMQ、NATS、Kafka 或其他传输产品。
- JSON、MessagePack、Protobuf 或其他最终序列化产品。
- Runtime Journal 使用 SQLite 或其他嵌入式存储。
- 首个 Crypto 交易所、MT5 Broker 和 SDK。
- 具体部署拓扑和网络产品。

任何传输实现必须满足本文契约，不得反向改变领域语义。

## 2. 核心原则

1. Command 表达请求发生某项动作，Event 表达已经发生的事实。
2. Platform Backend 是业务 Command 的唯一正式发起和持久化主体。
3. Runtime 只执行已经受理、授权并定向到自身的 Runtime Command。
4. 传输语义采用至少一次，消费者必须幂等。
5. Command 投递成功不等于 Runtime 已执行，更不等于外部订单已成功。
6. Event 发布失败不得导致 Runtime 重复外部下单。
7. 网络超时和连接中断不得直接解释为外部失败。
8. `result_unknown` 是待恢复状态，不是失败终态。
9. Platform 与 Runtime 均不得只依赖内存保存未完成链路。
10. 外部原始 ID、状态、错误和时间必须保留。
11. Secret、密码、API Key 和完整凭证不得进入 Command／Event payload。
12. 不兼容契约版本必须结构化拒绝，不能静默降级。

## 3. 协作边界

### 3.1 Platform Backend 负责

- 用户、Capability、DataScope、EnvironmentScope 和 TradingModeScope。
- Maker／Checker、ApprovalGrant 和 RiskDecision。
- StrategyInstance、StrategyAccountBinding 和 ExecutionPlan。
- TradeCommand、ExecutionBatch、LegInstruction 和 platformOrderId。
- Runtime Command Outbox。
- Runtime Event Inbox。
- 标准化 Order、Fill、Position、Account、EconomicEvent 和 PnL。
- 对账、人工处理、审计和 Read Model。

### 3.2 Execution Runtime 负责

- Runtime、Gateway、Worker 和外部 Session。
- Command 去重、路由和必要的防御性校验。
- 外部提交、撤销、查询、订阅和回报接收。
- Runtime OMS 缓存和 Runtime Local Journal。
- 外部状态、错误和 Symbol／ID 映射。
- Event 标准化、可靠保存和补发。
- 启动同步、恢复和对账输入。

### 3.3 Runtime 不得负责

- 重新决定用户权限和审批结论。
- 修改 StrategyVersion 业务规则。
- 自行创建未经 Platform 受理的正式 ExecutionBatch。
- 计算正式策略 PnL。
- 直接写 Platform 业务模块内部表。
- 将本地 Journal 当作永久交易账本。

## 4. 总体链路

```text
User / Controlled Strategy
→ Platform API
→ Application Use Case
→ TradeCommand
→ ExecutionBatch
→ ExecutionPlan
→ LegInstruction
→ pre-created platform Order
→ Runtime Command Outbox
→ RuntimeCommandEnvelope
→ Execution Runtime Inbox / Journal
→ Worker / Gateway Adapter
→ External Trading System
→ Raw Callback / Query Result
→ RuntimeEventEnvelope
→ Platform Event Inbox
→ Domain Processing
→ Order / Fill / Position / EconomicEvent
→ Read Model / Reconciliation / PnL
```

## 5. 通用 Envelope 约束

所有 Command 和 Event 必须包含：

- 全局稳定 ID。
- 契约名称和版本。
- 业务发生、创建、接收和发布时间中的适用时间。
- source 和 target。
- DeploymentEnvironment。
- TradingMode，适用时。
- correlationId 和 causationId。
- payloadVersion。
- 结构化 payload。

禁止在 Envelope 中传输：

- ORM Entity。
- Python、JavaScript 或其他语言类实例。
- 前端 View Model。
- 外部 SDK 完整对象。
- Secret 和完整凭证。
- 无版本的任意 Map 作为长期正式契约。

## 6. RuntimeCommandEnvelope

### 6.1 最小结构

```ts
interface RuntimeCommandEnvelope<TPayload> {
  commandId: string;
  commandType: string;
  contractName: 'runtime-command';
  contractVersion: string;
  payloadVersion: string;

  requestId: string;
  correlationId: string;
  causationId?: string;
  idempotencyKey: string;

  createdAt: string;
  expiresAt: string;

  sourceService: string;
  sourceEnvironment: string;
  deploymentEnvironment: string;
  tradingMode: string;

  runtimeInstanceId: string;
  gatewayRuntimeId: string;
  workerInstanceId?: string;

  fundId?: string;
  portfolioId?: string;
  bookId?: string;
  strategyInstanceId?: string;
  tradeCommandId?: string;
  executionBatchId?: string;
  legInstructionId?: string;
  platformOrderId?: string;

  operatorContextReference?: string;
  approvalGrantReference?: string;
  riskDecisionReference?: string;

  payload: TPayload;
}
```

### 6.2 Command 身份

- `commandId`：单次 Runtime Command 的稳定身份。
- `idempotencyKey`：业务幂等身份，作用域必须明确。
- 相同 commandId 重复到达必须返回原处理结果，不重复执行。
- 相同幂等键但 payload 哈希不同必须拒绝为冲突。
- 一个 TradeCommand 可以产生多个 Runtime Command，例如不同交易腿或后续撤单。

### 6.3 Command 目标

- `runtimeInstanceId` 必填。
- `gatewayRuntimeId` 必填。
- `workerInstanceId` 在平台明确绑定 Worker 时填写；否则由 Runtime 在已授权范围内路由。
- Runtime 不得将命令自动路由到不同 DeploymentEnvironment 或 TradingMode。
- Gateway／Worker 不可用时发布结构化拒绝或不可执行事件。

### 6.4 Command 过期

- 所有可能改变外部状态的 Command 必须具有 `expiresAt`。
- Runtime 收到已过期 Command 时不得执行外部动作。
- 过期必须形成 `RuntimeCommandExpired` Event。
- 过期不自动等同于对应 TradeCommand 或 ExecutionBatch 失败，Platform 根据业务上下文处理。

### 6.5 引用而非复制

Command 可以携带执行所需快照和参数，但业务身份使用稳定引用：

- StrategyInstanceId。
- ExecutionBatchId。
- LegInstructionId。
- platformOrderId。
- AccountId。
- InstrumentId。
- GatewayRuntimeId。

Runtime 不通过 Command 修改这些对象的业务定义。

## 7. Runtime Command 类型

### 7.1 订单类

- `SubmitOrderCommand`。
- `CancelOrderCommand`。
- `ReplaceOrderCommand`，Gateway 支持时。
- `ClosePositionCommand`。
- `ReducePositionCommand`。

### 7.2 查询与同步类

- `QueryOrderCommand`。
- `QueryOpenOrdersCommand`。
- `QueryFillsCommand`。
- `QueryPositionsCommand`。
- `QueryAccountCommand`。
- `QueryFundingSettlementsCommand`。
- `SynchronizeGatewayCommand`。

### 7.3 Runtime 管理类

- `StartGatewayCommand`。
- `StopGatewayCommand`。
- `RestartWorkerCommand`。
- `RefreshCapabilityCommand`。
- `BeginRecoveryCommand`。
- `SetGatewayReadOnlyCommand`。
- `BlockGatewayTradingCommand`。

Runtime 管理命令与交易业务命令必须采用不同 Capability、审批和审计范围。

### 7.4 算法执行类

- `StartExecutionAlgorithmCommand`。
- `PauseExecutionAlgorithmCommand`。
- `ResumeExecutionAlgorithmCommand`。
- `StopExecutionAlgorithmCommand`。

算法命令必须关联 ExecutionBatch、ExecutionPlan 和 LegInstruction，不能在 Runtime 内形成孤立的第二套业务交易目标。

## 8. SubmitOrderCommand Payload

建议最小结构：

```ts
interface SubmitOrderPayload {
  accountId: string;
  instrumentId: string;
  externalSymbolReference: string;

  side: 'buy' | 'sell';
  positionEffect?: 'open' | 'close' | 'close_today' | 'close_yesterday' | 'reduce';
  orderType: string;
  timeInForce?: string;

  quantity: string;
  quantityUnit: string;
  limitPrice?: string;
  stopPrice?: string;
  priceCurrency?: string;

  reduceOnly?: boolean;
  postOnly?: boolean;

  clientOrderId?: string;
  magicNumber?: number;
  externalComment?: string;

  maxSlippage?: string;
  algorithmReference?: string;
  metadataVersion: string;
}
```

规则：

- Decimal 使用字符串传输，禁止 IEEE 浮点隐式转换。
- Currency、Unit 和 Instrument 元数据版本必须明确。
- Runtime 必须再次检查数量、精度、最小名义价值和当前 GatewayCapability。
- 防御性校验失败形成结构化 Event，不替代 Platform RiskDecision。
- platformOrderId 必须在 Command 发送前已存在。

## 9. RuntimeEventEnvelope

### 9.1 最小结构

```ts
interface RuntimeEventEnvelope<TPayload> {
  eventId: string;
  eventType: string;
  contractName: 'runtime-event';
  contractVersion: string;
  payloadVersion: string;

  sourceRuntimeId: string;
  sourceRuntimeSessionId: string;
  sourceGatewayRuntimeId?: string;
  sourceWorkerInstanceId?: string;

  correlationId: string;
  causationId?: string;
  commandId?: string;

  deploymentEnvironment: string;
  tradingMode?: string;

  fundId?: string;
  portfolioId?: string;
  bookId?: string;
  strategyInstanceId?: string;
  tradeCommandId?: string;
  executionBatchId?: string;
  legInstructionId?: string;
  platformOrderId?: string;

  externalReference?: ExternalReference;

  occurredAt: string;
  externalTime?: string;
  receivedAt: string;
  publishedAt: string;

  sequence?: number;
  streamKey?: string;
  dataQualityStatus?: string;

  payload: TPayload;
}
```

### 9.2 Event 原则

- Event 名称使用过去式或已发生事实。
- Event 可以重复、延迟、乱序和补发。
- Platform Event Inbox 使用 eventId 幂等消费。
- 旧 sequence 或旧实体版本不得覆盖更新状态。
- 没有可靠 sequence 时必须通过外部查询和对账恢复，不能猜测。
- Event 不因 Platform 暂时不可用而丢弃。

### 9.3 ExternalReference

建议表达：

```ts
interface ExternalReference {
  externalSystem: string;
  venueId?: string;
  brokerId?: string;
  externalAccountId?: string;
  externalObjectType: string;
  externalId?: string;
  clientOrderId?: string;
  externalStatus?: string;
  externalErrorCode?: string;
  rawReferenceId?: string;
}
```

完整原始 payload 可以进入受控原始事件存储或对象存储，不要求全部复制进标准 Event。

## 10. Runtime Event 类型

### 10.1 Command 生命周期

- `RuntimeCommandReceived`。
- `RuntimeCommandAccepted`。
- `RuntimeCommandRejected`。
- `RuntimeCommandExpired`。
- `RuntimeCommandResultUnknown`。
- `RuntimeCommandCompleted`。

`RuntimeCommandCompleted` 只表示 Runtime 对该 Command 的处理流程完成，不自动表示 ExecutionBatch 完成。

### 10.2 外部订单

- `ExternalOrderSubmissionStarted`。
- `ExternalOrderAcknowledged`。
- `ExternalOrderRejected`。
- `ExternalOrderPartiallyFilled`。
- `ExternalOrderFilled`。
- `ExternalOrderCancelRequested`。
- `ExternalOrderCancelled`。
- `ExternalOrderCancelRejected`。
- `ExternalOrderStatusUnknown`。
- `ExternalOrderDiscovered`。

### 10.3 成交

- `ExternalFillReceived`。
- `ExternalFillCorrected`，仅上游存在正式修正时。
- `ExternalFillReversed`，仅上游存在正式冲销时。

Fill 去重优先使用稳定 externalFillId／DealId；没有稳定 ID 时使用正式替代去重键并记录可靠等级。

### 10.4 账户和持仓

- `ExternalAccountSnapshotReceived`。
- `ExternalBalanceSnapshotReceived`。
- `ExternalMarginSnapshotReceived`。
- `ExternalPositionSnapshotReceived`。
- `ExternalOpenOrdersSnapshotReceived`。

Snapshot Event 必须包含 `dataAsOf`、来源和完整／增量语义。

### 10.5 Funding、Swap 和费用

- `FundingRateSnapshotReceived`。
- `FundingSettlementReceived`。
- `SwapSettlementReceived`。
- `CommissionReceived`。
- `FeeReceived`。

FundingRateSnapshot 不等于 FundingSettlement；预计值不得作为实际经济事实。

### 10.6 Runtime 和 Gateway

- `RuntimeStarted`。
- `RuntimeStopped`。
- `RuntimeDegraded`。
- `RuntimeRecoveryStarted`。
- `RuntimeRecoveryCompleted`。
- `RuntimeRecoveryFailed`。
- `GatewayConnected`。
- `GatewayDisconnected`。
- `GatewayAuthenticated`。
- `GatewaySynchronizationStarted`。
- `GatewaySynchronizationCompleted`。
- `GatewayReady`。
- `GatewayReadOnly`。
- `GatewayBlocked`。
- `GatewayCapabilityChanged`。
- `WorkerStarted`。
- `WorkerStopped`。
- `WorkerCrashed`。

`GatewayConnected` 不表示可以交易；只有 Connectivity、Authentication、Synchronization、Recovery 和 Capability 均满足条件后才形成 `GatewayReady`。

### 10.7 数据质量和对账输入

- `RuntimeSequenceGapDetected`。
- `ExternalDataDelayed`。
- `ExternalDataConflictDetected`。
- `UnallocatedExternalOrderDetected`。
- `UnallocatedExternalFillDetected`。
- `RuntimeReconciliationSnapshotProduced`。

Runtime 只提供事实和差异输入，Platform Reconciliation 是正式差异对象和处置主体。

## 11. Command 状态与 Event 关系

推荐 Runtime Command 处理状态：

```text
created
→ published
→ received
→ accepted / rejected / expired
→ executing
→ completed / result_unknown
```

规则：

- `published` 表示 Platform Outbox 已成功投递，不表示 Runtime 已收到。
- `received` 表示 Runtime Journal 已持久化接收证据。
- `accepted` 表示 Runtime 能够处理该命令，不表示外部动作成功。
- `completed` 表示 Command 处理流程完成。
- 外部 Order 和 Fill 状态由独立 Event 表达。
- `result_unknown` 后必须通过 Query、同步和对账恢复。

## 12. Outbox、Inbox 与 Journal

### 12.1 Platform Runtime Command Outbox

至少保存：

- commandId。
- Envelope 和 payload 哈希。
- 目标 Runtime／Gateway。
- 发布状态、尝试次数和最近错误。
- 创建、下次重试和确认时间。

规则：

- 业务事务与 Outbox 记录使用本地事务提交。
- 发布失败可以重试，但不能创建新 commandId 规避历史。
- Outbox 不直接标记外部订单成功。

### 12.2 Runtime Command Inbox／Journal

至少保存：

- 已接收 commandId。
- payload 哈希。
- 接收和处理状态。
- Worker 路由结果。
- 外部请求证据。
- 结果摘要。
- 已产生 Event 引用。

规则：

- 重复 commandId 返回原结果摘要。
- 相同 commandId 不同 payload 拒绝并告警。
- Journal 写入失败时不得执行可能产生外部副作用的命令。

### 12.3 Runtime Event Outbox／Journal

至少保存：

- eventId。
- Event Envelope。
- 产生原因和来源 Worker。
- 发布尝试和确认位置。
- 保留和清理状态。

Event 通道不可用时先持久化，恢复后补发。

### 12.4 Platform Event Inbox

至少保存：

- eventId。
- 来源 Runtime／Session／Gateway。
- payload 哈希。
- 接收和处理状态。
- 领域处理结果。
- 失败、重试和人工状态。

同一 eventId 不重复产生 Order、Fill、EconomicEvent、通知或审计副作用。

## 13. 确认语义

传输层确认与业务确认分开：

- Transport Ack：消息已被传输基础设施接收。
- Runtime Received：Runtime Journal 已保存 Command。
- Runtime Accepted：Runtime 已通过契约和能力校验。
- External Acknowledged：外部系统已确认订单或请求。
- Domain Applied：Platform 已将 Event 应用于权威领域状态。

不得将 Transport Ack 显示为“下单成功”。

## 14. 顺序、重复与乱序

### 14.1 顺序范围

不要求全平台全局有序。可以在以下范围提供 sequence：

- RuntimeSession。
- GatewayRuntime。
- Account。
- external order。
- streamKey。

### 14.2 重复

- Command 消费按 commandId 和 idempotencyKey 去重。
- Event 消费按 eventId 去重。
- Fill 按 externalFillId 或正式替代键去重。
- Snapshot 按 source、account、dataAsOf 和版本判断。

### 14.3 乱序

- 旧版本不得覆盖新版本。
- Fill 可以先于 Order Acknowledged 到达，平台必须容忍。
- Cancelled 可以晚于 Fill 到达，已发生 Fill 不得删除。
- 发现 sequence gap 时标记数据不完整并触发 Query／Recovery。

## 15. 重试政策

### 15.1 可以自动重试

- 只读查询。
- Event 发布。
- Command 投递。
- 明确未到达外部系统的操作。
- 外部支持稳定 clientOrderId 且可先查询确认的恢复动作。

### 15.2 不得盲目自动重试

- 结果未知的 SubmitOrder。
- 结果未知的 Cancel／Replace。
- 无稳定幂等或查询能力的外部接口。
- 可能扩大单腿暴露的动作。
- Risk、Approval、Account 或 Capability 已变化的命令。

重试前必须重新判断 Command 是否过期、Gateway 是否 READY，以及业务上下文是否仍允许。

## 16. 结果未知

出现以下情况时进入 `result_unknown`：

- 外部请求超时但无法确认是否到达。
- Worker 在提交后、记录结果前崩溃。
- Runtime 与外部系统断开，订单状态无法查询。
- 外部返回含糊或互相冲突的结果。
- clientOrderId 查询与账户历史仍无法确认。

恢复顺序：

```text
标记 result_unknown
→ 禁止重复提交
→ 查询 clientOrderId / externalOrderId
→ 查询 Open Orders / Order History / Fills
→ 查询 Position / Account
→ 对账 platformOrderId 映射
→ 恢复明确状态
→ 或进入 ManualIntervention
```

未知状态持续期间，Platform 可以按风险规则阻断对应策略、账户或 Gateway 新增风险。

## 17. 启动与恢复契约

Runtime／Gateway 启动不直接进入 READY。

```text
starting
→ connecting
→ authenticating
→ synchronizing
→ reconciling
→ recovering
→ risk_confirming
→ ready / read_only / blocked
```

Runtime 必须发布：

- 本次 RuntimeSession。
- 当前软件、配置和契约版本。
- GatewayCapability。
- 同步范围和 dataAsOf。
- 未完成 Command 数量。
- 未发送 Event 数量。
- unknown Order 数量。
- 未归属外部 Order／Fill 数量。
- Recovery 结果。

Platform 在恢复完成前不得自动开放新增 Live 风险。

## 18. 外部手工订单和未知归属

Runtime 发现非平台发起的外部订单、成交或持仓时：

1. 发布 `ExternalOrderDiscovered` 或对应 Event。
2. 保留 Account、Instrument、Magic、Comment、Tag、时间和外部 ID。
3. 尝试按正式映射规则关联 StrategyInstance 和 platformOrderId。
4. 无法确认时标记 `unallocated`／`unverified`。
5. Platform 创建 ReconciliationDifference 或人工归属任务。
6. 归属修正形成审计，不无痕修改原始发现事实。

## 19. 版本管理

### 19.1 Contract Version

`contractVersion` 表达 Envelope 和通用传输语义版本。

破坏性变化包括：

- 删除必填字段。
- 改变字段含义。
- 改变 ID 作用域。
- 改变时间、金额或单位语义。
- 改变确认和幂等语义。

### 19.2 Payload Version

`payloadVersion` 表达具体 Command／Event payload 版本。

同一 contractVersion 下可以并存多个 payloadVersion，但消费者必须声明支持范围。

### 19.3 兼容规则

消费者必须：

- 忽略未知可选字段。
- 对未知必需语义或不兼容版本明确拒绝。
- 对未知 Event 类型保存原始 Envelope 并告警，不得崩溃或误应用。
- 对新增枚举值使用 unknown／unsupported 降级，不按默认成功处理。

### 19.4 Runtime 注册

RuntimeDefinition 和 RuntimeInstance 必须声明：

- 支持的 contractVersion。
- 支持的 Command 类型和 payloadVersion。
- 发布的 Event 类型和 payloadVersion。
- GatewayCapability 版本。

Platform 在发送 Command 前校验版本兼容性。

## 20. 错误结构

建议：

```ts
interface RuntimeError {
  code: string;
  category: string;
  message: string;
  retryable: boolean;
  resultUnknown: boolean;
  externalErrorCode?: string;
  externalStatus?: string;
  fieldErrors?: Array<{
    field: string;
    code: string;
    message: string;
  }>;
  rawReferenceId?: string;
}
```

错误分类至少包括：

- `contract`。
- `routing`。
- `capability`。
- `validation`。
- `authentication`。
- `connectivity`。
- `rate_limit`。
- `external_rejection`。
- `timeout`。
- `result_unknown`。
- `internal`。

中文文案可以变化，稳定错误码不得变化。

## 21. 安全

- Platform 与 Runtime 使用独立服务身份和双向认证能力。
- Command 来源必须验证，不接受任意客户端直连 Runtime。
- Runtime 管理命令与交易命令分权。
- SecretReference 只指向受控密钥，不携带 Secret。
- payload 和日志执行脱敏。
- 防止跨 DeploymentEnvironment 和 TradingMode 重放。
- 过期 Command 不执行。
- 高风险命令保留 ApprovalGrant 和 OperatorContext 引用。
- Event Inbox 和 Journal 访问受最小权限控制。

## 22. 可观测性

至少监控：

- Command Outbox 积压。
- Runtime Command 接收和处理延迟。
- Command 重复和幂等冲突。
- Event Outbox 积压和补发次数。
- Event Inbox 处理失败。
- sequence gap 和乱序。
- result_unknown 数量和持续时间。
- 各 Command／Event 类型错误率。
- Runtime／Gateway 契约版本不兼容。
- 未归属外部订单和成交。
- Journal 写入、读取和清理失败。

## 23. 测试要求

契约实现至少覆盖：

1. 正常 SubmitOrder → Ack → Fill。
2. Command 重复投递。
3. 相同 commandId 不同 payload。
4. Event 重复投递。
5. Fill 先于 Order Ack。
6. 部分成交后撤单。
7. Event 发布失败后补发。
8. Runtime 在外部提交后崩溃。
9. Platform 在 Event 到达前重启。
10. 外部结果未知。
11. Command 过期。
12. GatewayCapability 变化。
13. 不兼容 contractVersion。
14. 未知可选字段。
15. 未知 Event 类型。
16. sequence gap。
17. 外部手工订单发现。
18. MT5 Magic／Comment 映射。
19. Crypto clientOrderId 恢复。
20. CTP 平今／平昨字段兼容，后续。

应通过机器可读 Schema 和契约测试验证，不只依赖文档阅读。

## 24. 实施产物要求

后续工程建设必须形成：

- Runtime Command JSON Schema／Protobuf Schema 或等效机器契约。
- Runtime Event Schema。
- Command／Event 类型注册表。
- 稳定错误码注册表。
- 版本兼容矩阵。
- Platform Producer／Consumer 契约测试。
- Runtime Producer／Consumer 契约测试。
- Fake Gateway 故障注入测试。
- 示例消息和脱敏测试夹具。

生成代码可以用于 DTO，但不得替代 Domain Model。

## 25. 验收标准

- Platform 与 Runtime 只通过正式契约协作。
- Command 和 Event 语义严格分开。
- 传输采用至少一次且消费者幂等。
- platformOrderId 在外部提交前存在。
- Command 投递、Runtime 受理、外部确认和领域应用分别表达。
- Event 发布失败不会造成重复外部下单。
- result_unknown 不被误判为失败并盲目重试。
- Command／Event 具备稳定 ID、版本、时间和关联上下文。
- Decimal、Currency 和 Unit 语义明确。
- Runtime Journal、Platform Outbox 和 Inbox 各自边界明确。
- 外部手工订单和未知归属不会被丢弃。
- 契约可通过机器可读 Schema 和自动测试验证。
