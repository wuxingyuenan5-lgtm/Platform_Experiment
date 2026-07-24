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

## 2. Current DDL owners

### Platform Backend

| Owner module | Primary responsibility |
|---|---|
| `app/database.py` | core reference data, commands, orders, fills, operational projections and initial seed data |
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

`app/financial_facts.py` owns normalization, hashing, formal-accounting calculations, rebuild orchestration and API routes. It does not own DDL or direct SQL. Fact+audit, Position+PnL, rebuild-clear and NAV+audit transaction units are owned by `app/financial_fact_repository.py`.

### Execution Runtime

| Owner module | Primary responsibility |
|---|---|
| `app/journal.py` | command claims and persisted execution events |
| `app/venue_store.py` | normalized external order/fill/position/balance snapshots |
| `app/live_route_store.py` | deterministic live routing and atomic notional claims |

Runtime storage is not the permanent financial ledger and must not be written directly by Platform modules.

## 3. Migration ledger

Platform migrations are declared in `platform-backend/app/schema_migrations.py`.

The `schema_migrations` table records:

- monotonic integer version;
- unique migration name;
- SHA-256 checksum of version, name and statements;
- application time.

Version 1 is `existing-platform-schema-baseline`. It intentionally records the already-existing schema without moving tables or changing business data.

At application startup, the schema-governance router applies pending migrations. Reapplying the same migration is idempotent. Changing an already-applied migration name or checksum fails closed.

Status endpoint:

```http
GET /api/v1/ops/schema-migrations
```

## 4. Rules for a new migration

1. Never edit an applied migration.
2. Add one new version after the current highest version.
3. Use additive SQL by default: new table, new nullable column, new index or new compatibility view.
4. Put data backfills in a separately testable step; do not hide a large backfill in service startup.
5. Record owner, authority class, compatibility window and rollback behavior in the task packet.
6. Add tests for fresh database, existing database, repeated startup and checksum drift.
7. Do not combine a schema migration with unrelated refactoring.

## 5. High-risk changes requiring explicit review

- table or column deletion;
- column type or meaning change;
- authority transfer between operational and formal data;
- identifier or seed replacement;
- PnL, position or order-state backfill;
- encryption/credential storage changes;
- switching away from SQLite.

These require a dedicated Issue, migration task packet, backup/restore evidence and an explicit rollback or forward-fix strategy.

## 6. Planned decomposition

The next safe decomposition is not a table rewrite. It is:

```text
platform-backend/app/database/
  connection.py
  bootstrap.py
  migrations/
  seeds/
```

That move should happen only after all current DDL owners are registered in the ledger and compatibility tests prove identical fresh/existing database behavior.
