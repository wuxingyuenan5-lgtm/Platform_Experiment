# Runbook

## Platform data audit

### Hedge Board local data producer

The sibling `platform-data` checkout is a research-data producer for this
Platform, not an unrelated product or a trading backend. Its Windows task
`HedgeBoard-LocalData-Refresh` writes to `D:\自营数据库\hedge-board`, which
Platform API reads through `app/research_local_data.py` for the macro, commodity
and crypto providers. Do not disable this task merely because its code is in a
separate directory.

Repair its action using `platform-data/scripts/install_local_task.ps1` in
PowerShell 7. The installer preserves existing triggers, principal and settings,
pins the Python executable, and uses this repository's
`scripts/launch-platform-child.py --wait` through `pythonw.exe`; PowerShell is
created with `CREATE_NO_WINDOW`. The Platform checkout must remain available.
New tasks run at 00:15, 06:15, 12:15 and 18:15 under interactive user logon;
this does not guarantee collection while logged out or while the host is off.
Inspect `logs/refresh-*.log` and `logs/scheduled-refresh.{out,err}.log` under the
data root, together with the scheduled task result. A failed source command
returns failure even if later commands update other artifacts or the DuckDB
mirror; preserve quality failures rather than treating a fresh mirror as full
success.

### Persisted audit results

`/risk/data-audit` is the internal `risk.read` view; `GET /api/v1/risk/data-audit` reads persisted results only. Platform API lifespan runs a serial audit every 300 seconds without browser activity. `GET /health/monitors` includes `dataAudit`; a report older than 900 seconds is not considered current. The header indicator reports read failures even if the API cannot answer.

`app/data_audit.py` owns rules and the explicit table inventory. `data_audit_runs` retains 30 days of inspection evidence; `operational_alerts` category `data_audit` retains deduplicated incidents and recovery status. Only audit-owned results are pruned. New tables and history datasets without classified policies are warnings. Research fetch time, observed time, source status, field missingness, per-asset derived freshness, manifest file existence, account sync and management projections are distinct checks. Monthly/quarterly/weekly sources and on-demand strategy detail do not inherit a continuous-feed deadline. Runtime data is inspected through its owner read-only status endpoints, not through direct journal writes or venue actions.

CN session coverage comes from the independent Sina calendar, fetched with an eight-second timeout and TLS verification, cached in `data_audit_calendar` for seven days. Failed refresh retries at the next scan; stale or insufficient coverage is explicit. No Vibe project file or service is a runtime dependency. Completeness is checked from each dataset's first stored date, not an invented pre-inception history. Other markets do not yet have independent session-calendar completeness guarantees.

Every UTC day, physical SQLite and foreign-key checks each receive a two-second query budget. Timeout remains an unresolved coverage warning; it must not be relabeled healthy. Full offline validation and archive content hashing belong to the existing backup/restore verification, not repeated full scans on the trading database. Five-minute scans do not run upstream business refreshes, place orders, repair data, or change trading authorization. Standalone external delivery for whole-host outages is not configured by this feature; station-internal notifications require a running browser and reachable service. Use the existing watchdog and independent operational monitoring for process/host outages.

## Standard local startup

From the repository root on Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

Expected local endpoints:

- Platform Web: `http://127.0.0.1:4373/index.html`
- Platform API: `http://127.0.0.1:8000/health`
- Platform Execution Runtime: `http://127.0.0.1:8100/health` when execution integration is required

The local platform is supervised independently from the Codex or terminal shell. `Global Variable Platform Supervisor` is a Windows logon task that runs `scripts/dev-platform.ps1 -Action supervisor` under the interactive user and keeps one watchdog running. The watchdog alone recovers failed service health checks. `Global Variable Platform Supervisor Pulse` is an independent one-minute task that starts the registered supervisor task when it is absent. Live Write is read from both running backends when available and is never enabled from a saved flag. This is service lifecycle management, not the retired 72-hour notification sampling job.

