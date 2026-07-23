# V6 Production Gate 5C：密钥托管、轮换与全链路脱敏

状态：`engineering accepted / merge pending`  
实施分支：`hardening/v6-production-gate-secret-provider-redaction`  
Pull Request：`#25 Add production secret providers, rotation metadata, and redaction`  
跟踪 Issue：`#24 V6 Production Gate 5C：SecretProvider、密钥轮换与全链路脱敏`  
前置阶段：Production Gate 5A/5B 已通过 PR `#23` 合入 main  
工程验收：`Platform CI #408 / run 30025117570`  
独立 Secret Scan：`run 30025117534`  
更新时间：`2026-07-23`

## 1. 目标

```text
secret:// provider/name
→ SecretProvider.inspect / resolve
→ Environment 或 Windows Credential Manager
→ 版本与轮换元数据
→ 递归脱敏
→ Gateway 内部消费
```

本阶段不配置真实 Bybit、MT5 或认证 Token，也不打开任何 Live Write。真实凭证只在受控主机中设置。

## 2. Secret Reference

正式引用必须显式指定 Provider：

```text
secret://environment/bybit-live-001
secret://windows-credential-manager/bybit-live-001
```

旧 `secret://bybit-live-001` 暂时按 Environment 兼容，并在 Inspection 中标记 `legacyReference=true`。新配置和文档不得继续创建隐式引用。

## 3. Provider Contract

统一能力：

- `inspect`：返回 Provider、Secret Name、Version、字段存在性和缺失字段；不返回值。
- `resolve`：仅在 Runtime Gateway 内部读取实际值。
- 未知 Provider、非法引用、依赖缺失和平台不支持全部 fail-closed。

当前 Provider：

- Environment：读取 `VG_SECRET_<NAME>_<FIELD>`，版本来自 `_VERSION`。
- Windows Credential Manager：读取 `VariableGlobal/<name>/<FIELD>`；非 Windows 或缺少 pywin32 时拒绝。

## 4. Rotation Metadata

```http
POST /api/v1/security/credential-rotations
GET  /api/v1/security/credential-rotations
```

只保存 Credential Ref、Provider、Version、Rotated At、Rotated By、Reason 和幂等载荷哈希。不得保存旧值或新值。

写入需要 admin；读取需要 audit 权限。轮换完成后由运维重启或重新加载 Runtime，避免继续使用旧进程内客户端。

## 5. Redaction

Backend 与 Runtime 统一覆盖：

- 嵌套 dict/list/tuple/set。
- authorization、token、api_key、api_secret、secret、password、passphrase、private_key。
- Bearer Token。
- 私钥块。
- URL 中的认证信息。
- Exception 和自由文本中的受控字段赋值。

脱敏结果统一使用 `[REDACTED]`。AuditEvent、异常响应、能力检查和测试快照不得出现凭证内容。

## 6. CI

严格 Gate 覆盖：

- Runtime SecretProvider、Redactor 及测试。
- Backend Rotation Metadata、Redactor 及测试。
- Repository Secret Scan。
- 既有 Backend、Runtime 与 Frontend 全量回归。

## 7. 工程验收

- [x] Environment Provider 使用显式引用并返回版本元数据。
- [x] Windows Credential Manager Provider 支持注入测试，非 Windows fail-closed。
- [x] Legacy Reference 明确标记并保持迁移兼容。
- [x] Inspection 不返回凭证内容。
- [x] Rotation API 只记录元数据并具备幂等/冲突语义。
- [x] Rotation Actor 来自认证 Principal。
- [x] Backend 与 Runtime Redactor 覆盖嵌套结构、Bearer、URL Password、私钥和异常。
- [x] Live 配置模板切换为显式 Provider Reference。
- [x] Platform Backend strict/full Ruff 与 Pytest 通过。
- [x] Execution Runtime strict/full Ruff 与 Pytest 通过。
- [x] Frontend frozen install、type-check 与 production build 通过。
- [x] Repository Safety 与独立 Secret Scan 通过。
- [x] Platform CI `#408 / run 30025117570` 全部通过。
- [x] README、START-HERE、API Spec、Release Gate、总计划与 Changelog 已同步。

## 8. 运营验收

- [ ] 受控 Windows 主机建立 Credential Manager 项目。
- [ ] Runtime Inspection 只显示 Provider、Version 和字段存在性。
- [ ] Bybit 与 MT5 只读连接通过，日志中不出现凭证内容。
- [ ] 完成一次版本轮换并重启 Runtime。
- [ ] 轮换前后只读查询和 EOD 均可追溯。
- [ ] 回滚到关闭 Live Write、空临时 allowlist 和安全 Kill Switch 状态。

## 9. 延期

告警、调度、备份和恢复进入 Production Gate 5D。云端 Secret Manager 作为后续 Provider，不阻塞当前 Windows 实盘主机。