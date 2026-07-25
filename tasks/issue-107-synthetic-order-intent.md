# Task: Synthetic cross-spread order intent

Issue: #107
Status: done
Branch: `feature/issue-107-synthetic-order-intent`
Base commit: `1947728b4b7eb8590e21720690fd294b54c7a47b`

## Objective

Introduce one authoritative synthetic-order intent model for all four cross-spread business actions while preserving the completed Market lifecycle exactly.

## Non-goals

- No real Limit/FOK/PostOnly/IOC submission.
- No private WebSocket.
- No database migration.
- No fee, spread, quantity, Live Write, monitor or acceptance-limit change.

## Allowed scope

- Cross-spread lifecycle schemas, service and route adapters.
- A focused shared intent/policy module.
- Cross-spread lifecycle frontend API types needed to expose the normalized intent.
- Direct Backend tests.
- API, ownership, current-state and synthetic-execution documentation.

## Actual changed files

- `platform-backend/app/cross_spread_order_intent.py` (new)
- `platform-backend/app/cross_spread_synthetic_service.py` (new)
- `platform-backend/app/cross_spread_exit_schemas.py`
- `platform-backend/app/cross_spread_exit_routes.py`
- `platform-backend/tests/test_cross_spread_synthetic_intent.py` (new)
- `admin-risk/src/api/platform/crossSpreadLifecycle.ts`
- `docs/technical/CROSS_SPREAD_SYNTHETIC_EXECUTION.md` (new)
- `docs/technical/API_SPEC.md`
- `docs/architecture/OWNERSHIP.md`
- `docs/codex/current-state.md`
- this task packet

## Protected semantics

- Existing Market execution order and result handling do not change.
- Bybit remains first leg; MT5 quantity remains derived from confirmed Bybit fill.
- Existing close reduce-only/ticket binding, compensation, reconciliation and manual-intervention behavior remain unchanged.
- TP/SL remains executable-spread triggered and Market-executed in this batch.
- Limit requests fail closed and never execute Market.
- Live Write, exit monitor and temporary one-ounce/single-lifecycle controls remain unchanged.

## Required verification

- Backend Ruff, Pyright and classified tests.
- Existing market lifecycle and acceptance rollback tests.
- Focused intent mapping and trigger-reason tests.
- Frontend lint, no-new-debt, type check and production build.
- Repository Safety and Secret Scan.

## Stop conditions

- Stop if implementing the model requires changing Venue order behavior.
- Stop if a database migration becomes necessary; split it into a dedicated Issue.
- Stop if Limit execution would be partially implemented or could fall through to Market.

## Acceptance criteria

- [x] Four actions map deterministically to existing Market commands and leg directions.
- [x] Open/manual close/TP/SL close use the same normalized command model.
- [x] Existing public Market endpoints remain compatible.
- [x] Trigger reason is explicit for manual and automatic closes.
- [x] Limit remains rejected with no side effect.
- [x] Documentation records the five-batch roadmap and Batch 1 boundary.
- [x] Required CI and Secret Scan pass.

## Risk and rollback

Risk: medium

- Failure modes: action mapping changes a Market direction; trigger metadata leaks into execution behavior; compatibility payload changes.
- Detection: mapping unit tests plus full existing lifecycle tests.
- Rollback: revert the squash merge; no migration or external state change is introduced.

## Progress

- Done: authoritative intent model, public synthetic lifecycle adapter, response metadata, focused tests, frontend API types and documentation completed.
- Current: final metadata-head verification before squash merge.
- Next: Batch 2 will implement FOK spread-limit execution in a separate Issue and PR.
- Blocked by: none.

## Completion

- PR: #108
- Merge commit: GitHub PR/main history is authoritative; no post-merge metadata PR will be created.
- Behavior changed: normalized internal intent and additive response metadata only.
- Behavior intentionally unchanged: all Market/Venue/risk behavior, safety defaults and operational gates.
- Tests/CI: Platform CI #1502 and Secret Scan #826 passed on the completed code/documentation head; final task-metadata head must repeat the same repository gates.
- Follow-up debt: FOK Limit, shared TP/SL Limit selection, PostOnly/WebSocket and execution protections remain separate batches.
