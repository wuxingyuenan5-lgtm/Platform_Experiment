# Architecture Ownership Catalog

This document is the canonical human-readable catalog of major code ownership boundaries. It records current module authority, not implementation history. `docs/codex/current-state.md` records current operating truth; task packets and pull requests record change progress.

## Reading rules

- One responsibility has one authoritative implementation.
- Compatibility modules may explicitly re-export an owner but may not redefine or monkey-patch it.
- A structural refactor must preserve behavior and update this catalog in the same pull request.
- Detailed protocols remain in `docs/technical/`, `docs/contracts/` and `docs/database/`.

## Platform composition and API contracts

| Boundary | Authoritative owner | Responsibility | Must not own |
|---|---|---|---|
| Platform composition root | `platform-backend/app/main.py` | Router and middleware assembly | Domain rules, calculations, runtime patching |
| Execution API DTOs | `platform-backend/app/execution_schemas.py` | Public execution-domain request/response models | Trading execution or persistence |
| Execution compatibility DTO exports | `platform-backend/app/schemas.py` | Explicit aliases to execution DTO owners | Duplicate DTO definitions |
| Platform–Runtime contracts | `platform-backend/app/runtime_contracts.py`, `execution-runtime/app/runtime_contracts.py`, `docs/contracts/runtime-v1.json` | Versioned command/event models and executable field snapshot | Silent incompatible V1 changes |
| Cross-spread lifecycle DTOs | `platform-backend/app/cross_spread_exit_schemas.py` | Market-open, market-close, normalized synthetic-intent, exit-plan and evaluation request/response models | Threshold policy, SQL or venue execution |
| Cross-spread observability DTOs | `platform-backend/app/cross_spread_observability_schemas.py` | Read-only aggregate status, section-state and venue evidence response models | Runtime HTTP, venue mapping or execution decisions |

## Trading and formal accounting

