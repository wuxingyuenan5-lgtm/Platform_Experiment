# Live Acceptance Runbook

Status: active trading validation and operator evidence procedure; normal authorization is owned by AUTHORIZATION.md.

Owner changed the product to normal trading on 2026-09-09. Normal CEO trading does not require acceptance sessions, staged mode approval, temporary windows, small-size/notional caps or temporary strategy/symbol lists. The validation cases below are operator evidence procedures, not extra permission gates. This document itself does not authorize a real order, closing an existing position, activating Live Write, or deployment. Execution uncertainty still stops further side effects and requires reconciliation.

Before explicitly activating both live gates, inspect existing pending instructions, orders and active TP/SL plans: activation can resume their external side effects. Preserve existing positions and plans unless the Owner authorizes their disposition. MT5 must allow algorithmic trading and external Python API trading; Platform cannot override broker or terminal permissions.

## Automated test isolation

Automated tests must not inherit the business Runtime endpoint or reach live venues. A temporary Platform database or a `simulation` strategy label does not establish isolation when its account bindings still point to live accounts. Platform API tests default to an unavailable loopback Runtime and block socket connections to the business service ports and external networks. Integration tests use their own ephemeral loopback Runtime; tests of production venue adapters replace SDK I/O and independently deny external network access. Concurrency tests must explicitly configure their transport outcome.

The default Platform test database is also assigned to a per-test temporary path, including tests that omit an explicit database fixture. Restoring incident records requires an online business backup, offline rehearsal, exact native identity/quantity/price verification, one atomic insertion of the selected original records, and a retained recovery audit. Do not copy test accounts, credentials, reservations or policies into the business database. Restored opening records keep their original caller and failure/incident provenance; recovery is not retroactive authorization for the opening trade.

If a test reaches a business service, stop the test, retain the original test database and native order/fill evidence, and disclose the effect. Further real disposition requires operation-specific Owner authorization; test cleanup must not silently submit offsetting trades or rewrite the original facts.

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
- In a multi-account Bybit Runtime, every private-read path must carry the
  explicit logical `accountId` all the way to the resolved client. A read that
  falls back to a single-account default is a contract failure.

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

Market in both directions, FOK, TP/SL and PostOnly Chase remain distinct validation cases. Their earlier staged acceptance order is historical and does not gate normal trading.

## 2. Normal trading safety boundaries

- CEO browser login and CSRF authorize Cross/Funding commands within active `trade_and_read` account bindings. Technical lead, employee/member, development fallback and API-Key admin do not automatically gain CEO trade authority.
- Platform and Runtime Live Write remain independent, default-off operational controls. Starting with the explicit `-EnableLiveWrite` operator flag enables normal trading; it no longer enables founder-demo self-approval.
- Runtime writable-account configuration remains authoritative; monitor accounts remain read-only. Temporary Strategy/Symbol acceptance lists and fixed-size/notional/daily/position-count caps no longer apply.
- One instruction creates at most one batch; cumulative external fills may not exceed its quantities. Resource serialization, bounded chase, Kill Switch and reconciliation remain.
- ACK is not Fill. Unknown outcomes prohibit blind retry, duplicate intent and blind rollback. Missing reads are unavailable evidence, never zero balances or empty positions.
- MT5 account login, automated-trade permission, terminal algorithmic-trading permission, Python API permission and native lot specifications must all pass.
- Opening or closing uses actual venue balances/margin, quantity precision and applicable order constraints. A code test never authorizes an external write.

## 3. Instruction-bounded execution-mode acceptance

The responsible CEO specifies the instruction quantities before submission; the frozen plan owns both leg quantities. Runtime validates current contract multiplier, minimum and quantity step, and cumulative external fills remain bounded by the immutable instruction quantities.

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

- Validate exit evaluation with isolated quotes and a stubbed execution boundary before enabling the monitor; real activation still requires explicit authorization.
- TP and SL retain their own execution mode and limit strategy but execute the same controlled Close action.
- Partial fill, post-submit timeout or unknown result does not release the Close claim.
- No limit path silently falls back to Market or another strategy.

### PostOnly Chase

