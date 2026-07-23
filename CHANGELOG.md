# Changelog

## Unreleased

### Controlled Bybit and MT5 live adapters — Phase 4C

- Replaced the planned Demo-adapter scope with controlled real-account integration because Bybit and MT5 simulation environments do not sufficiently reproduce live account, execution, Funding, Swap, and terminal behavior.
- Defined small-capital real-account testing with the venue or broker minimum order size as the primary operational acceptance path after read-only and shadow reconciliation; passing a simulated environment is not treated as final acceptance.
- Added a deterministic account router that maps each Platform Account to exactly one Bybit or MT5 live adapter and rejects ambiguous or missing routes.
- Added a second Runtime live-write gate, independent of the Platform live gate and Kill Switch, with `liveWriteEnabled=false` by default.
- Added Account, StrategyInstance, and Symbol allowlists plus per-order and per-day notional limits.
- Added persistent live order routes, deterministic external client identities, and atomic daily-notional claims in the Runtime Journal SQLite.
- Added Bybit V5 Unified Trading live queries for Orders, Executions, Positions, Wallet Balances, and Transaction Logs.
- Added controlled Bybit Submit/Cancel using a deterministic `orderLinkId`; synchronous order acknowledgement is no longer treated as a fill.
- Added Bybit Funding and Fee economic-event mappings.
- Added MT5 live queries for Orders, Deals, Positions, and AccountInfo through the official Python integration.
- Added controlled MT5 `order_check` and `order_send`, with Magic Number, deterministic Comment, Order Ticket, Deal Ticket, and Position Ticket traceability.
- Added MT5 Swap, Commission, and Fee economic-event mappings from external Deal fields.
- Added explicit configuration, request-rejection, unsupported-query, and result-unknown gateway error semantics.
- Added `/gateway/capabilities` without exposing secret values and `/venue/economic-events` for Funding, Swap, and Fee queries.
- Added `POST /api/v1/ops/live-economic-events/import` to idempotently ingest live Funding, Swap, and Fee into immutable FinancialFact; unmapped instruments are explicitly returned in `skippedExternalIds`.
- Preserved StrategyInstance identity across the Platform-to-Runtime TradeCommand boundary for Runtime strategy allowlists.
- Added offline Provider Contract Tests for Bybit and MT5 mappings, live-write gates, allowlists, notional limits, external identities, and economic-event imports.
- Added `execution-runtime/.env.live.example` with write gates closed, empty allowlists, zero notional limits, and credential references only.
- Added `scripts/live-readonly-preflight.ps1` to verify Live Environment, Gateway, write-gate state, credential completeness, and Venue Readiness without submitting or canceling orders.
- Added `docs/operations/V6-小资金实盘验收手册.md` covering read-only verification, shadow reconciliation, minimum-size order/cancel/fill testing, Kill Switch drills, end-of-day checks, and mandatory gate reset.
- Expanded Platform CI strict gates for all Phase 4C Runtime and Backend files and tests.
- Added `docs/planning/V6-Phase4C-受控实盘适配器.md` and `docs/technical/LIVE_VENUE_ADAPTERS.md`.
- Synchronized Issue #18, Issue #12, README, START-HERE, API Specification, Release Gate, overall V6 plan, and this Changelog.
- Kept operational approval separate from engineering acceptance: real credentials, read-only verification, continuous reconciliation, minimum-size live writes, and Kill Switch drills remain manual acceptance items.

### Venue query, fact ingestion, and reconciliation differences — Phase 4B

