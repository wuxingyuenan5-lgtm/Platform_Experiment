# 用户系统浏览器验收手册

状态：`automated verification passed / manual acceptance pending`
适用版本：`Platform Experiment 0.9.0`
Issue：`#117`
Draft PR：`#118`
任务包：`../../tasks/issue-117-user-system.md`
部署与恢复：`USER_SYSTEM_DEPLOYMENT_READINESS.md`

## 1. 目的

本手册用于在真实同源浏览器环境中验证用户系统。自动化 CI 证明代码、类型、构建和后端合同成立，但不能代替 Cookie、反向代理、多标签页和实际页面操作证据。

```text
静态配置
→ 公共注册与登录
→ CEO 管理
→ 技术负责人目标范围
→ 员工脱敏只读
→ 会员本人持仓
→ Session/CSRF/头像
→ 负向权限与 Live 隔离
→ 证据归档
```

任何步骤出现越权、凭证持久化、跨用户持仓、Cookie 属性错误或 Live Write 放行，立即停止验收。

## 2. 验收数据规则

- 仅使用虚构姓名、邮箱、手机号、基金代码和持仓数值。
- 不在截图、日志、Markdown 或 Issue 中记录密码、Cookie、CSRF、重置凭证或真实客户数据。
- 四类测试账号：`ceo`、`tech_lead`、`employee`、`member`。
- 测试结束后撤销全部测试 Session；是否保留测试账号由验收负责人决定。
- Platform Live Write、Runtime Live Write、Exit Monitor 和 PostOnly Chase 全程保持关闭。

## 3. 环境前置

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

- [ ] 前端通过同一 Origin 提供，默认开发地址为 `http://localhost:4373` 或 `http://127.0.0.1:4373`。
- [ ] 浏览器请求 `/api/v1`，不直接访问跨域 Backend 地址。
- [ ] `VG_CORS_ORIGINS` 只包含实际受信 Origin。
- [ ] `VG_LIVE_TRADING_ENABLED=false`。
- [ ] Runtime Live Write 保持 `false`。
- [ ] 使用全新或已备份的测试数据库和独立头像目录。
- [ ] 浏览器 DevTools 已打开 Network、Application/Cookies 和 Console。

## 4. 公共注册与登录

### 4.1 注册

- [ ] 注册页只允许申请 `member` 或 `employee`。
- [ ] 页面与 API 均不能申请 `ceo` 或 `tech_lead`。
- [ ] 员工申请缺少部门时被拒绝。
- [ ] 会员申请缺少会员类型时被拒绝。
- [ ] 注册成功后状态为待审批，不能直接登录。
- [ ] 重复用户名、邮箱或手机号返回稳定错误码。

### 4.2 登录与锁定

- [ ] 未审批、已拒绝、停用或锁定账号不能登录。
- [ ] 正确密码登录后返回个人信息和显式权限集合。
- [ ] Cookie 为 HttpOnly；前端存储中没有 Session Token、Bearer Token 或 CSRF 持久化值。
- [ ] 连续失败达到阈值后账号临时锁定，锁定到期后可恢复。
- [ ] 登录、失败和锁定均产生脱敏审计事件。

## 5. CEO 验收

- [ ] 可查看用户列表、搜索、过滤和分页。
- [ ] 可创建 CEO、技术负责人、员工和会员；员工/会员必填字段不能绕过。
- [ ] 可审批或拒绝注册申请。
- [ ] 可修改普通用户角色和状态。
- [ ] 最后一个活动 CEO 不能被停用、降级或删除权限。
- [ ] 敏感操作要求近期重新认证。
- [ ] 密码重置凭证只展示一次，使用后失效。
- [ ] 可撤销指定用户 Session。
- [ ] 可维护会员持仓和基金单位净值，写入来源固定为 `manual_admin`。

## 6. 技术负责人验收

