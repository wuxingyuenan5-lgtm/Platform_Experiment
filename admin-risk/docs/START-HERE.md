# 人工阅读入口

状态：`active`  
产品基线：Platform V6  
架构版本：Platform V6 Simplified  
适用分支：`main`  
当前实施：Production Gate 5A/5B——身份认证、RBAC、双人实盘会话  
文档层级：人工阅读入口

继续工程实施先看：

1. `../../docs/planning/V6-交易安全加固实施计划.md`
2. `../../docs/planning/V6-Production-Gate-身份权限与实盘会话.md`
3. `../../docs/technical/AUTH_RBAC_LIVE_SESSIONS.md`
4. `../../docs/operations/V6-小资金实盘验收手册.md`
5. `quality/release-gate.md`

## 1. 当前一句话结论

```text
Phase 1–3：交易安全、命令恢复与可重建正式账务，已完成
+
Phase 4A–4D：Kill Switch、Venue Query、Bybit/MT5 实盘适配器与 EOD，已完成工程验收
+
Production Gate 5A：Live 身份认证与 default-deny RBAC，已实现
+
Production Gate 5B：双人 LiveTradingSession 与并发安全额度认领，已实现
+
Production Gate 5C/5D：生产密钥托管、监控、告警、备份和恢复，待实施
```

Bybit 与 MT5 的最终测试使用真实账户的小资金和最小允许仓位，不把 Demo 当作主要验收环境。但 Platform 与 Runtime Live Write 默认关闭；真实账户运营验收、生产密钥治理、监控恢复和连续清洁 EOD 未完成前，不得扩大实盘。

## 2. 优先阅读

1. `../../docs/planning/V6-Production-Gate-身份权限与实盘会话.md`
2. `../../docs/technical/AUTH_RBAC_LIVE_SESSIONS.md`
3. `../../docs/planning/V6-交易安全加固实施计划.md`
4. `../../docs/operations/V6-小资金实盘验收手册.md`
5. `../../docs/planning/V6-Phase4D-实盘日终对账与运营门禁.md`
6. `../../docs/technical/EOD_RECONCILIATION.md`
7. `../../docs/planning/V6-Phase4C-受控实盘适配器.md`
8. `../../docs/technical/LIVE_VENUE_ADAPTERS.md`
9. `../../docs/technical/API_SPEC.md`
10. `quality/release-gate.md`

## 3. 当前工程优先级

| 顺序 | 主题 | 状态 |
|---|---|---|
| 1 | Fail-closed、Runtime 幂等、CI、文档留痕 | 已完成 |
| 2 | TradeCommand、ExecutionBatch、Journal/Venue 恢复 | 已完成 |
| 3 | FinancialFact、Formal PnL 与统一估值 NAV | 已完成 |
| 4 | Kill Switch、残留敞口、Bybit/MT5 Live Adapter、EOD | 已完成工程验收 |
| 5 | Authentication、Principal、RBAC | 已实现，PR #23 验收中 |
| 6 | 双人 LiveTradingSession、原子额度认领 | 已实现，PR #23 验收中 |
| 7 | SecretProvider、密钥轮换、全链路脱敏 | 待实施 |
| 8 | 监控、告警、调度、备份与恢复 | 待实施 |
| 9 | 真实账户只读、最小仓位和连续 EOD | 待人工执行 |
| 10 | 新策略和金融AI功能 | 暂缓 |

## 4. Production Authentication

Live 请求：

```http
Authorization: Bearer <runtime-injected-token>
```

平台只配置 Token SHA-256，不保存或返回原始 Token。Live 环境只允许 `api_key` 模式；匿名、无效 Credential、停用 Credential 和 development identity 全部拒绝。`/health` 是唯一不含业务数据的公开探针。

最小角色：

- viewer：普通查询。
- researcher：研究运行。
- trader：交易命令和实盘会话申请。
- risk_officer：Kill Switch、风险动作、差异/EOD 复核、会话批准和撤销。
- operations：事实导入、对账和 EOD 执行。
- admin：管理权限，但不能绕过双人自批限制。

请求中的 actor、reviewer 等身份必须与认证 Principal 一致，不能由请求体冒充。

## 5. LiveTradingSession

```http
POST /api/v1/live-trading/sessions
GET  /api/v1/live-trading/sessions
POST /api/v1/live-trading/sessions/{sessionId}/approve
POST /api/v1/live-trading/sessions/{sessionId}/revoke
```

底线：

