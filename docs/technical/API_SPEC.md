# Platform V6 API Specification

状态：`active`  
Platform API Prefix：`/api/v1`  
Platform 组合入口：`platform-backend/app/main.py`  
Runtime 根地址：`http://127.0.0.1:8100`  
当前阶段：`docs/planning/V6-Production-Gate-身份权限与实盘会话.md`  
安全合同：`docs/technical/AUTH_RBAC_LIVE_SESSIONS.md`

## 1. 服务边界

| 服务 | 默认地址 | 权威职责 |
|---|---|---|
| Platform Backend | `http://127.0.0.1:8000` | Auth、RBAC、Live Session、Strategy、Account、Command、Order、Risk、FinancialFact、Reconciliation、EOD、Formal Accounting |
| Execution Runtime | `http://127.0.0.1:8100` | Journal、Runtime Live Safety、Account Router、Venue Query、外部副作用隔离 |
| Frontend | `http://127.0.0.1:5173` | 查询、交互和命令发起；不持有 Venue Secret |

公开健康探针：

```http
GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8100/health
```

除不含业务数据的 `/health` 外，Live Platform API 进入认证边界。

## 2. Authentication

Live 请求：

```http
Authorization: Bearer <runtime-injected-token>
X-Request-ID: <client-request-id>
```

规则：

- `VG_ENVIRONMENT=live` 时必须使用 `VG_AUTH_MODE=api_key`。
- 服务端配置 Credential 的 `tokenSha256`，不保存或返回原始 Token。
- 匿名、无效 Credential、停用 Credential、未知 Role 和 development auth 全部 fail-closed。
- 响应回传 `X-Request-ID`；认证成功时可以回传不敏感的 User ID 标识。
- User、Role、Credential ID、Request ID、Source IP（可用时）和结果进入安全审计。
- Request Body 中的 actor、reviewer 等字段不能覆盖认证 Principal。

非 Live 开发环境允许显式 Development Identity，用于 Simulation 和 CI；该旁路在 Live 环境无效。

## 3. RBAC

| Role | 主要权限 |
|---|---|
| viewer | 普通业务只读 |
| researcher | 普通只读、研究运行 |
| trader | TradeCommand、ExecutionBatch、Live Session 申请 |
| risk_officer | Kill Switch、RiskAction、Difference/EOD Review、Live Session 批准与撤销 |
| operations | Venue Import、Reconciliation、EOD 执行 |
| admin | 管理权限；不豁免 Applicant/Approver 分离 |

Permission 默认拒绝。普通 viewer 不能读取 Credential Reference、AuditEvent，不能执行交易、风险、对账或批准操作。

## 4. LiveTradingSession

```http
POST /api/v1/live-trading/sessions
GET  /api/v1/live-trading/sessions
POST /api/v1/live-trading/sessions/{sessionId}/approve
POST /api/v1/live-trading/sessions/{sessionId}/revoke
```

申请示例：

```json
{
  "idempotencyKey": "minimum-live-window-001",
  "sessionType": "minimum_size_acceptance",
  "strategyInstanceId": "strategy-live-funding",
  "accountId": "account-live-bybit",
  "symbols": ["XAUTUSDT"],
  "sides": ["buy", "sell"],
  "orderTypes": ["limit"],
  "startsAt": "2026-07-24T09:00:00+08:00",
  "endsAt": "2026-07-24T10:00:00+08:00",
  "maxOrderNotional": "100",
  "maxDailyNotional": "200",
  "readOnlyVerifiedAt": "2026-07-24T08:30:00+08:00",
  "evidenceReference": "ops://readonly-preflight/20260724",
  "reason": "minimum-size controlled live acceptance"
}
```

语义：

- Applicant 来自认证 Principal，不由客户端指定。
- trader/admin 可以申请；risk_officer/admin 可以批准。
- Applicant 与 Approver 必须不同，admin 也不能自批。
- Approval 绑定不可变 Payload Hash；修改范围必须新建 Session。
- Session 固定 Strategy、Account、Symbol、Side、Order Type、时间和额度。
- Kill Switch、Open/Accepted Difference、重叠 Approved Session、超过平台绝对限额、不合格 EOD 或未批准 Scale Change 阻断批准。
- revoke 不可逆；过期 Session 自动失效。

## 5. Live Session Claim

Claim 没有独立公共 API。正式 Live Command 在写入 Order 和调用 Runtime 前由 Platform 内部完成：

```text
Authentication
→ RBAC
→ Account/Instrument Safety
→ Platform Live Gate
→ LiveTradingSession Scope
→ SQLite BEGIN IMMEDIATE
→ Per-order + Daily Notional Claim
→ Order Insert
→ Runtime Live Gate
```

约束：

- 必须找到一个且仅一个有效 Approved Session。
- Command 的 Strategy、Account、Symbol、Side 和 Order Type 必须完全匹配。
- 当前 Live Market Order 无明确 Reference Price 时 fail-closed。
- Claim 以 Command ID 幂等；相同 ID 不同载荷返回 409。
- SQLite `BEGIN IMMEDIATE` 在读取累计额度前取得写锁，防止并发 Command 共同穿透单日限额。

