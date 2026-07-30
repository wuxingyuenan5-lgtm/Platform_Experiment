# Issue #136 — Platform 0.9.2 全平台系统性优化任务包

Workstream: critical
Issue: #136
Branch: `refactor/issue-136-platform-0-9-2-system-optimization`

## 状态

- Baseline branch: `feature/issue-134-platform-0-9-1-unified-delivery`
- Frozen baseline SHA: `8114fce45e46e7920f316f49d03db12dc424acf1`
- Development/acceptance version: `0.9.2`
- Final accepted candidate: `0.10.1`
- Merge policy: Draft only; never auto-merge; never modify `main`; owner approval required.
- Live Draft PR, HEAD, CI and review status: GitHub Issue #136.
- Superseded PRs #137 and #138 remain closed and unmerged as branch-governance migration history.

## Core objective

对整个基金投研交易资管平台进行证据化审计、减负、架构与代码优化、命名治理、AI上下文和Token优化，并在保持平台可运行、前端视觉和业务/安全语义稳定的前提下，分阶段完成0.9.2开发验收，最终形成0.10.1正式候选。

对冲基金看板只是Research业务域中的一个模块，不是本任务中心。

## Phase A — Baseline and audit

- [x] Read the complete execution instruction and adopt it as scope and boundary.
- [x] Confirm the real 0.9.1 unified delivery line.
- [x] Freeze baseline at `8114fce45e46e7920f316f49d03db12dc424acf1`.
- [x] Create the independent 0.9.2 optimization line.
- [x] Create master Issue #136.
- [x] Create and keep a Draft PR against the frozen 0.9.1 unified branch.
- [x] Collect repository inventory and reproducible audit evidence through a read-only GitHub Actions workflow.
- [x] Audit frontend, Platform API, Execution Runtime, identity/security, research/providers, A-share/申万, strategy/trading/risk, member assets/NAV, Financial Fact/PnL/accounting/reconciliation, database/migrations/backup, operations, tests/CI/local run, documentation, AI context and legacy naming.
- [x] Quantify representative task context cost: file count, code/doc lines, cross-service reads, repeated facts and misleading paths.
- [x] Produce `docs/architecture/PLATFORM_0_9_2_SYSTEM_OPTIMIZATION_MASTER_PLAN.md` from repository evidence.
- [x] Run baseline Platform API and Runtime test suites: Platform API `418 passed`; Runtime `76 passed`.
- [x] Extend the existing governed CI matrix to PRs based on the frozen 0.9.1 unified branch.
- [x] Migrate the delivery line to the repository-compliant Critical branch syntax.
- [ ] Capture durable pre-refactor visual baselines for all core pages at 1440/1024/768/390.

## Phase A evidence

- Corrected audit workflow run: `30560041240` — success.
- Corrected audit evidence snapshot: `cbe4e97fb3b179608e9b95633a84d88627793d0e`.
- Frozen product tree: approximately 1,776 text files, 276,992 lines and 2,014,104 estimated text tokens.
- Platform API baseline: `418 passed`.
- Execution Runtime baseline: `76 passed`.
- Initial complete CI attachment proved Backend, Runtime, Frontend, both browser E2Es, Secret Scan, Version Consistency and Provider Smoke passed; Repository Safety correctly rejected non-governed branch syntax. The branch was migrated rather than weakening the check.
- Product behavior changes in Phase A: none.

## Phase B — Authority and AI context reduction

- [x] Synchronize maintained version declarations to `0.9.2`.
- [x] Make `docs/codex/current-state.md` the sole current engineering-state document.
- [x] Convert `docs/codex/CURRENT_CONTEXT.md` into a non-authoritative compatibility pointer.
- [x] Remove volatile branch, commit and task progress from `AGENTS.md` and `README.md`.
- [x] Expand `docs/codex/context-map.md` into bounded domain reading packs and default exclusions.
- [x] Rewrite `scripts/check-codex-context.py` to derive repository facts instead of hardcoding version and main commit.
- [ ] Re-run version, context, repository structure and documentation checks on the final governed branch.
- [ ] Re-run the complete PR quality matrix before beginning product-code refactoring.
- [ ] Re-measure representative task context cost.

## Confirmed high-level decisions

1. Keep the three deployment and safety boundaries: Platform Web, Platform API modular monolith and Execution Runtime.
2. Do not introduce microservices, Kubernetes, Kafka/RabbitMQ, GraphQL, CQRS, Event Sourcing or micro-frontends.
3. Treat authority drift, template/history noise, flat module ownership, high-frequency large files and conflicting legacy deployment paths as the primary optimization targets.
4. Recommend isolated directory renames: `admin-risk → platform-web`, then `platform-backend → platform-api`; keep `execution-runtime`.
5. Do not delete or rename `projects/risk-control` until real production/MySQL/server dependencies are confirmed.
6. Perform AI/context reduction before broad code refactoring so later phases operate with smaller, more reliable reading packages.
7. Use Research, Identity and Portfolio as low-risk modularization pilots before touching trading, risk, accounting, reconciliation or Runtime.

## Protected invariants

- Browser Session and API-Key permission isolation.
- CSRF and Origin validation.
- User roles, member data isolation and last-CEO protection.
- Decimal money, Financial Fact, PnL, NAV, formal accounting and reconciliation semantics.
- Immutable database migrations and recoverability.
- Kill Switch, two-person approval and Live Write disabled by default.
- Idempotency, Market, FOK, PostOnly, TP/SL and Result Unknown semantics.
- EOD, reconciliation, Last Known Good and `partial`/`stale`/`no_data`/`error` states.
- TLS verification.
- Platform API and Execution Runtime boundary.
- Existing user-visible layout, visual hierarchy, main workflows and responsive behavior unless an explicit defect is approved.

## Engineering boundary

Do not introduce heavy infrastructure or abstraction layers without repository evidence and measurable benefit. Do not split files solely by line count. Do not mechanically replace legitimate financial terms, fixtures, historical records or third-party licenses. Directory renames must be isolated from behavioral refactors.

## Stage gate and rollback

Each main stage must have a bounded goal and file scope, baseline and acceptance commands, a separate commit group, a documented rollback point and no stacking of large changes on a failed stage.

Pause and report when a change would alter business/trading/accounting/permission semantics, require an irreversible migration, prevent visual parity, expose a secret, disable TLS/security/type checks, require modifying `main`, or reveal an unstable baseline.
