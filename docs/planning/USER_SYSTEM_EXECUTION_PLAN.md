# 用户系统执行计划

状态：`implemented / automated verification passed / manual acceptance pending`<br>
适用版本：`Platform Experiment 0.9.0`
Issue：`#117`
任务包：`../../tasks/issue-117-user-system.md`
需求：`USER_SYSTEM_REQUIREMENTS.md`
架构：`../technical/USER_SYSTEM_TECHNICAL_ARCHITECTURE.md`

## 1. 执行目标

在一个 Critical Issue、一个 Issue 分支和一个最终 Squash PR 中，完成以下可运行闭环：

```text
注册
→ 审核
→ Session 登录
→ 权限导航
→ 个人资料/密码/设备
→ 后台用户管理
→ 会员本人持仓
→ 审计
```

不修改交易语义，不启用任何 Live Write，不把 CI 当作真实环境验收。

## 2. 工作流

```text
Issue #117
→ tasks/issue-117-user-system.md
→ feature/issue-117-user-system
→ documentation review
→ implementation checkpoints
→ one Pull Request
→ full CI + Secret Scan + Version Consistency
→ Squash Merge
```

当前分支基线：

```text
71603bcc6807284ef3a6da26ad3f43c541bc99c2
```

进入代码实施前必须重新比较最新 `main`。如果 `main` 已前进，先评估并安全同步，不在过期基线上开发认证和迁移。

## 3. 执行原则

1. 先形成完整 Patch，再整理提交；不逐文件提交几十次。
2. 每个批次在进入下一批前直接运行相关测试。
3. 新用户接口全部显式声明认证保障等级和权限。
4. 人类身份接口不接受 API-Key wildcard 代替 Session。
5. 数据范围从 Principal 推导，不相信客户端 user/member 标识。
6. 数据库迁移只能追加，已应用迁移不可编辑。
7. 敏感成功写入与审计同事务。
8. 资金边界使用 `Decimal` 与字符串合同。
9. 发生安全或架构冲突时停止，不用兼容代码掩盖。
10. 不在此 Issue 删除旧 Go 服务；切流和清理分开。

## 4. 实施前决策门

### Gate D1 — 旧用户数据

在 Migration 5 和切换登录前，核实旧 MySQL 是否有真实用户。

需要的仅是脱敏统计：

```text
用户总数
pending/approved/rejected 数量
guest/employee/admin 数量
密码哈希算法分布
是否有仍在使用的 Session
```

禁止把用户名、邮箱、手机号、密码哈希或 Token 写入 Issue、Markdown 或日志。

结论分支：

- 无真实用户：不开发旧库导入；
- 有真实用户：增加一次性迁移子任务，但仍在 Issue #117 范围内先评审映射和 dry-run；
- 数据不明：停止登录切换，不猜测。

### Gate D2 — 持仓数据来源

批次 4 开始前确认第一批数据来源：

```text
manual_admin（默认）
migration
external_import
```

若没有现成来源，使用虚构测试数据和 CEO 手工维护闭环，不把 Seed 示例当作真实客户数据。

### Gate D3 — 同源部署

确认正式部署继续使用：

```text
frontend origin
/api/v1 reverse proxy
```

如需跨域，停止并重新评审 Cookie、CORS、CSRF 和域名策略。

## 5. 批次 0：设计冻结

### 5.1 输出

- Issue #117；
- Critical 任务包；
- 产品需求与验收标准；
- 技术架构；
- 执行计划；
- 自审结论和已接受 ADR。

### 5.2 设计冻结标准

- 单一身份权威明确；
- Session/API-Key/Live 路由边界明确；
- 四角色权限和目标范围明确；
- 用户生命周期与临时锁定分离；
- 密码重置不使用管理员可见临时密码；
- 持仓权威类型和 Decimal 边界明确；
- API、迁移、回滚和测试可追踪；
- 没有未说明的真实数据假设。

### 5.3 检查

```powershell
python scripts/check-documentation-consistency.py
python scripts/check-repository-structure.py
python scripts/check-version-consistency.py
```

文档阶段不修改业务代码，不创建虚构 CI 结果。

## 6. 批次 1：身份、迁移和 Session 基础

### 6.1 目标

建立 Platform Backend 内唯一的人类身份、安全 Session 和显式认证保障等级。

### 6.2 需求覆盖

```text
USR-AUTH-002/005/006/007/008/009
USR-PWD-001/002/004
USR-SESSION-005
USR-ACCESS-001/002
USR-AUDIT-002/003/004/005
```

