# Live Acceptance Runbook

Status: active Platform 0.11.2 controlled-live operational contract.

This runbook governs controlled, instruction-bounded live acceptance. It does not authorize production rollout or Live Write activation. Any failed, unavailable or contradictory step immediately returns the system to read-only live mode and requires an accountable operator decision.

## 0.1 Read-only real-account onboarding prerequisites

Read-only onboarding is a prerequisite audit step. It does not authorize live
execution, controlled-live windows, funds transfer, `LiveTradingSession`
creation or any write action.

The responsible Owner must provide exact, already-installed configuration facts
before any credential-backed read-only verification:

- Bybit
  - the real UTA's Platform logical `accounts.id`
  - installed credential secret reference
  - whether the API key is read-only or has trade permission
  - IP allowlist status
  - `environment=live`
  - instrument mappings
  - symbol allowlist
  - category and settle coin
  - Runtime account allowlist entry
- MT5
  - Platform logical `accounts.id`
  - installed credential reference
  - terminal/login identity
  - instrument mapping
  - read-only readiness
  - whether trading is currently permitted

Same-UTA binding rules:

- Funding primary and the cross-spread Bybit leg must reference the same
  `accounts.id`.
- Account identity is proven only by the explicit logical account binding, never
  by display name, account code or API-key label.
- The first read-only verification uses one logical account ID and one
  credential reference.
- Do not create two logical Platform accounts that map to the same real UTA.

If the Owner has not yet installed the secret reference, stop at local
configuration audit only. Do not call any external account, venue, quote,
balance, order, fill, risk or funding endpoint.

## 0. Authorization unit

An Owner authorization is one complete, named business scenario, not one local
technical action. Its written scope must identify the responsible CEO, account,
strategy, symbols, each leg's maximum quantity, permitted execution policy and
absolute expiry. Within that scope the operator may complete the matching open,
authoritative order/fill/position verification, corresponding close,
reconciliation and forced reset without seeking a separate authorization for
each local call.

This reduces approval fragmentation only. It never replaces the independent
Platform and Runtime Live Write gates, API-key/live-session requirements, Kill
Switch, one-instruction/one-batch identity, idempotency, cumulative-fill and
quantity limits, `result_unknown` fail-closed handling, or reconciliation. A
scope change, expiry, identity mismatch, unknown external state or unavailable
venue evidence ends the scenario and requires a new Owner decision.

## 1. Release sequence

```text
只读实盘
→ 合约规格、账户风险、订单和成交历史核对
→ 影子对账
→ 指令限定数量 Market人工监督
→ 指令限定数量 FOK人工监督
→ TP/SL执行验收
→ PostOnly Chase专门监督验收
→ 失败处置与Kill Switch
→ 日终对账
→ 强制复位
```

Read-only onboarding always happens before this sequence. It only verifies
configuration, private-read readiness and observability contracts; it never
submits, cancels, transfers or changes venue state.

The sequence is strict. A later step cannot compensate for a failed earlier step. Repository CI, simulation results, an order ACK or an application response cannot replace venue evidence.

For Platform 0.11.1, the controlled execution order is Market in one direction, Market in the reverse direction, FOK, TP/SL, then PostOnly Chase. This explicit step gate controls where the shorthand sequence above is less specific; every later step remains blocked until its predecessor has evidence, reconciliation and forced reset.

## 2. Mandatory safety boundaries

- Platform Live Write and Runtime Live Write are independent gates; both remain disabled except inside an owner-authorized supervised window.
- Platform 0.11.1 permits one founder CEO/fund-manager to operate a founder-owned local test account under direct supervision. This is a narrow exception, not a precedent for client funds, multi-person operation, unattended trading, long-lived Live Write, production deployment, or expansion of funds, symbols or concurrency.
- Each window has a named single responsible operator and a single pre-authorized Account, Strategy, Symbol, direction, quantity and execution mode. It is manually unlocked for one execution batch, must be started within 10 minutes and has an absolute 30-minute expiry.
- Live and Simulation use different databases, Runtime Journals, Accounts and Credentials.
- Account, Strategy and Symbol use exact allowlists. Each CEO instruction fixes both leg quantities and creates at most one execution batch; cumulative external fills may not exceed those instruction quantities.
- ACK is not Fill. External terminal state and fill/deal evidence are authoritative for execution completion.
- `result_unknown` forbids blind retry, blind rollback and duplicate business intent.
- Query failure is unavailable evidence, never an empty position, zero balance, zero order or zero history result.
- External Order, Fill, Deal and Position identities must remain traceable to Platform and Runtime facts.
- Funds, quantity, symbols, concurrency and automation cannot expand before end-of-day reconciliation is complete.
- Fixed position, notional, daily-volume, batch-count and loss caps are not part of the founder-owned local test-account contract. This does not relax one-instruction/one-batch identity, instruction quantity ceilings, global one-active-execution serialization, allowlists, bounded chase, Kill Switch, reconciliation or forced read-only reset.
- Existing Platform and Runtime fixed-notional-cap code remains a controlled-live readiness blocker. It is retained unchanged in this rule-alignment slice for legacy compatibility and cannot be treated as owner-approved risk policy or readiness evidence; a separately authorized behavior change must align it before any Live Write window.
- A process restart, connection loss, `result_unknown`, identity mismatch, position mismatch or expiry automatically returns both Live Write gates to `false`.
- Credentials, private values and live evidence are not copied into source control, general logs or ordinary documentation.

## 3. Instruction-bounded execution-mode acceptance

