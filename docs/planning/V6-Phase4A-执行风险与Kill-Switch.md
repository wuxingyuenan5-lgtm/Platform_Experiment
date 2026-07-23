# V6 Phase 4A：执行风险与 Kill Switch

状态：`completed / merge pending`  
实施分支：`hardening/v6-phase4a-execution-risk`  
跟踪 Issue：`#14 V6 Phase 4A：ExecutionBatch 风险状态机、Kill Switch 与残腿处置`  
Pull Request：`#15 Implement V6 Phase 4A execution risk controls`  
上级计划：Issue `#12`、`V6-交易安全加固实施计划.md`  
最终验收：`Platform CI #185 / run 30002639120`  
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

命中时返回 `423 Locked`，且不得创建新的 TradeCommand 或产生 Runtime/Gateway 副作用。

Kill Switch 用于阻止新增风险。风险降低型平仓使用单独、可审计的 RiskAction，避免系统在已有裸敞口时被锁死。

## 3. 风险策略

每个 StrategyInstance 可以配置：

- `maxLegDelaySeconds`
- `maxResidualNotional`
- `failureAction`

当前 FailureAction：

- `hold_and_escalate`
- `auto_flatten`

ExecutionBatch 创建后将策略快照写入 `execution_batch_risk`。后续策略修改不反向改变已创建 Batch。

默认值：

```text
maxLegDelaySeconds = 10
maxResidualNotional = 100000
failureAction = hold_and_escalate
```

## 4. 风险状态

| riskStatus | 含义 |
|---|---|
| `clear` | 当前没有可识别的残留方向敞口 |
| `residual_exposure` | 存在未对冲敞口或不可可靠换算的混合币种敞口 |
| `disposition_in_progress` | 正在执行平仓、替代对冲或其他风险动作 |
| `resolved` | 风险动作已完成，残留风险已解除 |
| `escalated` | 需要人工接管或外部 Venue 能力尚不完整 |

Batch 业务状态与风险状态分离。`failed` 不代表无风险；`hedged` 也不能只凭两条命令提交成功判断。

## 5. 残留敞口

Phase 4A 最终采用“先净合约 Delta，再折算未匹配名义金额”的口径：

```text
signed contract delta
= side sign × fill quantity × contract multiplier
```

同一 Base Currency 与 Quantity Unit 的多条腿先净额：

```text
unmatched delta = sum(signed contract delta)
residual notional = abs(unmatched delta) × conservative reference price
```

因此，两条数量与 Contract Multiplier 完全匹配、方向相反的腿，即使成交价格不同，也属于已对冲方向风险；价格差进入策略收益，不应被误判为残留方向敞口。

数据来源：

- 优先使用实际 Fill Quantity 与 Fill Price。
- 没有 Fill 但存在限价时，使用请求数量和价格作为保守回退。
- 市场单既无 Fill 又无价格时，状态为 `incomplete`。
- 多 Base／Quantity Unit 或多结算币种无法可靠比较时，返回 `MIXED / incomplete` 和保守绝对值合计。

正式算法位于 `platform-backend/app/execution_exposure.py`，由组合入口注入 Execution Risk 模块，便于 Phase 4 后续继续拆分过大的风险模块。

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

调用方提供完整替代 Leg，经正式 TradeCommand 提交。替代命令成交后可标记 resolved；失败或未知时继续升级人工处理。

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

- `kill_switch_changed`
- `execution_risk_policy_changed`
- `execution_batch_risk_state_changed`
- `execution_risk_action_completed`

不得无痕覆盖风险状态、操作人、原因或处置结果。

## 9. 金样本

1. Global Kill Switch 开启后 Batch 在认领前返回 423，数据库中没有 Batch 和 TradeCommand。
2. 第一腿方向名义敞口为 100、策略阈值为 50 时，第二腿不提交并进入 escalated。
3. 第一腿成交、第二腿 result_unknown，failureAction=auto_flatten 时生成反向 TradeCommand，最终 Position 回到零。
4. 同一 RiskAction 幂等键重复提交只返回原动作，不产生第二次平仓。
5. 同一幂等键使用不同动作载荷返回 409。
6. firstFillAt 到下一腿超过 maxLegDelaySeconds 时阻止继续执行。
7. 两条反向腿数量相同但成交价格不同，Batch 仍正确标记 hedged，而不是把价差误判为方向敞口。

## 10. 验收记录

最终验收：`Platform CI #185 / run 30002639120`

| 检查 | 结果 |
|---|---|
| Platform Backend Phase 4 strict Ruff Gate | 通过 |
| Platform Backend 全量 Ruff 与 Pytest | 通过，45 项测试 |
| Execution Runtime strict Ruff、全量 Ruff 与 Pytest | 通过 |
| Frontend frozen install、type-check、production build | 通过 |
| Kill Switch 创建前阻断 | 通过 |
| 残留敞口阈值与腿间时间 | 通过 |
| 自动平仓与 Position 回零 | 通过 |
| RiskAction 幂等与载荷冲突 | 通过 |
| 价差与方向敞口正确区分 | 通过 |
| README、START-HERE、API Spec、技术设计、Release Gate、Changelog | 已同步 |

## 11. 明确延期

Phase 4A 不完成：

- Bybit／MT5 外部撤单。
- 外部 Order、Fill、Position、Balance 主动查询。
- Bybit Demo 与 MT5 Demo 端到端验证。
- 外部事实自动导入和 Reconciliation Difference。
- 日终对账和连续运行验收。
- Live 发布审批、RBAC、双人审批和生产密钥托管。

以上内容进入 Phase 4B–4D。