### 6.3 预期修改

后端：

```text
platform-api/app/auth.py
platform-api/app/user_schemas.py             new
platform-api/app/user_repository.py          new
platform-api/app/user_service.py             new
platform-api/app/user_routes.py              new
platform-api/app/schema_migrations.py
platform-api/app/main.py
platform-api/app/config.py
platform-api/pyproject.toml
```

测试：

```text
platform-api/tests/test_user_schema_migrations.py   new
platform-api/tests/test_user_authentication.py      new
platform-api/tests/test_user_sessions.py            new
platform-api/tests/test_user_authorization_architecture.py new
platform-api/tests/test_auth_rbac.py
```

文档：

```text
docs/technical/AUTH_RBAC_LIVE_SESSIONS.md
docs/architecture/OWNERSHIP.md
docs/database/README.md
docs/codex/current-state.md
```

实际文件可以依据现有边界合并，但不得产生平行认证实现。

### 6.4 实施步骤

1. 添加 Migration 5：users、sessions、reset tickets、audit 查询字段和索引。
2. 添加 Argon2id 依赖和密码策略。
3. 扩展 Principal 支持 `session_id`，保留 API-Key 字段和现有角色。
4. 实现歧义凭证拒绝。
5. 引入路由认证保障等级。
6. 实现 Session 创建、查找、绝对/空闲过期、撤销、活动时间节流和最大会话数。
7. 实现 CSRF 和 Origin 校验。
8. 实现 `auth_version` 即时失效。
9. 实现 `POST /auth/reauth` 和近期再认证。
10. 实现初始 CEO 交互命令。
11. 实现最后一个 CEO 事务保护基础函数。
12. 增加认证架构测试，确保用户域非公开路由有显式声明。

### 6.5 直接测试

```powershell
cd platform-api
python -m ruff check app tests
python -m pyright
python -m pytest tests/test_user_schema_migrations.py -q
python -m pytest tests/test_user_authentication.py -q
python -m pytest tests/test_user_sessions.py -q
python -m pytest tests/test_user_authorization_architecture.py -q
python -m pytest tests/test_auth_rbac.py -q
python -m pytest tests/test_live_trading_sessions.py -q
```

### 6.6 退出标准

- 全新和 0.9.0 数据库迁移通过；
- API-Key 行为和现有 Live 测试无回归；
- Session 可认证但尚不要求完整 UI；
- 角色、密码、状态变化使旧 Session 失效；
- Cookie+Bearer 同时存在被拒绝；
- Live 写路由仍为 API-Key-only；
- 无默认 CEO 密码。

## 7. 批次 2：注册、登录和个人账号

### 7.1 目标

完成普通用户从注册到个人资料和安全管理的浏览器闭环。

### 7.2 需求覆盖

```text
USR-REG-001..009
USR-AUTH-001/003/004
USR-ME-001..005
USR-AVATAR-001..006
USR-PWD-003..007
USR-SESSION-001..003
```

### 7.3 预期修改

后端：

```text
platform-api/app/user_schemas.py
platform-api/app/user_repository.py
platform-api/app/user_service.py
platform-api/app/user_routes.py
platform-api/app/config.py
```

前端：

```text
platform-web/src/api/platform/userSystem.ts              new
platform-web/src/store/modules/user.ts
platform-web/src/router/guard/permissionGuard.ts
platform-web/src/views/sys/login/LoginForm.vue
platform-web/src/views/sys/register/index.vue
platform-web/src/views/account/index.vue                 new
platform-web/src/views/account/components/*              bounded
platform-web/src/utils/http/axios/index.ts
```

测试：

```text
platform-api/tests/test_user_registration.py
platform-api/tests/test_user_profile.py
platform-api/tests/test_password_reset_tickets.py
platform-api/tests/test_user_avatar.py
platform-web focused tests if current harness supports them
```

### 7.4 实施步骤

1. 实现注册、登录、`/auth/me`、退出和重置凭证使用。
2. 实现登录失败计数和 `locked_until`。
3. 实现普通资料和联系方式分离更新。
4. 实现用户修改密码。
5. 实现头像流式限制、解码、重编码和原子替换。
6. 实现本人 Session 列表、单个撤销和退出其他设备。
7. 前端取消持久化认证 Token，改为启动时 `/auth/me` hydration。
8. 登录页保持现有视觉；注册页改为相同视觉体系。
9. 实现个人账号三个页签。
10. 明确 loading、error、empty、401、403 和 session-expired 状态。

