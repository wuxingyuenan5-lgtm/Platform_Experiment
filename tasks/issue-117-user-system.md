# Task: Complete user system

Issue: #117
Status: review
Branch: `feature/issue-117-user-system`
Base commit: `71603bcc6807284ef3a6da26ad3f43c541bc99c2`

## Objective

Deliver one maintainable `platform-backend` user-system boundary for browser registration/login, server-side Sessions, four fixed business roles, personal accounts, backend user administration, member fund holdings and auditable sensitive operations, without weakening API-key, LiveTradingSession or execution-safety controls.

## Protected semantics

- Market, FOK, PostOnly and TP/SL execution semantics remain unchanged.
- Cross-venue pricing, sizing, ordering, compensation and reconciliation remain unchanged.
- Platform Live Write and Runtime Live Write remain disabled by default.
- Current Live write routes remain API-key-only and retain Actor Binding, LiveTradingSession, Kill Switch, reconciliation and absolute-limit gates.
- API-key `admin` wildcard does not become human CEO authority.
- Unknown external results remain unknown and never authorize blind retry.
- Passwords, raw Session/CSRF/reset tokens, API keys, full customer contacts and real holding data must not enter Git, logs or audit details.
- Applied migrations are immutable; later corrections use additive migrations.

## Scope

Included outcomes:

- Human users, Argon2id passwords, opaque server-side Sessions and CSRF/Origin validation.
- Separate API-key and human-role namespaces resolved through one Principal boundary.
- Fixed roles: `ceo`, `tech_lead`, `employee`, `member`.
- Public member/employee registration, login, logout, reauthentication and one-time password-reset tickets.
- Personal profile, avatar, password and device/Session management.
- CEO/technical-lead user administration with target-role, field and data-scope policy.
- Transactional last-active-CEO guard, optimistic `row_version` and same-transaction audit.
- Member fund-holding and fund-unit-NAV customer-reporting read model using exact Decimal strings.
- Permission-driven frontend navigation, account, user-management and holding/NAV pages.
- Stable authentication/authorization error codes with Request ID correlation.
- Additive Migrations 5 and 6, initial CEO CLI and same-origin `/api/v1` development path.
- User-domain table counts and avatar files included in the existing fail-closed production backup/restore boundary.

Explicit non-goals:

- Social login, SMS/email-code login, SSO, MFA or enterprise identity providers.
- Arbitrary per-user permission overrides or visual permission editor.
- User hard deletion.
- Subscription, redemption, payment, settlement or formal accounting.
- Independent object storage.
- Browser authentication for real Live trading.
- Removal of legacy Go services.
- Unrelated Runtime, Venue, execution, strategy or risk refactoring.

## Context

Authoritative requirements and design:

- `docs/planning/USER_SYSTEM_REQUIREMENTS.md`
- `docs/technical/USER_SYSTEM_TECHNICAL_ARCHITECTURE.md`
- `docs/technical/USER_SYSTEM_AUTH_ERROR_CONTRACT.md`
- `docs/planning/USER_SYSTEM_EXECUTION_PLAN.md`
- `docs/planning/USER_SYSTEM_DESIGN_AND_IMPLEMENTATION_PLAN.md`
- `docs/technical/AUTH_RBAC_LIVE_SESSIONS.md`
- `docs/technical/MEMBER_HOLDINGS_READ_MODEL.md`
- `docs/database/README.md`
- `docs/architecture/OWNERSHIP.md`
- `docs/operations/USER_SYSTEM_BROWSER_ACCEPTANCE.md`
- `docs/operations/USER_SYSTEM_DEPLOYMENT_READINESS.md`

Primary implementation owners:

- `platform-backend/app/auth.py`
- `platform-backend/app/user_*.py`
- `platform-backend/app/member_holding_*.py`
- `platform-backend/app/schema_migrations.py`
- `platform-backend/app/disaster_recovery.py`
- `platform-backend/app/user_backup_archive.py`
- `platform-backend/tests/test_auth_*.py`
- `platform-backend/tests/test_user_*.py`
- `platform-backend/tests/test_member_holding_*.py`
- `platform-backend/tests/test_disaster_recovery.py`
- `admin-risk/src/api/platform/userSystem.ts`
- `admin-risk/src/api/platform/memberHoldings.ts`
- `admin-risk/src/access/`
- `admin-risk/src/store/modules/user.ts`
- `admin-risk/src/router/guard/permissionGuard.ts`
- `admin-risk/src/views/account/`
- `admin-risk/src/views/users/`
- `admin-risk/src/views/sys/login/`
- `admin-risk/src/views/sys/register/`
- `admin-risk/src/views/sys/reset-password/`
- `admin-risk/scripts/test-user-system-access.cjs`
- `admin-risk/tsconfig.user-system.json`

## Deployment decision gates

The code branch uses these safe defaults, but production cutover must stop if evidence conflicts:

1. Legacy users: default is no import; confirm whether old Go/MySQL contains real users.
2. Initial holdings: default is CEO `manual_admin`; confirm the production source.
3. Origin model: default is same-origin `/api/v1`; redesign Cookie/CORS/CSRF before any cross-origin deployment.

