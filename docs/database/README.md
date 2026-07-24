# Database Schema and Migration Guide

This is the canonical persistence entrypoint. SQLite remains the approved database for the current stage.

## 1. Data authority classes

| Class | Purpose | Examples |
|---|---|---|
| Reference/master data | stable business identity and configuration | legal entity, fund, portfolio, book, strategy, venue, account, instrument |
| Command/execution journal | accepted intent and execution lifecycle | trade command, order, execution batch, Runtime command/events |
| Operational projection | low-latency monitoring, not formal accounting | `positions`, `pnl_results` |
| Immutable financial fact | auditable economic truth | `financial_facts` |
| Formal projection | rebuildable position, PnL and NAV | `formal_positions`, `formal_pnl_results`, formal NAV |
| Risk/approval | safety state and bounded authorization | Kill Switch, execution risk, LiveTradingSession |
| Reconciliation/operations | differences, EOD, alerts, backup and restore evidence | venue reconciliation, EOD reports, operational alerts |

A table must have one owning module and one authority class.

## 2. Shared connection and core bootstrap

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

`app/database.py` explicitly re-exports the connection and Bootstrap compatibility surfaces. It currently owns initializer ordering and fixed reference-data seeds, but it must not reimplement connection or core DDL behavior.

## 3. Current DDL owners

### Platform Backend

| Owner module | Primary responsibility |
|---|---|
| `app/database_bootstrap.py` | core Platform Schema and legacy compatibility DDL |
| `app/financial_fact_repository.py` | immutable financial facts, formal Position/PnL/NAV persistence and transaction boundaries |
| `app/execution_risk.py` | Kill Switch, batch risk snapshots and residual-risk actions |
| `app/venue_reconciliation.py` | venue reconciliation runs and differences |
| `app/live_venue_accounting.py` | imported live economic-event accounting records |
| `app/eod_reconciliation.py` | EOD reports, reviews and scale-gate evidence |
| `app/live_trading_sessions.py` | two-person live-session state |
| `app/credential_security.py` | credential-rotation metadata only |
| `app/production_monitoring.py` | alerts, scans and controlled operation runs |
| `app/disaster_recovery.py` | backup and restore manifests/drill records |
| `app/schema_migrations.py` | migration ledger and ordered additive migrations |

`app/database.py` is a compatibility facade and initializer, not a core DDL Owner. Fixed reference-data Seed ownership remains there only until the dedicated Seed extraction.

FinancialFact responsibilities are separated into Schema, Normalization, Repository, Projection Service and API modules. Only `app/financial_fact_repository.py` owns its direct SQL and protected transaction units.

### Execution Runtime

| Owner module | Primary responsibility |
|---|---|
| `app/journal.py` | command claims and persisted execution events |
| `app/venue_store.py` | normalized external order/fill/position/balance snapshots |
| `app/live_route_store.py` | deterministic live routing and atomic notional claims |

Runtime storage is not the permanent financial ledger and must not be written directly by Platform modules.

## 4. Migration ledger

Platform migrations are declared in `platform-backend/app/schema_migrations.py`.

The `schema_migrations` table records:

- monotonic integer version;
- unique migration name;
- SHA-256 checksum of version, name and statements;
- application time.

Version 1 is `existing-platform-schema-baseline`. It records the already-existing schema without moving tables or changing business data.

At application startup, the schema-governance router applies pending migrations. Reapplying the same migration is idempotent. Changing an already-applied migration name or checksum fails closed.

Status endpoint:

```http
GET /api/v1/ops/schema-migrations
```

## 5. Rules for a new migration

1. Never edit an applied migration.
2. Add one new version after the current highest version.
3. Use additive SQL by default: new table, new nullable column, new index or new compatibility view.
4. Put data backfills in a separately testable step; do not hide a large backfill in service startup.
5. Record owner, authority class, compatibility window and rollback behavior in the task packet.
6. Add tests for fresh database, existing database, repeated startup and checksum drift.
7. Do not combine a schema migration with unrelated refactoring.

## 6. High-risk changes requiring explicit review

- table or column deletion;
- column type or meaning change;
- authority transfer between operational and formal data;
- identifier or seed replacement;
- PnL, position or order-state backfill;
- encryption/credential storage changes;
- switching away from SQLite.

These require a dedicated Issue, migration task packet, backup/restore evidence and an explicit rollback or forward-fix strategy.

## 7. Decomposition sequence

The safe decomposition is structural, not a table rewrite:

```text
app/database_connection.py  # completed
app/database_bootstrap.py   # completed: core Schema and compatibility DDL
app/database_seeds.py       # pending: fixed reference-data seeds
app/database.py             # compatibility facade / initializer
```

Every step requires fresh-database, existing-database and repeated-initialization equivalence. The Bootstrap Schema text is pinned by SHA-256 `421f0625ffe3a8a26ca48bc827e64bd6aa6b2e49d95faef0b17313e808375801`. No structural extraction may be combined with business Schema or Seed changes.
