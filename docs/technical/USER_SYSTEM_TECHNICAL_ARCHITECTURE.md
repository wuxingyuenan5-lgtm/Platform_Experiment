# 用户系统技术架构

状态：`implemented / automated verification passed / manual acceptance pending`<br>
适用产品：`Platform`
Issue：`#117`
产品与验收基线：`../product/PRD.md`、`../product/ACCEPTANCE_CRITERIA.md`

## 1. 架构目标

建立一个浏览器用户系统，同时保持现有交易与 Live 安全边界不变：

```text
platform-web
    ↓ same-origin HTTPS
platform-api
    ├─ Human Identity / Password
    ├─ Server-side Session / CSRF
    ├─ Principal / Permission / Target Scope
    ├─ Personal Account / User Administration
    ├─ Member Holding Read Model
    └─ Audit Evidence

API-Key / Automation / Live Client
    ↓ Bearer API Key
platform-api
    ↓ existing LiveTradingSession + risk gates
execution-runtime
```

本架构不建立第三套认证系统，也不把旧 Go `auth-service` 扩展为正式权威。

## 2. 当前冲突与收敛方式

### 2.1 当前冲突

- `platform-api/app/auth.py` 是现有 API-Key Principal 和 Live 安全认证边界；
- 前端登录仍调用旧 `/api/auth` Go/MySQL 服务；
- 当前 `auth.py` 在 Live 环境要求全局 `api_key`；
- 浏览器会员和员工未来必须能够在生产环境登录；
- API-Key `admin` 当前具有 wildcard，但不应自动成为客户身份系统的 CEO；
- 当前权限主要按 HTTP Method 和路径字符串推断，不足以表达字段和数据范围。

### 2.2 收敛原则

不把“生产环境”与“所有路由只能 API-Key”继续绑定为同一概念，改为显式的认证保障等级。现有 Live 写入路由仍保持 API-Key-only；新增人类身份路由允许生产环境的同源 Session。

这不是放宽 Live 安全，而是把认证方式按路由责任分类。

## 3. 认证保障等级

每个路由必须声明一个保障等级，而不是只根据环境全局选择认证方式。

| 等级 | 允许认证 | 典型路由 | 额外条件 |
|---|---|---|---|
| `public` | 无 | `/health`、注册、登录、密码重置使用 | Origin/速率限制/输入校验 |
| `human_session` | 浏览器 Session | `/auth/me`、`/me/**`、`/users/**`、会员持仓 | 同源、CSRF、权限、目标范围 |
| `platform_read` | Session 或 API Key | 普通平台读取 | 对客户敏感数据仍限制 Session |
| `simulation_write` | Session 或 API Key | 非 Live 的模拟写操作 | 权限、Actor Binding、必要时近期再认证 |
| `live_write` | API Key only | 真实交易、核心风控、Live Session | 保留现有全部 Live 闸门 |

### 3.1 客户身份数据边界

以下接口必须是 `human_session`，即使 API-Key Principal 具备 `*` 也拒绝：

```text
/users/**
/me/**
/auth/me
/auth/logout
/auth/reauth
member holding administration
password reset ticket administration
```

原因：API Key 是自动化/系统凭证，不是人类账号生命周期的业务身份。

### 3.2 Live 边界

第一阶段不允许浏览器 Session 替代 API Key 调用 `live_write` 路由。CEO 的业务权限只代表角色层允许；真实写入仍需：

```text
API-Key Principal
+ required permission
+ Actor Binding
+ LiveTradingSession
+ Kill Switch
+ reconciliation gates
+ Platform Live Write
+ Runtime Live Write
+ existing execution safety
```

未来若开放浏览器真实交易，必须单独设计 MFA、再认证、批准链和 Live assurance，不属于 Issue #117。

## 4. 统一 Principal

建议扩展现有 Principal：

```python
@dataclass(frozen=True)
class Principal:
    user_id: str
    roles: tuple[str, ...]
    auth_method: Literal["session", "api_key", "development"]
    session_id: str | None = None
    credential_id: str | None = None
```

权限不从客户端、Cookie 或 Session 行直接信任，而是由服务器根据当前角色集中解析：

```text
Principal.roles
→ permission resolver
→ permission set
```

业务路由通过以下顺序授权：

