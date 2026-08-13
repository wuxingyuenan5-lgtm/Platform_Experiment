# Task Record Template

Use the lightest record that preserves safety and recovery. Full task cards are required for implementation edits, Critical acceptance, recovery, parallel implementation and any owner-gated or immutable-evidence task. A short task record is sufficient for a single-session read-only investigation or status query.

```markdown
# Task: <short name>

Task ID: `<stable-id>`
Issue: #<number>
Status: `planned | active | review | attention | blocked | done`
Last transition at: `<YYYY-MM-DD HH:MM TZ>`
Owner notice: `none | required | sent`
Business status summary: `<business capability, current state, and who acts next when needed>`
Current leaf task/agent ID: `<leaf-id-or-none>`
Risk level: low | medium | high | critical
Role: investigation | implementation | acceptance
Agent ID: `<agent-id-or-none-before-dispatch>`
Context Pack: `<pack-name>`
Token indicator budget: `<integer>`
Token indicator used: `<integer>`
Token status: `green | amber | red`
Control-plane token used: `<integer>`

## Objective

One measurable outcome.

## Implementation fields

Include only for implementation tasks:

- Implementation owner: `<agent-id>`
- Branch: `codex/<slug>`
- Worktree: `<absolute-isolated-path>`
- Base commit: `<sha>`

## Protected semantics

Only the behavior and safety rules that must remain unchanged.

## Scope

- Included paths/outcomes.
- Explicit non-goals.

## Dispatch concurrency decision

Include only when applicable:

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
- Active-agent count after dispatch: `<implementers>/2 implementation, <read-only>/2 read-only, <total>/4 total`
- Recovery from: `<closed-agent-id>`
- Recovered owner status: `closed`

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

Replace stale progress instead of appending chat history. Use `Business status summary` as the status-event payload: `attention` and `blocked` must say who needs to do what; `done` must name the business capability, immutable evidence and next gate. Do not send duplicate notices for the same unchanged state, and never use "still running" as an event.

Default to one implementation agent. The `4/2/2` limits are maximum safe upper bounds, not a target. A second implementation agent is allowed only when the dispatch record proves disjoint writes, no unfinished dependency, independent testing and independent rollback; do not split work merely to use concurrency capacity. Critical implementation still requires an independent read-only acceptance task. Recovery still requires the prior owner to be closed and recorded first.

Token indicators are management metrics, not API billing. Default slice gates are 2,000,000 total, 1,200,000 implementation, 300,000 technical-lead control plane, 300,000 independent review, 200,000 combined project-lead plus advisor, and at most 30 percent control-plane share. At 60 percent, do not add agents or broaden scope. At 80 percent, stop non-essential refactors, repeated reviews and broad scans. At 100 percent, preserve immutable evidence, set status to `attention` and wait for owner budget extension.
## Documentation contract

When a task changes product or module behavior, its authoritative document must state scope and exclusions, user/permission boundary, data authority, Query/Command/Event ownership, lifecycle and failure states, audit/recovery rules, dependencies and executable acceptance criteria. Discussion history and completed checklists stay in the task packet, not in the authority document.