## 6. Catalog

```http
GET /api/v1/strategies/definitions
GET /api/v1/strategies/instances
GET /api/v1/strategies/instances/{strategyInstanceId}
GET /api/v1/strategies/instances/{strategyInstanceId}/accounts
GET /api/v1/accounts
GET /api/v1/accounts/{accountId}
GET /api/v1/instruments
GET /api/v1/instruments/{instrumentId}
```

TradeCommand、ExecutionBatch、RiskAction、FinancialFact、Live Adapter 映射和 EOD Report 必须使用 Backend Catalog。客户端不得覆盖 Quantity Unit、Settlement Currency 和 Contract Multiplier。

## 7. TradeCommand

```http
POST /api/v1/trading/commands
GET  /api/v1/trading/commands/{tradeCommandId}
```

```json
{
  "idempotencyKey": "client-command-001",
  "strategyInstanceId": "strategy-funding-live",
  "accountId": "account-live-bybit",
  "instrumentId": "instrument-xaut-usdt",
  "symbol": "XAUTUSDT",
  "side": "buy",
  "orderType": "limit",
  "quantity": "0.01",
  "price": "2400"
}
```

服务端校验 Strategy、active Binding、Account、Instrument、ContractSpecification、数量、价格步长、Platform Live Gate、Kill Switch、Authentication、RBAC 和 LiveTradingSession。正式 TradeCommand 将 StrategyInstance 身份传到 Runtime。

## 8. ExecutionBatch 与风险处置

```http
POST /api/v1/trading/execution-batches
GET  /api/v1/trading/execution-batches
GET  /api/v1/trading/execution-batches/{batchId}
GET  /api/v1/trading/execution-batches/{batchId}/risk
GET  /api/v1/trading/execution-batches/{batchId}/risk-actions
POST /api/v1/trading/execution-batches/{batchId}/risk-actions
```

执行顺序：Catalog → Authentication/RBAC → Kill Switch → Batch 原子认领 → Risk Policy 快照 → 每腿 TradeCommand 与 Session Claim → 腿间延迟/残留风险检查 → RiskAction。

## 9. Order、Fill 与未知结果

```http
GET  /api/v1/trading/orders
GET  /api/v1/trading/orders/{orderId}
GET  /api/v1/trading/fills
POST /api/v1/trading/orders/{orderId}/reconcile
POST /api/v1/trading/orders/{orderId}/venue-reconcile
```

- Journal Reconcile 只查询 Runtime Journal。
- Venue Reconcile 查询外部 Order 和 Fill/Deal。
- 两者都不得重新提交原订单。
- Runtime 网络结果不确定时，Platform 保持 `result_unknown`。
- `POST /api/v1/trading/orders` 仅为 deprecated 兼容入口，不得用于 Live。

## 10. Kill Switch 与 Execution Risk

```http
GET /api/v1/risk/kill-switches/{scopeType}/{scopeId}
PUT /api/v1/risk/kill-switches/{scopeType}/{scopeId}
GET /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
PUT /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
```

Scope：`global/*`、`strategy/{strategyInstanceId}`、`account/{accountId}`。修改需要 risk_officer/admin 权限，Body Actor 必须匹配 Principal。Kill Switch 在 Session Approval、Session Claim、Batch 和每腿执行前检查。

## 11. Runtime Gateway Capability 与 Query

```http
GET /gateway/capabilities
GET /venue/orders/by-platform/{platformOrderId}
GET /venue/orders/{externalOrderId}
GET /venue/fills?accountId=...&externalOrderId=...&platformOrderId=...
GET /venue/positions?accountId=...
GET /venue/balances?accountId=...
GET /venue/economic-events?accountId=...&instrumentId=...&eventType=...
POST /venue/orders/{externalOrderId}/cancel
```

Capability 不返回 Secret。查询失败与空结果不同；Runtime 不可用不得被解释为空仓或零余额。Query API 不得隐式提交订单。

## 12. Runtime Command Contract

```http
POST /commands/orders
```

```json
{
  "command_id": "trade-command-id",
  "platform_order_id": "platform-order-id",
  "strategy_instance_id": "strategy-instance-id",
  "account_id": "account-id",
  "instrument_id": "instrument-id",
  "symbol": "XAUTUSDT",
  "side": "buy",
  "order_type": "limit",
  "quantity": "0.01",
  "price": "2400",
  "reduce_only": false
}
```

Runtime 在调用 Venue 前检查 Command Journal 和独立 Live Safety。确定性门禁或 Venue 拒绝返回 `order_rejected`；可能已到 Venue 但无法确认时返回 502，使 Platform 进入 `result_unknown`。

## 13. Runtime Live Safety

正式模板：`execution-runtime/.env.live.example`

