# Platform V6 前后端协作架构

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：前后端协作架构

## 1. 文档定位

本文档定义前端与后端之间的职责、交互类型和基础数据约定。具体 API 路径、错误、幂等和版本规则以 `api-contract-and-versioning.md` 为唯一来源；实时事件和恢复以 `realtime-events-and-recovery.md` 为唯一来源。

协作目标：

- 对同一业务对象使用同一稳定语义和 ID。
- 区分 Query、Command 和 Event。
- 让 Mock 和真实 API 可以通过 Adapter 替换。
- 避免前端补造业务事实。
- 保持 DeploymentEnvironment、TradingMode 和 TradingPermissionState 分开。

## 2. 职责边界

### 前端负责

- 收集用户输入。
- 展示数据、状态和来源。
- 执行基础格式校验。
- 展示权限、风险、审批和交易能力结果。
- 发起 Query 和 Command。
- 订阅 Event。
- 处理加载、错误、重试和恢复交互。

### 后端负责

- 身份认证和最终权限判定。
- DeploymentEnvironment、TradingMode 和交易能力上下文。
- 业务规则、风险和审批校验。
- TradeCommand、ExecutionBatch、Order、Fill、Account、Position、PnL 和 Risk 事实。
- 幂等、审计、持久化和恢复。
- 与外部交易和数据系统通信。

前端校验用于改善体验，不替代后端校验。

## 3. Query

Query 用于读取数据，不改变核心业务事实。

示例：

- 查询策略和策略实例。
- 查询行情、研究数据和数据质量。
- 查询账户、持仓、订单、成交和执行批次。
- 查询损益、风险、对账和审批状态。
- 查询页面 Backend Read Model。

Query 响应至少根据场景提供：

- 数据主体。
- requestId 和 serverTime。
- dataTime 或数据截止时间。
- 来源和 DataQualityStatus。
- 分页和版本信息，适用时。

权威对象查询与页面聚合 Read Model 的边界参见 `../backend/query-and-read-models.md`。

## 4. Command

Command 用于请求改变业务状态。

示例：

- 提交交易。
- 撤单、平仓和配平。
- 启停策略实例。
- 确认对账差异。
- 发起和处理审批。
- 修改风险规则和账户绑定。

命令至少包含：

- `requestId`
- `idempotencyKey`
- 目标业务对象 ID
- 命令参数
- 客户端提交时间
- `approvalGrantId`，适用时

操作人、能力、数据范围、DeploymentEnvironment 和 TradingMode 从受信任会话上下文获得，不接受前端伪造。

命令响应区分：

- 已受理。
- 已拒绝。
- 参数错误。
- 权限或审批不足。
- 结果未知。

“已受理”不等于“已成交”或“已完成”。

## 5. Event

Event 通知已经发生的事实，例如：

- QuoteUpdated。
- TradeCommandAccepted。
- ExecutionBatchCreated。
- ExecutionBatchStatusChanged。
- OrderAcknowledged。
- FillReceived。
- RiskDecisionChanged。
- ApprovalRequestApproved。
- GatewayDisconnected。

事件至少包含：

- `eventId`
- `eventType`
- `occurredAt`
- `entityType`
- `entityId`
- `version` 或 sequence，适用时
- 来源和环境上下文
- 事件数据

前端和后端消费者处理重复、延迟和乱序事件。

## 6. 通信方式

### REST／HTTP

适用于：

- 页面初始化。
- 条件查询。
- 权威对象和 Read Model 查询。
- 命令提交。
- 历史数据和报表。
- 文件导入导出。

### WebSocket／SSE

适用于：

- 行情更新。
- 订单、Fill 和 ExecutionBatch 状态。
- 账户、保证金、持仓和风险状态。
- Gateway 和数据质量告警。
- 审批和人工处理状态。

实时连接断开后，前端通过重新查询恢复权威状态。

## 7. 统一响应和错误

面向前端的 Platform API 使用一致响应结构，至少包含：

- requestId。
- data 或 error。
- serverTime。
- traceId，发生错误或需要追踪时。

错误提供：

- 稳定错误码。
- 用户可理解信息。
- 是否可重试。
- 受影响对象。
- 字段错误，适用时。

前端不得解析自然语言错误文本判断业务类型。

完整规则参见 `api-contract-and-versioning.md`。