- PostOnly Chase uses the normal live gates; the former acceptance-only enable flag is retired. Its hard limit, private stream health, finite TTL and mutation count still apply.
- Private order/execution events are the primary state source; REST is bounded reconciliation evidence.
- Only deduplicated cumulative fill exactly equal to requested quantity releases the second leg.
- Partial fill, private-stream disconnect, sequence or identity anomaly, and cancel/fill race fail closed: stop Chase, submit no second leg and reconcile terminal state.
- Initial local-test amend/repost settings are a 15-second total chase TTL, one-second evaluation cadence, at most five amend or cancel-repost mutations, and at least one tick of price change before mutation. These are owner-approved initial configuration values, not exchange facts or permanent production defaults; cancel terminal state must be proven before repost, and any pre-live change requires evidence and owner approval.

### Funding carry incremental hedge

Funding uses the normal authorized trading gates and the persisted perpetual-first
instruction pipeline. Market, explicit-price FOK and bounded PostOnly Chase are
separate validation cases for both open and partial/full close. Market submits once;
FOK requires terminal exact full fill before Spot release. A confirmed zero-fill
terminal order releases reservations only after all order/fill/release evidence is
checked. Partial or unknown FOK results require reconciliation and never replay.
The legacy two-market-leg endpoint is not acceptance evidence.

- Funding quotes and plan creation must resolve the same account binding: live primary or simulation local_test, with matching account environment. Validate the native Spot/Perpetual contract identities, quantity steps, minimum quantities and price ticks before an Owner submits a new instruction. Repairing stale instance mode never changes or replays an existing immutable rejected plan.
- A persisted rejection displays as failed and leaves active holdings; timeout recovery queries the original idempotency key only. Verify both cases in the UI without placing an additional live test order.

- Funding carry opens and closes perpetual-first. Each newly proven, deduplicated perpetual cumulative-fill increment releases only its proportional Spot quantity rounded down to the current Spot quantity step.
- Quantization remainder stays explicit until later proven cumulative fill makes another full Spot step releasable. Perpetual and Spot cumulative fills never exceed their respective CEO instruction quantities.
- Every Spot release remains in the same execution batch and uses a deterministic child identity derived from the batch and cumulative released Spot quantity. Replayed `execId` values release nothing.
- Disconnect, sequence or identity mismatch, unknown order state, terminal-cancel ambiguity or `result_unknown` freezes new releases and retains reconciliation-required state. A cancel acknowledgement alone is not terminal evidence and cannot authorize repost.
- These incremental second-leg semantics apply only to funding carry. Cross-venue Market, FOK and PostOnly Chase retain their existing terminal-fill rules.
- Platform's Funding monitor advances only accepted/executing/reconciling persisted instructions through their existing immutable plan. Browser disconnect does not stop a proven hedge's completion; unknown results and manual-intervention states never enter automatic replay. Reconciliation checks all child Order/Fill identities and cumulative quantities, then account positions. Bybit Spot is checked against actual base-coin cash after native fees, not a nonexistent Spot derivatives position.
- CEO partial/full close reserves the original group's remaining quantity, uses actual canonical fills for closed quantity, and floors net Spot cash to the venue step. Missing fee evidence or native available cash blocks new closing instructions. Stale live balance evidence (over 90 seconds) also blocks admission.
- Declaring concurrent Funding closes validates group capacity inside the same SQLite write transaction; their combined reserved quantity cannot exceed proven open fills. Admission rejection before a batch is claimed terminates that intent, so later background ticks cannot unexpectedly dispatch it after balances or claims change. A declared Spot child without a persisted command can resume using its original deterministic identity; any existing command is read idempotently, never replayed as a new order.

### Shared Bybit account concurrency

Cross-spread and funding carry may use the same real Bybit UTA, logical Platform Account and credential reference. Normal execution follows the existing authorized account bindings and both Live Write gates; test success does not activate either gate.

