# Platform V6 状态枚举与生命周期规范

状态：`active`  
适用分支：`refactor/frontend-architecture-v6`  
架构层级：公共领域模型

## 1. 文档定位

本文档定义前端、后端、接口和报表共同使用的核心状态枚举及生命周期边界。

状态码用于表达稳定业务语义；中文文案、颜色、图标和页面布局属于 View Model 和 UI 层，不作为状态本身。

## 2. 通用规则

- 状态码使用稳定英文小写下划线格式。
- 不同业务维度使用不同状态字段。
- 不通过自然语言、颜色或数值正负号推断状态。
- 状态变化应记录时间、来源和必要原因。
- 未识别的新状态前端应降级展示为“未知状态”，不得白屏。
- 外部系统状态先映射到平台状态，并保留原始值。

## 3. QuoteStatus

| 状态码 | 含义 |
|---|---|
| `fresh` | 报价在允许的新鲜度范围内 |
| `delayed` | 报价延迟但仍可用于只读观察 |
| `stale` | 报价过期，不允许依赖其执行交易 |
| `unavailable` | 当前无可用报价 |
| `conflicted` | 多来源报价冲突 |
| `unknown` | 状态无法确认 |

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
| `blocked` | 被风险或系统限制阻断 |
| `error` | 运行异常 |
| `archived` | 已归档 |

策略实例状态不等于策略定义是否在前端注册表中展示。

## 6. TradeCommandStatus

| 状态码 | 含义 |
|---|---|
| `received` | 已收到请求 |
| `validating` | 正在进行权限、参数和风险校验 |
| `rejected` | 校验未通过 |
| `accepted` | 命令已受理 |
| `executing` | 正在执行 |
| `completed` | 命令目标已完成 |
| `failed` | 已确认失败且不会继续 |
| `result_unknown` | 结果暂时无法确认 |
| `cancelled` | 命令已取消 |

`accepted` 不等于成交；`failed` 必须区别于 `result_unknown`。

## 7. ExecutionBatchStatus

| 状态码 | 含义 |
|---|---|
| `created` | 已创建执行批次 |
| `prechecking` | 正在执行前检查 |
| `ready` | 可以开始提交交易腿 |
| `submitting` | 正在提交订单 |
| `partially_filled` | 部分交易腿或订单已成交 |
| `balancing` | 正在补齐或配平 |
| `completed` | 已完成并达到结束条件 |
| `cancel_requested` | 已请求取消 |
| `cancelled` | 已取消 |
| `exception` | 出现明确异常 |
| `manual_intervention` | 等待或正在人工处理 |
| `result_unknown` | 批次结果无法确认 |
| `terminated` | 已终止且不再继续 |

ExecutionBatchStatus 与配平状态、风险状态分开。

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
| `rejected` | 被外部系统或平台拒绝 |
| `expired` | 已过期 |
| `failed` | 已确认失败 |
| `status_unknown` | 当前状态无法确认 |

订单状态终态通常包括：

- `filled`
- `cancelled`
- `rejected`
- `expired`
- `failed`

`status_unknown` 不是终态。

## 9. ReconciliationStatus

| 状态码 | 含义 |
|---|---|
| `pending` | 等待核对 |
| `running` | 正在核对 |
| `matched` | 核对一致 |
| `difference_found` | 发现差异 |
| `manual_review` | 等待人工复核 |
| `resolved` | 差异已处理 |
| `accepted_difference` | 已确认接受差异 |
| `failed` | 核对任务失败 |

## 10. BalanceStatus

| 状态码 | 含义 |
|---|---|
| `not_calculated` | 尚未计算 |
| `unbalanced` | 未配平 |
| `partially_balanced` | 部分配平 |
| `balanced` | 已配平 |
| `outside_tolerance` | 超出容忍范围 |
| `manual_override` | 人工确认接受当前状态 |

BalanceStatus 用于执行组合，不等于账户余额状态。

## 11. RiskStatus

| 状态码 | 含义 |
|---|---|
| `normal` | 正常 |
| `watch` | 观察 |
| `warning` | 警告 |
| `restricted` | 部分操作受限 |
| `blocked` | 禁止相关操作 |
| `manual_review` | 需要人工确认 |
| `insufficient_data` | 数据不足，无法形成可靠判断 |
| `unknown` | 状态未知 |

RiskStatus 只表达结果层级；具体原因由 RiskDecision 和规则明细提供。

## 12. EnvironmentStatus

| 状态码 | 含义 |
|---|---|
| `demo` | 纯前端演示或 Mock |
| `simulation` | 后端模拟执行 |
| `test` | 测试环境或沙盒 |
| `paper` | 模拟账户或仿真实盘 |
| `live` | 真实资金实盘 |

环境是独立字段，不通过接口域名或页面颜色推断。

## 13. GatewayStatus

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

## 14. 生命周期约束

### 14.1 TradeCommand

典型路径：

```text
received → validating → accepted → executing → completed
```

拒绝路径：

```text
received → validating → rejected
```

未知路径：

```text
accepted → executing → result_unknown
```

恢复后可进入 `executing`、`completed` 或 `failed`。

### 14.2 ExecutionBatch

典型路径：

```text
created → prechecking → ready → submitting → completed
```

部分成交路径：

```text
submitting → partially_filled → balancing → completed
```

异常路径：

```text
submitting → exception → manual_intervention → completed / terminated
```

### 14.3 Order

典型路径：

```text
pending_submit → submitted → acknowledged → filled
```

部分成交路径：

```text
acknowledged → partially_filled → filled
```

撤销路径：

```text
acknowledged / partially_filled → cancel_pending → cancelled
```

## 15. 状态变化记录

状态变化至少记录：

- 对象 ID。
- 旧状态。
- 新状态。
- 发生时间。
- 来源。
- 原因码。
- 关联命令或事件 ID。
- 操作人，适用时。

## 16. 前端展示映射

前端可以将状态映射为：

- 中文文案。
- 颜色。
- 图标。
- 操作建议。
- 是否允许按钮。

但 View Model 映射不得改变状态本身含义。

例如 `result_unknown` 不得简单展示为“失败”。

## 17. 新增状态规则

新增状态前必须确认：

1. 是否是新的业务语义，而不是新的显示文案。
2. 是否可以通过现有状态加原因码表达。
3. 是否会改变生命周期和终态判断。
4. 前端、后端、事件和报表是否都能兼容。
5. 是否需要接口版本或 ADR。

## 18. 验收标准

- 同一状态码在前后端语义一致。
- 订单、执行批次、配平、风险和数据质量状态分开。
- 未知结果不被错误映射为失败。
- 状态变化可追溯。
- 前端不通过自然语言解析业务状态。
- 新状态具有兼容和降级策略。
