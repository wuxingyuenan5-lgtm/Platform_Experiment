# Task: Core database bootstrap extraction

Issue: #50
Status: active
Branch: `refactor/issue-50-database-bootstrap`
Base commit: `8a72dcf9a88db73873262024af5dfa73387a713e`

## Objective

Extract core Schema SQL and legacy compatibility DDL into `app/database_bootstrap.py` while preserving all definitions, ordering, startup results and compatibility imports.

## Non-goals

- No Seed extraction or Seed value change.
- No migration-ledger change.
- No table/index/column definition change.
- No connection, business, API, trading, accounting, risk-control or Live Write change.

## Protected semantics

- Exact core `SCHEMA_SQL` and statement order.
- All core tables and indexes.
- Legacy compatibility columns and partial unique index.
- Startup order: Schema → compatibility DDL → Seeds.
- Fresh/existing/repeated initialization results.
- Existing `app.database` compatibility identities.

## Acceptance criteria

- [ ] One Issue, task packet, branch and PR.
- [ ] Bootstrap module owns Schema and compatibility DDL.
- [ ] `database.py` retains compatibility aliases and Seed/orchestration only.
- [ ] Exact Schema checksum and equivalence tests pass.
- [ ] DDL Owner inventory and Repository Safety use the Bootstrap owner.
- [ ] Existing Seed and classified suites pass unchanged.
- [ ] Bootstrap is in progressive Pyright and machine-checked.
- [ ] Runtime/frontend regressions and Secret Scan pass.
- [ ] Documentation matches final implementation.

## Risk and rollback

Risk: medium because every fresh and legacy database startup uses this Schema.

Rollback: revert the final squash commit. No migration or external state is introduced.

## Progress

- Done: created Issue #50 and unique branch after PR #49 merge.
- Current: move Schema and compatibility DDL behind compatibility exports.
- Next: checksum, ownership and initialization-order tests.
- Blocked by: none.

## Completion

- PR: pending.
- Merge commit: pending.
- Behavior changed: none intended; Bootstrap ownership only.
- Tests/CI: pending.
- Follow-up: fixed reference Seed extraction remains separate.