```text
1. authentication assurance
2. permission point
3. target-role policy
4. field policy
5. data-scope policy
6. recent reauthentication when required
7. domain validation
```

## 5. 角色与权限解析

### 5.1 浏览器业务角色

```text
ceo
tech_lead
employee
member
```

### 5.2 现有 API-Key 角色

```text
viewer
researcher
trader
risk_officer
operations
admin
```

两组角色保持独立命名空间和用途，不自动互相映射。

### 5.3 权限注册表

现有冒号权限保持兼容：

```text
platform:read
trade:submit
risk:manage
audit:read
operations:run
...
```

新增用户域使用点式权限：

```text
profile.read_self
profile.update_self
profile.avatar.update_self
profile.password.change_self
session.read_self
session.revoke_self

user.read
user.sensitive.read
user.create
user.update
user.disable
user.reset_password
user.assign_role
user.session.revoke
user.audit.read

member.read_self
member.read_all
member.holding.read_self
member.holding.read_all
member.holding.update

system.read
system.manage
risk.read
trade.read
```

权限映射集中定义，不允许页面或服务各自维护一份角色表。

### 5.4 目标角色策略

权限点不能替代目标范围。服务层策略至少包括：

```text
ceo
    → 可管理所有角色，但不能移除最后一个 active CEO
    → 不能修改自己角色或停用自己

tech_lead
    → 只管理 member / employee
    → 不能管理 ceo / tech_lead
    → 不能给自己扩大权限

employee
    → 用户域只读脱敏

member
    → 只访问本人
```

## 6. 请求认证流程

### 6.1 凭证选择

```text
Authorization: Bearer ... present?
Cookie: vg_session present?
```

规则：

- 两者都存在：拒绝 `ambiguous_credentials`；
- 仅 Bearer：进入 API-Key 验证；
- 仅 Cookie：进入 Session 验证；
- 都不存在：仅 public 路由允许；
- Development Identity 只在明确 non-live 开发模式可用。

不得静默优先 Bearer 或 Cookie。

### 6.2 Session 验证

```text
Cookie raw token
→ SHA-256
→ user_sessions.token_hash lookup
→ session not revoked
→ now < expires_at
→ now < idle_expires_at
→ users.lifecycle_status == active
→ locked_until <= now
→ session.auth_version == users.auth_version
→ build Principal(auth_method=session)
```

### 6.3 API-Key 验证

继续复用现有恒定时间哈希比较和角色校验；新增保障等级检查在 Principal 构建后执行，不改变原始 Token 存储规则。

## 7. 浏览器 Session

### 7.1 默认参数

第一阶段建议默认值，均由安全配置读取：

```text
absolute_ttl          = 12 hours
idle_ttl              = 30 minutes
recent_reauth_window  = 10 minutes
last_seen_write_step  = 5 minutes
max_active_sessions   = 5 per user
```

这些是安全默认，不应成为前端可修改业务参数。

### 7.2 Cookie

```text
Name: vg_session
HttpOnly: true
Secure: true in production
SameSite: Lax
Path: /
Domain: omitted (host-only)
```

生产环境不允许无 HTTPS Session。Cookie 不包含角色、权限、用户资料或 CSRF Token。

### 7.3 Token

- 使用密码学安全随机值，至少 256 位熵；
- 数据库只保存 SHA-256；
- 登录成功时创建新 Session，避免 Session Fixation；
- 角色、密码和状态变化递增 `auth_version` 并撤销全部 Session；
- `last_seen_at` 最多每 5 分钟持久化一次，避免写放大；
- 超过最大 Session 数时优先撤销最旧非当前 Session，并形成审计。

### 7.4 CSRF

Cookie 认证的所有非安全方法要求：

```text
X-CSRF-Token
+ trusted Origin
```

CSRF Token：

- 与 Session 一起生成；
- 原始值只返回给当前浏览器内存；
- 数据库保存 SHA-256；
- `/auth/me` 可重新返回当前 Session 的 CSRF Token；
- 不放入 URL、日志或持久化前端缓存；
- API-Key 请求不使用该机制。

登录、注册、再认证和密码重置使用也必须校验 Origin，防止 Login CSRF。

### 7.5 近期再认证

Session 行保存：

```text
last_reauthenticated_at
```

接口：

```http
POST /api/v1/auth/reauth
```

