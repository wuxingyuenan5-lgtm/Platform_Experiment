# Task: Cross-Spread Market Execution Through Confirmed Bybit Fills

Issue: #90
Status: review
Branch: `feature/issue-90-cross-spread-market-loop`
Base commit: `fceb486783c45e7c6f1ffe261af05de4750cf16f`

## Objective

Complete the smallest verifiable market-order execution loop for the cross-venue spread strategy: submit the Bybit leg first, wait for a confirmed terminal fill, then size and submit the MT5 hedge from the actual filled quantity. Extend the direct MT5 terminal data path so raw swap long/short values are available to the existing strategy snapshot.

## Confirmed product decisions

- Keep the existing nominal spread calculation unchanged.
- Treat Bybit as the uncertain execution leg and MT5 as the immediate hedge leg.
- Do not treat a Bybit REST acknowledgement as a fill.
- Hedge only a terminal confirmed Bybit filled quantity.
- Keep market-order scope only.
- Keep Platform and Runtime Live Write disabled by default.

## Non-goals

- No USDT/USD normalization in trading spread calculation.
- No spread-limit execution.
- No automated take-profit or stop-loss.
- No real close, reduce-only or MT5 position-ticket semantics.
- No production Live Write enablement.
- No unrelated frontend or strategy-page changes.

## Changed files

- `execution-runtime/app/bybit_fill_confirming_adapter.py`
- `execution-runtime/app/bybit_mt5_gateway.py`
- `execution-runtime/app/config.py`
- `execution-runtime/app/cross_spread_market.py`
- `execution-runtime/tests/test_bybit_fill_confirming_adapter.py`
- `execution-runtime/tests/test_cross_spread_mt5_swap.py`
- `platform-backend/app/execution_batches.py`
- `platform-backend/tests/test_cross_spread_execution_quantity.py`
- `docs/codex/current-state.md`
- this task packet

## Implementation decisions

- Use a bounded synchronous confirmation loop as the minimum implementation; private Bybit WebSocket confirmation remains a later upgrade.
- Emit a deterministic fill event only for a full fill or terminal partial fill.
- Leave unresolved New/PartiallyFilled orders acknowledged and route the batch to manual intervention rather than submitting MT5 blindly.
- Derive the MT5 quantity from confirmed Bybit fill quantity using the requested hedge ratio and validate it against MT5 contract minimum and step.
- Read MT5 swap values and symbol metadata through `symbol_info()` when available while preserving compatibility with the file bridge and injected test modules.

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
- Frontend no-regression quality jobs.
- Secret Scan.

## Stop conditions

- Stop if the implementation requires enabling either Live Write default.
- Stop if unresolved Bybit status would require blind MT5 submission.
- Stop if partial fill cannot be mapped exactly to the MT5 contract minimum and step.
- Stop if the change expands into spread-limit or close-position semantics.
- Stop if an unrelated architecture boundary must change.

## Acceptance criteria

- [x] Bybit acknowledgement alone does not produce a fill event.
- [x] Full terminal Bybit fill produces a deterministic fill event.
- [x] Terminal partial fill exposes only the confirmed quantity.
- [x] Unresolved timeout does not submit an automatic hedge.
- [x] MT5 hedge quantity is recalculated from the confirmed Bybit fill.
- [x] Invalid MT5 minimum or step mapping is blocked.
- [x] Direct MT5 snapshot exposes raw swap long and swap short values.
- [x] Existing nominal spread formula remains unchanged.
- [x] Safe defaults remain unchanged.

## Progress

- Done: Issue, issue-numbered branch, implementation, focused tests, PR creation, repository-governance correction and complete implementation-head CI.
- Current: final documentation synchronization and merge.
- Next: squash merge after the documentation-only head passes; create a separate bounded issue for close/reduce-only semantics.
- Blocked by: none.

## Completion

- PR: #91
- Merge commit:
- Application behavior changed: market-order execution waits for confirmed Bybit fill before MT5 hedge; direct MT5 swap values are exposed.
- Business behavior changed: requested MT5 hedge quantity is replaced by actual-fill-proportional quantity for this strategy.
- Tests/CI: implementation head `1e9ef1c84bc6491a3f79e43a791b68499fabe0fe`; Platform CI #1250 passed; Secret Scan #677 passed; Repository Safety, Backend, Runtime and frontend quality all passed.
- Follow-up: real close semantics and private WebSocket confirmation remain separate scopes.
