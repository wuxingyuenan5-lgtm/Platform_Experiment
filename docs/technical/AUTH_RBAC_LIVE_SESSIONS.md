# Authentication, RBAC, Browser Session, and LiveTradingSession

状态：`active authentication and authorization contract`
适用产品：`Platform`
用户系统架构：`USER_SYSTEM_TECHNICAL_ARCHITECTURE.md`
产品与验收基线：`../product/PRD.md`、`../product/ACCEPTANCE_CRITERIA.md`
浏览器访问合同：[Browser Access and Product Data](../contracts/BROWSER_ACCESS_AND_PRODUCT_DATA.md)
角色权限矩阵：[Platform 0.10.2 前端访问权限矩阵](../product/PLATFORM_0_10_2_FRONTEND_ACCESS_MATRIX.md)

## 1. 两类 Session 不是同一概念

平台存在两种名称相近但责任完全不同的 Session：

| 类型 | 目的 | 凭证/身份 | 能否授权真实交易 |
|---|---|---|---|
| Browser Session | 让会员和内部人员登录网页、访问个人账号和被授权的业务页面 | HttpOnly opaque Cookie → human Principal | 不能替代 API Key，也不能直接授权 Live Write |
| LiveTradingSession | 对已经通过 API-Key 认证的真实交易 Command 提供限时、限范围、双人审批授权 | API-Key Principal + approved LiveTradingSession claim | 只有继续通过全部 Live 闸门时才可参与授权 |

禁止把 Browser Session ID、Cookie 或 CSRF Token 写入 `LiveTradingSession`，也禁止把 LiveTradingSession ID 当作浏览器登录凭证。

## 2. 总体安全边界

```text
HTTP Request
→ Authentication Credential Selection
→ Authentication Assurance
→ Permission Resolution
→ Authenticated Principal
→ Actor / Target / Data Scope Binding
→ Business Validation
→ [Live Write only] LiveTradingSession Claim
→ [Live Write only] Platform Live Gate / Kill Switch
→ [Live Write only] Runtime Live Gate
→ Venue
```

认证与授权必须位于所有既有和新增 API 路由之外层。业务模块不能假设客户端提供的 actor、reviewer、applicant、userId 或 memberId 可信。

## 3. Principal

统一 Principal 最小字段：

- `user_id`；
- `roles`；
- `auth_method`：`session | api_key | development`；
- `session_id`：Browser Session 适用；
- `credential_id`：API Key 适用。

权限由服务器根据当前角色集中解析。角色和权限不能来自前端菜单、本地存储、请求体或 Cookie 自带声明。

Bearer Token 只在请求中存在。API-Key 配置保存 Token SHA-256，比较使用恒定时间 `compare_digest`。响应、日志、数据库和 AuditEvent 不保存原始 API Key。

Browser Session Cookie 只保存高熵 opaque token。数据库只保存其 SHA-256；Cookie 不保存用户资料、角色、权限或 CSRF Token。

## 4. 角色命名空间

### 4.1 API-Key / Development 角色

```text
viewer
researcher
trader
risk_officer
operations
admin
```

这些角色继续服务自动化、系统调用和现有 Live 链路。配置中的 API-Key 和 Development Identity 只能使用这一命名空间。

API-Key `admin` 保留 `*` 通配符兼容语义，但该通配符只能在 API-Key/Development 权限解析中生效，不能进入 Browser Session、用户管理或客户持仓域。

### 4.2 浏览器业务角色

浏览器角色来自 `users.role_code`，使用显式权限集合，不使用 API-Key wildcard，也不与 API-Key 角色自动转换。

