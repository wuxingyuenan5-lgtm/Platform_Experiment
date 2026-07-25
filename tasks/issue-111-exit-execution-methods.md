# Task: Persist TP/SL execution methods

Issue: #111
Status: done
Branch: `feature/issue-111-exit-execution-methods`
Base commit: `d8561dee1523d07a7bae511263bd81100be4cb51`

## Objective

Persist independent take-profit and stop-loss execution modes on every cross-spread Exit Plan and route manual close, automatic take profit and automatic stop loss through the same claimed-plan Market/FOK close action.

## Protected semantics

- Existing threshold formulas and inequalities remain unchanged.
- Existing manual Market and FOK close behavior remains unchanged.
- Bybit remains the first/main leg; MT5 remains the actual-fill-sized hedge leg.
- Bybit close remains reduce-only with matching position index.
- MT5 close remains bound to the intended Position Ticket.
- Atomic claim, position verification, rollback and failure-state distinctions remain authoritative.
- Live Write, monitor, 1 oz and single-lifecycle defaults remain unchanged.

## Implemented data contract

- Migration v3 adds `take_profit_execution_mode` and `stop_loss_execution_mode`.
- Persisted values are constrained to `market` or `limit`.
- Existing plans migrate to `market / market` without data loss.
- New requests and response models remain backward compatible through Market defaults.
- Exit Plan API and frontend expose both fields.

## Implemented automatic close contract

- TP uses its persisted TP execution mode.
- SL uses its persisted SL execution mode.
- Manual, TP and SL use the same claimed-plan Close Action.
- Automatic Limit uses the atomic Claim's `trigger_spread` as `limitSpread`.
- Limit never silently falls through to Market.
- Pre-submit quote movement and clean FOK zero-fill release the Claim back to `active`.
- Partial, mismatch, timeout and unknown outcomes remain manual-intervention/reconciliation states.
- FOK Close idempotency includes the Claim timestamp, so a released clean no-fill may be attempted again without replaying the first Batch.

## Actual scope

- `platform-backend/app/schema_migrations.py`
- `platform-backend/app/cross_spread_exit_schemas.py`
- `platform-backend/app/cross_spread_exit_repository.py`
- `platform-backend/app/cross_spread_synthetic_service.py`
- migration, FOK lifecycle and automatic-exit tests
- frontend lifecycle API and execution controls
- ownership, current-state, database and synthetic-execution documentation

## Non-goals

- No PostOnly, chase, amend/cancel or private WebSocket.
- No IOC.
- No Batch 5 execution-quality work.
- No safety-default relaxation.

## Acceptance criteria

- [x] Existing plans migrate to Market/Market without data loss.
- [x] New plans persist independent TP/SL modes.
- [x] Manual, TP and SL close share the same close action.
- [x] Automatic FOK uses claimed trigger spread.
- [x] Automatic Limit does not fall through to Market.
- [x] Clean zero-fill and abnormal outcomes preserve current state semantics.
- [x] Frontend exposes and displays both modes.
- [x] Backend, Runtime, frontend, Repository Safety and Secret Scan pass.

## Completion

- PR: #112
- Merge commit: GitHub PR/main history is authoritative; no post-merge metadata PR will be created.
- Behavior changed: Exit Plans persist TP/SL execution methods and automatic exits can select Market/FOK through the shared Close Action.
- Behavior intentionally unchanged: threshold formulas, Market/FOK leg semantics, reduce-only/ticket safeguards, Live Write defaults, monitor default and acceptance limits.
- Tests/CI: Platform CI #1576 and Secret Scan #855 passed on the completed code/documentation head; final task-metadata head must repeat repository gates.
- Operational evidence not produced: no real Bybit/MT5 order, automatic monitor enablement or Windows-host execution occurred.
- Follow-up: Batch 4 PostOnly Chase remains separate; Batch 5 remains deferred by user request.
