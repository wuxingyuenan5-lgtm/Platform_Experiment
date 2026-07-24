# Task: Project operating system and engineering hardening

Issue: #36
Status: active
Branch: `hardening/issue-36-project-operating-system`
Base commit: `e826c9e4808a0b76c3265bfd5da5b8e65c133b77`

## Objective

Complete the agreed safe-scope engineering hardening while establishing a low-token, single-workstream process for future development.

## Non-goals

- No trading strategy, PnL formula or order-state redesign.
- No destructive schema migration or database replacement.
- No real credential configuration or Live Write enablement.
- No microservices, Kafka or broad framework migration.
- No mass frontend formatting unrelated to changed files.

## Allowed scope

- `AGENTS.md`, `README.md`, `00-人工可读目录/README.md`.
- `docs/codex/`, `docs/architecture/`, `docs/database/`, `docs/contracts/`, `docs/engineering/`.
- `.github/`, `scripts/`, `tasks/`, `outputs/README.md`.
- Selected Platform, Runtime and frontend configuration/test files required for the six hardening items.

## Protected semantics

- Trading calculations and state transitions.
- Kill Switch, approval, session-limit and live-write behavior.
- Existing API field meaning and compatibility aliases.
- Existing database tables, indexes and seed identifiers.
- Operational versus formal accounting ownership.
- Credential custody and redaction behavior.

## Context packet

Primary:

1. `AGENTS.md`.
2. `docs/codex/current-state.md`.
3. `docs/codex/context-map.md`.
4. `.github/workflows/platform-ci.yml`.
5. `scripts/check-repository-structure.py`.
6. `platform-backend/app/database.py`.
7. Platform/Runtime contract and safety tests directly affected.

Additional context:

- PR #28 — verify and extend the already-merged Codex context optimization rather than duplicating it.
- Closed unmerged PRs #8, #13 and #30 — confirm they were superseded before reusing any work.

## Acceptance criteria

- [ ] One Issue, one active branch and one PR for this workstream.
- [ ] Context documentation has one canonical map and one task template.
- [ ] Duplicate-Issue PRs and invalid branch/task linkage fail CI.
- [ ] Database schema inventory and additive migration ledger exist without changing business tables.
- [ ] Platform–Runtime contracts are versioned and compatibility-tested.
- [ ] Progressive Python type checks run for critical boundary modules.
- [ ] Frontend changed-file/no-new-debt lint gate is executable.
- [ ] Failure-injection and production-acceptance tests cover critical uncertain-result and recovery scenarios.
- [ ] All existing CI suites and Secret Scan pass.
- [ ] No unrelated production behavior changes.

## Verification commands

```text
python scripts/check-repository-structure.py
python scripts/check-workstream.py
cd platform-backend && python -m ruff check app tests && python -m pip check && python -m pytest
cd execution-runtime && python -m ruff check app tests && python -m pip check && python -m pytest
cd admin-risk && pnpm exec eslint --max-warnings 0 <maintained paths> && pnpm type:check && pnpm build
```

## Risk and rollback

Risk: medium

- Failure modes: false-positive governance gate, contract snapshot drift, migration ledger startup regression, type-check noise.
- Detection: focused tests followed by full Platform CI and Secret Scan.
- Rollback: squash-revert the PR; all schema work is additive and Live Write remains disabled.

## Progress

- Done: verified PR #28 was already merged; created Issue #36; moved active changes to one Issue-numbered branch; reset the pre-policy duplicate branch to `main`; started canonical documentation consolidation.
- Current: Git/workstream governance and context operating system.
- Next: database inventory/migration ledger, contracts, typing, frontend debt gate and failure injection.
- Blocked by: none.

## Completion

- PR: pending.
- Merge commit: pending.
- Behavior changed: engineering workflow and non-destructive hardening only.
- Behavior intentionally unchanged: trading, funds safety, API semantics, existing business schema and Live Write defaults.
- Tests/CI: pending.
- Follow-up debt: real-account operational acceptance remains manual and bounded.
