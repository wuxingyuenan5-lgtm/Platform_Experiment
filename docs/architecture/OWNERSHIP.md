# Architecture Ownership Catalog

This document owns current code and data responsibilities. It records present authority, not implementation history.

## Platform composition and contracts

| Boundary | Owner | Must not own |
|---|---|---|
| Application composition | `platform-api/app/application.py`, `platform-api/app/main.py` | business rules, SQL, venue effects |
| Public execution DTO compatibility | `platform-api/app/execution_schemas.py`, `platform-api/app/schemas.py` | persistence or execution |
| Platform–Runtime contract | both `runtime_contracts.py` modules and `docs/contracts/runtime-v1.json` | silent incompatible changes |
| Frontend API boundary | `platform-web/src/api/platform/` | database access or authorization policy |
| Research API composition, background refresh, persistent snapshots, providers, cache, quality metadata and partial-failure semantics | `platform-api/app/research_routes.py`, `platform-api/app/research_service.py`, `platform-api/app/research_a_share_refresh.py`, `platform-api/app/research_a_share_repository.py`, `platform-api/app/research_providers.py`, `platform-api/app/research_cache.py`, `platform-api/app/research_data_schemas.py` | trade quotes, position/accounting facts or browser-side provider fan-out |
| Hedge Board research presentation | `platform-web/src/api/hedgeResearch.ts`, `platform-web/src/views/hedgeBoard/` | upstream truth, Live Write or fabricated data availability |
| Financial AI route composition and model/configuration adapter | `platform-api/app/financial_ai_routes.py`, `platform-web/src/router/routes/modules/financial-ai.ts`, `platform-web/src/api/financialAi.ts` | page-local authorization, arbitrary command execution, trading or accounting facts |
| Financial AI news and global-market upstream adaptation | `platform-api/app/financial_ai_routes.py` | claiming upstream availability or freshness beyond returned evidence |
| Financial AI machine configuration authorization | `platform-api/app/auth.py`, `platform-api/app/user_permissions.py` | returning provider secrets or delegating authorization to the browser |

## Browser access and restored product presentation

| Boundary | Owner | Must not own |
|---|---|---|
| Human browser role capability registry | `platform-api/app/user_permissions.py`, `platform-api/app/user_authority.py` | page-local role invention or API-Key role conversion |
| Browser route capability transformation and route/menu access | `platform-web/src/access/browserRouteCapabilities.ts`, `platform-web/src/access/userAccess.ts`, `platform-web/src/router/routes/index.ts` | backend authorization decisions or data-scope enforcement |
| Product data envelope and restored state presentation | `platform-web/src/data/productDataEnvelope.ts`, `platform-web/src/components/ProductDataState/`, `platform-web/src/data/sample/` | fabricated provider success or authoritative realtime market facts |
| Personal-security form and payload contracts | `platform-web/src/views/risk/profile/security/contracts.ts`, `platform-web/src/views/risk/profile/security/modules.tsx` | parent persistence, provider completion or synthetic success responses |

Frontend owners present and transform capabilities but do not own backend authorization decisions. Menu hiding is not a security authorization boundary. The sample-data directory does not own realtime market facts. Personal-security child components must not fabricate parent persistence or provider success.

Strategy account presentation is owned by `strategyFinancialPresentation.ts`, `useStrategyAccountSnapshots.ts` and `useCrossSpreadFinance.ts` under `platform-web/src/views/strategy/management/composables/`. The snapshot API owns position scope; the browser must not choose a historical position fallback. Shared query keys and session invalidation remain in `src/api/platform/strategyQueries.ts`.

For this boundary, run `corepack pnpm type:check` in `platform-web` and `corepack pnpm test:strategy-finance` (includes executed function/composable checks and existing source guards); exercise the actual page with `corepack pnpm test:e2e:strategy-accounts`. The latter uses isolated services and synthetic account responses, so live data binding still needs separate read-only API evidence. The visual config owns test process/database identity and rejects reused listeners. Failure traces, screenshots and request summaries are retained under `test-results/platform-visual/`.

`type:check` uses `tsconfig.strategy.json`; use `type:check:full` for Hedge Board components outside that scope. `test:hedge-board-layout` is a source/layout guard, not browser acceptance. Browser checks must also reject captured widget errors and visible rendering-error placeholders.

## Execution risk

| Boundary | Owner | Responsibility |
|---|---|---|
| Risk DTOs and enums | `platform-api/app/execution_risk_models.py` | Pydantic requests/responses, enums and domain DTOs; no database |
| Pure risk policy | `platform-api/app/execution_risk_policy.py` | deadline, residual exposure, threshold, completion and disposition decisions |
| Risk persistence | `platform-api/app/execution_risk_repository.py` | Kill Switch, policy, batch-risk and risk-action SQL and row mapping |
| Risk HTTP/application orchestration | `platform-api/app/execution_risk.py` | router, boundary validation, policy/repository coordination and HTTP mapping |
| Trade-command side effect | `platform-api/app/trade_commands.py` | authoritative command creation; wired to risk through a callable port |
| Batch sequencing | `platform-api/app/execution_batches.py` | leg sequencing and calls into the stable risk facade |

Risk policy must remain deterministic and independently testable. Risk persistence must not import FastAPI. Risk actions may create orders only through the TradeCommand port.

## Identity, trading and accounting

| Boundary | Owner |
|---|---|
| Authentication and request assurance | `app/auth.py`, `app/user_session_auth.py` |
| Role/permission registry and protected authority | `app/user_permissions.py`, `app/user_authority.py` |
| User/session persistence | `app/user_repository.py` and dedicated user repositories |
| Order submission orchestration | `app/trade_command_execution.py` |
| Operational fill projections | `app/trading.py` |
| Immutable financial facts | `app/financial_fact_repository.py` |
| Formal projection calculations | `app/financial_projection_service.py` |
| Venue reconciliation | dedicated policy/repository/client/service/routes modules |
| EOD reconciliation | dedicated policy/repository/service/routes modules |
| Live session approval | `app/live_trading_sessions.py` |
| Runtime journal and venue effects | `execution-runtime/app/` owners |

## Database infrastructure

| Boundary | Owner |
|---|---|
| SQLite connection and transaction boundary | `app/database_connection.py` |
| Core bootstrap | `app/database_bootstrap.py` |
| Fixed reference seeds | `app/database_seeds.py` |
| Ordered additive migrations | `app/schema_migrations.py` |
| Domain DDL/SQL | the registered repository or persistence owner |

Account snapshot scope and financial read projections are checked by `platform-api/tests/test_strategy_account_snapshot.py`; migrations by `tests/test_schema_migrations.py`. Local service recovery is owned by `scripts/dev-platform.ps1` and `scripts/platform-watchdog.ps1`; `scripts/tests/test_platform_watchdog.py` injects fake process/network failures and checks bounded recovery, foreign-process refusal and Live Write interruption protection. `scripts/tests/test_platform_child_launcher.py` verifies log handles after launcher exit. These isolated checks do not establish long-running venue/Worker stability.

## Protected invariants

- Result Unknown remains unknown until reconciled from persisted evidence.
- Duplicate submission is never authorized by missing or ambiguous external results.
- Live Write remains fail-closed and requires the existing approval/safety gates.
- Formal accounting never reads operational projections as authoritative inputs.
- Decimal and timezone-aware values remain exact at financial boundaries.
- External SDKs remain isolated in Execution Runtime.
