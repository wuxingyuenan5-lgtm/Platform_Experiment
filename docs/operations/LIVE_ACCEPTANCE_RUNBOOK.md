# Live Acceptance Runbook

Status: active Platform 0.10.x operational contract.

This runbook governs controlled, minimum-size live acceptance. It does not authorize production rollout or Live Write activation. Any failed, unavailable or contradictory step immediately returns the system to read-only live mode and requires an accountable operator decision.

## 1. Release sequence

```text
只读实盘
→ 合约规格、账户风险、订单和成交历史核对
→ 影子对账
→ 1 oz Market人工监督
→ 1 oz FOK人工监督
→ TP/SL执行验收
→ PostOnly Chase专门监督验收
→ 失败处置与Kill Switch
→ 日终对账
→ 强制复位
```

The sequence is strict. A later step cannot compensate for a failed earlier step. Repository CI, simulation results, an order ACK or an application response cannot replace venue evidence.

## 2. Mandatory safety boundaries

- Platform Live Write and Runtime Live Write are independent gates; both remain disabled except inside an approved supervised window.
- Live and Simulation use different databases, Runtime Journals, Accounts and Credentials.
- Account, Strategy and Symbol use exact allowlists. Per-order and per-day limits are mandatory.
- ACK is not Fill. External terminal state and fill/deal evidence are authoritative for execution completion.
- `result_unknown` forbids blind retry, blind rollback and duplicate business intent.
- Query failure is unavailable evidence, never an empty position, zero balance, zero order or zero history result.
- External Order, Fill, Deal and Position identities must remain traceable to Platform and Runtime facts.
- Funds, quantity, symbols, concurrency and automation cannot expand before end-of-day reconciliation is complete.
- Credentials, private values and live evidence are not copied into source control, general logs or ordinary documentation.

## 3. One-ounce and execution-mode acceptance

The maximum acceptance quantity is `1 troy ounce`, including quantity derived after contract-multiplier and step-size conversion.

### Market

- Supervise both long/short opening and closing paths.
- Submit the second leg only after the first leg has a proven terminal fill and size is derived from actual fill quantity.
- Close is complete only when external positions reach the intended terminal state; a response or Batch state alone is insufficient.

### FOK

- Exact full fill: only a terminal cumulative fill equal to requested quantity may create normal Fill evidence and release the second leg.
- Zero fill: create no Fill, submit no second leg, create no Open Exit Plan, and restore an affected Close plan to `active`.
- Partial fill: do not submit the second leg automatically; enter reconciliation or accountable manual intervention.
- Unknown result: do not interpret as zero fill and do not retry the original intent.
- A Close anomaly must not incorrectly close the Exit Plan or release its claim.

### TP/SL

- Validate manual evaluation before any temporary Exit Monitor window.
- TP and SL retain their own execution mode and limit strategy but execute the same controlled Close action.
- Partial fill, post-submit timeout or unknown result does not release the Close claim.
- No limit path silently falls back to Market or another strategy.

### PostOnly Chase

- PostOnly Chase is disabled by default and enabled only in a dedicated supervised window after Market, FOK and TP/SL acceptance pass.
- Private order/execution events are the primary state source; REST is bounded reconciliation evidence.
- Only deduplicated cumulative fill exactly equal to requested quantity releases the second leg.
- Partial fill, private-stream disconnect, sequence or identity anomaly, and cancel/fill race fail closed: stop Chase, submit no second leg and reconcile terminal state.
- Amend/repost behavior remains bounded by TTL, minimum tick movement, mutation count and cooldown; cancel terminal state must be proven before repost.

## 4. Two-leg failure disposition

Each case has distinct semantics:

| Case | Required disposition |
|---|---|
| First leg explicitly failed with zero fill | Stop; submit no second leg and preserve the explicit failure. |
| First leg partially filled | Preserve actual fill and residual exposure; do not automatically submit the normal second leg. Use the pre-authorized idempotent risk-reduction path or accountable manual takeover. |
| Second leg explicitly rejected | Only the established idempotent risk-contraction workflow may reduce the proven first-leg exposure. No new business intent is inferred. |
| Second leg result unknown | Do not blindly roll back, retry or submit a duplicate intent. Query Runtime and Venue evidence until terminal state is proven or risk is manually owned. |
| Runtime or Terminal restarted | Rebuild state from persisted Journal plus Venue Order/Fill/Deal/Position identities before any write. Missing routes or in-memory state are not evidence of absence. |
| Venue query unavailable | Remain fail closed and read only; do not infer positions, balances, orders or completion. |

The final disposition must be one of: unfilled legs canceled with proof, filled exposure flattened through the established idempotent risk path, substitute hedge proven complete, or residual exposure assigned to a named operator under Kill Switch.

## 5. Kill Switch and escalation

- Any unexplained position, quantity mismatch, identity mismatch, private-stream fault, `result_unknown`, query unavailability or failed risk-reduction command activates the applicable Kill Switch and returns both write gates to false.
- A risk-reduction command that is not proven filled cannot be marked resolved.
- Accepted or unknown external orders are not claimed canceled without Venue evidence.
- Manual intervention records the subject, observed evidence, difference category, responsible owner, next action and decision time.

## 6. End-of-day reconciliation

Reconcile at least:

- Order;
- Fill and Deal;
- Position;
- Balance;
- Funding, Swap and Fee;
- FinancialFact;
- realized and unrealized PnL/NAV.

Every Difference receives a category, severity, responsible owner, evidence reference and disposition. Open or unexplained Differences prevent expansion and may require continued Kill Switch protection.

## 7. Forced reset

Before leaving the supervised window, prove all of the following:

- Platform Live Write = `false`;
- Runtime Live Write = `false`;
- automatic Exit Monitor = `false`;
- PostOnly Chase = `false`;
- temporary Account/Strategy/Symbol allowlists are cleared;
- temporary per-order and per-day limits are cleared or restored to safe defaults;
- every external pending order has a proven terminal state;
- every external position matches the Formal Position or has been explicitly transferred to accountable manual ownership;
- Runtime Journal, Platform facts and EOD reconciliation evidence are retained.

No operator may treat process exit, service restart or local database state as proof that external orders or positions are absent.