```text
VG_RUNTIME_ENVIRONMENT=live
VG_RUNTIME_GATEWAY_NAME=bybit_mt5
VG_RUNTIME_JOURNAL_PATH=./data/live_runtime_journal.db
VG_RUNTIME_LIVE_WRITE_ENABLED=false
VG_RUNTIME_LIVE_ACCOUNT_ALLOWLIST=
VG_RUNTIME_LIVE_STRATEGY_ALLOWLIST=
VG_RUNTIME_LIVE_SYMBOL_ALLOWLIST=
VG_RUNTIME_LIVE_MAX_ORDER_NOTIONAL=0
VG_RUNTIME_LIVE_MAX_DAILY_NOTIONAL=0
```

Runtime Live Write 默认关闭，且独立于 Platform Authentication、Session 和 Live Gate。任一门禁失败不得自动回退 Fake Gateway。

## 14. Bybit 与 MT5 Live 语义

### Bybit

- V5 Unified Trading API。
- Platform Order ID 确定性派生唯一 `orderLinkId`。
- Place-order ACK 只生成 acknowledged，不直接生成 Fill。
- 最终状态通过 Open Orders、Order History 和 Executions 查询。
- Execution `execId` 用作 Fill 自然身份。
- Transaction Log 映射 Funding 和 Fee。

### MT5

- 仅支持 Windows Terminal 或测试注入 Provider。
- 下单前 `order_check`，写入使用 `order_send`。
- 查询使用 `orders_get`、`history_orders_get`、`history_deals_get`、`positions_get`、`account_info`。
- Magic、Comment、Order Ticket、Deal Ticket 和 Position Ticket 用于追溯。
- Deal 中 Swap、Commission 和 Fee 进入 Economic Event。
- Terminal 未连接、登录账号不匹配或权限不足时 fail-closed。

Secret 值不得写入仓库、日志、审计、Markdown、截图或 API 响应。

## 15. Live Economic Event Import

```http
POST /api/v1/ops/live-economic-events/import
```

- 需要 operations/admin 权限。
- Runtime Query 返回 Funding、Swap、Fee。
- External Event ID 用作 FinancialFact 自然身份。
- 重复 Import 返回原结果；同键不同载荷返回 409。
- 缺 Instrument 映射的事件进入 `skippedExternalIds`。

## 16. Venue Reconciliation

```http
POST /api/v1/ops/venue-reconciliation/runs
GET  /api/v1/ops/venue-reconciliation/runs/{runId}
GET  /api/v1/ops/venue-reconciliation/runs/{runId}/differences
POST /api/v1/ops/venue-reconciliation/differences/{differenceId}/resolve
```

运行需要 operations/admin；Difference Review 需要 risk_officer/admin。Difference Type：`missing_local`、`missing_external`、`quantity_mismatch`、`price_mismatch`、`currency_mismatch`、`status_mismatch`。`accepted` 不表示数据一致，Open 与 Accepted 均阻断 Session Approval 和扩大实盘。

## 17. EOD Reconciliation

```http
POST /api/v1/ops/eod-reconciliation/reports
GET  /api/v1/ops/eod-reconciliation/reports
GET  /api/v1/ops/eod-reconciliation/reports/{reportId}
POST /api/v1/ops/eod-reconciliation/reports/{reportId}/review
```

- EOD 执行需要 operations/admin；Review 需要 risk_officer/admin。
- Business Date、IANA Timezone、Valuation Time、Owner 和 Due At 必须显式。
- 订单范围为业务日期窗口，加上估值时点仍未终结的历史订单。
- 编排 Position、Balance、Funding、Swap、Fee、FinancialFact、Formal PnL 和 Formal NAV。
- 外部失败进入 errors，不能生成虚假 complete。
- Scale Gate 默认 blocked；只有 clean report 可以 `approved_same_limits`。
- Review Actor 必须匹配认证 Principal，且不会自动提高限额或开启写入。

## 18. FinancialFact 与 Formal Accounting

```http
POST /api/v1/financial-facts
GET  /api/v1/financial-facts
POST /api/v1/strategies/instances/{strategyInstanceId}/financials/rebuild
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-positions
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-pnl
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots/run
```

FinancialFact 支持 `external_order`、`trade_fill`、`deal`、`funding`、`swap`、`fee`、`balance`、`position`、`fx`。Formal PnL 分为 Trading、Funding、Swap、Fee、FX 和 Total。

## 19. 审计与通用规则

安全与生产门禁审计至少包括：

- authentication accepted/rejected。
- authorization rejected。
- actor mismatch。
- live trading session requested/approved/revoked/expired/claimed。
- kill switch changed。
- risk action executed。
- venue reconciliation and difference review。
- EOD completed/reviewed。

通用规则：

- JSON 金融数值使用十进制字符串。
- 时间使用带时区 ISO 8601。
- Query 与 Command 分离。
- ACK 与 Fill 分离。
- `result_unknown` 与失败不同。
- 缺失值与零不同。
- Stablecoin 不自动等同法币。
- 外部与本地冲突形成 Difference。
- Platform 与 Runtime Live Write 默认关闭。
- EOD Report 不自动修改外部仓位、解决差异、提高限额或开启写入。
- 工程验收不等于真实账户运营验收。