# Authentication, RBAC, and LiveTradingSession

状态：`active`  
适用版本：`Platform V6 / Production Gate`  
实施计划：`../planning/V6-Production-Gate-身份权限与实盘会话.md`

## 1. 安全边界

```text
HTTP Request
→ Authentication
→ Permission Resolution
→ Authenticated Principal
→ Actor Binding
→ Business Validation
→ LiveTradingSession Claim
→ Platform Live Gate / Kill Switch
→ Runtime Live Gate
→ Venue
```

认证与授权必须位于所有既有和新增 API 路由之外层。业务模块不能假设客户端提供的 actor、reviewer 或 applicant 身份可信。

## 2. Principal

Principal 最小字段：

- userId
- roles
- authMethod
- credentialId（适用时）

Bearer Token 只在请求中存在。配置保存 Token SHA-256，比较使用恒定时间 `compare_digest`。响应、日志、数据库和 AuditEvent 不保存原始 Token。

## 3. 环境规则

### Live

- 只允许 `authMode=api_key`。
- 匿名、Development Identity、无效配置全部拒绝。
- 除 `/health` 外，系统与业务接口进入认证边界。

### Non-live

- 可以使用显式 Development Identity 维持本地和 CI 流程。
- Development Identity 的 User ID 和 Roles 必须配置有效。
- 切换到 Live 后 Development Mode 立即失效。

## 4. Permission Resolution

权限按 HTTP Method 与 Route Pattern 解析，采用 default-deny：

| Permission | 典型操作 |
|---|---|
| platform:read | 普通查询 |
| audit:read | Audit、Credential Reference |
| strategy:run | Strategy Run |
| trade:submit | TradeCommand、ExecutionBatch |
| risk:manage | Kill Switch、Risk Policy、RiskAction |
| operations:run | Fact Import、Venue Reconciliation、EOD Run |
| reconciliation:review | Difference Resolution |
| eod:review | EOD Review |
| live_session:request | 申请实盘会话 |
| live_session:approve | 批准实盘会话 |
| live_session:revoke | 撤销实盘会话 |
| admin:write | 未明确分类的管理写操作 |

未知 Role 不产生任何权限。Admin 的 wildcard 不豁免“双人不能同一人”这一业务约束。

## 5. Actor Binding

Live 或 API-Key 模式下，JSON 请求体出现以下字段时必须与 Principal User ID 相同：

- actor
- reviewer
- requestedBy
- approvedBy
- revokedBy

不一致在进入业务处理前返回 403。新接口优先不在请求体暴露身份字段，直接从 Principal 读取。

## 6. Request Audit

认证或授权拒绝记录：

- Request ID
- Method / Path
- User ID（如果已认证）
- Roles
- Credential ID
- Required Permission
- Result / Detail
- Source IP（可用时）
- Created At

Audit 写入失败不能使请求 fail-open；原本应拒绝的请求仍然拒绝。

## 7. LiveTradingSession 状态

```text
pending → approved → expired
   │          │
   └──────────┴→ revoked
```

- pending：已申请，未获第二人批准。
- approved：可在时间、范围和额度内认领 Live Command。
- revoked：风险人员主动撤销，不可恢复。
- expired：结束时间已到，由查询或认领流程惰性更新。

## 8. 双人审批

Applicant 来自创建请求 Principal。Approver 来自批准请求 Principal。

约束：

- Approver 必须具备 risk_officer 或 admin。
- Applicant User ID 与 Approver User ID 必须不同。
- Approval 只允许 pending → approved。
- Approval 原因、User ID 和时间不可被后续请求覆盖。
- 修改 Session Payload 必须使用新 Idempotency Key 新建申请。

## 9. Session Scope

Session 固化：

- StrategyInstance / Account
- Symbol Set
- Side Set
- Order Type Set
- Starts At / Ends At
- Per-order Notional
- Daily Notional
- Read-only Evidence
- Session Type

`minimum_size_acceptance` 用于真实账户最小允许仓位验收。`existing_limits` 需要最新 Clean EOD。`scale_change` 在独立扩大规模流程落地前始终阻断。

## 10. Approval Blockers

批准与每次 Command Claim 都必须重新检查：

- Platform Absolute Notional Limits。
- Kill Switch。
- Open / Accepted Reconciliation Difference。
- Approved Session 时间重叠。
- Existing-limit EOD Gate。
- Session Type 规则。

批准后出现 Kill Switch 或 Difference 时，Session 不再可用于新 Command，即使状态仍为 approved。

## 11. Command Claim

Session Claim 使用 Command ID 作为唯一身份：

```text
Command ID
+ Strategy / Account / Symbol / Side / Order Type
+ Quantity / Price
→ Payload Hash
→ Atomic Notional Claim
```

- 相同 Command 与相同 Payload 返回原 Session ID。
- 相同 Command 与不同 Payload 返回 409。
- 必须唯一匹配一个 Active Approved Session。
- 必须使用正数 Price 计算 Notional；当前 Live Market Order 无明确价格时拒绝。
- Claim 在创建 Platform Order 和调用 Runtime 之前完成。
- Platform Session Limit 与 Runtime Limit 均需通过。

## 12. 失败语义

- 401：缺少或无效认证。
- 403：身份、角色、会话或范围无权限。
- 409：幂等身份冲突、重复自相矛盾操作。
- 422：时间、额度、范围或审批前置条件不满足。
- 423：批准后出现 Kill Switch 或其他活动安全阻断。
- 503：Live Authentication 或绝对上限未安全配置。

## 13. 当前限制

- 当前 API Key 配置适合单机小型私募第一阶段，不等同完整企业身份提供商。
- Token Rotation、Windows Credential Manager、Secret Scan 和集中 SecretProvider 属于下一批 Production Gate。
- 并发 Session Claim 仍需强事务金样本。
- Frontend 登录、用户管理和审批页面尚未接入新 Principal API。
- 认证、审批和工程验收均不能自动打开 Runtime Live Write。
