# Platform V6 最小发布门槛

状态：`active`  
适用基线：`main / Platform V6`  
总体计划：`../../../docs/planning/V6-交易安全加固实施计划.md`  
当前阶段：`../../../docs/planning/V6-Phase4A-执行风险与Kill-Switch.md`

## 1. 目的

为以 Vibe Coding 为主的开发方式建立低成本、可重复、可审计的质量门槛。任何涉及交易、账户、持仓、PnL、Runtime、权限、风险或部署的变更，不能只凭页面效果判断完成。

本规范是稳定提交和 Pull Request 的最低门槛，不等于完整生产测试体系。

## 2. 自动检查

### 2.1 前端

在 `admin-risk` 执行：

```bash
pnpm sync:trading-tools
pnpm type:check
pnpm build
```

要求：

- Markdown 交易工具源与生成数据一致。
- 本次范围无 TypeScript 类型错误。
- 正式构建无阻断错误。
- 交易页面不得硬编码正式账户、策略实例或 Instrument ID。
- 产品页面只展示完成业务任务需要的信息、操作和状态。
- 开发说明、实现解释、跳转机制和联调备注进入 Markdown，不进入正式界面主要视觉层。

### 2.2 Platform Backend

在 `platform-backend` 执行：

```bash
python -m ruff check app tests
python -m pytest
```

Phase 4A 严格 Gate 至少覆盖：

- `app/main.py`
- `app/application.py`
- `app/trade_commands.py`
- `app/execution_batches.py`
- `app/execution_risk.py`
- `app/financial_facts.py`
- `tests/test_execution_batches.py`
- `tests/test_execution_batches_v1.py`
- `tests/test_execution_risk.py`
- Phase 1–3 安全、恢复和账务测试

### 2.3 Execution Runtime

在 `execution-runtime` 执行：

```bash
python -m ruff check app tests
python -m pytest
```

### 2.4 GitHub Actions

- `main` push、`hardening/**` push 和面向 `main` 的 PR 必须触发 CI。
- Backend、Runtime、Frontend 全部通过后才允许合并。
- 不允许强制更新 `main` 绕过检查。
- 本批次修改文件必须通过严格 Ruff Gate；历史债务可以盘点，但不得隐藏。
- `docs/planning/**`、`docs/technical/**`、README、START-HERE、Release Gate 和 Changelog 变化必须触发 CI。

## 3. 交易安全检查

- 未知或非 active Account fail-closed。
- Account 与 StrategyInstance 必须存在 active binding。
- StrategyInstance 必须 active 且属于 closed-loop。
- Instrument 与 ContractSpecification 必须存在。
- 数量、数量步长和价格步长必须合法。
- Live 默认关闭。
- 凭证只保存引用，不进入数据库响应、日志和代码。
- Runtime 在外部副作用前原子抢占 Command。
- 重复 Command 不产生第二次 Gateway 调用。

任何一项无法确认，不能标记为可交易版本。

## 4. 命令入口与幂等检查

正式业务写入口：

```http
POST /api/v1/trading/commands
POST /api/v1/trading/execution-batches
```

必须确认：

- TradeCommand 强制提供 `idempotencyKey`。
- ExecutionBatch 强制提供 `idempotencyKey` 与 `strategyInstanceId`。
- 每条 Batch Leg 都生成独立 TradeCommand。
- Leg 幂等键由 Batch 幂等键和 Leg Role 确定性派生。
- Batch 在第一腿前完成全部 Catalog 预校验。
- 重复 Batch 不生成新的 Command、Order 或 Runtime 调用。
- 相同幂等键不同业务载荷返回 409。
- `POST /api/v1/trading/orders` 仅为 deprecated 兼容入口。

## 5. result_unknown 与事件重放检查

- `result_unknown` 不得被当作失败后直接重试。
- 恢复接口只能查询 Runtime／外部系统，不能重新提交原订单。
- Runtime 无事件或不可用时继续保持未知。
- Runtime event 的 `command_id` 与 `platform_order_id` 必须匹配。
- Fill 只有去重插入成功后才能更新投影。
- 相同 Fill event 重放不得重复改变持仓和损益。
- 恢复后同步 TradeCommand 与 Order 状态。
- 人工处理和恢复动作必须留痕。

外部 Venue 主动查询尚未完成前，不允许真实资金 Live。

## 6. Phase 4A Kill Switch 检查

接口：

```http
GET /api/v1/risk/kill-switches/{scopeType}/{scopeId}
PUT /api/v1/risk/kill-switches/{scopeType}/{scopeId}
```

必须确认：

