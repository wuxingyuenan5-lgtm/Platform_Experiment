# V6 Production Gate 5D：监控、告警、调度、备份与恢复

状态：`implementation complete / acceptance pending`
实施分支：`hardening/v6-production-gate-observability-backup-restore`
Pull Request：`#27 Add production monitoring, controlled operations, backup, and restore drills`
跟踪 Issue：`#26 V6 Production Gate 5D：监控告警、受控调度、备份与恢复演练`
总 Production Gate：Issue `#22`
更新时间：`2026-07-28`

## 1. 目标

在模块化单体 Platform Backend 与独立 Execution Runtime 的现有边界内，补齐本地 Windows 实盘主机持续运行所需的生产运维基础：

```text
Production Status
→ Alert Scan / Acknowledge / Close
→ Allowlisted Scheduler
→ SQLite Online Backup
→ New-directory Restore Drill
→ Safe Startup State
```

本阶段不注册真实 Windows Task Scheduler，不访问真实账户，也不打开 Live Write。

## 2. Production Status

```http
GET /api/v1/ops/production-status
```

汇总：

- Platform Database。
- Runtime `/status`。
- Venue Readiness。
- Credential Inspection 完整性。
- Global/Strategy/Account Kill Switch 数量。
- 当前 Approved LiveTradingSession。
- `result_unknown` Order。
- Manual Intervention 与 Residual Execution Risk。
- Open/Accepted Reconciliation Difference。
- 最新 EOD 状态、Scale Gate 与 SLA。
- 最新 Backup 与 Restore Drill。

Runtime 或 Venue 不可用必须返回明确失败状态，不能解释为空仓、零余额或 clean 状态。

## 3. Operational Alert

```http
POST /api/v1/ops/alerts/scan
GET  /api/v1/ops/alerts
POST /api/v1/ops/alerts/{alertId}/acknowledge
POST /api/v1/ops/alerts/{alertId}/close
```

Alert 具有：

- category、severity、fingerprint。
- subjectType、subjectId。
- owner、message、redacted details。
- firstSeenAt、lastSeenAt、occurrenceCount。
- open、acknowledged、closed。
- acknowledge/close actor、time、reason。

相同 category + subject 的重复扫描更新同一 fingerprint，不产生重复告警。已关闭条件再次出现时重新打开。

风险人员负责 acknowledge；Operations 完成处置后 close。所有动作写入 AuditEvent。

## 4. 受控调度

```http
POST /api/v1/ops/controlled-operations
GET  /api/v1/ops/controlled-operations
```

唯一允许任务：

- `health_scan`
- `backup`
- `eod`

每次运行固定 idempotencyKey、taskType、scheduledFor、actor、result 和 error。调度器不能下单、批准 Session、修改 Kill Switch、解决 Difference 或打开 Live Write。

Windows 入口：

```powershell
.\scripts\run-controlled-operation.ps1 -TaskType health_scan
.\scripts\run-controlled-operation.ps1 -TaskType backup -BackupLabel nightly
.\scripts\run-controlled-operation.ps1 -TaskType eod -EodPayloadPath .\eod-request.json
```

脚本从受控主机环境读取 Platform Bearer Token，不输出 Token。

## 5. 一致性备份

```http
POST /api/v1/ops/backups
GET  /api/v1/ops/backups
```

备份对象：

- Platform SQLite Database。
- Runtime Journal SQLite Database。
- 用户头像安全归档 `avatars.zip`。
- Redacted `manifest.json`。

使用 SQLite Online Backup API，不直接复制活动数据库文件。Manifest 记录：

- backupId、createdAt、environment。
- logicalName、fileName、sourceFileName。
- SHA-256、sizeBytes、`PRAGMA integrity_check`。
- 关键 Table Count，包括用户、Session、重置凭证、基金、持仓和 NAV。
- 头像文件数与总字节数；不在 Manifest 暴露头像文件名。
- Safe Restore Defaults。

Backup Root 由配置指定。Label 只允许字母、数字、点、下划线和连字符。拒绝路径穿越和覆盖非空目录。

