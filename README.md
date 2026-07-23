# Variable-Global 本地工作台

这是一个面向内部投研、策略执行、风险控制和账务核对的交易平台。当前工程原则是：先建立交易安全、执行恢复、正式账务和生产门禁，再扩展新策略与页面。

## 当前权威基线

- 正式分支：`main`
- Phase 1–4D：已完成工程验收
- Production Gate 5A/5B：身份认证、RBAC、双人 `LiveTradingSession`，已通过 PR `#23`
- 当前实施：Production Gate 5C——SecretProvider、密钥轮换元数据与全链路脱敏
- 当前 Issue：`#24`
- 当前 PR：`#25`
- 总 Production Gate：Issue `#22`
- 总跟踪：Issue `#2`
- 当前计划：`docs/planning/V6-Production-Gate-密钥托管与脱敏.md`
- 当前技术合同：`docs/technical/SECRET_PROVIDER_AND_REDACTION.md`
- 小资金实盘验收：`docs/operations/V6-小资金实盘验收手册.md`

Bybit 与 MT5 的最终运营验收优先使用真实账户、小资金和最小允许仓位。工程验收、真实账户存在或 Secret 可解析都不等于自动实盘获批；Platform 与 Runtime Live Write 仍默认关闭。

## 先看这里

| 主题 | 文档 |
|---|---|
| 总体路线 | `docs/planning/V6-交易安全加固实施计划.md` |
| 当前 5C 计划 | `docs/planning/V6-Production-Gate-密钥托管与脱敏.md` |
| SecretProvider 与脱敏 | `docs/technical/SECRET_PROVIDER_AND_REDACTION.md` |
| 认证与双人审批 | `docs/technical/AUTH_RBAC_LIVE_SESSIONS.md` |
| 实盘 EOD | `docs/technical/EOD_RECONCILIATION.md` |
| Live Adapter | `docs/technical/LIVE_VENUE_ADAPTERS.md` |
| Venue 对账 | `docs/technical/VENUE_RECONCILIATION.md` |
| 执行风险 | `docs/technical/EXECUTION_RISK_CONTROLS.md` |
| 正式账务 | `docs/technical/FINANCIAL_FACTS.md` |
| API 总表 | `docs/technical/API_SPEC.md` |
| 发布门槛 | `admin-risk/docs/quality/release-gate.md` |
| 人工入口 | `admin-risk/docs/START-HERE.md` |

## 服务与默认模式

| 服务 | 默认地址 | 职责 |
|---|---|---|
| Frontend | `http://127.0.0.1:5173` | 产品交互，不持有 Venue Secret |
| Platform Backend | `http://127.0.0.1:8000` | Auth、RBAC、Session、Command、Risk、Fact、PnL、EOD |
| Execution Runtime | `http://127.0.0.1:8100` | Journal、Gateway、Secret Resolution、Venue Query 与外部副作用 |

默认：

```text
TradingMode=simulation
Gateway=fake
Platform Live Write=false
Runtime Live Write=false
```

Live Runtime 必须使用独立 Environment、Journal、Account、Credential Ref 和 Platform Database。

## Production Gate 5A/5B

Live API 使用：

```http
Authorization: Bearer <host-injected-token>
```

- Live 环境只允许 `api_key` 认证模式。
- Token 只配置 SHA-256 哈希，不保存原始值。
- 最小角色：viewer、researcher、trader、risk_officer、operations、admin。
- 权限默认拒绝。
- actor、reviewer 等身份必须匹配认证 Principal。
- trader/admin 申请实盘会话，独立 risk_officer/admin 批准。
- admin 也不能自批。
- 会话固定 Strategy、Account、Symbol、Side、Order Type、时间和额度。
- Kill Switch、历史差异、不合格 EOD、重叠会话和超限阻断批准。
- Live Command 在进入 Runtime 前原子认领会话额度。

实盘会话 API：

```http
POST /api/v1/live-trading/sessions
GET  /api/v1/live-trading/sessions
POST /api/v1/live-trading/sessions/{sessionId}/approve
POST /api/v1/live-trading/sessions/{sessionId}/revoke
```

## Production Gate 5C

正式 Secret Reference：

```text
secret://environment/<secret-name>
secret://windows-credential-manager/<secret-name>
```

旧 `secret://<secret-name>` 仅保留迁移兼容，并标记为 legacy。新配置必须显式指定 Provider。

### Environment Provider

示例：

```text
secret://environment/bybit-live-001
VG_SECRET_BYBIT_LIVE_001_API_KEY
VG_SECRET_BYBIT_LIVE_001_SECRET
VG_SECRET_BYBIT_LIVE_001_VERSION
```

### Windows Credential Manager Provider

示例：

