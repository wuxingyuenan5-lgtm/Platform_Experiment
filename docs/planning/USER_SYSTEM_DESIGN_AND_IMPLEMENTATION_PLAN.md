# 用户系统设计与实施计划

状态：`approved design baseline / implementation not started`  
适用版本：`Platform Experiment 0.9.0`  
Issue：`#117`  
任务包：`tasks/issue-117-user-system.md`  
基线提交：`71603bcc6807284ef3a6da26ad3f43c541bc99c2`

## 1. 文档目的

本文档定义第一阶段用户系统的完整设计基线，包括：

- 浏览器用户注册、登录和服务端 Session；
- CEO、技术负责人、员工、会员四类业务角色；
- 菜单、路由、页面、字段、操作、API 和数据范围权限；
- 个人账号、头像、密码和登录设备管理；
- 后台用户管理；
- 会员基金持仓和基金净值展示；
- 审计、安全、数据库迁移、兼容和回滚；
- 分批实施、测试与验收计划。

本文档描述目标设计，不代表当前代码已经具备这些能力。设计批准后仍必须按 Critical 工作流实施、测试并通过完整 CI，才可进入 `main`。

## 2. 不可改变的安全边界

本工作不得改变以下行为：

- Market、FOK、PostOnly、TP/SL 的执行语义；
- 跨所价差的定价、数量、开平仓顺序、补偿和对账逻辑；
- Platform Live Write 和 Runtime Live Write 默认关闭；
- LiveTradingSession、Kill Switch、绝对限额和对账阻断；
- 外部结果未知时保持未知，不进行盲目重复提交；
- Platform Backend 不直接引入 Venue SDK；
- 密码、原始 Session Token、API Key 和客户敏感数据不得进入日志、响应、测试样例或 Git。

CEO 的“全部业务权限”不能绕过上述交易和实盘安全闸门。

## 3. 第一阶段边界

### 3.1 第一阶段必须完成

```text
注册申请
→ 后台审核
→ 用户登录
→ 服务端识别身份、角色和权限
→ 前端生成对应菜单
→ 路由、页面、字段和按钮按权限展示
→ 后端再次校验权限和数据范围
→ 用户维护个人资料、头像、密码和 Session
→ 管理员管理用户
→ 会员查看自己的基金持仓
→ 敏感操作形成审计记录
```

### 3.2 第一阶段不做

- 社交登录；
- 短信或邮件验证码登录；
- 邮件或短信找回密码；
- 企业 SSO、IAM 或多租户；
- 任意自定义角色和可视化权限编辑器；
- 每个用户单独覆盖权限；
- 基金申购、赎回、支付、清算和结算；
- 独立对象存储服务；
- 与用户系统无关的交易、Runtime、风险或数据服务重构；
- 为了架构形式拆分大量微型 Policy/Repository/Service 文件；
- 在同一工作中主动删除旧 Go 服务。

## 4. 当前现状与主要缺口

### 4.1 当前正式安全能力

`platform-backend/app/auth.py` 已有：

- API-Key Bearer 认证；
- `Principal`；
- 固定角色到权限的映射；
- HTTP 请求默认拒绝；
- Actor Binding；
- 鉴权拒绝审计；
- Live 环境禁止 Development Identity。

这一能力是现有交易、风险和 LiveTradingSession 安全链路的一部分，必须保留。

### 4.2 当前浏览器登录仍依赖旧服务

前端认证客户端仍指向旧 `/api/auth` 代理，实际对应 `projects/risk-control/auth-service`。该服务使用 Go、MySQL、JWT 和角色字符串；一键本地启动脚本却只启动 Runtime、Platform Backend 和前端，因此现有登录、用户、平台 API 不是一个完整闭环。

### 4.3 当前用户页面主要是演示实现

当前用户管理页面主要包含：

- 当前登录用户展示；
- 静态角色矩阵；
- 注册申请批准和拒绝。

尚不具备完整用户分页、搜索、状态、详情、角色保护、密码重置、Session 强退、持仓和审计管理。

当前个人账号页面将名称、头像 URL 和说明写入浏览器 `localStorage`，不属于权威用户数据；头像允许任意 URL；基金曲线实际使用通用交易账户净值组件，不是会员基金持仓。

### 4.4 当前权限主要是角色字符串过滤

当前菜单和按钮大量依赖：

```text
admin
employee
guest
```

这种方式不能表达字段脱敏、数据范围、目标用户等级、真实交易限制和操作审计，也无法安全支持技术负责人和会员。

### 4.5 当前会员数据存在潜在横向访问问题

旧数据接口允许客户端传入账户标识查询净值，且部分读取接口没有统一身份和数据范围校验。会员数据必须改为从认证 Principal 推导本人范围，不能相信客户端提供的用户或账户标识。

## 5. 目标架构

### 5.1 单一权威边界

```text
admin-risk
    ↓
platform-backend
    ├─ 用户身份与密码
    ├─ 浏览器 Session
    ├─ 业务角色与权限
    ├─ 用户资料
    ├─ 会员基金持仓
    └─ 用户系统审计
```

`platform-backend` 成为浏览器用户、Session、RBAC、会员持仓和用户审计的唯一权威。

旧 Go 服务暂不在本批删除，但不再扩展为新用户系统的权威实现。旧数据服务可以继续承载与本次无关的旧页面，直到后续独立迁移。

### 5.2 两种认证方式，共用一个 Principal

```text
浏览器用户
→ HttpOnly Session Cookie
→ Session 验证
→ 当前用户与角色查询
→ Principal

自动化或 Live 客户端
→ Bearer API Key
→ API-Key 验证
→ Principal
```

统一 Principal 建议字段：

```text
user_id
roles
permissions
auth_method        session | api_key | development
session_id         浏览器 Session 适用
credential_id      API Key 适用
```