要求重新输入当前密码。以下操作默认要求 10 分钟内近期再认证：

- 创建或修改 CEO/技术负责人；
- 修改任何用户角色；
- 停用用户；
- 签发密码重置凭证；
- 修改会员持仓；
- 修改本人手机号或邮箱；
- 撤销其他用户全部 Session。

## 8. 用户状态与登录锁定

账号生命周期字段：

```text
lifecycle_status = pending | active | disabled | rejected
```

安全锁定独立保存：

```text
failed_login_count
locked_until
```

不使用 `locked` 生命周期状态，避免临时锁定与管理员停用状态冲突。

默认登录策略：

```text
5 consecutive failures
→ locked_until = now + 15 minutes
```

同时由反向代理和应用层执行 IP/用户名维度频率限制。成功登录后清零账号失败计数。

## 9. 密码与恢复

### 9.1 密码哈希

- Argon2id；
- 依赖在实施时固定兼容版本；
- 参数集中配置并可在成功登录时按需升级；
- 密码比较和错误响应不泄露账号存在性。

### 9.2 用户修改密码

```text
current password
+ new password
+ confirmation
→ validate
→ update hash
→ auth_version + 1
→ revoke all sessions
→ audit
```

### 9.3 管理员密码重置

不允许管理员设置或查看临时密码，使用一次性重置凭证：

```text
administrator requests reset ticket
→ recent reauth + permission + target policy
→ revoke target sessions
→ generate high-entropy code
→ persist only token hash and 30-minute expiry
→ return raw code once
→ administrator securely gives code to user
→ user submits username + code + new password
→ consume ticket atomically
→ update password hash
→ audit without raw code
```

接口：

```http
POST /api/v1/users/{user_id}/password-reset-tickets
POST /api/v1/auth/reset-password
```

重置凭证：

- 30 分钟有效；
- 单次使用；
- 每个用户最多一个活动凭证；
- 新凭证使旧凭证失效；
- 原始值不进入 URL、日志、审计或前端持久化；
- 接口响应使用 `Cache-Control: no-store`。

## 10. 数据模型

所有时间为 timezone-aware UTC ISO 8601。SQLite 金融值使用规范化十进制字符串。

### 10.1 `users`

```sql
CREATE TABLE users (
    id                    TEXT PRIMARY KEY,
    username              TEXT NOT NULL,
    username_normalized   TEXT NOT NULL UNIQUE,
    password_hash         TEXT NOT NULL,

    display_name          TEXT,
    real_name             TEXT,
    avatar_key            TEXT,
    phone                 TEXT,
    phone_normalized      TEXT,
    email                 TEXT,
    email_normalized      TEXT,

    role_code             TEXT,
    requested_role_code   TEXT,
    department            TEXT,
    member_type           TEXT,
    application_note      TEXT,
    rejection_reason      TEXT,

    lifecycle_status      TEXT NOT NULL,
    auth_version           INTEGER NOT NULL DEFAULT 1,
    row_version            INTEGER NOT NULL DEFAULT 1,
    failed_login_count     INTEGER NOT NULL DEFAULT 0,
    locked_until           TEXT,

    registered_at          TEXT NOT NULL,
    approved_at            TEXT,
    approved_by            TEXT,
    last_login_at          TEXT,
    password_changed_at    TEXT,
    created_by             TEXT,
    created_at             TEXT NOT NULL,
    updated_at             TEXT NOT NULL
);
```

关键约束：

- `role_code` 允许 `ceo/tech_lead/employee/member` 或空；
- `requested_role_code` 公开注册只允许 `employee/member`；
- `pending` 必须 `role_code IS NULL`；
- `active/disabled` 必须具有正式角色；
- `row_version` 每次管理写入递增；
- 邮箱和手机号使用非空部分唯一索引；
- 不提供硬删除。

### 10.2 `user_sessions`

```sql
CREATE TABLE user_sessions (
    id                       TEXT PRIMARY KEY,
    user_id                  TEXT NOT NULL,
    token_hash               TEXT NOT NULL UNIQUE,
    csrf_token_hash          TEXT NOT NULL,
    auth_version             INTEGER NOT NULL,

    created_at               TEXT NOT NULL,
    expires_at               TEXT NOT NULL,
    idle_expires_at          TEXT NOT NULL,
    last_seen_at             TEXT NOT NULL,
    last_reauthenticated_at  TEXT,
    revoked_at               TEXT,
    revoke_reason            TEXT,

    ip_address               TEXT,
    user_agent               TEXT,

    FOREIGN KEY(user_id) REFERENCES users(id)
);
```

