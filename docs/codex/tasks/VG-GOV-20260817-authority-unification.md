# Task: Unify 0.11.1 Governance And Accepted Execution Authority
Task ID: `VG-GOV-20260817-authority-unification`
Issue: `#none`
Status: `attention`
Last transition at: `2026-08-17 00:00 Asia/Shanghai`
Owner notice: `sent`
Business status summary: `Needs: the sole governance implementation owner must form one immutable HEAD containing 75e8e4a and da001936, correct control evidence, and bound only the live-readiness Pack.`
Current leaf task/agent ID: `none`
Risk level: `critical`
Role: `implementation`
Agent ID: `unassigned`
Context Pack: `governance`
Token baseline: `unavailable`
Token current: `unavailable`
Token delta: `unavailable`
Control-plane token delta: `unavailable`
Token budget: `2000000`
Token status: `unavailable`

## Objective
Create one traceable immutable repository authority that contains both governance commit `75e8e4a033639c4aaf082ac77720171d0044b3b0` and accepted 0.11.1 execution closure `da001936144c9299c6e2d89befceedd53077efca`, while preserving accepted behavior and making the next `live-readiness` context bounded.

## Implementation fields
- Implementation owner: `unassigned`
- Branch: `codex/vg-0111-authority-unification`
- Worktree: `C:\Users\jiuxi\Desktop\codex\全球变量平台\.codex\worktrees\vg-0111-authority-unification`
- Base commit: `75e8e4a033639c4aaf082ac77720171d0044b3b0`

## Protected semantics
- Preserve the accepted SF-01/SF-02 business commits and tests without rewriting, squashing or repairing business source.
- The unified HEAD must retain `75e8e4a` and `da001936` as ancestors.
- Program control must state global strategy batch serialization is complete and cite merge `ba629851170d2c3177002bbb127b449b64531ea2` plus closure `da001936144c9299c6e2d89befceedd53077efca`; no contradictory pending statement may remain.
- Without a trustworthy Token snapshot, all snapshot/delta fields are `unavailable`; estimates, inferred zeroes and chat-token guesses are prohibited.
- The control-plane 30 percent measure is a business-slice aggregate reporting metric, not a hard requirement applied independently to every task or leaf agent.
- Only the next `live-readiness` Pack may be compressed to its configured required budget. Do not repair or reclassify any other historical over-budget Pack.
- External connection, credentials, Live Write, controlled-live operation, real accounts, deployment and new 0.11.1 business development remain prohibited.
- Preserve every shared-workspace tracked modification and untracked file; never use the shared checkout as the merge workspace.

## Scope
- Non-squash integration of `da001936` into this isolated branch with explicit conflict resolution.
- Governance conflicts in `AGENTS.md`, `.github/ISSUE_TEMPLATE/engineering-task.yml`, `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`, `docs/codex/0.11.1-program.md`, `docs/codex/task-template.md`, governance task records, `scripts/check-task-card.py`, its tests, and Context Pack routing/check files.
- Minimal `live-readiness` Pack membership/compression changes in `scripts/context-packs.json` and `scripts/context-for.py` only when needed to keep required context within budget without weakening checks or safety authority.
- This task card and status-event evidence.
- Non-goals: business-source edits beyond immutable merge ancestry, frontend edits, broad Pack-budget cleanup, product scope changes, external-state activity, credentials, Live Write or real operations.

## Dispatch concurrency decision
- Write set: `AGENTS.md`; `.github/ISSUE_TEMPLATE/engineering-task.yml`; `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`; `docs/codex/0.11.1-program.md`; `docs/codex/task-template.md`; `docs/codex/tasks/VG-GOV-20260817-authority-unification.md`; governance task records introduced by either parent; `scripts/check-task-card.py`; `scripts/tests/test_check_task_card.py`; `scripts/context-for.py`; `scripts/context-packs.json`.
- Shared workflow, public contract, migration chain or file set: `repository governance authority and 0.11.1 program control`.
- Dependencies: `accepted SF-02 closure da001936; no unfinished implementation dependency`.
- Independent test: `governance Pack checks, task-card validator, ancestry checks, live-readiness budget assertion, and diff inspection proving no conflict-resolution edits to accepted business source`.
- Rollback boundary: `single governance merge branch and explicit post-merge governance commits; parents remain immutable`.
- Parallel decision: `serial`
- Parallel with: `none`
- Parallel peer write set: `none`
- Independence evidence: `not applicable; one implementation owner only`.
- Acceptance task: `VG-GOV-20260817-authority-unification-ACCEPTANCE`
- Active-agent count after dispatch: `1/2 implementation, 0/2 read-only, 1/4 total`
- Recovery from: `none`
- Recovered owner status: `closed`

## Context
- `docs/codex/0.11.1-program.md`
- Parent commits `75e8e4a033639c4aaf082ac77720171d0044b3b0` and `da001936144c9299c6e2d89befceedd53077efca`.
- Owner delta persisted in Protected semantics above.

## Verification
- `python scripts/check-task-card.py docs/codex/tasks/VG-GOV-20260817-authority-unification.md`
- `python scripts/context-for.py governance`
- `python scripts/context-for.py live-readiness`
- `python scripts/context-for.py --check-budgets --json`
- `python scripts/check-version-consistency.py`
- `python scripts/check-repository-structure.py`
- `python scripts/check-documentation-consistency.py`
- `git diff --check`
- `git merge-base --is-ancestor 75e8e4a HEAD`
- `git merge-base --is-ancestor da001936 HEAD`

## Progress
- Done: cold-started from `75e8e4a` with the governance Pack and confirmed the two required authorities are divergent.
- Current: task card persisted; awaiting sole implementation-owner dispatch.
- Next: merge, resolve only governance authority conflicts, compress only `live-readiness`, validate, then enter independent Critical acceptance.
- Blocked by: no trusted Token snapshot; owner has been notified and explicitly authorized this bounded governance unification while all external gates remain closed.