## 8. 权限、审批和交易能力协作

后端返回：

- 当前用户身份。
- 角色和能力权限。
- 数据范围。
- DeploymentEnvironment。
- TradingMode。
- TradingPermissionState 和原因。
- 适用风险限制和审批要求。

前端据此：

- 控制页面访问。
- 隐藏或禁用操作。
- 显示禁用和审批原因。
- 避免发起明显无效的请求。

后端仍对每个 Command 执行最终权限、风险、审批和对象版本检查。

## 9. 时间规范

- 传输时间优先使用 ISO 8601。
- 后端保存 UTC 或明确时区时间。
- 前端按用户时区展示。
- 业务日期与自然时间分开。
- 行情时间、来源时间、接收时间、计算时间和更新时间分开。

常用字段：

- `businessDate`
- `occurredAt`
- `sourceTime`
- `receivedAt`
- `calculatedAt`
- `updatedAt`
- `dataTime`

## 10. 金额、数量和币种

金额和数量不得只返回格式化字符串。

```ts
interface MoneyValue {
  amount: string;
  currency: string;
}

interface QuantityValue {
  amount: string;
  unit: string;
}
```

规则：

- 高精度数字使用字符串传输。
- 金额带币种。
- 数量带单位、合约乘数或 Instrument 引用。
- 汇率包含币种对、来源和时间。
- 前端格式化不改变原始值。

## 11. 状态枚举

状态码和生命周期以 `../domain/status-enums-and-lifecycles.md` 为唯一来源。

至少分别使用：

- QuoteStatus。
- DataQualityStatus。
- TradeCommandStatus。
- ExecutionBatchStatus。
- OrderStatus。
- ExecutionBalanceStatus。
- ExposureStatus。
- RiskStatus。
- ReconciliationStatus。
- ApprovalStatus。
- DeploymentEnvironment。
- TradingMode。
- TradingPermissionState。

不同接口不得使用 `success`、`done` 等模糊词替代业务状态。

## 12. DTO、Domain、Read Model 和 View Model

```text
External / API DTO
        ↓ Adapter
Domain Model
        ↓ projection
Backend Read Model
        ↓ API DTO
Frontend Adapter
        ↓
Frontend View Model
```

- API DTO 可以按接口版本变化。
- Domain Model 保持稳定业务语义。
- Backend Read Model 服务查询，不拥有写入权。
- View Model 服务页面展示。

## 13. Mock 与正式接口迁移

```text
Page / Use Case
      ↓
Repository Interface
  ├─ Mock Adapter
  └─ API Adapter
```

要求：

- Mock 使用正式 StrategyId、业务 ID 和状态枚举。
- Mock 时间、币种、单位和质量结构接近正式契约。
- 页面不通过 `isMock` 维护两套业务逻辑。
- Demo 和 Simulation 明确标识。
- 接入 API 时主要替换 DTO、Adapter 和 Repository 实现。

## 14. 双腿交易协作

```text
前端准备 TradeIntent 和参数
  ↓
POST TradeCommand
  ↓
后端权限、模式、风险、审批和幂等检查
  ↓
返回 TradeCommand 受理结果和 ExecutionBatch ID
  ↓
后端执行 LegInstruction 和 Order
  ↓
Event 推送 Order、Fill、配平和暴露变化
  ↓
前端按 ExecutionBatch 聚合展示
  ↓
断线后通过 Query 恢复权威状态
```

前端不得将两次独立 Order 请求自行拼接成可靠双腿执行批次。

## 15. 唯一来源

- API、错误、幂等和版本：`api-contract-and-versioning.md`。
- 实时事件和恢复：`realtime-events-and-recovery.md`。
- 状态枚举：`../domain/status-enums-and-lifecycles.md`。
- 公共对象：`../domain-model-boundaries.md`。
- Read Model：`../backend/query-and-read-models.md`。

## 16. 验收标准

- 相同对象在 Query、Command 和 Event 中使用相同稳定 ID。
- 前端可以从 Mock Adapter 切换到 API Adapter而不重写页面结构。
- 权限、审批、风险和交易能力协作清晰。
- DeploymentEnvironment 与 TradingMode 分开。
- 错误、状态、币种、时间和分页规则统一。
- 实时连接断开后可以重新获取权威状态。
- 页面不通过自然语言字符串推断核心业务状态。