### 7.5 直接测试

```powershell
cd platform-api
python -m pytest tests/test_user_registration.py -q
python -m pytest tests/test_user_profile.py -q
python -m pytest tests/test_password_reset_tickets.py -q
python -m pytest tests/test_user_avatar.py -q
python -m pytest tests/test_user_sessions.py -q

cd ../platform-web
pnpm exec eslint --max-warnings 0 <changed-user-system-files>
pnpm type:check
pnpm build
```

### 7.6 退出标准

- 会员/员工申请为 pending；
- 公开请求不能申请高权限角色；
- 审核前不能登录；
- 登录后只使用 HttpOnly Session；
- 资料保存在后端；
- 密码修改撤销全部 Session；
- 管理员重置只生成一次性凭证；
- 头像异常输入全部 fail-closed；
- 页面刷新可以通过 `/auth/me` 恢复身份。

## 8. 批次 3：用户管理、角色保护和审计

### 8.1 目标

形成可随用户数量增长使用的后台管理闭环。

### 8.2 需求覆盖

```text
USR-ADMIN-001..008
USR-SESSION-004
USR-ACCESS-001/002/006
USR-AUDIT-001..005
```

### 8.3 预期修改

后端：

```text
platform-api/app/user_schemas.py
platform-api/app/user_repository.py
platform-api/app/user_service.py
platform-api/app/user_routes.py
```

前端：

```text
platform-web/src/views/users/index.vue
platform-web/src/views/users/components/UserDetailDrawer.vue
platform-web/src/access/userAccess.ts
platform-web/src/router/routes/modules/risk.ts
```

测试：

```text
platform-api/tests/test_user_admin.py
platform-api/tests/test_user_target_scope.py
platform-api/tests/test_last_ceo_concurrency.py
platform-api/tests/test_user_audit_transactions.py
```

### 8.4 实施步骤

1. 用户分页、搜索、筛选、排序和后端字段脱敏。
2. 用户详情聚合接口。
3. 创建会员/员工及 CEO 创建高角色流程。
4. 审批和拒绝流程，批准请求携带最终角色。
5. 编辑普通字段和 `expectedVersion`。
6. 角色、启用、停用和 Session 强退动作接口。
7. 重置凭证签发及近期再认证。
8. 最后一个 CEO `BEGIN IMMEDIATE` 事务保护。
9. 禁止自我角色变化和停用自己。
10. 技术负责人目标角色范围。
11. 敏感写入与审计同事务。
12. 前端详情抽屉和危险操作确认。

### 8.5 直接测试

```powershell
cd platform-api
python -m pytest tests/test_user_admin.py -q
python -m pytest tests/test_user_target_scope.py -q
python -m pytest tests/test_last_ceo_concurrency.py -q
python -m pytest tests/test_user_audit_transactions.py -q
python -m pytest tests/test_auth_rbac.py -q
```

### 8.6 退出标准

- 员工只收到脱敏 DTO；
- 技术负责人不能管理 CEO/技术负责人；
- 任何人不能修改自己角色或停用自己；
- 并发请求不能移除最后一个 active CEO；
- 旧版本更新返回 409；
- 停用、角色、重置和强退即时生效；
- 敏感写入没有审计时不能提交。

## 9. 批次 4：会员持仓和基金净值

### 9.1 目标

完成客户基金持仓的精确读模型、管理入口和本人展示。

### 9.2 需求覆盖

```text
USR-HOLD-001..009
USR-AUDIT-001/002/004/005
```

### 9.3 预期修改

后端：

```text
platform-api/app/schema_migrations.py
platform-api/app/user_schemas.py
platform-api/app/user_repository.py
platform-api/app/user_service.py
platform-api/app/user_routes.py
```

前端：

```text
platform-web/src/views/account/components/HoldingsPanel.vue
platform-web/src/views/users/components/UserDetailDrawer.vue
platform-web/src/api/platform/userSystem.ts
```

测试：

```text
platform-api/tests/test_member_holding_migrations.py
platform-api/tests/test_member_holdings.py
platform-api/tests/test_member_holding_scope.py
platform-api/tests/test_member_holding_decimal.py
```

### 9.4 实施步骤

