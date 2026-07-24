# Task: SQLite connection boundary extraction

Issue: #48
Status: ready for merge
Branch: `refactor/issue-48-database-connection`
Base commit: `1d37bedf9bb917c532f2a1aa00eb162e20a96f56`

## Objective

Extract configured SQLite path resolution and transaction-managed connection creation into `app/database_connection.py` while preserving every existing caller and persistence behavior.

## Non-goals

- No Schema SQL, compatibility DDL or seed extraction.
- No table, index, column, seed identifier or database-technology change.
- No caller import migration.
- No business, trading, financial, API, risk-control or Live Write change.

## Protected semantics

- Dynamic settings lookup and parent-directory creation.
- `sqlite3.Row` mapping behavior.
- Foreign Keys enabled on every connection.
- Commit on success, rollback/re-raise on exception and close in all cases.
- `app.database.connection` and `database_path` compatibility identity.
- Fresh and existing database contents and startup behavior.

## Acceptance criteria

- [x] One Issue, task packet, branch and PR.
- [x] New module owns path/connection transaction behavior.
- [x] `app.database` re-exports identical compatibility objects.
- [x] `database.py` contains no `sqlite3.connect` or connection context implementation.
- [x] Direct commit/rollback/foreign-key/path tests pass.
- [x] Fresh Schema/index/Seed snapshot, repeated initialization and legacy DB compatibility tests pass.
- [x] Existing classified Backend suites pass unchanged on implementation heads.
- [x] Connection boundary is in progressive Pyright and machine-checked.
- [x] Runtime and Repository Safety pass on implementation heads.
- [x] Secret Scan passes on implementation heads.
- [x] Documentation matches the final implementation.
- [ ] Final frozen-head Platform CI and independent Secret Scan; evidence recorded in PR #49.

## Risk and rollback

Risk: medium because all Backend persistence uses this boundary.

Rollback: revert the final squash commit. No migration or external state is introduced.

## Progress

- Done: extracted the connection owner, preserved compatibility identity, added direct transaction tests plus fresh/existing/repeated initialization snapshots, Pyright and architecture checks, and synchronized documentation.
- Current: final frozen-head CI and PR evidence.
- Next: squash merge, then extract core Bootstrap/Schema in a separate Issue.
- Blocked by: none.

## Completion

- PR: #49.
- Merge commit: pending squash merge.
- Behavior changed: none; connection ownership only.
- Tests/CI: implementation-head Backend, Runtime, Repository Safety and Secret Scan passed; final evidence will be recorded in PR #49.
- Follow-up: core bootstrap/schema and reference seed extraction remain separate Issues.
