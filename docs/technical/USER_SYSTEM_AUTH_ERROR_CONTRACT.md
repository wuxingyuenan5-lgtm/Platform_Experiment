# 用户系统认证与授权错误合同

状态：`active / implemented, executable verification pending`
适用产品：`Platform`
Issue：`#117`
架构基线：`USER_SYSTEM_TECHNICAL_ARCHITECTURE.md`

## 1. 目的

本合同统一 Browser Session、API Key、认证保障等级、权限依赖、Origin、CSRF 和请求身份绑定的错误响应。

目标：

- 前端不再依赖英文错误消息判断 Session 是否失效；
- API 调用方可稳定区分认证失败、授权失败、安全配置失败和并发/业务失败；
- AuditEvent 记录稳定错误代码，但不记录密码或原始 Token；
- 不改变现有状态码、API-Key 角色、LiveTradingSession 或 Live Write 闸门。

本合同不覆盖各业务模块自己的领域错误码，例如用户资料不变量、持仓版本冲突或最后 CEO 保护；这些错误继续由对应服务定义。

## 2. 响应格式

认证中间件拒绝请求时返回：

```json
{
  "detail": {
    "code": "invalid_session",
    "message": "Browser session is invalid"
  },
  "requestId": "request-correlation-id"
}
```

同时返回：

```text
X-Request-ID: request-correlation-id
```

无 Cookie 的 401 Bearer 认证失败继续返回：

```text
WWW-Authenticate: Bearer
```

FastAPI 权限依赖返回相同的 `detail.code/detail.message` 结构。请求关联 ID 始终可从 `X-Request-ID` 获取；认证中间件直接拒绝的响应还会在 JSON 顶层返回 `requestId`。

## 3. 稳定错误代码

### 3.1 凭证和配置

| Code | HTTP | 含义 |
|---|---:|---|
| `bearer_required` | 401 | 当前路由要求 Bearer，但请求未提供有效 Bearer 结构 |
| `credential_invalid` | 401 | API Key 不存在或哈希不匹配 |
| `credential_inactive` | 403 | API Key 存在但已停用 |
| `ambiguous_credentials` | 400 | 同一请求同时携带 Bearer 和 Browser Session Cookie |
| `auth_configuration_invalid` | 503 | API-Key 配置格式、角色或哈希配置无效 |
| `live_auth_mode_required` | 503 | Live 环境未使用安全的 API-Key 认证模式 |
| `development_identity_invalid` | 503 | Development Identity 的角色配置无效 |
| `auth_mode_unsafe` | 503 | 当前认证模式无法安全解析 |

### 3.2 Browser Session

| Code | HTTP | 含义 |
|---|---:|---|
| `invalid_session` | 401 | Session 缺失、撤销、过期、授权版本失效或上下文不可用 |
| `browser_sessions_disabled` | 503 | 服务端明确关闭 Browser Session |
| `session_timestamp_invalid` | 503 | Session 时间字段缺少有效时区或配置损坏 |
| `account_inactive` | 403 | Session 对应用户已不是 active 状态 |
| `account_temporarily_locked` | 423 | Session 对应用户仍处于临时安全锁定窗口 |

### 3.3 保障等级、权限和身份绑定

| Code | HTTP | 含义 |
|---|---:|---|
| `human_session_required` | 403 | 客户身份域只允许 Browser Session，API-Key wildcard 不豁免 |
| `live_api_key_required` | 403 | Live Write 只允许 API-Key Principal |
| `permission_denied` | 403 | Principal 缺少路由要求的显式权限 |
| `principal_unavailable` | 401 | 路由依赖没有获得认证中间件建立的 Principal |
| `request_identity_mismatch` | 403 | 请求体 actor/reviewer 等身份字段与 Principal 不一致 |

### 3.4 Origin 和 CSRF

| Code | HTTP | 含义 |
|---|---:|---|
| `untrusted_origin` | 403 | Cookie 写请求没有可信 Origin |
| `csrf_required` | 403 | Cookie 写请求未提供 `X-CSRF-Token` |
| `csrf_invalid` | 403 | CSRF Token 哈希不匹配 |

## 4. 前端 Session 处理

浏览器客户端只把以下错误视为当前 Session/CSRF 内存不可继续使用：

```text
invalid_session
human_session_required
csrf_required
csrf_invalid
account_inactive
account_temporarily_locked
browser_sessions_disabled
session_timestamp_invalid
```

处理规则：

1. 清除当前标签页的内存 CSRF；
2. 通过同源 `BroadcastChannel` 通知其他标签页清除内存 CSRF；
3. 不写入 `localStorage`、`sessionStorage` 或持久化 Pinia；
4. 路由守卫下一次导航调用 `/auth/me` 尝试重新水合；
5. Cookie 仍有效时恢复新的 CSRF；Cookie 无效时进入登录页。

`permission_denied`、`recent_reauthentication_required` 和普通业务 403 不自动清除 Session；调用方应显示权限或近期再认证提示。

在旧字符串错误完全退出前，前端可保留对历史 `CSRF token` / `browser session` 字符串的兼容判断，但新代码和测试必须优先使用稳定 `code`。

## 5. 审计

认证或授权拒绝的 AuditEvent `details_json` 至少记录：

```text
method
path
roles
credentialId（适用时）
required permission（适用时）
code
detail
```

禁止记录：

```text
原始 API Key
Session Cookie
CSRF Token
密码
一次性重置凭证
完整客户敏感数据
```

审计写入失败不能使拒绝请求 fail-open。原本应拒绝的请求仍然拒绝。

## 6. 兼容与验证

必须保持：

- 原 HTTP 状态码语义；
- 401 Bearer challenge；
- API-Key 与 Browser Session 歧义拒绝；
- 客户身份域 Session-only；
- Live Write API-Key-only；
- Actor Binding；
- 现有 LiveTradingSession、Kill Switch、对账和绝对限额。

直接验证至少包括：

- Cookie + Bearer 返回 `ambiguous_credentials`；
- API-Key wildcard 访问 `/me` 返回 `human_session_required`；
- Browser Session 调用 Live Write 返回 `live_api_key_required`；
- 无效或过期 Session 返回 `invalid_session`；
- 缺少/错误 CSRF 分别返回 `csrf_required` / `csrf_invalid`；
- 响应 `requestId` 与 `X-Request-ID` 一致；
- AuditEvent 记录 `code` 且不包含原始凭证。

当前代码和直接测试已提交，但 Ruff、Pyright、分类 Pytest、前端类型检查、构建和 PR CI 尚未在可执行仓库环境中运行。
