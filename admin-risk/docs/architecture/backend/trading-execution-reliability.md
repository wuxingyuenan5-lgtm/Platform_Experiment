# Platform V6 交易执行与可靠性架构

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：后端架构

## 1. 文档定位

本文档定义真实交易接入前必须具备的交易命令、执行批次、订单、成交、配平、异常恢复和人工处理边界。

本文不指定交易内核或 Gateway 技术。状态码和生命周期以 `../domain/status-enums-and-lifecycles.md` 为唯一来源，本文件只定义可靠性流程和职责。

## 2. 核心原则

- 用户的业务目标不等于交易所订单。
- 命令已受理不等于订单已提交。
- 订单已提交不等于已成交。
- 单腿成交不等于策略组合完成。
- 前端连接断开不影响后端执行。
- 未知结果必须显式记录，不能假定成功或失败。
- 所有高风险操作可审计、可恢复、可人工接管。
- DeploymentEnvironment、TradingMode 和 TradingPermissionState 分开。

## 3. 标准执行链路

```text
TradeIntent
   ↓
TradeCommand
   ↓ permission / validation / risk
ExecutionBatch
   ↓
LegInstruction
   ↓
Order
   ↓
Execution / Fill
   ↓
Position / Exposure / PnL
```

### TradeIntent

表示用户或策略希望完成的业务目标，例如建立某个套利组合。

### TradeCommand

表示平台对一次改变交易状态请求的受理记录。TradeCommand 只负责：

- 接收请求。
- 幂等判断。
- 权限、参数、模式和风险校验。
- 接受或拒绝命令。
- 创建或关联目标 ExecutionBatch。

TradeCommand 不重复维护 ExecutionBatch 的执行进度。

### ExecutionBatch

表示为完成同一交易目标而组织的一组交易腿、订单和异常处理，是双腿或多腿执行的核心聚合对象。

## 4. TradeCommand 要求

正式命令至少包含：

- `tradeCommandId`
- `requestId`
- `idempotencyKey`
- `strategyInstanceId`
- 操作类型
- 操作人
- 目标账户和标的
- 命令参数
- 客户端提交时间
- 服务端受理时间
- DeploymentEnvironment
- TradingMode

命令状态以状态枚举文档为准。成功受理并建立执行批次后，命令保持 `accepted`；后续过程读取 ExecutionBatchStatus。

## 5. 幂等

以下操作必须支持幂等：

- 提交交易。
- 撤单。
- 平仓。
- 配平。
- 人工确认异常。
- 使用审批结果执行高风险操作。

同一幂等键和同一业务上下文重复提交时：

- 不创建重复执行批次或重复命令目标。
- 返回原受理结果或当前权威状态。
- 记录重复请求。
- 相同幂等键但不同 payload 返回冲突。

前端可以生成请求级幂等键，但幂等作用域、有效期和冲突判断由后端权威维护。

## 6. 执行前校验

至少包括：

- 身份和能力权限。
- DeploymentEnvironment 与 TradingMode 是否允许操作。
- TradingPermissionState。
- 策略实例状态。
- 策略与账户绑定关系。
- 账户可用性。
- 标的和合约规则。
- 报价新鲜度和数据质量。
- 数量、价格和精度。
- 余额和保证金。
- 两腿方向、目标比例和暴露容忍范围。
- 风险规则和全局阻断。
- 是否存在冲突中的执行批次。
- 高风险操作是否需要有效审批。

校验形成结构化 ValidationResult 和 RiskDecision，不能只返回自然语言。

## 7. ExecutionBatch 要求

一个双腿或多腿目标必须由一个 ExecutionBatch 组织。

执行批次至少记录：

- `executionBatchId`
- `tradeCommandId`
- `strategyInstanceId`
- 目标组合和交易腿列表
- 目标名义价值和配平关系
- 执行方式，例如顺序、并行或条件触发
- 当前 ExecutionBatchStatus
- 当前 ExecutionBalanceStatus
- 当前 ExposureStatus
- 已成交数量和剩余数量
- 异常和人工处理状态
- 创建、更新和完成时间

ExecutionBatch 状态、执行配平状态和暴露状态必须分别保存。

## 8. LegInstruction

每条交易腿指令至少包含：

- `legInstructionId`
- `executionBatchId`
- 腿角色
- `accountId`
- `instrumentId`
- 买卖方向
- 目标数量或目标名义价值
- 订单类型
- 价格参数
- 外部执行目标或 Gateway

LegInstruction 是平台执行计划，不等于外部 Order。

## 9. Order 与 Fill

平台订单状态与外部状态码分开，平台枚举以状态文档为准。

规则：

- 一张 Order 可以产生多笔 Fill。
- Fill 记录不可因订单状态变化被覆盖。
- Fill 至少保留价格、数量、费用、成交时间和外部成交 ID。
- 订单撤销不删除已经发生的成交。
- Gateway 映射外部状态并保留原始状态码。
- 持仓变化依据成交或经核对后的外部持仓事实生成。

## 10. 配平与暴露

