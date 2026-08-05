# Platform 0.10.x API 契约与版本管理规范

状态：`active`  
适用分支：`refactor/frontend-architecture-v6`  
架构层级：前后端协作架构

## 1. 文档定位

本文档定义面向前端的 Platform API 契约、资源命名、查询、命令、错误、幂等和版本兼容规则。

具体接口清单和字段应在后端建设阶段通过 OpenAPI 或同等机器可读契约维护。

## 2. API 边界

前端优先访问 Platform API／BFF，不直接依赖多个后端内部服务和外部交易系统。

Platform API 负责：

- 鉴权上下文。
- 面向页面的查询聚合。
- DTO 版本和兼容。
- 命令入口。
- 错误和追踪 ID。

Platform API 不负责重新实现各领域业务规则。

## 3. URL 与资源命名

建议采用：

```text
/api/v1/strategies
/api/v1/strategy-instances
/api/v1/accounts
/api/v1/positions
/api/v1/orders
/api/v1/fills
/api/v1/deals
/api/v1/executions
/api/v1/execution-batches
/api/v1/pnl-results
/api/v1/strategy-nav-snapshots
/api/v1/risk-snapshots
/api/v1/reconciliations
```

规则：

- 资源名称使用稳定英文复数。
- URL 不使用页面组件名称。
- 不将 Vue 路由直接复制为后端接口结构。
- 稳定业务 ID 放在资源路径或查询参数中。
- 动作型命令使用明确命令端点，不伪装成普通字段更新。

示例：

```text
POST /api/v1/trade-commands
POST /api/v1/orders/{orderId}/cancel-commands
POST /api/v1/execution-batches/{id}/rebalance-commands
```

## 4. 查询请求

查询参数至少遵循：

- `strategyId`
- `strategyInstanceId`
- `accountId`
- `instrumentId`
- `from`
- `to`
- `status`
- `page`
- `pageSize`
- `cursor`
- `sort`

规则：

- 时间使用 ISO 8601。
- 多值参数使用重复参数或明确数组格式。
- 不使用自然语言作为状态查询条件。
- 无筛选条件时使用安全、可预测默认值。
- 大数据量查询使用游标或稳定分页。

## 5. 查询响应

推荐：

```ts
interface ApiResponse<T> {
  requestId: string;
  success: boolean;
  data?: T;
  error?: ApiError;
  serverTime: string;
}
```

重要查询可附加：

- `dataTime`
- `source`
- `qualityStatus`
- `isEstimated`
- `version`

分页响应：

```ts
interface PageResult<T> {
  items: T[];
  page?: number;
  pageSize: number;
  total?: number;
  nextCursor?: string;
}
```

## 6. 命令请求

正式命令至少包含：

```ts
interface CommandRequest<T> {
  requestId: string;
  idempotencyKey: string;
  clientTime: string;
  payload: T;
}
```

操作人、角色、能力和环境由受信任会话上下文确定，不接受前端任意伪造。

交易命令 payload 必须显式包含目标 `strategyInstanceId`、`accountId`、`tradingMode`、目标标的和操作意图。V1 中，`paper` 可对应交易所测试网、模拟盘或 MT5 Demo；`live` 只能由服务端根据账户白名单、GatewayCapability、TradingPermissionState、风控和审批共同决定，前端不能通过字段切换成实盘。

## 7. 命令响应

建议：

```ts
interface CommandResponse {
  requestId: string;
  commandId: string;
  status: 'accepted' | 'rejected' | 'result_unknown';
  entityType?: string;
  entityId?: string;
  error?: ApiError;
  serverTime: string;
}
```

规则：

- `accepted` 只表示后端受理命令。
- 下单命令通常返回 `tradeCommandId` 或 `executionBatchId`。
- 最终订单和成交状态通过查询或实时事件获得。
- `result_unknown` 不允许前端直接重复提交。
- 交易命令返回成功受理后，前端必须通过查询或实时事件读取 TradeCommand、ExecutionBatch、Order、Fill、Deal 和 Reconciliation 状态，不能把命令响应当作成交结果。

## 8. HTTP 状态码

建议：