## Verification

Repository governance:

```powershell
python scripts/check-documentation-consistency.py
python scripts/check-repository-structure.py
python scripts/check-version-consistency.py
python scripts/scan-secrets.py
```

Backend:

```powershell
cd platform-backend
python -m pip install -e '.[dev]'
python -m pip check
python -m ruff check app tests
python -m pyright
python -m pytest -m architecture
python -m pytest -m unit
python -m pytest -m integration
python -m pytest -m live_safety
```

Frontend:

```powershell
cd admin-risk
pnpm install --frozen-lockfile
pnpm test:user-system
pnpm exec eslint --max-warnings 0 `
  "src/access/**/*.{ts,tsx}" `
  "src/api/platform/userSystem.ts" `
  "src/api/platform/memberHoldings.ts" `
  "src/router/guard/permissionGuard.ts" `
  "src/router/routes/modules/{account,dashboard,risk}.ts" `
  "src/store/modules/user.ts" `
  "src/utils/decimalDisplay.ts" `
  "src/views/account/index.vue" `
  "src/views/account/components/HoldingsPanel.vue" `
  "src/views/sys/login/**/*.{vue,ts,tsx}" `
  "src/views/sys/register/**/*.{vue,ts,tsx}" `
  "src/views/sys/reset-password/**/*.{vue,ts,tsx}" `
  "src/views/users/**/*.{vue,ts,tsx}"
pnpm type:check
pnpm exec vue-tsc -p tsconfig.user-system.json --noEmit --skipLibCheck
pnpm build
```

Final integration requires one linked Critical PR, Repository Safety, full Backend/Runtime/Frontend matrix, Secret Scan, Version Consistency and Squash Merge.

## Acceptance evidence required

- Session and API-key principals coexist without weakening Live controls.
- Customer identity routes are Session-only and reject API-key wildcard.
- Public registration cannot request CEO/technical-lead authority.
- Role, target, field and holding scopes pass backend tests.
- Last active CEO survives concurrent disable/downgrade attempts.
- Password/role/status changes invalidate old Sessions.
- Members can read only their own holdings.
- Holding calculations remain exact Decimal with explicit stale/unavailable NAV.
- Sensitive writes and denials produce audit evidence without raw secrets.
- Fresh, upgrade, repeat-startup and checksum-drift migration tests pass.
- Frontend menu, route and action visibility derive from one exact permission registry.
- Authentication failures use stable `detail.code/detail.message` and Request ID correlation.
- Frozen frontend install, type checks and production build pass.
- Production backup includes user-domain table counts and a safe avatar archive; restore drills reject unsafe entries and never modify active paths.
- Full CI, Secret Scan and Version Consistency pass before merge.

Automated acceptance evidence is confirmed by the latest clean-head Platform CI, Secret Scan and Version Consistency runs recorded in Draft PR #118. Manual browser acceptance, controlled-host backup/restore rehearsal and the three deployment decision gates remain required before review-ready status or production cutover.

## Progress

- Done:
  - Batches 1–6 implemented: identity/Session foundation, browser and personal account, administration/audit, member holdings/NAV, navigation/ownership convergence and stable authentication error contract.
  - Draft Critical PR #118 is linked to Issue #117 and remains unmerged.
  - Repository Safety passed: workstream, architecture/structure and documentation consistency.
  - Platform Backend passed dependency validation, Ruff, Pyright and all **399** classified tests after adding avatar backup/restore coverage.
  - Execution Runtime passed dependency validation, Ruff, Pyright and its full unit/integration/live-safety matrix; no Runtime or Venue behavior changed.
  - Frontend passed frozen install, **11** access/route/Decimal tests, focused ESLint, no-new-debt enforcement, strategy type check, user-system Vue type check and production build.
  - Version Consistency and full tracked-tree Secret Scan passed.
  - Authentication error contracts, target-scoped masking, Session/CSRF recovery, multipart avatar upload, explicit profile clearing and exact Decimal holding semantics are covered by executable evidence.
  - Existing production backup/restore includes user-domain table counts plus a fail-closed avatar archive and safe restore directory.
  - Browser acceptance and deployment/recovery runbooks define executable evidence fields without storing secrets.
  - Latest comparison remains behind `main` by **0**, with the original merge base unchanged.
- Current:
  - Status is `review`: automated verification is complete and the PR remains Draft.
  - The branch remains isolated from `main`; no merge or Live Write enablement is authorized.
- Next:
  - Execute `docs/operations/USER_SYSTEM_BROWSER_ACCEPTANCE.md` for all four roles.
  - Execute the controlled-host backup/restore and proxy/Cookie checks in `docs/operations/USER_SYSTEM_DEPLOYMENT_READINESS.md`.
  - Resolve the three deployment decision gates: legacy real-user migration, initial production holding source and same-origin production routing.
  - Re-run the latest-head checks after any further code or documentation change; use Squash Merge only after explicit approval.
- Blocked by:
  - This connector session has no interactive browser/deployment environment for manual acceptance, reverse-proxy/Cookie Secure validation or controlled-host backup/restore rehearsal.
  - No known product-code or automated-test blocker remains.
