# Task: Repair Live Reads and Harden One-Ounce Acceptance

Issue: #96
Status: completed
Branch: `hardening/issue-96-one-ounce-live-acceptance`
Base commit: `060f4ede1c9eb08a2ead2d3da3007b29a9f66f58`
PR: #97

## Objective

Repair the real Bybit/MT5 order-read path and add the temporary P0 controls required before a supervised 1 troy ounce real-money cross-spread acceptance test.

## Confirmed operating boundary

- The acceptance account may contain about 1000 USDT.
- Maximum requested Bybit quantity is temporarily 1 oz.
- A terminal Bybit partial fill may be hedged below 1 oz only when it maps exactly to the current MT5 contract minimum and step.
- At most one non-closed cross-spread lifecycle may exist.
- Market open, market close and spread-triggered market TP/SL are the only connected execution modes.
- Limit execution remains out of scope.
- Platform Live Write, Runtime Live Write and the automatic exit monitor remain disabled by default.

## Changed ownership and modules

### Execution Runtime

- `bybit_acceptance_adapter.py`: route-independent Order/Fill reads, bounded order list, current instrument and API-key readiness evidence.
- `mt5_acceptance_adapter.py`: route-independent Order/Deal reads, explicit Order/Deal Ticket resolution, current Symbol/Terminal evidence.
- `strict_live_acceptance_adapters.py`: independent 1 oz cap, current quantity-step/contract-size/access checks and one-position admission.
- `bybit_mt5_gateway.py`: account-routed reads and deterministic route-independent external-ID dispatch.
- `gateway.py`, `main.py`, `models.py`: public order-list and instrument-specification query contracts.
- `fake_gateway.py`: compatibility implementation for the expanded read contract.
- `config.py` and `.env.live.example`: safe acceptance defaults.
- focused Runtime tests.

### Platform Backend

- `cross_spread_live_read_client.py`: typed Runtime live reads.
- `cross_spread.py`: current-spec exact sizing and Bybit-only emergency rollback validation.
- `cross_spread_exit_service.py`: single-lifecycle admission, external position verification and definitive-failure rollback coordination.
- `cross_spread_exit_repository.py`: non-closed lifecycle and unresolved-batch counts.
- `config.py` and `.env.example`: temporary acceptance defaults.
- focused Backend tests.

### Documentation and governance

- `docs/operations/V6-小资金实盘验收手册.md`
- `docs/technical/LIVE_VENUE_ADAPTERS.md`
- `docs/technical/VENUE_RECONCILIATION.md`
- `docs/codex/current-state.md`
- `docs/architecture/OWNERSHIP.md`
- this task packet

## Implementation decisions

- Route metadata enriches a read result but is not a prerequisite for reading a real order.
- MT5 Order Ticket, Deal Ticket and Position Ticket remain distinct identities.
- Current venue contract specifications and access evidence are required before live writes.
- Database Seed specifications are not authoritative for real execution.
- The 1 oz limit and single-active-plan rule are temporary acceptance controls with explicit removal evidence.
- A definitive MT5 hedge rejection/failure after a confirmed Bybit fill may initiate one idempotent Bybit reduce-only rollback only after live positions prove the expected first-leg exposure and no MT5 exposure.
- An unknown MT5 outcome must not trigger a blind rollback or duplicate write.
- If external positions are already flat, no duplicate rollback is submitted.
- Open and close success require external position evidence, not command status alone.
- Flat verification checks every target-symbol position, not only the expected MT5 ticket.

## Temporary restriction removal criteria

Review temporary restrictions only in a separate Issue/PR after Issue #39 records repeated real-money evidence for:

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

Final delivery also requires Runtime and Backend lint, progressive type gates and classified tests; frontend checks; Platform CI; and Secret Scan.

## Stop conditions

- Stop if implementation requires enabling either Live Write default or the exit monitor default.
- Stop if an unknown venue result would cause automatic duplicate execution.
- Stop if a rollback can increase, reverse or duplicate exposure.
- Stop if current venue specifications cannot prove exact quantity mapping.
- Stop if the scope expands into limit execution, WebSocket migration, increased quantity or concurrent positions.
- Stop if credentials or account secrets would enter Git, Markdown, logs or tests.

## Acceptance criteria

- [x] Bybit and MT5 current/recent orders can be listed without local route state.
- [x] Direct order reads work for external and Platform-created orders.
- [x] MT5 Order/Deal/Position ticket semantics are separated.
- [x] Current Bybit and MT5 specifications are exposed read-only.
- [x] Exactly 1 oz maps to a valid MT5 volume using current contract size and step.
- [x] Quantity above 1 oz is blocked at Platform and Runtime boundaries.
- [x] A second active or unresolved cross-spread open is blocked.
- [x] Definitive second-leg failure causes at most one safe rollback attempt.
- [x] Unknown outcomes do not cause blind rollback or retry.
- [x] Post-open/post-close external positions are verified.
- [x] Temporary restrictions and removal criteria are synchronized in canonical Markdown.
- [x] Required CI and Secret Scan passed before final documentation-state commit.

## Progress

- Done: root-cause audit, Issue #96, branch, task packet and PR #97.
- Done: Runtime route-independent reads, specification/access evidence and strict acceptance adapters.
- Done: Platform exact live sizing, single-lifecycle controls, external position verification and safe rollback coordination.
- Done: Backend/Runtime regression tests and canonical Markdown synchronization.
- Done: Secret Scan, repository safety, Backend lint/type/tests, Runtime lint/type/tests and Frontend lint/type/build on the pre-close final head.
- Final: documentation-state closeout committed; the final head must pass the same CI before squash merge.
- Blocked by: none.