- Extended the ExecutionGateway contract with external Order, Fill, Position, Balance, and Cancel Order operations while keeping read queries separate from execution commands.
- Added Runtime APIs for Order lookup by Platform or external ID, Fill listing, Position listing, Balance listing, and idempotent cancellation.
- Added a persistent deterministic Fake Venue store in the Runtime Journal SQLite for Orders, Fills, Positions, Balances, and Cancel commands.
- Derived stable Fake external identities from Platform Order IDs so repeated commands, queries, and Runtime restarts do not create duplicate external facts.
- Added explicit unsupported query and cancel behavior for the Bybit/MT5 shell until external adapters are delivered in Phase 4C.
- Added `POST /api/v1/trading/orders/{orderId}/venue-reconcile`: Runtime Journal is checked first, then the external Order and Fills are queried without resubmitting the original order.
- Imported external Order, Fill, Position, and Balance snapshots into the immutable Phase 3 FinancialFact layer.
- Reused External Fill ID as the local Fill event identity so repeated Venue reconciliation does not duplicate execution or accounting projections.
- Added account-level Venue Reconciliation Runs with idempotency keys, source, snapshot counts, fact counts, difference counts, and explicit completion status.
- Added auditable Reconciliation Differences for missing local/external state, quantity, price, currency, and status mismatches.
- Added immutable first-resolution semantics for Differences with `open`, `resolved`, and `accepted` statuses plus actor, reason, and time.
- Added audit events for Venue Order reconciliation, account reconciliation completion, and Difference resolution.
- Added Runtime tests for persistent Fake Venue state across restarts and idempotent terminal-order cancellation.
- Added Backend tests for external recovery of `result_unknown`, non-duplicating fact replay, Formal Position reconstruction, account snapshot import, Difference resolution, and reconciliation payload conflicts.
- Expanded Platform CI strict gates and retained Runtime/Backend pytest diagnostics as short-lived artifacts.
- Added `docs/planning/V6-Phase4B-外部查询与对账差异.md` and `docs/technical/VENUE_RECONCILIATION.md`.
- Synchronized the V6 plan, API Specification, Release Gate, README, START-HERE, Issue #16, PR #17, and this Changelog.

### Execution risk controls and Kill Switch — Phase 4A

- Added global, strategy, and account Kill Switches with idempotent writes, payload-conflict detection, versioning, actor/reason metadata, and AuditEvent records.
- Added Kill Switch checks before ExecutionBatch claim and before every Batch Leg, returning `423 Locked` before new TradeCommand or Runtime side effects.
- Added per-Strategy execution-risk policies for maximum leg delay, maximum residual notional, and failure action.
- Added immutable per-Batch risk-policy snapshots so later policy changes do not rewrite historical execution boundaries.
- Added Batch risk states: `clear`, `residual_exposure`, `disposition_in_progress`, `resolved`, and `escalated`.
- Added first-fill and last-leg timestamps and enforced maximum leg delay before the next Leg is submitted.
- Added residual-exposure calculation using Fill Quantity, Fill Price, Contract Multiplier, side, and Settlement Currency.
- Added conservative `MIXED / incomplete` handling for multi-currency exposure without a risk FX snapshot.
- Changed normal Batch completion so `hedged` requires both Legs completed and a complete zero-residual risk result.
- Added idempotent RiskActions: `hold_and_escalate`, `flatten_filled_legs`, `cancel_open_legs`, and `substitute_hedge`.
- Routed automatic flattening and substitute hedges through authoritative TradeCommand rather than direct Order insertion.
- Added golden tests for pre-claim Kill Switch blocking, residual-notional limits, automatic flattening, Position returning to zero, RiskAction replay/conflict, and leg-deadline enforcement.
- Added `docs/planning/V6-Phase4A-执行风险与Kill-Switch.md` and `docs/technical/EXECUTION_RISK_CONTROLS.md`.

### Immutable financial facts and formal accounting — Phase 3

- Added immutable `financial_facts` with client idempotency keys, external fact identities, normalized payload hashes, event time, source metadata, and explicit data quality.
- Rejected reuse of a FinancialFact identity with a different normalized payload using `409 Conflict`.
- Derived Trade Fact settlement currency, quantity unit, and contract multiplier from the backend Instrument Catalog rather than accepting client overrides.
- Added rebuildable `formal_positions` and `formal_pnl_results` projections.
- Separated Trading, Funding, Swap, Fee, FX, and Total PnL.
- Included Contract Multiplier and explicit FX conversion in the formal Trading PnL boundary.
- Added one-valuation-time multi-account Formal NAV with explicit missing-account disclosure.
- Added FinancialFact ingestion/listing, formal projection rebuild, formal Position/PnL, and formal NAV APIs.
- Added audit events and golden tests for facts, conflicts, PnL components, rebuild, missing FX, and NAV completeness.
- Completed Platform CI `#127 / run 29993137286` and merged through PR #9.

### Product surface cleanup

- Removed the explanatory redirect paragraph from the login card so the page contains only identity, authentication, and registration actions required by the user.
- Removed the unused login subhead styles and preserved the existing redirect behavior in code.
