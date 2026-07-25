# Task: Persist TP/SL execution methods

Issue: #111
Status: active
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
- Atomic claim, idempotency, position verification, rollback and failure-state distinctions remain authoritative.
- Live Write, monitor, 1 oz and single-lifecycle defaults remain unchanged.

## Data contract

- Add `take_profit_execution_mode` and `stop_loss_execution_mode` columns.
- Allowed persisted values: `market`, `limit`.
- Migration defaults all existing plans to `market` / `market`.
- New open requests default both fields to `market` for backward compatibility.
- Exit Plan responses expose both fields.

## Automatic close contract

- TP uses the persisted TP execution mode.
- SL uses the persisted SL execution mode.
- Automatic Limit uses the atomically claimed `trigger_spread` as `limitSpread`.
- Limit never silently falls through to Market.
- Clean FOK zero-fill releases the claim back to active.
- Partial, mismatch, timeout and unknown outcomes remain manual-intervention/reconciliation states.

## Expected scope

- ordered schema migration and migration tests;
- schemas, repository and open-plan creation;
- shared claimed-plan close selection;
- frontend TP/SL execution controls and plan display;
- focused lifecycle/state tests and existing regressions;
- API, ownership, current-state and synthetic execution docs.

## Non-goals

- No PostOnly, chase, amend/cancel or private WebSocket.
- No IOC.
- No Batch 5 execution-quality work.
- No safety-default relaxation.

## Acceptance criteria

- [ ] Existing plans migrate to Market/Market without data loss.
- [ ] New plans persist independent TP/SL modes.
- [ ] Manual, TP and SL close share the same close action.
- [ ] Automatic FOK uses claimed trigger spread.
- [ ] Automatic Limit does not fall through to Market.
- [ ] Clean zero-fill and abnormal outcomes preserve current state semantics.
- [ ] Frontend exposes and displays both modes.
- [ ] Backend, Runtime, frontend, Repository Safety and Secret Scan pass.

## Progress

- Done: baseline audited; Issue and branch created.
- Current: implement migration and Backend contract.
- Next: state-machine tests, frontend and documentation.
- Blocked by: none.

## Completion

- PR:
- Merge commit:
- Behavior changed:
- Behavior intentionally unchanged:
- Tests/CI:
- Follow-up: Batch 4 PostOnly Chase remains separate; Batch 5 remains deferred by user request.
