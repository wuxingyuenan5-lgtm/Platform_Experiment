# AI Development Governance

This document is the durable operating system for AI-assisted development. It applies to all modules and releases; it is not a release plan or a record of current task progress.

## Authority hierarchy

1. Direct owner authorization and applicable safety policy decide what may be done now.
2. `AGENTS.md` defines global startup, safety and single-writer boundaries.
3. `docs/codex/current-state.md` defines the stable baseline, candidate, authorized stage, verified facts and known limits.
4. Module `AGENTS.md` files define module ownership, prohibitions and baseline checks.
5. Owning contracts define durable business semantics; runbooks define operational disposition.
6. `scripts/context-packs.json` and `scripts/context-for.py` define the minimum context and verification route for a stable task type.
7. An Issue or equivalent task card defines one-time objective, write scope, non-goals, acceptance and blockers; a PR preserves implementation difference and evidence.
8. Chat history is not project authority and does not preserve project state.

When authorities conflict, stop the affected work, identify the conflict and route it to the project owner or technical lead. A lower authority cannot silently weaken a higher safety boundary.

## Roles

- Project owner: product scope, priority, risk acceptance, stage authorization and final acceptance.
- Development advisor: a long-term, independent and read-only-by-default advisor to the project owner. Reviews Vibe Coding practice, Token and AI-resource efficiency, project strategy, architecture fit and reusable AI-development methods. The advisor does not replace the project lead or technical lead, direct routine implementation or create process merely to demonstrate value; when no material issue exists, the advisor should say that work may continue.
- Project lead: a long-term coordination owner for state stewardship, objective decomposition, task routing, phase coordination and task closure. The project lead routes coding objectives to the project technical lead instead of directly managing coding agents.
- Project technical lead: the long-term technical owner for the whole project across modules and releases. Owns architecture direction, module and contract boundaries, technical roadmap, implementation decomposition, technical risk and evidence sufficiency. The technical lead arranges technical investigation, coding agents, test work and technical acceptance, but does not set product priority, expand scope or accept business risk.
- Investigation agent: read-only by default; gathers current-state, root-cause, external-reference and risk evidence.
- Implementation agent: the single file-modification owner for one workflow.
- Acceptance agent: independently reads contracts, diff and test evidence; does not repeat implementation.
- Research, communication and specialist-audit agents are temporary and receive only the context needed for their assigned evidence or communication outcome.

The project owner, development advisor, project lead and project technical lead may remain long-term responsibilities. This does not make their chats project authority or require them to retain implementation history. Every concrete investigation, implementation or acceptance action remains bound by a task card rather than a permanent chat assignment. The development advisor, project lead and project technical lead report independently to the project owner; delivery and technical disagreements are preserved as short decision briefs for owner disposition rather than silently overriding either role.

The project technical lead does not modify business source or become the fallback implementer inside its long-term governance task. It may write technical task cards, create isolated worktrees, run read-only orientation or evidence checks, select implementation and review channels, and route findings. Business code, implementation tests and fix rounds belong to the single temporary implementation owner; independent reviewers remain read-only. The technical lead retains only the active technical task map, contract decisions, material findings and next gate, not step-by-step worker commentary or test logs.

The project lead proactively notifies the project owner when an active routed task becomes idle because it reached an owner gate, becomes blocked, changes approved scope or reports a material risk. The owner must not be expected to infer this state from the task list. Ordinary progress remains in the task record and does not require chat narration.

Codex task messages and delegated agents do not reliably wake every upstream task when the receiver completes. After routing work, each coordinator records the complete active chain in the task card: parent task, current leaf agent identifier, branch or worktree, immutable starting reference and status. The coordinator waits on the current leaf with the appropriate task or agent wait mechanism until completion, attention or an explicit handoff; after a new reviewer or fix owner is dispatched, monitoring moves to that new leaf. Confirming that a child started is not a valid terminal state, and a sent request is not monitored merely because the receiver was told to report back. When a leaf reaches terminal state, its coordinator reads evidence from system files and Git, advances already-authorized review, repair or integration work, updates the task card, and only then may its own turn end. The project lead separately monitors the technical-lead task plus the recorded current leaf and notifies the owner when an owner gate, blocker, scope change, material risk or version milestone exists.

## Risk-proportionate delivery and execution channels

