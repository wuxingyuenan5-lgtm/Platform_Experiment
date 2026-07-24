# Task: Project operating system and engineering hardening

Issue: #36
Status: done
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
- Selected Platform, Runtime and frontend configuration/test files required for the hardening items.

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

- PR #28 — verified as already merged and extended instead of duplicated.
- Closed unmerged PRs #8, #13 and #30 — verified as superseded.
- Duplicate/superseded branch refs — compared against `main` before returning them to the stable baseline.

## Acceptance criteria

- [x] One Issue, one active branch and one PR for this workstream.
- [x] Context documentation has one canonical map and one task template.
- [x] Duplicate-Issue PRs and invalid branch/task linkage fail CI.
- [x] Database schema inventory and additive migration ledger exist without changing business tables.
- [x] Platform–Runtime contracts are versioned and compatibility-tested.
- [x] Progressive Python type checks run for critical boundary modules.
- [x] Frontend changed-file/no-new-debt lint gate is executable.
- [x] Failure-injection and production-acceptance tests cover critical uncertain-result and recovery scenarios.
- [x] All existing CI suites and Secret Scan pass.
- [x] No unrelated production behavior changes.

## Verification commands

```text
python scripts/check-workstream.py
python scripts/scan-secrets.py
python scripts/check-repository-structure.py
cd platform-backend && python -m pip check && python -m ruff check app tests && python -m pyright && python -m pytest
cd execution-runtime && python -m pip check && python -m ruff check app tests && python -m pyright && python -m pytest
cd admin-risk && pnpm exec eslint --max-warnings 0 <maintained paths> && pnpm type:check && pnpm build
```

## Risk and rollback

Risk: medium

- Failure modes: false-positive governance gate, contract snapshot drift, migration-ledger startup regression, type-check noise.
- Detection: focused tests followed by full Platform CI and Secret Scan.
- Rollback: squash-revert PR #37; all schema work is additive and Live Write remains disabled.

## Progress

- Done: all planned safe-scope implementation, tests, documentation, branch review and CI verification.
- Current: PR #37 final merge.
- Next: no default engineering workstream; future work begins from an Issue and bounded task packet.
- Blocked by: repository-level branch protection/ruleset must be verified manually because the available connector cannot mutate it.

## Completion

- PR: #37.
- Merge commit: recorded by GitHub on PR #37 after squash merge; do not hardcode it as a perpetually current `main` tip.
- Behavior changed: engineering workflow, schema governance, contract validation, type/lint gates and failure-injection evidence.
- Behavior intentionally unchanged: trading, funds safety, API field meaning, existing business schema, credentials and Live Write defaults.
- Tests/CI: Platform CI run `30072939611` passed all four jobs; Secret Scan run `30072939641` passed.
- Follow-up debt: real-account operational acceptance remains manual and bounded; branch protection/ruleset verification remains an administrator setting.