执行批次独立计算：

- 目标配平比例。
- 实际成交比例。
- 名义价值偏差。
- 数量偏差。
- Delta 或方向暴露。
- 汇率暴露，适用时。
- 暴露持续时间。

配平结果使用 ExecutionBalanceStatus；不得使用容易与账户余额混淆的通用 BalanceStatus。

暴露结果使用 ExposureStatus。执行批次可以已经完成订单提交，但仍处于未配平或存在暴露状态。

## 11. 异常类型

至少包括：

- 报价过期或数据质量不足。
- 账户不可用。
- Gateway 或上游连接中断。
- 提交超时。
- 订单被拒绝。
- 单腿成交。
- 部分成交。
- 撤单结果未知。
- 成交回报重复或乱序。
- 实际持仓与平台推导不一致。
- 保证金不足。
- 风险状态在执行中变化。
- 数据源冲突。
- 审批授权失效。

异常关联：

- ExecutionBatch。
- LegInstruction。
- Order 或 Fill。
- 当前配平和暴露。
- 处理动作。
- 操作人、时间和原因码。

## 12. 结果未知

网络超时或上游结果不确定时，不得直接标记失败并重新下单。

处理顺序：

1. 标记命令、执行批次或订单对应的 unknown 状态。
2. 暂停自动重复提交。
3. 使用客户端订单 ID、外部订单 ID 或账户查询确认。
4. 重新同步订单、成交、持仓和账户。
5. 根据权威查询恢复状态。
6. 无法自动确认时进入人工处理。

未知状态属于待恢复状态，不是失败终态。

## 13. 重试原则

可以自动重试：

- 只读查询。
- 明确未到达上游的幂等命令。
- 具有稳定幂等键且结果可确认的操作。

不得盲目自动重试：

- 结果未知的下单。
- 无幂等支持的外部接口。
- 可能扩大单腿暴露的操作。
- 风险、权限、审批或账户状态已变化的命令。

## 14. 恢复与重启

执行服务重启后必须：

- 读取未完成 ExecutionBatch。
- 查询外部订单和成交。
- 恢复账户、持仓、配平和暴露状态。
- 识别重复或乱序事件。
- 继续安全自动流程或进入人工处理。

运行状态不得只保存在进程内存。

## 15. 对账

至少核对：

- 平台订单与外部订单。
- 平台成交与外部成交。
- 平台推导持仓与外部持仓。
- 平台余额与外部余额。
- 损益、费用和资金事件。

发现差异时：

- 不直接覆盖原始记录。
- 生成差异项和影响范围。
- 必要时阻止新增风险。
- 进入自动修复、人工复核或接受差异流程。
- 记录审批、确认和修正。

## 16. 人工处理与审批

人工处理可以包括：

- 确认外部订单真实状态。
- 选择撤销、补单或配平。
- 终止执行批次。
- 接受已知偏差。
- 关联外部成交或持仓。
- 添加处理备注。

高风险动作是否需要 Maker／Checker 审批，以 `../domain/approval-and-dual-control.md` 为准。

所有人工动作必须进行权限校验和审计。

## 17. 全局交易阻断

系统预留范围化阻断能力：

- 全平台。
- 某 DeploymentEnvironment 或 TradingMode。
- 某 Gateway。
- 某账户。
- 某策略实例。
- 某标的。

阻断状态由后端权威维护并推送前端。阻断默认禁止新增风险，不应无条件自动平仓。

## 18. 监控指标

至少监控：

- 命令受理量和拒绝量。
- ExecutionBatch 创建和完成量。
- Gateway 提交成功率和延迟。
- 订单确认延迟。
- 单腿暴露数量和持续时间。
- unknown 状态数量和持续时间。
- 对账差异。
- Gateway 连接状态。
- 人工处理和审批积压。

## 19. 分阶段启用

交易能力按以下原则逐步启用：

1. Demo。
2. 后端 Simulation。
3. Paper 或测试交易通道。
4. 只读真实账户接入。
5. 小资金、单策略、受控 Live。
6. 扩展账户、策略和 Gateway。

具体实施安排由后续正式规划决定；`implementation-roadmap.md` 当前为 draft，不作为已批准计划。

## 20. 唯一来源

- 状态枚举：`../domain/status-enums-and-lifecycles.md`。
- 领域对象：`../domain-model-boundaries.md`。
- API 与幂等：`../integration/api-contract-and-versioning.md`。
- 实时恢复：`../integration/realtime-events-and-recovery.md`。
- 审批：`../domain/approval-and-dual-control.md`。

## 21. 验收标准

- TradeCommand 只表达命令受理，不重复表达执行批次进度。
- 双腿交易由 ExecutionBatch 组织。
- 订单和成交分开保存。
- ExecutionBatchStatus、ExecutionBalanceStatus 和 ExposureStatus 分开。
- 结果未知不会被误判为失败并重复下单。
- 服务重启后可以恢复未完成执行。
- 对账差异、人工处理和高风险审批可审计。
- 前端断线不会中止后台执行。
