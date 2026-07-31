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
| Platform composition root | `platform-api/app/main.py` | Router and middleware assembly | Domain rules, calculations, runtime patching |
| Execution API DTOs | `platform-api/app/execution_schemas.py` | Public execution-domain request/response models | Trading execution or persistence |
| Execution compatibility DTO exports | `platform-api/app/schemas.py` | Explicit aliases to execution DTO owners | Duplicate DTO definitions |
| Platform–Runtime contracts | `platform-api/app/runtime_contracts.py`, `execution-runtime/app/runtime_contracts.py`, `docs/contracts/runtime-v1.json` | Versioned command/event models, execution-policy field and executable snapshot | Silent incompatible V1 changes |
| Cross-spread lifecycle DTOs | `platform-api/app/cross_spread_exit_schemas.py` | Market/Limit lifecycle requests, FOK/PostOnly selections, TP/SL modes and strategies, normalized intent, pricing evidence and Exit Plan responses | Pricing formulas, SQL or Venue execution |
| Cross-spread observability DTOs | `platform-api/app/cross_spread_observability_schemas.py` | Read-only aggregate status, section-state and Venue evidence response models | Runtime HTTP, Venue mapping or execution decisions |

## Human identity, authorization and browser sessions

| Boundary | Authoritative owner | Responsibility | Must not own |
|---|---|---|---|
| Request authentication and assurance | `platform-api/app/auth.py` | API-key/development authentication compatibility, browser-session Principal integration, route assurance, legacy permission mapping and request-level denial audit | Password hashing, direct user SQL, target-user policy or Live gate replacement |
| Authentication and authorization error contract | `docs/technical/USER_SYSTEM_AUTH_ERROR_CONTRACT.md` | Stable security error codes, response envelope, Request ID correlation, client invalidation semantics and denial-audit vocabulary | Authentication decisions, business-domain errors or frontend presentation copy |
| Sensitive identity response cache policy | `platform-api/app/user_cache_control.py` | `no-store` and legacy proxy-cache prevention for `/auth/**`, `/me/**` and `/users/**`, including rejected requests | Authentication decisions, user data or route permissions |
| Role and permission registry | `platform-api/app/user_permissions.py` | Separate API-key and human-role namespaces plus centralized permission resolution | Route orchestration, persistence or target-user decisions |
| Password and opaque-token security | `platform-api/app/user_security.py` | Argon2id hashing, password policy, identity normalization and high-entropy token hashing | User persistence, HTTP cookies or account lifecycle transitions |
| User and Session persistence | `platform-api/app/user_repository.py` | User lookup, browser-user persistence, opaque Session persistence, bounded Session count, reset tickets and revocation SQL | HTTP, password verification, menu policy or trading authorization |
| Human authority invariants | `platform-api/app/user_authority.py` | Transactional protected-role invariants including the last-active-CEO guard | Authentication, SQL unrelated to user authority or frontend visibility |
| Browser Session validation | `platform-api/app/user_session_auth.py` | Session expiry, idle timeout, auth-version invalidation, stable Session/CSRF error codes, Origin validation and activity throttling | Login credential verification, user administration or API-key validation |
| Public auth and self-account use cases | `platform-api/app/user_service.py`, `platform-api/app/user_password_reset.py`, `platform-api/app/user_logout.py` | Registration, login, current authentication, reauthentication, profile/password/device workflows, reset-ticket consumption and idempotent logout | FastAPI route assembly, administrator target policy, Venue effects or formal accounting |
| Public auth and self-account routes/DTOs | `platform-api/app/user_routes.py`, `platform-api/app/user_schemas.py` | `/auth/**` and `/me/**` HTTP contracts, Cookie issuance/clearing, rate-limit routing and service-error mapping | Direct SQL, password hashing or business authorization policy |
| Avatar processing and persistence | `platform-api/app/user_avatar.py`, `platform-api/app/user_avatar_repository.py` | Bounded decode, EXIF normalization, WebP re-encoding, opaque filesystem keys, optimistic row updates and transactional audit | Arbitrary external URLs, raw upload persistence or general profile policy |
| Avatar routes/DTOs | `platform-api/app/user_avatar_routes.py`, `platform-api/app/user_avatar_schemas.py` | Session-only upload/read/delete contracts and exact HTTP error mapping | Image processing or direct SQL |
| User-administration target policy | `platform-api/app/user_admin_policy.py` | CEO/technical-lead target and assignable-role rules plus recent-reauth requirements | SQL, HTTP or menu visibility |
| User-administration persistence | `platform-api/app/user_admin_repository.py` | User search/detail/update, lifecycle/role transitions and administration audit reads within protected transactions | FastAPI or target-role decisions |
| User-administration use cases | `platform-api/app/user_admin_service.py` | Search, create, approve/reject, edit, role/status, reset-ticket and forced-session-revocation sequencing with transactional audit | Route composition, frontend visibility or hard deletion |
| User-administration routes/DTOs | `platform-api/app/user_admin_routes.py`, `platform-api/app/user_admin_schemas.py` | `/users/**` management HTTP contracts, permission dependencies and response masking selection | Direct SQL, password generation or target policy redefinition |
| Member holding Decimal policy | `platform-api/app/member_holding_decimal.py` | Plain non-negative Decimal parsing, canonical strings and exact derived reporting values | Currency conversion, formal accounting or SQL |
| Member holding pure valuation | `platform-api/app/member_holding_valuation.py` | Loaded Fund/Holding/NAV validation, exact response construction, NAV available/stale/unavailable classification and UTC normalization | SQL, configuration lookup, HTTP, permission checks, audit or write orchestration |
| Member holding and NAV persistence | `platform-api/app/member_holding_repository.py` | Holding/NAV SQL, optimistic versions, source constraints and fund catalog reads | HTTP, permission policy or derived Decimal formulas |
| Member holding and NAV use cases | `platform-api/app/member_holding_service.py` | Self/admin scope, member-target validation, Fund/NAV loading, valuation-error mapping, recent reauthentication and transactional audit | Derived valuation formulas, subscription/redemption accounting, execution or strategy NAV substitution |
| Member holding routes/DTOs | `platform-api/app/member_holding_routes.py`, `platform-api/app/member_holding_schemas.py` | Session-only self/admin holding and NAV HTTP contracts; browser writes restricted to `manual_admin` | Import pipelines, direct SQL or floating-point calculations |
| User bootstrap command | `platform-api/app/user_cli.py` | Interactive, no-default-password first-CEO bootstrap | Automated production account creation or secret persistence |
| Frontend user-system API boundary | `platform-web/src/api/platform/userSystem.ts`, `platform-web/src/api/platform/memberHoldings.ts` | Same-origin Cookie clients, memory-only/multi-tab CSRF, structured DTOs and stable-code Session invalidation | Persistent authentication tokens, role authorization or floating-point holding calculations |
| Frontend browser access registry | `platform-web/src/access/userAccess.ts`, `platform-web/src/access/routeAccess.ts` | Exact permission matching and one permission-aware route/menu tree | Wildcard expansion, backend authorization or duplicate menu facts |
| Frontend browser Session state | `platform-web/src/store/modules/user.ts`, `platform-web/src/router/guard/permissionGuard.ts` | Session hydration, permission-store population, state reset and centralized dynamic-route installation | Credential persistence, backend role inference or unfiltered route installation |

