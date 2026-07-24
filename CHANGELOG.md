# Changelog

## Unreleased

### Fixed database Seed ownership — Issue #53 / PR #54

- Extracted every fixed reference-data Seed vector and insertion statement into `platform-backend/app/database_seeds.py`.
- Preserved `app.database.seed_reference_data` as an identical compatibility export.
- Reduced `app/database.py` to explicit Connection/Bootstrap/Seed compatibility exports and `Connection → Bootstrap → Seed` initialization orchestration.
- Added an exhaustive all-row/all-field snapshot across the 15 fixed Seed tables, pinned by SHA-256 `d42f7e4f95a6efa9044b1e91b4e603f1d87f515923a57d941ee16e75109e6183`.
- Added explicit checks for simulation/active/paused safety defaults and the existing XAUUSD contract specification.
- Added repeated-initialization full-snapshot equivalence and static Seed ownership checks.
- Added the Seed boundary to progressive Pyright.
- Retained every Seed ID/value/order, Schema checksum, compatibility DDL, migration-ledger entry, API/trading/accounting behavior and both Live Write defaults unchanged.

### Core database Bootstrap ownership — Issue #50 / PR #51

- Extracted the complete ordered core `SCHEMA_SQL` and legacy compatibility DDL into `platform-backend/app/database_bootstrap.py`.
- Preserved `app.database.SCHEMA_SQL`, `migrate_schema` and `ensure_column` as identical compatibility exports.
- Kept startup order unchanged: shared Connection → core Bootstrap → fixed reference Seeds.
- Transferred the machine-checked core DDL Owner from `app/database.py` to `app/database_bootstrap.py`.
- Pinned the complete Schema text with SHA-256 `421f0625ffe3a8a26ca48bc827e64bd6aa6b2e49d95faef0b17313e808375801`.
- Added Bootstrap ownership and initialization-order architecture tests.
- Reused fresh-database table/index/Seed snapshots, legacy compatibility-column/index tests and repeated-initialization idempotency to prove equivalent startup behavior.
- Added the Bootstrap boundary to progressive Pyright.
- Retained every table, index, compatibility column, fixed Seed, migration-ledger entry, API/trading/accounting behavior and both Live Write defaults unchanged.

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
- Preserved `app.financial_facts` as the compatibility, normalization, hashing, calculation, rebuild-orchestration and API surface.
- Moved existing DDL, queries and row mapping without changing table, index, migration or API semantics.
- Preserved fact+audit, Position+PnL, rebuild-clear and NAV+audit transaction boundaries.
- Added forced-rollback integration tests proving those transaction units leave no partial state.
- Added repository ownership checks that forbid SQL or direct database access from `app/financial_facts.py`.
- Added the repository boundary to progressive Pyright and registered it as the formal-accounting DDL Owner.
- Retained idempotency, content hashing, FX conversion, contract multipliers, average cost, PnL attribution, rebuild results, trading behavior and both Live Write defaults unchanged.

### FinancialFact public schema ownership — Issue #40 / PR #41

- Extracted FinancialFact, formal Position, formal PnL, NAV and projection-rebuild Pydantic DTOs into `platform-backend/app/financial_fact_schemas.py`.
- Preserved `app.financial_facts` compatibility exports as the same Python class objects.
- Added JSON Schema snapshots for public field aliases and required-field sets.
- Added validator compatibility coverage for trade-fact shape requirements.
- Added the schema module to progressive Pyright and moved the Pydantic-specific Ruff exception to the new owner.
- Retained all FinancialFact SQL, normalization, content hashing, FX conversion, average-cost, PnL attribution, rebuild and API routing implementation unchanged.
- Kept database schema, trading behavior, credentials and both Live Write defaults unchanged.

### Project operating system and engineering hardening — Issue #36 / PR #37

- Consolidated human and Agent entrypoints around `00-人工可读目录/README.md`, `docs/codex/context-map.md`, `docs/codex/current-state.md`, and one canonical task template.
- Added bounded `tasks/issue-<number>-<slug>.md` packets so new conversations load only the active task, target module and direct tests.
- Enforced one Issue, one Issue-numbered branch, one task packet and one open PR through `scripts/check-workstream.py` and Platform CI.
- Added engineering Issue/PR templates and documented the complete Git/version workflow.
- Verified PR #28 was already merged, identified closed PRs #8/#13/#30 as superseded, and returned reviewed duplicate/superseded branch refs to the stable `main` baseline.
- Added a non-destructive `schema_migrations` ledger with monotonic versions, immutable checksums, startup application, status API and repeated-startup/mutation tests.
- Added a complete DDL Owner and data-authority inventory without moving or changing existing business tables.
- Added explicit Platform–Runtime `runtime-command` / `runtime-event` V1.0 contracts, dual-side models and executable JSON snapshots.
- Made incompatible Runtime events fail closed as `result_unknown` instead of deterministic failure or automatic resubmission.
- Added blocking progressive Pyright gates for critical Backend and Runtime execution/persistence boundaries.
- Added frontend changed-file zero-warning ESLint enforcement while retaining full lint for the maintained trading surface.
- Added failure injection for unsupported versions, Fill-before-ACK, duplicate Fill and unknown external outcomes without Gateway replay.
- Added the controlled production-acceptance matrix and mandatory stop conditions.
- Synchronized README, architecture, database, operations, technical-debt and current-state documentation.
- Final verified engineering behavior keeps existing trading formulas, order semantics, business schema, credentials, risk gates and both Live Write defaults unchanged.

### SecretProvider, rotation metadata, and redaction — Production Gate 5C

