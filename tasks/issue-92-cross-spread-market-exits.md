# Task: Cross-Spread Market Close and Spread-Triggered Exits

Issue: #92
Status: active
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

## Expected changed files

- `platform-backend/app/execution_schemas.py`
- `platform-backend/app/runtime_contracts.py`
- `platform-backend/app/trade_commands.py`
- `platform-backend/app/trade_command_execution.py`
- `platform-backend/app/execution_batches.py`
- `platform-backend/app/cross_spread.py`
- `platform-backend/app/cross_spread_exit_schemas.py`
- `platform-backend/app/cross_spread_exit_policy.py`
- `platform-backend/app/cross_spread_exit_repository.py`
- `platform-backend/app/cross_spread_exit_service.py`
- `platform-backend/app/schema_migrations.py`
- `platform-backend/app/config.py`
- `platform-backend/app/application.py`
- `platform-backend/app/schemas.py`
- `execution-runtime/app/models.py`
- `execution-runtime/app/runtime_contracts.py`
- `execution-runtime/app/bybit_live_adapter.py`
- `execution-runtime/app/mt5_live_adapter.py`
- `docs/contracts/runtime-v1.json`
- `docs/architecture/OWNERSHIP.md`
- `docs/codex/current-state.md`
- focused Backend, Runtime and frontend tests
- existing cross-spread frontend/API files only as needed for minimal market wiring
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

- [ ] CLOSE commands persist and transmit reduce-only intent.
- [ ] Bybit close uses reduce-only and correct position index.
- [ ] MT5 close uses the intended Position Ticket.
- [ ] Ambiguous/wrong-side/oversized close requests are rejected.
- [ ] Hedged OPEN batches create active exit plans from actual fills.
- [ ] LONG_SPREAD TP/SL evaluates `shortSpread` with correct inequalities.
- [ ] SHORT_SPREAD TP/SL evaluates `longSpread` with correct inequalities.
- [ ] Threshold claim and close submission are idempotent.
- [ ] Result unknown never auto-retries.
- [ ] Market UI uses real plans and market close actions.
- [ ] Limit UI remains visible but cannot misroute into market execution.
- [ ] Existing spread formulas and safe defaults remain unchanged.

## Progress

- Done: Issue #92, issue-numbered branch and bounded task packet.
- Current: command-contract and venue-close implementation.
- Next: exit-plan persistence, trigger service, frontend wiring and CI.
- Blocked by: none.

## Completion

- PR:
- Merge commit:
- Application behavior changed:
- Business behavior changed:
- Tests/CI:
- Follow-up: real limit entry/exit and private Bybit WebSocket remain separate scopes.