### 10.3 `password_reset_tickets`

```sql
CREATE TABLE password_reset_tickets (
    id           TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    token_hash   TEXT NOT NULL UNIQUE,
    created_by   TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    expires_at   TEXT NOT NULL,
    consumed_at  TEXT,
    revoked_at   TEXT,

    FOREIGN KEY(user_id) REFERENCES users(id)
);
```

### 10.4 `member_fund_holdings`

```sql
CREATE TABLE member_fund_holdings (
    id                   TEXT PRIMARY KEY,
    member_user_id       TEXT NOT NULL,
    fund_id              TEXT NOT NULL,
    share_quantity       TEXT NOT NULL,
    cumulative_invested  TEXT NOT NULL,
    confirmed_at         TEXT,
    as_of                TEXT NOT NULL,
    source               TEXT NOT NULL,
    status               TEXT NOT NULL,
    row_version          INTEGER NOT NULL DEFAULT 1,
    updated_by           TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL,

    UNIQUE(member_user_id, fund_id),
    FOREIGN KEY(member_user_id) REFERENCES users(id),
    FOREIGN KEY(fund_id) REFERENCES funds(id)
);
```

该表是客户展示读模型，不是正式清算账本。`source` 第一阶段至少允许：

```text
manual_admin
migration
external_import
```

### 10.5 `fund_nav_snapshots`

```sql
CREATE TABLE fund_nav_snapshots (
    id              TEXT PRIMARY KEY,
    fund_id         TEXT NOT NULL,
    valuation_time  TEXT NOT NULL,
    unit_nav        TEXT NOT NULL,
    currency        TEXT NOT NULL,
    source          TEXT NOT NULL,
    status          TEXT NOT NULL,
    created_at      TEXT NOT NULL,

    UNIQUE(fund_id, valuation_time),
    FOREIGN KEY(fund_id) REFERENCES funds(id)
);
```

`funds` 增加 nullable `fund_code`，并使用非空部分唯一索引。真实基金代码不在 Seed 或设计文档中虚构。

### 10.6 审计字段

复用 `audit_events`，增量增加：

```text
actor_user_id
request_id
result
ip_address
auth_method
```

新列保持可空，兼容现有审计写入。

## 11. 数据权威分类

| 数据 | 权威类型 | Owner | 非权威用途 |
|---|---|---|---|
| 用户、Session、重置凭证 | 身份与安全状态 | user identity repository | 前端缓存不得成为权威 |
| 会员持仓 | 客户报告读模型 | user/member holding repository | 不作为正式清算账本 |
| 基金单位净值 | 客户报告市场/估值输入 | fund NAV repository | 不直接等同策略 NAV |
| `strategy_nav_snapshots` | 策略运营净值 | 现有策略模块 | 不能冒充基金单位净值 |
| `financial_facts` | 正式经济事实 | 现有正式会计模块 | 不由用户系统改写 |

用户系统不得修改 `financial_facts`、正式 PnL、订单或执行账本。

## 12. 金融计算

所有计算在后端 `Decimal` 边界完成：

```python
market_value = share_quantity * latest_unit_nav
cumulative_return = market_value - cumulative_invested
return_rate = (
    cumulative_return / cumulative_invested
    if cumulative_invested != Decimal("0")
    else None
)
```

规则：

- 输入拒绝指数格式、NaN、Infinity 和负值；
- 计算精度、存储精度和显示位数分离；
- API 返回字符串；
- 没有 NAV 时相关结果为 `null`；
- NAV 超过配置的新鲜度阈值时返回 `stale`；
- 第一阶段默认全局阈值可配置，建议 36 小时；未来可按基金配置；
- 持仓更新使用 `expectedVersion` 乐观锁。

## 13. 后端模块边界

在不过度拆分的前提下：

