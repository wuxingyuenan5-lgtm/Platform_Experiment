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
- `app/database.py` — single application/CLI/test initializer: bootstrap and reference seed, then all Platform and user-product migrations in numeric order;
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
| `app/research_a_share_repository.py` | collected A-share snapshots/history and shared core-pool configuration; personal focus remains in `user_research_watchlists` |
| `app/live_venue_snapshot_sync.py` | atomic account monitoring frames, risk, synchronization status and append-only native venue events |
| `app/venue_identity_repository.py` | exact native order identity and legacy alias resolution shared by monitoring, management and Funding account checks; no new ledger |
| `app/strategy_financial_readmodel.py` | read-only management PnL derived from canonical fills and native events; no formal accounting writes |
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

Execution-risk module refactors change ownership only unless an explicit migration changes DDL or persisted semantics.

## A-share schema version 21

Version 20 remains immutable. Version 21 rebuilds the three research tables under their status checks and refresh-run foreign keys, repairing databases originally created by the retired repository DDL guard. Valid rows are copied unchanged; invalid statuses or orphan references abort and roll back the migration rather than being discarded. Migration DDL and its ledger entry share a savepoint.

`research_a_share_pool_config` is a singleton configuration row with ordered codes, version and update time. It imports the existing core-pool membership once. Market snapshots retain their own source and observation times; membership edits do not manufacture fresh prices. Personal focus uses authenticated `user_id` and optimistic `row_version` in the existing watchlist owner. The legacy global focus snapshot is retained but is not distributed to every account.

Initialize explicitly before application/CLI use. Research GETs never create or alter tables. Forward repair is tested on fresh and legacy schemas; running databases are not reset as part of validation.

## Strategy account schema version 22

Version 22 moves account synchronization/risk DDL into the ordered initializer, adds scope and raw risk payloads, and introduces `account_venue_snapshots` plus `venue_account_events`. The first retains each account's last successful frame and declared history coverage. The second retains native fill, fee, funding, swap and realized-settlement evidence across venue windows, keyed by `(account_id, source, event_type, external_id)`. An existing identity with conflicting financial content aborts the whole refresh. These are monitoring/source facts and do not silently become formal NAV or accounting facts.

Orders gain a venue payload without replacing their command identity; synchronization uses constrained updates rather than deleting and reinserting an order. `balance_snapshots.available_balance` becomes nullable while preserving prior rows and indexes. Unknown cash availability cannot satisfy admission. Existing financial fact table definitions are frozen in this migration for fresh databases.

Schema initialization precedes services and reads; management GETs perform no DDL. A successful frame, current positions, native events and last-success time commit together. Validation or persistence failure retains the previous frame and marks the attempt failed. Backward, foreign-account or malformed snapshots cannot clear positions. Old account-risk scope is `unspecified`, so old points cannot silently join a newly defined USD/UTA curve. Validation includes a read-only copy of the existing version-21 business database: upgrade to 22 and repeated initialization preserve execution-row counts and strategy bindings, with SQLite integrity check passing. Applying 22 to the original database is a separate deployment operation.

## Operational fill provenance version 23

Version 23 only adds `fills.origin`, `fills.source` and `fills.external_fill_id`. Existing rows default to `origin=legacy` with unknown source/native ID; their identifiers, quantities, prices and timestamps are unchanged. New execution confirmations use `runtime_confirmation`; native imports and monitor projections use `venue_execution`. Both represent increments within their own source stream. Runtime V1 wire fields and the execution ceiling remain unchanged.

Legacy aliases are resolved from existing order/account/instrument/native-order evidence, without renaming rows or creating a parallel alias ledger. Monitoring synthetic order IDs include account and instrument; monitoring fill IDs include account, source and native fill identity. A replay can reuse an old fill ID only with matching evidence. Command confirmations may have a different confirmation time from the native execution time: the immutable native event owns native replay validation, and monitoring does not rewrite the command confirmation.

An isolated copy of the existing version-22 backup passed upgrade to 23, two initializations and `integrity_check`. All original fields of 313 orders, 429 fills, 60 commands, 14 bindings, six positions and 222 native events were preserved. Four stored account frames replayed twice without inserting duplicate orders, fills or native events.

The Owner-authorized local maintenance on 2026-09-08 subsequently backed up both stores and upgraded the business database from 22 to 23. Backup and business integrity checks passed. Existing identities, bindings and external positions were retained; all original command, fill, instruction and batch fields matched the backup. Runtime commands, events and order routes were unchanged. Four configured accounts resumed successful read-only synchronization with both live-write gates disabled. Evidence is retained in `platform-api/data/backups/strategy-maintenance-20260908T115443Z/`, outside Git. This establishes this local installation's migration and read-only compatibility; it does not establish complete historical provenance, financial coverage or real-trading acceptance. Future upgrades use authorized maintenance; rollback uses the pre-upgrade backup or a forward repair, never relabeling or deleting historical financial facts.

## Capital monitoring schema versions 24–25

Version 24 adds `account_capital_movements` (native evidence, scope and nullable classified amount), `account_capital_coverage` (successful bounded reads), `account_capital_sync` (independent attempt/error state), and `account_valuation_rates` (timestamped USD rates). Version 25 records valuation source provenance. Amounts/rates remain decimal strings and timestamps UTC; unknown classification is null. Additive migrations preserve existing account, execution and accounting rows. Bybit UTA/Funding and MT5 history backfill starts at the earliest local equity observation. These tables support monitoring only; calculation semantics belong to `../contracts/LIVE_ACCOUNT_OBSERVABILITY.md`.