| 浏览器角色 | 正式业务页面 | 风险管理 | 用户管理 | 本人个人账号 | 写入边界 |
|---|---|---|---|---|---|
| CEO | 全部正式页面 | 允许 | 允许 | 允许 | 产品业务写权限保留，但仍受 Live Write、审批、Kill Switch 和全部交易安全门禁约束 |
| 技术负责人 | 接近完整或完整的正式页面范围 | 允许 | 允许 | 允许 | 仍受全部正式安全门禁约束 |
| 员工 | 全部正式业务页面只读 | 只读 | 用户列表只读 | 允许 | 仅本人获准的密码、头像、设备和会话等安全自助；无业务或其他账号写权限 |
| 会员 | 规定范围内正式业务页面只读 | 禁止 | 禁止 | 必须允许 | 只能访问当前认证会员本人；不得读取其他账号或内部组织数据 |

长期授权原则：

- 菜单隐藏不是授权；
- 直接 URL 与后端 API 必须独立验证权限和数据范围；
- 浏览器角色只使用显式权限集；
- API-Key 角色命名空间继续独立；
- Browser Session 不能授权 Platform 或 Runtime Live Write；
- 前端菜单和路由转换不拥有后端授权决策。

人类 CEO 使用显式业务权限集合，不返回或依赖 `*`。API-Key `admin` 不自动等同 CEO，`ceo` 也不是有效 API-Key 配置角色。

## 5. 认证保障等级

每个请求先确定保障等级：

| 等级 | 允许认证 | 典型范围 |
|---|---|---|
| `public` | 无 | `/health`、注册、登录、重置凭证使用 |
| `human_session` | Browser Session only | `/auth/me`、`/auth/logout`、`/auth/reauth`、`/me/**`、`/users/**` |
| `platform_read` | Browser Session 或 API Key；non-live 可使用显式 Development Identity | 普通平台读取 |
| `simulation_write` | Browser Session 或 API Key；non-live 可使用显式 Development Identity | 非 Live 模拟写入，仍需权限与领域校验 |
| `live_write` | API Key only | 真实交易、核心风控和 LiveTradingSession 写操作 |

同一请求同时携带 Bearer 和 Browser Session Cookie 时返回歧义认证错误，不静默选择其中一种。

## 6. 环境规则

### 6.1 Live

- Development Identity 永远禁用；
- `live_write` 路由只允许 API Key；
- Browser Session 可以访问声明为 `human_session` 的用户域接口；
- Browser Session 可以访问明确允许的 `platform_read` 接口；
- Browser Session 不能替代 API Key 申请、批准、认领或提交真实交易；
- 匿名、无效配置、未知角色和无法识别的保障等级全部拒绝。

现有 `auth_mode=api_key` 是 Live 系统凭证配置要求，但不解释为“生产环境所有网页接口只能 Bearer”。路由保障等级负责区分人类网页访问和真实写入。

### 6.2 Non-live

- 可以使用显式 Development Identity 维持本地和 CI 的旧接口流程；
- Development Identity 的 User ID 和 API-Key 命名空间 Roles 必须配置有效；
- Browser Session 可测试真实的用户身份边界；
- 切换到 Live 后 Development Identity 立即失效。

## 7. Browser Session 安全规则

默认安全参数：

```text
absolute TTL         12 hours
idle TTL             30 minutes
recent reauth        10 minutes
last-seen write step 5 minutes
max active sessions  5 per user
```

Cookie：

```text
Name     vg_session
HttpOnly true
Secure   production true
SameSite Lax
Path     /
Domain   omitted / host-only
```

验证顺序：

```text
raw Cookie
→ SHA-256 lookup
→ Session exists and not revoked
→ user lifecycle_status == active
→ temporary lock not active
→ session.auth_version == user.auth_version
→ absolute expiry not reached
→ idle expiry not reached
→ build Principal(auth_method=session)
```

角色、密码或账号生命周期变化通过递增 `users.auth_version` 使旧 Browser Session 下一次请求立即失效。过期、用户停用和授权版本变化会持久化 Session revocation evidence。

Cookie 认证的非安全 HTTP 方法必须同时通过：

```text
X-CSRF-Token
+ trusted Origin
```

CSRF 原始值只存在于当前浏览器内存；数据库保存哈希。用户系统或持仓客户端收到 401 时清除内存 CSRF。API-Key 请求不使用 Browser CSRF 机制。

