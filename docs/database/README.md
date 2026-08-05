# Database Schema and Migration Guide

SQLite remains the approved local Platform database. This document owns persistence rules; domain meaning belongs to the relevant contract.

## Authority classes

| Class | Examples |
|---|---|
| Reference/master | legal entity, fund, strategy, venue, account, instrument |
| Identity/access | users, sessions and recovery tickets |
| Command/execution | trade commands, orders, batches and Runtime evidence |
| Operational projection | monitoring positions, PnL and exit plans |
| Immutable financial fact | `financial_facts` |
| Formal projection | formal positions, PnL and NAV |
| Risk/approval | Kill Switch, execution risk and Live Trading Session |
| Reconciliation/operations | differences, reports, alerts and recovery evidence |

A table has one owner and one authority class.

## Shared infrastructure

- `app/database_connection.py` — configured path and transaction-managed connection;
- `app/database_bootstrap.py` — core bootstrap schema;
- `app/database_seeds.py` — fixed reference data;
- `app/database.py` — compatibility facade and initializer;
- `app/schema_migrations.py` — ordered, additive, checksum-protected migrations.

## Domain persistence owners

| Owner | Responsibility |
|---|---|
| `app/execution_risk_repository.py` | Kill Switch, risk policy, batch-risk snapshots and risk actions |
| `app/financial_fact_repository.py` | immutable financial facts and formal projections |
| `app/venue_reconciliation_repository.py` | venue reconciliation |
| `app/eod_reconciliation_repository.py` | EOD reports and reviews |
| `app/live_trading_sessions.py` | two-person Live session state |
| `app/cross_spread_exit_repository.py` | exit plans and lifecycle persistence |
| dedicated identity repositories | users, sessions, notes and holdings |
| Runtime journal/store owners | Runtime command, event and venue snapshots |

Router, pure-policy and service modules must not contain direct SQL when a repository owner exists.

## Migration rules

1. Never edit an applied migration.
2. Add one monotonic version with a stable name and checksum.
3. Prefer additive DDL.
4. Test fresh, existing-row, repeated-startup and checksum-drift behavior.
5. Record ownership, compatibility and rollback/forward-fix behavior.
6. Do not insert real users, credentials, holdings or secrets.
7. Do not transfer authority between operational and formal data implicitly.

The Platform 0.10.1 execution-risk split changes module ownership only. It does not alter DDL, table structure or data semantics.
