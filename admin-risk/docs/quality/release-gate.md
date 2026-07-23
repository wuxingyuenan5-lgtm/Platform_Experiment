# Platform V6 最小发布门槛

状态：`active`  
适用基线：`main / Platform V6`  
总体计划：`../../../docs/planning/V6-交易安全加固实施计划.md`  
当前阶段：`../../../docs/planning/V6-Phase4C-受控实盘适配器.md`

## 1. 目的

建立可重复、可审计的工程与运营门槛。涉及交易、账户、执行、风险、Live Adapter、FinancialFact、PnL、NAV、Venue Query、Reconciliation 或部署的变更，不能只凭页面效果或“接口能调用”判断完成。

Phase 4C 区分：

- 工程验收：代码、离线 Provider Contract Tests、CI 和文档。
- 运营验收：真实账户只读、连续对账、最小仓位写入和 Kill Switch 演练。

工程验收通过不自动授予实盘写入权限。

## 2. 自动检查

### Frontend

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

严格 Gate 至少覆盖：

- `app/trade_commands.py`
- `app/trade_command_execution.py`
- `app/execution_batches.py`
- `app/execution_risk.py`
- `app/financial_facts.py`
- `app/venue_reconciliation.py`
- `app/live_venue_accounting.py`
- `tests/test_trade_command_live_runtime_payload.py`
- `tests/test_live_venue_accounting.py`
- Phase 1–4B 全部安全、恢复、账务和对账测试

### Execution Runtime

```bash
cd execution-runtime
python -m ruff check app tests
python -m pytest
```

严格 Gate 至少覆盖：

- `app/main.py`
- `app/models.py`
- `app/gateway.py`
- `app/gateway_factory.py`
- `app/gateway_errors.py`
- `app/bybit_mt5_gateway.py`
- `app/bybit_live_adapter.py`
- `app/mt5_live_adapter.py`
- `app/live_safety.py`
- `app/live_route_store.py`
- `app/secret_resolver.py`
- `tests/test_live_safety.py`
- `tests/test_bybit_live_adapter.py`
- `tests/test_mt5_live_adapter.py`
- Phase 1–4B Runtime 回归测试

### GitHub Actions

- `main`、`hardening/**` 和面向 `main` 的 PR 必须触发 Platform CI。
- Backend、Runtime、Frontend 全部通过后才允许合并。
- 失败日志保留短期 Artifact。
- README、START-HERE、Release Gate、Planning、Technical、API Spec 和 Changelog 变化必须触发 CI。
- 不允许强推 main 绕过检查。

## 3. TradeCommand 与 ExecutionBatch

- 正式写入口只有 TradeCommand 和 ExecutionBatch。
- 业务级幂等键必填。
- Strategy、active Binding、Account、Instrument、ContractSpecification 必须有效。
- 数量、价格和步长合法。
- Platform Live Gate 默认关闭。
- 每个 Batch Leg 生成独立 TradeCommand。
- StrategyInstance 身份必须传递到 Runtime。
- 相同幂等键不同载荷返回 409。
- Deprecated `/trading/orders` 不得作为 Live 写入口。

## 4. Runtime Command 幂等

- Runtime 在 Gateway 副作用前原子抢占 command_id。
- 重复 Command 返回持久化事件。
- 已认领但无事件时不重复调用 Gateway。
- Runtime 重启后 Journal 可恢复。
- LiveWriteClaim 在 SQLite 原子事务中认领。
- Command 载荷冲突拒绝。
- Query API 不得调用 submit_order。

## 5. Result Unknown

- 同步 ACK 不等于成交。
- Venue 明确拒绝与结果未知分开处理。
- 可能已到 Venue但无法确认时返回 502，使 Platform 标记 `result_unknown`。
- `result_unknown` 不得直接重下。
- 第一层查 Runtime Journal，第二层查 Venue Order 与 Fill/Deal。
- 外部仍查不到时生成 Difference。
- External Fill/Deal ID 必须作为稳定事实身份。