- 支持 global、strategy、account 三级作用域。
- Global 作用域固定使用 `scopeId=*`。
- 写操作必须提供 `idempotencyKey`、`actor`、`enabled` 和可选原因。
- 同一幂等键同载荷返回原结果，不增加版本。
- 同一幂等键不同载荷返回 409。
- Batch 原子认领之前检查 Kill Switch。
- 每条 Leg 调用 TradeCommand 之前再次检查。
- 命中时返回 423，且没有新增 Batch／TradeCommand／Runtime 副作用。
- 开关变化记录版本、操作人、原因和 AuditEvent。
- Kill Switch 用于阻止新增风险，不得删除或改写历史事实。

## 7. Phase 4A 风险策略与快照检查

接口：

```http
GET /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
PUT /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
```

必须确认：

- 策略包含 `maxLegDelaySeconds`、`maxResidualNotional` 和 `failureAction`。
- 数值边界经过模型校验。
- 策略写入幂等且载荷冲突返回 409。
- Batch 创建时将策略复制到 `execution_batch_risk`。
- 修改 Strategy Risk Policy 不反向改变历史 Batch。
- 缺少显式配置时使用文档化默认值，不使用空值或隐式零。

## 8. Phase 4A 残留敞口检查

接口：

```http
GET /api/v1/trading/execution-batches/{batchId}/risk
```

必须确认：

- 第一腿成交后保存 `firstFillAt`。
- 后续腿在提交前检查最大腿间延迟。
- 残留敞口优先使用实际 Fill Quantity 和 Fill Price。
- Contract Multiplier 进入名义敞口。
- Settlement Currency 明确保存。
- 同币种按买入正、卖出负计算净敞口。
- 多币种没有风险 FX 快照时使用保守绝对值合计，并标记 `MIXED / incomplete`。
- 无 Fill 且市场单无价格时标记 incomplete，不伪造零风险。
- 超过 `maxResidualNotional` 后禁止继续增加风险。
- Batch `failed` 不得被解释为风险已经解除。
- `hedged` 必须同时满足两腿完成、残留敞口为零且数据质量完整。

## 9. Phase 4A 风险动作检查

接口：

```http
GET  /api/v1/trading/execution-batches/{batchId}/risk-actions
POST /api/v1/trading/execution-batches/{batchId}/risk-actions
```

必须确认：

- 每个 RiskAction 强制提供 `idempotencyKey` 和 `actor`。
- 同一动作重复提交不产生第二次订单副作用。
- 同一幂等键不同载荷返回 409。
- `hold_and_escalate` 进入 `manual_intervention / escalated`。
- `flatten_filled_legs` 对每个已成交 Leg 生成反向 TradeCommand。
- 自动平仓不直接插入 orders 表。
- 全部反向命令 filled 后才能标记 resolved。
- 任一平仓命令失败或未知时继续 escalated。
- `cancel_open_legs` 不能把已有外部 Order 伪装为取消成功。
- `substitute_hedge` 必须提供完整替代 Leg 并经过 TradeCommand 安全校验。
- 风险状态变化和动作结果写入 AuditEvent。

## 10. Phase 3 FinancialFact 检查

```http
POST /api/v1/financial-facts
GET  /api/v1/financial-facts
```

- FinancialFact 只允许新增。
- 客户端幂等键和外部身份双重唯一。
- 身份相同载荷不同返回 409。
- Account、Instrument、ContractSpecification 和 Strategy 归属必须有效。
- Quantity Unit、Settlement Currency 和 Contract Multiplier 来自 Catalog。
- 事实保存 occurredAt、createdAt、source、externalId 和数据质量。
- 重复导入不得重复改变 Position、PnL 或 NAV。

## 11. Formal Position、PnL 与 NAV 检查

```http
POST /api/v1/strategies/instances/{strategyInstanceId}/financials/rebuild
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-positions
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-pnl
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots/run
```

- Position 和 PnL 只由 FinancialFact 生成并可完整重建。
- Trading PnL 使用数量、价格、方向和 Contract Multiplier。
- PnL 分项保存 Trading、Funding、Swap、Fee、FX 和 Total。
- Stablecoin 不自动等同 USD。
- 缺失 FX 时标记 incomplete。
- NAV 对全部 active binding 使用同一 valuationTime。
- 缺失账户返回 missingAccountIds，不静默补零。
- 旧 PnL／NAV 接口不得标记为正式账务。

## 12. 前端 Catalog 与产品界面检查

- 从 Backend 获取 Strategy、Binding、Account、Instrument 和 ContractSpecification。
- Catalog 不完整时禁用提交。
- 明确显示 TradingMode；不得把 Simulation 展示为 Demo 或 Live。
- 缺失 Position、PnL、风险和账务数据展示 `—` 或未知。
- 不允许通过环境变量或代码内 UUID 绕过 Catalog。
- 不展示无业务必要的开发说明、实现解释和联调备注。

