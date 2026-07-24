# Task: Fixed database Seed extraction

Issue: #53
Status: ready for merge
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

- [x] One Issue, task packet, branch and PR.
- [x] `database_seeds.py` is the single fixed Seed owner.
- [x] `database.py` is only compatibility exports and initializer orchestration.
- [x] Exhaustive all-row/all-field Seed snapshot SHA-256 `d42f7e4f95a6efa9044b1e91b4e603f1d87f515923a57d941ee16e75109e6183` is frozen.
- [x] Repeated initialization and existing Schema/legacy tests pass on implementation heads.
- [x] Seed ownership is machine-checked and in progressive Pyright.
- [x] Backend, Runtime and Repository Safety pass on implementation heads.
- [x] Secret Scan passes on implementation heads.
- [x] Documentation matches final implementation.
- [ ] Final frozen-head Platform CI and independent Secret Scan; evidence recorded in PR #54.

## Risk and rollback

Risk: medium because seeded identities and safety defaults are widely referenced.

Rollback: revert the final squash commit. No migration or external state is introduced.

## Progress

- Done: extracted Seed owner, preserved compatibility and initializer order, froze exhaustive Seed hash, added safety-default/repeated-startup/architecture tests, progressive Pyright and synchronized documentation.
- Current: final frozen-head CI and PR evidence.
- Next: squash merge and close the engineering workstream.
- Blocked by: none.

## Completion

- PR: #54.
- Merge commit: pending squash merge.
- Behavior changed: none; fixed Seed ownership only.
- Tests/CI: implementation-head Backend, Runtime, Repository Safety and Secret Scan passed; final evidence will be recorded in PR #54.
