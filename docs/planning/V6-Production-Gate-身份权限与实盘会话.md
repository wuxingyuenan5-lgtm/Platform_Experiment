# V6 Production Gate：身份权限与双人实盘会话

状态：`implementation complete / final CI and merge pending`  
实施分支：`hardening/v6-production-gate-auth-live-sessions`  
Pull Request：`#23 Add production authentication and two-person live sessions`  
跟踪 Issue：`#22 V6 Production Gate：身份权限、双人审批、密钥托管、监控与恢复`  
前置阶段：Phase 4D 已通过 PR `#21` 合入 main  
更新时间：`2026-07-23`

## 1. 目标

Phase 4 已经形成受控实盘适配器、风险处置、外部查询和日终对账，但尚不能持续开放真实资金写入。当前批次补齐最先必须落地的两道生产门禁：

```text
Authenticated Principal + Default-deny RBAC
+
Two-person approved LiveTradingSession
+
Atomic session notional claim
+
Platform Live Gate + Runtime Live Gate + Kill Switch
```

小资金真实账户测试仍是运营验收方式，但任何测试都必须处于有范围、有时限、有额度、有第二人批准的实盘会话中。

## 2. 身份认证

### 2.1 Live 环境

- `environment=live` 时只接受 `authMode=api_key`。
- 请求使用 Bearer Token。
- 配置只保存 Token SHA-256，不保存原始 Token。
- Credential 包含 credentialId、userId、roles、status 和 tokenSha256。
- 未认证、无效、停用或配置错误全部 fail-closed。
- `/health` 保持不含业务数据的公开健康探针，其余接口进入认证边界。

### 2.2 Development 环境

- 仅非 Live 环境允许显式 Development Identity。
- Development Identity 不能在 Live 环境启用。
- CI 和既有 Simulation 测试通过 Development Identity 兼容，不削弱 Live 门禁。

## 3. RBAC

最小角色：

| Role | 核心权限 |
|---|---|
| viewer | 普通只读 |
| researcher | 只读、研究运行 |
| trader | 下单、申请 LiveTradingSession |
| risk_officer | Kill Switch、RiskAction、差异/EOD 复核、批准/撤销实盘会话 |
| operations | 外部事实导入、对账与 EOD 执行 |
| admin | 管理权限，不豁免双人自批限制 |

规则：

- 权限未知或不匹配默认拒绝。
- Audit 与 Credential Reference 不是普通 viewer 权限。
- Live 请求体中的 actor、reviewer 等身份字段必须与认证用户一致。
- Request ID、User ID、Role、Credential ID、Source IP 和拒绝原因写入安全审计。

## 4. LiveTradingSession

### 4.1 申请范围

每个会话固定：

- Session Type：minimum_size_acceptance、existing_limits、scale_change。
- StrategyInstance。
- Account。
- Symbol Allowlist。
- Side Allowlist。
- Order Type Allowlist。
- Starts At / Ends At。
- Max Order Notional。
- Max Daily Notional。
- Read-only Verified At。
- Evidence Reference。
- Applicant 与申请原因。

### 4.2 双人审批

- trader 或 admin 可以申请。
- risk_officer 或 admin 可以批准。
- Applicant 与 Approver 必须是不同 User ID；admin 也不能自批。
- Approval 绑定不可变申请 Payload Hash。
- 修改范围、时间、品种或额度必须新建会话。
- 会话可由 risk_officer/admin 撤销，撤销不可逆。

### 4.3 审批阻断

以下任一存在，拒绝批准：

- Platform 绝对单笔或单日上限未配置或为零。
- 申请额度超过 Platform 绝对上限。
- Global、Strategy 或 Account Kill Switch 开启。
- 存在历史 Open 或 Accepted Reconciliation Difference。
- 同一 Strategy/Account 存在时间重叠的 Approved Session。
- existing_limits 缺少最新 Clean EOD。
- scale_change 尚未经过独立扩大规模评审。

## 5. 下单时会话认领

Live Order 在写入 Order 表和调用 Runtime 之前必须：