- [ ] 能查看用户目录。
- [ ] 员工和会员详情可按权限显示完整管理字段。
- [ ] CEO 和其他技术负责人详情保持脱敏。
- [ ] 不能修改 CEO 或其他技术负责人。
- [ ] 不能重置、强退或更改受保护目标。
- [ ] 不具备全部会员持仓读取权限。
- [ ] 不能获得 LiveTradingSession、交易写入或核心风险配置权限。

## 7. 员工验收

- [ ] 登录后存在合法首页，不出现空白路由。
- [ ] 用户目录仅返回脱敏字段。
- [ ] 不能打开任意用户的完整详情或执行管理写操作。
- [ ] 不能查看任意会员持仓。
- [ ] 直接输入无权限 URL 返回禁止访问或安全重定向。

## 8. 会员验收

- [ ] 登录后只能读取自己的资料、设备和持仓。
- [ ] API 不接受由浏览器指定其他 `userId` 读取持仓。
- [ ] NAV 可用时显示市值和收益；所有 Decimal 保持精确字符串语义。
- [ ] NAV 缺失时显示 unavailable，不显示伪造的 0。
- [ ] NAV 超过时效时显示 stale。
- [ ] 会员不能修改持仓或 NAV。

## 9. 资料、头像与 Session

### 9.1 资料 PATCH

- [ ] 只修改展示名时，邮箱和手机号保持不变。
- [ ] 显式清空邮箱或手机号发送 `null`，并保留至少一个联系方式。
- [ ] 使用旧 `rowVersion` 更新时返回并发冲突。

### 9.2 头像

- [ ] JPEG、PNG、WebP 可上传并统一输出为 WebP。
- [ ] multipart 请求包含浏览器生成的 boundary。
- [ ] 超字节、超像素、损坏文件或不支持格式被拒绝。
- [ ] 替换后旧文件被清理；删除后资料中的头像引用清空。
- [ ] URL/key 不允许路径穿越。

### 9.3 Session 与 CSRF

- [ ] `/auth/me` 轮换 CSRF 后当前页面仍可写入。
- [ ] 第二个同源标签页通过内存 BroadcastChannel 获得最新 CSRF。
- [ ] 关闭全部标签后不存在持久化 CSRF。
- [ ] 401 或 CSRF 失效后前端清空旧状态；Cookie 有效时可重新水合。
- [ ] 修改密码后其他 Session 全部失效。
- [ ] 退出成功删除 Cookie；陈旧 Cookie 也能被浏览器清理。

## 10. 安全与负向验收

- [ ] 同时携带 Bearer 与 Cookie 时请求被拒绝。
- [ ] API-Key `admin` 不能调用人类用户和会员持仓路由。
- [ ] Browser Session 不能调用现有 Live Write 路由。
- [ ] 非受信 Origin 的写请求被拒绝。
- [ ] 敏感响应包含 `Cache-Control: no-store`。
- [ ] 错误响应包含稳定 `detail.code/detail.message` 和 Request ID。
- [ ] 审计不包含密码、原始 Token、完整联系方式或完整持仓快照。

## 11. 证据记录

| 项目 | 结果 | 证据位置 | 验收人 | 时间 |
|---|---|---|---|---|
| 公共注册与登录 | pending |  |  |  |
| CEO 管理 | pending |  |  |  |
| 技术负责人范围 | pending |  |  |  |
| 员工脱敏 | pending |  |  |  |
| 会员本人持仓 | pending |  |  |  |
| 资料与头像 | pending |  |  |  |
| Session/CSRF | pending |  |  |  |
| 负向权限与 Live 隔离 | pending |  |  |  |

证据可以是脱敏截图、Network Header 摘要、Request ID、审计事件 ID 和测试环境日志位置。禁止粘贴 Cookie、CSRF、密码或重置凭证。

## 12. 通过标准

只有全部项目通过，且不存在未解释的越权、数据泄露、Session 恢复异常或持仓水平越权，才可将 PR #118 从 Draft 改为 Ready for review。人工验收通过仍不等于允许生产切换或开启 Live Write。
