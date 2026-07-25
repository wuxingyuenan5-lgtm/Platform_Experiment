# Task: Lightweight maintenance workflow

Issue: #105
Status: active
Branch: `hardening/issue-105-lightweight-maintenance-workflow`
Base commit: `b0bff37fbd56b05fc0057cd4eee348ae62714d1c`

## Objective

Add a machine-enforced lightweight PR path for bounded Markdown and synchronized product-version maintenance, without weakening engineering governance for behavioral or safety-sensitive changes.

## Non-goals

- No trading, execution, risk, permission, credential, database, contract or deployment behavior change.
- No Live Write or safety-default change.
- No CI or Secret Scan bypass.

## Allowed scope

- `scripts/check-workstream.py`
- `platform-backend/tests/test_architecture_workstream_governance.py`
- `.github/pull_request_template.md`
- `docs/engineering/GIT_WORKFLOW.md`
- `docs/codex/task-template.md`
- `docs/codex/current-state.md`
- this task packet

## Expected changed files

Only the files listed in Allowed scope.

## Protected semantics

- Full engineering work still requires one Issue, one task packet, one Issue-numbered branch and one linked PR.
- Maintenance mode cannot touch application source, runtime configuration, workflows, database, contracts, migrations, credentials or safety defaults.
- All PRs still require CI and Secret Scan.

## Required verification

- Repository Safety and documentation consistency.
- Backend lint, type gate and classified tests, including focused workstream governance tests.
- Runtime and frontend regression gates.
- Secret Scan.

## Stop conditions

- Stop if maintenance mode would allow executable product changes.
- Stop if changed-file or version-patch validation cannot fail closed.
- Stop if the full engineering path becomes optional for ambiguous changes.

## Acceptance criteria

- [ ] Maintenance PRs can omit Issue/task packet only with explicit declarations.
- [ ] Markdown and synchronized version declarations are allowed.
- [ ] Source/config/contract/safety changes are rejected.
- [ ] Full engineering workflow remains unchanged.
- [ ] Documentation forbids post-merge metadata-only PRs.
- [ ] Required CI and Secret Scan pass.

## Risk and rollback

Risk: medium

- Failure modes: maintenance classification is too broad or too strict.
- Detection: focused validator tests and Repository Safety.
- Rollback: revert the squash merge and restore Issue-only validation.

## Progress

- Done: issue repurposed, two-track design fixed, checker/tests/docs implementation drafted.
- Current: open PR and run full repository gates.
- Next: correct any CI findings and merge after all checks pass.
- Blocked by: none.

## Completion

- PR:
- Merge commit:
- Behavior changed: repository governance only.
- Behavior intentionally unchanged: all product/runtime/trading/safety behavior.
- Tests/CI:
- Follow-up debt: none expected.