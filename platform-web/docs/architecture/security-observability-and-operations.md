# Platform 0.10.x 安全、可观测性与运维架构

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：跨层技术架构

## 1. 文档定位

本文档定义贯穿前端、后端、接口、数据和交易执行的安全、日志、指标、追踪、告警、配置、发布和恢复原则。

金融平台不能只保证页面可打开，还必须回答：谁做了什么、系统发生了什么、当前是否允许交易、数据是否可靠、异常影响哪些账户，以及如何安全恢复。

## 2. 安全原则

- 最小权限和默认拒绝。
- 前端权限只改善体验，后端执行最终校验。
- DeploymentEnvironment、TradingMode 和 TradingPermissionState 分开。
- 开发、测试、预发布和生产配置隔离。
- Demo、Simulation、Paper 和 Live 交易模式明确标识。
- 敏感凭证不进入前端和普通日志。
- 高风险操作执行权限、审批和审计。
- 未知状态优先停止扩大风险。
- 数据导出和人工修正受权限控制。

## 3. 身份、会话和审批

至少具备：

- 安全登录和会话管理。
- 会话过期和主动退出。
- 用户禁用后及时失效会话。
- 角色、能力和数据范围分离。
- 高风险操作二次认证，适用时。
- Maker／Checker 审批，适用时。
- ApprovalGrant 与目标对象、参数、TradingMode 和有效期绑定。

前端不得保存长期有效交易凭证，也不得通过本地“已审批”状态绕过服务端验证。

## 4. DeploymentEnvironment 和 TradingMode

### DeploymentEnvironment

- `development`
- `testing`
- `staging`
- `production`

负责部署位置、配置、网络和数据隔离。

### TradingMode

- `demo`
- `simulation`
- `paper`
- `live`

负责表示是否产生演示、模拟或真实交易结果。

规则：

- `production` 不等于 `live`。
- `testing` 不等于 `paper`。
- Live 使用独立账户、凭证、额度、告警和运维流程。
- 页面和服务在运行上下文未知时不得开放正式交易。

详细决策参见 `decisions/ADR-007-部署环境与交易模式分离.md`。

## 5. 密钥与外部账户凭证

- 使用专用密钥管理或加密存储。
- 不写入 Git、前端构建产物和普通配置文件。
- 不通过日志、错误和审计详情输出完整凭证。
- 不同 DeploymentEnvironment 使用不同凭证。
- Paper 和 Live 原则上使用不同账户和密钥。
- 凭证按 Gateway 和 Account 最小化授权。
- 支持轮换、吊销和访问记录。

## 6. 网络与接口安全

- 敏感通信使用 TLS。
- API 执行认证、授权、限频和输入校验。
- WebSocket／SSE 执行会话和订阅权限检查。
- 防止重放、重复命令和伪造请求。
- 管理接口和普通查询接口使用不同能力权限。
- 内部服务访问使用独立服务身份。
- Command 验证 idempotencyKey、TradingMode 和 ApprovalGrant，适用时。

## 7. 数据安全

- 敏感账户字段按需展示和脱敏。
- 导出文件设置权限、有效期和访问日志。
- 数据库账号按模块和 DeploymentEnvironment 隔离。
- 备份数据加密和受控。
- 非生产环境不得默认复制完整 Live 敏感数据。
- 人工修正和删除使用权限、审批和审计。
- Research Data、Content 和交易数据按用途控制访问。

## 8. 日志分类

### 应用日志

记录应用运行、请求和异常。

### 交易日志

记录 TradeCommand、ExecutionBatch、Order、Fill、Gateway 通信和状态变化。

### 审计日志

记录用户、权限、审批、配置、风险覆盖、数据修正和人工处理。

### 安全日志

记录登录失败、权限拒绝、异常访问和凭证问题。

### 数据质量日志

记录延迟、缺失、重复、冲突、修订和对账差异。

不同日志可以共用基础设施，但语义、权限和保留周期分开。

## 9. 统一日志字段

建议包括：

- `timestamp`
- `level`
- `service`
- `deploymentEnvironment`
- `tradingMode`，适用时
- `requestId`
- `traceId`
- `correlationId`
- `causationId`
- `userId`，适用时
- `entityType`
- `entityId`
- `eventCode`
- `message`

交易和审计日志还应包含 StrategyInstance、Account、TradeCommand、ExecutionBatch、ApprovalRequest 和结果。

不得记录：

- 完整 API Key、Secret、密码和令牌。
- 不必要的个人敏感信息。
- 大量未经脱敏的请求体。
- 只有自然语言而没有结构化事件码的关键异常。

## 10. 指标体系

### 系统指标

- CPU、内存、磁盘和网络。
- 请求量、错误率和延迟。
- 数据库连接和慢查询。
- 队列和 Outbox 积压。

