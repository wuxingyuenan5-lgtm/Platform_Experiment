# Acceptance Criteria

## Current Global Criteria

- Local frontend opens at `http://127.0.0.1:4373/index.html#/strategy/platform`.
- Start page opens at `http://127.0.0.1:4373/#/` as the dark star-map Variable Global landing screen.
- Start-page navigation must not show legacy labels `平台入口`, `研究框架`, or `新闻日历`; the AI entry is named `金融AI分析`.
- Clicking protected start-page entries routes to `/login?redirect=...`; after account login, the app redirects to the intended subpage.
- Start-page core entry cards use large gold functional icons and serif-style titles, and point to product modules such as `对冲基金看板`, `新闻日历与理财`, `策略研究`, `风控管理`, and `金融AI分析`.
- Logged-in top navigation uses readable 16px menu text at regular 400 weight and functional icons for every primary product entry, including `首页`, `新闻日历与理财`, `风控管理`, and `金融AI分析`.
- `#/home/index` is the logged-in Home Dashboard, not the public start page; it uses the butterfly-water topology visual as the hero background and shows market, portfolio, strategy, and calendar summary modules.
- Home Dashboard hero art must not expose baked-in legacy text from source images; the butterfly-water topology should use the high-resolution original-color asset as a controlled local visual layer behind the intended dashboard copy.
- Home Dashboard hero should render as one continuous butterfly-water visual field, not a split left-image/right-empty background; lower dashboard modules may overlap the hero edge to match the reference layout.
- Platform API health check returns 200 at `http://127.0.0.1:8000/health`.
- Platform Execution Runtime health check returns 200 at `http://127.0.0.1:8100/health` when runtime integration is enabled.
- Product pages must not show debug-only backend or runtime panels.
- Trading and account behavior changes require separate approval.
- Routine code search does not scan `node_modules`, `.venv`, `dist`, or `outputs`.
- Root SQL references live under `references/database/`.
- Large external reference code does not live in the project root.
- Shared documentation and default configuration must not bind the platform to a named developer workstation.

## Platform 0.11.1 staged criteria

The following are prospective gates, not completion claims. Repository validation alone never proves external credentials, venue connectivity, a real account or live execution.

1. Governance foundation: the designated authorities agree on the local founder-owned test-account exception, six gates, default-disabled Live Write and excluded scope; context-budget validation passes.
2. Connection verification and performance baseline: authorized read-only verification proves the configured data/account/order/fill/position paths and shadow reconciliation, with measured external-source, collector, database, API and browser p50/p95 latency and no silent 24-hour interruption.
3. Cross-venue spread controlled-live acceptance: automated, fault-injection, idempotency, duplicate-intent and `result_unknown` tests pass; each separately authorized Market-direction, FOK, TP/SL and PostOnly Chase step has complete venue evidence, reconciliation and forced reset.
4. Funding-rate data pipeline: authorized real data collection is durable, source/timezone/quality-addressable, deduplicated, queryable within the baseline-derived target, and has a collection success rate of at least 99%; it provides no live trading execution.
5. Strategy management and market pages: real, sample and unavailable data states are distinguished; accounts, orders, fills, positions, fees and PnL/NAV are traceable to their authoritative facts and sampled external reconciliation is exact; pages show freshness, delay and degraded state.
6. Final independent acceptance: security, browser, recovery, reconciliation, documentation and repository checks pass, and unverified external or production capability remains explicitly unclaimed.

## Identity, permission, and member-data criteria

The durable browser-access contracts are [Browser Access and Product Data](../contracts/BROWSER_ACCESS_AND_PRODUCT_DATA.md) and the [Platform 0.10.2 frontend access matrix](PLATFORM_0_10_2_FRONTEND_ACCESS_MATRIX.md).

- Browser Cookie and Bearer API Key are mutually exclusive request credentials; ambiguous requests fail closed.
- Browser Session uses server-side revocation, CSRF plus Origin validation, secure cookie settings in production, and immediate permission invalidation after role or status change.
- CEO, technical lead, employee, and member permissions are enforced on the server for routes, fields, actions, and resource scope; direct URL access cannot bypass them.
- All four browser-role classes have access to their own personal account.
- CEO, technical lead and employees retain both their authorized risk-management scope and their own personal account.
- Members retain their own personal account but have no risk-management or user-management access.
- A member cannot use Path, Query, ID or API parameters to switch the personal-account scope to another user or internal organization data.
- Employees have read-only formal business pages; backend business or other-account write requests must return 403.
- Menu visibility, direct URL authorization and backend API authorization must resolve consistently from explicit permissions and data scope.
- A member can read only their own fund holdings. Administrative full-holding reads and holding changes require explicit permission, recent reauthentication, transactionally coupled audit, and Decimal-string responses.
- The last active CEO cannot be disabled or downgraded, including concurrent requests. Passwords, raw tokens, API keys, complete contact details, and complete holding snapshots never enter Git or ordinary logs.
- Browser identity never authorizes Platform or Runtime Live Write. LiveTradingSession, Kill Switch, absolute limits, approval, reconciliation, and data-quality gates remain independently required.

## User-system deployment and rollback gates

- Before production cutover, confirm whether real legacy users exist, identify the authoritative holding source, and verify same-origin TLS, reverse proxy, cookie security, backup, avatar restore, and rate limiting.
- Legacy user import, when required, is dry-run capable, idempotent, excludes old Sessions, never auto-promotes an old admin to CEO, and records only counts and redacted errors.
- Schema migrations are append-only and must pass fresh-database, upgrade, repeat-initialization, checksum-drift, failed-rollback, index, and foreign-key tests without changing existing trading, accounting, reconciliation, or audit facts.
- A failed identity or holding cutover rolls back the complete deployment unit; it must not leave mixed identity authorities or partially migrated customer data.

## Global product and frontend criteria

- Every page exposes explicit loading, empty, error, stale/delayed, partial, permission-denied, read-only and degraded states where applicable.
- Restored formal product pages distinguish `live`, `sample`, `unavailable` and `error` states in their internal data model.
- Internal envelopes retain source and actionability boundaries, but ordinary product UI uses concise business language and does not expose Provider, source, `actionable` or architecture information.
- `sample` state is non-actionable and cannot trigger save, strategy deployment, order, execution or provider actions.
- `error` state remains explicit and cannot be silently presented as a normal `live` or `sample` result.
- Unknown, delayed or incomplete financial data is never rendered as confirmed zero.
- Commands are idempotent, auditable and recoverable; `result_unknown` remains unknown until authoritative reconciliation.
- Monetary, price and quantity values use exact Decimal/string contracts, explicit currency/unit and UTC timestamps.
- Module degradation remains bounded: a failed external widget, provider or realtime channel cannot erase unrelated page content.
- Responsive behavior preserves the primary decision path; secondary panels may stack or collapse but critical status, risk and action context remain visible.
- The visual candidate covers the current four formal viewport widths and records evidence against the candidate under review.
- Sensitive credentials, approval evidence and unrestricted personal data never enter routes, browser persistence or client logs.