| Boundary | Authoritative owner | Responsibility | Must not own |
|---|---|---|---|
| Platform order submission orchestration | `platform-backend/app/trade_command_execution.py` | Single local Order creation, Safety enforcement, legacy/V1 Runtime dispatch, unknown-result handling and Event handoff | Event projection, reconciliation or formal accounting |
| Venue order execution intent | `platform-backend/app/order_execution_intents.py` | Idempotent reduce-only and venue-position target lookup for a TradeCommand | Batch sequencing, venue SDK calls or exit-threshold policy |
| Cross-spread synthetic order intent | `platform-backend/app/cross_spread_order_intent.py` | Authoritative four business actions, Market/Limit execution type, trigger reason and deterministic existing-Market-command mapping | Venue submission, persistence, quote formulas or exit-plan claims |
| Cross-spread market command and live sizing | `platform-backend/app/cross_spread.py` | Nominal spread command mapping, live venue specification validation, exact ounce-to-lot sizing and deterministic Bybit rollback intent | Venue SDK calls, exit-plan SQL or automatic monitor loops |
| Cross-spread live read transport | `platform-backend/app/cross_spread_live_read_client.py` | Configured Runtime transport and validated Instrument, Position, Account Risk and paged Order/Fill reads | FastAPI routes, SQL, venue SDKs or execution decisions |
| Cross-spread observability service | `platform-backend/app/cross_spread_observability_service.py` | Independent section reads, partial/unavailable semantics and two-venue read-only aggregation | Venue SDKs, order submission, SQL or secret access |
| Cross-spread observability routes | `platform-backend/app/cross_spread_observability_routes.py` | Bounded read-only history query parameters and aggregate API routing | Venue mapping, execution or persistence |
| Cross-spread exit threshold policy | `platform-backend/app/cross_spread_exit_policy.py` | Pure executable-close-spread selection and TP/SL inequality decisions | SQL, HTTP, background tasks or order submission |
| Cross-spread exit-plan persistence | `platform-backend/app/cross_spread_exit_repository.py` | Exact-Decimal fill summary, exit-plan SQL, row mapping, atomic trigger claims and unresolved-lifecycle counts | Venue HTTP, threshold formulas, background loops or routes |
| Cross-spread Market safety helpers | `platform-backend/app/cross_spread_exit_service.py` | Existing admission, external-position verification, hedged-open plan creation, definitive-failure rollback coordination, MT5 ticket mapping and flat-position verification reused without semantic change | New Limit policy, public synthetic-intent ownership or venue SDKs |
| Cross-spread synthetic lifecycle service | `platform-backend/app/cross_spread_synthetic_service.py` | Public Market open/manual-close/TP-SL-close orchestration through normalized intent, existing Market-command mapping and additive intent response metadata | Direct SQL, venue SDKs, Limit submission or replacement of Market safety helpers |
| Cross-spread lifecycle routes | `platform-backend/app/cross_spread_exit_routes.py` | API routing and disabled-by-default monitor lifespan through the synthetic lifecycle service | SQL, threshold formulas or venue execution logic |
| EOD Reconciliation public DTOs | `platform-backend/app/eod_reconciliation_schemas.py` | EOD report/review request-response models and public status types | DDL, SQL, report orchestration, review policy or routes |
| EOD report and review policy | `platform-backend/app/eod_reconciliation_policy.py` | Pure report status, scale-gate, historical-Difference and immutable-review decisions | FastAPI, database/repository access, HTTP or cross-domain orchestration |
| EOD Reconciliation persistence | `platform-backend/app/eod_reconciliation_repository.py` | EOD report DDL, direct SQL, row mapping, report identity, review transactions and policy persistence reads/writes | FastAPI, cross-domain orchestration, status formulas or routes |
| EOD Reconciliation Service | `platform-backend/app/eod_reconciliation_service.py` | Report creation/read/list/review sequencing, cross-domain coordination, partial-failure capture and explicit service failures | FastAPI/APIRouter/Query, direct SQL/DDL, duplicate Policy decisions or routes |
| EOD Reconciliation facade | `platform-backend/app/eod_reconciliation.py` | Per-call dependency wiring, compatibility delegates, exact service-error-to-HTTP mapping and routes pending dedicated route-module extraction | Cross-domain use-case sequencing, direct SQL/DDL or duplicate Policy decisions |
| EOD operational gate coordination | `platform-backend/app/eod_policy.py` | Business-day order selection and repository coordination for the historical-Difference gate | Direct SQL/DDL, report row mapping, duplicate status/review decisions or routes |
| Venue Reconciliation public DTOs | `platform-backend/app/venue_reconciliation_schemas.py` | Reconciliation run, difference-resolution and order-reconciliation request/response models plus public status types | SQL, Runtime queries, comparison or route orchestration |
| Venue Reconciliation difference policy | `platform-backend/app/venue_reconciliation_policy.py` | Pure external-status mapping and immutable Order/Position/Balance difference-draft decisions | SQL, Runtime queries, persistence, audit or routes |
| Venue Reconciliation persistence | `platform-backend/app/venue_reconciliation_repository.py` | Reconciliation DDL, direct SQL, audit/run/difference persistence, comparison reads, row mapping and protected transactions | FastAPI, Runtime queries, FinancialFact import or difference rules |
| Venue Reconciliation Runtime client | `platform-backend/app/venue_reconciliation_runtime_client.py` | Configured Runtime GET transport, URL/parameter/timeout application and transport-error boundary | FastAPI error responses, persistence, FinancialFact import, difference rules or use-case orchestration |
| Venue Reconciliation Service | `platform-backend/app/venue_reconciliation_service.py` | Order/account reconciliation sequencing, FinancialFact import, policy/repository/client coordination and explicit domain failures | FastAPI/APIRouter, configured HTTP implementation, direct SQL/DDL or public DTO definitions |
| Venue Reconciliation facade | `platform-backend/app/venue_reconciliation.py` | Compatibility exports/delegates, exact domain/transport-error-to-HTTP mapping and routes pending dedicated route-module extraction | FinancialFact import, reconciliation sequencing, direct Runtime HTTP, SQL/DDL or duplicate DTO/policy definitions |
| Operational fill projection | `platform-backend/app/trading.py` | Low-latency `positions` and `pnl_results` updates plus explicit legacy submission compatibility export | Authoritative order submission or formal accounting |
| Position calculation policy | `platform-backend/app/position_math.py` | Pure per-fill net quantity, average price and realized PnL calculation shared by operational and formal projections | SQL, HTTP, FX, multiplier application or projection persistence |
| FinancialFact public DTOs | `platform-backend/app/financial_fact_schemas.py` | FinancialFact, formal Position/PnL/NAV and rebuild API models | Normalization, SQL or calculations |
| FinancialFact normalization | `platform-backend/app/financial_fact_normalization.py` | Canonical currency, Decimal, UTC, JSON, FX/data-quality and immutable content hash | Repository access, FastAPI or venue SDKs |
| FinancialFact persistence | `platform-backend/app/financial_fact_repository.py` | FinancialFact/formal projection SQL, row mapping and protected transaction units | HTTP routing or accounting formulas |
| Formal projection calculations | `platform-backend/app/financial_projection_service.py` | FinancialFact replay, multiplier/FX application, component PnL, formal rebuild and NAV orchestration | FastAPI, configuration, direct SQL or duplicate position math |
| FinancialFact API orchestration | `platform-backend/app/financial_facts.py` | Catalog resolution, immutable fact recording, domain-error mapping, compatibility wrappers and routes | DTO definitions, normalization rules, direct SQL or projection formulas |

Operational projections are monitoring views. Formal accounting is reconstructed from immutable FinancialFacts and may not read operational projections as calculation inputs.

## Shared database infrastructure

