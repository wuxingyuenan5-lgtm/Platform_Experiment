# Critical Task Packet Template

Every temporary agent receives a task card. Use this durable packet for implementation, Critical work and any cross-session handoff; an Issue with the same required fields may serve as the task card for small read-only work.

```markdown
# Task: <short name>

Task ID: `<stable-id>`
Issue: #<number>
Status: planned | active | blocked | review | done
Risk level: low | medium | high | critical
Role: investigation | implementation | acceptance
Agent ID: `<agent-id-or-none-before-dispatch>`
Implementation owner: `<agent-id-or-none-for-read-only>`
Branch: `<type>/issue-<number>-<slug>`
Worktree: `<absolute-isolated-path>`
Base commit: `<sha>`
Context Pack: `<pack-name>`
Recovery from: `<closed-agent-id-or-none>`
Recovered owner status: `closed | none`
Parallel with: `<parallel-task-id-or-none>`
Parallel peer write set: `<exact peer paths or none>`

## Objective

One measurable outcome.

## Protected semantics

Only the behavior and safety rules that must remain unchanged.

## Scope

- Included paths/outcomes.
- Explicit non-goals.

## Dispatch concurrency decision

- Write set: `<exact paths or none (read-only)>`
- Shared workflow, public contract, migration chain or file set: `<name or none>`
- Dependencies: `<unfinished dependencies or none>`
- Independent test: `<exact command or not-applicable-read-only>`
- Rollback boundary: `<independent commit/revert boundary or not-applicable-read-only>`
- Parallel decision: `serial | parallel-approved | read-only`
- Acceptance task: `<independent-read-only-task-id for critical implementation; otherwise not-required>`
- Active-agent count after dispatch: `<implementers>/2 implementation, <read-only>/2 read-only, <total>/4 total`
- Independence evidence: `<why writes, dependencies, tests and rollback are independent; required for parallel-approved>`

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

For AI collaboration, assign exactly one implementation owner to each workflow, public contract, migration chain and shared file set. Each implementation owner uses a separate task card, `codex/` branch and isolated worktree. A second implementation agent is allowed only when the dispatch concurrency decision proves disjoint writes, no unfinished dependency, independent testing and independent rollback. Critical tasks require an independent read-only acceptance agent. Review findings return to the original owner; replacement requires the prior owner to be closed and recorded first. Investigation agents are read-only and may not delegate.
## Documentation contract

When a task changes product or module behavior, its authoritative document must state scope and exclusions, user/permission boundary, data authority, Query/Command/Event ownership, lifecycle and failure states, audit/recovery rules, dependencies and executable acceptance criteria. Discussion history and completed checklists stay in the task packet, not in the authority document.
