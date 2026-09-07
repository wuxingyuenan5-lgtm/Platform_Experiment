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

## Safe local verification

The following focused checks run from the repository root, do not start long-running services or external connections and do not require credentials or Live Write. They use repository files, temporary paths and mocked or synthetic inputs; install each package's declared development dependencies first.

Documentation links and authority consistency:

```powershell
.\platform-api\.venv\Scripts\python.exe .\scripts\check-documentation-consistency.py
```

Financial AI API contracts, local secret-file isolation and permissions:

```powershell
$previousDatabasePath = $env:VG_DATABASE_PATH
$temporaryDatabasePath = Join-Path ([System.IO.Path]::GetTempPath()) ("vg-financial-ai-test-{0}.db" -f [guid]::NewGuid())
$temporaryWalPath = "$temporaryDatabasePath-wal"
$temporaryShmPath = "$temporaryDatabasePath-shm"
$testExitCode = 0
try {
  $env:VG_DATABASE_PATH = $temporaryDatabasePath
  Push-Location .\platform-api
  try {
    .\.venv\Scripts\python.exe -m pytest tests/test_financial_ai_routes.py -q
    $testExitCode = $LASTEXITCODE
  } finally {
    Pop-Location
  }
} finally {
  if ($null -eq $previousDatabasePath) {
    Remove-Item Env:VG_DATABASE_PATH -ErrorAction SilentlyContinue
  } else {
    $env:VG_DATABASE_PATH = $previousDatabasePath
  }
  if (Test-Path -LiteralPath $temporaryDatabasePath) { Remove-Item -LiteralPath $temporaryDatabasePath }
  if (Test-Path -LiteralPath $temporaryWalPath) { Remove-Item -LiteralPath $temporaryWalPath }
  if (Test-Path -LiteralPath $temporaryShmPath) { Remove-Item -LiteralPath $temporaryShmPath }
}
if ($testExitCode -ne 0) { throw "Financial AI tests failed with exit code $testExitCode" }
```

Hedge Board research orchestration, last-known-good behavior and local-data path isolation:

```powershell
Push-Location .\platform-api
.\.venv\Scripts\python.exe -m pytest tests/test_research_service.py tests/test_research_local_data.py -q
Pop-Location
```

Hedge Board frontend market-detail transformation:

```powershell
Push-Location .\platform-web
corepack pnpm test:hedge-board-market-detail
Pop-Location
```

These checks do not prove an upstream provider is reachable or current. Provider availability and browser-level review are separate validations and must not be inferred from an isolated pass.

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

Normal startup and deployment do not authorize Live Write. Instruction-bounded controlled-live validation, fail-closed two-leg handling, EOD reconciliation and forced reset are governed by [`LIVE_ACCEPTANCE_RUNBOOK.md`](LIVE_ACCEPTANCE_RUNBOOK.md).

## Result Unknown

When an external result cannot be proven:

1. preserve `result_unknown`;
2. do not submit the order again;
3. inspect the Runtime journal and venue order/fill evidence;
4. reconcile Platform state only from persisted facts;
5. escalate contradictory or absent evidence;
6. keep Live Write disabled until resolved.

## Hedge Board research data

The Hedge Board is read-only research functionality. A-share data is refreshed by the Platform API lifecycle worker and committed to the SQLite `research_a_share_*` snapshot/history tables. Scheduled production refreshes are eligible only on China-market weekdays after 15:05 Asia/Shanghai. A successful run is not repeated for the same local trade date; a partial/error run remains eligible at the configured cadence until a complete snapshot is available. An authorized manual refresh can be used for repair. The browser reads `/api/v1/research/a-share/*` only; it must not call Vibe Research, AKShare, Eastmoney or other upstream providers.

To pause the worker for an isolated test, set `VG_RESEARCH_REFRESH_ENABLED=false`. To adjust cadence, set `VG_RESEARCH_REFRESH_INTERVAL_SECONDS` (minimum effective interval is 60 seconds). A refresh run is guarded by a process mutex and records `running`, `ready`, `partial` or `error` status in `research_a_share_refresh_runs`. Failed modules never erase an existing meaningful snapshot.

An explicitly authorized operator can trigger one refresh with `POST /api/v1/research/a-share/refresh`; normal page loads use `GET /api/v1/research/a-share/dashboard` and remain read-only. `GET /api/v1/research/a-share/refresh-status` exposes the latest run state.

Historical bootstrap is a one-time operation, not a runtime dependency:
`platform-api\.venv\Scripts\python.exe scripts\backfill_a_share_history.py --vibe-root <reference-root>`.
The imported rows are tagged `vibe-research-historical-backfill`; subsequent updates come from Platform-owned adapters.

To explicitly seed or repair the eight dashboard index series, run
`platform-api\.venv\Scripts\python.exe scripts\collect_a_share_index_history.py` from `platform-api`. The collector uses direct public Tencent daily K-lines for the four broad benchmarks and Eastmoney index K-lines for the four theme indexes, then performs one all-or-nothing SQLite upsert. If any source does not return all eight series, it writes nothing and must be retried after source availability is restored.

To seed the tracked stock-pool history used by the 5-day, 20-day and YTD views, run
`platform-api\.venv\Scripts\python.exe scripts\backfill_a_share_stock_history.py` from `platform-api`. It reads the Platform-owned pool definition and writes only after every tracked symbol has a usable Tencent adjusted daily series.

When a source is delayed or unavailable, verify the dashboard status and the local refresh logs before intervention. Preserve the last meaningful observation as explicitly stale where the data contract permits it. External research links open at their original provider and are not part of the Platform service health boundary.

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
