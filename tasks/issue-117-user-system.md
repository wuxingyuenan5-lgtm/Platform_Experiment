# Task: Complete user system and integrate Platform 0.9.1

Issue: #117  
Status: `validation`  
Branch: `feature/issue-117-platform-0-9-1`  
Base commit: `a4e22021c71cf5cd703cb0bc35676ff5adbfec36`

## Objective

Integrate the completed browser user system into the latest uploaded Platform `main` as version `0.9.1`, while preserving the hedge-fund dashboard, funding, cross-spread, Runtime and startup changes and without weakening API-key, LiveTradingSession or execution-safety controls.

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
- Latest uploaded Platform UI, strategy, Runtime and local-startup changes retained in the 0.9.1 branch.

## Protected semantics

- Platform Live Write and Runtime Live Write remain disabled by default.
- Existing Live Write routes remain API-key-only and retain Actor Binding, LiveTradingSession, Kill Switch, reconciliation and absolute-limit gates.
- API-key `admin` wildcard does not become human CEO authority.
- Passwords, raw Session/CSRF/reset tokens, API keys, full customer contacts and real holding data must not enter Git, logs or audit details.
- Applied migrations are immutable; later corrections use additive migrations.
- Social login, MFA, SSO, arbitrary per-user permission overrides, hard deletion, subscription/redemption/payment/settlement and browser Live trading remain explicit non-goals.

## Integration evidence

The branch is based on the latest uploaded `main` at `a4e22021c71cf5cd703cb0bc35676ff5adbfec36` and is versioned as `0.9.1`.

Integration repairs completed include:

- manual fusion of frontend package scripts, login UI, backend settings and startup documentation;
- frozen pnpm lockfile alignment;
- tracked frontend version and title declarations;
- Runtime Ruff and injected MT5 test platform handling;
- Python UTF-8 BOM normalization;
- repository/Codex context updates for the new main baseline;
- user-system E2E triggering for tracked environment changes.

## Required final acceptance

- Platform CI: Repository Safety, Platform Backend, Execution Runtime and Frontend Quality.
- User System Browser E2E including all eight reusable accounts.
- Secret Scan.
- Version Consistency.
- PR remains Draft and unmerged.

## Production-only follow-up

These items do not block code integration, but remain mandatory before a real production cutover:

1. Confirm whether legacy Go/MySQL contains real users requiring migration.
2. Confirm the initial production member-holding source.
3. Confirm production remains same-origin `/api/v1`.
4. Validate HTTPS reverse proxy and `Secure; HttpOnly; SameSite=Lax` Cookie behavior on the target host.
5. Execute controlled-host Backup, Restore Drill, read-only restored startup and rollback rehearsal.
6. Complete controlled Windows, Bybit and MT5 acceptance.

## References

- `docs/releases/0.9.1.md`
- `docs/operations/USER_SYSTEM_LOCAL_INTEGRATION_HANDOFF.md`
- `docs/operations/USER_SYSTEM_DEMO_ACCOUNTS.md`
- `docs/operations/USER_SYSTEM_BROWSER_ACCEPTANCE.md`
- `docs/operations/USER_SYSTEM_DEPLOYMENT_READINESS.md`

## Final rule

Do not merge this branch into GitHub `main`. The deliverable is `feature/issue-117-platform-0-9-1`, which may be fetched and used independently until the project owner explicitly authorizes a later merge.