- `200`：成功查询或同步命令完成。
- `201`：资源或命令已创建。
- `202`：异步命令已受理。
- `400`：请求格式或参数错误。
- `401`：未认证。
- `403`：无权限。
- `404`：资源不存在。
- `409`：版本冲突、幂等冲突或状态冲突。
- `422`：业务校验或风险拒绝。
- `429`：限频。
- `503`：上游或关键服务不可用。

HTTP 状态码与业务错误码同时使用。

## 9. 错误结构

```ts
interface ApiError {
  code: string;
  message: string;
  retryable: boolean;
  traceId?: string;
  fieldErrors?: Array<{
    field: string;
    code: string;
    message: string;
  }>;
  entityType?: string;
  entityId?: string;
  details?: Record<string, unknown>;
}
```

稳定错误码不得随中文文案变化。

## 10. 幂等规则

- 所有改变核心状态的命令支持幂等。
- 幂等作用域至少包含用户、环境、命令类型和业务目标。
- 相同幂等键但不同 payload 应返回冲突。
- 服务器保存幂等结果和有效期。
- API 文档明确哪些命令可以安全重试。

## 11. 并发和版本

对可编辑配置建议使用：

- `version`
- `updatedAt`
- `If-Match`／ETag，适用时。

版本不一致返回 `409 CONFLICT`，避免旧页面覆盖新配置。

## 12. 批量接口

批量操作必须明确：

- 是全部成功或全部失败。
- 还是逐项返回结果。
- 每项是否独立幂等。
- 最大批量数量。
- 部分失败如何重试。

交易类批量命令不得用一个模糊成功状态隐藏部分失败。

V1 不建议开放跨账户、跨策略的大批量交易命令。资费套利和跨所价差如需多腿执行，应通过 ExecutionBatch 表达，不通过前端批量下单接口拼装。

## 13. 文件导入导出

导入流程建议：

1. 上传文件。
2. 创建导入任务。
3. 校验格式和业务数据。
4. 返回预览和差异。
5. 用户确认。
6. 正式写入并审计。

导出文件应包含：

- 生成时间。
- 数据截止时间。
- 筛选条件。
- 计价币种和时区。
- 报表或导出版本。

## 14. API 版本

### 主版本

破坏性变化使用新主版本，例如 `/api/v2`。

### 兼容变化

可以在当前版本增加：

- 可选字段。
- 新枚举值，前端必须支持未知值降级。
- 新查询参数。
- 新端点。

### 破坏性变化

包括：

- 删除字段。
- 改变字段含义。
- 改变金额单位或时间语义。
- 改变状态枚举含义。
- 修改 ID 类型。

## 15. 弃用策略

接口弃用应提供：

- 弃用日期。
- 替代接口。
- 预计下线日期。
- 影响范围。
- 迁移说明。

前端在下线前完成迁移，不长期同时维护多套分支逻辑。

## 16. OpenAPI 与契约测试

后端建设阶段必须：

- 使用 OpenAPI 或等效工具维护接口契约。
- 由契约生成或校验前端 DTO 类型，适用时。
- 对关键查询和命令建立契约测试。
- Mock 数据遵循同一契约。
- CI 检查破坏性接口变化。

生成类型不能直接替代 Domain Model 和 View Model。

## 17. 安全

- 不在 URL query 传递密钥和敏感凭证。
- 不通过 Platform API 明文传递交易所 API Key、Secret、Passphrase、MT5 登录密码或服务器地址；这些信息进入独立 Secret/Credential 边界。
- 写操作执行 CSRF、令牌或会话安全控制。
- 导出接口检查数据范围权限。
- 高风险命令支持二次认证或短期操作授权。
- 错误响应不泄露密钥、内部堆栈和敏感配置。

客户/投资者侧 API 权限待用户系统完成后再设计。当前 V1 只要求内部接口的数据范围、交易模式和实盘门禁清晰，不提前设计客户侧细粒度授权。

## 18. 验收标准

- API 以业务资源和命令组织，不以页面组件组织。
- 查询、命令和事件语义分开。
- 命令具备幂等和结构化结果。
- 交易查询能区分 Order、Fill、MT5 Deal、Position、Balance、PnL 和 StrategyNavSnapshot。
- 错误码稳定且不依赖文本解析。
- 金额、时间、分页和状态约定统一。
- 契约可通过机器可读文件和测试验证。
- 版本变化具有兼容和弃用策略。
- API 不允许前端绕过服务端门禁切换 Live 交易。
