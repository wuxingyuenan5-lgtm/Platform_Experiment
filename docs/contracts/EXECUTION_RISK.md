# Execution Risk Contract

Status: `active contract`.

## Ownership

```text
ExecutionBatch → multi-leg sequencing
Execution Risk models → enums and public DTOs
Execution Risk policy → deterministic deadline, residual and disposition rules
Execution Risk repository → SQL and persisted risk state
Execution Risk router/application → validation and orchestration
TradeCommand → every order side effect
Financial Facts → auditable post-trade economic truth
```

Risk actions never bypass TradeCommand. Kill Switch does not rewrite historical orders, fills or financial facts.

## Normal trading

Owner confirmed normal trading on 2026-09-09. Browser CEO authorization, active trading bindings, live gates, balance/margin checks and venue specifications replace acceptance sessions, temporary windows and fixed-size/notional/position-count caps. Every live order checks Kill Switch and unresolved venue reconciliation directly; these checks must not depend on a legacy session having initialized or claimed anything.

Instruction quantity ceilings, one-instruction/one-batch identity, resource serialization, bounded chase, fail-closed unknown handling and reconciliation remain mandatory. The [acceptance runbook](../operations/LIVE_ACCEPTANCE_RUNBOOK.md) supplies evidence procedures, not additional normal-trading permission gates.

## Persisted objects

Batch admission checks every live leg's account binding, gate and reconciliation before dispatching the first leg; per-order checks still run immediately before dispatch. A formally accepted native timestamp correction is non-blocking only when the exact old/new receipts satisfy the same time-only acceptance rules used by venue-event ingestion. Other open/accepted differences still block. This prevents a known second-account blocker from first being discovered after the first fill.

- `trading_kill_switches` and `kill_switch_commands`;
- `execution_risk_policies` and idempotency commands;
- `execution_batch_risk`;
- `execution_risk_actions`.

The 0.10.1 refactor moves their SQL to `execution_risk_repository.py` without changing the schema or row meaning.

## Admission and fail-closed order

```text
catalog and binding validation
→ global Kill Switch
→ strategy Kill Switch
→ account Kill Switches
→ batch claim
→ policy snapshot
→ first leg
```

Kill Switch and leg deadline are checked again before later legs.

Funding evaluates the batch's frozen residual limit before each Spot release and
checks the first-fill deadline when confirmed perpetual fills remain unreleased.
The one authoritatively synchronized working perpetual order may contribute its
confirmed fills to this incremental gate; this does not prove terminal execution
or a flat position. Native Spot fees must be reconciled before a later release.
On breach, an active perpetual attempt is canceled and checked, then the batch
pauses. An opening batch with complete terminal evidence may apply its frozen
`auto_flatten` policy; unknown evidence stays paused. A failed closing batch is
never reversed by this policy.

Funding and Cross account-capital pages expose existing risk policy and strategy
Kill Switch APIs to users with `risk:manage`. Changes require explicit confirmation
and retain the same request key after a lost response. Policy updates affect new
batches; existing batch snapshots remain unchanged. No account-specific values are
chosen automatically, and global/account Kill Switches continue to apply.

## Residual exposure

Use exact command-owned orders from all batch legs, including partial fills,
every Funding perpetual attempt and Spot release, the persisted Cross rollback
command and generated risk-action order IDs. Persisted action/leg idempotency
keys retain ownership even if a later exception interrupts the action response.
Unrelated orders in a shared account do not belong to the batch. For each
proven execution:

```text
signed contract delta = side sign × fill quantity × contract multiplier
```

Within one base-currency group:

```text
net contract delta = sum(signed contract delta)
reference price = maximum valid fill price
residual = abs(net contract delta) × reference price
```

Runtime confirmations and native executions describe overlapping evidence;
never add their quantities together. Native executions are deduplicated by
source and native fill ID within the exact account, instrument and order.
Unclassified legacy fills remain immutable and cannot prove closure without
full native execution coverage. Conflicting identity, excess execution,
unresolved order/command outcome or missing contract metadata remains incomplete.

Net quantity is calculated before applying a price. A proven zero quantity
across USD/USDT legs is zero residual execution exposure; differing fill prices
are not an unhedged position. Nonzero mixed-currency exposure without a risk-FX
snapshot remains incomplete. This metric is an execution-risk gate, not formal
PnL, full market-risk equivalence or accounting input.

## Evidence-based recheck

