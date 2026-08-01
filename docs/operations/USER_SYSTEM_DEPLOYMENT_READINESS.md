# 用户系统部署、备份与恢复就绪手册

状态：`local integration ready / production host rehearsal pending`

- Issue：`#117`
- Draft PR：`#118`
- 交付分支：`feature/issue-117-user-system`
- 本地交接：`USER_SYSTEM_LOCAL_INTEGRATION_HANDOFF.md`
- 浏览器验收：`USER_SYSTEM_BROWSER_ACCEPTANCE.md`

## 1. 适用边界

用户系统代码、自动化测试、浏览器 E2E、构建、Secret Scan 和版本一致性已经通过，可由项目负责人合入本地更新后的项目。

本手册剩余内容只针对正式生产部署。目标主机、HTTPS 代理、真实数据路径和恢复目录无法由 GitHub Actions 代替，因此这些步骤不阻塞本地代码集成，但会阻塞生产切换。

## 2. 三项生产决策

| 决策 | 安全默认 | 状态 |
|---|---|---|
| 旧 Go/MySQL 是否存在真实用户 | 不导入 | pending production |
| 初始会员持仓来源 | CEO `manual_admin` | pending production |
| 生产 Origin 模型 | 同源 `/api/v1` | pending production |

任一结论与安全默认冲突时，停止切换并新建独立 Critical Issue，不在部署现场临时改变认证或迁移语义。

## 3. 推荐生产路径与配置

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

要求：

- Backup Root 和 Restore Root 不等于、也不位于任何活动数据路径。
- 头像目录只包含根目录下随机 `.webp` 文件，不包含软链接、子目录或临时文件。
- 配置、API Key 和操作 Token 不进入 Git、Markdown、截图或命令历史。
- Platform 与 Runtime Live Write 保持关闭。
- 生产环境不得运行固定演示账号初始化脚本。

## 4. 同源 HTTPS 代理

推荐模型：

```text
https://<production-host>/        → platform-web 静态前端
https://<production-host>/api/v1 → platform-api
```

必须验证：

- 浏览器与 API 使用同一 Scheme、Host 和 Port。
- HTTP 重定向 HTTPS。
- 代理保留 `Host`、`Origin`、客户端 IP 和 Request ID Header。
- `Set-Cookie` 包含 `Secure; HttpOnly; SameSite=Lax; Path=/`，不设置不必要的 Domain。
- `/auth/me`、`/me`、`/users/**` 返回 `Cache-Control: no-store`。
- 登录、注册和重置密码具有等于或严于应用层的代理限流。

## 5. 自动化已覆盖的备份边界

`POST /api/v1/ops/backups` 生成：

1. `platform.db`：SQLite Online Backup；
2. `runtime_journal.db`：SQLite Online Backup；
3. `avatars.zip`：仅包含安全头像根目录中的 `.webp` 文件；
4. `manifest.json`：checksum、size、integrity、关键 table count、头像文件数和总字节数。

自动化已覆盖：

- 用户、Session、密码重置凭证、基金、持仓和 NAV 的关键计数；
- Platform 与 Runtime SQLite integrity；
- 头像软链接、子目录、路径穿越、重复文件和异常扩展名拒绝；
- Restore Drill 不修改活动路径；
- 恢复副本强制关闭两层 Live Write。

最终 Platform API **403 项测试通过**，完整 Platform CI 为 `30374949395`。

## 6. 生产主机 Restore Drill

在受控主机上执行：

1. 记录活动数据库、Runtime Journal、头像、Backup Root 和 Restore Root 的绝对路径。
2. 确认两层 Live Write 为 false。
3. 创建一次唯一 Idempotency Key 的 Backup。
4. 核对 Manifest 中 checksum、integrity、table count 和头像统计。
5. 在全新 Restore Drill Directory 中恢复。
6. 核对 Platform、Runtime 和 avatars integrity 均为 `ok`。
7. 抽查恢复副本中 CEO、会员、Session、持仓、NAV 和头像记录存在，但不复制真实值到验收记录。
8. 使用生成的 `safe-startup.env` 进行只读启动。
9. 停止恢复副本，确认活动数据路径未改变。
10. 记录 Backup ID、Restore Drill ID、负责人、时间和脱敏证据位置。

## 7. 切换与回退

生产切换前：

- 三项生产决策已确认。
- HTTPS 同源代理和 Secure Cookie 验证通过。
- Backup、Restore Drill 和只读恢复启动成功。
- 旧服务只读窗口、代理切换点和回退时间窗明确。
- 正式初始 CEO 使用安全渠道交付临时密码。

回退触发条件：

- Cookie/CSRF 经生产代理后不稳定；
- 角色或字段范围越权；
- 用户、持仓、NAV 或头像数据不一致；
- 迁移、启动或恢复校验失败；
- Live Write 边界出现意外变化。

回退只恢复认证与用户系统流量，不开启 Live Write。正式替换生产数据库需要停机、双人审批，并先在新路径完成只读核对。

## 8. 当前状态

| 项目 | 状态 |
|---|---|
| 本地代码交接 | passed |
| Platform CI | passed `30374949395` |
| Browser E2E | passed `30374950288` |
| Secret Scan | passed `30374949706` |
| Version Consistency | passed `30374949357` |
| 三项生产决策 | pending production |
| 同源代理与 Secure Cookie | pending production |
| 受控主机 Backup | pending production |
| Restore Drill | pending production |
| 只读恢复启动 | pending production |
| 回退演练 | pending production |

## 9. 结论

当前分支可以合入本地更新后的项目。未完成生产主机演练不影响本地合并，但在上述 production 项目通过前，不得宣称生产切换完成，也不得开启 Platform Live Write 或 Runtime Live Write。