The responsible CEO specifies both leg quantities before each authorized window. Runtime validates current contract multiplier, minimum and quantity step, and cumulative external fills remain bounded by the immutable instruction quantities.

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
- Initial local-test amend/repost settings are a 15-second total chase TTL, one-second evaluation cadence, at most five amend or cancel-repost mutations, and at least one tick of price change before mutation. These are owner-approved initial configuration values, not exchange facts or permanent production defaults; cancel terminal state must be proven before repost, and any pre-live change requires evidence and owner approval.

### Funding carry incremental hedge

Funding controlled-live is unavailable until Phase 2 implements and proves the
bounded PostOnly Chase plus authoritative, deduplicated incremental release.
The legacy two-market-leg endpoint is not acceptance evidence and must remain
fail closed for controlled-live funding during that gap.

- Funding carry opens and closes perpetual-first. Each newly proven, deduplicated perpetual cumulative-fill increment releases only its proportional Spot quantity rounded down to the current Spot quantity step.
- Quantization remainder stays explicit until later proven cumulative fill makes another full Spot step releasable. Perpetual and Spot cumulative fills never exceed their respective CEO instruction quantities.
- Every Spot release remains in the same execution batch and uses a deterministic child identity derived from the batch and cumulative released Spot quantity. Replayed `execId` values release nothing.
- Disconnect, sequence or identity mismatch, unknown order state, terminal-cancel ambiguity or `result_unknown` freezes new releases and retains reconciliation-required state. A cancel acknowledgement alone is not terminal evidence and cannot authorize repost.
- These incremental second-leg semantics apply only to funding carry. Cross-venue Market, FOK and PostOnly Chase retain their existing terminal-fill rules.

### Shared Bybit account concurrency

Cross-spread and funding carry may use the same real Bybit UTA, logical Platform Account and credential reference. Trading permission may be configured before a controlled-live window, but both Live Write gates remain false outside an authorized scenario.

- Concurrent writes are permitted only when the immutable plans use disjoint `account + category + symbol` resources and sufficient authoritative available balance remains after active reservations.
- The same `category + symbol` cannot be opened, chased or closed concurrently by different strategies until a reviewed strategy-position allocation mechanism exists.
- Orders, fills, fees and PnL retain Strategy/Instruction/Batch/Command identity. The UTA balance is shared account truth and must not be duplicated as separate strategy-owned cash.
- Internal capital transfer, unknown account identity, unavailable balance/margin evidence, account Kill Switch or an uncertainty whose resource scope cannot be proven blocks account writes.
- `result_unknown`, cancel ambiguity and residual exposure retain the affected resource and balance reservation. Completion alone does not release them without terminal external and reconciliation evidence.

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
- The responsible CEO/fund-manager may trigger Kill Switch alone. It must be triggered automatically or manually on `result_unknown`, duplicate-order risk, first/second-leg quantity mismatch, external/platform position mismatch, Private Stream or critical-query loss, unmatched order/fill/position identity, any hard-limit breach, or inability to prove an external order terminal.
- Release requires the responsible operator to manually verify external order status, actual positions, residual exposure, Runtime Journal and Platform records. Release never restores trading automatically: it only permits a new, separately authorized time-limited Live Write window.

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

## 6.1 Authorized step sequence and evidence

Read-only venue/account/order/fill/deal/position verification, Platform/Runtime/database/venue shadow reconciliation, automated tests and fault injection must pass before any Live Write window. Controlled-live steps require separate owner authorization and proceed strictly in this order: Market in one direction, Market in the reverse direction, FOK, TP/SL, then PostOnly Chase. A failed step blocks all later steps.

For every step retain the unlock and limits snapshot; operator, account, strategy, symbol and timestamps; pre-submit Bid/Ask, quote age and contract specification; request, correlation and idempotency identifiers; external Order, Fill, Deal and Position identities; acknowledgements, fills, fees and timestamps; before/after account, position, balance and PnL snapshots; Runtime Journal and Platform facts; shadow-reconciliation result; any Kill Switch or exception record; and proof of forced reset. Each step ends with venue-evidence review, end-of-day reconciliation and forced reset.

## 6.2 Read-only onboarding checklist

Before any separately authorized controlled-live step, confirm all of the
following in read-only mode:

- Runtime gateway capability is readable.
- Credential configured/operational state is readable without exposing the
  secret value.
- Bybit API-key readiness is readable.
- Instrument specifications are readable.
- Authoritative quote is readable.
- Balances are readable.
- Positions are readable.
- Open orders are readable.
- Order history is readable.
- Fill history is readable.
- Account risk is readable.
- Funding rate is readable.
- MT5 account/readiness is readable.
- Platform account binding is correct.
- `management-overview` returns all six strategies with current status.
- Reconciliation baseline is captured before any write window.
- Platform Live Write remains `false`.
- Runtime Live Write remains `false`.
- Funding controlled-live still returns `423` until separately authorized and
  fully ready.
- No approved `LiveTradingSession` exists.

Two states are valid:

- A. Owner has not installed the secret reference:
  - local configuration audit only;
  - no external request;
  - final receipt lists the exact missing Owner-provided items.
- B. Owner has installed the secret reference and later gives explicit read-only
  authorization:
  - only read endpoints may be called;
  - no submit/cancel/transfer;
  - no state-changing action on account, order, position or funds;
  - acceptance output remains redacted.

## 7. Forced reset

Before leaving the supervised window, prove all of the following:

- Platform Live Write = `false`;
- Runtime Live Write = `false`;
- automatic Exit Monitor = `false`;
- PostOnly Chase = `false`;
- temporary Account/Strategy/Symbol allowlists are cleared;
- the window's immutable instruction quantities and one-batch claim are retained with the evidence record;
- every external pending order has a proven terminal state;
- every external position matches the Formal Position or has been explicitly transferred to accountable manual ownership;
- Runtime Journal, Platform facts and EOD reconciliation evidence are retained.

No operator may treat process exit, service restart or local database state as proof that external orders or positions are absent.
