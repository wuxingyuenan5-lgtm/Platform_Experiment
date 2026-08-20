# Task Record Template
Use the lightest record that preserves safety. Full task cards are required for repository writes, Critical acceptance, recovery, parallel implementation and explicit owner-gated immutable evidence. A short task record is enough for a single-session read-only investigation or status query.

```markdown
# Task: <short name>
Task ID: `<stable-id>`
Issue: `#<number-or-none>`
Status: `planned | active | review | attention | blocked | done`
Last transition at: `<YYYY-MM-DD HH:MM TZ>`
Owner notice: `none | required | sent`
Business status summary: `<business capability, current state, and who acts next when needed>`
Current leaf task/agent ID: `<leaf-id-or-none>`
Risk level: `low | medium | high | critical`
Role: `investigation | implementation | acceptance`
Agent ID: `<agent-id>`
Context Pack: `<pack-name>`
Token baseline: `<integer | unavailable>`
Token current: `<integer | unavailable>`
Token delta: `<integer | unavailable>`
Control-plane token delta: `<integer | unavailable>`
Token budget: `<integer>`
Token status: `green | amber | red | unavailable`

## Objective
One measurable business outcome.

## Implementation fields
- Implementation owner: `<agent-id>`
- Mode: `Local`
- Branch/worktree exception: `none` (only approved high-risk recovery or proven parallel write)
- Branch: `main` unless the exception above is approved
- Worktree: `none` unless the exception above is approved
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
- Active-agent count after dispatch: `<implementers>/2 implementation, <read-only>/2 read-only, <total>/4 total`
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

Status-event rules: `review`, `attention`, `blocked` and `done` are real events; "still running" is not. `attention` and `blocked` summaries must include `Needs:`. `done` summaries must include `Capability:`, `Evidence:` and `Next gate:`.
Token rules: `Token delta = Token current - Token baseline`; at 60 percent of budget, do not add agents or broaden scope; at 80 percent, `Owner notice` is mandatory and non-essential work stops; at 100 percent, `Status` must be `attention` and work stops; if any Token snapshot field is unavailable, record `unavailable` instead of fake zero and move the task to `attention`; the 30 percent control-plane measure is calculated across the whole business slice, not enforced per task or leaf agent; repository validation checks task declarations only and is not Codex runtime throttling.
Concurrency rules: default to one Local implementation writer on `main`; no second implementation agent; read-only acceptance may review an immutable candidate without creating a branch; linked worktrees are exception-only for approved high-risk recovery or proven parallel writes and must close after use.
