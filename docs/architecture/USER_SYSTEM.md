# 用户系统架构

用户系统在 Platform API 内保持单一身份权威，统一浏览器用户、API 调用者、角色 Capability、资源范围、Session、审计和个人账号。正常交易权限见 AUTHORIZATION.md；它不替代交易风险或 Runtime Live Write 门禁。

详细权限与错误合同见 [AUTHORIZATION](../contracts/AUTHORIZATION.md)、[ACCESS_MATRIX](../contracts/ACCESS_MATRIX.md) 和 [AUTH_ERRORS](../contracts/AUTH_ERRORS.md)；会员持仓与净值见 [MEMBER_HOLDINGS](../contracts/MEMBER_HOLDINGS.md)。

## 身份与凭证边界

```text
Browser credential / API key
  → Authentication
  → trusted Principal
  → Capability + resource scope
  → domain authorization
  → audit
```

- 浏览器业务使用服务端 Session，不在浏览器保存长期身份 JWT。
- API Key 继续服务明确的程序化接口；它不能自动取得浏览器用户权限。
- Browser Session 与 API Key 是不同认证凭证，均按角色和范围授权；LiveTradingSession 仅为历史验收兼容记录，不再授权正常交易。
- Live 路由还必须通过审批、风险、Kill Switch、Allowlist 及 Platform/Runtime 双写入门禁。
- 无法确认 Principal、Capability 或资源范围时默认拒绝。

## 浏览器角色

| 角色 | 产品访问 | 内部管理 | 写入基线 |
|---|---|---|---|
| CEO | 全部正式页面 | 全部内部视图 | 广泛业务能力，但交易安全门禁独立生效 |
| 技术负责人 | 全部正式页面 | 运行与受限身份管理 | 受 Capability、目标范围和安全规则约束 |
| 员工 | 业务页面只读 | 风险与账号目录只读 | 默认拒绝业务写入 |
| 会员 | 业务页面只读 | 不可见且 API 拒绝 | 默认拒绝业务写入 |

角色只作为 Capability 集合的输入。前端菜单、直接 URL 和后端 API 必须消费同一权限语义；前端隐藏不是授权。

## Session 与账号安全

- Session 由服务端保存、可撤销、具有绝对到期和空闲到期。
- Cookie 使用 HttpOnly、合适的 SameSite 和生产 Secure 策略；状态修改请求具备 CSRF 防护。
- 密码使用批准的自适应哈希，不记录明文、可逆密文或可推断摘要。
- 登录失败、临时锁定、账号生命周期和凭证撤销是不同状态。
- 修改密码、管理员重置和高风险身份操作需要近期认证、明确审计和会话处置。
- 密码恢复凭证一次性、短时有效且只保存不可逆表示。

## 用户生命周期

- 用户启用、停用和锁定不通过物理删除表达。
- 最后一个有效 CEO 受到事务级并发保护，不能被停用、降级或删除。
- 管理员不能通过修改请求中的 actor 字段冒充其他 Principal。
- 对受保护目标的角色、状态、密码和会话操作使用独立目标范围规则。

## 数据与模块 Owner

| 事实 | Owner |
|---|---|
| 用户、角色、状态与凭证元数据 | identity/user repository |
| Browser Session 与撤销 | session repository/service |
| Capability 与目标范围 | authorization policy/registry |
| 个人资料与头像引用 | user profile service |
| 会员持仓与单位净值 | member holdings read model |
| 审计事件 | audit owner；业务模块提交事实，审计层持久化 |

数据库 DDL、迁移和 Seed 纪律以 [database/README.md](../database/README.md) 为准。公开 DTO、路由和错误不得在多个模块重复定义。

## 会员持仓边界

- 会员只能读取本人获授权的账户和持仓。
- 持仓、估值、资金流、NAV 和数据质量具有明确时点、币种和来源。
- 会员视图是报告与查询模型，不成为正式账务或交易执行输入。
- 缺失账户、过期价格或不完整估值不得显示为零持仓或完整 NAV。

## 前端边界

- 用户与 Capability 可以进入全局状态；订单、持仓和正式收益仍从服务端查询。
- 401 表示需要重新认证，403 表示已认证但范围不足，两者不能混用。
- 个人账号与系统设置是不同产品区域。
- 前端不显示凭证、内部调试状态或可推断的 Secret 元数据。

## 部署与恢复

- 固定演示账号只允许本地和测试环境，不进入生产 Seed。
- 缺少生产认证、Cookie、数据库或 Secret 配置时启动应明确失败。
- 迁移前备份，恢复演练必须验证用户、Session、审计和会员读模型的一致性。
- 本地测试、浏览器验收或 CI 不证明生产代理、域名、凭据或真实用户数据就绪。

## 不变量

- Platform API 是身份与 Capability 的唯一业务权威。
- 高风险未知状态默认拒绝。
- 身份审批不能替代交易审批，交易审批不能替代 Live Write 门禁。
- 用户和审计数据变更保持事务性、可追溯和可恢复。
- 权限、合同或持久化语义变化必须同步对应合同与可执行测试。
