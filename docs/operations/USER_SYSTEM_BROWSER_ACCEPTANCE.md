# 用户系统浏览器验收手册

状态：`automated browser acceptance passed / local visual smoke optional / production proxy validation pending`

- Issue：`#117`
- Draft PR：`#118`
- 交付分支：`feature/issue-117-user-system`
- 本地交接：`USER_SYSTEM_LOCAL_INTEGRATION_HANDOFF.md`
- 部署与恢复：`USER_SYSTEM_DEPLOYMENT_READINESS.md`

## 1. 当前结论

GitHub Actions 的真实 Chromium 验收已经通过，覆盖注册、审批、四角色权限、固定八账号、运营备注、会员资产、头像、CSRF、修改密码和跨设备 Session 失效。

已通过的 User System Browser E2E：`30374950288`。

自动化证明功能流程和浏览器合同成立，但正式生产切换前仍需在目标 HTTPS 同源代理后检查 Secure Cookie、代理 Header、真实浏览器视觉和多标签页行为。

## 2. 验收数据规则

- 仅使用虚构姓名、邮箱、手机号、基金代码和持仓数值。
- 不在截图、日志、Markdown 或 Issue 中记录密码、Cookie、CSRF、重置凭证或真实客户数据。
- 固定演示角色包括 `ceo`、`tech_lead`、`employee`、`member`。
- Platform Live Write、Runtime Live Write、Exit Monitor 和 PostOnly Chase 全程保持关闭。
- 生产环境不得初始化 `demo_*` 账号。

## 3. 已自动化通过的流程

### 公共注册与登录

- 注册页只允许申请会员或员工。
- 待审批账号不能登录。
- CEO 可审批会员申请。
- Cookie 为 HttpOnly，前端不持久化 Session Token 或 CSRF。
- 登录、失败、锁定和权限错误使用稳定错误合同。

### CEO

- 查看用户列表、搜索和详情。
- 创建和审批用户。
- 维护会员持仓和基金单位净值。
- 编辑 VIP 运营备注。
- 运营备注不进入会员端，审计详情不保存备注正文。
- 敏感管理动作遵循重新认证和目标角色限制。

### 技术负责人

- 可查看权限范围内的用户。
- CEO 和其他技术负责人保持受保护和脱敏。
- 不能修改、重置或强退受保护目标。
- 不获得 Live Write 权限。

### 员工

- 登录后存在合法页面。
- 用户目录按权限脱敏。
- 不能执行管理写操作或读取任意会员持仓。

### 会员

- 只能读取自己的资料、设备和持仓。
- 资产页显示账户估值、累计投入、累计收益、基金数量和持仓明细。
- 三个固定 VIP 分别验证正收益和负收益场景。
- NAV 缺失与过期状态不会伪造为 0。
- 不能修改持仓或 NAV。

### 资料、头像、Session 与 CSRF

- 资料更新和显式清空字段通过。
- 头像上传、读取和删除通过。
- CSRF 轮换及同源多标签页行为通过。
- 修改密码后其他设备 Session 失效。
- 陈旧或撤销 Session 不能依赖前端内存状态继续访问受保护页面。

### 安全负向流程

- API Key 不能获得人类 CEO 权限。
- Browser Session 不能调用 Live Write 路由。
- 会员不能读取其他会员持仓。
- 敏感响应使用 `Cache-Control: no-store`。
- 审计不包含密码、原始 Token、完整联系方式或完整持仓快照。

## 4. 本地合并后的可选视觉冒烟

本地合并后建议人工打开一次常用浏览器，只检查视觉和交互，不必重复完整 API 验收：

- CEO 登录，进入用户管理并打开 VIP 详情。
- 保存一条虚构运营备注。
- 分别登录一个员工和一个 VIP。
- 检查窄窗口下用户详情抽屉和会员资产卡片。
- 修改 VIP 密码后确认另一个标签页回到登录页。
- 检查控制台没有未解释错误。

固定测试账号初始化方式见 `USER_SYSTEM_DEMO_ACCOUNTS.md`。

## 5. 生产代理后必须检查

以下不能由隔离 CI 代替：

- 前端与 `/api/v1` 使用相同 Scheme、Host 和 Port。
- `Set-Cookie` 包含 `Secure; HttpOnly; SameSite=Lax; Path=/`。
- HTTP 跳转 HTTPS。
- 代理保留 `Host`、`Origin`、客户端 IP 和 Request ID Header。
- 非受信 Origin 写请求被拒绝。
- 关闭全部标签后没有持久化 CSRF。
- 登录、注册和重置密码具有代理层限流。

## 6. 证据状态

| 项目 | 状态 | 证据 |
|---|---|---|
| 公共注册与登录 | passed | Browser E2E `30374950288` |
| CEO 管理与运营备注 | passed | Browser E2E `30374950288` |
| 技术负责人范围 | passed | Browser E2E `30374950288` |
| 员工脱敏 | passed | Browser E2E `30374950288` |
| 会员本人持仓与资产 | passed | Browser E2E `30374950288` |
| 资料与头像 | passed | Browser E2E `30374950288` |
| Session/CSRF | passed | Browser E2E `30374950288` |
| 负向权限与 Live 隔离 | passed | Browser E2E 与 Platform CI |
| 本地视觉冒烟 | optional | 本地合并后执行 |
| 生产代理与 Secure Cookie | pending production | 目标主机执行 |

## 7. 通过标准

当前分支已经满足本地代码集成条件。生产代理与 Secure Cookie 验证仅在正式部署前执行；它不阻塞项目负责人把本分支合入本地更新后的项目，但未完成前不得宣称生产切换就绪或开启 Live Write。
