# Platform V6 状态枚举与生命周期规范

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：公共领域模型

## 1. 文档定位

本文档是前端、后端、接口、事件和报表共同使用的核心状态枚举唯一来源。

状态码表达稳定业务语义；中文文案、颜色、图标和操作建议属于 View Model 与 UI 层，不属于状态本身。

## 2. 通用规则

- 状态码使用稳定英文小写下划线格式。
- 不同业务维度使用不同状态字段。
- 不通过自然语言、颜色或数值正负号推断状态。
- 状态变化记录时间、来源、原因码和关联对象。
- 外部状态先映射为平台状态，并保留外部原始值。
- 未识别的新状态降级显示为未知状态，不得导致白屏或自动开放操作。
- 其他文档只引用本文件，不重复维护完整状态清单。

## 3. QuoteStatus

| 状态码 | 含义 |
|---|---|
| `fresh` | 报价处于允许的新鲜度范围 |
| `delayed` | 报价延迟，但仍可用于只读观察 |
| `stale` | 报价过期，不允许依赖其执行交易 |
| `unavailable` | 当前没有可用报价 |
| `conflicted` | 多来源报价存在冲突 |
| `unknown` | 当前状态无法确认 |

QuoteStatus 与价格涨跌方向无关。

## 4. DataQualityStatus

| 状态码 | 含义 |
|---|---|
| `complete` | 数据完整且已验证 |
| `partial` | 仅部分数据可用 |
| `delayed` | 数据更新延迟 |
| `missing` | 必要数据缺失 |
| `duplicated` | 存在重复记录 |
| `conflicted` | 多来源或计算结果冲突 |
| `unverified` | 尚未完成核对 |
| `invalid` | 数据格式或业务规则无效 |

数据质量状态不能替代业务对象状态。

## 5. StrategyInstanceStatus

| 状态码 | 含义 |
|---|---|
| `draft` | 尚未启用的实例 |
| `ready` | 配置完成，可等待运行 |
| `running` | 正在运行 |
| `paused` | 暂停，不接受新增动作 |
| `stopping` | 正在停止 |
| `stopped` | 已停止 |
| `degraded` | 部分能力异常但仍可观察 |
| `blocked` | 被风险、权限或系统状态阻断 |
| `error` | 运行异常 |
| `archived` | 已归档 |

策略实例状态不等于策略定义是否在前端注册表中展示。

## 6. TradeCommandStatus

TradeCommand 只表达命令是否被有效接收和受理，不重复表达订单和执行批次的完整过程。

| 状态码 | 含义 |
|---|---|
| `received` | 服务端已收到命令请求 |
| `validating` | 正在执行权限、参数、环境和风险校验 |
| `rejected` | 命令未通过校验，不会创建执行批次 |
| `accepted` | 命令已受理，并已创建或准备创建目标业务对象 |
| `result_unknown` | 无法确认命令是否已被有效受理或创建目标对象 |
| `cancelled` | 命令在受理前被取消 |

规则：

- `accepted` 不等于订单已提交、成交或执行完成。
- 命令受理后的执行进度由 ExecutionBatchStatus 表达。
- `result_unknown` 不允许客户端直接使用新幂等键重复提交。
- 已有 ExecutionBatch 后，不再依赖 TradeCommandStatus 表达执行结果。

典型路径：

```text
received → validating → accepted
received → validating → rejected
received → validating → result_unknown
received → cancelled
```

## 7. ExecutionBatchStatus

| 状态码 | 含义 |
|---|---|
| `created` | 已创建执行批次 |
| `prechecking` | 正在执行批次级检查 |
| `ready` | 可以开始提交交易腿 |
| `submitting` | 正在向外部系统提交订单 |
| `partially_filled` | 部分交易腿或订单已成交 |
| `balancing` | 正在补齐、调整或配平 |
| `completed` | 已满足批次结束条件 |
| `cancel_requested` | 已请求取消尚未完成的部分 |
| `cancelled` | 批次已取消且不再继续 |
| `exception` | 出现已确认异常 |
| `manual_intervention` | 等待或正在人工处理 |
| `result_unknown` | 批次结果暂时无法确认 |
| `terminated` | 已终止且不再继续 |

ExecutionBatchStatus 与订单状态、执行配平状态、风险状态和暴露状态分开。

典型路径：

```text
created → prechecking → ready → submitting → completed
submitting → partially_filled → balancing → completed
submitting → exception → manual_intervention → completed / terminated
submitting → result_unknown → submitting / partially_filled / completed / exception
```

## 8. OrderStatus

| 状态码 | 含义 |
|---|---|
| `pending_submit` | 等待提交 |
| `submitted` | 已发送至外部系统 |
| `acknowledged` | 外部系统已确认接收 |
| `partially_filled` | 部分成交 |
| `filled` | 全部成交 |
| `cancel_pending` | 正在撤销 |
| `cancelled` | 已撤销 |
| `rejected` | 被平台或外部系统拒绝 |
| `expired` | 已过期 |
| `failed` | 已确认失败 |
| `status_unknown` | 当前状态无法确认 |

通常终态：

- `filled`
- `cancelled`
- `rejected`
- `expired`
- `failed`

`status_unknown` 不是终态。

## 9. ExecutionBalanceStatus

ExecutionBalanceStatus 表达执行批次的实际交易腿关系，不表示账户余额。