## Trading and formal accounting

| Boundary | Authoritative owner | Responsibility | Must not own |
|---|---|---|---|
| Platform order submission orchestration | `platform-api/app/trade_command_execution.py` | Single local Order creation, Safety enforcement, legacy/V1 Runtime dispatch including execution policy, unknown-result handling and Event handoff | Event projection, reconciliation or formal accounting |
| Venue order execution intent | `platform-api/app/order_execution_intents.py` | Idempotent reduce-only, Venue-position target and persisted execution-policy lookup for a TradeCommand | Batch sequencing, Venue SDK calls or exit-threshold policy |
| Cross-spread synthetic order intent | `platform-api/app/cross_spread_order_intent.py` | Authoritative four business actions, Market/Limit execution type, trigger reason and execution-independent four-action mapping | Venue submission, persistence, quote formulas or Exit Plan claims |
| Cross-spread Limit pricing policy | `platform-api/app/cross_spread_limit_policy.py` | Pure two-direction executable-spread formulas, Hedge Reserve application and conservative Tick rounding | Catalog reads, HTTP, persistence, Batch creation or Venue submission |
| Cross-spread Limit batch construction | `platform-api/app/cross_spread_limit_execution.py` | Catalog Tick validation, acceptance sizing, reduce-only/ticket intent registration, FOK/PostOnly execution policy and Bybit-Limit/MT5-Market ExecutionBatch construction | Venue SDKs, quote acquisition, TP/SL selection or Exit Plan state transitions |
| Cross-spread market command and live sizing | `platform-api/app/cross_spread.py` | Nominal spread command mapping, live Venue specification validation, exact ounce-to-lot sizing and deterministic Bybit rollback intent | Venue SDK calls, Exit Plan SQL or automatic monitor loops |
| Cross-spread live read transport | `platform-api/app/cross_spread_live_read_client.py` | Configured Runtime transport and validated Instrument, Position, Account Risk and paged Order/Fill reads | FastAPI routes, SQL, Venue SDKs or execution decisions |
| Cross-spread observability service | `platform-api/app/cross_spread_observability_service.py` | Independent section reads, partial/unavailable semantics and two-Venue read-only aggregation | Venue SDKs, order submission, SQL or secret access |
| Cross-spread observability routes | `platform-api/app/cross_spread_observability_routes.py` | Bounded read-only history query parameters and aggregate API routing | Venue mapping, execution or persistence |
| Cross-spread exit threshold policy | `platform-api/app/cross_spread_exit_policy.py` | Pure executable-close-spread selection and TP/SL inequality decisions | SQL, HTTP, background tasks or order submission |
| Cross-spread Exit Plan persistence | `platform-api/app/cross_spread_exit_repository.py` | Exact-Decimal fill summary, Exit Plan SQL, TP/SL execution-mode and Limit-strategy persistence, atomic claims, clean Claim release and unresolved-lifecycle counts | Venue HTTP, threshold formulas, background loops or routes |
| Cross-spread Market safety helpers | `platform-api/app/cross_spread_exit_service.py` | Existing admission, external-position verification, hedged-open plan creation, definitive-failure rollback coordination, MT5 Ticket mapping and flat-position verification reused without semantic change | Limit pricing, public synthetic-intent ownership or Venue SDKs |
| Cross-spread synthetic lifecycle service | `platform-api/app/cross_spread_synthetic_service.py` | Public Market/FOK/PostOnly Open/Close orchestration, TP/SL stored-mode/strategy selection, claimed trigger-spread pricing, shared Close Action and plan-state coordination | Direct SQL, Venue SDKs, private WebSocket implementation, IOC or post-trade analytics |
| Cross-spread lifecycle routes | `platform-api/app/cross_spread_exit_routes.py` | API routing and disabled-by-default monitor lifespan through the synthetic lifecycle service | SQL, threshold formulas or Venue execution logic |
| EOD Reconciliation public DTOs | `platform-api/app/eod_reconciliation_schemas.py` | EOD report/review request-response models and public status types | DDL, SQL, report orchestration, review policy or routes |
| EOD report and review policy | `platform-api/app/eod_reconciliation_policy.py` | Pure report status, scale-gate, historical-Difference and immutable-review decisions | FastAPI, database/repository access, HTTP or cross-domain orchestration |
| EOD Reconciliation persistence | `platform-api/app/eod_reconciliation_repository.py` | EOD report DDL, direct SQL, row mapping, report identity, review transactions and policy persistence reads/writes | FastAPI, cross-domain orchestration, status formulas or routes |
| EOD Reconciliation Service | `platform-api/app/eod_reconciliation_service.py` | Report creation/read/list/review sequencing, cross-domain coordination, partial-failure capture and explicit service failures | FastAPI/APIRouter/Query, direct SQL/DDL, duplicate Policy decisions or routes |
| EOD Reconciliation facade | `platform-api/app/eod_reconciliation.py` | Per-call dependency wiring, stable compatibility delegates and exact service-error-to-HTTP mapping | FastAPI route assembly, cross-domain use-case sequencing, direct SQL/DDL or duplicate Policy decisions |
| EOD Reconciliation routes | `platform-api/app/eod_reconciliation_routes.py` | Four EOD HTTP endpoints, response models and stable query aliases delegated to the facade | Service/Repository imports, dependency wiring, error translation, SQL or report policy |
| EOD operational gate coordination | `platform-api/app/eod_policy.py` | Business-day order selection and repository coordination for the historical-Difference gate | Direct SQL/DDL, report row mapping, duplicate status/review decisions or routes |
| Venue Reconciliation public DTOs | `platform-api/app/venue_reconciliation_schemas.py` | Reconciliation run, difference-resolution and order-reconciliation request/response models plus public status types | SQL, Runtime queries, comparison or route orchestration |
| Venue Reconciliation difference policy | `platform-api/app/venue_reconciliation_policy.py` | Pure external-status mapping and immutable Order/Position/Balance difference-draft decisions | SQL, Runtime queries, persistence, audit or routes |
| Venue Reconciliation persistence | `platform-api/app/venue_reconciliation_repository.py` | Reconciliation DDL, direct SQL, audit/run/difference persistence, comparison reads, row mapping and protected transactions | FastAPI, Runtime queries, FinancialFact import or difference rules |
| Venue Reconciliation Runtime client | `platform-api/app/venue_reconciliation_runtime_client.py` | Configured Runtime GET transport, URL/parameter/timeout application and transport-error boundary | FastAPI error responses, persistence, FinancialFact import, difference rules or use-case orchestration |
| Venue Reconciliation Service | `platform-api/app/venue_reconciliation_service.py` | Order/account reconciliation sequencing, FinancialFact import, policy/repository/client coordination and explicit domain failures | FastAPI/APIRouter, configured HTTP implementation, direct SQL/DDL or public DTO definitions |
| Venue Reconciliation facade | `platform-api/app/venue_reconciliation.py` | Compatibility exports/delegates, exact domain/transport-error-to-HTTP mapping and routes pending dedicated route-module extraction | FinancialFact import, reconciliation sequencing, direct Runtime HTTP, SQL/DDL or duplicate DTO/policy definitions |
| Operational fill projection | `platform-api/app/trading.py` | Low-latency `positions` and `pnl_results` updates plus explicit legacy submission compatibility export | Authoritative order submission or formal accounting |
| Position calculation policy | `platform-api/app/position_math.py` | Pure per-fill net quantity, average price and realized PnL calculation shared by operational and formal projections | SQL, HTTP, FX, multiplier application or projection persistence |
| FinancialFact public DTOs | `platform-api/app/financial_fact_schemas.py` | FinancialFact, formal Position/PnL/NAV and rebuild API models | Normalization, SQL or calculations |
| FinancialFact normalization | `platform-api/app/financial_fact_normalization.py` | Canonical currency, Decimal, UTC, JSON, FX/data-quality and immutable content hash | Repository access, FastAPI or Venue SDKs |
| FinancialFact persistence | `platform-api/app/financial_fact_repository.py` | FinancialFact/formal projection SQL, row mapping and protected transaction units | HTTP routing or accounting formulas |
| Formal projection calculations | `platform-api/app/financial_projection_service.py` | FinancialFact replay, multiplier/FX application, component PnL, formal rebuild and NAV orchestration | FastAPI, configuration, direct SQL or duplicate position math |
| FinancialFact API orchestration | `platform-api/app/financial_facts.py` | Catalog resolution, immutable fact recording, domain-error mapping, compatibility wrappers and routes | DTO definitions, normalization rules, direct SQL or projection formulas |

