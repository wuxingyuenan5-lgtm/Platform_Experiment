# Domain Contract Index

This index routes to current contracts; implementation history is not a contract.

| Domain | Contract | Implementation owner |
|---|---|---|
| Browser Access & Product Data | `BROWSER_ACCESS_AND_PRODUCT_DATA.md` | browser role capabilities, route/menu policy, personal account and restored product state owners |
| Identity & Permission | `../technical/AUTH_RBAC_LIVE_SESSIONS.md`, `../technical/USER_SYSTEM_AUTH_ERROR_CONTRACT.md` | auth, authority, permissions and user modules |
| Live Write | `../technical/EXECUTION_RISK_CONTROLS.md` | Live session modules, risk modules and Runtime live safety |
| Execution Risk | `../technical/EXECUTION_RISK_CONTROLS.md` | `execution_risk_models.py`, `execution_risk_policy.py`, `execution_risk_repository.py`, `execution_risk.py` |
| Trading | `../technical/CROSS_SPREAD_SYNTHETIC_EXECUTION.md` | trading and cross-spread owners in `../architecture/OWNERSHIP.md` |
| Execution | `runtime-v1.json` | both Runtime contract modules |
| Accounting | `../technical/FINANCIAL_FACTS.md` | Financial Fact repository and formal projection service |
| Reconciliation | `../technical/VENUE_RECONCILIATION.md`, `../technical/EOD_RECONCILIATION.md` | dedicated reconciliation modules |
| Member Portfolio | `../technical/MEMBER_HOLDINGS_READ_MODEL.md` | member holding modules |
| Research & Market Data | `../technical/RESEARCH_DATA_PLATFORM.md` | research schemas, providers, cache and service |
| Secret handling | `../technical/SECRET_PROVIDER_AND_REDACTION.md` | metadata, resolver and redaction owners |
| Operations | `../technical/PRODUCTION_OPERATIONS.md` | monitoring, controlled operation and disaster recovery |

Rules:

- one business rule has one implementation owner;
- `docs/architecture/OWNERSHIP.md` resolves ownership conflicts;
- public compatibility changes update producer, consumer, snapshot and tests together;
- historical plans and acceptance receipts are not contracts.