Both scheduled actions enter through `pythonw.exe scripts/launch-platform-child.py --wait`, which creates the PowerShell worker with `CREATE_NO_WINDOW`, waits for it and propagates its exit code. Starting a console executable directly from an interactive scheduled task can open Windows Terminal on every pulse even while services remain healthy. `scripts/configure-platform-supervision.ps1` updates the two existing task actions to the exact repository script paths, preserving their triggers, principal and restart policy; it does not restart business services. Do not re-import obsolete XML actions from `.codex` that directly launch PowerShell. Scheduled output appends to `logs/scheduled-supervisor.*.log` and `logs/scheduled-pulse.*.log` under `.codex/dev-platform`.

The waiting launcher owns only its direct scheduled worker through a Windows Job Object with kill-on-close. Descendant watchdog/service launches break away and retain their independent lifecycle, so stopping the supervisor must end its worker without killing business services. Task stop completion is asynchronous: wait for the prior worker to exit before evaluating orphan status. Verify both the actual stop/pulse-recovery chain and visible console creation; task exit code alone is insufficient.

The 2026-09-19 outage review reproduced conflicting recovery owners, a watchdog parent-PID check invalid after detached launch, and a pulse script that failed when the supervisor was missing. The supervisor now checks the watchdog process signature, freshness and trading mode without relying on its transient launcher PID. A Windows task result of `0xC000013A` shows termination, but does not by itself prove a process crash; stopping or replacing the task during maintenance can produce it. The cause of earlier individual Caddy exits remains unproven without process-exit evidence.

Bybit read failures caused by a remote TCP reset are handled at the Runtime connection boundary: the affected account session is discarded and rebuilt before one bounded read retry. This protects account/history synchronization without retrying venue rejections or submitting duplicate writes.

Account health is per account. During this incident `account_mt5_short_term_a` separately returned `MT5 initialize failed` (`IPC initialize failed, Process create failed`) while `mt5-live-main`, `bybit-live-main`, and the Bybit monitoring account continued to answer. That is an MT5 terminal-process availability problem for the optional short-term monitoring account, not a Platform API/Web disconnect; it must remain visibly degraded until that terminal can be initialized.

### Reversible local web publication

The local Caddy template serves content-hashed `/assets/` files from `.codex/releases/web/shared/assets/` with a one-year immutable browser cache. Publication seeds this shared store once from retained timestamped releases, then adds each build's hashed assets before updating the release marker; conflicting content under an existing immutable filename fails publication. Keep these assets available across release switches: an already open page can request an older lazy chart chunk later, and serving assets only from the latest release causes 404 errors and failed chart modules. HTML, runtime brand configuration and other mutable files still come from the selected release with `no-cache`. Missing hashed assets return 404 rather than the SPA index. API responses retain their existing cache policy. Verify old and current chunk responses and the served headers after publication; never apply immutable caching to the SPA index or `_app.config.js`. Run `powershell -NoProfile -File scripts/test-static-web-assets.ps1` for the retention and immutable-content regression checks.