| Boundary | Authoritative owner | Responsibility | Must not own |
|---|---|---|---|
| SQLite connection | `platform-backend/app/database_connection.py` | Dynamic path, parent creation, Row Factory, Foreign Keys and Commit/Rollback/Close | Schema or Seed content |
| Core database bootstrap | `platform-backend/app/database_bootstrap.py` | Ordered core Schema and legacy compatibility DDL | Seed vectors or business services |
| Fixed reference Seeds | `platform-backend/app/database_seeds.py` | Fixed Seed vectors, insertion order and approved default updates | Connection or Schema implementation |
| Database compatibility facade | `platform-backend/app/database.py` | Explicit compatibility exports and `Connection → Bootstrap → Seed` initialization | Connection, Schema or Seed implementation |
| Migration ledger | `platform-backend/app/schema_migrations.py` | Ordered additive migrations and immutable checksums | Editing an applied migration |
| Database authority documentation | `docs/database/README.md` | Table authority, DDL owners, Seed authority and migration discipline | Runtime implementation |

## Runtime and external effects

| Boundary | Authoritative owner | Responsibility | Must not own |
|---|---|---|---|
| Venue SDKs and external execution | `execution-runtime/` | Gateway adapters, external side effects and runtime journal | Platform business API or formal accounting |
| Runtime journal | `execution-runtime/app/journal.py` | Durable runtime Command/Event evidence | Permanent financial ledger authority |
| Platform execution exposure | `platform-backend/app/execution_exposure.py` | Canonical residual exposure calculation | Parallel exposure formulas |
| Bybit confirmed market execution | `execution-runtime/app/bybit_fill_confirming_adapter.py` | REST submission, reduce-only position validation, positionIdx mapping and bounded terminal-fill confirmation | Platform exit plans, live specification policy or MT5 ticket policy |
| Bybit acceptance reads | `execution-runtime/app/bybit_acceptance_adapter.py` | Route-independent Order/Fill reads, paged venue history, account risk, live instrument specification and API-key readiness mapping | Platform business rules, write authorization or MT5 behavior |
| MT5 ticket-bound close execution | `execution-runtime/app/mt5_position_closing_adapter.py` | Reduce-only Position Ticket, side and quantity validation before MT5 deal submission | Platform plan selection, live Order/Deal discovery or threshold evaluation |
| MT5 acceptance reads | `execution-runtime/app/mt5_acceptance_adapter.py` | Route-independent Order/Deal reads, Order/Deal Ticket resolution, live Symbol and Terminal specification mapping | Platform business rules, write authorization or Bybit behavior |
| Live risk and history mapping | `execution-runtime/app/live_observability.py` | Bybit position liquidation mapping, MT5 explicit unavailable liquidation semantics, account Stop Out mapping and deterministic MT5 history continuation | Platform aggregation, estimated liquidation prices or external writes |
| Strict live acceptance write gate | `execution-runtime/app/strict_live_acceptance_adapters.py` | Runtime-independent ounce cap, venue step/contract-size/access validation and one-position admission rule | Platform lifecycle persistence, credential values or limit execution |
| Live adapter routing | `execution-runtime/app/bybit_mt5_gateway.py` | Account-routed adapter selection and deterministic route-independent external-ID lookup | Venue-specific mapping rules or Platform persistence |

The Platform Backend must not import venue SDKs. Unknown external results remain unknown until reconciled and must never trigger an automatic duplicate submission.

## Engineering and context governance

| Boundary | Authoritative owner | Responsibility | Must not own |
|---|---|---|---|
| Durable Agent rules | `AGENTS.md` | Safety and engineering rules that remain valid across tasks | Current task progress or PR history |
| Agent context loading | `docs/codex/context-map.md` | Bounded context-loading order and module entrypoints | Duplicate ownership registry |
| Current engineering truth | `docs/codex/current-state.md` | Compact current state, safety defaults and active work | Historical implementation diary |
| Task handoff | `docs/codex/task-template.md`, `tasks/` | One bounded packet per non-trivial Issue | Repository-wide permanent rules |
| Architecture ownership | `docs/architecture/OWNERSHIP.md` | This canonical ownership catalog | Task progress or operational runbooks |
| Architecture enforcement | `scripts/check-repository-structure.py`, `scripts/check-documentation-consistency.py` | Machine checks for code and documentation boundaries | Runtime application behavior |
| Workstream enforcement | `scripts/check-workstream.py` | Full engineering and bounded lightweight-maintenance workflow enforcement | Product behavior |

## Change protocol

A change to an ownership boundary requires:

1. one concrete Issue and task packet;
2. explicit old and new Owner in the pull request;
3. direct architecture and behavioral evidence;
4. synchronized updates to this catalog, current-state and directly affected technical documentation;
5. no unrelated business, persistence or Live Write change hidden inside the refactor.
