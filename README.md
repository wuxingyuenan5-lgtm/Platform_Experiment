# 全球变量金融平台（Variable-Global）

全球变量金融平台（Variable-Global）服务于Research、Market Data、Strategy、Trading、Execution、Risk、Accounting、Reconciliation、User & Access、Member Portfolio和Operations。`Platform`是工程与架构层通用简称，不取代正式产品品牌。

The maintained services are Platform Web, Platform API and Platform Execution Runtime.

## Start locally

From Windows PowerShell at the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

Operational details, service addresses, stop procedures and troubleshooting belong to `docs/operations/RUNBOOK.md`.

## Read next

| Need | Authority |
|---|---|
| Current version, branch, phase and known limits | `docs/codex/current-state.md` |
| Documentation navigation | `docs/README.md` |
| AI and engineering execution rules | `AGENTS.md` |
| Smallest task context | `docs/codex/context-map.md` |
| Service and data-flow boundaries | `docs/architecture/SYSTEM_MAP.md` |
| Business-rule and data ownership | `docs/architecture/OWNERSHIP.md` |
| Domain contracts | `docs/contracts/README.md` |
| Database, migration, backup and recovery | `docs/database/README.md` |
