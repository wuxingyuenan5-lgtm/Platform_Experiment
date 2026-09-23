# Production Operations

状态：`active operational reference`

受控实盘验收、失败处置、EOD与强制复位见 [LIVE_ACCEPTANCE_RUNBOOK.md](LIVE_ACCEPTANCE_RUNBOOK.md)。

## 1. 权威边界

```text
Platform API
├─ Production Status
├─ Operational Alerts
├─ Controlled Operation Journal
├─ Backup Metadata
└─ Restore Drill Metadata

Platform Execution Runtime
├─ Runtime Status
├─ Venue Readiness
├─ Credential Inspection
└─ Runtime Journal SQLite
```

Platform 只通过 Runtime 的只读状态接口观察外部执行环境。Production Operations 不提交 TradeCommand、不修改外部持仓、不批准 LiveTradingSession，也不解决 Reconciliation Difference。

## 2. Status Semantics

`GET /api/v1/ops/production-status` 返回整体：

- `ok`
- `warning`
- `critical`

Critical 至少包括：

- Runtime 或 Venue unavailable。
- `result_unknown` Order。
- Residual/Dispositon/Escalated Execution Risk。
- Open Difference。
- EOD failed、partial 或 overdue。
- Backup/Restore failed。

Warning 至少包括：

- Manual Intervention Batch。
- Accepted Difference。
- Credential Reference 未完整解析。

Query Failure 与空集合不同，不得以零值掩盖错误。

本地 Platform→Runtime 的 `VG_RUNTIME_TIMEOUT_SECONDS` 使用现有默认值 `20`，示例配置与实际维护配置保持一致。完整 Bybit 账户快照包含分市场分页订单、成交、资产分类和经济事件，本机实取曾需约 7 秒；旧 5 秒配置会在 Runtime 正常完成读取前令 Platform 报超时。该配置只规定单次 HTTP 等待上限，不增加交易重试；失败仍保留上次成功快照并标记过期。

### Local Prometheus metrics

For the approved local stability observation, `scripts/collect-strategy-stability.py` takes one sample of existing loopback health/metrics, read-only SQLite status counts and native Windows process resources. It appends JSONL evidence in the existing operator evidence directory; scheduling belongs to the current Codex task automation. It is not another daemon, trading-state database, venue client or alert-disposition owner. Hourly samples can show drift, restarts and observed failures but cannot prove absence of short failures between samples; use existing service logs alongside them, and retain version changes and missing intervals as acceptance limitations.

`prometheus-client==0.26.0` instruments existing processes. Platform serves `GET /api/v1/ops/metrics` under the existing authenticated `audit:read` permission. Runtime serves `GET /metrics` only to loopback clients (`127.0.0.1`/`::1`). These are exports, not an installed Prometheus server, Grafana deployment or new authentication system; remote collection and service installation require a separate deployment decision.

| Metric family | Evidence and interpretation |
|---|---|
| `vg_platform_runtime_request_seconds` | Histogram of individual Platform→Runtime HTTP attempts, by GET/POST and outcome. Timeout, transport failure, HTTP class and rate limit remain distinct. |
| `vg_runtime_venue_request_seconds` | Bybit HTTP or MT5 Worker-call duration by venue, bounded operation and outcome. Bybit HTTP 429 and native rate-limit codes are classified separately; this is not order-to-fill latency. |
| `vg_platform_pending_instructions`, `vg_platform_pending_batches`, `vg_platform_pending_risks` | Counts from existing Platform rows by strategy/state. Their `*_oldest_seconds` report age since work creation, or since the recorded risk update; they do not invent when a risk first began. |
| `vg_runtime_pending_commands` and `*_oldest_seconds` | Persisted `processing`/`result_unknown` counts and age since claim, reconstructed from the journal after process restart. |
| `vg_platform_account_sync`, `*_oldest_success_seconds`, `vg_platform_account_snapshot_oldest_seconds` | Persisted sync result, last successful retrieval age and source snapshot age by venue/state. Missing time evidence remains NaN; `vg_platform_account_evidence_missing` counts absent evidence separately. |
| `vg_runtime_mt5_worker_starts_total`, `vg_runtime_mt5_worker_ready` | Starts and current process liveness after the fixed-account identity handshake. Logical account labels are limited to configured Workers; zero or absent does not authorize a restart or order replay. |

Scraping uses SQLite `mode=ro`, never invokes schema initialization, starts a Worker, queries a venue, reconciles a command or writes an alert. Unavailable stores export `vg_platform_metrics_snapshot_available=0` or `vg_runtime_metrics_journal_available=0`, with their business counts omitted. An uninitialized optional risk store exports `vg_platform_metrics_risk_store_available=0`. Empty state groups are absent; dashboards must first check store availability before treating missing counts as zero. Invalid or missing timestamps cannot be displayed as fresh.

No financial amounts, PnL, external account numbers, order/client IDs, credentials, arbitrary URLs or raw errors become metric labels. Detailed unresolved-command warnings carry Platform order/command correlation IDs and an error class; original execution evidence stays in its existing journal. Request counters and process metrics reset with the process; persistent work counts come from the stores. Thresholds, alerts and unattended operational actions are not inferred from metric availability. Existing operational alerts continue to own acknowledgment and disposition; Prometheus is not another ledger or trading state authority.