- Added explicit Secret References: `secret://environment/<name>` and `secret://windows-credential-manager/<name>`.
- Retained legacy `secret://<name>` as migration-only Environment compatibility and exposed `legacyReference` in inspection metadata.
- Added a pluggable Runtime `SecretProvider` contract with `inspect` and `resolve` operations.
- Added Environment Provider field-existence and version metadata without exposing values.
- Added Windows Credential Manager Provider using `VariableGlobal/<name>/<FIELD>` targets, injected Provider tests, and fail-closed behavior outside Windows or without its optional dependency.
- Rejected unknown providers and malformed references without automatic fallback.
- Extended Runtime credential inspection with Provider, Secret Name, Version, available/missing fields, and legacy status.
- Updated Runtime defaults and `.env.live.example` to use explicit Provider references.
- Added Backend credential-rotation metadata records and authenticated APIs.
- Rotation records contain Reference, Provider, Version, time, actor, reason, and idempotency hash only; old and new values are never persisted.
- Added idempotent replay and `409 Conflict` for reused rotation identities with different payloads.
- Restricted rotation writes to admin and reads to audit-capable roles.
- Added recursive Backend and Runtime redactors for nested structures, sensitive keys, Bearer tokens, private-key blocks, URL credentials, assignments, and exception text.
- Standardized redacted output as `[REDACTED]` while retaining non-sensitive operational context.
- Added Environment, Windows, legacy, invalid-provider, missing-field, rotation, RBAC, idempotency, and redaction golden tests.
- Expanded Platform CI strict gates for Provider, Rotation, Redaction, tests, and Repository Secret Scan.
- Added `docs/planning/V6-Production-Gate-密钥托管与脱敏.md` and `docs/technical/SECRET_PROVIDER_AND_REDACTION.md`.
- Synchronized Issue #24, PR #25, README, START-HERE, API Specification, Release Gate, overall plan, live template, and this Changelog.
- Kept Platform and Runtime Live Write disabled; controlled-host Provider setup, real-account read-only verification, version rotation, Runtime restart, minimum-size trading, and EOD remain operational acceptance items.
- Deferred monitoring, alerting, scheduling, backup, and restore drills to Production Gate 5D.

### Production authentication and two-person live sessions — Production Gate 5A/5B

- Added live-environment Bearer authentication with SHA-256 credential matching.
- Added default-deny RBAC for viewer, researcher, trader, risk_officer, operations, and admin.
- Bound actor/reviewer fields to authenticated Principals.
- Added idempotent, bounded `LiveTradingSession` requests and two-person approval.
- Rejected Applicant self-approval, including admin self-approval.
- Blocked approval on Kill Switch, open/accepted differences, overlapping sessions, invalid limits, and EOD/scale-gate failures.
- Required Live Commands to atomically claim one approved session before Order insertion and Runtime submission.
- Added SQLite `BEGIN IMMEDIATE` serialization for concurrent daily-notional claims.
- Added Repository Secret Scan and synchronized Production Gate documentation.
- Completed Platform CI and merged through PR #23.

### Live end-of-day reconciliation — Phase 4D

- Added EOD Reports with Business Date, IANA Timezone, Valuation Time, Due At, SLA, owner, and immutable review.
- Reconciled business-day orders plus unresolved historical orders.
- Imported Position, Balance, Funding, Swap, Commission, and Fee.
- Rebuilt Formal Position/PnL and generated point-in-time Formal NAV.
- Blocked scale review on open/accepted differences, skipped events, missing accounts, incomplete PnL, or errors.
- Limited approval to `approved_same_limits`; EOD never raises limits or enables Live Write.
- Merged through PR #21.

### Controlled Bybit and MT5 live adapters — Phase 4C

- Implemented Bybit V5 Order, Execution, Position, Wallet, Funding, and Fee mappings.
- Implemented MT5 Order, Deal, Position, Account, Swap, Commission, and Fee mappings.
- Added deterministic external identities, Account Routing, Runtime Live Gate, allowlists, and notional limits.
- Added Live Economic Event import into immutable FinancialFact.
- Added live configuration template, read-only preflight, and small-capital acceptance handbook.
- Merged through PR #19.

### Venue query and reconciliation differences — Phase 4B

- Added Runtime Query APIs for Order, Fill, Position, Balance, and cancellation.
- Added Journal-first and Venue-second unknown-result recovery.
- Imported external snapshots into FinancialFact.
- Added Reconciliation Runs, immutable Differences, and explicit resolution states.

### Execution risk controls — Phase 4A

- Added global, strategy, and account Kill Switches.
- Added maximum leg delay, residual-notional thresholds, and failure-action policies.
- Added idempotent RiskActions for hold/escalate, cancel, flatten, and substitute hedge.

### Immutable financial facts and formal accounting — Phase 3

- Added immutable FinancialFact with dual identities, payload hashes, Catalog-derived units and multipliers, explicit FX, and quality states.
- Added rebuildable Formal Position/PnL and one-valuation-time multi-account NAV.
- Separated Trading, Funding, Swap, Fee, FX, and Total PnL.

### Command authority and recovery — Phase 2

- Unified single- and multi-leg execution through TradeCommand and ExecutionBatch.
- Added business idempotency, payload-conflict detection, dynamic Catalog, and `result_unknown` recovery without resubmission.

### Trading safety foundation — Phase 1

- Added fail-closed Account/Instrument/Contract validation.
- Added Runtime atomic command claims before Gateway side effects.
- Added Live global switch, secret-reference-only storage, CI, and engineering documentation governance.
