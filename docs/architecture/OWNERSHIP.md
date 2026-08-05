# Architecture Ownership Catalog

This document owns current code and data responsibilities. It records present authority, not implementation history.

## Platform composition and contracts

| Boundary | Owner | Must not own |
|---|---|---|
| Application composition | `platform-api/app/application.py`, `platform-api/app/main.py` | business rules, SQL, venue effects |
| Public execution DTO compatibility | `platform-api/app/execution_schemas.py`, `platform-api/app/schemas.py` | persistence or execution |
| Platform–Runtime contract | both `runtime_contracts.py` modules and `docs/contracts/runtime-v1.json` | silent incompatible changes |
| Frontend API boundary | `platform-web/src/api/platform/` | database access or authorization policy |

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

## Protected invariants

- Result Unknown remains unknown until reconciled from persisted evidence.
- Duplicate submission is never authorized by missing or ambiguous external results.
- Live Write remains fail-closed and requires the existing approval/safety gates.
- Formal accounting never reads operational projections as authoritative inputs.
- Decimal and timezone-aware values remain exact at financial boundaries.
- External SDKs remain isolated in Execution Runtime.