1. 添加 Migration 6。
2. 添加 `fund_code` nullable 和部分唯一索引。
3. 实现持仓和 NAV Repository。
4. 实现 Decimal 输入、计算和响应。
5. 实现 NAV unavailable/stale 语义。
6. 实现 `/me/holdings`，不接受身份参数。
7. 实现 CEO 管理读取和更新，使用近期再认证、版本和事务审计。
8. 默认拒绝技术负责人读取全部完整持仓。
9. 前端持仓卡片/表格、空状态、过期状态和更新时间。
10. 通过虚构测试向量验证精度。

### 9.5 直接测试

```powershell
cd platform-api
python -m pytest tests/test_member_holding_migrations.py -q
python -m pytest tests/test_member_holdings.py -q
python -m pytest tests/test_member_holding_scope.py -q
python -m pytest tests/test_member_holding_decimal.py -q
```

### 9.6 退出标准

- 会员无法通过路径、查询或请求体读取他人持仓；
- API-Key admin 无法调用客户身份/持仓管理接口；
- CEO 可查看和维护全部持仓；
- 技术负责人默认无完整全量持仓；
- Decimal 与测试向量一致；
- unavailable/stale 不被显示为零；
- 管理员查看他人完整持仓和修改持仓有审计。

## 10. 批次 5：权限导航、运行收口和兼容

### 10.1 目标

使用户系统成为默认本地运行路径，移除前端对旧认证服务的运行依赖，同时不删除旧代码。

### 10.2 需求覆盖

```text
USR-ACCESS-003..006
全部本地验收标准
```

### 10.3 实施步骤

1. 完成统一权限注册表。
2. 菜单和路由从同一注册表生成。
3. 会员使用顶级 `/account`。
4. 内部用户在风控管理下显示用户管理和个人账号。
5. `/risk/profile` 重定向到 `/account`。
6. 用户系统调用全部切换到 `/api/v1` Platform Backend。
7. 更新本地代理和 `dev-platform.ps1`，确保无需旧 8080 认证服务。
8. 旧 Go 服务标记 legacy/deferred cleanup，但本次不删除。
9. 更新 AUTH、OWNERSHIP、DATABASE、current-state 和部署文档。
10. 逐项运行本地验收清单。

### 10.4 直接测试

