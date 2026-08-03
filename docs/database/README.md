# Database Schema and Migration Guide

This is the canonical persistence entrypoint. SQLite remains the approved database for the current stage.

## 1. Data authority classes

| Class | Purpose | Examples |
|---|---|---|
| Reference/master data | stable business identity and configuration | legal entity, fund, portfolio, book, strategy, venue, account, instrument |
| Human identity and access | browser-user identity, password/session state and bounded account recovery | `users`, `user_sessions`, `password_reset_tickets` |
| Command/execution journal | accepted intent and execution lifecycle | trade command, order, execution batch, Runtime command/events, venue execution intent |
| Operational projection | low-latency monitoring, not formal accounting | `positions`, `pnl_results`, cross-spread Exit Plans |
| Immutable financial fact | auditable economic truth | `financial_facts` |
| Formal projection | rebuildable position, PnL and NAV | `formal_positions`, `formal_pnl_results`, formal NAV |
| Risk/approval | safety state and bounded authorization | Kill Switch, execution risk, LiveTradingSession |
| Reconciliation/operations | differences, EOD, alerts, backup and restore evidence | venue reconciliation, EOD reports, operational alerts |

A table must have one owning module and one authority class.

Human identity and browser Session rows are security state. They are not reference Seeds, execution credentials, LiveTradingSessions or formal financial records.

## 2. Shared database infrastructure

`app/database_connection.py` owns the shared SQLite connection boundary: configured path, parent creation, `sqlite3.Row`, Foreign Keys, transaction commit/rollback and close.

`app/database_bootstrap.py` owns the core Platform Schema and legacy compatibility DDL.

`app/database_seeds.py` owns fixed reference-data Seed vectors and insertion order.

`app/database.py` is a compatibility facade and initializer only:

```text
Connection → Bootstrap → Seed
```

Ordered additive migrations are applied separately by `app/schema_migrations.py`. User-system code must not add DDL to request handlers, repositories or service methods.

## 3. DDL and SQL owners

### Platform API

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
| `app/schema_migrations.py` | migration ledger and ordered additive migrations, including user-system tables and audit columns |
| `app/cross_spread_exit_repository.py` | direct SQL and row mapping for migrated Exit Plans |
| `app/order_execution_intents.py` | idempotent reduce-only, position-target and Runtime execution-policy intent reads/writes |
| `app/user_repository.py` | direct user, browser Session and account-recovery persistence after Migration 5 has created the schema |

Table creation and additive column migration remain owned by `app/schema_migrations.py`. `app/database.py` is not a DDL or Seed owner. `app/user_repository.py` may read and write user-system rows but may not create or alter their schema.

### Platform Execution Runtime

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

The user system intentionally has no default CEO Seed and no committed password. The first CEO is created through the interactive `python -m app.user_cli create-ceo` command after migrations have applied. Test users use isolated fixtures and fictitious values.

## 5. Migration ledger

Platform migrations are declared in `platform-api/app/schema_migrations.py`.

`schema_migrations` records monotonic version, unique name, SHA-256 checksum and application time. Migrations are applied in order. Reapplication is idempotent; changing an applied name or checksum fails closed.

### Version 1 — `existing-platform-schema-baseline`

Records the existing Schema without moving tables or changing business data.

### Version 2 — `cross-spread-market-exit-plans`

Additively creates:

- `order_execution_intents` for reduce-only and Venue position target intent by immutable command idempotency key;
- `cross_spread_exit_plans` for one exit lifecycle per successfully hedged Open, including exact text Decimals, MT5 Position Ticket, TP/SL thresholds and atomic trigger state;
- the status/creation-time lookup index used by the bounded monitor.

### Version 3 — `cross-spread-exit-execution-modes`

Additively adds to `cross_spread_exit_plans`:

```text
take_profit_execution_mode TEXT NOT NULL DEFAULT 'market'
stop_loss_execution_mode   TEXT NOT NULL DEFAULT 'market'
```

