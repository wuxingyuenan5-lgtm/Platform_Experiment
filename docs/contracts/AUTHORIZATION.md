# Authentication, Authorization, Browser Session, and LiveTradingSession

状态：`active authentication and authorization contract`
适用产品：`Platform`
用户系统架构：`../architecture/USER_SYSTEM.md`
产品基线：`../product/PRD.md`；前端验收：`../../platform-web/docs/ACCEPTANCE.md`
浏览器访问合同：[Browser Access and Product Data](../contracts/BROWSER_ACCESS_AND_PRODUCT_DATA.md)
角色权限矩阵：[前端访问权限矩阵](ACCESS_MATRIX.md)

## 1. 正常交易与两类 Session

2026-09-09 Owner 明确要求取消早期测试和初步验收限制，改为常规交易权限及对应风控。

Browser Session 是正常网页登录凭证。有效的 CEO 登录会话通过 CSRF、角色权限和账户交易绑定后，可以发起 Cross/Funding 的开仓、平仓及获准管理操作；不需要另建 API Key 或临时实盘审批会话。API Key 继续用于已授权系统调用，API-Key admin 不自动等同人类 CEO。

Cross/Funding 批次的 RiskAction 同样受 CEO 会话边界约束，包括故障后的平仓处置。CEO 的显式权限包含现有风险接口使用的 `risk:manage`；技术负责人、员工、会员和 API-Key admin 不能借通用风险接口绕过这两个策略的交易授权。

Funding 原平仓 `recover-close` 补现货入口同样要求 CEO Browser Session、CSRF 和 `trading.write`；恢复审计的 actor 取认证主体，不接受客户端指定交易人。

策略交易权限按数据库中实例关联的 `strategy_definitions.strategy_key` 判定，不以默认实例 ID、实例名称或客户端自报类型作为授权依据。批次风险处置沿持久化批次解析实际实例。所有 Cross/Funding 实例均须使用专用指令与生命周期入口；通用 Command、Batch、Run、Instruction 入口即使由 CEO 调用也不能绕过该链路。缺省实例的受控 Batch 同样拒绝；旧裸 Order 入口按账户的活动交易绑定识别受控策略。拒绝发生在创建订单、批次、资源占用及 Runtime 调用之前，内部获准执行链保持原有入口。

旧 LiveTradingSession 的表、公共结构和兼容接口保留历史与审计语义。它的批准、过期、额度、次数、品种集合和验收窗口不参与正常订单授权，也不能绕过其他安全检查。

## 2. 总体安全边界

