# V6 Phase 4A：执行风险与 Kill Switch

状态：`implementation complete / acceptance pending`  
实施分支：`hardening/v6-phase4a-execution-risk`  
跟踪 Issue：`#14 V6 Phase 4A：ExecutionBatch 风险状态机、Kill Switch 与残腿处置`  
Pull Request：`#15 Implement V6 Phase 4A execution risk controls`  
上级计划：Issue `#12`、`V6-交易安全加固实施计划.md`  
更新时间：`2026-07-23`

## 1. 阶段目标

Phase 4A 只处理双腿执行期间的风险控制，不连接真实资金：

```text
ExecutionBatch
→ Kill Switch 双重检查
→ 风险策略快照
→ 第一腿成交
→ 腿间时间与残留敞口检查
→ 第二腿成交或失败
→ 幂等风险处置
→ AuditEvent
```

当前发布边界仍为 Simulation / Fake Gateway。

## 2. Kill Switch

支持三级作用域：

- `global / *`
- `strategy / {strategyInstanceId}`
- `account / {accountId}`

写操作必须提供 `idempotencyKey`、`actor`、`enabled` 和可选 `reason`。

执行链路在两个位置检查：

1. ExecutionBatch 创建和认领之前。
2. 每条 Leg 调用 TradeCommand 之前。

任何命中的 Kill Switch 都返回 `423 Locked`，且不得创建新的 TradeCommand 或产生 Runtime/Gateway 副作用。

Kill Switch 用于阻止新增风险。风险降低型的自动平仓使用单独、可审计的 RiskAction，不被普通 Batch 写入口替代。

## 3. 风险策略

每个 StrategyInstance 可以配置：

- `maxLegDelaySeconds`
- `maxResidualNotional`
- `failureAction`

当前 FailureAction：

- `hold_and_escalate`
- `auto_flatten`

ExecutionBatch 创建后将策略快照写入 `execution_batch_risk`。后续策略修改不反向改变已创建 Batch 的风险边界。

默认值：

```text
maxLegDelaySeconds = 10
maxResidualNotional = 100000
failureAction = hold_and_escalate
```

## 4. 风险状态

| riskStatus | 含义 |
|---|---|
| `clear` | 当前没有可识别的残留敞口 |
| `residual_exposure` | 存在未对冲敞口或无法可靠换算的混合币种敞口 |
| `disposition_in_progress` | 正在执行平仓、替代对冲或其他风险动作 |
| `resolved` | 风险动作已完成，残留风险已解除 |
| `escalated` | 需要人工接管或外部 Venue 能力尚不完整 |

Batch 业务状态与风险状态分离。`hedged` 不应仅凭两条命令提交成功判断，而应同时满足残留敞口为零且数据质量完整。

## 5. 残留敞口

残留敞口优先使用实际 Fill：

```text
Fill Quantity × Fill Price × Contract Multiplier
```

没有 Fill 但存在限价时，使用请求数量和价格作为保守回退。市场单既无 Fill 又无价格时，数据质量为 `incomplete`。

同一结算币种按买入为正、卖出为负净额计算。多结算币种在没有正式风险 FX 快照时使用保守绝对值合计，币种标记为 `MIXED`、数据质量标记为 `incomplete`，不得伪装成已完全对冲。

## 6. 风险处置动作

### 6.1 hold_and_escalate

- Batch 进入 `manual_intervention`。
- `requiresManualIntervention=true`。
- Risk 状态进入 `escalated`。
- 操作人、原因和动作写入 AuditEvent。

### 6.2 flatten_filled_legs

- 对已成交 Leg 逐条生成反向 Market TradeCommand。
- 幂等键由 RiskAction 幂等键和 Leg Role 确定性派生。
- 不允许直接向 orders 表插入风险平仓单。
- 全部平仓命令成交后 Risk 状态为 `resolved`。
- 任一平仓结果未知或失败时进入 `escalated`。

### 6.3 cancel_open_legs

- 尚未生成 Order 的 pending/submitting Leg 可以本地取消。
- 已存在外部 Order 的 accepted/processing/result_unknown Leg 在 Phase 4B/4C 接入外部撤单前返回 `action_required`，不伪装为取消成功。

### 6.4 substitute_hedge

调用方提供完整替代 Leg，经正式 TradeCommand 提交。替代命令成交后可以将 Batch 风险标记为 resolved；失败或未知时继续升级人工处理。

## 7. API

```http
GET /api/v1/risk/kill-switches/{scopeType}/{scopeId}
PUT /api/v1/risk/kill-switches/{scopeType}/{scopeId}

GET /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
PUT /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy

GET /api/v1/trading/execution-batches/{batchId}/risk
GET /api/v1/trading/execution-batches/{batchId}/risk-actions
POST /api/v1/trading/execution-batches/{batchId}/risk-actions
```

## 8. 审计事件

至少记录：

- `kill_switch_changed`
- `execution_risk_policy_changed`
- `execution_batch_risk_state_changed`
- `execution_risk_action_completed`

不得无痕覆盖风险状态、操作人、原因或处置结果。

## 9. 金样本

1. Global Kill Switch 开启后 Batch 在认领前返回 423，数据库中没有 Batch 和 TradeCommand。
2. 第一腿名义敞口为 100，策略阈值为 50 时，第二腿不提交并进入 escalated。
3. 第一腿成交、第二腿 result_unknown，failureAction=auto_flatten 时，生成一条反向 TradeCommand，最终 Position 回到零。
4. 同一 RiskAction 幂等键重复提交只返回原动作，不产生第二次平仓。
5. 同一幂等键使用不同动作载荷返回 409。
6. firstFillAt 到下一腿超过 maxLegDelaySeconds 时阻止继续执行。

## 10. 验收清单

- [x] Kill Switch 具备 global、strategy、account 作用域。
- [x] Kill Switch 写入幂等且载荷冲突返回 409。
- [x] Batch 创建前与每腿执行前均检查 Kill Switch。
- [x] 风险策略按 Batch 快照固定。
- [x] 实际 Fill、Contract Multiplier 和结算币种进入残留敞口。
- [x] 自动平仓经过 TradeCommand。
- [x] RiskAction 幂等且有审计记录。
- [x] Kill Switch、超限、自动平仓、重复动作和腿间超时有测试。
- [ ] Platform CI 全部通过并记录最终 Run ID。
- [ ] PR、Issue、README、START-HERE、API Spec、Release Gate 和 Changelog 完成最终留痕。

## 11. 明确延期

Phase 4A 不完成：

- Bybit／MT5 外部撤单。
- 外部 Order、Fill、Position、Balance 主动查询。
- Bybit Demo 与 MT5 Demo 端到端验证。
- 外部事实自动导入和 Reconciliation Difference。
- 日终对账和连续运行验收。
- Live 发布审批、RBAC、双人审批和生产密钥托管。

以上内容进入 Phase 4B–4D。