```text
app/auth.py
    Principal、凭证选择、API-Key/Session 认证、保障等级、Request State

app/user_schemas.py
    用户系统请求/响应模型、错误码、分页 DTO

app/user_repository.py
    用户、Session、重置凭证、持仓、NAV、事务性审计 SQL

app/user_service.py
    注册、登录、资料、角色目标、Session、密码、头像和管理用例

app/user_routes.py
    /auth、/me、/users 路由与显式权限依赖

app/schema_migrations.py
    Migration 5/6
```

若 `user_service.py` 在实现中出现两个明显独立责任，可只提取一个 `member_holding_service.py`；不得预先拆成大量微型 Policy。

### 13.1 中间件与路由依赖

中间件负责：

- Request ID；
- 凭证歧义拒绝；
- 认证；
- Principal；
- 保障等级基础校验；
- 认证拒绝审计。

路由依赖负责：

```python
require_auth_method("session")
require_permission("user.read")
require_recent_reauth()
```

服务层负责目标角色、字段、数据范围和事务规则。

### 13.2 现有路径权限兼容

`permission_for_request()` 继续服务未迁移旧路由。新用户系统路由全部使用显式依赖，并增加架构测试：除注册、登录和密码重置使用外，任何用户系统路由缺少权限/认证声明均失败。

## 14. API 合同

统一前缀：

```text
/api/v1
```

### 14.1 公开认证

```http
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/reset-password
```

### 14.2 Session 认证

```http
GET  /api/v1/auth/me
POST /api/v1/auth/logout
POST /api/v1/auth/reauth
```

`GET /auth/me` 返回：

```text
user
roles
permissions
csrfToken
session
```

不返回后台菜单树。前端使用本地统一路由注册表根据权限生成菜单，避免前后端维护两套菜单事实。

### 14.3 个人账号

```http
GET    /api/v1/me
PATCH  /api/v1/me/profile
POST   /api/v1/me/contact

POST   /api/v1/me/avatar
DELETE /api/v1/me/avatar

POST   /api/v1/me/password

GET    /api/v1/me/sessions
DELETE /api/v1/me/sessions/{session_id}
POST   /api/v1/me/sessions/revoke-others

GET    /api/v1/me/holdings
```

联系方式单独使用 `POST /me/contact`，便于强制当前密码或近期再认证，不把安全验证混入普通资料 PATCH。

### 14.4 用户管理

```http
GET   /api/v1/users
POST  /api/v1/users
GET   /api/v1/users/{user_id}
PATCH /api/v1/users/{user_id}

POST /api/v1/users/{user_id}/approve
POST /api/v1/users/{user_id}/reject
POST /api/v1/users/{user_id}/role
POST /api/v1/users/{user_id}/enable
POST /api/v1/users/{user_id}/disable
POST /api/v1/users/{user_id}/password-reset-tickets
POST /api/v1/users/{user_id}/sessions/revoke

GET /api/v1/users/{user_id}/audit-events
```

没有 DELETE 用户接口。

### 14.5 持仓

```http
GET /api/v1/users/{user_id}/holdings
PUT /api/v1/users/{user_id}/holdings/{fund_id}
```

会员本人只使用 `/me/holdings`，管理接口必须经过 `member.holding.read_all/update` 和目标范围。

### 14.6 并发合同

关键写请求包含：

```json
{
  "expectedVersion": 3
}
```

版本不匹配返回 `409 stale_version`，响应包含当前版本但不包含无权字段。

### 14.7 错误合同

统一错误结构：

```json
{
  "code": "permission_denied",
  "message": "Permission denied",
  "requestId": "...",
  "fieldErrors": []
}
```

核心机器码：

```text
invalid_credentials
account_pending
account_disabled
account_temporarily_locked
ambiguous_credentials
session_expired
csrf_invalid
recent_reauth_required
permission_denied
target_scope_denied
last_ceo_protected
self_role_change_denied
self_disable_denied
stale_version
reset_ticket_invalid
reset_ticket_expired
nav_unavailable
nav_stale
```

HTTP 语义：

| HTTP | 用途 |
|---:|---|
| 400 | 请求结构或歧义凭证 |
| 401 | 未认证、Session 过期、密码/重置凭证无效 |
| 403 | 权限、认证方式、字段或目标范围拒绝 |
| 404 | 资源不存在或隐藏存在性 |
| 409 | 唯一冲突、状态冲突、最后 CEO、乐观锁冲突 |
| 413 | 文件过大 |
| 415 | 媒体类型不支持 |
| 422 | 字段、密码、角色或 Decimal 校验 |
| 423 | 临时安全锁定 |
| 429 | 频率限制 |
| 503 | 安全配置缺失且必须 fail-closed |