## 6. Kill Switch 与 Execution Risk

- Global、Strategy、Account Kill Switch 在 Batch 认领前和每腿执行前检查。
- 命中后不能产生新增风险。
- Batch 固化腿间延迟、残留名义敞口和失败处置策略。
- `failed` 不等于风险解除。
- 自动平仓和替代对冲必须通过 TradeCommand。
- RiskAction 重放不得重复下单。
- 风险状态、动作、操作人和原因进入 AuditEvent。

## 7. Live Runtime 双重门禁

写入必须同时满足：

1. Runtime `environment=live`。
2. Runtime `liveWriteEnabled=true`；默认 false。
3. Account 位于 allowlist。
4. StrategyInstance 位于 allowlist。
5. Symbol 位于 allowlist。
6. 正数 Reference Price 可用。
7. 单笔 Notional 不超限。
8. 单日累计 Notional 不超限。
9. Platform Live Gate、Kill Switch 和 Execution Risk 已通过。
10. Credential Ref、Account Route 和 Instrument Map 完整。

任一条件无法确认时 fail-closed。不得自动回退 Fake Gateway。

## 8. Account 与 Instrument 路由

- 一个 Account 只能映射一个 Live Adapter。
- 未映射 Account 拒绝 Query 和 Command。
- Bybit Symbol 和 MT5 Symbol 必须显式映射到 Backend Instrument ID。
- 未映射 Instrument 的 Position、Deal、Funding、Swap 或 Fee 不得标记 complete。
- Query 不得把未映射数据静默丢弃后声称完整；Import 响应必须列出 skippedExternalIds。

## 9. Bybit Live Adapter

必须确认：

- 使用 V5 Unified Trading API。
- `orderLinkId` 由 Platform Order ID 确定性派生且符合长度限制。
- place-order ACK 只生成 acknowledged，不生成虚假 Fill。
- Open Orders、Order History 和 Executions 可以恢复最终状态。
- Execution `execId` 用作 Fill 自然身份。
- Position、Wallet 和 Transaction Log 查询失败不返回伪造零值。
- Funding 与 Fee 分项映射，Fee 使用带符号负贡献。
- API Key 和 Secret 不进入响应、日志和审计。

## 10. MT5 Live Adapter

必须确认：

- 非 Windows 或无可用 Terminal 时 fail-closed。
- 使用配置的真实登录账号，account_info login 必须匹配。
- 下单前执行 `order_check`。
- 写入使用 `order_send`。
- Order、Deal、Position 和 Account 查询使用官方接口。
- Magic Number、Comment、Order/Deal/Position Ticket 可追溯。
- Deal Ticket 用作 Fill、Swap 和 Fee 自然身份。
- Swap、Commission 和 Fee 从外部字段导入，不倒推。
- Password 和 Server 不进入响应、日志和审计。

## 11. Runtime Capability

```http
GET /gateway/capabilities
```

必须返回：

- Gateway 与 Environment。
- 全局 Live Write 是否开启。
- 每个 Adapter 的 configured、operational、writeEnabled。
- Account IDs、Capabilities、Missing Requirements。

不得返回任何 Secret 值。configured 与 operational 必须区分；依赖或环境不可用时不能标记 operational。

## 12. Venue Query 与 Economic Event

```http
GET /venue/orders/by-platform/{platformOrderId}
GET /venue/orders/{externalOrderId}
GET /venue/fills
GET /venue/positions
GET /venue/balances
GET /venue/economic-events
POST /venue/orders/{externalOrderId}/cancel
```

检查项：

- Query 与 Command 分离。
- 404、空结果、网络错误、配置错误和结果未知含义不同。
- Snapshot 有 source、外部 ID、Account、Instrument、时间和质量状态。
- Cancel 也受 Runtime Live Gate 和 allowlist 约束。
- Bybit Funding/Fee 与 MT5 Swap/Fee 使用稳定 External Event ID。