Late Runtime recovery, successful formal Venue reconciliation and a filled,
verified Cross rollback recheck the finished batch's persisted risk. The recheck
shares one database transaction with its `execution_batch_risk_reconciled` audit,
which retains the prior state, exact order/fill IDs, quantities and evidence
quality. Only complete zero-residual evidence resolves a prior risk; incomplete
evidence stays escalated. Repeated identical rechecks do not create another audit.
This operation does not submit orders or rewrite fills, financial facts, positions
or exit plans. Background account monitoring alone cannot resolve an unknown command.

## States and actions

Risk states remain `clear`, `residual_exposure`, `disposition_in_progress`, `resolved` and `escalated`.

Live Spot exposure uses executed base quantity less verified native base-currency fees. Quote-currency fees affect costs, not coin quantity. Missing or incomplete native fee coverage keeps evidence incomplete. Funding's planned positive rounding remainder remains real residual exposure; it is never reported as zero merely because it is smaller than a perpetual quantity step.

Supported actions remain:

- `hold_and_escalate`;
- `flatten_filled_legs`;
- `cancel_open_legs`;
- `substitute_hedge`.

Flattening requires a failed or manually paused batch and complete terminal execution evidence. Reconcile live owned orders and native fills before calculating remaining quantity. Sum every original attempt, release and previous reduction by account and instrument; a zero directional hedge is not proof that both instruments are flat. Spot base-currency fees reduce sellable inventory; missing fee coverage and untradeable dust remain explicit blockers. Funding uses its frozen quantity steps, and live order admission revalidates current native specifications. Crypto perpetual reductions are reduce-only; a position needing a venue-specific close target cannot use the generic reduction path.

Create an opposite TradeCommand only for a proven remaining position. A non-filled or Result Unknown reduction stops further leg dispatch and keeps the risk unresolved. Retain any generated order IDs when a later operation fails. A new action key after verified closure produces no additional orders. Substitute hedge continues to use an independent idempotent TradeCommand.

Only proof that every owned instrument is flat can finalize a flatten action. Finalization atomically resolves risk, closes the failed Funding instruction, cancels unsubmitted legs, releases claims/reservations, and records exact execution evidence plus the previous failure reasons. Replaying an already completed action may finish this local bookkeeping from existing evidence; it cannot resubmit trades. Original orders, fills and economic facts remain immutable. Funding enters manual intervention with a refreshed residual-risk calculation even when its first fill query failed.

Cancel and substitute actions also require a failed or manually paused batch.
Canceling unsubmitted legs does not erase earlier fills; a filled substitute does
not prove a complete hedge. Both recheck owned execution evidence and keep
`action_required` while nonzero or incomplete exposure remains. A Funding close
cannot use generic flattening, which would reopen its completed perpetual leg;
use the original close recovery described in the API contract. Unresolved Funding
recovery children block competing risk disposition.

## Idempotency

| Object | Identity |
|---|---|
| Kill Switch change | request `idempotencyKey` |
| Risk policy change | request `idempotencyKey` |
| Risk action | request `idempotencyKey` |
| Auto-flatten leg | `<risk-action-key>:<leg-role>` |
| Substitute hedge | `<risk-action-key>:replacement` |

Reusing a key with a different batch or payload returns 409. Risk actions are claimed atomically and serialized within one batch, including requests with different keys.

## Safety limits

- Accepted or Result Unknown external orders are not claimed canceled without venue evidence.
- Multi-currency residual comparison remains fail-closed without a risk-FX snapshot.
- Live Write remains disabled by default. Existing explicit Owner authorization governs the current operating period; CEO/account authorization and independent Platform/Runtime safety gates remain required. Local validation never grants real-trading permission.

## Funding executable-spread exits

The per-opening plan compares spot Bid minus perpetual Ask in USDT per base coin: TP uses >=, SL uses <=. Both quotes must match the frozen account and pair, have complete quality, positive uncrossed books and aware source timestamps no more than 10 seconds old (future tolerance 2 seconds). Only normal active groups without pending/unknown closes are eligible. Platform Live Write off skips evaluation; readiness, Kill Switch, Runtime permissions and all existing Funding close checks still apply at dispatch.

A revision-checked database claim freezes the quantity and unique `funding-exit:<open-id>` key. Recovery looks up the original instruction before any submission; an existing instruction is handled by the normal runner, including unknown-result reconciliation. Before initial publication or recovery of an unpublished claim, revalidate current quotes/threshold, original account/pair and unchanged remaining quantity. A changed group pauses; no new identity or automatic rearming is allowed. Concurrent manual closes are protected by the same transactional group-capacity and original-leg identity check. A terminal failed automatic close remains the same recorded close; any recovery uses existing explicit recovery controls.