## 8. Password 和初始 CEO

- 密码使用 Argon2id；
- 密码、密码哈希、原始 Session/CSRF/reset token 不进入日志、响应、Markdown 或 Git；
- 不提供默认 CEO Seed 或默认密码；
- 初始 CEO 通过 `python -m app.user_cli create-ceo` 交互创建；
- 命令使用 `getpass`，只有数据库尚无 active CEO 时才能成功；
- 最后一个 active CEO 的停用或降级必须在 `BEGIN IMMEDIATE` 保护的事务内拒绝；
- 管理员密码重置使用一次性短期凭证，不设置或查看用户临时密码。

## 9. Permission Resolution

现有 API-Key 接口权限继续按 HTTP Method 与 Route Pattern 解析并 default-deny：

| Permission | 典型操作 |
|---|---|
| `platform:read` | 普通查询 |
| `audit:read` | Audit、Credential Reference |
| `strategy:run` | Strategy Run |
| `trade:submit` | TradeCommand、ExecutionBatch |
| `risk:manage` | Kill Switch、Risk Policy、RiskAction |
| `operations:run` | Fact Import、Venue Reconciliation、EOD Run |
| `reconciliation:review` | Difference Resolution |
| `eod:review` | EOD Review |
| `live_session:request` | 申请实盘会话 |
| `live_session:approve` | 批准实盘会话 |
| `live_session:revoke` | 撤销实盘会话 |
| `admin:write` | 未明确分类的旧管理写操作 |

用户域采用显式点号权限，例如：

```text
profile.read_self
profile.update_self
session.read_self
user.read
user.update
user.assign_role
member.holding.read_self
member.holding.read_all
member.holding.update
```

新增用户域路由必须使用显式权限依赖，不依靠 URL 字符串推导完整的字段、目标和数据范围规则。

授权顺序：

```text
authentication assurance
→ permission point
→ target-role policy
→ field policy
→ data scope
→ recent reauthentication when required
→ domain invariant
```

未知 Role 不产生权限。API-Key wildcard 不豁免目标范围、最后 CEO、禁止自我提权、CSRF、近期再认证或 Live 闸门；Browser Session 不使用 wildcard。

员工账号在批准或改为 `employee` 前必须有非空部门；会员账号在批准或改为 `member` 前必须有非空会员类型。检查必须位于权限和目标角色策略之后，并由 `expectedVersion` 防止并发资料变化被静默覆盖。

## 10. Actor、Target 和 Data Scope Binding

Live 或 API-Key 模式下，JSON 请求体出现以下字段时必须与 Principal User ID 相同：

- `actor`；
- `reviewer`；
- `requestedBy`；
- `approvedBy`；
- `revokedBy`。

不一致在进入业务处理前返回 403。新接口优先不在请求体暴露身份字段，直接从 Principal 读取。

用户域还必须执行目标与数据范围绑定：本人账号接口不接受客户端提供的其他 `user_id` 或 `member_id`。Path、Query、ID 和 API 参数不能扩大当前认证主体的数据范围。

## 11. Request Audit

认证或授权拒绝记录：

- Request ID；
- Method / Path；
- User ID（如果已认证）；
- Roles；
- Auth Method；
- Credential ID（适用时）；
- Required Permission；
- Result / Detail；
- Source IP（可用时）；
- Created At。

Audit 写入失败不能使请求 fail-open；原本应拒绝的请求仍然拒绝。

用户域敏感成功写操作与审计在同一事务提交。审计不保存密码、原始 Token、完整联系方式、头像内容或完整客户持仓快照。

## 12. LiveTradingSession 状态

```text
pending → approved → expired
   │          │
   └──────────┴→ revoked
```

- pending：已申请，未获第二人批准；
- approved：可在时间、范围和额度内认领 Live Command；
- revoked：风险人员主动撤销，不可恢复；
- expired：结束时间已到，由查询或认领流程惰性更新。

## 13. 双人审批

Applicant 来自 API-Key 请求 Principal。Approver 来自批准请求 Principal。