| 状态码 | 含义 |
|---|---|
| `not_calculated` | 尚未计算 |
| `unbalanced` | 未达到目标配平关系 |
| `partially_balanced` | 部分达到目标关系 |
| `balanced` | 达到目标配平关系 |
| `outside_tolerance` | 偏差超出允许范围 |
| `manual_override` | 经授权人工接受当前偏差 |

不得再使用容易与账户余额混淆的通用 `BalanceStatus` 名称。

## 10. ExposureStatus

| 状态码 | 含义 |
|---|---|
| `none` | 无已识别异常暴露 |
| `primary_leg_exposed` | 主腿存在未对冲暴露 |
| `hedge_leg_exposed` | 对冲腿存在未对冲暴露 |
| `fx_exposed` | 存在汇率暴露 |
| `multi_leg_mismatch` | 多腿名义价值或风险不匹配 |
| `unknown` | 暴露状态无法确认 |

ExposureStatus 与 Position、ExecutionBalanceStatus 分开。

## 11. ReconciliationStatus

| 状态码 | 含义 |
|---|---|
| `pending` | 等待核对 |
| `running` | 正在核对 |
| `matched` | 核对一致 |
| `difference_found` | 发现差异 |
| `manual_review` | 等待人工复核 |
| `resolved` | 差异已处理 |
| `accepted_difference` | 经授权接受已知差异 |
| `failed` | 核对任务失败 |

## 12. RiskStatus

| 状态码 | 含义 |
|---|---|
| `normal` | 正常 |
| `watch` | 观察 |
| `warning` | 警告 |
| `restricted` | 部分操作受限 |
| `blocked` | 禁止相关操作 |
| `manual_review` | 需要人工确认 |
| `insufficient_data` | 数据不足，无法可靠判断 |
| `unknown` | 状态未知 |

RiskStatus 只表达结果层级；具体原因由 RiskDecision 和规则明细提供。

## 13. DeploymentEnvironment

表示系统部署位置和配置隔离层级。

| 状态码 | 含义 |
|---|---|
| `development` | 本地或开发环境 |
| `testing` | 集成与自动化测试环境 |
| `staging` | 接近生产配置的预发布环境 |
| `production` | 正式生产环境 |

DeploymentEnvironment 不代表是否产生真实订单。

## 14. TradingMode

表示当前交易执行模式。

| 状态码 | 含义 |
|---|---|
| `demo` | 纯前端演示或静态 Mock |
| `simulation` | 后端模拟撮合或模拟执行 |
| `paper` | 外部模拟账户、仿真实盘或测试交易通道 |
| `live` | 真实资金和真实订单 |

`production` 可以运行 `paper`；`testing` 也不能仅因名称而被视为安全实盘。

## 15. TradingPermissionState

表示当前用户和业务上下文是否允许交易操作。

| 状态码 | 含义 |
|---|---|
| `disabled` | 当前模式或功能未启用交易能力 |
| `read_only` | 仅允许查询，不允许改变交易状态 |
| `enabled` | 当前上下文允许执行授权范围内的交易命令 |
| `blocked` | 因风险、账户、服务或全局限制禁止交易 |

TradingPermissionState 应由服务端综合以下条件形成：

- DeploymentEnvironment。
- TradingMode。
- 用户能力权限和数据范围。
- 风险状态与全局阻断。
- 账户、Gateway 和执行服务健康。
- 报价和必要数据质量。

## 16. GatewayStatus

| 状态码 | 含义 |
|---|---|
| `starting` | 正在启动 |
| `connected` | 已连接且可用 |
| `degraded` | 部分能力异常 |
| `reconnecting` | 正在重连 |
| `disconnected` | 已断开 |
| `unauthorized` | 认证失败 |
| `rate_limited` | 被上游限频 |
| `maintenance` | 维护状态 |
| `error` | 未恢复错误 |

## 17. ApprovalStatus

| 状态码 | 含义 |
|---|---|
| `draft` | 审批请求尚未提交 |
| `pending` | 等待审批 |
| `approved` | 已批准 |
| `rejected` | 已拒绝 |
| `cancelled` | 发起人已取消 |
| `expired` | 审批授权已过期 |
| `executed` | 已使用审批结果完成目标操作 |

高风险操作的审批状态不替代目标对象自身状态。

## 18. 状态变化记录

状态变化至少记录：

- 对象 ID。
- 旧状态。
- 新状态。
- 发生时间。
- 来源模块或外部系统。
- 原因码。
- 关联命令、事件或审批 ID。
- 操作人，适用时。

## 19. 前端展示映射

前端可以将状态映射为：

- 中文文案。
- 颜色和图标。
- 操作建议。
- 按钮可用性和禁用原因。

但 View Model 不得改变状态本身含义。例如：

- `result_unknown` 不得展示为“失败”。
- `accepted` 不得展示为“交易成功”。
- `production` 不得展示为“实盘已启用”。

## 20. 新增状态规则

新增状态前必须确认：

1. 是否是新的业务语义，而不是新文案。
2. 是否可以通过现有状态加原因码表达。
3. 是否会改变生命周期和终态判断。
4. 前端、后端、接口、事件和报表是否兼容。
5. 是否需要接口版本或 ADR。
6. 是否已经更新本唯一来源文档。

## 21. 验收标准

- 同一状态码在前后端语义一致。
- 命令、执行批次、订单、配平、暴露、风险和数据质量状态分开。
- DeploymentEnvironment 与 TradingMode 分开。
- TradeCommand 不重复承担执行批次生命周期。
- 未知结果不被错误映射为失败。
- 状态变化可以追溯。
- 新状态具有兼容和降级策略。
