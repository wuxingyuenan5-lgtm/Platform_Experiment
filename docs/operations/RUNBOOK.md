# Runbook

## Local health checks

Platform Web:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:4373/index.html"
```

Platform API:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/health"
```

Execution Runtime:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8100/health"
```

## Standard local startup

From the repository root on Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

Expected long-running services:

- Platform Web on `4373`;
- Platform API on `8000`;
- Execution Runtime on `8100` only when execution integration is required.

Default safety state remains Simulation, Fake Gateway and Platform/Runtime Live Write disabled.

## Check running ports

```powershell
Get-NetTCPConnection -LocalPort 4373,8000,8100 -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,State,OwningProcess
```

When the machine feels slow, first identify duplicate dev servers and heavy browser dashboards. Do not delete dependencies, virtual environments or runtime data as a performance shortcut.

## Workspace noise

Large generated or local directories are excluded from normal search through root`.ignore` and component `.gitignore` files:

- `platform-web/node_modules/`;
- `platform-web/dist/`;
- `execution-runtime/.venv/`;
- `platform-api/.venv/`;
- `outputs/`;
- local SQLite/runtime data directories.

Do not record workstation-specific absolute paths in shared documentation. External reference repositories must remain outside the project root and be located through the operator's local workspace configuration.

## Destructive operations

Do not perform destructive cleanup, database reset, production route changes or service shutdown as part of routine repository organization.

Before using reset or migration tools:

1. verify the target environment and data path;
2. confirm the latest backup and restore procedure;
3. keep Live Write disabled unless the dedicated acceptance procedure explicitly requires it;
4. preserve `projects/risk-control`, `deploy/`, `platform-web/.gitlab-ci.yml` and production API routes until external Legacy evidence is reviewed.

Authoritative cleanup policy: `WORKSPACE_HYGIENE.md`.
