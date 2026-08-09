# Active Technical Debt

This register contains only unresolved work with a concrete risk and trigger. Completed refactor history belongs in GitHub.

## TD-003 — Operational projection retirement

- **Status:** accepted
- **Risk:** consumers may treat low-latency `positions` or `pnl_results` as formal accounting truth.
- **Protected rule:** formal accounting never reads operational projections as inputs.
- **Trigger:** every consumer is inventoried and a replacement latency SLA is proven.

## TD-004 — Frontend inherited lint debt

- **Status:** active, contained by no-new-debt checks.
- **Risk:** untouched template modules still contain warnings.
- **Trigger:** clean a module only when that module receives real product work.
- **Protected rule:** no mass-formatting or behavior-changing cleanup PR.

## TD-005 — Progressive Python typing

- **Status:** active.
- **Risk:** legacy untyped rows and payloads may drift outside selected critical modules.
- **Trigger:** add a module to Pyright when it receives material work and its public boundary is clear.
- **Protected rule:** do not change runtime behavior solely to satisfy typing.

## TD-006 — Real production evidence

- **Status:** active, Issue #39.
- **Risk:** CI cannot prove Broker timing, private-stream behavior, partial fills or recovery.
- **Trigger:** controlled Windows host, approved accounts and minimum-size checklist are ready.
- **Protected rule:** Live Write remains disabled by default.

## TD-007 — Repository branch protection

- **Status:** administrator verification pending, Issue #38.
- **Risk:** repository settings may allow bypass even when code-level checks exist.
- **Trigger:** verify required Platform CI and Secret Scan checks, block direct/force pushes and enable merged-branch cleanup in GitHub Settings.
## TD-008 — Deferred production and external capability closure

- **Status:** active and protected.
- **Risk:** repository-level contracts may be mistaken for proven server, broker, database or recovery readiness.
- **Trigger:** approved production evidence for hosts, TLS, Runner, MySQL, backup/restore, credentials and minimum-size Venue execution.
- **Protected rule:** do not delete Legacy evidence, enable Live Write or replace external routes before owner acceptance.

## TD-009 — Windows local multi-service start/stop lifecycle governance

- **Status:** active, deferred to next development stage.
- **Risk:** local Platform Web, Platform API, execution runtime and legacy comparison frontend can leave stale listener processes, ambiguous port ownership or misleading health state after repeated starts and stops.
- **Scope:** process identity verification, port conflict handling, residual process cleanup, repeated start/stop idempotence, new/old version parallel operation, logs and diagnostics.
- **Trigger:** before declaring local lifecycle management complete or promoting a one-command Windows operator workflow.
- **Protected rule:** do not stop unrelated Node, Python or PowerShell processes by name or port alone; verify ownership before stopping.
## TD-010 - Global risk and notification message source

- **Status:** active, deferred until a Capability or explicit backend service is available.
- **Risk:** the formal risk detail page is available, but the global risk message strip and notification center currently have no backend message source; unconditional polling would create noisy 404s and misleading product state.
- **Current behavior:** global risk and notification surfaces show empty business states without API, Provider or engineering explanations in the user interface.
- **Trigger:** restore only after a maintained Capability or explicit service configuration defines message source, permissions and failure semantics.
- **Protected rule:** do not reintroduce timer polling against nonexistent `/risk` or `/notifications` endpoints.
