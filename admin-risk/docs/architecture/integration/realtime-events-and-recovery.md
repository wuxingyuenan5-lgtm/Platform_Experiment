# Platform V6 实时事件与状态恢复规范

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：前后端协作架构

## 1. 文档定位

本文档定义行情、订单、成交、执行批次、账户和风险状态的实时推送、重复与乱序处理、断线恢复和权威状态重建规则。

实时连接用于提高及时性，不是唯一数据来源。关键页面必须能够通过查询重新获得权威状态。

V1 实时事件只从 Platform API 对前端推送。浏览器不得直接连接交易所 API、MT5 Worker、Runtime 私有通道或保存任何交易凭证；前端看到的是平台整理后的状态投影，权威事实仍来自后端查询、Runtime Journal、交易所/MT5 历史查询和对账结果。

## 2. 适用数据

适合实时推送：

- 报价和行情质量。
- 订单状态变化。
- 新增成交。
- MT5 Deal、Position 和账户历史摘要。
- ExecutionBatch 状态。
- ExecutionBalanceStatus 和 ExposureStatus。
- 账户余额、保证金和持仓摘要。
- StrategyNavSnapshot 和 PnL 计算状态，适用时。
- 风险状态和阻断状态。
- Gateway、数据源和服务健康。
- 对账差异、审批和人工处理状态。

不适合只依赖实时推送：

- 历史订单完整查询。
- 正式报表。
- 长区间损益重算。
- 大批量数据导入。
- 权限、配置和账户主档的唯一来源。

## 3. 通信方式

可以采用：

- WebSocket：双向订阅和高频事件。
- SSE：服务端单向推送和较简单状态流。
- 消息代理到 Platform API，再由前端通道推送。

具体技术后续确定，但事件语义和恢复原则保持一致。

## 4. 连接生命周期

前端连接状态：

- `connecting`
- `connected`
- `degraded`
- `reconnecting`
- `disconnected`
- `unauthorized`

连接状态不得与业务对象状态、数据质量状态和 TradingPermissionState 混为一体。

## 5. 订阅模型

订阅主题使用稳定业务 ID，例如：

```text
market.instrument.{instrumentId}
trading.execution-batch.{executionBatchId}
trading.account.{accountId}
risk.strategy-instance.{strategyInstanceId}
system.gateway.{gatewayId}
approval.request.{approvalRequestId}
```

规则：

- 前端只订阅当前页面和授权范围需要的数据。
- 页面离开后释放无用订阅。
- 权限、账户范围或 TradingMode 变化后重新建立订阅。
- 不使用显示名称作为主题标识。
- 服务端再次校验订阅权限。

## 6. 事件信封

建议统一结构：

```ts
interface RealtimeEvent<T> {
  eventId: string;
  eventType: string;
  entityType: string;
  entityId: string;
  occurredAt: string;
  publishedAt: string;
  version?: number;
  sequence?: number;
  source: string;
  deploymentEnvironment: string;
  tradingMode?: string;
  correlationId?: string;
  causationId?: string;
  qualityStatus?: string;
  payload: T;
}
```

DeploymentEnvironment 和 TradingMode 分开传递，不使用单一 `environment` 字段混合表达。

## 7. 事件命名

事件名称使用已经发生的事实，并与领域对象一一对应，例如：

- `QuoteUpdated`
- `OrderAcknowledged`
- `OrderPartiallyFilled`
- `OrderFilled`
- `FillReceived`
- `DealReceived`
- `PositionSnapshotUpdated`
- `ExecutionBatchCreated`
- `ExecutionBatchStatusChanged`
- `ExecutionBalanceStatusChanged`
- `ExposureStatusChanged`
- `BalanceSnapshotUpdated`
- `StrategyNavSnapshotUpdated`
- `RiskDecisionChanged`
- `GatewayDisconnected`
- `ApprovalRequestApproved`

禁止使用：

- `ExecutionCreated`：无法区分执行批次和实际成交。
- `UpdateOrder`：命令式且语义含糊。
- `Success`：没有明确业务对象。

## 8. 重复事件

前端和服务端消费者必须能够安全处理相同 `eventId` 的重复投递。

- 已处理事件不重复产生通知和副作用。
- 当前状态更新具有幂等性。
- Fill 以稳定成交 ID 去重。
- MT5 Deal 以 DealId、Account、Gateway 和成交时间范围去重。
- 不仅凭显示时间去重。
- 重复事件仍可以计入可观测性指标。

## 9. 乱序和序列缺口

当事件具有 `version` 或 `sequence` 时：

- 旧版本不得覆盖新版本。
- 发现序列缺口时标记状态可能不完整。
- 触发对应资源权威查询。

没有可靠序列时，前端以权威查询结果恢复，不自行猜测顺序。

## 10. 断线重连

重连流程：

1. 标记实时连接中断。
2. 页面提示数据可能不是最新。
3. 根据安全策略执行指数退避重连。
4. 重新认证和恢复订阅。
5. 查询关键对象当前快照。
6. 用权威快照覆盖本地过期状态。
7. 从可用序列点继续接收事件。
8. 恢复正常状态。

