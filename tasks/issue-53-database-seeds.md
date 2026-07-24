# Task: Fixed database Seed extraction

Issue: #53
Status: active
Branch: `refactor/issue-53-database-seeds`
Base commit: `4dfa0ce0800f8ab4cdd457580e03b4a7cdfc1e4d`

## Objective

Extract every existing fixed reference-data Seed vector and insertion statement into `app/database_seeds.py` while preserving all values, identifiers, order, compatibility imports and startup results.

## Non-goals

- No Seed ID/value/status/default change.
- No Schema, compatibility DDL, migration-ledger or connection change.
- No caller import migration.
- No business, API, trading, accounting, risk-control or Live Write change.

## Protected semantics

- Exact fixed timestamp and every seeded row/column value.
- Strategy, venue, account and instrument active/paused/simulation defaults.
- Contract defaults and existing XAUUSD specification update.
- `INSERT OR IGNORE` idempotency.
- Startup order: Connection → Bootstrap → Seed.
- `app.database.seed_reference_data` compatibility identity.

## Acceptance criteria

- [ ] One Issue, task packet, branch and PR.
- [ ] `database_seeds.py` is the single fixed Seed owner.
- [ ] `database.py` is only compatibility exports and initializer orchestration.
- [ ] Exhaustive Seed row/value snapshot passes.
- [ ] Repeated initialization and existing Schema/legacy tests pass.
- [ ] Seed ownership is machine-checked and in progressive Pyright.
- [ ] Backend/Runtime/frontend, Repository Safety and Secret Scan pass.
- [ ] Documentation matches final implementation.

## Risk and rollback

Risk: medium because seeded identities and safety defaults are widely referenced.

Rollback: revert the final squash commit. No migration or external state is introduced.

## Progress

- Done: merged Connection and Bootstrap owners; created Issue #53 and unique branch.
- Current: move fixed Seed code behind compatibility export.
- Next: exhaustive row snapshot and architecture ownership checks.
- Blocked by: none.

## Completion

- PR: pending.
- Merge commit: pending.
- Behavior changed: none intended; Seed ownership only.
- Tests/CI: pending.
