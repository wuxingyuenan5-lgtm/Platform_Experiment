# AI Development Governance

This reference is read only when the Owner explicitly requests governance context or the task directly changes governance. It is not a startup gate.

## Authority

1. Direct Owner authorization and applicable safety policy.
2. `AGENTS.md`.
3. Directly affected contracts and runbooks when needed.

Direct Owner authorization may select an operating mode but cannot weaken trading, credential, or Live Write safety.

## Default Execution

Mode 1 is the normal path: one Agent directly completes one Owner request on `main`. It has no parent, child, coordinator, technical lead, project lead, reviewer, task card, branch, Worktree, global lock, or monitoring Agent by default.

An Agent reads only the context needed to solve the request. Context Packs, task cards, status records, and this document are on-demand references, not default startup inputs. It preserves user changes and runs validation needed for the changed surface.

Mode 2 is allowed only by explicit Owner request for multi-Agent execution. Mode 3 is allowed only by explicit Owner request for a Web GPT/GitHub candidate and local verification. Neither is inferred from task complexity, criticality, available capacity, a task card, or a profile file. An explicit Mode 2 record may define independent parallel write sets and recovery evidence, but must never become a normal-task gate.

## Progress, Recovery, and Closure

Progress belongs in commentary. Ordinary tasks close with a concise outcome and relevant evidence, not a fixed receipt. A type error, failed test, source-location problem, local service recovery, ordinary API failure, or normal interface mismatch is work to diagnose and safely repair.

For external credentials, API access, or Live Write, finish all safe local and read-only work first, then pause for explicit authorization. Do not infer permission from repository files, CI, or prior chats.

## Task Records and Token Use

Ordinary Mode 1 work does not require a task card, Issue, status event, Token budget, Token snapshot, or Token gate. A task record remains optional for explicit Mode 2 work, critical acceptance, recovery, parallel writes, or separately Owner-gated immutable evidence.

There are no standing monitor Agents, mandatory polling loops, or repository-enforced serialization across chats. Different chats may proceed independently while preserving normal Git conflict discipline.

## Hooks and Local Configuration

Project Codex configuration is intentionally minimal. Project hooks, runtime injection, and agent profiles do not route or block work.

## Non-Negotiable Financial Safety

- Live Write remains disabled by default.
- Never guess, create, expose, or configure credentials.
- Preserve Decimal precision and timezone-aware timestamps at financial boundaries.
- `result_unknown` fails closed and is never blindly retried.
- Real trading retains idempotency, one-business-intent protection, duplicate prevention, cumulative-fill ceilings, position convergence, Kill Switch controls, and safe reconciliation.
- Repository validation does not prove external connectivity, account state, deployment, credentials, or Live Write authorization.