不得只依赖补收断线期间事件而跳过权威快照查询。

## 11. 交易页面恢复

交易执行页重连后至少查询：

- TradeCommand 当前受理状态。
- ExecutionBatch 当前状态。
- 关联 Order、Fill 和 MT5 Deal。
- 当前 ExecutionBalanceStatus 和 ExposureStatus。
- 当前账户、持仓和保证金。
- 当前 BalanceSnapshot、PositionSnapshot 和必要的账户历史摘要。
- 当前 RiskDecision、全局阻断和 TradingPermissionState。
- 当前 result_unknown、ManualIntervention 和 ReconciliationDifference。

恢复完成前：

- 禁止重复提交相同命令。
- 对 unknown 状态显示明确提示。
- 不将本地最后一条事件视为最终结果。
- 不因实时连接恢复就自动重新开放交易。
- 不因页面刷新、浏览器重连或订阅恢复而重新下发 Runtime Command。

资费套利页面恢复时，还必须查询 FundingSettlement 或账户账本的最新入账状态，不能用断线前 Funding Rate 推算收益。跨所价差页面恢复时，必须同时查询 Crypto Runtime 与 MT5 Worker 经平台汇总后的订单、Deal、持仓和账户状态，不能只凭一侧事件判断组合完成。

## 12. 行情恢复

行情重连后：

- 获取最新 QuoteSnapshot。
- 比较报价时间和接收时间。
- 标记 delayed、stale 或 unavailable。
- 历史图表缺口通过历史查询补齐。
- 不用一条最新报价补造缺失 K 线。

## 13. 心跳与健康

实时通道支持：

- 心跳或 ping／pong。
- 服务端时间。
- 最近事件时间。
- 订阅确认。
- 降级和维护状态。

前端可以展示：

- 已连接。
- 延迟升高。
- 数据延迟。
- 正在恢复。
- 服务不可用。

连接正常不代表交易服务、Gateway 和风险服务全部可用。

## 14. 背压与优先级

高频行情和大量事件应支持：

- 按标的订阅。
- 服务端聚合或采样。
- 前端节流渲染。
- 重要事件优先。
- 最大队列和明确丢弃策略。

订单、成交、风险和阻断事件优先于图表刷新。不得因行情渲染阻塞交易状态处理。

## 15. 通知与业务事件

业务事件和用户通知分开：

- `OrderPartiallyFilled` 是业务事实。
- “订单部分成交，请关注”是 Notification。

Notification 模块决定渠道、阅读状态和聚合方式，不改变业务事件。

## 16. 安全

- 实时连接必须认证。
- 订阅执行数据时检查账户和策略数据范围。
- 令牌过期后停止推送敏感数据。
- 日志不记录完整凭证和敏感 payload。
- 不允许客户端通过伪造主题订阅其他账户。
- TradingMode 变化后必须重新验证订阅范围。

## 17. 可观测性

至少监控：

- 当前连接数。
- 重连次数。
- 事件发布和消费延迟。
- 重复事件量。
- 序列缺口。
- 订阅失败。
- 客户端恢复查询次数。
- 关键事件丢失告警。
- 业务事件积压和丢弃量。

## 18. 测试场景

至少覆盖：

- 正常连接和订阅。
- 连接短暂和长时间中断。
- 重复、乱序和序列缺口。
- 权限在连接期间变化。
- TradingMode 变化。
- 命令提交后立即断线。
- 部分成交期间断线。
- Gateway 中断和恢复。
- Fill 与订单状态事件乱序到达。
- 实时恢复期间风险阻断。
- Crypto 真实 API 模拟/测试链路 WebSocket 中断后，平台通过 REST 回补并重新推送权威快照。
- MT5 Demo/Worker 重启后，平台通过 Deal 历史和 Position 恢复并重新推送权威快照。
- 前端刷新、断线和重连都不会重复提交 TradeCommand 或 Runtime Command。
- result_unknown 期间收到迟到事件后，页面以权威查询结果覆盖本地状态。

## 19. 唯一来源

- 状态枚举：`../domain/status-enums-and-lifecycles.md`。
- API 契约：`api-contract-and-versioning.md`。
- 交易恢复流程：`../backend/trading-execution-reliability.md`。

## 20. 验收标准

- 实时通道不是唯一权威来源。
- 事件具有稳定 ID、对象类型、对象 ID、时间和来源。
- 事件名称与领域对象明确对应。
- 前端可处理重复、乱序和序列缺口。
- 断线重连后通过查询重建权威状态。
- 交易页面恢复前不会重复提交命令。
- 行情、订单、成交、风险和系统事件具有独立优先级和质量状态。
- 实时订阅执行服务端权限校验。
- V1 资费套利和跨所价差的实时恢复测试覆盖 Fake Gateway、首个 Crypto 真实 API 模拟/测试链路和首个 MT5 Demo/Worker 链路。
- 前端不直接连接交易所、MT5 Worker 或 Runtime 私有接口。
