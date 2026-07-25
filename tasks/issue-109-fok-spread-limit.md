# Task: FOK spread-limit execution

Issue: #109
Status: done
Branch: `feature/issue-109-fok-spread-limit`
Base commit: `b79b911e4a4fe736a2f2cf7641b1abe7d812d282`

## Objective

Implement real synthetic `LIMIT` execution for all four cross-spread actions using a Bybit FOK main leg and an MT5 market hedge only after confirmed full fill.

## Protected Market semantics

- Existing Market open/close behavior remains unchanged.
- Bybit remains the first/main leg.
- MT5 sizing remains based on confirmed actual Bybit fill and current MT5 specification.
- Bybit close remains reduce-only with matching position index.
- MT5 close remains bound to the intended Position Ticket.
- Existing position verification, rollback, reconciliation and manual-intervention rules remain authoritative.

## Implemented Limit contract

- User input is a spread limit, not a fixed Bybit price.
- Buy Bybit/sell MT5 uses `Bybit Ask - MT5 Bid` and a maximum allowed spread.
- Sell Bybit/buy MT5 uses `Bybit Bid - MT5 Ask` and a minimum allowed spread.
- Derived Bybit price uses current executable quotes, Platform Contract Tick, a configured non-negative hedge reserve and conservative rounding.
- A non-executable current spread is rejected before Batch creation.
- Cross-spread Limit submits Bybit `timeInForce=FOK`.
- Only terminal exact full fill emits a normal Fill that permits MT5 submission.
- Zero fill rejects without MT5; clean manual-close zero fill restores the Exit Plan to `active`.
- Partial, quantity-mismatch, timeout or unknown outcome does not emit a hedge-driving Fill and requires reconciliation/manual intervention.
- A successful full fill reuses actual-fill MT5 sizing, reduce-only/ticket-bound close, external-position verification and existing rollback rules.

## Non-goals

- No PostOnly/chase/amend loop.
- No private WebSocket.
- No IOC.
- No automatic TP/SL Market-vs-Limit selection.
- No safety-default relaxation.
- No database migration.

## Actual scope

- `platform-backend/app/cross_spread_limit_policy.py` (new)
- `platform-backend/app/cross_spread_limit_execution.py` (new)
- `platform-backend/app/cross_spread_order_intent.py`
- `platform-backend/app/cross_spread_synthetic_service.py`
- `platform-backend/app/cross_spread_exit_repository.py`
- `platform-backend/app/cross_spread_exit_schemas.py`
- `platform-backend/app/cross_spread_exit_routes.py`
- `platform-backend/app/config.py`
- focused Backend policy/lifecycle tests and existing Market regression updates
- `execution-runtime/app/bybit_fill_confirming_adapter.py`
- Runtime FOK terminal-state tests
- frontend lifecycle API types and Market/FOK execution controls
- synthetic execution, API, ownership, current-state and operational acceptance documentation

## Required verification

- Backend Ruff, Pyright and classified tests.
- Runtime Ruff, Pyright and classified tests.
- Existing Market lifecycle/rollback regression suites.
- FOK price rounding, full-fill, no-fill, partial and unknown-result tests.
- Frontend lint, no-new-debt, type check and build.
- Repository Safety and Secret Scan.

## Acceptance criteria

- [x] Four actions share two deterministic executable-direction formulas.
- [x] Derived Bybit prices are conservative after reserve and tick rounding.
- [x] Full Bybit FOK fill permits exactly one existing MT5 market hedge path.
- [x] No-fill submits no MT5 command.
- [x] Partial/unknown fails closed into reconciliation/manual intervention.
- [x] Open and close external-position verification remain mandatory.
- [x] Market behavior is unchanged.
- [x] Frontend supports selecting Market/Limit and entering a spread limit.
- [x] Required CI and Secret Scan pass.

## Risk and rollback

Risk: high

- Primary failure modes: permissive Tick rounding, partial FOK interpreted as a full Fill, MT5 submission after no-fill/unknown, or Market regression.
- Detection: pure pricing tests, Runtime terminal-state tests, Platform lifecycle/state tests and full existing suites.
- Rollback: revert the squash merge; no database migration or mandatory external-state transition is introduced.

## Progress

- Done: pricing, Platform orchestration, Runtime FOK confirmation, plan-state handling, UI, tests and authoritative documentation completed.
- Current: final task-metadata-head verification before squash merge.
- Next: a separate batch will persist TP/SL execution methods and route automatic exits through the same Market/FOK Close Action.
- Blocked by: none.

## Completion

- PR: #110
- Merge commit: GitHub PR/main history is authoritative; no post-merge metadata PR will be created.
- Behavior changed: manual Open/Close can use synthetic FOK spread-limit execution with additive pricing evidence.
- Behavior intentionally unchanged: existing Market execution, automatic TP/SL Market behavior, Live Write defaults, exit-monitor default, 1 oz/single-lifecycle controls and all permanent safety invariants.
- Tests/CI: Platform CI #1545 and Secret Scan #843 passed on the completed code/documentation head; the final task-metadata head must repeat the same repository gates.
- Operational evidence not produced: no real Bybit/MT5 order, real Tick check, Broker Hedge Reserve validation or Windows-host execution occurred.
- Follow-up debt: TP/SL execution selection, PostOnly/private WebSocket, IOC and execution-quality protections remain separate batches.
