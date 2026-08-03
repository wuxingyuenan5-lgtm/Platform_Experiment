# Domain Contract Index

This A1 index routes readers to current A2 contracts. It does not duplicate contract rules. A2 documents are loaded only for the affected domain.

| Domain | A2 contract | Authoritative implementation owner |
|---|---|---|
| Identity & Permission | `../technical/AUTH_RBAC_LIVE_SESSIONS.md`, `../technical/USER_SYSTEM_AUTH_ERROR_CONTRACT.md` | `platform-api/app/auth.py`, `platform-api/app/user_authority.py`, `platform-api/app/user_permissions.py` |
| Live Write | `../technical/EXECUTION_RISK_CONTROLS.md` | `platform-api/app/live_trading_sessions.py`, `platform-api/app/execution_risk.py`, `execution-runtime/app/live_safety.py` |
| Trading | `../technical/CROSS_SPREAD_SYNTHETIC_EXECUTION.md` | Cross-spread policy, lifecycle and orchestration modules listed in `../architecture/OWNERSHIP.md` |
| Execution | `runtime-v1.json` | `platform-api/app/runtime_contracts.py`, `execution-runtime/app/runtime_contracts.py` |
| Risk | `../technical/EXECUTION_RISK_CONTROLS.md` | `platform-api/app/execution_risk.py` |
| Accounting | `../technical/FINANCIAL_FACTS.md` | Financial Fact and formal projection owners listed in `../architecture/OWNERSHIP.md` |
| Reconciliation | `../technical/VENUE_RECONCILIATION.md`, `../technical/EOD_RECONCILIATION.md` | Venue and EOD policy/repository/service owners listed in `../architecture/OWNERSHIP.md` |
| Member Portfolio | `../technical/MEMBER_HOLDINGS_READ_MODEL.md` | Member holding Decimal, repository, service and route owners |
| Research | `../technical/RESEARCH_DATA_PLATFORM.md` | Research schema, policy, cache, provider and service owners |
| Market Data | `../technical/RESEARCH_DATA_PLATFORM.md` | Research provider adapters and normalized data schemas |
| Secret handling | `../technical/SECRET_PROVIDER_AND_REDACTION.md` | Platform metadata owner and Platform Execution Runtime resolver/redactor owners |
| Operations | `../technical/PRODUCTION_OPERATIONS.md` | Monitoring, controlled-operation and disaster-recovery owners |

Rules:

- One business rule has one implementation owner.
- `docs/architecture/OWNERSHIP.md` resolves ownership conflicts.
- A1 documents link here instead of copying contract text.
- Historical plans, acceptance records and release notes are not contracts.