## 15. 头像存储

目录：

```text
<platform-data-directory>/avatars/
```

流程：

```text
stream upload with size cap
→ image decoder validation
→ dimension/pixel cap
→ strip metadata
→ center crop/fit
→ re-encode 512×512 WebP
→ UUID key
→ atomic temp-file rename
→ database update + audit
→ best-effort remove replaced file after commit
```

安全要求：

- 不信任文件名和 MIME Header；
- 不使用用户路径；
- 防止解压炸弹和超高像素；
- 响应 `Content-Type: image/webp`、私有缓存、ETag；
- 用户和持仓相关 API 使用 `Cache-Control: no-store`；
- 头像文件备份与数据库备份保持一致。

## 16. 前端架构

### 16.1 API 客户端

新增：

```text
platform-web/src/api/platform/userSystem.ts
```

使用现有 Platform API 客户端边界。浏览器 Session 依赖同源 Cookie，不设置 Bearer Token。

### 16.2 内存身份状态

```text
user
roles
permissions
csrfToken
session
hydrationStatus
```

不持久化认证 Token。页面刷新：

```text
app bootstrap
→ GET /auth/me
→ build permission registry
→ register routes
→ render
```

### 16.3 权限注册表

建议：

```text
platform-web/src/access/userAccess.ts
```

记录：

```text
route
component
title
requiredPermissions
placement
field capabilities
action capabilities
```

菜单和路由从同一注册表生成。

内部用户：

```text
风控管理
├─ 用户管理
└─ 个人账号
```

会员：

```text
个人账号
```

统一路由 `/account`，旧 `/risk/profile` 只做重定向。

### 16.4 401/403

- 401：清理内存状态，跳转登录并保留安全的站内 redirect；
- 403：显示无权限状态，不伪装成空数据；
- `recent_reauth_required`：打开再认证弹窗，成功后只重试明确幂等或用户确认的操作；
- 不自动重试密码、角色、停用、持仓等非幂等写入。

### 16.5 页面边界

```text
src/views/account/index.vue
    Profile/Security
    Holdings
    Sessions

src/views/users/index.vue
    filters + paged table
    UserDetailDrawer
    dangerous action modals
```

允许合并简单组件，不机械创建目录。

## 17. 审计

### 17.1 成功写入

敏感业务写入和审计必须使用同一数据库事务：

```text
BEGIN
→ validate current row/version/target policy
→ update state
→ insert audit event
→ COMMIT
```

审计失败则回滚。

### 17.2 拒绝事件

认证/授权拒绝审计为 best-effort persistence，但原请求始终拒绝，不得 fail-open。

### 17.3 内容

记录：

```text
actor user id
auth method
roles
target type/id
event type
result
request id
source ip
reason
changed field names
non-sensitive before/after status
```

不记录原始秘密或完整客户明细。

## 18. 初始 CEO

命令：

```powershell
python -m app.user_cli create-ceo
```

要求：

- 仅本地主机交互运行；
- `getpass` 输入密码；
- 不支持命令行密码参数；
- 使用 `BEGIN IMMEDIATE`；
- 仅当数据库没有 active CEO 时允许；
- 创建用户和审计同事务；
- 不输出密码或哈希；
- 不自动转换旧 `admin`。

## 19. 最后一个 CEO 并发保护

对降级或停用 CEO：

```text
BEGIN IMMEDIATE
→ load target and expected row_version
→ reject self role/disable
→ count active CEOs excluding target
→ require count >= 1
→ update target + auth_version + row_version
→ revoke sessions
→ write audit
→ COMMIT
```

并发测试必须覆盖两个 CEO 同时被不同请求降级或停用，确保至少一个保留。

## 20. 迁移计划

现有 Migration 1—4 不修改。

### Migration 5 — `user-identity-security-and-audit`

- `users`；
- `user_sessions`；
- `password_reset_tickets`；
- 用户、状态、角色、Session 和凭证索引；
- `audit_events` 增量查询字段；
- 不创建带默认密码的 CEO。

### Migration 6 — `member-holdings-and-fund-nav`