Governance is a risk ceiling, not a mandatory large-team ceremony. A small, reversible and non-critical task may use one implementer and its direct checks. Ordinary multi-file work adds investigation or acceptance only when it lowers expected rework. Trading, Live Write, identity and permission, database, public-contract, deployment and other critical work uses explicit technical review and independent acceptance. Do not create an agent when direct handling costs less context and produces equally reliable evidence.

The project technical lead selects and briefs the implementation channel. A web AI may act as a temporary GitHub-based implementation agent for authorized ordinary code, tests or documentation and deliver an immutable branch, commit or pull request for focused local validation. It is not a long-term control role and does not join project-owner, project-lead, project-technical-lead or development-advisor discussions unless the project owner requests it. Web AI work does not currently include trading or Live Write, identity or permission, database, credentials, external-account access or deployment. Local and web agents must not share file-modification ownership in one workflow, and successful use does not expand future authority automatically.

## Bounded concurrency and implementation ownership

Multi-agent delivery uses bounded concurrency rather than a project-wide single agent:

1. The whole project has at most four active temporary agents: at most two implementation agents and at most two read-only investigation or acceptance agents. Long-term governance roles are not implementation slots, but they may not bypass these limits by modifying business source.
2. One business workflow, public contract, database migration chain or shared file set has one implementation owner. Overlap in any of these boundaries makes the work serial even if individual paths appear different.
3. Two implementation agents may run concurrently only when the technical lead proves before dispatch that their declared write sets are disjoint, neither depends on unfinished output from the other, and each can be tested and rolled back independently. Unproven independence defaults to serial execution.
4. Every implementation agent has a separate task card, `codex/` branch and isolated worktree. A shared branch, shared worktree or undocumented write set prohibits concurrent implementation.
5. Critical work uses one implementation agent plus one read-only acceptance agent. The acceptance agent reviews an immutable reference and may not repair it.
6. Review findings return to the original implementation owner. Do not create another implementation agent to fix the same workflow concurrently.
7. If an implementation agent becomes unavailable or unusable, its coordinator first marks it closed and records its last immutable reference, branch, worktree and unresolved state. Only then may a named recovery owner take over through a new task card or explicit task-card reassignment.
8. Before dispatch, the technical lead records write set, any parallel peer write set, shared workflow or contract boundary, dependency state, independent test command, rollback boundary and serial-or-parallel decision in the task card. The coordinator also verifies resulting active-agent counts stay within project limits.
9. Investigation agents are read-only evidence collectors. They do not modify repository or external state, become implicit implementers or delegate further.

System files or the Issue/PR own agent status. Active means dispatched but not closed, including blocked or review-waiting agents; a slot releases only after final state is recorded.

## Task startup protocol

Every task card contains at minimum these required fields: `task_id`, `role`, `risk_level`, `status`, `agent_id`, `objective`, `context_pack`, `authority`, `implementation_owner`, `branch`, `worktree`, `base_commit`, `write_set`, `shared_boundary`, `dependencies`, `independent_test`, `rollback_boundary`, `parallel_decision`, `parallel_with`, `parallel_peer_write_set`, `acceptance_task`, `recovery_from`, `recovered_owner_status`, `non_goals`, `acceptance`, `stop_conditions`, and `output_contract`. Read-only tasks use `none` for implementation-only identity fields, declare `write_set: none (read-only)`, and still identify evidence scope. Missing required fields prohibit dispatch or scope expansion.

Task dispatch is system-file-first. A dispatch message contains only the task identifier, immutable authority reference or commit, Context Pack, task-card or Issue path and any new authorization delta. It does not duplicate full requirements, source, logs, historical summaries or agent process. A receiving agent must be able to cold-start from repository authorities and the task card without access to the sender's chat context; if it cannot, the task card is incomplete and work stops for correction.

New agents start in this order:

1. Read root `AGENTS.md`.
2. Read `docs/codex/current-state.md`.
3. Run `python scripts/context-for.py <pack>` using the project/environment-configured Python interpreter. If `python` is not on `PATH`, use the platform-provided configured dependency runtime; in Codex desktop, load workspace dependencies first and use the returned Python absolute path. Do not install an interpreter or bypass the Pack. If no configured interpreter resolves, stop and escalate.
4. Read the Pack required files.
5. Read the current Issue or task card.
6. State the understood objective, write scope and stop conditions.
7. Begin work.

Optional Pack files are loaded only for an explicit question. Do not scan the repository merely to become familiar with it.