```powershell
cd platform-web
pnpm exec eslint --max-warnings 0 <all-user-system-changed-files>
pnpm type:check
pnpm build

cd ..
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

人工本地验收按需求文档第 10 节逐项记录，不提交真实客户截图或数据。

### 10.5 退出标准

- 一键本地启动完成用户闭环；
- 登录/注册不依赖旧 8080；
- 菜单、路由、按钮和后端拒绝一致；
- 旧用户路径有兼容重定向；
- 文档权威边界同步；
- 没有 Live 配置变化。

## 11. 最终回归矩阵

### 11.1 Backend

```powershell
cd platform-api
python -m ruff check app tests
python -m pyright
python -m pytest -m architecture
python -m pytest -m unit
python -m pytest -m integration
python -m pytest -m live_safety
```

### 11.2 Runtime

用户系统不应修改 Runtime，但 Critical 共享认证/数据库工作最终必须运行 Runtime 完整矩阵：

```powershell
cd execution-runtime
python -m ruff check app tests
python -m pyright
python -m pytest
```

### 11.3 Frontend

```powershell
cd platform-web
pnpm lint
pnpm type:check
pnpm build
```

如仓库不存在 `pnpm lint`，按 `package.json` 实际脚本和模块 AGENTS.md 使用准确命令，不虚构成功。

### 11.4 Repository

```powershell
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
python scripts/check-version-consistency.py
```

PR 还必须通过：

- Repository Safety；
- Platform CI 全矩阵；
- Secret Scan；
- Version Consistency；
- Review conversation resolution。

## 12. 安全专项测试

### 12.1 认证

- 匿名访问非公开路由；
- 无效 Cookie；
- 过期和空闲过期；
- 已撤销 Session；
- Cookie+Bearer 歧义；
- Live route with Session only；
- human route with API-Key admin；
- Development Identity in live；
- Origin/CSRF 错误；
- recent reauth 过期。

### 12.2 密码与凭证

- 弱密码；
- 账号枚举；
- 失败锁定和自动解锁；
- 重置凭证错误、过期、重复使用、并发使用；
- 新凭证撤销旧凭证；
- 日志和审计无原始凭证。

### 12.3 授权

- 会员访问用户管理；
- 会员读取他人持仓；
- 员工写操作；
- 技术负责人操作 CEO/技术负责人；
- 自我提权和自我停用；
- API-Key wildcard 访问人类身份域；
- 最后 CEO 并发保护；
- 后端字段脱敏。

### 12.4 文件

- 伪造扩展名；
- 超大文件；
- 超高像素/解压炸弹；
- 路径穿越；
- 非图片；
- 替换失败后的原文件一致性；
- 头像目录不可写时的失败和审计。

### 12.5 金融

- 高精度份额和 NAV；
- 零投入；
- NAV 缺失；
- NAV stale；
- 非法十进制；
- 负值；
- 并发版本冲突；
- 管理员修改审计回滚。

## 13. 提交计划

目标仍是 1—3 个逻辑实现提交；GitHub Contents API 产生的文档检查点不代表最终实现提交结构。建议代码完成后形成：

```text
1. Add human identity, secure sessions and authorization boundary
2. Implement user administration, personal account and member holdings
3. Integrate permission-driven frontend, tests and authoritative docs
```

最终使用 Squash Merge，因此主分支只有一个完成身份。

## 14. PR 结构

PR 标题建议：

```text
Implement complete user identity and member account system
```

PR 必须声明：

```text
Workstream: critical
Issue: #117
```

PR 正文只包含：

- 可测量结果；
- 主要范围；
- 关键安全边界；
- 实际验证；
- 风险与回滚。

不复制整份任务包或提交历史。

## 15. 风险与回滚

### 15.1 主要风险

| 风险 | 检测 | 缓解 |
|---|---|---|
| 身份体系继续双写 | API/启动检查 | Platform Backend 单一权威 |
| Live 认证被放宽 | live_safety/route assurance tests | live_write API-Key-only |
| API-Key admin 成为 CEO | human-session-only tests | auth method gate |
| 最后 CEO 被移除 | 并发事务测试 | `BEGIN IMMEDIATE` |
| 旧 Session 保留权限 | auth_version tests | 每请求版本检查 |
| 客户横向越权 | IDOR tests | self endpoint 无 user id |
| 前端脱敏但后端泄露 | DTO tests | 服务端字段策略 |
| 重置密码泄露 | log/audit tests | 一次性哈希凭证 |
| 持仓浮点误差 | Decimal vectors | 字符串合同 |
| 迁移破坏旧数据 | fresh/upgrade/equivalence | additive migration + backup |
| 头像文件攻击 | malformed image tests | decode/re-encode/caps |

### 15.2 发布前备份

```text
Platform SQLite database
avatar data directory
reverse proxy configuration
application configuration
```

### 15.3 回滚步骤

1. 停止新版本；
2. 验证 Platform/Runtime Live Write 仍关闭；
3. 回退应用版本；
4. 如迁移已应用且必须回滚，恢复迁移前数据库和头像目录；
5. 恢复旧代理配置；
6. 清除浏览器 Session Cookie并要求重新登录；
7. 运行健康检查和只读数据核对。

稳定环境中优先 forward-fix，不编辑已应用迁移。

## 16. 停止条件

出现以下任一情况立即停止并回到设计评审：

- 需要修改已应用 Migration 1—4；
- Session 会降低现有 Live API-Key 或 LiveTradingSession 要求；
- 人类身份或客户数据必须允许 API-Key wildcard 才能运行；
- 无法事务性保护最后一个 CEO；
- 会员数据隔离依赖前端隐藏或客户端 user id；
- 需要把密码、Token、完整联系方式或真实持仓写入日志/测试/Git；
- 用户系统必须改变 Venue、Runtime、FOK、PostOnly、TP/SL 或跨所价差语义；
- 迁移前无法确认旧真实用户数据是否存在；
- 正式部署变为跨域但没有重新设计 Cookie/CORS/CSRF；
- CI 或本地测试出现无法解释的现有 Live 安全回归。

## 17. 完成定义

Issue #117 只有在以下全部满足后才完成：

- 所有第一阶段需求实现；
- 本地验收 20 项通过；
- 迁移 fresh/upgrade/repeat/checksum 测试通过；
- 权限、目标范围、并发、密码、Session、头像和 Decimal 专项测试通过；
- 前端菜单/路由/按钮与后端拒绝一致；
- 旧 8080 不再是用户系统运行依赖；
- AUTH、OWNERSHIP、DATABASE、current-state 和任务包同步；
- 完整 CI、Secret Scan 和 Version Consistency 通过；
- 没有未解决评审线程；
- 使用 Squash Merge；
- 合并后 `main` 再次通过全矩阵。
