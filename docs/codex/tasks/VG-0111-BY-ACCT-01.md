# Task: Bybit Strategy Accounts Data Wiring and Read Models
Task ID: `VG-0111-BY-ACCT-01`
Issue: `#none`
Status: `active`
Last transition at: `2026-08-21 00:00 Asia/Shanghai`
Owner notice: `sent`
Business status summary: `Capability: owner-authorized 0.11.1 scope extension for one funding-carry Bybit trading account and three Bybit read-only strategy accounts (bottom-fishing, short-term trader A, short-term trader B). Evidence: owner instruction in this task. Next gate: local contract and migration acceptance, then separately authorized credential-backed read-only verification; funding Live Write remains separately gated.`
Current leaf task/agent ID: `root`
Risk level: `critical`
Role: `implementation`
Agent ID: `root`
Context Pack: `strategy-management` (plus `funding-data` and `live-readiness` for bounded sub-workflows)
Token baseline: `unavailable`
Token current: `unavailable`
Token delta: `unavailable`
Control-plane token delta: `unavailable`
Token budget: `2000000`
Token status: `unavailable`

## Objective
Make one funding-carry Bybit account safely executable and make funding-carry, bottom-fishing, short-term trader A and short-term trader B PnL, capital and order facts queryable from authoritative Bybit data, with the latter three accounts structurally read-only.

## Implementation fields
- Implementation owner: `root`
- Mode: `Local`
- Branch/worktree exception: `none`
- Branch: `main`
- Worktree: `none`
- Base commit: `ddb83b5d5b45838b82fc5e58177aa8c5d75c07c7`

## Protected semantics
- Runtime owns all Bybit SDK effects; Platform API keeps Decimal values and UTC timestamps at financial boundaries.
- Only the funding-carry account may originate an order command, and only through the existing independently gated Live Write session, Kill Switch, idempotency and reconciliation contracts.
- All authorized roles retain read access to strategy-account PnL, capital and orders. Funding-carry and cross-spread commands are CEO-only. The existing development-only `admin` bridge is the demonstration CEO account; technical-lead, employee, member and production API-admin identities cannot use it as a bypass.
- Bottom-fishing and both short-term trader accounts must reject every order/cancel/amend command before Runtime dispatch.
- A missing credential or failed source is `unavailable` or `error`; it is never silently replaced by mock data or zero balances/PnL.
- No credential, external connection, real order, deployment or Live Write step is authorized by this task card.

## Scope
- Included: binding existing strategy surfaces to their account/strategy registry entries, per-account Runtime read contracts, authoritative order/fill/position/balance/economic-event sync, PnL/NAV read models, funding-only command account enforcement, replacement of affected mock data in existing management surfaces, tests and explicit UI data states.
- Existing page layout, navigation and information architecture are retained. This task does not rebuild or redesign the user interface.
- Non-goals: automatic strategy selection, sizing, rebalancing, unattended trading, production deployment, use of credentials before separately supplied and authorized, or trading commands for the three read-only accounts.

## Dispatch concurrency decision
- Write set: `docs/codex/{current-state.md,0.11.1-program.md,tasks/VG-0111-BY-ACCT-01.md}; docs/superpowers/{specs,plans}; platform-api/app/{database_bootstrap.py,catalog.py,schemas.py,trading.py,trading_routes.py,live_venue_snapshot_sync.py}; platform-api/tests/*account*; execution-runtime/app/{config.py,bybit_live_adapter.py,gateway_routes.py,models.py}; execution-runtime/tests/*bybit*; platform-web/src/{api/platform/trading.ts,api/platform/trading.types.ts,views/strategy/management/**}`
- Shared workflow, public contract, migration chain or file set: `Bybit strategy account registry, private-account read model and funding command boundary`
- Dependencies: existing `VG-0111-FC-01` local closed-loop evidence; credential-backed verification is a later owner gate.
- Independent test: `cd platform-api && python -m pytest tests/test_strategy_account_* tests/test_funding_local_closed_loop.py`
- Rollback boundary: one dedicated migration commit, followed by one API/Runtime/UI implementation commit.
- Parallel decision: `serial`
- Parallel with: `none`
- Parallel peer write set: `none`
- Independence evidence: one shared account registry, Runtime adapter and strategy-management surface require a single writer and serialized integration tests.
- Acceptance task: `owner acceptance after immutable candidate`
- Active-agent count after dispatch: `1/1 implementation, 0/1 read-only, 1/2 total`
- Recovery from: `none`
- Recovered owner status: `n/a`

## Context
- `docs/codex/0.11.1-program.md`
- `docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md`
- `docs/contracts/BROWSER_ACCESS_AND_PRODUCT_DATA.md`

## Verification
- Relevant Context Pack checks for `strategy-management`, `funding-data` and `live-readiness`.
- Focused Platform API, Runtime and web tests added by this task; `git diff --check`; required repository consistency checks.

## Progress
- Done: registry capability migration, four Bybit account bindings, unified account-snapshot API, Decimal-safe account PnL aggregation, runtime account-to-credential isolation, runtime read-only write denial, CEO/demo-CEO market-command and generic-command gate, and existing management-surface API wiring for funding, bottom-fishing, short-term trader A and B.
- Current: run bounded local acceptance and repository consistency checks; no affected surface now renders static PnL/capital/order samples as live facts.
- Next: credential-backed Bybit private-read verification for each account, then a separately authorized funding Live Write acceptance window.
- Blocked by: external API verification is intentionally blocked until credentials are supplied; no mock replacement or Live Write inference is permitted.
