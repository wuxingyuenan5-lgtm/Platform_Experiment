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

Platform Execution Runtime:

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
- Platform Execution Runtime on `8100` only when execution integration is required.

Default safety state remains Simulation, Fake Gateway and Platform/Runtime Live Write disabled.

## Check running ports

```powershell
Get-NetTCPConnection -LocalPort 4373,8000,8100 -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,State,OwningProcess
```

When the machine feels slow, first identify duplicate dev servers and heavy browser dashboards. Do not delete dependencies, virtual environments or runtime data as a performance shortcut.

## Workspace noise

Large generated or local directories are excluded from normal search through root `.ignore` and component `.gitignore` files:

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

## Platform 0.9.3 Phase 6 candidate operations

The Phase 6 candidate is a stacked verification branch. Its rollback point is the previous Accepted Head:

```text
766d406737c2efc21a1ce7d49d70ee4aa6f21f81
```

The candidate must remain Draft and must not be treated as an RC, Ready PR or merged release until the Phase 6 evidence ledger and owner decision are complete.

### Verification startup order

1. Start Platform Execution Runtime when execution integration is required.
2. Confirm Runtime `/health` before relying on Runtime-backed Platform API reads.
3. Start Platform API and confirm `/health`.
4. Start Platform Web and confirm `/index.html`.
5. Verify the Platform API and Runtime both report version `0.9.3`.
6. Keep Platform Live Write and Runtime Live Write disabled throughout Phase 6 verification.
7. Do not load Demo Seed data into the formal application database.

A Runtime or Provider failure must remain explicitly `unavailable`, `error`, `stale`, `partial` or `not configured` as applicable. It must not be converted to an empty collection, zero value, synthetic online state or apparent execution success.

### Result Unknown handling

When an execution result cannot be proven from persisted Runtime events and Venue facts:

1. preserve `result_unknown` as the authoritative state;
2. do not call `submit_order` again during recovery;
3. inspect the Runtime Journal, Venue Order and Venue Fill facts;
4. reconcile Platform Order and Trade Command state only from persisted evidence;
5. escalate contradictory terminal facts or missing Venue evidence for manual disposition;
6. keep Live Write disabled until the unknown result is resolved.

### Backup and restore verification

Use the existing controlled Backup and Restore Drill interfaces. Restore only into an isolated directory. Validate SHA-256, SQLite integrity and critical table counts, then start the restored Platform API in safe state. Preserve the Safe Startup contract defined in `docs/technical/PRODUCTION_OPERATIONS.md`, including disabled Platform and Runtime Live Write.

A restore drill is not a production cutover and must not modify active Platform or Runtime data paths.

### Candidate rollback

If a Phase 6 P0/P1 issue cannot be safely corrected within the bounded branch:

1. stop candidate services;
2. preserve candidate logs, databases, Runtime Journal and evidence artifacts;
3. checkout the previous Accepted Head shown above in a new clean directory;
4. restore the last verified backup only when data rollback is required and separately approved;
5. confirm the three health checks and safety defaults;
6. do not re-enable Live Write automatically;
7. record the failure and rollback evidence in the Phase 6 total receipt.
