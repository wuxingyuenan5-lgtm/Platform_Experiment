# Task Record Template
Task records are optional references. Create or read one only when the Owner explicitly requests it, or for an Owner-gated Mode 2/3, recovery, parallel, or critical-acceptance evidence workflow.

```markdown
# Task: <short name>
Task ID: `<stable-id>`
Issue: `#<number-or-none>`
Status: `planned | active | review | attention | blocked | done`
Last transition at: `<YYYY-MM-DD HH:MM TZ>`
Business status summary: `<business capability, current state, and who acts next when needed>`
Risk level: `low | medium | high | critical`
Role: `investigation | implementation | acceptance`
Context Pack: `<pack-name>`

## Objective
One measurable business outcome.

## Implementation fields
- Implementation owner: `<agent-id>`
- Mode: `Local`
- Base commit: `<sha>`

## Protected semantics
Only the behavior and safety rules that must remain unchanged.

## Scope
- Included paths/outcomes.
- Explicit non-goals.

## Dispatch concurrency decision
- Write set: `<exact paths>`
- Shared workflow, public contract, migration chain or file set: `<name>`
- Dependencies: `<unfinished dependencies>`
- Independent test: `<exact command>`
- Rollback boundary: `<independent commit/revert boundary>`
- Parallel decision: `serial | parallel-approved`
- Parallel with: `<parallel-task-id>`
- Parallel peer write set: `<exact peer paths>`
- Independence evidence: `<why writes, dependencies, tests and rollback are independent>`
- Acceptance task: `<independent-read-only-task-id>`
- Recovery from: `<closed-agent-id>`
- Recovered owner status: `closed`

## Context
List only extra authority files beyond `AGENTS.md`, `current-state.md`, the Pack files, the current version control file and direct source/tests.

## Verification
Exact commands and any final full-CI requirement.

## Progress
- Done:
- Current:
- Next:
- Blocked by:
```

Status rules: commentary reports progress. Use only fields relevant to the requested evidence; ordinary tasks do not require a fixed receipt.
Concurrency rules: Mode 1 is direct work. Mode 2 is available only when the Owner explicitly asks for multi-Agent work. Parallel implementation requires clearly independent write sets and rollback boundaries. A Worktree is never a normal-task prerequisite.