### 交易指标

- 命令受理和拒绝数量。
- ExecutionBatch 创建、完成和异常数量。
- Order 提交和确认延迟。
- Fill 到达延迟。
- 单腿暴露数量和持续时间。
- unknown 状态数量和持续时间。
- 人工处理和审批积压。

### 数据指标

- 行情延迟和数据源中断。
- Research Data 同步和修订失败。
- 缺失、重复和冲突记录。
- 对账差异数量。
- 损益重算和 Read Model 投影失败。

### 业务指标

- 活跃 StrategyInstance。
- 活跃 Account。
- 资金和风险占用。
- 风险限制触发。
- 报表和导出任务状态。

## 11. 分布式追踪

请求、命令和事件通过以下标识关联：

- `requestId`
- `traceId`
- `correlationId`
- `causationId`
- `tradeCommandId`
- `executionBatchId`
- `approvalRequestId`

从用户操作到权限、审批、风险、Gateway、外部回报和最终状态应可追踪。

## 12. 告警分级

建议：

- `info`：可观察。
- `warning`：需要关注，业务仍可运行。
- `critical`：影响交易、账户或关键数据。
- `emergency`：可能造成持续资金风险或平台级故障。

告警级别由明确规则决定，不直接等同于页面颜色。

## 13. 关键告警

至少包括：

- Live Gateway 断开。
- TradeCommand、ExecutionBatch 或 Order 结果未知。
- 单腿暴露超时。
- 风险或权限服务不可用。
- Approval 服务在高风险操作期间不可用。
- Account、Position 或策略经济账本对账差异。
- 行情严重延迟或冲突。
- 数据库写入、Outbox 或 Read Model 投影失败。
- 审计记录失败。
- 备份失败。
- 权限和 TradingMode 异常变更。

## 14. 健康检查

服务区分：

- 进程是否存活。
- 是否可以接收查询。
- 是否可以访问关键依赖。
- 是否可以接受 Command。
- 是否可以执行 Live 交易。
- 数据是否新鲜。
- 审计、风险、审批和 Gateway 是否可用。

普通页面可用不代表交易能力可用。

## 15. 配置管理

配置分类：

- 应用配置。
- DeploymentEnvironment 配置。
- TradingMode 和交易业务配置。
- 风险和额度配置。
- 审批策略。
- 密钥和凭证。
- 动态配置。

规则：

- 配置有明确来源、版本和生效时间。
- Live 配置变更执行权限、审批和审计。
- 密钥与普通配置分开。
- 页面不得通过本地常量决定 Live 能力。
- 重要配置支持回滚和失效处理。

## 16. 发布策略

后续应具备：

- 独立 development、testing、staging 和 production。
- 可重复构建。
- 数据库迁移版本化。
- 发布前自动检查。
- 交易能力按 TradingMode 受控启用。
- 发布后健康检查和回滚条件。

前端和后端可以独立发布，但接口和状态契约必须兼容。

## 17. 故障处理

流程：

1. 识别和分级。
2. 判断是否阻断新增风险。
3. 保护现有 Order、Position 和账户。
4. 恢复服务和外部连接。
5. 重新查询权威状态。
6. 执行对账。
7. 处理遗留异常、审批和人工任务。
8. 记录原因和改进措施。

故障恢复不能仅以页面重新打开作为完成标准。

## 18. 备份与灾难恢复

必须定义：

- RPO 和 RTO。
- 数据库和对象存储备份。
- 密钥和配置恢复。
- 异地或跨区域需求。
- 定期恢复演练。
- 恢复后 Order、Fill、Position、Account、策略经济账本、审批和审计对账。

## 19. 运维权限

运维人员不默认拥有全部交易和资金权限。

应分离：

- 系统运维。
- 用户和权限管理。
- 风险规则管理。
- 审批管理。
- 交易操作。
- 数据修正。
- 审计查看。

高风险操作遵循最小权限和完整记录。

## 20. 唯一来源

- 状态和运行上下文：`domain/status-enums-and-lifecycles.md`。
- 审批：`domain/approval-and-dual-control.md`。
- 交易可靠性：`backend/trading-execution-reliability.md`。
- 数据和账本：`backend/storage-ledger-and-audit.md`。
- 实时恢复：`integration/realtime-events-and-recovery.md`。

## 21. 验收标准

- 安全、日志、指标、追踪和告警覆盖关键交易链路。
- DeploymentEnvironment 和 TradingMode 分开管理。
- Paper 和 Live 的账户、凭证、额度和告警边界清晰。
- 关键日志不泄露敏感信息。
- 用户操作可关联权限、审批、命令、执行批次和外部回报。
- 关键故障具有告警、阻断、恢复和对账流程。
- 配置、发布和回滚具有版本和审计。
- 备份恢复在实施阶段定期演练。
