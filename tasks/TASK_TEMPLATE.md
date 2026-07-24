# Task: <short name>

Status: planned | active | blocked | review | done
Owner: <person or agent>
Branch: `<branch>`
Base commit: `<sha>`

## Objective

One measurable outcome. Describe the user-visible or engineering result, not the implementation activity.

## Non-goals

- Explicitly excluded behavior.
- Adjacent cleanup that must not be pulled into this task.

## Allowed scope

- Directories/files that may be changed.
- Required documentation and tests.

## Protected semantics

List behavior that must remain unchanged, especially:

- trading calculations;
- order state transitions;
- funds/risk controls;
- API field meaning;
- database schema and migration behavior;
- live-write defaults.

## Context packet

Read only:

1. `AGENTS.md`;
2. `docs/context/CURRENT_STATE.md`;
3. `<module start document>`;
4. `<3–8 direct source files>`;
5. `<direct tests>`.

Additional context must be recorded here with a reason.

## Acceptance criteria

- [ ] Functional requirement.
- [ ] Relevant lint/type/test commands pass.
- [ ] Architecture and repository safety checks pass.
- [ ] Documentation matches the final implementation.
- [ ] No unrelated diff.

## Verification commands

```text
<exact commands>
```

## Risk and rollback

Risk level: low | medium | high

- Failure modes:
- Detection:
- Rollback:

## Progress log

Keep this short and replace stale detail rather than appending a chat transcript.

- Done:
- Current:
- Next:
- Blocked by:

## Completion summary

Fill at completion:

- PR:
- Merge commit:
- Behavior changed:
- Behavior intentionally unchanged:
- Tests/CI:
- Follow-up debt:
