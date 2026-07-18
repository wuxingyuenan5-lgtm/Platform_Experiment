# Platform V6+ 状态枚举与生命周期规范

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：公共领域模型状态唯一来源

配套文档：

- `domain-overview.md`
- `unified-domain-model.md`
- `value-currency-unit-and-time-contract.md`
- `../integration/runtime-command-event-contract.md`
- `../backend/trading-execution-reliability.md`
- `../backend/execution-runtime-and-gateway.md`

## 1. 文档定位

本文是前端、Platform Backend、Execution Runtime、API、事件、数据库和报表共同使用的核心状态枚举与生命周期唯一来源。

状态码表达稳定业务语义；中文文案、颜色、图标和操作建议属于 View Model 与 UI 层。

其他文档可以定义原因码和场景示例，但不得维护冲突的完整状态清单。

## 2. 通用规则

- 状态码使用稳定英文小写下划线。
- 不同业务维度使用不同状态字段。
- 不通过自然语言、颜色或数值正负推断状态。
- 外部状态映射为平台状态，并保留原始值。
- 未识别状态降级为 `unknown` 或 Unknown Variant，不自动开放操作。
- 状态变化记录旧值、新值、时间、来源、原因码和关联对象。
- `unknown`／`result_unknown`／`status_unknown` 通常不是终态。
- 终态必须由具体生命周期定义，不能由前端猜测。
- 连接状态、同步状态、就绪状态和交易能力不得合并为一个 `connected`。

## 3. QuoteStatus

| 状态码 | 含义 |
|---|---|
| `fresh` | 报价处于允许的新鲜度范围 |
| `delayed` | 延迟但仍可只读观察 |
| `stale` | 已过期，不允许依赖其新增交易风险 |
| `unavailable` | 无可用报价 |
| `conflicted` | 多来源存在冲突 |
| `unknown` | 无法确认 |

## 4. DataQualityStatus

| 状态码 | 含义 |
|---|---|
| `complete` | 完整且通过必要验证 |
| `partial` | 部分数据可用 |
| `delayed` | 更新延迟 |
| `missing` | 必要数据缺失 |
| `duplicated` | 存在重复记录 |
| `conflicted` | 来源或结果冲突 |
| `unverified` | 尚未核对 |
| `invalid` | 格式或业务规则无效 |
| `unavailable` | 来源当前不可用 |

数据质量状态不替代对象业务状态。

## 5. MasterDataStatus

适用于 LegalEntity、Fund、Portfolio、Book、Account、Instrument、StrategyDefinition 等主数据。

| 状态码 | 含义 |
|---|---|
| `draft` | 尚未正式生效 |
| `active` | 当前有效 |
| `suspended` | 暂停使用，但历史关系保留 |
| `inactive` | 当前不使用 |
| `expired` | 已超过有效期 |
| `archived` | 已归档 |

## 6. StrategyVersionStatus

| 状态码 | 含义 |
|---|---|
| `draft` | 编辑中 |
| `review` | 等待审核 |
| `approved` | 已批准但未必已生效 |
| `active` | 当前可用于新实例或新交易 |
| `superseded` | 已被新版本替代 |
| `retired` | 不再允许新使用 |
| `rejected` | 审核未通过 |

历史交易始终关联交易发生时的版本。

## 7. StrategyInstanceStatus

| 状态码 | 含义 |
|---|---|
| `draft` | 尚未完成配置 |
| `ready` | 配置完成，可等待运行 |
| `starting` | 正在启动 |
| `running` | 正在运行或接受授权操作 |
| `paused` | 暂停新增动作 |
| `stopping` | 正在停止 |
| `stopped` | 已停止 |
| `degraded` | 部分能力异常，仅允许受限操作 |
| `blocked` | 被风险、权限或系统状态阻断 |
| `error` | 已确认运行异常 |
| `archived` | 已归档 |

StrategyInstanceStatus 不等于 RuntimeStatus，也不等于交易许可。