The task card is the dynamic authority loaded at step 5. It is not copied into a static Pack, and it need not repeat the Pack required-file list. Reading static source that contains credential-loading code is not the same as reading a real secret; static code may be read within task scope, while actual secrets, external connections and Live Write remain separately prohibited unless directly authorized.

## Task closure and durable evidence

An agent ends with only: `outcome`, `changed_files`, `validations`, `evidence`, `contract_impact`, `unproven_facts`, `residual_risks`, and `next_gate`.

One-time status belongs in the Issue or PR. Only stable facts belong in current state or an owning contract. Do not transfer full chat summaries, source, diff or long logs to the next task. Close a completed task; a new phase starts a new task and reloads its Context Pack.

Issue cards preserve role, context pack, write scope, non-goals, acceptance, contract impact, unproven facts and Token/context anomalies. PRs preserve the resulting diff, verification evidence, contract impact, unproven facts and residual risk. Historical Issue or PR identifiers embedded in contracts are context, not live Git authority; current state and Git/GitHub facts read at execution time govern current status.

An acceptance task card must provide an immutable review reference, either a PR URL or commit range, plus an entry point to test evidence. If either is missing, the acceptance agent stops and requests correction. Repository checks alone cannot establish release completion, external connectivity or production readiness.

Temporary agents close after their result is accepted and routed to an Issue, PR or owning authority. Investigation agents do not delegate; other delegation is normally no deeper than two levels. Parallel work follows the bounded-concurrency proof above. Semi-long-term assistants are reserved for sustained, frequent, stable-boundary and read-only-by-default work whose reuse benefit exceeds restart cost; they are reviewed and closed when that condition no longer holds.

## Version, phase and conversation context

Context has five layers: durable project authorities; current-version scope and gates; current-phase decisions and risks; task-card and Context Pack inputs; and immutable diff or test evidence. Long-term roles retain only the conclusions and unresolved risks appropriate to their responsibility. They do not retain full source, logs, diffs or chats as project memory.

A new version, phase or materially different topic normally starts a clean task and reloads the relevant Context Pack. Stable facts go to an owning contract or current state; one-time status and evidence go to an Issue or PR. Do not copy an old conversation into the new task. If discussion fails to converge after two focused rounds, repeats background, requires broad new source context or changes from product coordination into technical investigation, implementation or acceptance, the project lead creates a short decision brief and routes the issue to the project technical lead, development advisor, investigator, acceptance agent or project owner as appropriate.

## Context Pack governance

Packs are stable task types, never release numbers or agent names. Each has `category`, `description`, `owner_modules`, `required`, `optional`, `checks`, `input_budget`, `output_budget`, `risk_level`, and `write_boundary`. Supported categories are `governance`, `architecture`, `product-domain`, `data-provider`, `execution-critical`, `frontend-display`, `identity-security`, `release-acceptance`, `operations`, and `documentation-only`.

Packs route stable input, boundaries and checks; they are not role dossiers or version histories. The task card supplies the one-time role, objective, authority, non-goals, acceptance, stop conditions and `output_contract`. Together, the root startup files, nearest module rules, task-type Pack and task-card delta must be sufficient for a new agent to start without historical chat.

Add or change a Pack only when a repeatable task type appears, a deployed module or durable ownership boundary changes, a Pack exceeds budget twice, agents repeatedly need the same out-of-pack file, or acceptance commands or an owning contract change. Do not create a Pack for every Issue or duplicate Packs per release.

## Token and coordination controls

Track required-file count, estimated input budget, tool-output volume, repeated file reads, task duration, handoffs, parallel implementers in one module, rework count, out-of-pack read frequency and long-task closure rate. These compare relative consumption only; they are not API billing.

Development advisors consume project state, phase receipts, Token indicators and dispute material, not routine source or ordinary PR detail. Project leads consume version scope, phase status, acceptance gates and short receipts. Project technical leads consume module boundaries, owning contracts and the active technical task map, not the whole repository or historical chat. Implementers consume direct code and tests through the task Pack. Acceptance agents consume contracts, immutable diff and evidence rather than the implementer's full process. Repeated over-budget work, repeated out-of-pack reads, rework, role conflict or an architecture dispute triggers technical-lead review and, when material, independent advisor audit.

The multi-agent operating model is improved incrementally from observed delivery failures, Token evidence and owner feedback. Stable improvements belong in this governance authority, Context Packs or task templates rather than in remembered chat conventions. Do not add permanent roles, mandatory agents or ceremony solely to demonstrate process maturity.
