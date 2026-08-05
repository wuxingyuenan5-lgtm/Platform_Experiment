# Runbook

## Standard local startup

From the repository root on Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

Expected local endpoints:

- Platform Web: `http://127.0.0.1:4373/index.html`
- Platform API: `http://127.0.0.1:8000/health`
- Platform Execution Runtime: `http://127.0.0.1:8100/health` when execution integration is required

Default state is Simulation/Fake Gateway with Platform and Runtime Live Write disabled.

## Health checks

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:4373/index.html"
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/health"
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8100/health"
```

```powershell
Get-NetTCPConnection -LocalPort 4373,8000,8100 -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,State,OwningProcess
```

## Controlled live acceptance

Normal startup and deployment do not authorize Live Write. Minimum-size live validation, fail-closed two-leg handling, EOD reconciliation and forced reset are governed by [`LIVE_ACCEPTANCE_RUNBOOK.md`](LIVE_ACCEPTANCE_RUNBOOK.md).

## Result Unknown

When an external result cannot be proven:

1. preserve `result_unknown`;
2. do not submit the order again;
3. inspect the Runtime journal and venue order/fill evidence;
4. reconcile Platform state only from persisted facts;
5. escalate contradictory or absent evidence;
6. keep Live Write disabled until resolved.

## Backup and recovery

Use the controlled backup/restore interfaces. Restore only into an isolated path, validate checksums and SQLite integrity, compare critical table counts, and start the restored API in safe state. A restore drill is not a production cutover.

## External deployment configuration

Repository deployment configuration uses required neutral variables and provides no server-specific defaults:

```text
PLATFORM_WEB_DEPLOY_DIR
PLATFORM_WEB_PUBLIC_URL
PLATFORM_API_DEPLOY_DIR
PLATFORM_API_PUBLIC_URL
```

Configure them in the external CI/CD or operator environment. Missing variables must fail deployment clearly. Repository files do not prove that any server, domain, proxy or external variable is configured.

## Safety

Do not reset databases, delete runtime evidence, enable Live Write, alter production routes or restart external services as routine repository maintenance. Generated dependencies and local data are ignored; do not remove them as a performance shortcut.