## 13. 金样本检查

Phase 4A 至少保留：

- Global Kill Switch 在 Batch 认领前阻断的样本。
- 第一腿残留名义敞口超过阈值、第二腿不提交的样本。
- 第一腿成交、第二腿未知、自动反向平仓的样本。
- 自动平仓 Position 回到零的样本。
- RiskAction 重复提交不重复下单的样本。
- RiskAction 幂等键载荷冲突的样本。
- maxLegDelaySeconds 超时样本。

Phase 3 金样本继续保留：Contract Multiplier PnL、分项 PnL、重建、缺失 FX、多账户 NAV 和事实冲突。

预期值必须写入测试和实施文档，不依赖口头解释。

## 14. 文档一致性

涉及架构、状态机、幂等、恢复、Kill Switch、残留敞口、RiskAction、FinancialFact、PnL、NAV、API 或发布范围时，必须同步更新：

1. 当前阶段实施计划。
2. 对应技术设计。
3. `docs/technical/API_SPEC.md`。
4. `docs/planning/V6-交易安全加固实施计划.md`。
5. README 与 START-HERE。
6. 本 Release Gate。
7. CHANGELOG。
8. Issue、PR 和 CI 验收记录。

普通样式微调可以不改需求文档，但仍须有清晰提交记录。

## 15. 变更范围检查

- 没有意外修改一级架构和无关路由。
- 没有误改归档文档。
- 没有把真实凭证、`.env`、数据库或日志提交到仓库。
- 没有因局部问题重写公共主题。
- 没有直接修改生成文件作为唯一修改。
- 大规模自动变更有来源、测试和验收说明。
- 新增组合入口不改变既有应用生命周期。
- 临时 Ruff 例外有具体文件、具体规则和后续拆分说明，不能全局关闭检查。

## 16. 人工冒烟检查

- Backend 和 Runtime 健康接口可用。
- Simulation / Fake Gateway 模式明确。
- TradeCommand、ExecutionBatch、FinancialFact 和 RiskAction 返回可查询幂等标识。
- Global Kill Switch 开启后 Batch 返回 423。
- Kill Switch 关闭后 Simulation Batch 可恢复执行。
- Batch Risk、RiskAction、Formal PnL 和 Formal NAV 路由可访问。
- 失败、未知、残留敞口、escalated 和 resolved 不会被展示为同一状态。
- Catalog 缺失时提交按钮不可用且原因准确。
- 正式页面不存在无业务必要的大段辅助文案。
- 受影响页面无持续控制台错误。

## 17. Pull Request 要求

PR 必须写明：

- 基线 commit。
- 风险与影响范围。
- 自动检查结果和 CI Run ID。
- 金样本和人工验收结果。
- 回滚方式。
- 未完成和延期内容。

一个稳定提交只表达一个清晰主题，代码、测试和文档同批闭环。

## 18. 阻断条件

存在以下任一情况，不得合并或发布：

- 任一 CI Job 失败或未执行。
- Kill Switch 命中后仍能创建新增风险订单。
- Kill Switch 写入没有幂等冲突检测或审计记录。
- 第一腿成交后没有显式残留敞口和腿间时间。
- 残留敞口未使用 Contract Multiplier。
- 多币种敞口被无依据净额抵消。
- 超过残留阈值后继续提交第二腿。
- RiskAction 重放会重复下单。
- 自动平仓绕过 TradeCommand。
- 平仓结果未知却标记 resolved。
- Batch failed 被误当作无风险。
- `result_unknown` 恢复重新提交原订单。
- FinancialFact 重放重复更新账务。
- Formal Position／PnL 无法重建。
- NAV 使用不同估值时点或缺失账户被补零。
- Stablecoin 被自动当作法币。
- 正式产品页面存在无业务必要的说明文案。
- active 文档与实现存在重大冲突。
- Live 开关、凭证、权限或回滚方案不清楚。

## 19. 后续升级

Phase 4B–4D 继续加入：

- 外部 Venue 主动查单、查成交、查持仓和查余额。
- 外部撤单与结果未知恢复。
- FinancialFact 自动导入和 Reconciliation Difference。
- Bybit Demo 与 MT5 Demo 端到端测试。
- 日终订单、成交、持仓、余额、PnL 和 NAV 对账。
- 断网、超时、Runtime 重启和单腿失败演练。
- Alembic 或等价迁移体系。
- 认证、RBAC、双人审批、CODEOWNERS 和生产密钥托管。