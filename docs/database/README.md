# Database Schema and Migration Guide

This is the canonical persistence entrypoint. SQLite remains the approved database for the current stage.

## 1. Data authority classes

| Class | Purpose | Examples |
|---|---|---|
| Reference/master data | stable business identity and configuration | legal entity, fund, portfolio, book, strategy, venue, account, instrument |
| Command/execution journal | accepted intent and execution lifecycle | trade command, order, execution batch, Runtime command/events, venue execution intent |
| Operational projection | low-latency monitoring, not formal accounting | `positions`, `pnl_results`, cross-spread exit plans |
| Immutable financial fact | auditable economic truth | `financial_facts` |
| Formal projection | rebuildable position, PnL and NAV | `formal_positions`, `formal_pnl_results`, formal NAV |
| Risk/approval | safety state and bounded authorization | Kill Switch, execution risk, LiveTradingSession |
| Reconciliation/operations | differences, EOD, alerts, backup and restore evidence | venue reconciliation, EOD reports, operational alerts |

A table must have one owning module and one authority class.

## 2. Shared database infrastructure

`app/database_connection.py` is the single owner of the shared SQLite connection boundary:

- resolve the configured path dynamically;
- create parent directories;
- open SQLite;
- install `sqlite3.Row`;
- enable Foreign Keys;
- commit on successful context exit;
- rollback and re-raise on exceptions;
- close in all cases.

`app/database_bootstrap.py` is the single owner of the core Platform Schema and legacy compatibility DDL:

- the complete ordered `SCHEMA_SQL`;
- fresh-database Schema execution;
- compatibility-column detection and additive `ALTER TABLE` statements;
- the partial unique execution-batch idempotency index.

`app/database_seeds.py` is the single owner of all fixed reference-data Seed vectors and insertion ordering.

`app/database.py` is now a compatibility facade and initializer only. It explicitly re-exports Connection, Bootstrap and Seed compatibility surfaces and preserves the order:

```text
Connection → Bootstrap → Seed
```

## 3. Current DDL owners

### Platform Backend

| Owner module | Primary responsibility |
|---|---|
| `app/database_bootstrap.py` | core Platform Schema and legacy compatibility DDL |
| `app/financial_fact_repository.py` | immutable financial facts, formal Position/PnL/NAV persistence and transaction boundaries |
| `app/execution_risk.py` | Kill Switch, batch risk snapshots and residual-risk actions |
| `app/venue_reconciliation_repository.py` | venue reconciliation runs and differences |
| `app/live_venue_accounting.py` | imported live economic-event accounting records |
| `app/eod_reconciliation_repository.py` | EOD reports, reviews and scale-gate persistence evidence |
| `app/live_trading_sessions.py` | two-person live-session state |
| `app/credential_security.py` | credential-rotation metadata only |
| `app/production_monitoring.py` | alerts, scans and controlled operation runs |
| `app/disaster_recovery.py` | backup and restore manifests/drill records |
| `app/schema_migrations.py` | migration ledger, `order_execution_intents`, `cross_spread_exit_plans` and ordered additive migrations |

`app/cross_spread_exit_repository.py` owns direct SQL and row mapping for the migrated cross-spread exit-plan tables after creation. `app/order_execution_intents.py` owns the idempotent intent reads and writes. Table creation remains owned by `app/schema_migrations.py`.

`app/database.py` is not a DDL or Seed Owner.

FinancialFact responsibilities are separated into Schema, Normalization, Repository, Projection Service and API modules. Only `app/financial_fact_repository.py` owns its direct SQL and protected transaction units.

### Execution Runtime

| Owner module | Primary responsibility |
|---|---|
| `app/journal.py` | command claims and persisted execution events |
| `app/venue_store.py` | normalized external order/fill/position/balance snapshots |
| `app/live_route_store.py` | deterministic live routing and atomic notional claims |

Runtime storage is not the permanent financial ledger and must not be written directly by Platform modules.

## 4. Fixed Seed authority

`app/database_seeds.py` owns the fixed organization, strategy, venue, account, balance, binding, instrument, contract-specification and mapping Seeds.

The complete values across all 15 Seed tables are pinned by SHA-256:

```text
d42f7e4f95a6efa9044b1e91b4e603f1d87f515923a57d941ee16e75109e6183
```

Changing a Seed identifier, status, default, mapping or contract value is a business-data change, not a structural refactor. It requires a dedicated Issue and explicit compatibility review.

## 5. Migration ledger

Platform migrations are declared in `platform-backend/app/schema_migrations.py`.

The `schema_migrations` table records monotonic version, unique name, SHA-256 checksum and application time. Version 1 is `existing-platform-schema-baseline` and records the existing Schema without moving tables or changing business data.

Version 2 is `cross-spread-market-exit-plans`. It additively creates:

- `order_execution_intents`, which records reduce-only and venue position-target intent by immutable TradeCommand idempotency key;
- `cross_spread_exit_plans`, which records one exit lifecycle for each successfully hedged market open, including exact text Decimals, MT5 Position Ticket, TP/SL thresholds and atomic trigger state;
- the status/creation-time lookup index used by the bounded exit monitor.

The exit-plan tables are operational execution state, not formal financial accounting inputs.

At startup, pending migrations are applied in order. Reapplication is idempotent; changing an applied migration name or checksum fails closed.

Status endpoint:

```http
GET /api/v1/ops/schema-migrations
```

## 6. Rules for a new migration

1. Never edit an applied migration.
2. Add one new version after the current highest version.
3. Use additive SQL by default.
4. Put data backfills in a separately testable step.
5. Record owner, authority class, compatibility window and rollback behavior.
6. Add fresh, existing, repeated-startup and checksum-drift tests.
7. Do not combine a migration with unrelated refactoring.

## 7. High-risk changes requiring explicit review

- table or column deletion;
- column type or meaning change;
- authority transfer between operational and formal data;
- identifier or Seed replacement;
- PnL, position or order-state backfill;
- encryption/credential storage changes;
- switching away from SQLite.

These require a dedicated Issue, backup/restore evidence and an explicit rollback or forward-fix strategy.

## 8. Completed decomposition

```text
app/database_connection.py  # shared path and transaction-managed connection
app/database_bootstrap.py   # core Schema and compatibility DDL
app/database_seeds.py       # fixed reference-data Seeds
app/database.py             # compatibility facade / initializer
```

The Bootstrap Schema is pinned by SHA-256 `421f0625ffe3a8a26ca48bc827e64bd6aa6b2e49d95faef0b17313e808375801`. Fresh-database, legacy-database, repeated-initialization and exhaustive Seed snapshots prove structural equivalence.
