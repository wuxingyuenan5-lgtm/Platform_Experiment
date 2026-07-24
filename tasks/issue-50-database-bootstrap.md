# Task: Core database bootstrap extraction

Issue: #50
Status: ready for merge
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

- [x] One Issue, task packet, branch and PR.
- [x] Bootstrap module owns Schema and compatibility DDL.
- [x] `database.py` retains compatibility aliases and Seed/orchestration only.
- [x] Exact Schema checksum `421f0625ffe3a8a26ca48bc827e64bd6aa6b2e49d95faef0b17313e808375801` is frozen.
- [x] Fresh/existing/repeated initialization equivalence tests pass on implementation heads.
- [x] DDL Owner inventory and Repository Safety use the Bootstrap owner.
- [x] Existing Seed and classified suites pass unchanged on implementation heads.
- [x] Bootstrap is in progressive Pyright and machine-checked.
- [x] Runtime and Repository Safety pass on implementation heads.
- [x] Secret Scan passes on implementation heads.
- [x] Documentation matches final implementation.
- [ ] Final frozen-head Platform CI and independent Secret Scan; evidence recorded in PR #51.

## Risk and rollback

Risk: medium because every fresh and legacy database startup uses this Schema.

Rollback: revert the final squash commit. No migration or external state is introduced.

## Progress

- Done: extracted Bootstrap owner, preserved compatibility aliases and startup order, froze Schema checksum, transferred DDL ownership and synchronized documentation.
- Current: final frozen-head CI and PR evidence.
- Next: squash merge, then extract fixed reference Seeds in the final structural PR.
- Blocked by: none.

## Completion

- PR: #51.
- Merge commit: pending squash merge.
- Behavior changed: none; Bootstrap ownership only.
- Tests/CI: implementation-head Backend, Runtime, Repository Safety and Secret Scan passed; final evidence will be recorded in PR #51.
- Follow-up: fixed reference Seed extraction remains separate.