## 8. TradeCommandStatus

TradeCommand 只表达平台业务命令的接收和受理。

| 状态码 | 含义 |
|---|---|
| `received` | 已收到请求 |
| `validating` | 正在进行权限、参数、模式、审批和风险校验 |
| `rejected` | 未通过校验，不会执行目标动作 |
| `accepted` | 已受理，并创建或准备创建目标对象 |
| `result_unknown` | 无法确认是否有效受理或创建目标对象 |
| `cancelled` | 在受理前取消 |

典型路径：

```text
received → validating → accepted
received → validating → rejected
received → validating → result_unknown
received → cancelled
```

`accepted` 不等于 Runtime 已接收、外部订单已提交或交易完成。

## 9. RuntimeCommandStatus

表示 Platform 发往 Runtime 的单条命令生命周期。

| 状态码 | 含义 |
|---|---|
| `outbox_pending` | 已写入 Platform Outbox，等待发送 |
| `published` | 已发送到传输通道 |
| `received` | Runtime 已持久化接收 |
| `accepted` | Runtime 已通过契约和能力检查 |
| `rejected` | Runtime 明确拒绝 |
| `executing` | Worker 正在处理 |
| `completed` | Runtime 层命令处理已完成 |
| `result_unknown` | 外部执行结果无法确认 |
| `expired` | 超过 expiresAt，未执行 |
| `cancelled` | 执行前被有效取消，适用时 |

`published` 不等于 `received`；`completed` 不等于 ExecutionBatch completed。

## 10. ExecutionBatchStatus

| 状态码 | 含义 |
|---|---|
| `created` | 已创建执行批次 |
| `prechecking` | 正在执行批次检查 |
| `ready` | 可以开始执行 |
| `submitting` | 正在提交交易腿 |
| `working` | 外部订单处于活动状态 |
| `partially_filled` | 部分订单或交易腿已成交 |
| `balancing` | 正在补齐或配平 |
| `completed` | 已满足批次结束条件 |
| `cancel_requested` | 已请求取消未完成部分 |
| `cancelled` | 已取消且不再继续 |
| `exception` | 出现已确认异常 |
| `manual_intervention` | 等待或正在人工处理 |
| `result_unknown` | 批次结果暂时无法确认 |
| `terminated` | 已终止且不再继续 |

ExecutionBatchStatus、ExecutionBalanceStatus、ExposureStatus、OrderStatus 和 RiskStatus 分开。

## 11. ExecutionPlanStatus

| 状态码 | 含义 |
|---|---|
| `draft` | 计划尚未冻结 |
| `validated` | 已通过结构和能力检查 |
| `approved` | 已满足审批要求 |
| `active` | 当前批次正在使用 |
| `completed` | 计划执行结束 |
| `cancelled` | 已取消 |
| `superseded` | 被新计划版本替代 |
| `invalid` | 当前不可执行 |

## 12. LegInstructionStatus

| 状态码 | 含义 |
|---|---|
| `pending` | 等待执行 |
| `ready` | 当前可以提交 |
| `submitting` | 正在创建或提交订单 |
| `working` | 对应订单仍在工作 |
| `partially_filled` | 部分完成 |
| `completed` | 达到该腿目标 |
| `cancelled` | 已取消 |
| `exception` | 出现异常 |
| `result_unknown` | 结果无法确认 |

## 13. OrderStatus

| 状态码 | 含义 |
|---|---|
| `pending_submit` | 平台订单已预创建，等待提交 |
| `submit_pending` | Runtime 正在处理提交 |
| `submitted` | 已向外部系统发出请求 |
| `acknowledged` | 外部系统已确认订单 |
| `working` | 订单当前有效并等待成交 |
| `partially_filled` | 部分成交 |
| `filled` | 全部成交 |
| `cancel_pending` | 正在撤销 |
| `cancelled` | 已撤销 |
| `rejected` | 被平台、Runtime 或外部系统明确拒绝 |
| `expired` | 已过期 |
| `failed` | 已确认失败且不存在有效外部订单 |
| `status_unknown` | 外部订单状态无法确认 |
| `unallocated` | 已发现外部订单但无法归属平台对象 |
| `unverified` | 归属或状态证据不足 |

