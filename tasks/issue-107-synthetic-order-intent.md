# Task: Synthetic cross-spread order intent

Issue: #107
Status: active
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
- Cross-spread lifecycle frontend API/component labels needed to expose the normalized intent.
- Direct Backend/frontend tests.
- API/current-state/strategy documentation.

## Expected changed files

- `platform-backend/app/cross_spread_order_intent.py` (new)
- `platform-backend/app/cross_spread_exit_schemas.py`
- `platform-backend/app/cross_spread_exit_service.py`
- `platform-backend/tests/test_cross_spread_market_lifecycle.py`
- `platform-backend/tests/test_cross_spread_exit_policy.py` or a focused new test file if needed
- `admin-risk/src/api/platform/crossSpreadLifecycle.ts`
- `admin-risk/src/views/strategy/spread-carry/components/CrossSpreadMarketLifecyclePanel.vue`
- `docs/technical/API_SPEC.md`
- `docs/codex/current-state.md`
- `admin-risk/docs/strategies/跨所价差.md`
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

- [ ] Four actions map deterministically to existing Market commands and leg directions.
- [ ] Open/manual close/TP/SL close use the same normalized command model.
- [ ] Existing public Market endpoints remain compatible.
- [ ] Trigger reason is explicit for manual and automatic closes.
- [ ] Limit remains rejected with no side effect.
- [ ] Documentation records the five-batch roadmap and Batch 1 boundary.
- [ ] Required CI and Secret Scan pass.

## Risk and rollback

Risk: medium

- Failure modes: action mapping changes a Market direction; trigger metadata leaks into execution behavior; compatibility payload changes.
- Detection: mapping unit tests plus full existing lifecycle tests.
- Rollback: revert the squash merge; no migration or external state change is introduced.

## Progress

- Done: Issue and branch created; current Market lifecycle entry points identified.
- Current: implement shared intent model and compatibility adapters.
- Next: add tests, frontend verification fields and documentation; open PR and run full gates.
- Blocked by: none.

## Completion

- PR:
- Merge commit:
- Behavior changed: normalized internal intent/metadata only.
- Behavior intentionally unchanged: all Market/Venue/risk behavior.
- Tests/CI:
- Follow-up debt: FOK Limit, shared TP/SL Limit selection, PostOnly/WebSocket and execution protections remain separate batches.
