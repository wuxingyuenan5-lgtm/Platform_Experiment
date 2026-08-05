# Execution Risk Controls

Status: active for Platform 0.10.1.

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

## Persisted objects

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

## Residual exposure

For each fill:

```text
signed contract delta = side sign × fill quantity × contract multiplier
```

Within one base/settlement group:

```text
net contract delta = sum(signed contract delta)
reference price = maximum valid fill price
residual = abs(net contract delta) × reference price
```

Mixed currency without a risk-FX snapshot is conservative and incomplete. This metric is an execution-risk gate, not formal PnL or accounting input.

## States and actions

Risk states remain `clear`, `residual_exposure`, `disposition_in_progress`, `resolved` and `escalated`.

Supported actions remain:

- `hold_and_escalate`;
- `flatten_filled_legs`;
- `cancel_open_legs`;
- `substitute_hedge`.

Auto-flatten creates an opposite TradeCommand for each filled original leg. Substitute hedge also uses an independent idempotent TradeCommand. A non-filled or Result Unknown risk-reduction command cannot be declared resolved.

## Idempotency

| Object | Identity |
|---|---|
| Kill Switch change | request `idempotencyKey` |
| Risk policy change | request `idempotencyKey` |
| Risk action | request `idempotencyKey` |
| Auto-flatten leg | `<risk-action-key>:<leg-role>` |
| Substitute hedge | `<risk-action-key>:replacement` |

Reusing a key with a different payload returns 409.

## Safety limits

- Accepted or Result Unknown external orders are not claimed canceled without venue evidence.
- Multi-currency residual comparison remains fail-closed without a risk-FX snapshot.
- Live Write remains disabled by default and continues to require existing authorization, two-person session and Runtime safety gates.
