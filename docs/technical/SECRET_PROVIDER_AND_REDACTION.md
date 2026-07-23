# Secret Provider and Redaction Contract

状态：`active`  
适用版本：`Platform V6 / Production Gate 5C`  
实施计划：`../planning/V6-Production-Gate-密钥托管与脱敏.md`

## 1. 安全边界

```text
Repository / Database / API / Audit
        只保存 Reference 与 Metadata
                    ↓
             Execution Runtime
                    ↓
        SecretProvider.resolve（内部）
                    ↓
             Venue Client
```

Secret 值不得越过 Runtime Gateway 内部边界。Platform 只管理引用、Provider、版本与轮换元数据。

## 2. Reference Grammar

```text
secret://<provider>/<secret-name>
```

当前 Provider：

- `environment`
- `windows-credential-manager`

Secret Name 不允许为空或包含 `..` 路径段。未知 Provider 不允许回退到 Environment。

Legacy `secret://<name>` 仅用于迁移兼容，等价于 Environment Provider，并显式标记为 legacy。

## 3. Environment Provider

Reference：

```text
secret://environment/bybit-live-001
```

字段：

```text
VG_SECRET_BYBIT_LIVE_001_API_KEY
VG_SECRET_BYBIT_LIVE_001_SECRET
VG_SECRET_BYBIT_LIVE_001_VERSION
```

MT5 使用 LOGIN、PASSWORD、SERVER 和 VERSION。`inspect` 只报告字段是否存在；`resolve` 才读取值。

## 4. Windows Credential Manager Provider

Reference：

```text
secret://windows-credential-manager/bybit-live-001
```

Generic Credential Target：

```text
VariableGlobal/bybit-live-001/API_KEY
VariableGlobal/bybit-live-001/SECRET
VariableGlobal/bybit-live-001/VERSION
```

约束：

- 仅 Windows 主机可用。
- 默认实现依赖可选 `pywin32`。
- 非 Windows、依赖缺失和字段缺失全部 fail-closed。
- Test 使用注入 Reader，不访问真实 Credential Manager。

## 5. Inspection

Inspection 可返回：

- credentialRef
- provider
- secretName
- version
- configured
- availableFields
- missingFields
- legacyReference
- Environment Provider 的 envPrefix

Inspection 不得返回值、长度、哈希、前后缀或可用于推断 Secret 的信息。

## 6. Resolution

`resolve` 只允许由 Runtime Gateway Adapter 调用。调用方必须明确 required fields：

- Bybit：API_KEY、SECRET。
- MT5：LOGIN、PASSWORD、SERVER。

Provider 返回的 dict 不得被写入日志、异常详情、API Response、AuditEvent 或数据库。

## 7. Rotation Metadata

Platform 表 `credential_rotation_records` 只保存：

- idempotency key
- payload hash
- credential reference
- provider
- version
- rotatedAt
- rotatedBy
- reason
- createdAt

同一幂等键或同一 Reference/Provider/Version 只允许相同载荷重放；不同载荷返回 409。Actor 来自认证 Principal。

Rotation Record 不代表 Secret 已经在外部 Provider 中成功写入。运维必须先在受控主机完成 Provider 变更，再记录元数据并重启/重载 Runtime。

## 8. Redaction

递归 Redactor 识别：

- Sensitive Key 名称及后缀。
- Bearer Token。
- 私钥块。
- `api_key=...`、`password:...` 等文本赋值。
- URL UserInfo 中的密码。
- Exception Message。

统一替换为 `[REDACTED]`。非敏感业务字段保持原值，以便对账和排障。

## 9. Failure Semantics

- Unknown Provider：配置错误，拒绝。
- Invalid Reference：配置错误，拒绝。
- Provider Unavailable：拒绝，不回退。
- Missing Field：拒绝，错误只列字段名。
- Rotation Provider 与 Reference 不一致：422。
- Rotation Identity Payload Conflict：409。

## 10. 运营要求

- Real Secret 不进入 Git、Markdown、Issue、PR、截图或聊天记录。
- Windows Credential Manager Target 建立和轮换由受控主机人工执行。
- 每次轮换保留版本、操作人、时间和原因。
- Runtime 轮换后重启或显式 Reload；不允许无限期使用旧 Client Cache。
- Live Write 在轮换和验证期间保持关闭。
- 只读 Preflight、Venue Readiness 与 EOD 必须在轮换后重新执行。