The installed client uses the standard [Prometheus metric types](https://prometheus.github.io/client_python/instrumenting/). Single-process in-memory metrics match the current local topology; future multi-worker/remote deployments must explicitly configure aggregation and collection rather than assuming the local counters cover every process.

## 3. Alert Identity

Fingerprint：

```text
SHA-256(category | subjectType | subjectId)
```

同一 Fingerprint：

- 首次出现：创建 open Alert。
- 后续扫描：更新 lastSeenAt、details、severity，occurrenceCount +1。
- acknowledged：保持 acknowledged 并继续累计。
- closed 后再次出现：重新 open，清空旧关闭字段。

Acknowledge 表示责任已确认；Close 表示当前告警已经完成处置。Close 不修改交易事实、外部状态或 Difference。

## 4. Alert Data Safety

写入前对 details、message 和 error 运行统一 Redactor。禁止写入：

- Authorization Header。
- Bearer Token。
- API Key、Secret、Password、Passphrase。
- 私钥块。
- URL UserInfo Password。
- Credential Value。

Alert 可以保留 Account ID、Strategy ID、Order ID、Difference ID、Report ID、状态、计数和时间。

## 5. Controlled Operations

任务白名单固定为：

| taskType | 行为 |
|---|---|
| `health_scan` | 采集 Production Status 并更新 Alert |
| `backup` | 调用一致性 Backup |
| `eod` | 调用既有 EOD Reconciliation Orchestrator |

拒绝其他 Task Type。每次运行使用幂等键和 Payload Hash。相同键不同载荷返回 409。

`scheduledFor` 必须含时区，并且调用时间只能接近计划时间；Scheduler 不能提前创建未来运行记录。

HTTP Validation/Authorization Failure 若发生在运行记录创建后，必须把状态终结为 failed，不能永久停留在 running。

## 6. SQLite Online Backup

活动 SQLite 文件不能通过普通文件复制作为权威备份。流程：

1. 打开 Source Connection。
2. 打开 Destination Connection。
3. 调用 `source.backup(destination)`。
4. Commit 并关闭。
5. 运行 Destination `PRAGMA integrity_check`。
6. 计算 SHA-256 和 Size。
7. 读取关键 Table Count。
8. 生成 Redacted Manifest。

备份记录先写 `processing`，成功后 `completed`，失败后 `failed`。失败不能返回伪造的 Completed Response。

## 7. Manifest

Manifest 不保存绝对 Source Path，只保存 Source File Name 和 Logical Name。

```json
{
  "schemaVersion": 1,
  "backupId": "...",
  "files": [
    {
      "logicalName": "platform_database",
      "fileName": "platform.db",
      "sourceFileName": "platform.db",
      "sha256": "...",
      "sizeBytes": 0,
      "integrity": "ok",
      "tableCounts": {}
    }
  ],
  "safeRestoreDefaults": {
    "platformLiveTradingEnabled": false,
    "runtimeLiveWriteEnabled": false,
    "globalKillSwitchEnabled": true
  }
}
```

关键计数包括：Order、TradeCommand、FinancialFact、Difference、EOD、Live Session、Runtime Command 和 Runtime Event。

## 8. Root and Path Rules

- Backup Root 与 Restore Root 来自配置。
- Child Directory 名称由 UTC Time、Validated Label 和 UUID 派生。
- Label 不接受 `/`、`\`、`..` 或空值。
- Resolve 后 Target Parent 必须等于 Configured Root。
- 非空目标目录拒绝覆盖。
- Restore Drill 目标不得等于活动 Platform DB、Runtime Journal 或其文件路径。

## 9. Restore Drill

Restore Drill 不执行 Production Cutover。流程：

1. 选择 Completed Backup。
2. 读取 Manifest。
3. 验证 Backup Artifact SHA-256。
4. Online Backup 到新的 Restore Directory。
5. 验证 Integrity 与 Table Count。
6. 在恢复 Platform 副本中启用 Global Kill Switch。
7. 生成 `safe-startup.env`。
8. 记录 `productionPathsModified=false`。

Safe Startup：

```text
VG_LIVE_TRADING_ENABLED=false
VG_RUNTIME_LIVE_WRITE_ENABLED=false
VG_RUNTIME_LIVE_ACCOUNT_ALLOWLIST=
VG_RUNTIME_LIVE_STRATEGY_ALLOWLIST=
VG_RUNTIME_LIVE_SYMBOL_ALLOWLIST=
VG_RUNTIME_LIVE_MAX_ORDER_NOTIONAL=0
VG_RUNTIME_LIVE_MAX_DAILY_NOTIONAL=0
```

任何正式切换必须另行停机、双人批准、数据校验、只读 Preflight 和最小仓位复验。

## 10. RBAC

- Production Status 与历史记录：audit-capable Role。
- Alert Scan、Close、Backup、Restore、Controlled Operation：operations。
- Alert Acknowledge：risk officer。
- 所有 Actor 从认证 Principal 获取。
- Scheduler 使用独立 Operations Credential，不使用 Trader Credential。

## 11. Failure Semantics

- Runtime/Venue Query Error：Status 明确 unavailable，生成 Alert。
- Backup Source Missing：Backup failed，生成 Alert。
- Checksum/Integrity/Count Mismatch：Restore failed，不生成 Safe Success。
- Unsupported Task：422，不创建外部副作用。
- Duplicate Idempotency + Same Payload：返回已有结果。
- Duplicate Idempotency + Different Payload：409。
- Alert Scan Failure：不关闭既有 Alert。

## 12. Current Limitations

- 不自动发送短信、电话、邮件或 IM；当前 Alert 为平台内可审计事件。
- 不自动注册 Windows Task Scheduler。
- 不自动将 Backup 复制到异地介质。
- 不自动执行 Production Cutover。
- 不自动开启 Live Write 或修改额度。
- 后续可增加通知 Adapter 和离线介质复制，但不得改变当前安全默认值。