## 6. Restore Drill

```http
POST /api/v1/ops/restore-drills
GET  /api/v1/ops/restore-drills
```

恢复演练只能写入新的 Drill Directory：

1. 读取 Completed Backup Manifest。
2. 验证源 Backup SHA-256。
3. 使用 SQLite Online Backup 创建恢复副本。
4. 执行 `PRAGMA integrity_check`。
5. 核对关键 Table Count。
6. 安全解压头像归档，核对文件数和总字节数，并拒绝路径穿越、软链接、重复或异常文件。
7. 在恢复副本中强制 Global Kill Switch enabled。
8. 生成 `safe-startup.env`：Platform/Runtime Live Write false、allowlist 空、limit 为零。
9. 确认 Production Paths 未被修改。

恢复成功不等于可以将副本直接替换生产。任何正式切换仍需停机、双人审批、重新只读核对和 EOD。

## 7. 配置

```text
VG_RUNTIME_JOURNAL_PATH=../execution-runtime/data/runtime_journal.db
VG_AVATAR_DATA_DIRECTORY=./data/avatars
VG_OPERATIONS_BACKUP_ROOT=./data/backups
VG_OPERATIONS_RESTORE_ROOT=./data/restore-drills
VG_OPERATIONS_ALERT_DEFAULT_OWNER=operations
VG_OPERATIONS_EOD_OVERDUE_GRACE_MINUTES=0
```

Backup Root 与 Restore Root 不得指向活动数据目录。

## 8. 权限

- Production Status、Alert/Backup/Restore/Controlled Operation 历史：`audit:read`。
- Alert Scan、Alert Close、Backup、Restore、Controlled Operations：`operations:run`。
- Alert Acknowledge：`reconciliation:review`。
- 所有 Actor 来自认证 Principal。

## 9. 工程验收

- [x] Production Status 聚合关键生产状态。
- [x] Runtime/Venue Failure 显式呈现。
- [x] Alert fingerprint 去重、计数、重新打开、acknowledge、close 已实现。
- [x] Alert details 和 error 经过 Redactor。
- [x] 调度只允许 health_scan、backup、eod。
- [x] Controlled Operation 具备幂等与失败终结状态。
- [x] Platform/Runtime 使用 SQLite Online Backup。
- [x] 用户头像使用受限根目录归档，异常目录项 fail-closed。
- [x] Manifest 包含 checksum、size、integrity、用户域关键计数和头像统计。
- [x] Restore Drill 使用新目录并核对 checksum/count/integrity 与头像归档。
- [x] 恢复副本 Global Kill Switch enabled。
- [x] Safe Startup 覆盖文件关闭两层 Live Write。
- [x] 原生产路径不被修改。
- [x] Backend 金样本已加入。
- [x] Platform CI 严格 Gate 已扩展。
- [ ] 最终 Platform CI 全部通过并记录 Run ID。
- [ ] README、START-HERE、API Spec、Release Gate、Runbook、Changelog 最终同步。

## 10. 运营验收

- [ ] 受控主机确认活动 Platform DB、Runtime Journal 与头像目录路径。
- [ ] 设置独立 Backup/Restore Root。
- [ ] 手工执行一次健康扫描、Backup 和 Restore Drill。
- [ ] 核对 Manifest、Checksum、Integrity、用户域 Table Count 和头像统计。
- [ ] 确认恢复副本 Live Write 关闭且 Global Kill Switch 开启。
- [ ] 将 health_scan、backup、eod 脚本登记到 Windows Task Scheduler。
- [ ] 演练 Runtime 不可用、Venue 不可用、EOD overdue 与 Backup Failure 告警。
- [ ] 明确备份保留周期、异地副本和人工责任人。

## 11. 发布边界

5D 工程完成后仍需真实账户、小资金运营验收。没有连续清洁 EOD、有效 Backup/Restore Drill、双人 Session、Kill Switch 演练和受控主机配置时，不扩大资金、仓位、品种或自动化频率。
