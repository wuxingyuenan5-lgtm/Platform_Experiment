# 用户系统部署、备份与恢复就绪手册

状态：`automated backup coverage passed / controlled-host rehearsal pending`
适用版本：`Platform Experiment 0.9.0`
Issue：`#117`
Draft PR：`#118`
浏览器验收：`USER_SYSTEM_BROWSER_ACCEPTANCE.md`
通用灾备基线：`../planning/V6-Production-Gate-监控备份恢复.md`

## 1. 目的

本手册将用户系统的生产切换条件、同源 Cookie 边界、Platform SQLite、Runtime Journal 与头像目录纳入一个受控部署与恢复流程。代码和 CI 不能代替受控主机演练。

## 2. 三项必须决策

| 决策 | 安全默认 | 当前状态 | 负责人 | 证据/结论 |
|---|---|---|---|---|
| 旧 Go/MySQL 是否存在真实用户 | 不导入 | pending |  |  |
| 初始会员持仓来源 | CEO `manual_admin` | pending |  |  |
| 生产 Origin 模型 | 同源 `/api/v1` | pending |  |  |

任一结论与安全默认冲突时，停止切换并新建独立 Critical Issue，不在部署现场临时改认证或迁移语义。

## 3. 生产路径与配置

```text
VG_DATABASE_PATH=<active-platform-db>
VG_RUNTIME_JOURNAL_PATH=<active-runtime-journal>
VG_AVATAR_DATA_DIRECTORY=<active-avatar-directory>
VG_OPERATIONS_BACKUP_ROOT=<separate-backup-root>
VG_OPERATIONS_RESTORE_ROOT=<separate-restore-root>
VG_CORS_ORIGINS=https://<production-host>
VG_ENVIRONMENT=production
VG_LIVE_TRADING_ENABLED=false
```

- [ ] Backup Root 和 Restore Root 不等于、也不位于任何活动数据文件路径。
- [ ] 头像目录仅包含根目录下的随机 `.webp` 文件，不包含软链接、子目录或临时文件。
- [ ] 配置、API Key 和操作 Token 不进入 Git、Markdown、截图或命令历史。
- [ ] Platform 与 Runtime Live Write 保持关闭。

## 4. 同源反向代理

推荐模型：

```text
https://<production-host>/        → admin-risk 静态前端
https://<production-host>/api/v1 → platform-backend
```

- [ ] 浏览器地址栏与 API 请求使用同一 Scheme、Host 和 Port。
- [ ] 代理保留 `Host`、`Origin`、客户端 IP 和 Request ID 相关 Header。
- [ ] 只允许 HTTPS；HTTP 重定向到 HTTPS。
- [ ] `Set-Cookie` 包含 `Secure; HttpOnly; SameSite=Lax; Path=/`，且不设置不必要的 Domain。
- [ ] 登录、`/auth/me`、`/me`、`/users/**` 返回 `Cache-Control: no-store`。
- [ ] 代理对登录、注册和重置密码采用等于或严于应用层的分布式限流。

## 5. 一致性备份对象

`POST /api/v1/ops/backups` 已生成：

1. `platform.db`：SQLite Online Backup；
2. `runtime_journal.db`：SQLite Online Backup；
3. `avatars.zip`：仅包含安全的头像根目录 `.webp` 文件；
4. `manifest.json`：脱敏的 checksum、size、integrity、关键 table count、头像文件数和总字节数。

Platform 关键计数已包含用户、Session、密码重置凭证、基金、会员持仓和基金单位净值表。Manifest 不暴露头像文件名。备份遇到头像软链接、子目录、临时文件或异常扩展名时 fail-closed。

自动化证据：头像归档、恢复目录安全、用户域计数、checksum、integrity 和异常目录项拒绝已进入完整 Backend 测试；Ruff、Pyright 和全部 **399** 项测试通过。

示例调用仅使用环境变量中的操作凭证：

```powershell
$headers = @{ Authorization = "Bearer $env:VG_OPERATIONS_TOKEN" }
$body = @{
  idempotencyKey = "user-system-backup-$(Get-Date -Format yyyyMMddHHmmss)"
  label = "user-system-precutover"
} | ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri "https://<production-host>/api/v1/ops/backups" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

不得把 Token 写入脚本文件或输出对象。

## 6. Restore Drill

`POST /api/v1/ops/restore-drills` 必须：

- 在新的 Restore Drill Directory 中恢复，不修改生产路径；
- 验证全部备份文件的 SHA-256；
- 对两个 SQLite 副本执行 `PRAGMA integrity_check` 和关键 Table Count；
- 安全解压头像归档，拒绝路径穿越、重复文件、软链接、非 `.webp` 文件和超限单文件；
- 核对头像文件数与总字节数；
- 在恢复的 Platform 副本中强制 Global Kill Switch enabled；
- 生成关闭两层 Live Write、清空 allowlist、额度为零的 `safe-startup.env`。

验收：

- [ ] `integrity.platform == ok`。
- [ ] `integrity.runtime == ok`。
- [ ] `integrity.avatars.status == ok`。
- [ ] 用户、Session、持仓与 NAV 的关键 Table Count 与 Manifest 一致。
- [ ] `avatars.restored` 文件数和总字节数与 Manifest 一致。
- [ ] 恢复目录不存在生产凭证文件。
- [ ] 生产 Platform DB、Runtime Journal 和头像目录未被修改。

## 7. 受控主机演练步骤

1. 记录活动数据库、Runtime Journal、头像、Backup Root 和 Restore Root 的绝对路径。
2. 确认两层 Live Write 为 false，Global Kill Switch 状态可解释。
3. 执行一次带唯一 Idempotency Key 的 Backup。
4. 核对 Manifest 中全部文件、checksum、integrity、table count 和头像统计。
5. 使用该 Backup 执行一次 Restore Drill。
6. 在恢复副本中抽查：CEO/会员记录、Session 行数、持仓/NAV 行数和头像文件存在性；不得复制真实值到验收记录。
7. 使用 `safe-startup.env` 对恢复副本做只读启动验证。
8. 停止恢复副本，确认生产服务与数据路径未受影响。
9. 记录负责人、时间、Backup ID、Restore Drill ID 和脱敏证据位置。

## 8. 切换与回退

切换前：

- [ ] 浏览器手册全部通过。
- [ ] 三项部署决策已签字确认。
- [ ] 最近一次 Backup 和 Restore Drill 成功。
- [ ] 旧服务是否保留只读窗口、DNS/代理切换点和回退时间窗明确。
- [ ] 初始 CEO 已通过 CLI 创建并使用临时密码安全交付。

回退触发条件：

- Cookie/CSRF 在生产代理后不稳定；
- 角色或字段范围越权；
- 用户、持仓、NAV 或头像数据不一致；
- 迁移、启动或恢复校验失败；
- 任何 Live 写入边界出现意外变化。

回退只恢复认证与用户系统流量，不开启 Live Write。正式替换生产数据库必须停机、双人审批，并先在新路径完成只读核对。

## 9. 演练记录

| 项目 | 状态 | 负责人 | 时间 | 证据/ID |
|---|---|---|---|---|
| 三项部署决策 | pending |  |  |  |
| 同源代理与 Secure Cookie | pending |  |  |  |
| 用户系统浏览器验收 | pending |  |  |  |
| Backup | pending |  |  |  |
| Restore Drill | pending |  |  |  |
| 只读恢复启动 | pending |  |  |  |
| 回退演练 | pending |  |  |  |

只有以上项目通过，PR #118 才可进入 Ready for review；合并后仍需独立生产变更批准。