Both columns allow only `market` or `limit`. Existing rows retain all prior data and become `market / market`.

### Version 4 — `cross-spread-limit-execution-policies`

Additively adds:

```text
order_execution_intents.execution_policy
    default | fok | post_only_chase

cross_spread_exit_plans.take_profit_limit_strategy
    fok | post_only_chase

cross_spread_exit_plans.stop_loss_limit_strategy
    fok | post_only_chase
```

Compatibility contract:

- existing Venue execution intents automatically become `default`;
- existing Exit Plans automatically receive `fok / fok` Limit strategies;
- Market execution modes ignore the stored Limit strategy;
- old Limit requests remain FOK because API defaults and migrated rows use `fok`;
- the migration is additive and does not alter quantities, thresholds, financial facts or formal projections;
- the migration does not enable PostOnly Chase, Live Write or the exit monitor;
- an applied migration is never edited or automatically removed.

Exit Plans and Venue execution intents are operational execution state, not formal financial accounting inputs.

### Version 5 — `user-identity-sessions-and-audit`

Additively creates:

- `users` as the authoritative browser-user identity and lifecycle table;
- `user_sessions` for opaque server-side browser Sessions, CSRF hash, expiry, idle expiry, reauthentication time, revocation and authorization version;
- `password_reset_tickets` for single-use, short-lived account-recovery tokens stored only as hashes;
- partial unique indexes for normalized email and phone;
- user lifecycle/role, temporary lock, Session expiry and active recovery-ticket indexes;
- queryable user-system audit columns on the existing `audit_events` table.

Compatibility and safety contract:

- no existing user, API-key credential, execution, accounting, risk or LiveTradingSession row is rewritten;
- no default CEO, default password, raw Session token, CSRF token or reset token is inserted;
- browser business roles are restricted to `ceo`, `tech_lead`, `employee` and `member`;
- public requested roles are restricted to `employee` and `member`;
- lifecycle status is `pending`, `active`, `disabled` or `rejected`; temporary login lock remains separate in `locked_until`;
- an active or disabled account must have a formal role, while pending or rejected applications must not;
- Session and recovery tokens remain application-generated opaque secrets whose database values are SHA-256 hashes;
- audit columns are nullable to preserve existing audit writers during the implementation transition;
- Migration 5 does not enable browser routes, alter API-key authentication or relax any Live gate by itself.

Authority classification:

```text
users                  → human identity and access
user_sessions          → human identity and access security state
password_reset_tickets → human identity and access recovery state
audit_events additions → cross-domain audit query metadata
```

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
8. Never commit a real user, password hash, Session token, reset token, email, phone number or customer holding as a migration or Seed.

## 7. High-risk changes requiring explicit review

- table or column deletion;
- column type or meaning change;
- authority transfer between operational and formal data;
- identifier or Seed replacement;
- PnL, position or order-state backfill;
- encryption/credential storage changes;
- switching away from SQLite;
- importing real legacy users or password hashes;
- weakening the last-active-CEO or Session-invalidation invariants.

These require a dedicated Issue, backup/restore evidence and an explicit rollback or forward-fix strategy.

## 8. Completed decomposition

```text
app/database_connection.py  # shared path and transaction-managed connection
app/database_bootstrap.py   # core Schema and compatibility DDL
app/database_seeds.py       # fixed reference-data Seeds
app/database.py             # compatibility facade / initializer
app/schema_migrations.py    # immutable additive migration ledger
app/user_repository.py      # user-system row persistence after migration
```

The Bootstrap Schema remains pinned by SHA-256 `421f0625ffe3a8a26ca48bc827e64bd6aa6b2e49d95faef0b17313e808375801`. Fresh-database, legacy-database, repeated-initialization and Seed snapshots prove structural equivalence. Migration-specific tests separately prove the additive user-system schema and checksum discipline.
