# Codex Task Packet Template

Use one packet for every cross-session, cross-module, migration, production or otherwise non-trivial task. Copy it to `tasks/issue-<number>-<slug>.md`.

```markdown
# Task: <short name>

Issue: #<number>
Status: planned | active | blocked | review | done
Branch: `<type>/issue-<number>-<slug>`
Base commit: `<sha>`

## Objective

One measurable outcome.

## Non-goals

- Explicitly excluded adjacent work.
- Refactors that must not be pulled into this task.

## Allowed scope

- Directories/files that may change.
- Required tests and documentation.

## Expected changed files

- List the files expected to change before editing.
- Mark any conditional file explicitly and state what evidence permits it.

## Protected semantics

List behavior that must remain unchanged, especially trading calculations, order states, risk/funds controls, API field meaning, database schema behavior and live-write defaults.

## Context packet

Read only:

1. `AGENTS.md`;
2. `docs/codex/current-state.md`;
3. one module entry document;
4. three to eight direct source files;
5. direct tests.

Additional context:

- `<path>` — `<reason>`

## Required verification

```text
<exact commands>
```

State whether final delivery also requires full CI, a Secret Scan, golden evidence or another repository-level gate.

## Stop conditions

- Stop when the change would exceed Allowed scope or Expected changed files without new evidence.
- Stop when a Protected semantic would need to change.
- Add task-specific conditions that require a dedicated Issue or explicit approval.

## Acceptance criteria

- [ ] Outcome completed.
- [ ] Relevant lint/type/test commands pass.
- [ ] Repository and architecture checks pass.
- [ ] Authoritative documentation matches implementation.
- [ ] Diff contains no unrelated cleanup.

## Risk and rollback

Risk: low | medium | high

- Failure modes:
- Detection:
- Rollback:

## Progress

Replace stale detail; do not append a chat transcript.

- Done:
- Current:
- Next:
- Blocked by:

## Completion

- PR:
- Merge commit:
- Behavior changed:
- Behavior intentionally unchanged:
- Tests/CI:
- Follow-up debt:
```

## Task uniqueness rule

Before creating a branch:

1. Search open Issues and PRs for the same outcome.
2. Reuse the existing Issue when one exists.
3. Confirm no active PR already references that Issue.
4. Create exactly one branch named with that Issue number.

If a branch must be replaced, close the old PR first and record `Superseded by #<new-pr>` before starting the replacement. Do not keep two active branches implementing the same Issue.
