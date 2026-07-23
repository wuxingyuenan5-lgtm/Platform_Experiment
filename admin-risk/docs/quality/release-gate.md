# Platform V6 最小发布门槛

状态：`active`  
适用基线：`main / Platform V6`  
总体计划：`../../../docs/planning/V6-交易安全加固实施计划.md`  
当前阶段：`../../../docs/planning/V6-Phase4B-外部查询与对账差异.md`

## 1. 目的

建立低成本、可重复、可审计的工程门槛。涉及交易、账户、执行、风险、FinancialFact、PnL、NAV、Venue Query、Reconciliation 或部署的变更，不能只凭页面效果判断完成。

## 2. 自动检查

### 前端

```bash
cd admin-risk
pnpm sync:trading-tools
pnpm type:check
pnpm build
```

### Platform Backend

```bash
cd platform-backend
python -m ruff check app tests
python -m pytest
```

Phase 4B 严格 Gate 至少覆盖：

- `app/main.py`
- `app/trading.py`
- `app/trade_commands.py`
- `app/execution_batches.py`
- `app/execution_risk.py`
- `app/execution_exposure.py`
- `app/financial_facts.py`
- `app/venue_reconciliation.py`
- `tests/test_execution_risk.py`
- `tests/test_financial_facts.py`
- `tests/test_venue_reconciliation.py`
- Phase 1–3 全部安全、恢复和账务测试

### Execution Runtime

```bash
cd execution-runtime
python -m ruff check app tests
python -m pytest
```

严格 Gate 至少覆盖：

- `app/main.py`
- `app/journal.py`
- `app/models.py`
- `app/gateway.py`
- `app/fake_gateway.py`
- `app/venue_store.py`
- `tests/test_atomic_command_claim.py`
- `tests/test_runtime_journal.py`
- `tests/test_venue_query.py`

### GitHub Actions

- `main`、`hardening/**` 和面向 `main` 的 PR 必须触发 Platform CI。
- Backend、Runtime、Frontend 全部通过后才允许合并。
- 失败日志必须保留为短期 Artifact。
- README、START-HERE、Release Gate、Planning、Technical、API Spec 和 Changelog 变化必须触发 CI。
- 不允许强推 `main` 绕过检查。

## 3. TradeCommand 与 ExecutionBatch

- 正式写入口只有 TradeCommand 和 ExecutionBatch。
- 两者都必须有业务级幂等键。
- Strategy、active Binding、Account、Instrument、ContractSpecification 必须有效。
- 数量、数量步长、价格步长合法。
- Live 默认关闭。
- 每个 Batch Leg 都生成独立 TradeCommand。
- Batch 第一腿前完成全部 Catalog 预校验。
- 相同幂等键不同载荷返回 409。
- Deprecated `/trading/orders` 不得被新代码依赖。

## 4. Runtime 命令幂等

- Runtime 在 Gateway 副作用前原子抢占 command_id。
- 重复 Command 返回持久化事件。
- 已认领但尚无事件时返回 409，不重复调用 Gateway。
- Runtime 重启后 Journal 仍可恢复事件。
- 任何 Query API 不得调用 `submit_order`。

## 5. result_unknown 恢复

- `result_unknown` 不得直接重试原订单。
- 第一层恢复查询 Runtime Journal。
- 第二层恢复查询 Venue Order 与 External Fill。
- Runtime Journal 无事件时保持未知，直到外部查询给出证据。
- External Fill ID 必须作为稳定本地 Fill Event ID。
- External Fill 重放不得重复改变 Position、FinancialFact、PnL 或 NAV。
- 恢复后同步 Order 与 TradeCommand。
- 外部仍查不到时创建 `missing_external` Difference，不伪装为失败或取消。

## 6. Kill Switch 与 Execution Risk

- 支持 global、strategy、account Kill Switch。
- Batch 认领前与每条 Leg 执行前检查。
- 命中返回 423，且不能产生新 TradeCommand 或 Runtime 副作用。
- Batch 固化最大腿间延迟、最大残留名义敞口和失败处置策略。
- 残留风险先净 Contract Delta，再折算未匹配名义金额。
- 多单位或多币种不可比较时标记 `MIXED / incomplete`。
- `failed` 不等于风险解除。
- 正常 Batch 只有 residual=0 且 quality=complete 才能标记 `hedged`。
- 自动平仓和替代对冲必须通过 TradeCommand。
- RiskAction 重放不得重复下单。

## 7. Runtime Venue Query

必须提供明确、无副作用的：

```http
GET /venue/orders/by-platform/{platformOrderId}
GET /venue/orders/{externalOrderId}
GET /venue/fills
GET /venue/positions
GET /venue/balances
POST /venue/orders/{externalOrderId}/cancel
```

检查项：

- Snapshot 有 source、外部身份、Account、Instrument、时间和质量状态。
- Query 404 与网络错误不同。
- 空列表表示查询成功但无结果，不等于 Runtime 不可用。
- Cancel 使用独立幂等键。
- 已终态 Order 返回 `already_final`，不得称为新取消成功。
- unsupported 必须显式返回，不能包装为空仓或零余额。
- Fake Gateway 外部 ID 确定性并持久化到 Journal SQLite。
- Runtime TestClient 重启后 Fake Order、Fill、Position、Balance 仍可查询。

## 8. FinancialFact 导入

