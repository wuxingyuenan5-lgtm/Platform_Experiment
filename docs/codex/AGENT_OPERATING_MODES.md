# Agent Operating Modes

This file defines how Codex work is started for this repository. It is a routing contract, not a fourth role and not a replacement for `AGENTS.md` or the governance contract.

## Mode 1: Single Executor

This is the default for normal work. One Agent receives the Owner request, reads the selected Context Pack and task record, implements the bounded change, validates it and returns the final receipt directly to the Owner.

- Do not create a coordinator, worker, reviewer or monitoring Agent.
- Treat one Owner request as one continuous task.
- Continue through investigation, implementation and validation in the same turn until the task is `done`, `blocked`, `attention` or requires an Owner gate.
- Intermediate commentary is optional and short. The eight-field receipt is emitted only at a terminal state.
- A failed command is not a terminal state. Diagnose and retry within the task when the retry is safe and bounded.
- Do not stop or restart a user service, modify business code during an operational acceptance, connect an external account or perform Live Write unless the task explicitly authorizes that action.

Use this mode for ordinary feature work, bug fixes, bounded refactors, local validation and repository maintenance.

## Mode 2: Multi-Agent

This mode must be explicitly requested or selected by the task card. It is justified only when the task is genuinely cross-module, independently parallel, Critical, or requires an independent acceptance review.

- One orchestrator defines the objective, write sets, dependencies and acceptance route.
- One implementation Agent writes the business change.
- One read-only reviewer is added only after an immutable Critical candidate exists.
- No standing technical lead, monitor or reporting Agent is created.
- The orchestrator must wait for the child result and may not emit a terminal receipt while a child is active.
- Findings return to the original implementation Agent; no automatic third repair Agent is created.
- Normal work remains serial even in this mode unless the task card proves independent write sets and rollback boundaries.

Use this mode for a large cross-module change, a proven parallel write, a Critical trading or permission change, or a separately requested architecture review.

## Mode 3: Web Contribution and Local Verification

Web GPT may prepare a plan or code change in GitHub. The local repository remains the verification authority.

- Web work must identify an exact GitHub commit or pull request.
- Web work must not directly overwrite the local dirty worktree.
- The local verifier checks the exact commit, changed-file scope, repository contracts and relevant tests.
- A dirty local worktree is a stop condition for automatic synchronization; preserve it and request an explicit no-loss procedure.
- Local verification does not imply merge, deployment, credentials, external connection or Live Write authorization.
- Merge to `main` is a separate Owner decision after local evidence is complete.

Use this mode when the Owner intentionally asks for web GPT planning or GitHub contribution followed by local verification.

## Owner Switches

The Owner does not need to understand internal role names. These plain-language switches are sufficient:

- `普通任务，单 Agent 直接完成。`
- `这是复杂任务，启用多 Agent：一个实现者，必要时一个只读审查者。`
- `网页 GPT 先提交方案或代码；本地按这个 commit 同步并验证，不要直接合并。`

If no switch is present, use Mode 1.

## Terminal Receipt Rule

The eight-field receipt is a task-closure format, not a progress format. During an active task do not emit `next_gate` as if the task were complete. Emit the final receipt only when the requested capability is delivered, a real blocker cannot be safely resolved, an Owner authorization is required, or the Token budget gate stops the task.