通常终态：

- `filled`
- `cancelled`
- `rejected`
- `expired`
- `failed`

`status_unknown`、`unallocated` 和 `unverified` 需要恢复或人工处理。

## 14. FillStatus

Fill 原则上是不可变事实，但修正和冲销需要显式状态。

| 状态码 | 含义 |
|---|---|
| `received` | 已摄取 |
| `verified` | 已完成必要核对 |
| `unverified` | 尚未核对 |
| `corrected` | 已通过修正记录替代或调整 |
| `reversed` | 已被外部或平台确认冲销 |
| `unallocated` | 无法归属 Order／Strategy |

## 15. ExecutionBalanceStatus

| 状态码 | 含义 |
|---|---|
| `not_calculated` | 尚未计算 |
| `unbalanced` | 未达到目标关系 |
| `partially_balanced` | 部分达到目标关系 |
| `balanced` | 达到目标关系 |
| `outside_tolerance` | 偏差超出容忍范围 |
| `manual_override` | 经授权接受当前偏差 |
| `unknown` | 无法可靠计算 |

## 16. ExposureStatus

| 状态码 | 含义 |
|---|---|
| `none` | 无已识别异常暴露 |
| `primary_leg_exposed` | 主腿未对冲 |
| `hedge_leg_exposed` | 对冲腿未对冲 |
| `fx_exposed` | 存在汇率暴露 |
| `multi_leg_mismatch` | 多腿名义或风险不匹配 |
| `outside_limit` | 暴露超出限制 |
| `unknown` | 无法确认 |

## 17. PositionQualityStatus

Position 自身不使用简单“正常／异常”代替来源质量。

| 状态码 | 含义 |
|---|---|
| `derived` | 由平台 Fill 推导 |
| `external_snapshot` | 来自外部账户快照 |
| `reconciled` | 已完成平台与外部核对 |
| `difference_found` | 存在差异 |
| `unverified` | 尚未核对 |
| `unknown` | 来源或状态未知 |

## 18. ReconciliationStatus

| 状态码 | 含义 |
|---|---|
| `pending` | 等待核对 |
| `running` | 正在核对 |
| `matched` | 一致 |
| `difference_found` | 发现差异 |
| `manual_review` | 等待人工复核 |
| `resolving` | 正在处理差异 |
| `resolved` | 差异已处理 |
| `accepted_difference` | 经授权接受差异 |
| `failed` | 核对任务失败 |

## 19. RiskStatus

| 状态码 | 含义 |
|---|---|
| `normal` | 正常 |
| `watch` | 观察 |
| `warning` | 警告 |
| `restricted` | 部分操作受限 |
| `blocked` | 禁止相关操作 |
| `manual_review` | 需要人工确认 |
| `insufficient_data` | 数据不足 |
| `unknown` | 状态未知 |

## 20. ApprovalStatus

| 状态码 | 含义 |
|---|---|
| `draft` | 尚未提交 |
| `pending` | 等待审批 |
| `approved` | 已批准 |
| `rejected` | 已拒绝 |
| `cancelled` | 已取消 |
| `expired` | 已过期 |
| `consumed` | 授权已被目标命令使用 |
| `revoked` | 已撤销 |

审批状态不替代目标对象状态。

## 21. DeploymentEnvironment

| 状态码 | 含义 |
|---|---|
| `development` | 开发环境 |
| `testing` | 集成与自动化测试环境 |
| `staging` | 预发布环境 |
| `production` | 生产环境 |

DeploymentEnvironment 不表示是否产生真实订单。

## 22. TradingMode

| 状态码 | 含义 |
|---|---|
| `demo` | 前端演示或静态 Mock |
| `simulation` | 平台模拟执行 |
| `paper` | 外部模拟账户或测试交易通道 |
| `live` | 真实资金和真实订单 |

