# Task: FOK spread-limit execution

Issue: #109
Status: active
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

## Limit contract

- User input is a spread limit, not a fixed Bybit price.
- Buy Bybit/sell MT5 uses `Bybit Ask - MT5 Bid` and a maximum allowed spread.
- Sell Bybit/buy MT5 uses `Bybit Bid - MT5 Ask` and a minimum allowed spread.
- Derived Bybit price uses current MT5 executable quote, current Bybit Tick Size, a bounded hedge reserve and conservative rounding.
- Bybit FOK full fill is required before any MT5 command.
- FOK no-fill ends without an MT5 order.
- Partial or unknown Bybit outcome enters reconciliation/manual intervention; it is not treated as normal FOK completion.

## Non-goals

- No PostOnly/chase/amend loop.
- No private WebSocket.
- No IOC.
- No automatic TP/SL Market-vs-Limit selection.
- No safety-default relaxation.
- No database migration unless evidence proves it unavoidable.

## Expected scope

- Pure spread-limit pricing policy.
- Lifecycle request/response schema additions.
- Synthetic lifecycle Limit orchestration.
- Runtime command and Bybit FOK support.
- Existing close intent/reduce-only/ticket rules.
- Frontend execution-mode and spread-limit controls.
- Focused Backend/Runtime/frontend tests.
- API, ownership, current-state and execution-contract documentation.

## Required verification

- Backend Ruff, Pyright and classified tests.
- Runtime Ruff, Pyright and classified tests.
- Existing Market lifecycle/rollback regression suites.
- FOK price rounding, full-fill, no-fill, partial and unknown-result tests.
- Frontend lint, no-new-debt, type check and build.
- Repository Safety and Secret Scan.

## Stop conditions

- Stop if FOK cannot be distinguished from partial/unknown Venue outcomes.
- Stop if implementing Limit requires weakening existing Market or Live safety gates.
- Stop if a database migration becomes necessary; split it explicitly.
- Stop if automatic TP/SL selection or PostOnly behavior begins leaking into this batch.

## Acceptance criteria

- [ ] Four actions share two deterministic executable-direction formulas.
- [ ] Derived Bybit prices are conservative after reserve and tick rounding.
- [ ] Full Bybit FOK fill submits exactly one MT5 market hedge.
- [ ] No-fill submits no MT5 command.
- [ ] Partial/unknown fails closed into reconciliation/manual intervention.
- [ ] Open and close external-position verification remain mandatory.
- [ ] Market behavior is unchanged.
- [ ] Frontend supports selecting Market/Limit and entering a spread limit.
- [ ] Required CI and Secret Scan pass.

## Progress

- Done: baseline audited; Issue and branch created.
- Current: inspect current command contracts and Bybit adapter before choosing the minimal safe implementation seam.
- Next: implement pricing policy, Runtime FOK support, Platform orchestration and tests.
- Blocked by: none.

## Completion

- PR:
- Merge commit:
- Behavior changed:
- Behavior intentionally unchanged:
- Tests/CI:
- Follow-up debt: TP/SL execution selection, PostOnly/WebSocket and execution-quality protections remain separate batches.
