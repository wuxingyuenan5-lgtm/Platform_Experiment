# Agent Operating Modes

This is a short optional reference. It does not replace `AGENTS.md`, safety contracts, or explicit Owner authorization.

## Mode 1: Single Executor

Mode 1 is the default. One Agent directly completes the Owner request with only the context and validation the task needs.

- Do not create a coordinator, lead, worker, reviewer, monitoring Agent, task card, branch, Worktree, global lock, or standing status event for ordinary work.
- Treat one Owner request as one continuous task. Source discovery, type errors, failed tests, local service recovery, and normal interface failures are work to resolve, not reasons to stop.
- Context Packs, task cards, governance documents, branches, Worktrees, locks, and monitors are optional; read or create them only when explicitly requested or technically necessary.
- Send short progress through commentary and close ordinary work with a concise outcome and relevant evidence.
- Do not connect external accounts, configure credentials, restart unrelated services, or perform Live Write unless the Owner explicitly authorizes the specific operation. Before a credential, external API, or Live Write gate, complete all safe local and read-only work, then pause once with the single missing condition.

Use this mode for normal features, bug fixes, bounded refactors, local validation, documentation, and repository maintenance.

## Mode 2: Explicit Multi-Agent Work

Mode 2 is enabled only when the Owner explicitly asks for multi-Agent execution. It is never inferred from task size, available capacity, a task card, or a criticality label.

- The explicit request defines the objective, write sets, dependencies, validation, and rollback boundary.
- No project lead, technical lead, or monitor is automatically created. Use only the minimum named roles required by the Owner request.
- Parallel writes require independent write sets, tests, and rollback boundaries. Otherwise work remains serial.
- A task record is optional evidence for the explicit workflow; it is not a prerequisite for Mode 1.

## Mode 3: Web Contribution and Local Verification

Mode 3 is enabled only when the Owner explicitly asks for a Web GPT or GitHub contribution plus local verification.

- The Owner supplies an exact commit or pull request.
- Local verification preserves a dirty worktree and does not merge, deploy, configure credentials, connect accounts, or enable Live Write.

## Safety That Applies in Every Mode

- Live Write is disabled by default. Never guess, create, print, or configure credentials.
- `result_unknown` fails closed and is never blindly retried.
- Real trading requires idempotency, duplicate-prevention, bounded cumulative-fill protection, position convergence, and the existing Kill Switch safeguards.
- Hooks may block only clearly destructive commands, credential operations, and unauthorized Live Write entrypoints. Hooks must not block ordinary reads, tests, or normal code modification, and must not serialize independent chats.

## Owner Switches

- `普通任务，单 Agent 直接完成。`
- `这是复杂任务，启用多 Agent：<明确角色和范围>。`
- `网页 GPT 先提交方案或代码；本地按这个 commit 同步并验证，不要直接合并。`

Without an explicit switch, use Mode 1.