约束：

- Approver 必须具备 `risk_officer` 或 `admin`；
- Applicant User ID 与 Approver User ID 必须不同；
- Approval 只允许 pending → approved；
- Approval 原因、User ID 和时间不可被后续请求覆盖；
- 修改 Session Payload 必须使用新 Idempotency Key 新建申请；
- Browser Session CEO 身份不能替代 API-Key Applicant 或 Approver。

## 14. LiveTradingSession Scope

LiveTradingSession 固化：

- StrategyInstance / Account；
- Symbol Set；
- Side Set；
- Order Type Set；
- Starts At / Ends At；
- Per-order Notional；
- Daily Notional；
- Read-only Evidence；
- Session Type。

`minimum_size_acceptance` 是必须保留的 public schema legacy compatibility 标识，不再表示 owner 要求固定最小仓位或 `1 oz` 上限。`existing_limits` 需要最新 Clean EOD。`scale_change` 在独立扩大规模流程落地前始终阻断。当前 Per-order / Daily Notional 字段及校验仍是 legacy fixed-cap 实现；在后续行为对齐完成前，它们是 controlled-live readiness blocker，不是 owner 风险合同。

## 15. Approval Blockers

批准与每次 Command Claim 都必须重新检查：

- Legacy Platform fixed-notional enforcement；当前代码仍检查，但只构成 controlled-live readiness blocker，不构成 owner 要求的固定 cap；
- Kill Switch；
- Open / Accepted Reconciliation Difference；
- Approved Session 时间重叠；
- Existing-limit EOD Gate；
- Session Type 规则。

批准后出现 Kill Switch 或 Difference 时，LiveTradingSession 不再可用于新 Command，即使状态仍为 approved。

## 16. Command Claim

LiveTradingSession Claim 使用 Command ID 作为唯一身份：

```text
Command ID
+ Strategy / Account / Symbol / Side / Order Type
+ Quantity / Price
→ Payload Hash
→ Atomic Notional Claim
```

- 相同 Command 与相同 Payload 返回原 LiveTradingSession ID；
- 相同 Command 与不同 Payload 返回 409；
- 必须唯一匹配一个 Active Approved LiveTradingSession；
- 必须使用正数 Price 计算 Notional；当前 Live Market Order 无明确价格时拒绝；
- Claim 在创建 Platform Order 和调用 Runtime 之前完成；
- Platform Session Limit 与 Runtime Limit 均需通过。

## 17. 失败语义

- 400：歧义凭证或请求格式错误；
- 401：缺少、无效或过期认证；
- 403：保障等级、身份、角色、会话、目标或范围无权限；
- 409：幂等身份冲突、最后 CEO 或并发状态冲突；
- 422：字段、时间、额度、范围或审批前置条件不满足；
- 423：临时账号锁定，或 Live 批准后出现活动安全阻断；
- 429：登录、注册或恢复请求达到频率限制；
- 503：认证、安全配置或绝对上限未安全配置。

## 18. 部署与外部状态限制

仓库合同、自动化测试和候选验证不能证明外部生产环境已经就绪。生产启用前仍需独立确认：

- 同源 TLS、反向代理、Cookie Secure 与 Origin 配置；
- 权威用户、会员持仓和基金净值数据来源；
- 数据库、头像、密钥和会话数据的备份恢复；
- 账号、凭证、Provider、Broker 与 Venue 的真实连接和权限；
- 生产监控、告警、回滚和灾备演练。

当前 API-Key 配置适合单机小型私募的受控部署边界，不等同完整企业身份提供商。认证、审批、代码完成、候选验证和 CI 均不能自动打开 Platform 或 Runtime Live Write。

## 19. Product authority and scope

The browser role set is CEO, technical lead, employee and member. Capability and resource scope are resolved centrally; UI visibility is never authorization. Any future research, trader, strategy-owner, risk, reconciliation or system-administration specialization must be introduced as reviewed Capability and Data Scope policy, not as an unreviewed page-local role.
