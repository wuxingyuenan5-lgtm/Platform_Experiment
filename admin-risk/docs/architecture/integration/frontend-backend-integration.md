# Platform V6 前后端协作架构

状态：`active`  
适用分支：`refactor/frontend-architecture-v6`

## 1. 文档定位

本文档定义前端与后端之间的职责分工、数据交换原则和接口约束。具体接口路径、字段和 OpenAPI 定义应在后端建设阶段另行形成接口契约。

前后端协作的核心目标是：

- 对同一个业务对象使用同一套稳定语义。
- 明确哪些是查询、哪些是命令、哪些是事件。
- 让 Mock 数据和真实接口可以通过适配层替换。
- 避免前端通过字符串、页面结构或本地状态补造业务事实。

## 2. 职责边界

### 前端负责

- 收集用户输入。
- 展示数据和状态。
- 执行基础格式校验。
- 展示权限结果。
- 发起查询和命令。
- 处理加载、错误和重试交互。

### 后端负责

- 身份认证和最终权限判定。
- 业务规则和风险校验。
- 订单、成交、账户、持仓和损益事实。
- 幂等、审计和数据持久化。
- 与外部交易系统和数据源通信。

前端校验用于改善用户体验，不替代后端校验。

## 3. 交互类型

### 3.1 Query

查询用于读取数据，不改变核心业务状态。

示例：

- 查询策略列表。
- 查询行情和历史数据。
- 查询账户、持仓、损益和订单。
- 查询风险状态和数据质量。

查询响应应包含：

- 数据主体。
- 数据时间。
- 服务处理时间。
- 数据来源或质量状态。
- 分页信息，适用时。

### 3.2 Command

命令用于请求改变业务状态。

示例：

- 提交交易。
- 撤单。
- 平仓。
- 配平。
- 启停策略实例。
- 确认对账差异。
- 修改风险规则。

命令请求应包含：

- `requestId`。
- `idempotencyKey`。
- 操作人上下文。
- 目标业务对象 ID。
- 命令参数。
- 客户端提交时间。

命令响应应区分：

- 已受理。
- 已拒绝。
- 参数错误。
- 权限不足。
- 结果未知。

“已受理”不等于“已成交”或“已完成”。

### 3.3 Event

事件用于通知已经发生的事实。

示例：

- 报价更新。
- 订单状态变化。
- 新增成交。
- 执行批次异常。
- 风险状态变化。
- 数据源中断。

事件应包含：

- `eventId`。
- `eventType`。
- `occurredAt`。
- `entityType`。
- `entityId`。
- `version` 或序列号。
- 事件数据。

前端应能够处理重复、延迟和乱序事件。

## 4. 通信方式

### REST／HTTP

适用于：

- 页面初始化。
- 条件查询。
- 命令提交。
- 历史数据和报表。
- 文件导入导出。

### WebSocket／SSE

适用于：

- 行情更新。
- 订单、成交和执行批次状态。
- 账户、保证金和风险状态。
- 系统和数据质量告警。

实时连接断开后，前端应通过重新查询恢复权威状态，不只依赖补收事件。

## 5. 统一响应结构

建议查询响应使用：

```ts
interface ApiResponse<T> {
  requestId: string;
  success: boolean;
  data?: T;
  error?: ApiError;
  serverTime: string;
}
```

分页响应使用：

```ts
interface PageResult<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  nextCursor?: string;
}
```

不要求所有后端内部服务使用相同传输结构，但面向前端的 Platform API 应保持一致。

## 6. 错误处理

错误应同时提供：

- 稳定错误码。
- 用户可理解的中文信息。
- 可选技术详情或追踪 ID。
- 是否允许重试。
- 受影响业务对象。

错误类型至少区分：

- `VALIDATION_ERROR`
- `AUTHENTICATION_REQUIRED`
- `PERMISSION_DENIED`
- `RESOURCE_NOT_FOUND`
- `CONFLICT`
- `RATE_LIMITED`
- `UPSTREAM_UNAVAILABLE`
- `STALE_DATA`
- `RISK_REJECTED`
- `COMMAND_RESULT_UNKNOWN`
- `INTERNAL_ERROR`

前端不得通过解析自然语言错误文本判断业务类型。

## 7. 权限协作

后端返回：

- 当前用户身份。
- 角色。
- 能力权限。
- 数据范围。
- 适用限制。

前端据此：

- 隐藏或禁用操作。
- 显示权限原因。
- 避免发起明显无权限请求。

后端仍必须对每个命令执行最终权限检查。

## 8. 时间规范

- 接口传输时间优先使用 ISO 8601。
- 后端保存 UTC 或明确时区的时间。
- 前端按用户时区展示。
- 业务日期与自然时间分开。
- 行情时间、接收时间、计算时间和更新时间不得混为同一字段。

建议字段：

```text
businessDate
occurredAt
receivedAt
calculatedAt
updatedAt
```

## 9. 金额、数量和币种

金额和数量不得仅返回格式化字符串。

建议结构：

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

- 高精度数字使用字符串传输，避免浮点误差。
- 金额必须带币种。
- 合约数量应带单位、乘数或标的定义引用。
- 汇率应包含币种对、来源和时间。
- 前端负责格式化，不改变原始数值。

## 10. 状态枚举

状态必须使用稳定枚举，显示文案由前端映射。

至少区分：

- QuoteStatus。
- OrderStatus。
- ExecutionBatchStatus。
- BalanceStatus。
- RiskStatus。
- ReconciliationStatus。
- DataQualityStatus。

不得让不同接口分别使用 `success`、`done`、`filled` 表达不同业务状态。

## 11. 版本和兼容性

- 接口发生不兼容变化时必须有版本策略。
- 新增可选字段通常不视为不兼容。
- 删除字段、修改枚举语义和改变单位属于不兼容变化。
- 前端适配层负责兼容具体接口版本，页面组件不直接判断多个版本。
- WebSocket 事件应包含事件版本。

## 12. Mock 与真实接口迁移

Mock 与 API 必须实现相同的 Repository 接口。

```text
Page
  ↓
Repository
  ├─ MockAdapter
  └─ ApiAdapter
```

要求：

- Mock 数据使用正式策略 ID 和状态枚举。
- Mock 时间、币种和单位结构与真实接口目标一致。
- 页面不得通过 `isMock` 分支维护两套业务逻辑。
- 模拟交易结果必须明确标记为模拟环境。

## 13. 交易命令协作

以双腿交易为例：

```text
前端准备交易参数
  ↓
POST TradeCommand
  ↓
后端权限、风险和幂等检查
  ↓
返回 ExecutionBatch ID 和受理状态
  ↓
后端执行两条交易腿
  ↓
WebSocket 推送订单、成交、配平和暴露变化
  ↓
前端按 ExecutionBatch 聚合展示
  ↓
前端断线后通过查询接口恢复批次状态
```

前端不得将两次独立订单请求自行拼接成一个可靠双腿交易批次。

## 14. 验收标准

- 相同业务对象在查询、命令和事件中使用相同 ID。
- 前端可以从 Mock Adapter 切换到 API Adapter，而不重写页面结构。
- 错误码、状态、币种、时间和分页规则统一。
- 命令具备幂等标识和审计上下文。
- 实时连接断开后可以重新获取权威状态。
- 页面不通过自然语言字符串推断核心业务状态。