```text
secret://windows-credential-manager/bybit-live-001
VariableGlobal/bybit-live-001/API_KEY
VariableGlobal/bybit-live-001/SECRET
VariableGlobal/bybit-live-001/VERSION
```

- `inspect` 只返回 Provider、Version、字段存在性和缺失字段。
- `resolve` 仅在 Runtime Gateway 内部调用。
- 未知 Provider、非 Windows 调用 Windows Provider、依赖缺失和字段缺失全部 fail-closed。
- Secret 值不得进入 API、日志、AuditEvent、数据库、Markdown、截图或对话。

Rotation Metadata API：

```http
POST /api/v1/security/credential-rotations
GET  /api/v1/security/credential-rotations
```

Rotation 只记录 Reference、Provider、Version、时间、操作人、原因和幂等哈希，不保存旧值或新值。

Repository Secret Scan：

```powershell
python .\scripts\scan-secrets.py
```

## 正式交易与风险入口

```http
POST /api/v1/trading/commands
POST /api/v1/trading/execution-batches
POST /api/v1/trading/orders/{orderId}/reconcile
POST /api/v1/trading/orders/{orderId}/venue-reconcile
GET  /api/v1/risk/kill-switches/{scopeType}/{scopeId}
PUT  /api/v1/risk/kill-switches/{scopeType}/{scopeId}
POST /api/v1/trading/execution-batches/{batchId}/risk-actions
```

底线：

- 正式交易只经过 TradeCommand 或 ExecutionBatch。
- `result_unknown` 只查询恢复，不重下。
- 每条 Batch Leg 生成独立 TradeCommand。
- Kill Switch 在会话批准、Command Claim、Batch 和每腿执行前检查。
- Bybit ACK 与 MT5 Order 结果不等同于 Fill/Deal。
- 外部与本地冲突形成 Reconciliation Difference，不无痕覆盖。

## 外部查询、事实和 EOD

Runtime Query：

```http
GET /gateway/capabilities
GET /venue/orders/by-platform/{platformOrderId}
GET /venue/orders/{externalOrderId}
GET /venue/fills
GET /venue/positions
GET /venue/balances
GET /venue/economic-events
```

Platform：

```http
POST /api/v1/ops/live-economic-events/import
POST /api/v1/ops/venue-reconciliation/runs
POST /api/v1/ops/eod-reconciliation/reports
POST /api/v1/ops/eod-reconciliation/reports/{reportId}/review
```

- External Order、Fill/Deal、Position、Balance、Funding、Swap、Fee 进入不可变 FinancialFact。
- Formal Position/PnL 可以从事实重建。
- Formal NAV 使用统一估值时点。
- Open/Accepted Difference、Skipped Event、Missing Account、Incomplete PnL 或 Runtime Error 阻断扩大实盘。
- EOD Review 不自动提高限额或开启 Live Write。

## 本地运行

前端：

```powershell
cd admin-risk
$env:VITE_PLATFORM_API_BASE_URL="http://127.0.0.1:8000/api/v1"
pnpm vite --host 127.0.0.1 --port 5173
```

Platform Backend：

```powershell
cd platform-backend
python -m uvicorn app.main:app --reload --port 8000
```

Execution Runtime：

```powershell
cd execution-runtime
python -m uvicorn app.main:app --reload --port 8100
```

## 稳定提交门槛

```powershell
python .\scripts\scan-secrets.py

cd admin-risk
pnpm type:check
pnpm build

cd ..\platform-backend
python -m ruff check app tests
python -m pytest

cd ..\execution-runtime
python -m ruff check app tests
python -m pytest
```

## 工程原则

1. Live 环境匿名、development auth、未知权限和未知 Provider 全部 fail-closed。
2. Applicant 与 Approver 必须分离。
3. Platform 与 Runtime Live Gate 独立且默认关闭。
4. 所有外部副作用在幂等认领之后发生。
5. Session、Runtime 和平台限额同时生效。
6. Query 与 Command 分离；ACK 与 Fill 分离。
7. Secret 值只在 Runtime Gateway 内部短暂使用。
8. Rotation 只记录元数据，不保存历史明文。
9. 外部差异不得无痕覆盖。
10. 缺失数据不得伪装为零。
11. 每个真实测试日必须形成 EOD Report。
12. 代码、测试、CI、计划、技术合同、API Spec、Release Gate 和 Changelog 同批留痕。
13. 未通过 CI 的 PR 不得合入 main。

## 当前发布边界

5C 工程完成后仍不自动开启实盘。受控 Windows 主机必须另行完成 Credential Manager 配置、只读连接、一次版本轮换、Runtime 重启、最小仓位双人审批测试和 EOD。Production Gate 5D 的监控、告警、调度、备份与恢复尚未完成前，不得扩大资金、仓位、品种或自动化频率。
