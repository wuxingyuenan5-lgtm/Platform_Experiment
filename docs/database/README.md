# Database Schema and Migration Guide

This is the canonical persistence entrypoint. SQLite remains the approved database for the current stage.

## 1. Data authority classes

| Class | Purpose | Examples |
|---|---|---|
| Reference/master data | stable business identity and configuration | legal entity, fund, portfolio, book, strategy, venue, account, instrument |
| Command/execution journal | accepted intent and execution lifecycle | trade command, order, execution batch, Runtime command/events, venue execution intent |
| Operational projection | low-latency monitoring, not formal accounting | `positions`, `pnl_results`, cross-spread Exit Plans |
| Immutable financial fact | auditable economic truth | `financial_facts` |
| Formal projection | rebuildable position, PnL and NAV | `formal_positions`, `formal_pnl_results`, formal NAV |
| Risk/approval | safety state and bounded authorization | Kill Switch, execution risk, LiveTradingSession |
| Reconciliation/operations | differences, EOD, alerts, backup and restore evidence | venue reconciliation, EOD reports, operational alerts |

A table must have one owning module and one authority class.

## 2. Shared database infrastructure

`app/database_connection.py` owns the shared SQLite connection boundary: configured path, parent creation, `sqlite3.Row`, Foreign Keys, transaction commit/rollback and close.

`app/database_bootstrap.py` owns the core Platform Schema and legacy compatibility DDL.

`app/database_seeds.py` owns fixed reference-data Seed vectors and insertion order.

`app/database.py` is a compatibility facade and initializer only:

```text
Connection → Bootstrap → Seed
```

## 3. DDL and SQL owners

### Platform Backend

| Owner module | Primary responsibility |
|---|---|
| `app/database_bootstrap.py` | core Platform Schema and legacy compatibility DDL |
| `app/financial_fact_repository.py` | immutable financial facts and formal Position/PnL/NAV persistence |
| `app/execution_risk.py` | Kill Switch, batch risk snapshots and residual-risk actions |
| `app/venue_reconciliation_repository.py` | Venue reconciliation runs and Differences |
| `app/live_venue_accounting.py` | imported live economic-event accounting records |
| `app/eod_reconciliation_repository.py` | EOD reports, reviews and scale-gate evidence |
| `app/live_trading_sessions.py` | two-person live-session state |
| `app/credential_security.py` | credential-rotation metadata only |
| `app/production_monitoring.py` | alerts, scans and controlled operation runs |
| `app/disaster_recovery.py` | backup and restore manifests/drills |
| `app/schema_migrations.py` | migration ledger and ordered additive migrations |
| `app/cross_spread_exit_repository.py` | direct SQL and row mapping for migrated Exit Plans |
| `app/order_execution_intents.py` | idempotent reduce-only and position-target intent reads/writes |

Table creation and additive column migration remain owned by `app/schema_migrations.py`. `app/database.py` is not a DDL or Seed owner.

### Execution Runtime

| Owner module | Primary responsibility |
|---|---|
| `app/journal.py` | command claims and persisted execution events |
| `app/venue_store.py` | normalized external Order/Fill/Position/Balance snapshots |
| `app/live_route_store.py` | deterministic live routing and atomic notional claims |

Runtime storage is not the permanent financial ledger and must not be written directly by Platform modules.

## 4. Fixed Seed authority

`app/database_seeds.py` owns fixed organization, strategy, venue, account, balance, binding, instrument, contract-specification and mapping Seeds.

The values across all maintained Seed tables are pinned by SHA-256:

```text
d42f7e4f95a6efa9044b1e91b4e603f1d87f515923a57d941ee16e75109e6183
```

A Seed identifier, status, default, mapping or contract change is a business-data change and requires a dedicated compatibility review.

## 5. Migration ledger

Platform migrations are declared in `platform-backend/app/schema_migrations.py`.

`schema_migrations` records monotonic version, unique name, SHA-256 checksum and application time. Migrations are applied in order. Reapplication is idempotent; changing an applied name or checksum fails closed.

### Version 1 — `existing-platform-schema-baseline`

Records the existing Schema without moving tables or changing business data.

### Version 2 — `cross-spread-market-exit-plans`

Additively creates:

- `order_execution_intents` for reduce-only and Venue position-target intent by immutable command idempotency key;
- `cross_spread_exit_plans` for one exit lifecycle per successfully hedged Open, including exact text Decimals, MT5 Position Ticket, TP/SL thresholds and atomic trigger state;
- the status/creation-time lookup index used by the bounded monitor.

### Version 3 — `cross-spread-exit-execution-modes`

Additively adds to `cross_spread_exit_plans`:

```text
take_profit_execution_mode TEXT NOT NULL DEFAULT 'market'
stop_loss_execution_mode   TEXT NOT NULL DEFAULT 'market'
```

Both columns have a `CHECK` constraint allowing only `market` or `limit`.

Compatibility contract:

- existing rows retain all prior data;
- existing rows automatically become `market / market`;
- no backfill derives values from historical thresholds;
- the migration is additive and does not alter financial facts or formal projections;
- reverting application code leaves harmless Market defaults in place; the applied migration itself is not edited or automatically removed.

Exit Plans are operational execution state, not formal financial accounting inputs.

Status endpoint:

```http
GET /api/v1/ops/schema-migrations
```

## 6. Rules for a new migration

1. Never edit an applied migration.
2. Add one new version after the current highest version.
3. Use additive SQL by default.
4. Put data backfills in a separately testable step.
5. Record owner, authority class, compatibility and rollback/forward-fix behavior.
6. Add fresh, existing-row, repeated-startup and checksum-drift tests.
7. Do not combine unrelated behavior.

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
app/schema_migrations.py    # immutable additive migration ledger
```

The Bootstrap Schema remains pinned by SHA-256 `421f0625ffe3a8a26ca48bc827e64bd6aa6b2e49d95faef0b17313e808375801`. Fresh-database, legacy-database, repeated-initialization and Seed snapshots prove structural equivalence.