## 13. FinancialFact 与 Economic Event Import

```http
POST /api/v1/ops/live-economic-events/import
```

- 请求有 idempotencyKey、StrategyInstance、Account、actor。
- 同一导入幂等键同载荷返回原结果。
- 相同幂等键不同载荷返回 409。
- Funding、Swap、Fee 写入不可变 FinancialFact。
- External Event ID 用作事实自然身份。
- 未映射 Instrument 进入 skippedExternalIds。
- 重复导入不重复改变 Formal PnL。
- 导入动作写入 AuditEvent。

## 14. Venue Reconciliation

- External Order、Fill/Deal、Position 和 Balance 进入 FinancialFact 或 Difference。
- Position Snapshot 不直接覆盖由 Fill 重建的 Formal Position。
- 外部与本地差异不得无痕覆盖。
- Difference 保存 local/external value、状态、操作人、原因和时间。
- 首次处置记录不可被重复请求改写。

## 15. Formal Accounting

- FinancialFact 只新增。
- Formal Position/PnL 可从事实重建。
- Trading、Funding、Swap、Fee、FX 分项。
- Contract Multiplier、Currency、Unit 和 FX 显式。
- Stablecoin 不自动等同法币。
- Formal NAV 使用统一 valuationTime。
- 缺失 Account、FX 或 Instrument Map 不补零。

## 16. 前端与产品界面

- Simulation 与 Live 明确区分。
- Catalog 或 Gateway Capability 不完整时禁用提交。
- Live Write 关闭时不得显示为可执行。
- 缺失 Position、PnL、Risk、Venue 和 Difference 展示 `—` 或未知。
- 产品页面不展示开发说明、实现解释或联调备注。

## 17. 工程金样本

至少保留：

1. LiveWrite 默认关闭。
2. Account、Strategy、Symbol allowlist 拒绝。
3. 单笔和单日名义金额限额。
4. 重复 Live Command 不重复累计 Notional。
5. Bybit ACK 不生成虚假 Fill。
6. Bybit orderLinkId、Execution、Funding 和 Fee 映射。
7. MT5 order_check/order_send、Magic/Comment/Ticket 映射。
8. MT5 Deal、Swap 和 Fee 映射。
9. StrategyInstance 跨 Platform/Runtime 边界保留。
10. Economic Event 重复导入不重复记账。
11. 既有 Phase 1–4B 金样本全部通过。

## 18. 运营验收

必须在真实账户上完成并人工留痕：

- Bybit 只读订单、成交、持仓、余额、Funding。
- MT5 只读 Order、Deal、Position、Balance、Swap。
- 连续多个日终周期无未解释差异。
- 最小允许仓位受控下单、撤单、查询和事实导入。
- Kill Switch 和人工接管演练。

运营验收前 `liveWriteEnabled=false`。

## 19. 阻断条件

任一情况存在，不得合并、开启 Live Write 或扩大实盘：

- 任一 CI Job 失败或未执行。
- Live Write 默认开启。
- Platform 或 Runtime 任一道门禁可被绕过。
- Account、Strategy、Symbol 或 Notional 未 fail-closed。
- 同步 ACK 被视为成交。
- `result_unknown` 会重下原订单。
- Query 失败被解释为空仓或零余额。
- 一个 Account 映射多个 Adapter。
- Secret 出现在响应、日志、审计或仓库。
- Funding、Swap、Fee 重复记账。
- 未映射 Instrument 被静默当作完整数据。
- Difference 被无痕覆盖。
- active Markdown 与实现冲突。
- 未完成真实账户运营验收却标记 Live Operational。

## 20. 后续升级

Phase 4D：日终自动调度、Difference 严重度、责任人、SLA、报告、断网/重启演练和连续运行验收。认证、RBAC、双人审批与生产密钥托管仍需独立建设。