### 5.3 人类账号写操作与 API Key 的边界

API-Key `admin` 的通配权限不应自动等同于业务 CEO。

第一阶段规则：

- 用户创建、角色变化、账号停用、密码重置等人类账号生命周期写操作要求 `auth_method=session`；
- 同时要求对应业务角色和权限；
- API-Key Principal 继续用于自动化、系统 API 和现有 Live 链路；
- API Key 不得绕过最后一个 CEO、禁止自我提权和受保护角色规则。

## 6. 角色与权限模型

### 6.1 角色代码

浏览器业务角色固定为：

```text
ceo
tech_lead
employee
member
```

现有 API-Key 角色保持兼容：

```text
viewer
researcher
trader
risk_officer
operations
admin
```

两组角色不能通过名称自动互相映射。旧 `admin` 用户或 API-Key 不能因为名称相似而自动成为 CEO。

### 6.2 权限点原则

底层关系：

```text
User
→ Role
→ Permission Set
```

第一阶段采用固定角色和固定权限映射，不开发权限编辑器。

现有权限名称如 `platform:read`、`trade:submit`、`risk:manage` 保持不变，避免全局重命名。新增用户域使用点式命名：

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

risk.read
trade.read
system.read
system.manage
```

### 6.3 授权必须分两层

```text
权限点校验
→ 当前身份是否具备某类能力

目标与数据范围校验
→ 是否允许操作这个具体用户、字段或持仓
```

仅有 `user.update` 不代表可以修改 CEO、技术负责人或自己。

## 7. 角色权限矩阵

### 7.1 总体能力

| 能力 | CEO | 技术负责人 | 员工 | 会员 |
|---|---|---|---|---|
| 内部后台导航 | 全部 | 绝大部分 | 正常业务后台 | 不可见 |
| 风控、策略、报表读取 | 全部 | 可读 | 可读 | 拒绝 |
| 系统运行和技术配置 | 全部 | 可管理 | 默认拒绝 | 拒绝 |
| 用户列表 | 全部字段 | 全部字段 | 只读脱敏 | 拒绝 |
| 创建会员或员工 | 允许 | 允许 | 拒绝 | 拒绝 |
| 创建技术负责人 | 允许 | 拒绝 | 拒绝 | 拒绝 |
| 创建 CEO | 允许，且不能破坏最后 CEO 规则 | 拒绝 | 拒绝 | 拒绝 |
| 修改普通用户 | 允许 | 允许 | 拒绝 | 拒绝 |
| 修改 CEO | 受最后 CEO 约束 | 拒绝 | 拒绝 | 拒绝 |
| 修改其他技术负责人 | 允许 | 拒绝 | 拒绝 | 拒绝 |
| 修改自己角色 | 拒绝 | 拒绝 | 拒绝 | 拒绝 |
| 停用自己 | 拒绝 | 拒绝 | 拒绝 | 拒绝 |
| 重置普通用户密码 | 允许 | 允许 | 拒绝 | 拒绝 |
| 强制普通用户退出 | 允许 | 允许 | 拒绝 | 拒绝 |
| 查看本人持仓 | 允许 | 有本人持仓时允许 | 有本人持仓时允许 | 允许 |
| 查看全部会员持仓 | 允许 | 默认拒绝 | 拒绝 | 拒绝 |
| 修改会员持仓 | 允许 | 默认拒绝 | 拒绝 | 拒绝 |
| 真实交易能力 | 业务上允许，但仍需现有 Live 全链路 | 默认拒绝 | 拒绝 | 拒绝 |
| 修改核心风控参数 | 允许，但仍受现有安全规则 | 默认拒绝 | 拒绝 | 拒绝 |
| 查看用户审计 | 全部 | 普通用户范围 | 默认拒绝 | 仅本人安全记录 |

### 7.2 推荐固定权限映射

CEO：

```text
*
```

CEO 的 `*` 不绕过领域安全规则和 Live 安全闸门。

技术负责人：

```text
platform:read
audit:read
system.read
system.manage

user.read
user.sensitive.read
user.create
user.update
user.disable
user.reset_password
user.assign_role
user.session.revoke
user.audit.read

profile.read_self
profile.update_self
profile.avatar.update_self
profile.password.change_self
session.read_self
session.revoke_self

member.read_self
member.read_all
member.holding.read_self

risk.read
trade.read
```

员工：

```text
platform:read
risk.read
trade.read
user.read

profile.read_self
profile.update_self
profile.avatar.update_self
profile.password.change_self
session.read_self
session.revoke_self

member.read_self
member.holding.read_self
```

会员：

```text
profile.read_self
profile.update_self
profile.avatar.update_self
profile.password.change_self
session.read_self
session.revoke_self

