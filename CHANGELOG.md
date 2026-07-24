# Changelog

## Unreleased

### SQLite connection ownership — Issue #48 / PR #49

- Extracted configured database path resolution and transaction-managed SQLite connections into `platform-backend/app/database_connection.py`.
- Preserved `app.database.connection` and `app.database.database_path` as identical compatibility exports for all existing callers.
- Preserved dynamic settings lookup, parent-directory creation, `sqlite3.Row`, Foreign Keys, successful Commit, exceptional Rollback/re-raise and unconditional Close behavior.
- Removed `sqlite3.connect` and Context Manager implementation from `app/database.py` while leaving core Schema SQL, compatibility DDL and fixed Seeds in place.
- Added direct connection/path/commit/rollback/foreign-key tests and architecture ownership checks.
- Added fresh-database table/index/Seed snapshots, repeated-initialization idempotency and existing legacy database compatibility-column/index coverage.
- Added the connection boundary to progressive Pyright.
- Retained every table, index, compatibility column, Seed identifier, API/trading/accounting behavior and both Live Write defaults unchanged.

### Formal projection service ownership — Issue #46 / PR #47

- Extracted average-cost and realized-PnL position updates into `platform-backend/app/financial_projection_service.py`.
- Moved Trading/Funding/Swap/Fee/FX component aggregation, incomplete-quality propagation and formal Position/PnL writes behind the Projection Service.
- Moved strategy rebuild pair orchestration, counts and audit-payload generation into the Projection Service.
- Moved formal NAV account coverage, missing-account ordering, equity, quality and capital-base division into the Projection Service.
- Preserved `app.financial_facts` compatibility callables while keeping catalog resolution, immutable fact recording, HTTP error mapping and API routes in the API module.
- Kept SQL, DDL, row mapping and protected transaction units in `app.financial_fact_repository.py`.
- Added exact average-cost, component attribution, incomplete-quality, rebuild-audit and NAV calculation golden tests.
- Added architecture checks preventing projection formulas or Repository orchestration from returning to the API layer and preventing FastAPI/config dependencies in the Projection Service.
- Added the Projection Service to progressive Pyright.
- Retained FinancialFact normalization/hash identity, repository transactions, API schemas/routes, database migrations, trading behavior and both Live Write defaults unchanged.

### FinancialFact normalization ownership — Issue #44 / PR #45

- Extracted currency, quantity-unit, contract-multiplier, FX/data-quality, Decimal, UTC timestamp and payload JSON canonicalization into `platform-backend/app/financial_fact_normalization.py`.
- Added an explicit `FinancialFactNormalizationContext` so the Policy consumes resolved catalog values without depending on Repository or database access.
- Moved normalized-content SHA-256 ownership into the Policy while preserving the exact JSON serialization parameters and immutable fact identity.
- Preserved `app.financial_facts.normalize_fact(request)`, `utc_iso` and `decimal_text` compatibility surfaces.
- Added full normalized-dictionary and exact hash golden vectors plus API status, persisted-value and currency/FX equivalence tests.
- Added architecture checks preventing normalization/error/hash implementation from returning to the service layer or gaining a persistence dependency.
- Added the Policy to progressive Pyright.
- Retained repository SQL/transactions, API schemas/routes, average-cost and PnL formulas, migrations, trading behavior and both Live Write defaults unchanged.

### FinancialFact persistence ownership — Issue #42 / PR #43

- Extracted FinancialFact and formal-accounting direct SQLite access into `platform-backend/app/financial_fact_repository.py`.
- Preserved `app.financial_facts` compatibility while moving DDL, queries and row mapping without changing table, index, migration or API semantics.
- Preserved fact+audit, Position+PnL, rebuild-clear and NAV+audit transaction boundaries.
- Added forced-rollback integration tests and repository ownership checks.
- Added the repository boundary to progressive Pyright and registered it as the formal-accounting DDL Owner.

### FinancialFact public schema ownership — Issue #40 / PR #41

- Extracted FinancialFact, formal Position, formal PnL, NAV and rebuild DTOs into `platform-backend/app/financial_fact_schemas.py`.
- Preserved compatibility exports as the same Python class objects.
- Added JSON Schema snapshots and validator compatibility coverage.
- Added the schema module to progressive Pyright.

### Project operating system and engineering hardening — Issue #36 / PR #37

- Consolidated human and Agent entrypoints and added bounded Issue-numbered task packets.
- Enforced one Issue, one branch, one task packet and one open PR through Platform CI.
- Added engineering templates, schema migration ledger, DDL Owner inventory, versioned Platform–Runtime V1 contracts, progressive typing, frontend no-new-debt, failure injection and controlled acceptance documentation.
- Kept trading formulas, order semantics, business Schema, credentials, risk gates and both Live Write defaults unchanged.

### SecretProvider, rotation metadata, and redaction — Production Gate 5C

- Added explicit Environment and Windows Credential Manager Secret References and a pluggable Runtime SecretProvider.
- Added credential-rotation metadata, recursive redaction, RBAC/idempotency tests and Repository Secret Scan.
- Kept both Live Write gates disabled; controlled-host acceptance remains operational work.

### Production authentication and two-person live sessions — Production Gate 5A/5B

- Added live-environment Bearer authentication, default-deny RBAC and bounded two-person LiveTradingSession approval.
- Required approved sessions before Live Commands and added SQLite serialization for concurrent notional claims.
- Completed Platform CI and merged through PR #23.

### Live end-of-day reconciliation — Phase 4D

- Added EOD Reports, formal financial rebuild/NAV, difference and scale-gate blocking, and immutable review.
- Merged through PR #21.

### Controlled Bybit and MT5 live adapters — Phase 4C

- Implemented controlled Bybit/MT5 mappings, deterministic identities, routing, Runtime Live Gate, limits and live accounting import.
- Merged through PR #19.

### Venue query and reconciliation differences — Phase 4B

- Added Runtime query APIs, Journal-first unknown-result recovery and immutable reconciliation differences.

### Execution risk controls — Phase 4A

- Added Kill Switches, residual-risk thresholds and idempotent RiskActions.

### Immutable financial facts and formal accounting — Phase 3

- Added immutable FinancialFact, rebuildable Formal Position/PnL/NAV and separated PnL components.

### Command authority and recovery — Phase 2

- Unified execution through TradeCommand/ExecutionBatch with idempotency and `result_unknown` recovery.

### Trading safety foundation — Phase 1

- Added fail-closed Catalog validation, Runtime command claims, Live global switch and documentation governance.
