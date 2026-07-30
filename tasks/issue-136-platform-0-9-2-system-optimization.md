# Issue #136 — Platform 0.9.2 全平台系统性优化任务包

## 状态

- Workstream: critical
- Issue: #136
- Draft PR: #137
- Baseline branch: `feature/issue-134-platform-0-9-1-unified-delivery`
- Frozen baseline SHA: `8114fce45e46e7920f316f49d03db12dc424acf1`
- Delivery branch: `refactor/platform-0.9.2-system-optimization`
- Current HEAD after Phase A plan: `5c16d56bf46873b47afa7d82d3a62cc513e049ed`
- Development/acceptance version: `0.9.2`
- Final accepted candidate: `0.10.1`
- Merge policy: Draft only; never auto-merge; never modify `main`; owner approval required.

## Core objective

对整个基金投研交易资管平台进行证据化审计、减负、架构与代码优化、命名治理、AI上下文和Token优化，并在保持平台可运行、前端视觉和业务/安全语义稳定的前提下，分阶段完成0.9.2开发验收，最终形成0.10.1正式候选。

对冲基金看板只是Research业务域中的一个模块，不是本任务中心。

## Phase A — Baseline and audit

- [x] Read the complete execution instruction and adopt it as scope and boundary.
- [x] Confirm the real 0.9.1 unified delivery line.
- [x] Freeze baseline at `8114fce45e46e7920f316f49d03db12dc424acf1`.
- [x] Create `refactor/platform-0.9.2-system-optimization`.
- [x] Create master Issue #136.
- [x] Create and keep Draft PR #137 against the frozen 0.9.1 unified branch.
- [x] Collect repository inventory and reproducible audit evidence through a read-only GitHub Actions workflow.
- [x] Audit frontend, Platform backend, Execution Runtime, identity/security, research/providers, A-share/申万, strategy/trading/risk, member assets/NAV, Financial Fact/PnL/accounting/reconciliation, database/migrations/backup, operations, tests/CI/local run, documentation, AI context and legacy naming.
- [x] Quantify representative task context cost: file count, code/doc lines, cross-service reads, repeated facts and misleading paths.
- [x] Produce `docs/architecture/PLATFORM_0_9_2_SYSTEM_OPTIMIZATION_MASTER_PLAN.md` from repository evidence.
- [x] Run baseline Platform API and Runtime test suites: Platform API `418 passed`; Runtime `76 passed`.
- [ ] Enable the complete governed CI matrix for PRs based on the frozen 0.9.1 unified branch.
- [ ] Capture a durable pre-refactor visual baseline for all core pages at 1440/1024/768/390.

## Phase A evidence

- Corrected audit workflow run: `30560041240` — success.
- Corrected audit evidence snapshot: `cbe4e97fb3b179608e9b95633a84d88627793d0e`.
- Frozen product tree: approximately 1,776 text files, 276,992 lines and 2,014,104 estimated text tokens.
- Master plan commit: `5c16d56bf46873b47afa7d82d3a62cc513e049ed`.
- Product behavior changes in Phase A: none.

## Confirmed high-level decisions

1. Keep the three deployment and safety boundaries: Platform Web, Platform API modular monolith and Execution Runtime.
2. Do not introduce microservices, Kubernetes, Kafka/RabbitMQ, GraphQL, CQRS, Event Sourcing or micro-frontends.
3. Treat authority drift, template/history noise, flat module ownership, high-frequency large files and conflicting legacy deployment paths as the primary optimization targets.
4. Recommend isolated directory renames: `admin-risk → platform-web`, then `platform-backend → platform-api`; keep `execution-runtime`.
5. Do not delete or rename `projects/risk-control` until real production/MySQL/server dependencies are confirmed.
6. Perform AI/context reduction before broad code refactoring so later phases operate with smaller, more reliable reading packages.
7. Use Research, Identity and Portfolio as low-risk modularization pilots before touching trading, risk, accounting, reconciliation or Runtime.

## Next gate

Before Phase B or any broad refactor:

1. Make the full CI, Secret Scan, Version Consistency, browser E2E and Provider Smoke workflows run for Draft PR #137's non-`main` base.
2. Confirm the resulting checks remain green without weakening TLS, security, type or test gates.
3. Freeze core-page visual baselines.

After that gate, start Phase B: single authority for current state, AI context map, historical-document isolation and task-specific reading entrypoints.

## Decision categories

Every audit finding must be classified as one of:

1. Must change in 0.9.2.
2. High-value change after a safe pilot.
3. Keep unchanged because current design is suitable.
4. Defer because migration risk exceeds benefit.
5. User confirmation required because business, accounting, trading, permission, brand or irreversible migration semantics would change.

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

Do not introduce microservices, Kubernetes, Kafka/RabbitMQ, GraphQL, CQRS, Event Sourcing, micro-frontends, a new frontend framework, a second global state system or abstraction layers without clear repository evidence and measurable benefit.

Do not split files solely by line count. Do not mechanically replace legitimate financial terms, fixtures, historical records or third-party licenses. Directory renames must be isolated from behavioral refactors.

## Stage gate and rollback

Each main stage must have:

- a bounded goal and file scope;
- baseline and acceptance commands;
- a separate commit group;
- a documented rollback point;
- no stacking of large changes on a failed stage.

Pause and report when a change would alter business/trading/accounting/permission semantics, require an irreversible migration, prevent visual parity, expose a secret, disable TLS/security/type checks, require modifying `main`, or reveal an unstable baseline.