## 23. TradingPermissionState

| 状态码 | 含义 |
|---|---|
| `disabled` | 功能或模式未启用 |
| `read_only` | 仅允许查询 |
| `enabled` | 允许授权范围内的交易命令 |
| `restricted` | 仅允许减仓、撤单或指定动作 |
| `blocked` | 禁止交易状态变更 |
| `unknown` | 无法可靠判断，默认不得新增风险 |

由服务端综合权限、环境、模式、审批、风险、账户、行情和 Runtime 状态形成。

## 24. RuntimeStatus

| 状态码 | 含义 |
|---|---|
| `starting` | 进程正在启动 |
| `connecting` | 正在连接基础依赖和 Gateway |
| `synchronizing` | 正在同步外部状态 |
| `reconciling` | 正在核对平台与外部事实 |
| `recovering` | 正在恢复未完成命令和事件 |
| `risk_confirming` | 等待平台风险确认 |
| `ready` | 已满足当前能力的运行条件 |
| `degraded` | 部分能力异常 |
| `read_only` | 只允许查询和同步 |
| `blocked` | 被阻断 |
| `stopping` | 正在停止 |
| `stopped` | 已停止 |
| `failed` | 已确认失败 |

Runtime `ready` 不表示所有 Gateway 都可 Live 交易。

## 25. WorkerStatus

| 状态码 | 含义 |
|---|---|
| `starting` | 正在启动 |
| `idle` | 已运行，当前无任务 |
| `working` | 正在处理任务 |
| `degraded` | 部分能力异常 |
| `blocked` | 不允许处理新命令 |
| `restarting` | 正在重启 |
| `stopping` | 正在停止 |
| `stopped` | 已停止 |
| `crashed` | 非正常退出 |
| `failed` | 无法自动恢复 |

## 26. GatewayConnectivityStatus

只表达网络或 Session 连通性。

| 状态码 | 含义 |
|---|---|
| `disconnected` | 未连接 |
| `connecting` | 正在连接 |
| `connected` | Session 已连接 |
| `reconnecting` | 正在重连 |
| `maintenance` | 上游维护 |
| `rate_limited` | 上游限频 |
| `failed` | 连接失败 |
| `unknown` | 无法确认 |

## 27. GatewayAuthenticationStatus

| 状态码 | 含义 |
|---|---|
| `not_required` | 不需要认证 |
| `pending` | 等待认证 |
| `authenticated` | 认证成功 |
| `unauthorized` | 凭证或权限失败 |
| `expired` | 会话或凭证过期 |
| `unknown` | 无法确认 |

## 28. GatewaySynchronizationStatus

| 状态码 | 含义 |
|---|---|
| `not_started` | 尚未同步 |
| `syncing` | 正在同步 |
| `in_sync` | 当前已同步 |
| `partial` | 部分数据同步完成 |
| `stale` | 同步结果已过期 |
| `difference_found` | 与平台事实存在差异 |
| `failed` | 同步失败 |
| `unknown` | 无法确认 |

## 29. GatewayReadinessStatus

综合表达 Gateway 是否可以接受当前类别命令。

| 状态码 | 含义 |
|---|---|
| `not_ready` | 尚未满足条件 |
| `recovering` | 正在恢复 |
| `ready` | 对声明能力已就绪 |
| `degraded` | 部分能力可用 |
| `read_only` | 只读 |
| `blocked` | 被平台或运行状态阻断 |
| `unknown` | 无法可靠判断 |

## 30. TradingCapabilityStatus

| 状态码 | 含义 |
|---|---|
| `unsupported` | Gateway 或账户不支持交易 |
| `disabled` | 配置未启用 |
| `read_only` | 只允许查询 |
| `paper_enabled` | 允许 Paper 交易 |
| `live_enabled` | 允许 Live 交易 |
| `restricted` | 仅允许指定动作，例如撤单或减仓 |
| `blocked` | 禁止交易 |
| `unknown` | 无法确认，默认禁止新增风险 |