To build a validated, timestamped local release under `.codex/releases/web/`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish-local-web.ps1
```

The script requires a verified portable Caddy at `.codex/tools/caddy/caddy.exe`, validates the candidate `deploy/Caddyfile.windows` configuration, and only then updates the local release marker. It preserves the previous marker as `previous.json`. It does not enable trading, change accounts or databases, register a service, or stop an existing web process. Activate the prepared release with `scripts/dev-platform.ps1 -Action restart-web`; this restarts only Web and refreshes the watchdog, retaining the API/Runtime processes and existing verified trading mode. `restart-api` similarly replaces only Platform API for backend maintenance, subject to the live maintenance checks in the acceptance runbook. `restart-runtime` replaces only Execution Runtime, preserving API/Web and the verified trading mode; it remains subject to the same live maintenance checks.

The published Web serves copied build artifacts on `127.0.0.1:4373`; source edits have no effect until the next publication. API routes are proxied before SPA fallback; GET `/login` is the frontend login page. When a release marker exists but its files are invalid, startup fails explicitly instead of reverting to development mode. Without a release marker, the original Vite development path remains available. For source development alongside the published Web, run `corepack pnpm dev --port 5173` in `platform-web`.

Rollback: restore `.codex/releases/web/previous.json` over `current.json`, then run `restart-web`. To return from the first publication to Vite, move the single `current.json` to `current.disabled.json` before `restart-web`; keep the release files for recovery. No bulk deletion is needed.

Each managed service start writes separate UTC timestamped stdout/stderr files under `.codex/dev-platform/logs/`. A short-lived launcher passes file handles directly to the child, so logging continues after the launcher exits and cannot block on a parent-owned pipe. Python runs unbuffered so diagnostic output appears promptly. Restarting a service does not overwrite its previous logs. Retention cleanup is a separate operator action. Account/history read failures remain visible through monitor health and do not restart healthy API/Runtime processes.

Default state is Simulation/Fake Gateway with Platform and Runtime Live Write disabled.

When Live Write is already enabled, the local watchdog recovers repeated health failures only after identity checks. It reads the Runtime journal before interrupting API/Runtime: unresolved `processing` or `result_unknown` commands keep backend recovery blocked; an empty journal permits recovery because no in-flight write is present. A single probe or file/network exception is recorded as degraded and the watchdog continues its loop. Trading-mode change, missing/changed process identity, cooldown and hourly recovery limits still prevent unsafe recovery. `scripts/tests/test_platform_watchdog.py` exercises the mocked recovery branches, including Windows PowerShell 5.1 array behavior.

Account current observations and historical/financial jobs report separate health. A history error is investigated through `accountHistory` and the account financial sync fields, not by restarting a healthy observation loop. Host clock maintenance uses Windows Time; starting/configuring that service requires appropriate Windows privileges. Venue signing offset correction does not replace host clock synchronization.

For the approved host clock repair, run `powershell.exe -NoProfile -File .\scripts\enable-windows-time.ps1` from an Administrator PowerShell at the repository root. It enables the existing Windows Time service, resynchronizes using its already configured source and prints the resulting status. It does not change MT5 server timezone, trading mode or order state. An access denial or nonzero resync result is an incomplete repair, not successful synchronization.

## Safe local verification

For chart lifecycle regressions, run
`node --test scripts/test-echarts-lifecycle.cjs` from `platform-web`. The shared
ECharts hook keeps only the latest pending options while hidden, applies them
when the container gains size or its KeepAlive page reactivates, and prevents
late asynchronous results from recreating an unmounted chart. Hidden charts
must not recursively retry on a timer. These isolated lifecycle tests do not
replace actual browser navigation, resize and scrolling acceptance.

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

The Hedge Board is read-only research functionality. A-share data is refreshed by the Platform API lifecycle worker and committed to the SQLite `research_a_share_*` snapshot/history tables. Scheduled production refreshes are eligible only on dates present in the cached China exchange trading calendar after 15:05 Asia/Shanghai; missing calendar coverage defers the run. A successful run is not repeated for the same local trade date; a partial/error run remains eligible at the configured cadence until a complete snapshot is available. An authorized manual refresh can be used for repair. The browser reads `/api/v1/research/a-share/*` only; it must not call Vibe Research, AKShare, Eastmoney or other upstream providers.

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


## Strategy research capture and archive

From the selected checkout, use `scripts/start-strategy-research.ps1 -Action check` before activation. It uses configured runtimes, checks loaded SQLite/durability, actual gateway/fixed Worker mapping and both live-write settings; it does not change gates. The normal trading API keeps `VG_STRATEGY_RESEARCH_WORKER_ENABLED` and `VG_STRATEGY_RESEARCH_PROJECTION_ENABLED` off so high-frequency research writes cannot block account reads or order control. `-Action start` additionally requires all three standard ports to be unowned, verifies an online backup, initializes the existing migration owner and delegates process startup to `dev-platform.ps1`; it explicitly enables the research worker and projection for that isolated maintenance run. It refuses to retake another checkout's running services. No new service manager or scheduled task is installed. Existing managed account connections must not be cloned into a parallel collector.

Runtime activation is `VG_RUNTIME_RESEARCH_CAPTURE_ENABLED=true`; Platform is `VG_STRATEGY_RESEARCH_ENABLED=true`. Both default false. Configure the existing Bybit account owner via `VG_RUNTIME_RESEARCH_BYBIT_ACCOUNT_ID`; the fixed MT5 primary account and instrument mapping remain existing configuration. Capture is independent of the browser. The public Runtime batch contract is local read-only and must retain the existing Runtime network exposure policy. Research startup does not grant credentials, external deployment or trading authority.

Before an authorized owner cutover, confirm free disk, expected directories, current branch/dirty files, database path/migration, actual Bybit/MT5 owners, TLS/proxy policy and Windows/native clocks. Record `w32tm /query /status`; do not silently enable or repair OS time services. Verify native MT5 source timestamps separately from local UTC, preserving raw values and any explicitly verified conversion version. Until verified, cross-clock samples remain excluded.

Monitor Runtime `/v1/market-data/status` and Platform `/api/v1/research/strategies/data-status` for source gaps, queue/drop count, spool/free space, last received/durable/published watermarks and capture errors. Data audit warns when spool usage reaches 80% of its configured budget and errors at the budget; raising the budget requires checking free disk and does not establish archival retention. The daily capacity estimate is extrapolated only from the measured archive window; it is not a measured full-day rate. Calendar coverage, end-to-end latency and backup status must not be inferred from a listening port. A 60-second REST scan, replay backlog and a provisional quote are separately labeled.

For local dashboard artifacts marked `daily_business_day`, the audit gives retrieval age a 72-hour weekend window and separately warns when the source observation date predates the previous weekday. A producer's explicit stale/partial state remains visible. This does not certify exchange holidays or manufacture a newer observation.

`platform-api/scripts/benchmark_strategy_research.py` runs an isolated synthetic spool-to-Parquet/SQLite pressure and concurrent-read probe. Synthetic results are not real Bybit 20ms latency, MT5 coverage, live fill quality or 24-hour acceptance. Real validation still requires native-stream continuity, MT5 same-ms batches, reconnect/reboot gaps, backlog recovery, clock checks and a full day of CPU/RSS/disk/latency evidence. Capacity pause, corrupt-tail recovery, orphan replay, manifest checksum and backup restore each need explicit evidence. Never delete old spool/shards to make a failed capacity test pass; archival retention is an operator action within the file-deletion rules.

The trading API keeps the research worker and SQLite serving projection disabled. If the projection has grown the business database, stop the managed services, create and verify an online backup with `platform-api/scripts/strategy_research_ops.py backup` and `verify-backup`, then run `platform-api/scripts/compact_research_projection.py --backup <verified-directory>`. The command checks integrity, recreates the empty projection tables, runs `VACUUM`, and reports preserved business-table counts; it never removes the Parquet catalog or backup. Start the managed services again with `scripts/dev-platform.ps1 -Action start -EnableLiveWrite:$false` and verify all three health endpoints, Runtime unresolved-command counts, and `health/monitors` before returning the platform to use. Rebuilding the projection is a separate authorized maintenance run and must not be enabled in the normal trading API.

For long-running operation, `platform-api/scripts/compact_observational_history.py --database-backup <verified-sqlite>` applies retention to market-spread and account-observation snapshots: full recent data, hourly for 14 days, and daily for 400 days. It requires a stopped service window, checks the database-only backup and SQLite integrity before changing data, preserves orders/fills/financial facts/research catalog rows, and runs `VACUUM`. A run that keeps row counts unchanged is expected when all current observations are inside the retention windows; it still establishes the policy for future growth.

The cross-spread snapshot endpoint and execution preflights do not write market history or acquire its sampling lock. Only the background market monitor requests persistence, at most once per configured `VG_CROSS_SPREAD_MARKET_SNAPSHOT_INTERVAL_SECONDS` for each strategy instance. Migration 37 supplies the covering created-time index for that sampling guard; do not substitute source observation time for ingestion time. A stale Runtime fallback remains readable but is not persisted as a new observation. Do not increase browser polling frequency as a way to collect history; high-frequency research belongs to the Runtime Parquet/archive path. `fetchLatencyMs` measures each Runtime leg's quote-plus-position read, not browser round-trip time or source quote age; an MT5 closed-session tick retains its original time and cannot authorize execution.

MT5 worker window maintenance filters process names before reading and resolving executable paths, then hides only windows belonging to the exact configured Terminal path. Do not resolve every host executable on each IPC loop: that synchronous maintenance competes with quote/account reads and consumes CPU even while idle. Process exit/access-denied races are skipped; matching another Terminal by name alone is forbidden. SDK identity verification, periodic window hiding and trading permissions remain unchanged.

Backup verification compares every sealed raw/derived shard and experiment-result artifact against the backed-up SQLite catalog before checking file checksums. A missing experiment entry in the manifest fails verification even when all listed files are intact. Native Bybit source health advances only for accepted raw callbacks; MT5 empty intervals are reported as `empty_range`, not as new tick coverage.

If a candle serving projection has internal holes but the sealed Parquet catalog
contains the missing candles, restore from that catalog before requesting another
venue backfill. `platform-api/scripts/restore_candle_projection.py` takes explicit
timezone-aware candle `--start/--end` and archive receipt `--received-start/--received-end`
bounds. Run from `platform-api` so the configured archive path resolves correctly.
It verifies each selected shard checksum, accepts only unflagged one-minute BTC/XAUT
linear trade candles, and inserts absent natural keys only. Existing observations,
archive files and collector/projection cursors remain untouched; repeat execution is
idempotent. Keep the emitted counts with the local maintenance evidence. The normal
cumulative-movement worker detects recoverable missing days and rebuilds its derived
series after the shared projection is restored; verify its API and actual chart too.
This repair does not resolve Runtime spool capacity pauses or establish retention.

Historical catch-up is owned by the same Runtime lifecycle. `price-<category>-<symbol>-<type>-1m.json` in the existing spool stores the configured retention-window one-minute scan cursor (365 days by default via `VG_RUNTIME_RESEARCH_PRICE_HISTORY_DAYS`), rows returned and empty windows; five core streams take turns with at least 500ms between requests and five seconds between catch-up rounds. When the configured floor moves backwards, the cursor status becomes `backfilling` and requests the missing older windows before returning to the live tail. Once caught up, the loop checks for newly closed bars every minute. Funding and public borrowing use the separate five-minute rates loop. `mt5-history-cursor.json` resumes the initial three-day fixed-account scan; it does not change account login or native clock. Cursor publication follows spool fsync. Preserve old resolution cursors/raw shards; do not rename them to claim finer coverage. `history:*` source status distinguishes backfilling, caught-up and MT5 range-scanned; none establishes completeness across missing broker sessions. MT5 raw batches retain every Tick while the historical overview samples by minute. The browser history refresh reads only the local archive and cannot restart catch-up. Full historical hashing state must not grow with the warehouse: the derivation checkpoint keeps only a bounded recent-candle overlap, with raw revisions retained in immutable shards.

For a feature already integrated into the current local checkout, preserve its existing supervisor, pulse, account owner and database paths. After a verified online backup and confirming both write gates are disabled with no unresolved Runtime commands, use the existing `dev-platform.ps1 -Action restart` to load Runtime/API/Web changes; an API-only change uses `restart-api`. A different checkout or supervisor retarget is not required for ordinary research-page updates. MT5 interval queries hold their cursor until a fresh conservative UTC reference is available, preventing a fast host clock from advancing into future ranges. This query reference does not establish the broker Tick clock.