- `funds.fund_code` nullable；
- 非空部分唯一索引；
- `member_fund_holdings`；
- `fund_nav_snapshots`；
- Decimal 文本、来源、时点和版本字段；
- 不回填虚构真实基金代码。

每个迁移测试：

- 全新数据库；
- 现有 0.9.0 数据库升级；
- 重复初始化；
- checksum drift；
- 失败回滚；
- 外键和索引；
- 现有交易、正式财务和审计数据不变。

## 21. 旧系统兼容

### 21.1 没有真实旧用户

- 不导入旧 MySQL；
- 使用 CEO CLI；
- 前端认证切换到 Platform API；
- 旧 auth-service 暂时保留但不接收新用户流量；
- 后续独立 Issue 清理。

### 21.2 存在真实旧用户

先只读盘点数量、角色、状态和哈希算法，不输出敏感值。映射：

```text
guest    → member
employee → employee
admin    → 人工指定 ceo 或 tech_lead
```

- 不迁移旧 Session；
- 不自动把 admin 升为 CEO；
- bcrypt 仅在确认需要时做首次登录升级；
- 迁移工具必须幂等、可 dry-run、只记录统计和脱敏错误；
- 真实数据导入不与通用代码 Seed 混合。

## 22. 部署与数据保护

- 前端和 API 保持同源 `/api/v1`；
- 生产 Session 要求 TLS；
- SQLite、头像目录和备份使用受限文件权限；
- 第一阶段不做字段级加密；该限制必须在部署文档中明确；
- 备份介质不得进入 Git 或普通共享目录；
- Nginx 对登录、注册和重置使用设置粗粒度 rate limit；
- 应用层执行账号/用户名维度限制；
- 部署前备份数据库、头像目录和代理配置。

## 23. 可观测性

建议增加聚合指标或结构化日志：

```text
auth_login_success_total
auth_login_failure_total
auth_lockout_total
auth_session_active
auth_session_revoked_total
auth_permission_denied_total
user_registration_pending
user_sensitive_action_total
audit_persistence_failure_total
member_nav_stale_total
```

日志不包含密码、Token、完整联系方式和完整持仓。

## 24. 设计决策记录

### ADR-US-001：Platform API 单一身份权威

接受。避免旧 Go、前端本地状态和 Platform Principal 三套事实并存。

### ADR-US-002：服务端 Session 而非浏览器长期 JWT

接受。支持即时撤销、角色变化、停用和设备管理。

### ADR-US-003：客户身份接口 Session-only

接受。API-Key wildcard 不等同人类 CEO。

### ADR-US-004：Live 路由继续 API-Key-only

接受。Issue #117 不重新设计浏览器 Live 认证。

### ADR-US-005：一次性密码重置凭证

接受。拒绝管理员设置或掌握临时密码。

### ADR-US-006：生命周期状态与临时锁定分离

接受。避免 `locked` 状态与自动解锁、停用相互冲突。

### ADR-US-007：前端本地权限注册表

接受。后端返回权限，不返回菜单树，避免双菜单事实。

### ADR-US-008：持仓为客户报告读模型

接受。不得冒充正式会计或申赎清算账本。

### ADR-US-009：第一阶段不硬删除用户

接受。使用停用和拒绝保持引用与审计连续性。

## 25. 被拒绝方案

- 继续扩展旧 Go auth-service：拒绝，造成双身份权威和本地启动缺口；
- 在前端保存角色并只隐藏菜单：拒绝，无法防 API 越权；
- API-Key admin 自动映射 CEO：拒绝，自动化凭证不应管理客户身份；
- 管理员查看或设置临时密码：拒绝；
- 把临时登录锁定做成用户状态：拒绝；
- 直接使用策略 NAV 计算会员基金市值：拒绝；
- 第一阶段引入微服务、IAM 或对象存储：拒绝，超出当前规模和闭环目标。

## 26. Cutover and rollback gates

The implementation remains fail-closed until three deployment facts are resolved: whether real legacy users require import, which source is authoritative for member holdings, and whether the production origin/TLS/proxy/cookie topology is verified. Import and migration tooling must be idempotent, dry-run capable, redacted and append-only. A failed cutover restores the database, avatar storage and proxy configuration as one deployment unit; it must not split identity authority between Platform API and a legacy service.