- External Order Snapshot → `external_order` Fact。
- External Fill → `trade_fill` Fact。
- External Position Snapshot → `position` Fact。
- External Balance Snapshot → `balance` Fact。
- Order/Position 时点快照身份必须包含 asOf。
- Fill 使用自然 External Fill ID。
- 同一事实重复导入返回原 Fact。
- 同一身份不同载荷返回 409。
- Position Snapshot 不得直接覆盖由 Fill 重建的 Formal Position。
- 缺少必要身份、时间、币种或 Instrument 时不得标记 complete。

## 9. Venue Reconciliation Run

```http
POST /api/v1/ops/venue-reconciliation/runs
GET  /api/v1/ops/venue-reconciliation/runs/{runId}
GET  /api/v1/ops/venue-reconciliation/runs/{runId}/differences
```

必须确认：

- 请求包含 `idempotencyKey`、StrategyInstance、Account、actor。
- Account 与 StrategyInstance active binding 有效。
- 相同幂等键同载荷返回原 Run。
- 相同幂等键不同载荷返回 409。
- Run 记录 source、status、各类 Snapshot Count、Fact Count、Difference Count 和时间。
- 查询或导入失败不能将 Run 标记 completed。
- 重复 Run 不重复记账。

## 10. Reconciliation Difference

支持：

- `missing_local`
- `missing_external`
- `quantity_mismatch`
- `price_mismatch`
- `currency_mismatch`
- `status_mismatch`

每个 Difference 必须保存：

- run_id 和稳定 difference_key。
- entity_type。
- local/external reference。
- local/external value JSON。
- `open / resolved / accepted`。
- resolution actor、reason、time。

约束：

- 差异不得通过无痕覆盖本地或外部值消失。
- 首次非 open 处置后，后续重复请求返回原结果。
- 处置动作写入 AuditEvent。
- `accepted` 表示已解释，不表示数值相等。

## 11. Formal Accounting

- FinancialFact 只新增，不提供业务更新和删除。
- Formal Position/PnL 能从事实完整重建。
- Trading PnL 使用 Quantity、Price、Direction、Contract Multiplier 和 FX。
- Funding、Swap、Fee、FX 与 Trading PnL 分项保存。
- Stablecoin 不自动等同法币。
- 缺失 FX 标记 incomplete。
- Formal NAV 对全部 active binding 使用同一 valuationTime。
- 缺失账户返回 missingAccountIds，不补零。
- 旧 PnL/NAV 兼容接口不得标记为正式账务。

## 12. 前端与产品界面

- 从 Backend 获取 Strategy、Binding、Account、Instrument 和 ContractSpecification。
- Catalog 不完整时禁用提交。
- Simulation、Demo、Live 明确区分。
- 缺失 Position、PnL、Risk、Venue 和 Difference 数据展示 `—` 或未知。
- 不展示无业务必要的开发说明、跳转机制、实现解释和联调备注。
- 必要提示短、准、就近；完整解释进入 Markdown。

## 13. 金样本

Phase 4B 至少保留：

1. Runtime timeout → result_unknown。
2. Journal 404 → Venue Order/Fill 恢复。
3. 恢复过程不调用 submit_order。
4. 重复 Venue Reconcile 不增加 Fill 与 FinancialFact。
5. Formal Position 由 External Fill 形成。
6. Position/Balance Snapshot 导入 Fact。
7. missing_local Difference。
8. Difference accepted 后重复处置不覆盖。
9. Run 幂等键载荷冲突返回 409。
10. Fake Venue 跨 Runtime 重启保持状态。
11. Fake Cancel 重复幂等，终态返回 already_final。

Phase 4A、Phase 3 和 Phase 1–2 金样本必须继续通过。

## 14. 审计

必须记录：

- TradeCommand、恢复和 Runtime identity 校验。
- Kill Switch、Risk Policy、Risk State、RiskAction。
- FinancialFact 入库、投影重建、Formal NAV。
- `venue_order_reconciled`。
- `venue_reconciliation_completed`。
- `reconciliation_difference_resolved`。

日志和响应不得泄露真实凭证。

## 15. 阻断条件

存在任一情况不得合并或发布：

- 任一 CI Job 失败或未执行。
- Query API 可能重新提交订单。
- result_unknown 恢复会重下原订单。
- External Fill 重放重复记账。
- External Snapshot 缺少身份或时间仍标记 complete。
- 外部与本地差异被无痕覆盖。
- Difference 没有 actor、reason 或处置时间。
- 已处置 Difference 可被重复请求改写。
- Runtime 不可用被解释为空仓或零余额。
- Cancel unsupported 被解释为成功。
- Kill Switch 命中后仍能创建新增风险。
- 自动平仓绕过 TradeCommand。
- Formal PnL/NAV 不能从事实核对。
- active Markdown 与实现冲突。
- Bybit/MT5 未真实完成 Demo 却被标记可用。
- Live 开关、凭证、权限或回滚方案不清楚。

## 16. 后续升级

Phase 4C–4D 加入：

- Bybit Demo 真实下单、撤单、查询、Funding。
- MT5 Demo Order/Deal、持仓、余额、Swap。
- Demo、Simulation、Live 账户与 Runtime 隔离。
- 日终调度、差异严重度、责任人、SLA 和报告。
- 断网、超时、Runtime 重启和单腿失败演练。
- 连续运行和零未解释差异验收。
- 认证、RBAC、双人审批和生产密钥托管。