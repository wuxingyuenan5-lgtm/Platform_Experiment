# Task: Cross-Spread Market Close and Spread-Triggered Exits

Issue: #92
Status: completed
Branch: `feature/issue-92-cross-spread-market-exits`
Base commit: `d5375de356fe411fa4922b68189fc17fbf6f5fcd`

## Objective

Complete the market-only cross-spread lifecycle: true reduce-only market close on both venues, persistent exit plans for hedged opens, and server-side take-profit/stop-loss thresholds that submit one idempotent market close using the executable close spread.

## Confirmed product decisions

- Preserve the existing frontend design for both market and limit choices.
- Wire only market open, market close and market TP/SL in this issue.
- Limit selections remain visible but must not silently fall through to market execution.
- Keep the existing nominal spread formulas unchanged.
- LONG_SPREAD exits observe `shortSpread`; SHORT_SPREAD exits observe `longSpread`.
- Keep Platform and Runtime Live Write disabled by default.

## Changed files

### Platform Backend

- `platform-backend/app/config.py`
- `platform-backend/app/cross_spread.py`
- `platform-backend/app/cross_spread_exit_policy.py`
- `platform-backend/app/cross_spread_exit_repository.py`
- `platform-backend/app/cross_spread_exit_routes.py`
- `platform-backend/app/cross_spread_exit_schemas.py`
- `platform-backend/app/cross_spread_exit_service.py`
- `platform-backend/app/main.py`
- `platform-backend/app/order_execution_intents.py`
- `platform-backend/app/runtime_contracts.py`
- `platform-backend/app/schema_migrations.py`
- `platform-backend/app/trade_command_execution.py`
- `platform-backend/app/trade_commands.py`
- focused Backend tests

### Execution Runtime

- `execution-runtime/app/bybit_fill_confirming_adapter.py`
- `execution-runtime/app/bybit_mt5_gateway.py`
- `execution-runtime/app/models.py`
- `execution-runtime/app/mt5_position_closing_adapter.py`
- `execution-runtime/app/runtime_contracts.py`
- focused Runtime tests

### Frontend

- `admin-risk/src/api/platform/crossSpreadLifecycle.ts`
- `admin-risk/src/views/strategy/spread-carry/components/CrossSpreadMarketLifecyclePanel.vue`
- `admin-risk/src/views/strategy/spread-carry/components/SpreadExecutionWorkspace.vue`
- `admin-risk/tsconfig.strategy.json`

### Governance and documentation

- `docs/contracts/runtime-v1.json`
- `docs/architecture/OWNERSHIP.md`
- `docs/database/README.md`
- `docs/codex/current-state.md`
- `scripts/check-repository-structure.py`
- this task packet

## Implementation decisions

- Add optional close-target fields to the V1 order command while preserving ordinary open-command compatibility.
- Persist reduce-only and close-target identity through Batch → TradeCommand → Order submission.
- Bybit close resolves and validates the current live side and position index before submission.
- MT5 close requires exactly one matching live Position Ticket for the requested symbol/side/quantity; ambiguity blocks execution.
- Persist a dedicated cross-spread exit plan only after an OPEN batch reaches `hedged`.
- Threshold evaluation is a pure policy; SQL ownership is isolated in a repository; orchestration and market-close submission are isolated in a service.
- The automatic monitor is disabled by default and must atomically claim a plan before submitting a close.
- Unknown results and manual-intervention batches are never retried automatically.
- Keep the 2600-line legacy visual component unchanged. Mount a bounded real market-lifecycle panel in the same workspace and make the legacy execution card read-only so its retained limit design cannot misroute to the market endpoint.

## Required verification

```text
python scripts/check-workstream.py
python scripts/scan-secrets.py
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
```

Final delivery also requires:

- Runtime lint, progressive type gate and classified tests.
- Backend lint, progressive type gate and classified tests.
- Frontend changed-file lint, type check and production build.
- Secret Scan.

## Stop conditions

- Stop if implementation requires enabling either Live Write default.
- Stop if a CLOSE command can increase or reverse either venue exposure.
- Stop if an MT5 close target is ambiguous.
- Stop if a threshold trigger could submit more than one business close.
- Stop if an unresolved result would require blind retry.
- Stop if implementation expands into real limit execution.
- Stop if an unrelated architecture boundary must change.

## Acceptance criteria

- [x] CLOSE commands persist and transmit reduce-only intent.
- [x] Bybit close uses reduce-only and correct position index.
- [x] MT5 close uses the intended Position Ticket.
- [x] Ambiguous/wrong-side/oversized close requests are rejected.
- [x] Hedged OPEN batches create active exit plans from actual fills.
- [x] LONG_SPREAD TP/SL evaluates `shortSpread` with correct inequalities.
- [x] SHORT_SPREAD TP/SL evaluates `longSpread` with correct inequalities.
- [x] Threshold claim and close submission are idempotent.
- [x] Result unknown never auto-retries.
- [x] Market UI uses real plans and market close actions.
- [x] Limit UI remains visible but cannot misroute into market execution.
- [x] Existing spread formulas and safe defaults remain unchanged.

## Progress

- Done: Issue, branch, task packet, venue-safe close semantics, exit-plan persistence, TP/SL policy and monitor, lifecycle APIs, real market UI panel, focused tests, documentation synchronization and PR #93.
- Current: complete and ready for squash merge.
- Next: controlled Demo/real-environment acceptance under Issue #39; real limit execution and private Bybit WebSocket remain separately bounded scopes.
- Blocked by: none.

## Completion

- PR: #93
- Merge commit: pending squash merge
- Application behavior changed: market opens create persistent exit plans; market closes are reduce-only and ticket-bound; TP/SL can trigger one idempotent market close when the controlled monitor is enabled.
- Business behavior changed: LONG and SHORT exits monitor the executable opposite-side spread rather than the opening-side spread.
- Tests/CI: Platform CI #1319 and Secret Scan #700 passed on the final code head before documentation completion.
- Follow-up: controlled operational acceptance, real limit entry/exit and private Bybit WebSocket remain separate scopes.
