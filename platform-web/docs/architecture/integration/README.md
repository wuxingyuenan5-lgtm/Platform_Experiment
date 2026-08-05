# Platform 0.10.x+ 协作契约入口

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`

## 1. 文档定位

本目录定义前端、Platform Backend、Execution Runtime 和外部系统之间的 Query、Command、Event、API、实时推送、可靠传输、恢复和版本规则。

协作契约不拥有 Strategy、Order、Account、Risk、PnL 等领域事实；它负责规定这些事实如何安全、稳定、可追踪地跨边界交换。

## 2. 核心文档

- `frontend-backend-integration.md`：前端与 Platform Backend 的总体协作方式。
- `api-contract-and-versioning.md`：面向前端的 Platform API、错误、幂等和版本规则。
- `realtime-events-and-recovery.md`：前端实时订阅、重复、乱序和断线恢复。
- `runtime-command-event-contract.md`：Platform Backend 与 Execution Runtime 的正式可靠 Command／Event 契约。

## 3. 两条不同协作链

### 3.1 前端与 Platform Backend

```text
Frontend
→ Query / Command
→ Platform API
→ Domain
→ Query / Realtime Event
→ Frontend
```

前端不直接访问 Execution Runtime、交易所、Broker、MT5 或 CTP。

### 3.2 Platform Backend 与 Execution Runtime

```text
Platform Domain
→ Runtime Command Outbox
→ RuntimeCommandEnvelope
→ Runtime Journal / Worker / Gateway
→ External Trading System
→ RuntimeEventEnvelope
→ Platform Event Inbox
→ Domain Processing
```

## 4. 共同原则

- Query、Command 和 Event 分开。
- Command accepted 不等于外部交易完成。
- Runtime Command 与前端 Command 不是同一个对象。
- 至少一次传输要求消费者幂等。
- 结果未知不是失败终态。
- 实时 Event 不是恢复的唯一来源。
- Decimal、Currency、Unit 和时间语义必须明确。
- 所有关键消息具有稳定 ID、版本、correlationId 和 causationId。
- 前端、Runtime 和外部 DTO 不直接成为领域模型。

## 5. 可靠消息决策

ADR-010 已确认：

- Platform Runtime Command Outbox。
- Runtime Command Inbox／Local Journal。
- Runtime Event Outbox／Journal。
- Platform Event Inbox。
- 至少一次传输。
- commandId／eventId 幂等。
- platformOrderId 预创建。
- result_unknown 和主动恢复。

具体消息中间件和序列化产品仍需 PoC。

## 6. 后续工程产物

后端和 Runtime 建设阶段必须形成：

- OpenAPI。
- Runtime Command Schema。
- Runtime Event Schema。
- 错误码注册表。
- Command／Event 类型注册表。
- 版本兼容矩阵。
- Producer／Consumer 契约测试。
- Fake Gateway 测试夹具。

机器可读 DTO 不替代 Domain Model 和 View Model。