Operational projections are monitoring views. Formal accounting is reconstructed from immutable FinancialFacts and may not read operational projections as calculation inputs.

## Shared database infrastructure

| Boundary | Authoritative owner | Responsibility | Must not own |
|---|---|---|---|
| SQLite connection | `platform-api/app/database_connection.py` | Dynamic path, parent creation, Row Factory, Foreign Keys and Commit/Rollback/Close | Schema or Seed content |
| Core database bootstrap | `platform-api/app/database_bootstrap.py` | Ordered core Schema and legacy compatibility DDL | Seed vectors or business services |
| Fixed reference Seeds | `platform-api/app/database_seeds.py` | Fixed Seed vectors, insertion order and approved default updates | Connection or Schema implementation |
| Database compatibility facade | `platform-api/app/database.py` | Explicit compatibility exports and `Connection → Bootstrap → Seed` initialization | Connection, Schema or Seed implementation |
| Migration ledger | `platform-api/app/schema_migrations.py` | Ordered additive migrations, including execution policy, user identity/session and member holding/NAV schema, with immutable checksums | Editing an applied migration |
| Database authority documentation | `docs/database/README.md` | Table authority, DDL owners, Seed authority and migration discipline | Runtime implementation |

## Runtime and external effects

| Boundary | Authoritative owner | Responsibility | Must not own |
|---|---|---|---|
| Venue SDKs and external execution | `execution-runtime/` | Gateway adapters, external side effects and Runtime Journal | Platform business API or formal accounting |
| Runtime journal | `execution-runtime/app/journal.py` | Durable Runtime Command/Event evidence | Permanent financial ledger authority |
| Platform execution exposure | `platform-api/app/execution_exposure.py` | Canonical residual exposure calculation | Parallel exposure formulas |
| Bybit confirmed Market/FOK/PostOnly execution | `execution-runtime/app/bybit_fill_confirming_adapter.py` | REST submission, reduce-only position validation, Position Index mapping, Market/FOK confirmation and bounded PostOnly place/amend/cancel/repost orchestration | Platform spread pricing, Exit Plans, MT5 ticket policy or post-trade analytics |
| Bybit PostOnly Chase policy | `execution-runtime/app/bybit_postonly_chase.py` | Pure maker-safe pricing, TTL/mutation/cooldown state transitions, private-event deduplication, cumulative fill and race resolution | Venue SDK, secrets, Platform models or MT5 submission |
| Bybit private stream source | `execution-runtime/app/bybit_private_stream.py` | Disabled-by-default Pybit private Order/Execution subscription, parsing, prefix filtering and disconnect evidence | Business action selection, spread pricing, MT5 submission or persistence |
| Bybit acceptance reads | `execution-runtime/app/bybit_acceptance_adapter.py` | Route-independent Order/Fill reads, paged Venue history, account risk, live instrument specification and API-key readiness mapping | Platform business rules, write authorization or MT5 behavior |
| MT5 ticket-bound close execution | `execution-runtime/app/mt5_position_closing_adapter.py` | Reduce-only Position Ticket, side and quantity validation before MT5 deal submission | Platform plan selection, live Order/Deal discovery or threshold evaluation |
| MT5 acceptance reads | `execution-runtime/app/mt5_acceptance_adapter.py` | Route-independent Order/Deal reads, Order/Deal Ticket resolution, live Symbol and Terminal specification mapping | Platform business rules, write authorization or Bybit behavior |
| Live risk and history mapping | `execution-runtime/app/live_observability.py` | Bybit position liquidation mapping, MT5 explicit unavailable liquidation semantics, account Stop Out mapping and deterministic MT5 history continuation | Platform aggregation, estimated liquidation prices or external writes |
| Strict live acceptance write gate | `execution-runtime/app/strict_live_acceptance_adapters.py` | Runtime-independent ounce cap, Venue Step/Contract Size/access validation and one-position admission rule | Platform lifecycle persistence, credential values or Limit execution |
| Live adapter routing | `execution-runtime/app/bybit_mt5_gateway.py` | Account-routed adapter selection and deterministic route-independent external-ID lookup | Venue-specific mapping rules or Platform persistence |

The Platform Backend must not import Venue SDKs. Unknown external results remain unknown until reconciled and must never trigger an automatic duplicate submission.

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
