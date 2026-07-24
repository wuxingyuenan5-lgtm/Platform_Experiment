# Task: SQLite connection boundary extraction

Issue: #48
Status: active
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

- [ ] One Issue, task packet, branch and PR.
- [ ] New module owns path/connection transaction behavior.
- [ ] `app.database` re-exports identical compatibility objects.
- [ ] `database.py` contains no `sqlite3.connect` or connection context implementation.
- [ ] Direct commit/rollback/foreign-key/path tests pass.
- [ ] Existing classified Backend suites pass unchanged.
- [ ] Connection boundary is in progressive Pyright and machine-checked.
- [ ] Runtime/frontend regressions, Repository Safety and Secret Scan pass.
- [ ] Documentation matches the final implementation.

## Risk and rollback

Risk: medium because all Backend persistence uses this boundary.

Rollback: revert the final squash commit. No migration or external state is introduced.

## Progress

- Done: audited `database.py` responsibilities and existing callers; created Issue #48 and unique branch.
- Current: extract connection implementation behind compatibility aliases.
- Next: add direct transaction equivalence and architecture tests.
- Blocked by: none.

## Completion

- PR: pending.
- Merge commit: pending.
- Behavior changed: none intended; connection ownership only.
- Tests/CI: pending.
- Follow-up: core bootstrap/schema and reference seed extraction remain separate Issues.
