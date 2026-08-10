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
- Project lead: state stewardship, task routing, phase coordination and task closure; does not become the default implementer.
- Technical lead: invoked by phase; owns technical approach, module boundaries, implementation decomposition and technical acceptance.
- Investigation agent: read-only by default; gathers current-state, root-cause, external-reference and risk evidence.
- Implementation agent: the single file-modification owner for one workflow.
- Acceptance agent: independently reads contracts, diff and test evidence; does not repeat implementation.
- Project coach or independent auditor: used for repeated rework, Token anomalies, role conflict, major releases or architecture disputes.

Roles are bound by a task card, not by permanent chat assignments.

## Task startup protocol

Every task card contains at minimum these required fields: `role`, `objective`, `context_pack`, `authority`, `write_scope`, `non_goals`, `acceptance`, `stop_conditions`, and `output_contract`. Additional safety, contract, rollback or evidence fields are allowed. Missing required fields prohibit scope expansion.

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

## Context Pack governance

Packs are stable task types, never release numbers or agent names. Each has `category`, `description`, `owner_modules`, `required`, `optional`, `checks`, `input_budget`, `output_budget`, `risk_level`, and `write_boundary`. Supported categories are `governance`, `architecture`, `product-domain`, `data-provider`, `execution-critical`, `frontend-display`, `identity-security`, `release-acceptance`, `operations`, and `documentation-only`.

Add or change a Pack only when a repeatable task type appears, a deployed module or durable ownership boundary changes, a Pack exceeds budget twice, agents repeatedly need the same out-of-pack file, or acceptance commands or an owning contract change. Do not create a Pack for every Issue or duplicate Packs per release.

## Token and coordination controls

Track required-file count, estimated input budget, tool-output volume, repeated file reads, task duration, handoffs, parallel implementers in one module, rework count, out-of-pack read frequency and long-task closure rate. These compare relative consumption only; they are not API billing.

Project leads consume phase status and short receipts. Technical leads consume module and contract context. Implementers consume direct code context. Acceptance agents consume contract, diff and evidence. Repeated over-budget work, repeated out-of-pack reads, rework, role conflict or an architecture dispute triggers technical-lead review and, when material, independent audit.
