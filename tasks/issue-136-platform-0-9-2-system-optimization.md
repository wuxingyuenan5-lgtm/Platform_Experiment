# Issue #136 — Platform 0.9.2 全平台系统性优化任务包

## 状态

- Workstream: critical
- Issue: #136
- Baseline branch: `feature/issue-134-platform-0-9-1-unified-delivery`
- Frozen baseline SHA: `8114fce45e46e7920f316f49d03db12dc424acf1`
- Delivery branch: `refactor/platform-0.9.2-system-optimization`
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
- [ ] Create and keep a Draft PR against the frozen 0.9.1 unified branch.
- [ ] Collect repository inventory and baseline evidence.
- [ ] Audit frontend, Platform backend, Execution Runtime, identity/security, research/providers, A-share/申万, strategy/trading/risk, member assets/NAV, Financial Fact/PnL/accounting/reconciliation, database/migrations/backup, operations, tests/CI/local run, documentation, AI context and legacy naming.
- [ ] Quantify typical-task context cost: file count, code/doc lines, cross-service reads, repeated facts and misleading paths.
- [ ] Produce `docs/architecture/PLATFORM_0_9_2_SYSTEM_OPTIMIZATION_MASTER_PLAN.md` from repository evidence.

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