member.read_self
member.holding.read_self
```

### 7.3 受保护目标规则

后端服务层必须强制：

1. 系统始终至少存在一个 `active` CEO；
2. 任何用户不能修改自己的角色；
3. 任何用户不能停用自己；
4. 技术负责人不能创建、编辑、停用或重置 CEO；
5. 技术负责人不能创建、编辑、停用或重置其他技术负责人；
6. 技术负责人只能分配 `employee` 或 `member`；
7. 员工不能执行任何用户写操作；
8. 会员不能访问用户管理 API；
9. API-Key Principal 默认不能执行人类账号生命周期写操作；
10. CEO 的通配权限不能取消最后一个 CEO，也不能绕过 Live 安全。

最后一个 CEO 检查必须在数据库写事务中进行，建议 SQLite `BEGIN IMMEDIATE`，避免两个并发操作同时通过预检查。

## 8. 字段权限和脱敏

### 8.1 字段修改矩阵

| 字段 | 本人 | CEO | 技术负责人 | 员工查看他人 |
|---|---:|---:|---:|---:|
| 用户名 | 不可修改 | 不可修改 | 不可修改 | 只读 |
| 展示名称 | 可修改 | 可修改 | 可修改普通用户 | 只读 |
| 真实姓名 | 不可修改 | 可修改 | 可修改普通用户 | 脱敏或按工作需要显示 |
| 头像 | 可修改 | 可修改 | 可修改普通用户 | 只读 |
| 手机号 | 可修改本人 | 可修改 | 可修改普通用户 | 脱敏 |
| 邮箱 | 可修改本人 | 可修改 | 可修改普通用户 | 脱敏 |
| 角色 | 不可修改 | 可修改 | 仅会员/员工 | 只读 |
| 部门或会员类型 | 不可修改 | 可修改 | 可修改普通用户 | 只读 |
| 状态 | 不可修改 | 可修改 | 仅会员/员工 | 只读 |
| 密码 | 修改本人 | 重置他人 | 重置普通用户 | 仅修改本人 |

用户名第一阶段不可变，避免影响登录、审计和历史关联。

修改手机号或邮箱时要求当前密码，并在成功后记录审计。

### 8.2 脱敏必须在后端完成

员工列表响应示例：

```text
张伟          → 张*
13800138000   → 138****8000
user@example.com → u***@example.com
```

没有 `user.sensitive.read` 时，后端只返回：

```text
phoneDisplay
emailDisplay
```

不能将完整数据返回前端后再用 CSS 或组件隐藏。

### 8.3 会员资金字段

以下字段属于财务敏感信息：

- 持有份额；
- 累计投入；
- 持仓市值；
- 累计收益；
- 收益率。

没有 `member.holding.read_all` 时，后端不得返回其他会员的这些字段。

## 9. 注册与审核设计

### 9.1 统一入口

现有登录页面继续作为员工和会员的统一登录入口，保留当前浅蓝灰白、蝴蝶拓扑背景和卡片视觉。

登录卡片底部保留：

```text
没有账号？提交注册申请
```

### 9.2 公开注册字段

```text
用户名
姓名
邮箱或手机号（至少一项）
申请身份：会员 / 员工
部门（员工申请时必填）
会员类型（会员申请时可选）
申请说明
密码
确认密码
隐私政策确认
```

公开页面不显示 CEO 或技术负责人。

### 9.3 注册状态

公开注册一律创建：

```text
status = pending
role_code = NULL
requested_role_code = member | employee
```

任何公开申请都不能自动获得登录权限。

### 9.4 审核流程

```text
申请提交
→ pending 用户
→ CEO 或技术负责人审核
→ 审核人选择最终角色
→ active
→ 用户可登录
```

技术负责人只能批准为会员或员工。

审核人可以将员工申请降为会员，不能盲目执行 `role=requested_role`。

拒绝必须填写理由；拒绝结果和理由可供后台查看，但公开登录接口不泄露内部审核人信息。

## 10. 用户状态模型

状态：

```text
pending
active
disabled
locked
rejected
```

允许转换：

```text
pending  → active
pending  → rejected
active   → disabled
disabled → active
active   → locked
locked   → active
```

含义：

- `pending`：等待审核，不能登录；
- `active`：正常；
- `disabled`：管理员停用；
- `locked`：安全锁定；
- `rejected`：注册申请已拒绝。

登录失败策略建议：

```text
连续失败 5 次
→ 临时锁定 15 分钟
```

成功登录后失败计数清零。具体阈值应成为可配置安全参数，但不得由普通业务用户修改。

## 11. 密码与登录安全

### 11.1 密码存储

- 使用 Argon2id；
- 通过维护中的 Python 库实现，并在实施时固定依赖版本；
- 数据库只保存密码哈希；
- 管理员不能查看用户原密码；
- 日志、错误响应、审计和测试快照不记录密码。

### 11.2 密码规则

建议：

- 长度 12—128 字符；
- 不能与用户名相同；
- 不能包含完整邮箱或手机号；
- 拒绝常见弱密码；
- 允许较长的中文或英文口令；
- 前端提示只用于体验，后端执行权威校验。

不将“大写、小写、数字、特殊字符必须同时存在”作为唯一安全标准。

### 11.3 登录响应

账号不存在或密码错误时统一返回：

```text
账号或密码错误
```

避免泄露账号是否存在。

密码验证成功后，待审核、停用或锁定账号可以返回对应状态提示。

### 11.4 用户修改密码

```text
当前密码
新密码
确认新密码
→ 校验
→ 更新哈希
→ auth_version + 1
→ 撤销全部 Session
→ 返回登录页
```

### 11.5 管理员重置密码

管理员在重置弹窗中输入临时密码：

```text
→ 后端保存哈希
→ must_change_password = true
→ auth_version + 1
→ 撤销目标用户全部 Session
```

后端响应不回显临时密码。

用户使用临时密码登录后，只允许进入强制修改密码流程，完成修改前不能访问其他业务页面。

## 12. 浏览器 Session 设计

### 12.1 Session Cookie

```text
Cookie Name: vg_session
HttpOnly: true
SameSite: Lax
Path: /
Secure: 生产环境 true
```

Session Token 使用密码学安全随机值，建议至少 256 位熵。数据库只保存 SHA-256，不保存原文。

### 12.2 前端存储原则

浏览器认证信息不再长期保存在：

```text
localStorage
sessionStorage
Pinia 持久化 Token 缓存
```

Pinia 只保存当前页面生命周期内的用户资料、角色和权限。刷新页面后调用：

```http
GET /api/v1/auth/me
```

重新获得用户、权限和 CSRF 信息。

### 12.3 CSRF

所有 Cookie 认证的写操作要求：

```text
X-CSRF-Token
```

流程：

- 登录或 `/auth/me` 返回 CSRF Token；
- 前端只保存在内存；
- Session 表保存其哈希；
- 后端校验 Token 和可信 `Origin`；
- API-Key Bearer 请求不使用浏览器 CSRF 流程。

### 12.4 Session 即时失效

用户表保存：

```text
auth_version
```

Session 创建时复制当前版本。

以下操作递增版本：

- 修改角色；
- 停用账号；
- 用户修改密码；
- 管理员重置密码；
- 其他重大权限变化。

每次请求检查：

```text
session.auth_version == user.auth_version
```

不一致立即拒绝并撤销 Session，避免旧角色权限长期存在。

### 12.5 Session 管理

个人账号提供：

- 当前 Session；
- 其他设备的创建时间、最近活动、IP 摘要和 User-Agent 摘要；
- 退出单个其他 Session；
- 退出所有其他 Session。

管理员可对普通用户执行“强制退出全部 Session”。

## 13. 头像设计

第一阶段不引入对象存储。

配置数据目录：

```text
<platform-data-directory>/avatars/
```

不得放入源码目录或 Git。

上传流程：

```text
上传
→ 最大 2 MB
→ 解码检查真实文件类型
→ 检查尺寸和总像素
→ 自动裁剪或缩放
→ 重新编码为 512×512 WebP
→ UUID 文件名
→ 更新 avatar_key
```

支持：

```text
JPEG
PNG
WebP
```

不保存未经处理的原始文件，不接受用户填写任意外部头像 URL。

读取接口要求认证：

```http
GET /api/v1/media/avatars/{avatar_key}
```

`avatar_key` 为空时使用前端平台默认头像。

## 14. 数据模型

所有时间均使用 timezone-aware UTC ISO 8601。

### 14.1 `users`

```sql
CREATE TABLE users (
    id                  TEXT PRIMARY KEY,
    username            TEXT NOT NULL,
    username_normalized TEXT NOT NULL UNIQUE,
    password_hash       TEXT NOT NULL,

    display_name        TEXT,
    real_name           TEXT,
    avatar_key          TEXT,
    phone               TEXT,
    phone_normalized    TEXT,
    email               TEXT,
    email_normalized    TEXT,

    role_code           TEXT,
    requested_role_code TEXT,
    department          TEXT,
    member_type         TEXT,
    application_note    TEXT,

    status               TEXT NOT NULL,
    must_change_password INTEGER NOT NULL DEFAULT 0,
    auth_version         INTEGER NOT NULL DEFAULT 1,
    failed_login_count   INTEGER NOT NULL DEFAULT 0,
    locked_until         TEXT,

    registered_at       TEXT NOT NULL,
    approved_at         TEXT,
    approved_by         TEXT,
    last_login_at       TEXT,
    password_changed_at TEXT,
    created_by          TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
```

约束：

- `username_normalized` 唯一；
- `email_normalized` 非空时唯一；
- `phone_normalized` 非空时唯一；
- `role_code` 仅允许 `ceo/tech_lead/employee/member` 或空；
- `requested_role_code` 公开注册仅允许 `employee/member`；
- `status` 仅允许规定状态；
- `pending` 用户必须没有正式 `role_code`；
- `active` 用户必须具有正式 `role_code`。

SQLite 可通过部分唯一索引实现非空邮箱和手机号唯一。

### 14.2 `user_sessions`

```sql
CREATE TABLE user_sessions (
    id               TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL,
    token_hash       TEXT NOT NULL UNIQUE,
    csrf_token_hash  TEXT NOT NULL,
    auth_version     INTEGER NOT NULL,

    created_at       TEXT NOT NULL,
    expires_at       TEXT NOT NULL,
    last_seen_at     TEXT NOT NULL,
    revoked_at       TEXT,
    revoke_reason    TEXT,

    ip_address       TEXT,
    user_agent       TEXT,

    FOREIGN KEY(user_id) REFERENCES users(id)
);
```

原始 Session 和 CSRF Token 只在客户端存在，不进入数据库。

### 14.3 `member_fund_holdings`

```sql
CREATE TABLE member_fund_holdings (
    id                  TEXT PRIMARY KEY,
    member_user_id      TEXT NOT NULL,
    fund_id             TEXT NOT NULL,
    share_quantity      TEXT NOT NULL,
    cumulative_invested TEXT NOT NULL,
    confirmed_at        TEXT,
    status              TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,

    UNIQUE(member_user_id, fund_id),
    FOREIGN KEY(member_user_id) REFERENCES users(id),
    FOREIGN KEY(fund_id) REFERENCES funds(id)
);
```

### 14.4 `fund_nav_snapshots`

```sql
CREATE TABLE fund_nav_snapshots (
    id             TEXT PRIMARY KEY,
    fund_id        TEXT NOT NULL,
    valuation_time TEXT NOT NULL,
    unit_nav       TEXT NOT NULL,
    currency       TEXT NOT NULL,
    source         TEXT NOT NULL,
    status         TEXT NOT NULL,
    created_at     TEXT NOT NULL,

    UNIQUE(fund_id, valuation_time),
    FOREIGN KEY(fund_id) REFERENCES funds(id)
);
```

现有 `funds` 增加：

```text
fund_code TEXT
```

使用非空唯一索引，允许已有行在迁移时暂时没有代码，再通过独立、可测试的回填步骤处理。

### 14.5 现有策略净值不能替代基金净值

`strategy_nav_snapshots` 表示策略实例净值，不等于会员购买基金的单位净值。第一阶段新增 `fund_nav_snapshots`，避免把策略运营数据错误呈现为客户基金净值。

## 15. 金融精度和持仓计算

权威计算：

```text
持仓市值 = 持有份额 × 最新单位净值
累计收益 = 持仓市值 - 累计投入
收益率   = 累计收益 ÷ 累计投入
```

规则：

- 后端使用 `Decimal`；
- SQLite 使用规范化十进制字符串；
- API 金融字段使用字符串；
- 前端 `Number` 只可用于图表坐标和非权威格式化；
- `累计投入 = 0` 时收益率返回 `null`；
- 没有净值时不使用零代替；
- 净值过期时明确返回 `stale`；
- 计算精度、量化位数和显示位数分离；
- 更新持仓时拒绝负份额、负投入和非法十进制格式。

持仓响应示例：

```json
{
  "fundId": "fund_example",
  "fundCode": "VG001",
  "fundName": "示例基金",
  "shareQuantity": "125000.0000",
  "latestUnitNav": "1.083452",
  "marketValue": "135431.500000",
  "cumulativeInvested": "120000.00",
  "cumulativeReturn": "15431.500000",
  "returnRate": "0.1285958333",
  "navUpdatedAt": "2026-07-26T08:00:00+00:00",
  "confirmedAt": "2026-04-02T00:00:00+00:00",
  "status": "active",
  "navStatus": "current"
}
```

该示例是虚构测试数据，不代表真实客户。

## 16. API 设计

统一前缀：

```text
/api/v1
```

### 16.1 公开认证 API

```http
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/logout
```

公开路由仅包括注册和登录。`/auth/me` 与退出登录要求有效 Session。

`GET /auth/me` 返回：

```text
user
role
permissions
menuProfile
session
csrfToken
mustChangePassword
```

### 16.2 个人账号 API

```http
GET    /api/v1/me
PATCH  /api/v1/me

POST   /api/v1/me/avatar
DELETE /api/v1/me/avatar

POST   /api/v1/me/password

GET    /api/v1/me/sessions
DELETE /api/v1/me/sessions/{session_id}
POST   /api/v1/me/sessions/revoke-others

GET    /api/v1/me/holdings
```

`GET /me/holdings` 不接受 `user_id` 或 `member_id`，身份直接来自 Principal。

### 16.3 用户管理 API

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
POST /api/v1/users/{user_id}/reset-password
POST /api/v1/users/{user_id}/sessions/revoke

GET /api/v1/users/{user_id}/audit-events
```

批准请求必须携带最终角色，而不是自动使用申请角色。

### 16.4 会员持仓管理 API

```http
GET /api/v1/users/{user_id}/holdings
PUT /api/v1/users/{user_id}/holdings/{fund_id}
```

第一阶段默认只有 CEO 具备 `member.holding.update`。

### 16.5 用户列表查询

```text
page
page_size
username
name
contact
role
status
created_from
created_to
last_login_from
last_login_to
sort=created_at | last_login_at | username
order=asc | desc
```

分页和排序规则：

- `page_size` 设置上限；
- 排序字段使用服务器白名单；
- 不直接将客户端字段拼接进 SQL；
- 搜索值规范化并转义；
- 返回 `items/total/page/pageSize`；
- 无权读取敏感字段时返回脱敏 DTO。

### 16.6 错误语义

| 状态码 | 含义 |
|---:|---|
| 400 | 请求格式错误 |
| 401 | 未认证、Session 失效或凭证错误 |
| 403 | 权限或数据范围拒绝 |
| 404 | 资源不存在，或为防止枚举而隐藏存在性 |
| 409 | 用户名冲突、状态冲突、最后 CEO 或并发冲突 |
| 413 | 头像文件过大 |
| 415 | 不支持的头像媒体类型 |
| 422 | 字段、密码、角色或金融数值校验失败 |
| 423 | 账号临时锁定 |
| 503 | 认证或安全配置缺失且必须 fail-closed |

## 17. 后端授权实现

### 17.1 中间件职责

认证中间件负责：

- Request ID；
- 识别 Session Cookie 或 Bearer API Key；
- 验证认证凭证；
- 构建 Principal；
- 基础认证拒绝；
- 记录认证/授权拒绝证据。

### 17.2 路由权限依赖

现有按 HTTP Method 和 URL 字符串推断权限的方式继续服务旧接口兼容，但新用户系统路由采用显式依赖：

```python
Depends(require_permission("user.read"))
```

禁止只依靠 URL 推断新增大量用户权限。

### 17.3 服务层领域规则

服务层负责：

- 受保护角色；
- 禁止自我提权；
- 禁止停用自己；
- 最后一个 CEO；
- 技术负责人目标范围；
- 会员本人数据范围；
- Session 即时失效；
- 敏感操作审计；
- 持仓 Decimal 计算。

### 17.4 预期模块边界

在不造成过度拆分的前提下，建议：

```text
app/auth.py              统一 Principal、API Key 和 Session 认证边界
app/user_schemas.py      用户系统公共请求/响应模型
app/user_repository.py   用户、Session、持仓和事务性审计 SQL
app/user_service.py      用户、权限目标、密码、持仓等用例规则
app/user_routes.py       认证、个人账号和用户管理路由
app/schema_migrations.py 增量迁移
```

头像文件 I/O 可以先保留在 `user_service.py` 的明确私有边界；只有出现真实第二责任或测试边界时再提取独立模块。

## 18. 审计设计

### 18.1 复用现有 `audit_events`

现有审计表继续作为权威记录。计划增量增加可查询字段：

```text
actor_user_id
request_id
result
ip_address
```

新列保持可空，避免破坏旧写入。

### 18.2 成功写操作必须事务性审计

对以下敏感成功操作：

```text
更新业务数据
+ 写审计事件
→ 同一事务提交
```

审计写入失败时敏感操作回滚。

认证和权限拒绝审计保持 fail-closed：即使审计持久化失败，原本应拒绝的请求仍然拒绝。

### 18.3 审计事件

```text
auth.login_succeeded
auth.login_failed
auth.logout
auth.permission_denied

user.registered
user.registration_approved
user.registration_rejected
user.created
user.updated
user.role_changed
user.enabled
user.disabled
user.password_changed
user.password_reset
user.session_revoked
user.avatar_changed

member.other_holdings_viewed
member.holding_updated
```

常规会员本人读取持仓可以不逐次写审计，避免噪音；管理员查看他人持仓必须审计。

### 18.4 审计内容

记录：

- 操作者；
- 目标对象；
- 操作类型；
- 结果；
- Request ID；
- 时间；
- 来源 IP；
- 修改字段名称；
- 状态前后值中的非敏感部分。

不记录：

- 密码或密码哈希；
- 原始 Session/CSRF Token；
- API Key；
- 完整请求体；
- 头像原始内容；
- 完整手机号、邮箱或基金客户明细快照。

## 19. 初始 CEO

禁止在 Seed、Markdown、测试输出或代码中保存默认 CEO 密码。

提供一次性交互命令：

```powershell
python -m app.user_cli create-ceo
```

交互输入：

```text
用户名
姓名
邮箱或手机号
密码
确认密码
```

要求：

- 使用 `getpass` 隐藏密码；
- 数据库没有有效 CEO 时才允许首次初始化；
- 已有 CEO 后只能由现有 CEO 创建新 CEO；
- 初始化写入审计；
- CI 通过测试 Fixture 创建虚构用户，不运行生产交互命令；
- 不将旧 Go 服务中的所有 `admin` 自动映射为 CEO。

## 20. 前端设计

### 20.1 API 边界

新接口放在：

```text
admin-risk/src/api/platform/userSystem.ts
```

不继续把新能力叠加到旧 `src/api/sys/user.ts`。旧客户端在切换完成前只作为兼容入口，完成后停止用户系统调用。

### 20.2 权限状态

前端用户状态包含：

```text
user
role
permissions
csrfToken
mustChangePassword
```

菜单、路由、按钮和字段展示读取权限集合，不直接判断角色名称。

前端权限仅用于体验，后端仍执行全部权威校验。

### 20.3 导航规则

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

个人账号统一真实路由：

```text
/account
```

旧路径：

```text
/risk/profile
```

保留重定向到 `/account`，避免旧书签失效。

导航注册使用单一配置：

```text
path
title
requiredPermissions
internalPlacement
memberPlacement
```

放置逻辑基于权限：

```text
有 risk.read
→ 放在风控管理下

没有 risk.read，但有 profile.read_self
→ 作为顶级个人账号
```

### 20.4 登录页面

保留现有截图中的：

- 浅蓝灰白背景；
- 蝴蝶和拓扑视觉；
- 中央登录卡片；
- 账号、密码、登录按钮；
- 注册申请入口。

增加：

- 登录加载状态；
- 通用错误提示；
- 待审核、停用、锁定状态提示；
- 强制修改密码跳转；
- 隐私政策入口；
- 窄屏基本可用性。

### 20.5 注册页面

使用同一背景和卡片体系，不再使用另一套深色视觉。

提交成功后显示明确状态并返回登录页：

```text
申请已提交，审核通过后方可登录
```

### 20.6 个人账号页面

建议三个页签：

```text
资料与安全
基金持仓
登录设备
```

会员默认进入“基金持仓”，内部用户默认进入“资料与安全”。

资料与安全：

- 头像；
- 用户名只读；
- 展示名称；
- 手机号；
- 邮箱；
- 角色只读；
- 部门或会员类型只读；
- 状态、注册时间和最近登录；
- 修改密码；
- 退出登录。

基金持仓：

- 汇总卡片；
- 持仓表；
- 基金净值更新时间；
- 缺失、过期和空状态；
- 可选基金净值曲线，但数据必须来自基金净值 API。

登录设备：

- 当前设备标记；
- 创建和最近活动时间；
- IP/User-Agent 摘要；
- 退出其他设备。

### 20.7 用户管理页面

页面结构：

```text
搜索与筛选
→ 用户列表
→ 用户详情抽屉
→ 危险操作确认弹窗
```

列表字段：

- 头像；
- 用户名；
- 姓名；
- 角色；
- 联系方式；
- 状态；
- 注册时间；
- 最近登录；
- 操作入口。

详情抽屉分区：

```text
基本资料
角色与权限
账号和 Session
会员持仓
登录记录
审计记录
```

危险操作必须提示影响：

- 停用将使已有 Session 失效；
- 角色变化将立即撤销旧权限；
- 重置密码将强制重新登录；
- 修改持仓会影响客户展示值；
- 最后一个 CEO 操作将被拒绝。

### 20.8 前端预期文件

```text
src/api/platform/userSystem.ts
src/access/userAccess.ts

src/views/users/index.vue
src/views/users/components/UserDetailDrawer.vue

src/views/account/index.vue
src/views/account/components/ProfilePanel.vue
src/views/account/components/HoldingsPanel.vue
src/views/account/components/SessionPanel.vue
```

允许根据现有组件实际边界合并文件，不要求为了匹配本文档机械创建全部文件。

## 21. 数据库迁移计划

现有迁移 1—4 不得修改。

建议新增：

### Migration 5 — `user-identity-and-sessions`

- `users`；
- `user_sessions`；
- 唯一索引；
- 状态、角色和 Session 查询索引；
- 不创建带密码的默认 CEO。

### Migration 6 — `member-holdings-and-fund-nav`

- `funds.fund_code`；
- `member_fund_holdings`；
- `fund_nav_snapshots`；
- 精确十进制约束和查询索引。

### Migration 7 — `user-audit-query-fields`

- `audit_events.actor_user_id`；
- `audit_events.request_id`；
- `audit_events.result`；
- `audit_events.ip_address`；
- 用户和目标对象查询索引。

每个迁移必须覆盖：

- 全新数据库；
- 已有 0.9.0 数据库升级；
- 重复初始化；
- 校验和漂移失败；
- 外键和索引；
- 已有交易、财务和审计数据不变。

## 22. 旧系统兼容策略

### 22.1 没有真实旧用户数据

- 不导入旧 MySQL 用户；
- 通过交互命令创建初始 CEO；
- 前端切换到 Platform Backend；
- 旧 auth-service 暂时保留但不接收新用户流量；
- 后续使用独立 Issue 清理死代码和部署配置。

### 22.2 已有真实旧用户数据

需要先获得实际数据清单，再开发一次性只读迁移工具：

```text
guest    → member
employee → employee
admin    → 必须人工指定 ceo 或 tech_lead
```

规则：

- 旧 Session 不迁移；
- 所有用户重新登录；
- 旧 `admin` 不自动成为 CEO；
- 如果需要兼容 bcrypt，采用首次成功登录后升级到 Argon2id；
- 没有真实旧数据时不为假设兼容增加依赖和复杂度；
- 导入工具不得写出真实密码、手机号、邮箱或持仓到日志。

## 23. 回滚策略

发布前备份：

```text
Platform SQLite 数据库
头像数据目录
部署配置
```

回滚步骤：

1. 停止新版本；
2. 回退应用版本；
3. 恢复迁移前数据库备份；
4. 恢复旧代理配置；
5. 强制所有浏览器用户重新登录；
6. 验证 Platform/Runtime Live Write 仍关闭；
7. 运行健康检查和只读数据核对。

迁移以新增表、列和索引为主。已经进入稳定环境后优先 forward-fix，不编辑或删除已应用迁移。

## 24. 分批实施计划

### 批次 0：设计文档

输出：

- Issue #117；
- Critical 任务包；
- 本设计与实施计划；
- 设计评审结论。

本批不修改业务代码。

### 批次 1：迁移、Principal 和 Session 基础

目标：建立统一身份和 Session 边界。

内容：

- Migration 5；
- 用户和 Session Repository；
- Argon2id；
- Session Cookie、CSRF 和 `auth_version`；
- API-Key 与 Session 统一 Principal；
- 显式权限依赖；
- 初始 CEO 命令；
- 最后一个 CEO 事务规则；
- 后端测试。

完成标准：

- API-Key 和现有 Live 鉴权测试保持通过；
- Session 用户能够认证；
- 停用、角色和密码变化立即失效；
- 未配置安全项时 fail-closed。

### 批次 2：登录、注册和个人账号

目标：完成浏览器用户基本闭环。

内容：

- 登录、注册、审核状态；
- `/auth/me` 和退出；
- 资料修改；
- 密码修改和强制修改密码；
- 头像上传；
- Session 设备管理；
- 登录/注册/个人账号前端；
- 前后端直接测试。

完成标准：

- 注册账号 pending；
- 审核前不能登录；
- 审核后可登录；
- Token 不进入本地持久化；
- 头像异常输入被拒绝；
- 密码变化撤销 Session。

### 批次 3：后台用户管理和审计

目标：形成可扩展的后台用户管理。

内容：

- 用户分页、搜索、筛选和排序；
- 详情抽屉；
- 创建、编辑、审批、启停；
- 修改角色；
- 重置密码；
- 强制退出；
- 字段脱敏；
- 事务性审计；
- 角色和目标范围测试。

完成标准：

- 员工只能读取脱敏信息；
- 技术负责人不能操作 CEO 或技术负责人；
- 不能自我提权或停用自己；
- 最后一个 CEO 不可被停用或降级。

### 批次 4：会员基金持仓

目标：完成会员持仓数据、API 和展示闭环。

内容：

- Migration 6；
- 基金代码和基金净值；
- 会员持仓；
- Decimal 计算；
- 本人持仓和管理员持仓 API；
- 持仓页面、空状态、过期状态；
- 横向越权测试；
- 管理员查看和修改审计。

完成标准：

- 会员请求结构不能指定其他用户；
- 修改 URL 或参数不能读取他人持仓；
- CEO 可查看和维护全部会员持仓；
- 技术负责人默认不能查看完整全部持仓；
- Decimal 结果与测试向量完全一致。

### 批次 5：导航收口、兼容和完整验收

目标：完成统一权限导航和旧依赖收口。

内容：

- 权限驱动菜单和路由；
- 会员顶级“个人账号”；
- 内部用户“风控管理/用户管理/个人账号”；
- 旧 `/risk/profile` 重定向；
- 清除用户系统对旧 8080 认证服务的运行依赖；
- Migration 7；
- 文档和部署说明；
- 完整本地验收；
- 完整 CI、Secret Scan 和 Version Consistency。

完成标准：

- 一键本地启动包含完整用户闭环；
- 前端隐藏和后端拒绝一致；
- 原交易、风险、Runtime 和 Live 测试无回归；
- 所有必需检查通过。

## 25. 提交计划

优先形成完整 Patch，再提交 1—3 个逻辑提交：

```text
1. Add user identity, sessions and permission foundation
2. Implement user, profile and member holding workflows
3. Integrate frontend access control, tests and documentation
```

不按文件逐个提交，不在每次小修复后更新任务元数据。

当前文档阶段的两个文档提交不代表最终实现提交结构；开始业务开发前可以在分支内保持清晰历史，最终 PR 仍使用 Squash Merge。

## 26. 测试计划

### 26.1 后端单元测试

- 角色到权限映射；
- 密码规则和 Argon2id 验证；
- Session Token 哈希和过期；
- CSRF；
- 状态转换；
- 目标角色规则；
- 手机和邮箱规范化/脱敏；
- Decimal 持仓计算；
- NAV 缺失、过期和零投入。

### 26.2 后端集成测试

- 注册、审核、登录、`/auth/me` 和退出；
- pending/disabled/locked 拒绝；
- 登录失败锁定；
- Session 撤销；
- 角色、密码和状态变化使旧 Session 失效；
- 最后一个 CEO；
- 禁止自我提权和停用自己；
- 技术负责人目标范围；
- 员工只读和字段脱敏；
- 会员 IDOR/横向越权；
- 管理员持仓读取和修改审计；
- 头像格式、大小、像素和路径穿越；
- API-Key 与 Session Principal 兼容。

### 26.3 并发和事务测试

- 两个并发请求同时尝试降级/停用最后两个 CEO；
- 敏感写操作审计失败时整体回滚；
- Session 撤销与并发请求；
- 用户名、邮箱和手机号唯一冲突；
- 持仓更新并发和最后写入规则。

### 26.4 迁移测试

- 全新数据库；
- 0.9.0 已有数据库；
- 重复启动；
- 校验和漂移；
- 迁移失败回滚；
- 旧审计和交易数据保持不变。

### 26.5 前端测试与检查

- 权限过滤菜单；
- 会员和内部用户菜单位置；
- 路由直接访问拒绝；
- 按钮和字段权限；
- 401 自动回登录；
- 403 无权限状态；
- loading/error/empty；
- 登录、注册、详情抽屉和危险操作；
- 窄屏基本可用性；
- ESLint、类型检查和生产构建。

### 26.6 回归测试

必须重复运行：

- 现有认证/RBAC 测试；
- LiveTradingSession 测试；
- live_safety 分类测试；
- Market、FOK、PostOnly 和 TP/SL 相关测试；
- Runtime 全套测试；
- 前端生产构建；
- Repository Safety；
- Secret Scan；
- Version Consistency。

## 27. 本地验收场景

必须逐项验证：

1. 注册会员，状态为 pending；
2. 未审核用户无法登录；
3. CEO 审核后会员可登录；
4. 会员只看到“个人账号”；
5. 会员不能访问用户管理或风控页面；
6. 会员修改 URL、路径参数或查询参数仍不能读取他人持仓；
7. 员工能查看用户列表，但联系方式脱敏且没有写按钮；
8. 技术负责人可以管理普通用户；
9. 技术负责人不能修改 CEO 或其他技术负责人；
10. 技术负责人不能查看全部会员完整持仓；
11. CEO 可以管理普通用户和全部会员持仓；
12. 不能停用或降级最后一个 CEO；
13. 用户不能修改自己的角色或停用自己；
14. 停用用户后已有 Session 下一次请求立即失效；
15. 角色变化后旧 Session 立即失效；
16. 修改或重置密码后全部旧 Session 失效；
17. 临时密码用户必须先修改密码；
18. 头像异常格式、过大文件和恶意路径被拒绝；
19. 持仓金额使用 Decimal 并匹配测试结果；
20. 没有净值时显示不可用，不显示零；
21. 敏感操作产生审计，但日志没有密码、Token 或完整客户敏感信息；
22. API-Key 和 LiveTradingSession 现有行为保持不变；
23. Platform 和 Runtime Live Write 仍关闭；
24. 一键本地启动可以完成完整用户闭环。

## 28. CI 和合并门槛

本工作属于 Critical。PR 必须声明：

```text
Workstream: critical
Issue: #117
```

必须通过：

- Repository Safety；
- Backend Ruff；
- Backend Pyright；
- Backend architecture/unit/integration/live_safety；
- Runtime 完整矩阵；
- Frontend ESLint、类型检查和构建；
- Secret Scan；
- Version Consistency；
- 文档和架构一致性检查。

全部通过后才可 Squash Merge。

## 29. 主要风险与缓解措施

| 风险 | 影响 | 缓解 |
|---|---|---|
| 双认证体系继续并存 | 身份不一致、权限绕过 | Platform Backend 单一权威；旧服务停止扩展 |
| API-Key admin 等同 CEO | 账号生命周期越权 | 人类账号写操作要求 Session 和业务角色 |
| 最后一个 CEO 被移除 | 系统无法管理 | `BEGIN IMMEDIATE` 事务检查与并发测试 |
| 角色变化后旧 Session 保留 | 权限长期滞留 | `auth_version` 每请求校验 |
| 会员修改参数查看他人数据 | 严重数据泄露 | self API 不接受用户 ID；服务端数据范围测试 |
| 前端脱敏但返回原始字段 | 敏感信息泄露 | 后端返回范围化 DTO |
| 浮点计算持仓 | 金融结果误差 | Decimal + 字符串存储/API |
| 头像恶意文件 | 文件和资源风险 | 解码、像素限制、重新编码、随机命名 |
| 审计失败但写操作成功 | 缺失证据 | 敏感成功写入与审计同事务 |
| 新认证削弱 Live | 真实交易风险 | 浏览器 Session 不替代 API Key/LiveTradingSession |
| 迁移破坏旧数据 | 平台不可用 | 只新增迁移、备份、升级测试、forward-fix |
| 范围过大导致无闭环 | 延期和不稳定 | 按五个实施批次，每批直接测试 |

## 30. 设计完成标准

本文档完成并经确认后，设计阶段视为完成。进入代码实施前应再次确认：

- Issue #117 仍开放且没有重复用户系统 PR；
- 分支仍基于最新 `main` 或已安全同步；
- 任务包状态更新为实施中；
- 旧用户数据库是否存在真实需要迁移的数据；
- 初始 CEO 创建方式和本地验收人员已明确；
- 未新增超出第一阶段边界的需求。

未经明确批准，不开始业务代码修改。