- trader/admin 申请，独立 risk_officer/admin 批准。
- Applicant 与 Approver 必须不同；admin 也不能自批。
- 会话固定 StrategyInstance、Account、Symbol、Side、Order Type、时间、单笔和单日限额。
- Kill Switch、Open/Accepted Difference、重叠会话、超过平台绝对限额或不合格 EOD 阻断批准。
- Live Command 必须在写入 Order 和调用 Runtime 前认领唯一 Approved Session。
- Claim 使用 Command ID 幂等，载荷冲突返回 409。
- SQLite `BEGIN IMMEDIATE` 串行化并发认领，避免并发命令穿透单日限额。
- 撤销和过期会话立即失效。

## 6. 正式交易、风险与 EOD 入口

```http
POST /api/v1/trading/commands
POST /api/v1/trading/execution-batches
POST /api/v1/trading/orders/{orderId}/reconcile
POST /api/v1/trading/orders/{orderId}/venue-reconcile
GET  /api/v1/risk/kill-switches/{scopeType}/{scopeId}
PUT  /api/v1/risk/kill-switches/{scopeType}/{scopeId}
POST /api/v1/trading/execution-batches/{batchId}/risk-actions
POST /api/v1/ops/eod-reconciliation/reports
POST /api/v1/ops/eod-reconciliation/reports/{reportId}/review
```

`POST /api/v1/trading/orders` 仅为 deprecated 兼容入口。正式 TradeCommand 必须携带 StrategyInstance 并将其传到 Runtime。

## 7. 受控实盘底线

- Platform Live Gate 与 Runtime Live Gate 是两道独立门禁。
- Runtime `liveWriteEnabled` 默认 false。
- Account、StrategyInstance、Symbol 必须位于 allowlist。
- Platform 绝对限额、LiveTradingSession 限额与 Runtime 限额同时生效。
- 同步 ACK 不等于成交。
- 无法确认请求结果时标记 `result_unknown`，不得重下。
- 真实凭证只通过 `secret://...` 或受控 SecretProvider 引用读取。
- Query 失败不得展示为空仓、零余额或 clean EOD。
- Open 与 Accepted Difference 均阻断后续会话批准和扩大实盘。
- 每个真实测试日必须形成 EOD Report。
- 会话结束后必须撤销/过期，并复位临时 allowlist、限额和 Write Gate。

## 8. Repository Secret Scan

```powershell
python .\scripts\scan-secrets.py
```

Platform CI 和独立 Secret Scan workflow 检查私钥、常见 Token、高熵明文 Secret 以及未审核的 tracked `.env*`。审核过的 `VITE_*` 文件属于浏览器公开配置，但仍接受 Token 和高熵内容扫描。

## 9. 当前最小对象

- AuthCredential / Principal / Role / Permission。
- LiveTradingSession / LiveTradingSessionClaim。
- StrategyDefinition / StrategyVersion / StrategyInstance。
- StrategyAccountBinding / Account。
- Instrument / ContractSpecification。
- TradeCommand / ExecutionBatch / Order / Fill / Deal。
- KillSwitch / ExecutionRiskPolicy / ExecutionRiskAction。
- Venue Snapshot / ReconciliationRun / ReconciliationDifference。
- EodReconciliationReport / EodReview / ScaleGateStatus。
- FinancialFact / Formal Position / Formal PnL / Formal NAV。
- AuditEvent。

## 10. 审视当前版本时必须问

- Live 环境匿名与 development auth 是否 fail-closed？
- 权限是否默认拒绝？
- Actor 是否只能来自认证上下文？
- Applicant 与 Approver 是否严格分离？
- Live Session 是否约束账户、策略、品种、方向、类型、时间和额度？
- 并发 Command 是否可能共同穿透日限额？
- Kill Switch、历史差异和 EOD 是否阻断批准与认领？
- Platform 与 Runtime Live Gate 是否都默认关闭？
- `result_unknown` 是否只查询恢复而不重下？
- 每个真实测试日是否完成 EOD 和门禁复位？
- Secret 值是否可能进入 Git、日志、响应或 AuditEvent？
- 备份恢复后 Live Gate 是否默认安全关闭？

前十项属于本阶段工程与运营门禁；最后两项将在 Production Gate 5C/5D 完成。

## 11. 文档治理

- 每个阶段必须有 Issue、分支、PR、计划、技术设计、CI 和回滚说明。
- 代码变化同步更新 API Spec、Release Gate、README、START-HERE 和 Changelog。
- 真实凭证、账户密码、API Key、Secret 和 Bearer Token 不得进入仓库、Markdown、截图或对话记录。