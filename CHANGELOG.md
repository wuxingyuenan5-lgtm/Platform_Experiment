# Changelog

## Unreleased

### Production authentication, RBAC, and two-person live sessions — Production Gate 5A/5B

- Added live-environment Bearer authentication with SHA-256 credential matching; raw tokens are not stored in source, database rows, logs, audit details, or responses.
- Rejected anonymous, invalid, inactive, and development-mode authentication in the Live environment while retaining an explicit non-Live development identity for Simulation and CI.
- Added default-deny RBAC for viewer, researcher, trader, risk_officer, operations, and admin roles.
- Bound actor/reviewer fields to the authenticated Principal so a request body cannot impersonate another user.
- Added request identity metadata and security rejection handling without exposing credential values.
- Added idempotent `LiveTradingSession` requests scoped to StrategyInstance, Account, Symbol, Side, Order Type, time window, per-order notional, daily notional, read-only evidence, and immutable payload hash.
- Required a trader/admin Applicant and a different risk_officer/admin Approver; admin self-approval is explicitly rejected.
- Blocked session approval when platform absolute limits are missing/exceeded, a Kill Switch is enabled, open/accepted reconciliation differences exist, an approved session overlaps, or the required EOD/scale gate is not clean.
- Required every Live Command to claim exactly one active approved session before inserting the Order or calling Runtime.
- Added Command-ID idempotency and payload-conflict detection for session claims.
- Added SQLite `BEGIN IMMEDIATE` claim serialization so concurrent commands cannot jointly exceed the approved daily notional.
- Added authentication, RBAC, actor binding, two-person approval, no-session rejection, Kill Switch, absolute-limit, replay, and concurrent-claim golden tests.
- Added repository Secret Scan for private keys, common platform tokens, high-entropy literal secrets, and unreviewed tracked `.env*` files.
- Added an independent diagnosable Secret Scan workflow and a blocking Repository Safety job in Platform CI.
- Reviewed tracked `admin-risk/.env*` files as public browser `VITE_*` manifests; their contents remain subject to known-token and high-entropy scanning.
- Added `docs/planning/V6-Production-Gate-身份权限与实盘会话.md` and `docs/technical/AUTH_RBAC_LIVE_SESSIONS.md`.
- Synchronized Issue #22, PR #23, README, START-HERE, API Specification, Release Gate, overall V6 plan, CI, and this Changelog.
- Kept Platform and Runtime Live Write disabled by default; engineering completion does not configure real credentials or authorize real-money writes.
- Deferred production SecretProvider/rotation, alerting, backup, restore drills, and user-management UI to Production Gate 5C/5D.

### Live end-of-day reconciliation and scale gates — Phase 4D

- Added idempotent EOD reconciliation reports keyed by business date, StrategyInstance, Account, IANA timezone, valuation time, and request payload hash.
- Added explicit `complete`, `completed_with_differences`, `partial`, and `failed` report states; external query failures can no longer appear as zero-difference completion.
- Added owner, due time, completion time, and dynamic SLA states (`pending`, `met`, `breached`, `overdue`).
- Added daily orchestration for Platform Order Venue Reconcile, external Position/Balance import, live Funding/Swap/Fee import, Formal Position/PnL rebuild, and point-in-time Formal NAV.
- Added business-day order selection plus older nonterminal orders so unresolved live orders remain in the reconciliation boundary.
- Added historical open and accepted Reconciliation Difference aggregation; both states block live-scale review.
- Added explicit counts for incomplete Formal PnL, skipped external events, missing NAV accounts, open/resolved/accepted differences, and orchestration errors.
- Added immutable human review decisions: `approved_same_limits`, `needs_remediation`, and `rejected`.
- Restricted clean-report approval to the existing small-capital limits; no EOD action raises limits or enables live order writes.
- Added `POST/GET /api/v1/ops/eod-reconciliation/reports` and immutable review endpoints.
- Added `scripts/run-live-eod-reconciliation.ps1`, which performs read-only Runtime preflight before running the live EOD batch and saves the resulting JSON report.
- Added clean, blocked, historical accepted-difference, order-window, idempotency-conflict, immutable-review, missing-account, skipped-event, and external-failure golden tests.
- Added `docs/planning/V6-Phase4D-实盘日终对账与运营门禁.md` and `docs/technical/EOD_RECONCILIATION.md`.
- Synchronized Issue #20, PR #21, README, START-HERE, API Specification, Release Gate, overall V6 plan, CI, and this Changelog.
- Kept real-account operational acceptance separate from engineering acceptance: minimum-size live writes, multiple clean live EOD cycles, Kill Switch drills, credential governance, and human approval remain required.

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
- Completed Platform CI `#294 / run 30016178285` and merged through PR #19 at `0badab7522ce5b5d11c6ba47cf85c949c68958ca`.
- Kept operational approval separate from engineering acceptance: real credentials, read-only verification, continuous reconciliation, minimum-size live writes, and Kill Switch drills remain manual acceptance items.

### Venue query, fact ingestion, and reconciliation differences — Phase 4B

- Extended the ExecutionGateway contract with external Order, Fill, Position, Balance, and Cancel Order operations while keeping read queries separate from execution commands.
- Added Runtime APIs for Order lookup by Platform or external ID, Fill listing, Position listing, Balance listing, and idempotent cancellation.
- Added a persistent deterministic Fake Venue store in the Runtime Journal SQLite for Orders, Fills, Positions, Balances, and Cancel commands.
- Derived stable Fake external identities from Platform Order IDs so repeated commands, queries, and Runtime restarts do not create duplicate external facts.
- Added `POST /api/v1/trading/orders/{orderId}/venue-reconcile`: Runtime Journal is checked first, then the external Order and Fills are queried without resubmitting the original order.
- Imported external Order, Fill, Position, and Balance snapshots into the immutable Phase 3 FinancialFact layer.
- Reused External Fill ID as the local Fill event identity so repeated Venue reconciliation does not duplicate execution or accounting projections.
- Added account-level Venue Reconciliation Runs and auditable Reconciliation Differences.
- Added immutable first-resolution semantics for Differences with `open`, `resolved`, and `accepted` statuses.
- Added tests for external recovery, non-duplicating fact replay, Formal Position reconstruction, snapshot import, Difference resolution, and payload conflicts.
- Added `docs/planning/V6-Phase4B-外部查询与对账差异.md` and `docs/technical/VENUE_RECONCILIATION.md`.

### Execution risk controls and Kill Switch — Phase 4A

- Added global, strategy, and account Kill Switches with idempotent writes, payload-conflict detection, versioning, actor/reason metadata, and AuditEvent records.
- Added Kill Switch checks before ExecutionBatch claim and before every Batch Leg.
- Added per-Strategy execution-risk policies for maximum leg delay, maximum residual notional, and failure action.
- Added immutable per-Batch risk-policy snapshots and Batch risk states.
- Added idempotent RiskActions: `hold_and_escalate`, `flatten_filled_legs`, `cancel_open_legs`, and `substitute_hedge`.
- Routed automatic flattening and substitute hedges through authoritative TradeCommand.
- Added execution-risk golden tests and synchronized technical documentation.

### Immutable financial facts and formal accounting — Phase 3

- Added immutable FinancialFact with dual identities, payload hashes, Catalog-derived units and multipliers, explicit FX, and data quality.
- Added rebuildable Formal Position/PnL and one-valuation-time multi-account Formal NAV.
- Separated Trading, Funding, Swap, Fee, FX, and Total PnL.
- Added audit events and golden tests.