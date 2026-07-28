# Task: Complete user system

Issue: #117  
Status: `handoff_ready`  
Branch: `feature/issue-117-user-system`  
Base commit: `71603bcc6807284ef3a6da26ad3f43c541bc99c2`

## Objective

Deliver one maintainable `platform-backend` user-system boundary for browser registration/login, server-side Sessions, four fixed business roles, personal accounts, backend user administration, operational notes, member fund holdings and auditable sensitive operations, without weakening API-key, LiveTradingSession or execution-safety controls.

## Delivered scope

- Human users with Argon2id passwords, opaque server-side Sessions and CSRF/Origin validation.
- Separate API-key and human-role namespaces resolved through one Principal boundary.
- Fixed roles: `ceo`, `tech_lead`, `employee`, `member`.
- Public member/employee registration, login, logout, reauthentication and one-time password-reset tickets.
- Personal profile, avatar, password and device/Session management.
- CEO/technical-lead user administration with target-role, field and data-scope policy.
- Transactional last-active-CEO guard, optimistic `row_version` and same-transaction audit.
- Admin-only operational notes whose plaintext is not exposed to members or stored in audit details.
- Member fund-holding and fund-unit-NAV customer-reporting read model using exact Decimal strings.
- Member asset overview with account valuation, invested amount, cumulative return and holding details.
- Permission-driven frontend navigation, account, user-management and holding/NAV pages.
- Stable authentication/authorization error codes with Request ID correlation.
- Additive Migrations 5–7, initial CEO CLI and same-origin `/api/v1` development path.
- Eight reusable development/test accounts: one CEO, one technical lead, three employees and three VIP members.
- User-domain table counts and avatar files included in the fail-closed production backup/restore boundary.

## Protected semantics

- Platform Live Write and Runtime Live Write remain disabled by default.
- Existing Live Write routes remain API-key-only and retain Actor Binding, LiveTradingSession, Kill Switch, reconciliation and absolute-limit gates.
- API-key `admin` wildcard does not become human CEO authority.
- Passwords, raw Session/CSRF/reset tokens, API keys, full customer contacts and real holding data must not enter Git, logs or audit details.
- Applied migrations are immutable; later corrections use additive migrations.
- Social login, MFA, SSO, arbitrary per-user permission overrides, hard deletion, subscription/redemption/payment/settlement and browser Live trading remain explicit non-goals.

## Automated acceptance

Clean handoff head before documentation finalization: `242cc03966bc437da08dd6a35b448d09ebc0c932`.

Passed runs:

- Platform CI `30374949395`
  - Repository Safety passed.
  - Platform Backend dependency validation, Ruff, Pyright and **403** classified tests passed.
  - Execution Runtime full matrix passed with no Runtime/Venue behavior change.
  - Frontend access tests, ESLint, no-new-debt gate, type checks and production build passed.
- User System Browser E2E `30374950288` passed.
- Secret Scan `30374949706` passed.
- Version Consistency `30374949357` passed.

Browser E2E includes:

- public registration and CEO approval;
- CEO, technical lead, employee and member role boundaries;
- reusable eight-account login and role verification;
- CEO operational-note editing for a VIP user;
- three VIP asset views with positive and negative returns;
- profile clearing, avatar upload/delete, CSRF rotation and multi-tab behavior;
- password change invalidating other devices;
- Browser Session denial from Live Write routes.

## Handoff state

The user-system code is complete for local integration. The branch remains isolated and is not authorized for GitHub merge into `main`.

Local handoff instructions:

- `docs/operations/USER_SYSTEM_LOCAL_INTEGRATION_HANDOFF.md`
- `docs/operations/USER_SYSTEM_DEMO_ACCOUNTS.md`

Current branch comparison at handoff preparation:

- ahead of `main`: 365 commits;
- behind `main`: 0 commits;
- merge base unchanged: `71603bcc6807284ef3a6da26ad3f43c541bc99c2`.

## Production-only follow-up

These items do not block local code integration, but remain mandatory before a real production cutover:

1. Confirm whether legacy Go/MySQL contains real users requiring migration.
2. Confirm the initial production member-holding source.
3. Confirm production remains same-origin `/api/v1`.
4. Validate HTTPS reverse proxy and `Secure; HttpOnly; SameSite=Lax` Cookie behavior on the target host.
5. Execute controlled-host Backup, Restore Drill, read-only restored startup and rollback rehearsal.

References:

- `docs/operations/USER_SYSTEM_BROWSER_ACCEPTANCE.md`
- `docs/operations/USER_SYSTEM_DEPLOYMENT_READINESS.md`

## Final rule

Do not merge this branch into `main` from the remote repository. The project owner will fetch and merge `feature/issue-117-user-system` into the updated local project and resolve any local conflicts there.