`connected`、`authenticated`、`in_sync` 和 `live_enabled` 是不同维度。

## 31. MarketDataCapabilityStatus

| 状态码 | 含义 |
|---|---|
| `unsupported` | 不支持行情 |
| `disabled` | 未启用 |
| `snapshot_only` | 只支持快照 |
| `streaming` | 支持实时流 |
| `delayed` | 仅延迟行情 |
| `degraded` | 部分行情能力异常 |
| `unavailable` | 当前不可用 |

## 32. RecoveryStatus

| 状态码 | 含义 |
|---|---|
| `not_required` | 无需恢复 |
| `pending` | 等待恢复 |
| `running` | 正在恢复 |
| `querying_external` | 正在查询外部事实 |
| `reconciling` | 正在核对 |
| `manual_review` | 需要人工确认 |
| `completed` | 恢复完成 |
| `completed_with_differences` | 恢复完成但保留已知差异 |
| `failed` | 恢复失败 |

## 33. PnLResultStatus

| 状态码 | 含义 |
|---|---|
| `calculating` | 正在计算 |
| `estimated` | 使用估算或未完整核对数据 |
| `provisional` | 初步结果，可继续修订 |
| `verified` | 已完成必要核对 |
| `final` | 对当前报告版本已锁定 |
| `superseded` | 被新计算版本替代 |
| `failed` | 计算失败 |
| `insufficient_data` | 数据不足 |

`final` 仅对特定 PnLResult／ReportVersion 有效，不代表正式 Fund NAV。

## 34. ImportStatus

| 状态码 | 含义 |
|---|---|
| `uploaded` | 文件已上传 |
| `validating` | 正在校验 |
| `preview_ready` | 可供确认 |
| `rejected` | 校验未通过 |
| `confirmed` | 已确认导入 |
| `processing` | 正在处理 |
| `completed` | 已完成 |
| `completed_with_errors` | 部分完成 |
| `failed` | 失败 |
| `cancelled` | 已取消 |

## 35. 状态变化记录

至少记录：

- entityType 和 entityId。
- oldStatus 和 newStatus。
- occurredAt。
- recordedAt。
- source。
- reasonCode。
- correlationId／causationId。
- Command、Event、Approval 或 Recovery 引用。
- 操作人，适用时。
- version。

## 36. 前端展示映射

前端可以映射中文文案、颜色、图标、操作建议和按钮状态，但不得改变语义。

禁止：

- 将 `result_unknown` 展示为“失败”。
- 将 `accepted` 展示为“交易成功”。
- 将 `connected` 展示为“实盘可交易”。
- 将 `production` 展示为“Live 已启用”。
- 将 `estimated` PnL 展示为正式锁定结果。

## 37. 新增和兼容规则

新增状态前必须确认：

1. 是否为新业务语义，而非新文案。
2. 是否可由现有状态加 reasonCode 表达。
3. 是否改变生命周期和终态。
4. 前端、Backend、Runtime、API、Event 和报表是否兼容。
5. 是否需要 payloadVersion、接口主版本或 ADR。
6. 是否已更新本唯一来源。

消费者遇到未知枚举值：

- 保留原值。
- 降级显示。
- 默认不得扩大交易风险。
- 记录兼容性指标和告警。

## 38. 验收标准

- 同一状态码跨系统语义一致。
- TradeCommand、RuntimeCommand、ExecutionBatch、LegInstruction 和 Order 生命周期分开。
- 配平、暴露、风险、数据质量和持仓来源状态分开。
- Runtime、Worker 和 Gateway 状态分开。
- Gateway 连通、认证、同步、就绪和交易能力分开。
- DeploymentEnvironment、TradingMode 和 TradingPermissionState 分开。
- 未知结果不被误判为失败。
- 状态变化可以追溯。
- 新枚举具有兼容和安全降级策略。
