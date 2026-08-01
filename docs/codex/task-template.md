# Critical Task Packet Template

Use a task packet only for Critical work that is cross-session, cross-service, migration-related, production-related or otherwise needs durable handoff. Fast and Standard work do not require one.

```markdown
# Task: <short name>

Issue: #<number>
Status: planned | active | blocked | review | done
Branch: `<type>/issue-<number>-<slug>`
Base commit: `<sha>`

## Objective

One measurable outcome.

## Protected semantics

Only the behavior and safety rules that must remain unchanged.

## Scope

- Included paths/outcomes.
- Explicit non-goals.

## Context

List only additional files beyond `AGENTS.md`, `current-state.md`, the module `AGENTS.md`, direct source and direct tests.

## Verification

Exact relevant commands and any final full-CI requirement.

## Progress

- Done:
- Current:
- Next:
- Blocked by:
```

Replace stale progress instead of appending chat history. GitHub PR/main history owns completion and merge identity; do not create a second metadata task or PR.
## Documentation contract

When a task changes product or module behavior, its authoritative document must state scope and exclusions, user/permission boundary, data authority, Query/Command/Event ownership, lifecycle and failure states, audit/recovery rules, dependencies and executable acceptance criteria. Discussion history and completed checklists stay in the task packet, not in the authority document.
