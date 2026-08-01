# Execution Risk Controls

状态：`active`  
适用版本：`Platform V6 / Phase 4A`  

## 1. 权威边界

```text
ExecutionBatch 负责双腿业务流程
Execution Risk 负责新增风险是否允许、残留敞口是否超限、失败后如何处置
TradeCommand 负责所有实际订单副作用
FinancialFact / Formal Accounting 负责成交后的正式金融事实与账务
```

RiskAction 不得直接绕过 TradeCommand 创建订单。Kill Switch 不修改历史订单、成交或金融事实。

## 2. 数据对象

### trading_kill_switches

保存 global、strategy、account 作用域的当前开关状态、原因、操作人、版本和更新时间。

### kill_switch_commands

保存 Kill Switch 写入幂等键和载荷哈希。同一幂等键不同载荷返回 409。

### execution_risk_policies

保存 StrategyInstance 当前执行风险策略。Batch 创建时读取并快照，不动态追溯修改历史 Batch。

### execution_batch_risk

保存每个 Batch 的策略快照、风险状态、残留敞口、币种、质量状态、第一腿成交时间、最后腿时间和原因。

### execution_risk_actions

保存人工或系统风险动作、幂等键、状态、操作人、原因、生成订单 ID 和失败原因。

## 3. Fail-closed 顺序

创建 ExecutionBatch 时：

```text
校验 Strategy / Account Binding / Instrument / ContractSpecification
→ 检查 global Kill Switch
→ 检查 strategy Kill Switch
→ 检查全部 account Kill Switch
→ 原子认领 Batch
→ 快照 ExecutionRiskPolicy
→ 执行第一腿
```

每条后续腿执行前再次检查 Kill Switch 和 maxLegDelaySeconds。

## 4. 残留敞口算法

风险敞口先按基础币种计算净合约数量，再对未匹配数量做保守估值；不能直接把两腿各自成交名义金额相加。

对每个 Fill：

```text
signed contract delta = side sign × fill quantity × contract multiplier
```

同一基础币种与结算币种组内：

```text
net contract delta = sum(signed contract delta)
reference price = max(valid fill price in the group)
residual = abs(net contract delta) × reference price
```

因此，方向相反且数量与 multiplier 完全匹配的两腿残留为零，即使两腿成交价格不同。不同币种且没有风险 FX 快照时，各币种残留绝对值保守相加，并标记：

```text
currency = MIXED
dataQualityState = incomplete
```

该值只用于执行风险门禁，不得作为正式 PnL 或会计输入。

## 5. 风险状态与 Batch 状态

风险状态和业务状态分别持久化：

| Batch status | Risk status | 解释 |
|---|---|---|
| `executing` | `clear` / `residual_exposure` | 执行中 |
| `partially_executed` | `residual_exposure` | 第一腿已成交 |
| `hedged` | `clear` | 两腿完成且风险计算完整 |
| `manual_intervention` | `escalated` | 需要人工接管 |
| `failed` | `resolved` | Batch 未完成，但风险已通过平仓解除 |

不得用 Batch failed 推断没有风险，也不得用两条 Order 已提交推断已经 hedged。

## 6. 自动平仓

`auto_flatten` 只对已成交原始 Leg 生成反向命令：

```text
risk action idempotency key + leg role
→ CreateTradeCommandRequest
→ TradeCommand
→ Platform Order
→ Runtime
```

风险平仓命令自身仍可能 result_unknown，因此只有全部反向命令 `filled` 才能标记 resolved。

## 7. 风险动作语义

当前受支持动作包括：

- `hold_and_escalate`：保持现状并进入人工接管；
- `flatten_filled_legs`：仅对已成交原始 Leg 创建反向 TradeCommand；
- `cancel_open_legs`：只记录并执行受支持的外部撤单边界，不能把未知结果宣称为已取消；
- `substitute_hedge`：通过独立幂等 TradeCommand 创建替代对冲。

任何风险动作都不能绕过 Account、Instrument、ContractSpecification、权限或 Live Write 门禁。

## 7. Kill Switch 语义

Kill Switch 阻止新增 Batch 风险。风险降低动作使用独立 RiskAction，并保留审计轨迹。

当前 4A 中：

- Batch 创建和后续 Leg 均受 Kill Switch 约束。
- 自动平仓不通过 Batch 写入口，避免 Kill Switch 将系统锁死在已存在裸敞口中。
- 风险降低动作仍受 Account、Instrument、ContractSpecification 和 TradeCommand 安全校验。

## 8. 幂等规则

| 对象 | 幂等身份 | 冲突行为 |
|---|---|---|
| Kill Switch change | `idempotencyKey` | 相同键不同载荷返回 409 |
| Risk Policy change | `idempotencyKey` | 相同键不同载荷返回 409 |
| RiskAction | `idempotencyKey` | 相同键不同载荷返回 409 |
| Auto flatten leg | `<risk-action-key>:<leg-role>` | 复用原 TradeCommand |
| Substitute hedge | `<risk-action-key>:replacement` | 复用原 TradeCommand |

## 9. 当前限制

- 没有外部 Venue Cancel Order 接口时，已存在的 accepted/result_unknown Order 不能声称取消成功。
- 多币种风险敞口尚未接入独立风险 FX 快照。
- RiskAction 的权限目前依赖本地部署边界，正式 RBAC 和双人审批尚未实现。
- 当前只允许 Simulation / Fake Gateway。