- Before a Batch may transition to `executing` or emit any `TradeCommand`, the complete resource claims and balance reservations required by its immutable plan must be acquired atomically in one transaction. Conflict, incomplete replay or insufficient balance rolls back the whole acquisition and emits no command.
- Concurrent writes are permitted only when the immutable plans use disjoint `account + category + symbol` resources and sufficient authoritative available balance remains after active reservations.
- The same `category + symbol` cannot be opened, chased or closed concurrently by different strategies until a reviewed strategy-position allocation mechanism exists.
- Orders, fills, fees and PnL retain Strategy/Instruction/Batch/Command identity. The UTA balance is shared account truth and must not be duplicated as separate strategy-owned cash.
- Internal capital transfer, unknown account identity, unavailable balance/margin evidence, account Kill Switch or an uncertainty whose resource scope cannot be proven blocks account writes.
- `result_unknown`, `manual_intervention`, cancel ambiguity, residual exposure and Funding `reconciling` retain the affected resource and balance reservation. They are released only after authoritative reconciliation completes or an explicit, accountable safe terminal disposition is recorded; a Batch state change alone is insufficient.

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
- Release requires the responsible operator to manually verify external order status, actual positions, residual exposure, Runtime Journal and Platform records. Release never restores trading automatically; further actions remain subject to the existing normal authorization and live gates.

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

Use read-only venue/account/order/fill/deal/position verification, reconciliation and isolated fault tests for the relevant acceptance claim. Market, reverse direction, FOK, TP/SL and PostOnly Chase are independent evidence cases, not a mandatory authorization sequence for normal CEO trading. A failed case remains unverified and any affected live execution must respect the existing risk boundary.

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
- Each MT5 logical account resolves to its own fixed Terminal/Worker and proves
  the configured Terminal Path, Login and Server. Shared-session account
  switching or restore-to-primary behavior is prohibited; see
  [Venue Adapter Contract](../contracts/VENUE_ADAPTERS.md).
- Platform account binding is correct.
- `management-overview` returns all six strategies with current status.
- Capture a reconciliation baseline before an authorized live validation.
- Platform Live Write remains `false`.
- Runtime Live Write remains `false`.
- Runtime `/status` must report `capabilities.liveWriteEnabled=false` before
  any credential-backed read-only verification and after every verification.
- The local startup path must keep Runtime, Platform API and Platform Web
  running independently of transient test processes. `scripts/dev-platform.ps1`
  is the authority for start/status/stop/restart, persistent PID ownership and
  login smoke verification. Cold startup keeps both Live Write gates disabled;
  `-EnableLiveWrite` enables explicitly Owner-authorized trading and
  `-EnableLiveWrite:$false` explicitly disables it. Without an explicit flag,
  start/restart/status read both running project backends and preserve their
  matching mode. Partial, unreadable, foreign or inconsistent backend state
  fails before any service is stopped. Saved process records establish process
  ownership only; they never confer live permission.
  Both Python services must report an active project virtual
  environment before the launcher accepts them as healthy.
- Lifecycle state JSON is read explicitly as UTF-8, including under Windows
  PowerShell 5 with a non-ASCII repository path. A malformed or mismatched state
  file must fail explicitly instead of silently reusing old processes during
  restart. After maintenance, verify new process IDs/start times and the changed
  API behavior; healthy endpoints alone do not prove that fixes were loaded.
  The `status-platform.ps1` and `stop-platform.ps1` shortcuts delegate to this
  same lifecycle owner; they must not maintain another process-state schema.
- The operator wants both MT5 terminals to run hidden in the background while
  algorithmic trading continues, matching the existing monitoring terminal.
  Do not bring them to the foreground for routine reads or service maintenance.
  A necessary interactive settings adjustment must end by restoring hidden
  background operation; making the terminal accessible for that adjustment
  does not change the operator's normal visibility preference.
  Fixed-account workers must pass the configured absolute terminal path and
  portable mode once to the MT5 SDK; the SDK owns the single launch/connect
  attempt. Runtime must not pre-launch the same terminal with `Popen` before
  calling the SDK, because recovery then creates duplicate-start attempts and
  `terminal process already started` noise. After successful initialization,
  restore hidden top-level windows for the configured terminal, including
  reconnection to an existing process, because MT5 can restore its saved window
  layout during startup.
  Initial connection and read-only IPC recovery share this startup path. Match
  the executable's absolute path and preserve its configured portable mode.
  The worker checks visibility at its one-second IPC polling boundary and hides
  reappearing windows only for processes matching the configured absolute path.
  Visibility maintenance does not reconnect, switch accounts or change trading permissions.
  The two configured fixed-account terminals keep MT5 terminal sounds muted in
  their local terminal configuration. This is an operator-notification preference
  only and must not change account, trading, connection or visibility behavior.
