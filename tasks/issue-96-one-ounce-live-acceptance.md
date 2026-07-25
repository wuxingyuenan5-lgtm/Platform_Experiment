# Task: Repair Live Reads and Harden One-Ounce Acceptance

Issue: #96
Status: active
Branch: `hardening/issue-96-one-ounce-live-acceptance`
Base commit: `060f4ede1c9eb08a2ead2d3da3007b29a9f66f58`

## Objective

Repair the real Bybit/MT5 order-read path and add the temporary P0 controls required before a supervised 1 troy ounce real-money cross-spread acceptance test.

## Confirmed operating boundary

- The acceptance account may contain about 1000 USDT.
- Maximum requested and confirmed Bybit quantity is temporarily 1 oz.
- At most one non-closed cross-spread lifecycle may exist.
- Market open, market close and spread-triggered market TP/SL are the only connected execution modes.
- Limit execution remains out of scope.
- Platform Live Write, Runtime Live Write and the automatic exit monitor remain disabled by default.

## Expected changed files

### Execution Runtime

- `execution-runtime/app/models.py`
- `execution-runtime/app/gateway.py`
- `execution-runtime/app/main.py`
- `execution-runtime/app/bybit_live_adapter.py`
- `execution-runtime/app/bybit_mt5_gateway.py`
- `execution-runtime/app/mt5_live_adapter.py`
- `execution-runtime/app/mt5_position_closing_adapter.py`
- `execution-runtime/app/live_route_store.py`
- `execution-runtime/app/live_safety.py`
- `execution-runtime/app/config.py`
- focused Runtime tests

### Platform Backend

- `platform-backend/app/config.py`
- `platform-backend/app/cross_spread.py`
- `platform-backend/app/cross_spread_exit_service.py`
- `platform-backend/app/cross_spread_exit_repository.py`
- `platform-backend/app/execution_batches.py`
- bounded live-read/preflight client or schema modules as required
- focused Backend tests

### Frontend / operational surfaces

- Existing lifecycle/API files only if required to expose read/preflight state.
- Do not redesign the spread workspace or connect limit execution.

### Documentation and governance

- `docs/operations/V6-小资金实盘验收手册.md`
- `docs/technical/LIVE_VENUE_ADAPTERS.md`
- `docs/technical/VENUE_RECONCILIATION.md`
- `docs/codex/current-state.md`
- `docs/architecture/OWNERSHIP.md` if ownership changes
- this task packet

## Implementation decisions

- Add route-independent bounded order listing and direct venue lookup. Route metadata enriches a result but is not a prerequisite for reading it.
- Distinguish MT5 Order Ticket, Deal Ticket and Position Ticket; do not reuse one identity as another.
- Query current venue contract specifications before live acceptance and require exact quantity mapping.
- Treat the 1 oz limit and single-active-plan rule as temporary acceptance controls with explicit removal evidence.
- Definitive MT5 hedge rejection/failure after a confirmed Bybit fill may initiate one idempotent Bybit reduce-only rollback. An unknown MT5 outcome must not trigger a blind rollback or duplicate write.
- Verify live positions after open and after close; lifecycle success requires external position evidence, not command status alone.

## Temporary restriction removal criteria

These restrictions are not permanent product requirements. Review them only in a separate Issue/PR after Issue #39 records repeated real-money evidence for:

1. reliable Order, Fill/Deal, Position and Balance reads without route dependence;
2. exact post-open and post-close external position reconciliation;
3. a controlled Bybit-filled/MT5-definitive-failure rollback drill;
4. Runtime restart and route-loss recovery;
5. network interruption and `result_unknown` handling;
6. TP/SL exactly-once market close;
7. no unexplained EOD reconciliation differences.

Do not silently raise limits in environment configuration. Mature acceptance must trigger an explicit review of which temporary restrictions can be removed and which safety invariants remain permanent.

## Required verification

```text
python scripts/check-workstream.py
python scripts/scan-secrets.py
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
```

Final delivery also requires Runtime and Backend lint, progressive type gates and classified tests; frontend checks if frontend files change; Platform CI; and Secret Scan.

## Stop conditions

- Stop if implementation requires enabling either Live Write default or the exit monitor default.
- Stop if an unknown venue result would cause automatic duplicate execution.
- Stop if a rollback can increase or reverse exposure.
- Stop if current venue specifications cannot prove exact 1 oz mapping.
- Stop if the scope expands into limit execution, WebSocket migration, increased quantity or concurrent positions.
- Stop if credentials or account secrets would enter Git, Markdown, logs or tests.

## Acceptance criteria

- [ ] Bybit and MT5 current/recent orders can be listed without local route state.
- [ ] Direct order reads work for external and Platform-created orders.
- [ ] MT5 Order/Deal/Position ticket semantics are separated.
- [ ] Current Bybit and MT5 specifications are exposed read-only.
- [ ] Exactly 1 oz maps to a valid MT5 volume using current contract size and step.
- [ ] Quantity above 1 oz is blocked at Platform and Runtime boundaries.
- [ ] A second active or unresolved cross-spread open is blocked.
- [ ] Definitive second-leg failure causes at most one safe rollback attempt.
- [ ] Unknown outcomes do not cause blind rollback or retry.
- [ ] Post-open/post-close external positions are verified.
- [ ] Temporary restrictions and removal criteria are synchronized in canonical Markdown.
- [ ] Required CI and Secret Scan pass.

## Progress

- Done: root-cause audit, Issue #96, branch and task packet.
- Current: Runtime read/specification contract implementation.
- Next: Platform one-ounce controls, rollback and position verification.
- Blocked by: none.