1. 通过账户、合约规格和 Platform Live Gate。
2. 确认 Production Authentication 已启用。
3. 提供 StrategyInstance、Command ID、Symbol、Side、Order Type。
4. 找到唯一 Active + Approved Session。
5. 确认 Symbol、Side、Order Type 位于范围内。
6. 使用明确 Price 计算名义金额；当前 Live Market Order 缺价格时 fail-closed。
7. 检查会话单笔和累计日限额。
8. 使用 SQLite `BEGIN IMMEDIATE` 在强事务中读取累计值并以 Command ID 写入 Claim。
9. 再进入 Runtime Live Gate、Runtime Allowlist 和 Runtime Notional Limit。

重复 Command ID 与相同载荷返回原 Claim；载荷冲突返回 409。并发命令不能同时读取相同的剩余额度后共同穿透单日上限。

## 6. API

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

Applicant 和 Approver 由认证上下文产生，不由请求体指定。

## 7. 配置

```text
VG_ENVIRONMENT=live
VG_AUTH_MODE=api_key
VG_AUTH_CREDENTIALS_JSON=[...tokenSha256 only...]
VG_LIVE_TRADING_ENABLED=false
VG_REQUIRE_LIVE_TRADING_SESSION=true
VG_LIVE_SESSION_ABSOLUTE_MAX_ORDER_NOTIONAL=0
VG_LIVE_SESSION_ABSOLUTE_MAX_DAILY_NOTIONAL=0
```

默认零上限和关闭 Live Trading 使系统 fail-closed。真实 Token 只在本地主机生成和注入，不进入 Git、Markdown、截图或对话。

## 8. Repository Secret Scan

```powershell
python .\scripts\scan-secrets.py
```

扫描范围：Git tracked files。阻断项：

- 私钥块。
- GitHub、AWS、OpenAI、Slack 等常见 Token 形式。
- 受控字段中的高熵明文 Secret。
- 非模板、非审核公共 Vite 配置的 tracked `.env*` 文件。

审核过的 `admin-risk/.env*` 只包含公开 `VITE_*` 浏览器配置，仍继续接受 Token 和高熵内容扫描。扫描器自身 regex 源文件被单独跳过，避免确定性自匹配。

## 9. 工程验收

- [x] Live 匿名和错误 Credential 被拒绝。
- [x] Development Auth 不能在 Live 使用。
- [x] Role Permission 默认拒绝。
- [x] 请求体 Actor/Reviewer 不能冒充其他用户。
- [x] LiveTradingSession 申请、幂等、双人审批、撤销和过期模型已实现。
- [x] Admin 自批也被拒绝。
- [x] Kill Switch、历史差异、绝对额度和重叠会话阻断审批。
- [x] Live Order 在 Runtime 之前认领 Approved Session。
- [x] 无 Approved Session 的 Live Order 被拒绝。
- [x] Session Claim 使用 Command ID 幂等。
- [x] 并发累计额度认领使用 SQLite `BEGIN IMMEDIATE` 并具备并发金样本。
- [x] Secret Scan 已进入 Platform CI 和独立可诊断 workflow。
- [x] Secret Scan 独立 workflow run `30022271523` 通过。
- [ ] Platform CI 最终全部通过并记录 Run ID。
- [ ] README、START-HERE、API Spec、Release Gate、总计划和 Changelog 最终同步。

## 10. 运营验收

- [ ] 真实账户只读 Preflight 通过。
- [ ] trader 申请最小仓位窗口，risk_officer 使用不同身份批准。
- [ ] Session 范围与 Runtime Allowlist/Limit 一致。
- [ ] 完成限价单、撤单、最小成交和 `result_unknown` 演练。
- [ ] 会话结束后撤销或过期，Runtime Write Gate 和限额强制复位。
- [ ] 当日 EOD Report 为 Clean 或明确进入 Remediation。

## 11. 明确延期

- SecretProvider、密钥轮换和全链路脱敏属于 Production Gate 5C。
- 告警、调度、备份和恢复属于 Production Gate 5D。
- Web 前端用户管理和审批界面在 API 安全边界稳定后实施。
- 不因本批工程完成自动打开 Live Write 或扩大实盘规模。