- A fixed-account MT5 worker reuses an already authenticated matching Login/Server
  instead of issuing another login during startup. Identity checks continue on
  subsequent calls. Account/profile-change auto-disable protections remain enabled;
  the platform must not force the Algorithmic Trading switch back on after a
  deliberate operator shutdown.
  Before accepting a dedicated portable Terminal, confirm its own data directory
  contains the broker's trade-server settings and verify a connected read-only
  snapshot against the intended Login, Server and Company. The terminal executable
  brand does not select the broker; a new portable data directory can otherwise
  remain on MetaQuotes-Demo even when the Runtime supplies a live Server name.
- Restoring existing Cross TP/SL requires both live gates and the local
  `VG_CROSS_SPREAD_EXIT_MONITOR_ENABLED=true` setting. Verify the monitor startup
  log, fresh executable quotes and the unchanged authorized plan thresholds;
  changing a flag alone does not prove that the monitor is running.
- Funding checks normal CEO authority, trading bindings, live gates and execution readiness.
- Legacy `LiveTradingSession` records do not participate in normal trading admission.
- Browser refresh/logout and backend interruption are separate cases. Follow the
  [Cross execution contract](../contracts/CROSS_SPREAD_EXECUTION.md) for saved
  TP/SL lifetime and outage limits. API restart must reuse the same database.
  Existing-account startup smoke uses an invalid probe, not a new CEO login.
  Prefer the existing browser session for read-only verification; repeated
  independent test logins consume the five-session allowance. An isolated
  authenticated verification must revoke only its own test session when finished.
  Never revoke the operator session or change expiry limits to make a check pass.

Funding page read-only execution context requirements:

- Funding and Cross share the same logical Bybit UTA binding
  (`bybit-live-main`).
- Funding execution context must read spot/perpetual quotes and contract
  specifications through explicit market scope (`crypto_spot/spot`,
  `crypto_perp/linear`) and expose the shared reservation summary.
- The Funding page may auto-poll only non-terminal instruction states; it must
  stop automatic progression on `result_unknown` or `manual_intervention`, keep
  read-only recovery identity, and never auto-resubmit.
- Funding close availability must use authoritative cumulative close fills for
  both legs. Requested close quantity is reservation only and cannot be shown as
  already closed.
- A fully closed Funding group moves to history only when authoritative closed
  quantity reaches hedged quantity and no pending or uncertain close
  reservation remains.

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

## 7. Operator-requested shutdown or isolated validation closeout

Normal trading has no automatic acceptance-window expiry or after-each-batch reset. When the Owner requests shutdown or the end of an isolated live validation, verify:

- Platform Live Write = `false`;
- Runtime Live Write = `false`;
- automatic Exit Monitor = `false`;
- no new PostOnly writes can pass the closed live gates;
- normal account permission configuration is preserved;
- the validation's immutable instruction quantities and one-batch claim are retained with the evidence record;
- every external pending order has a proven terminal state;
- every external position matches the Formal Position or has been explicitly transferred to accountable manual ownership;
- Runtime Journal, Platform facts and EOD reconciliation evidence are retained.

No operator may treat process exit, service restart or local database state as proof that external orders or positions are absent.

### Service update and clock checks

Before a Cross Chase service update, back up both SQLite databases and apply new schema changes as append-only migrations. Migration 26 retains its original adverse-spread columns; migration 27 adds terminal-fill evidence. Restart managed services with their explicit intended trading mode, then verify HTTP health, monitor health, native account reads and both legs of the executable snapshot. A live-write enable also resumes eligible persisted exit plans; review their actual quantities and thresholds before obtaining operation-specific authorization.

Bybit retCode 10002 with a timestamp ahead of server time is not fixed by increasing `recv_window`. Prefer a synchronized host clock; with `VG_RUNTIME_BYBIT_TIMESTAMP_OFFSET_MS=0`, Runtime calibrates against Bybit server time using a conservative post-response sample and refreshes that offset during long-running processes. A non-zero override is an explicit fixed offset and disables automatic refresh; it must only be used with current evidence. Account snapshots for multiple Bybit accounts are serialized inside the adapter so concurrent history reads do not amplify venue or signing contention. MT5 source clock preservation and independent tick-advancement evidence are defined in the account observability contract.
