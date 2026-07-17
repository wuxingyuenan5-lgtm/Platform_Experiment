# ADR-010：Platform 与 Runtime 采用可靠消息与结果未知语义

状态：`accepted`  
日期：2026-07-18  
适用分支：`refactor/frontend-architecture-v6`

## 背景

ADR-008 已确认 Platform Backend 与 Execution Runtime 必须保持独立进程，并通过平台自有契约协作。

真实交易链路无法依赖一次同步 HTTP／RPC 调用，因为：

- 外部订单可能已到达交易所，但调用方只收到超时。
- Runtime、Worker、Platform 或传输通道可能在不同阶段重启。
- Event 可能重复、延迟、乱序或暂时无法发布。
- MT5、Crypto 和后续 CTP 的外部幂等与查询能力不同。
- 双腿策略中盲目重试可能扩大单腿暴露。

如果不固定可靠消息语义，不同实现可能分别假设“最多一次”“恰好一次”或“超时即失败”，从而产生重复下单和状态丢失。

## 决策

### 1. 采用至少一次传输

Platform Runtime Command 和 Runtime Event 的传输语义采用至少一次。

系统接受消息可能重复，要求消费者通过稳定 ID 和业务幂等保证不会重复产生外部或领域副作用。

不宣称通过消息中间件实现端到端“恰好一次”。

### 2. Platform 使用 Command Outbox

Platform 在创建正式 Runtime Command 时，将业务事实和待发布 Command Outbox 记录置于可验证的本地事务边界。

Outbox 发布失败可以重试，但不得通过创建新的 commandId 隐藏历史失败。

### 3. Runtime 使用 Command Inbox／Local Journal

Runtime 在执行可能产生外部副作用的 Command 前，必须持久化：

- commandId。
- idempotencyKey。
- payload 哈希。
- 接收和处理状态。
- Worker 路由。
- 外部请求证据和结果摘要。

Journal 不可用时，不得执行可能产生外部交易副作用的 Command。

### 4. Runtime 使用 Event Outbox／Journal

Runtime 产生 Event 后先可靠保存，再发送给 Platform。

Event 通道不可用时允许补发；Event 发布失败不得导致重复外部下单。

### 5. Platform 使用 Event Inbox

Platform 根据 eventId 幂等消费 Runtime Event。

同一 Event 不得重复产生：

- Order 或 Fill。
- Position 变化。
- EconomicEvent。
- RiskEvent。
- Notification。
- Audit 副作用。

### 6. 固定结果未知语义

网络超时、Worker 崩溃、外部状态冲突或无法确认请求是否到达时，使用 `result_unknown`。

`result_unknown`：

- 不是成功。
- 不是失败终态。
- 不允许盲目重复提交。
- 必须通过 clientOrderId、externalOrderId、订单历史、成交、持仓和账户查询恢复。
- 无法自动恢复时进入 ManualIntervention。

### 7. 区分五类确认

必须分别表达：

1. Transport Ack：传输设施已接收。
2. Runtime Received：Runtime Journal 已保存。
3. Runtime Accepted：Runtime 已通过契约和能力校验。
4. External Acknowledged：外部系统已确认请求或订单。
5. Domain Applied：Platform 已将 Event 应用于权威领域状态。

任何前层确认不得被页面显示为后层成功。

### 8. 固定消息身份

- Runtime Command 使用稳定 commandId。
- Runtime Event 使用稳定 eventId。
- 外部订单提交前必须已有 platformOrderId。
- 可用时使用 clientOrderId／Magic／Comment／Tag 建立外部恢复关系。
- Fill 使用 externalFillId／DealId 或正式替代去重键。

### 9. 固定版本边界

Command 和 Event 均包含：

- contractVersion。
- payloadVersion。
- correlationId。
- causationId，适用时。
- DeploymentEnvironment。
- TradingMode，适用时。
- source 和 target。
- 业务稳定 ID。

不兼容版本明确拒绝并形成结构化事件。

### 10. 不决定具体消息产品

本 ADR 不决定：

- Redis Streams。
- RabbitMQ。
- NATS。
- Kafka。
- 其他消息产品。
- JSON、Protobuf 或其他序列化方式。
- Runtime Journal 的具体存储产品。

具体产品必须通过 PoC 证明满足本 ADR 和 `integration/runtime-command-event-contract.md`。

## 原因

- 交易系统无法依赖网络请求返回值判断最终状态。
- 至少一次加幂等比伪造端到端恰好一次更符合实际。
- Outbox／Inbox 解决数据库事实与消息发布之间的可靠衔接。
- Runtime Journal 解决 Runtime 重启和重复 Command。
- result_unknown 防止超时后重复下单。
- 明确确认层级避免前端和运营人员误判交易状态。

## 影响

- Platform Backend 必须实现 Runtime Command Outbox 和 Event Inbox。
- Execution Runtime 必须实现 Command Inbox／Journal 和 Event Outbox／Journal。
- Command／Event 需要机器可读 Schema 和契约测试。
- Fake Gateway 必须覆盖重复、乱序、超时、崩溃和补发场景。
- 前端不得将 Command accepted 或 Transport Ack 显示为交易成功。
- 对账和恢复必须能够读取 platformOrderId 与外部引用关系。

## 禁止事项

- 不以 HTTP／RPC 超时直接判定外部订单失败。
- 不在 Event 发布失败后重复执行原外部请求。
- 不通过生成新 ID 绕过失败和未知历史。
- 不依赖消息代理提供端到端恰好一次承诺。
- 不让 Runtime Journal 成为平台永久交易数据库。
- 不让 Platform 直接修改 Runtime Journal。
- 不让 Runtime 直接写 Platform 领域内部表。

## 配套文档

- `../integration/runtime-command-event-contract.md`
- `../backend/execution-runtime-and-gateway.md`
- `../backend/trading-execution-reliability.md`
- `ADR-008-总体逻辑分层与独立交易Runtime.md`

## 重新讨论条件

出现以下情况时可以新增 ADR 扩展或替代本决策：

- 目标外部交易系统提供可验证的不同事务语义。
- 平台和 Runtime 不再保持独立进程。
- 合规要求强制采用特定传输和审计机制。
- 实际 PoC 证明当前语义无法满足性能或恢复要求。