```text
HTTP Request
→ Authentication Credential Selection
→ Authentication Assurance
→ Permission Resolution
→ Authenticated Principal
→ Actor / Target / Data Scope Binding
→ Business Validation
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
| CEO | 全部正式页面 | 允许 | 允许 | 允许 | 正常业务写权限；Cross/Funding 交易仅 CEO，仍受账户权限、Live Write、Kill Switch 和交易风控约束 |
| 技术负责人 | 接近完整或完整的正式页面范围 | 允许 | 允许 | 允许 | 仍受全部正式安全门禁约束 |
| 员工 | 全部正式业务页面只读 | 只读 | 用户列表只读 | 允许 | 仅本人获准的密码、头像、设备和会话等安全自助；无业务或其他账号写权限 |
| 会员 | 规定范围内正式业务页面只读 | 禁止 | 禁止 | 必须允许 | 只能访问当前认证会员本人；不得读取其他账号或内部组织数据 |

长期授权原则：

- 菜单隐藏不是授权；
- 直接 URL 与后端 API 必须独立验证权限和数据范围；
- 浏览器角色只使用显式权限集；
- API-Key 角色命名空间继续独立；
- Browser Session 可授权其角色获准的正常交易；Runtime 仍独立检查真实写入开关、交易账户与命令身份；
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
| `live_write` | 有效 Browser Session 或 API Key，继续按角色和业务范围验证 | 真实交易及已开启真实写入时的非安全方法；Development Identity 不可用 |

同一请求同时携带 Bearer 和 Browser Session Cookie 时返回歧义认证错误，不静默选择其中一种。

## 6. 环境规则

### 6.1 Live 或已开启真实写入

- Development Identity 不得提交写请求；本地环境标记不是匿名真实交易的许可。
- 正常网页写入使用有效 Browser Session、CSRF 和明确业务权限；Cross/Funding 的交易必须通过 CEO 边界。
- API Key 的角色与权限继续独立解析。API-Key admin 不自动获得 CEO 的策略交易权限。
- 匿名、无效凭证、过期会话、未知角色、身份冲突和越权账户均拒绝。
- 真实账户下单继续要求 Platform 与 Runtime 的真实写入总开关。正常登录不自动开启总开关。

### 6.2 未开启真实写入的本地开发

显式 Development Identity 可用于模拟测试；开启真实写入后不再允许它提交写请求。Browser Session 可在本地验证与正式环境相同的角色边界。

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

受保护导航仍逐次调用 `/auth/me` 验证服务端 Session。浏览器已有内存 CSRF 时随该 GET 携带 `X-CSRF-Token`；仅当其哈希与本次已认证 Session 的哈希恒定时间比较一致时复用原值，避免每次点击都轮换 CSRF 并争用 SQLite 写锁。冷启动、未携带或不匹配时继续签发并持久化新 CSRF；停用、撤销、权限、空闲与绝对到期检查不缓存或跳过。

页面刷新及 API 正常重启通过原 Cookie 重新读取持久化 Session，不创建新会话或延长绝对有效期。`/auth/me` 的网络错误、408、429 和无明确认证失效代码的 5xx 表示暂时无法完成验证：已验证并加载的页面保留展示状态，拒绝新的受保护导航并提示稍后重试；冷启动没有已验证会话时进入现有连接重试页，不放行保护路由、不误报密码失效。重试只读取原会话。明确的 401、账号停用或认证失效继续清理身份并进入登录流程，不能使用缓存身份放行。30 分钟空闲按成功的认证请求续期，后台策略执行不替浏览器续期。

认证中间件的同步会话存储、审计落库及按指令/批次判定交易权限的 SQLite 查询在线程池中运行；锁等待不得占用共享 ASGI 事件循环。权限、CSRF、空闲和绝对有效期检查仍逐请求执行。

Browser Session 控制人类发起新操作的权限，不拥有已保存策略指令的生命周期。Cross 自动退出的后台运行与停机边界归 [Cross 执行合同](CROSS_SPREAD_EXECUTION.md)。

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
| `reconciliation:review` | Difference Resolution、单笔订单 `reconcile` / `venue-reconcile` 的证据读取与事实回补 |
| `eod:review` | EOD Review |

受控的 Cross 与 Funding 实例不接受公共 TradeCommand、ExecutionBatch、旧 Strategy Run、通用 StrategyInstruction 或 deprecated raw Order 入口。前四类请求按策略实例直接拒绝；raw Order 本身不携带策略身份，因此只要账户存在有效的受控策略交易绑定即拒绝。它们必须进入策略专用 lifecycle/instruction 主链；该路由封堵与 CEO 权限检查同时成立，不能以客户端入口选择替代业务授权。
| `live_session:request` | 申请实盘会话 |
| `live_session:approve` | 批准实盘会话 |
| `live_session:revoke` | 撤销实盘会话 |
| `admin:write` | 未明确分类的旧管理写操作 |

`POST /api/v1/trading/orders/{orderId}/reconcile` 与 `venue-reconcile` 使用已有 `reconciliation:review`，允许有该权限的 CEO 从 Runtime Journal 或原生证据恢复订单、成交与费用，浏览器 CSRF 仍须通过；两者不能发起新的 Venue 订单。`resolve-missing-external` 的管理权限与显式差异接受要求保持独立，不随该查询/导入接口放宽。

Financial AI 的状态、研究数据、连接检查和普通分析使用 `platform:read`。服务端共享 AI 配置的保存、替换和清除使用现有 `settings.write`；该边界同时适用于 Browser Session 和 API-Key Principal，不得由页面私有角色或按钮可见性放宽。详细语义见 [Financial AI 合同](FINANCIAL_AI.md)。

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

## 12. 旧 LiveTradingSession 兼容记录

原有 pending、approved、revoked、expired 状态、申请/批准人和窗口数据继续保留，不重写既有审计。兼容接口修改这些记录不会启用或撤销正常交易权限。正常交易不再执行 LiveTradingSession Claim，也不受旧的双人审批、只读证据时效、重叠窗口、EOD 放量审批和固定额度控制。

## 13. 正常订单的持续安全边界

在已授权请求或既有指令执行链中，真实订单须检查：

- 完整 StrategyInstance、Command 与账户身份；活动账户及 `trade_and_read` 绑定；
- Platform 与 Runtime Live Write；Runtime 可交易账户配置和原生账户读写权限；
- 全局、策略、账户 Kill Switch；尚未处理的对账差异；已确认拒单的 `accepted/missing_external` 记录沿用现有例外；
- 实际余额与保证金、Venue 数量最小值/步长/最大值、价格精度和 MT5 终端权限；
- 同一业务意图、命令幂等、资源占用、累计成交不超指令、平仓归属与结果未知时停止副作用。

历史验收的固定数量、单笔/每日名义额度、持仓组数量、Strategy/Symbol 临时白名单不再参与下单。每条指令自身的数量上限、有限追价次数/时长及真实账户范围继续有效。

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

当前 API-Key 配置适合单机小型私募的受控部署边界，不等同完整企业身份提供商。认证、代码完成、候选验证和 CI 均不能自动打开 Platform 或 Runtime Live Write。

## 19. Product authority and scope

The browser role set is CEO, technical lead, employee and member. Capability and resource scope are resolved centrally; UI visibility is never authorization. Any future research, trader, strategy-owner, risk, reconciliation or system-administration specialization must be introduced as reviewed Capability and Data Scope policy, not as an unreviewed page-local role.


## Strategy research request permissions

`/api/v1/research/strategies/**` keeps the existing authenticated research boundary. GET and pure `POST /scenario` require `research.read`. Persisted experiment creation/cancellation and draft saving require `research.write` in both middleware classification and route dependencies; browser CSRF remains mandatory. Cross-gold broker-scoped reads additionally require existing `trade.read`. Experiment/draft lookup is restricted to the authenticated owner. Research parameter import is a user-triggered form/prepare action and cannot grant trading authority or skip normal CEO, quote, quantity, risk or unknown-result checks. The generic admin-write fallback and all existing execution permissions remain unchanged for other routes.

Funding `PATCH /trading/funding/exit-plans/{open_instruction_id}` requires `trading.write`, existing CEO trade authority and browser CSRF. The configured actor is taken from the authenticated principal; callers cannot supply an actor or execution credentials. Saving thresholds grants no Live Write permission. Read-only strategy roles may view plan status through existing Funding position reads.
