# Task: Complete user system

Issue: #117
Status: active
Branch: `feature/issue-117-user-system`
Base commit: `71603bcc6807284ef3a6da26ad3f43c541bc99c2`

## Objective

Deliver one maintainable user-system boundary for browser registration/login, server-side sessions, business-role permissions, personal accounts, member fund holdings, backend user administration and auditable sensitive operations, without weakening existing API-key, LiveTradingSession or execution-safety controls.

## Protected semantics

- Market, FOK, PostOnly and TP/SL execution semantics remain unchanged.
- Cross-venue spread pricing, quantity, lifecycle, compensation and reconciliation remain unchanged.
- Platform Live Write and Runtime Live Write remain disabled by default.
- Existing API-key authentication remains authoritative for automation and current Live write routes.
- Live trading continues to require existing production authentication, LiveTradingSession, Kill Switch, reconciliation and absolute-limit gates.
- Unknown external results remain unknown and never authorize blind retry.
- No real password, token, phone number, email address or customer holding data may be committed.

## Scope

Included outcomes:

- `platform-backend` becomes the authoritative owner of browser users, passwords, server-side sessions, business roles, permission resolution, member holdings and user-system audit records.
- API-key and browser-session identities resolve through one Principal boundary with explicit authentication assurance classes.
- Customer identity, personal account, password-reset and holding-management APIs are human-session-only; API-key wildcard does not equal CEO.
- Fixed phase-one roles: CEO, technical lead, employee and member.
- Permission points plus target, field, data-scope and authentication-method policy control access.
- Public registration supports member and employee applications only.
- Personal profile, avatar, password and device/session management.
- Backend user search, detail, approval, creation, update, role, status, reset-ticket and forced-session-revocation workflows.
- Member holding and fund NAV read models with exact Decimal calculations.
- Additive migrations, initial CEO bootstrap, compatibility and rollback.
- Frontend permission-driven navigation and page integration using existing layout/components.
- Stable authentication/authorization error codes and Request ID correlation.
- Direct backend, frontend, migration, security and repository verification.

Explicit phase-one non-goals:

- Social login, SMS/email-code login or automated email/SMS password recovery.
- Multi-tenant IAM, SSO or enterprise identity-provider integration.
- Visual permission editor or arbitrary per-user permission overrides.
- User hard deletion.
- Fund subscription, redemption, payment, clearing or settlement.
- Independent object-storage service.
- Browser authentication redesign for real Live trading.
- Unrelated trading, execution, Runtime, risk or data-service refactoring.
- Removal of legacy Go services in this change.

## Independent branch operating mode

- This branch is an intentionally long-lived development line and is not expected to merge into `main` in the short term.
- Do not open a Pull Request until the user requests an integration/review checkpoint.
- Re-check divergence from `main` before each major batch; do not automatically merge unrelated `main` changes into security-sensitive work.
- Keep the branch runnable at coherent checkpoints and record unverified checks explicitly.
- The eventual integration path remains one linked Critical PR and Squash Merge; long-lived branch status does not relax repository or safety requirements.

## Context

Read in addition to standard startup context:

- `docs/planning/USER_SYSTEM_DESIGN_AND_IMPLEMENTATION_PLAN.md`
- `docs/planning/USER_SYSTEM_REQUIREMENTS.md`
- `docs/technical/USER_SYSTEM_TECHNICAL_ARCHITECTURE.md`
- `docs/technical/USER_SYSTEM_AUTH_ERROR_CONTRACT.md`
- `docs/planning/USER_SYSTEM_EXECUTION_PLAN.md`
- `docs/technical/AUTH_RBAC_LIVE_SESSIONS.md`
- `docs/technical/MEMBER_HOLDINGS_READ_MODEL.md`
- `docs/database/README.md`
- `docs/architecture/OWNERSHIP.md`
- `platform-backend/app/auth.py`
- `platform-backend/app/schema_migrations.py`
- `platform-backend/app/user_permissions.py`
- `platform-backend/app/user_security.py`
- `platform-backend/app/user_repository.py`
- `platform-backend/app/user_session_auth.py`
- `platform-backend/app/user_service.py`
- `platform-backend/app/user_routes.py`
- `platform-backend/app/user_avatar*.py`
- `platform-backend/app/user_admin_*.py`
- `platform-backend/app/member_holding_*.py`
- `platform-backend/tests/test_user_*.py`
- `platform-backend/tests/test_member_holding_*.py`
- `platform-backend/tests/test_password_reset_tickets.py`
- `platform-backend/tests/test_last_ceo_concurrency.py`
- `platform-backend/tests/test_auth_assurance.py`
- `admin-risk/src/api/platform/userSystem.ts`
- `admin-risk/src/api/platform/memberHoldings.ts`
- `admin-risk/src/store/modules/user.ts`
- `admin-risk/src/store/modules/permission.ts`
- `admin-risk/src/access/userAccess.ts`
- `admin-risk/src/access/routeAccess.ts`
- `admin-risk/src/router/routes/modules/risk.ts`
- `admin-risk/src/router/routes/modules/account.ts`
- `admin-risk/src/views/sys/login/`
- `admin-risk/src/views/sys/register/index.vue`
- `admin-risk/src/views/sys/reset-password/index.vue`
- `admin-risk/src/views/account/index.vue`
- `admin-risk/src/views/users/`
- `admin-risk/scripts/test-user-system-access.cjs`
- `admin-risk/tsconfig.user-system.json`

## Design decisions

- Browser users use same-origin server-side HttpOnly sessions; long-lived browser authentication tokens are not persisted.
- Public registration offers member and employee applications only. CEO and technical-lead accounts require an existing CEO.
- Customer identity APIs reject API-key principals even when the API-key role has wildcard permission.
- Current Live write routes remain API-key-only; browser Live authentication is a separate future Critical decision.
- Technical leads cannot modify CEOs or other technical leads, cannot grant themselves greater authority, cannot view all member holdings by default and cannot execute real trades or modify core risk parameters by default.
- Technical-lead list DTOs are masked; ordinary employee/member details may be complete, while CEO/peer technical-lead details remain masked.
- Authorization separates authentication assurance, permission points, target-role policy, field policy and data scope.
- Member self-holding APIs derive identity from Principal and accept no user identifier.
- Financial values use Decimal and canonical decimal strings.
- Role, password and lifecycle-state changes invalidate existing sessions through `auth_version`.
- Temporary login lock uses `locked_until`, not a lifecycle `locked` status.
- Administrator password reset uses a one-time short-lived reset ticket; administrators do not set or view temporary passwords.
- Backend returns permissions, not a menu tree; frontend menus and routes derive from one local permission registry.
- Human CEO permissions are explicit business permissions, not `*`; API-key `admin` remains the only wildcard role.
- Critical mutable rows use optimistic `row_version` checks.
- Employee approval/role assignment requires a non-empty department; member approval/role assignment requires a non-empty member type.
- Member holdings are a customer-reporting read model, not formal accounting or subscription/redemption truth.
- Browser holding/NAV writes accept only `manual_admin`; migration and external-import sources require future dedicated importers.
- Browser CSRF remains memory-only and uses same-origin `BroadcastChannel` for multi-tab rotation synchronization.
- Cookie-valid/CSRF-memory-missing navigation attempts `/auth/me` rehydration before requiring login.
- Authentication and authorization failures use stable `detail.code/detail.message`, Request ID correlation and unchanged status-code semantics.
- Phase one provides no user DELETE workflow.

## Deployment decision gates

- Legacy user migration: use the safe branch default of no import while building the new isolated database boundary. Stop before login cutover if evidence shows real users must migrate.
- Initial holding source: use the safe branch default `manual_admin`; stop before production data import if another source is required.
- Deployment origin: develop and test for same-origin `/api/v1`; stop before production deployment if cross-origin is required.

Do not silently assume a conflicting answer. Stop the affected deployment cutover if evidence differs from the safe default.

## Verification

Documentation and repository governance:

```powershell
python scripts/check-documentation-consistency.py
python scripts/check-repository-structure.py
python scripts/check-version-consistency.py
python scripts/scan-secrets.py
```

Implementation backend:

```powershell
cd platform-backend
python -m ruff check app tests
python -m pyright
python -m pytest -m architecture
python -m pytest -m unit
python -m pytest -m integration
python -m pytest -m live_safety
```

Implementation frontend:

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
  "src/views/account/**/*.{vue,ts,tsx}" `
  "src/views/sys/login/**/*.{vue,ts,tsx}" `
  "src/views/sys/register/**/*.{vue,ts,tsx}" `
  "src/views/sys/reset-password/**/*.{vue,ts,tsx}" `
  "src/views/users/**/*.{vue,ts,tsx}"
pnpm type:check
pnpm exec vue-tsc -p tsconfig.user-system.json --noEmit --skipLibCheck
pnpm build
```

Final PR:

- Repository Safety.
- Full Backend, Runtime and Frontend matrix.
- Secret Scan.
- Version Consistency.
- No Live Write or execution-semantics regression.

No complete repository command set above has been executed in the connector-only environment. The isolated same-content Node access-policy runner completed six assertions with zero failures; this is only runner evidence and is not a substitute for a real checkout or PR CI.

## Stop conditions

- Browser Session would weaken existing API-key or Live authentication requirements.
- API-key wildcard must manage human/customer identity for the system to work.
- Passwords, raw Session/CSRF/reset tokens, API keys or complete customer-sensitive fields would enter logs/responses/Git.
- Member isolation depends on frontend hiding or client-provided user identifiers.
- An applied migration must be edited.
- Venue adapters, execution ordering, spread calculations or Runtime write behavior must change.
- Last active CEO cannot be enforced transactionally.
- Initial CEO requires a committed default password.
- Legacy real-user state is unknown when migration/login cutover begins.
- Production becomes cross-origin without renewed Cookie/CORS/CSRF design.

## Acceptance criteria

- [ ] One authoritative identity, Session and RBAC boundary is implemented in `platform-backend`.
- [ ] Session and API-key principals coexist without weakening Live controls.
- [ ] Customer identity routes are Session-only and reject API-key wildcard.
- [ ] CEO, technical lead, employee and member permission/data-scope matrices are enforced by backend tests.
- [ ] Public registration cannot create or request CEO/technical-lead authority.
- [ ] Users can manage allowed profile fields, avatar, password and sessions.
- [ ] Administrators reset passwords through one-time tickets, not visible temporary passwords.
- [ ] Authorized administrators can search, inspect and manage users with protected-role rules.
- [ ] Last active CEO cannot be disabled or downgraded, including concurrent requests.
- [ ] Role, lifecycle status and password changes invalidate old sessions.
- [ ] Members can read only their own holdings.
- [ ] Holding calculations use exact Decimal and explicit unavailable/stale NAV semantics.
- [ ] Sensitive operations produce audit evidence without secret/customer payloads.
- [ ] Additive migrations pass fresh, upgrade, repeat-startup and checksum-drift tests.
- [ ] Frontend menu, route, field and action visibility derives from one permission registry.
- [ ] Authentication and authorization errors use stable codes and Request ID correlation.
- [ ] User-system local run no longer depends on legacy auth port 8080.
- [ ] Full CI, Secret Scan and Version Consistency pass before squash merge.

Acceptance boxes remain unchecked until the required executable evidence exists, even where implementation and direct tests have already been written.

## Risk and rollback

Risk: high

- Primary risks: authentication lockout, privilege escalation, API-key/human-domain confusion, horizontal member-data access, stale-session authority, last-CEO removal, reset-ticket leakage, migration failure and accidental Live-safety weakening.
- Detection: assurance-class tests, structured-error tests, target/data-scope tests, migration tests, session invalidation tests, reset-ticket tests, protected-role concurrency tests, frontend route tests and existing live-safety suite.
- Rollback: back up Platform SQLite, avatar directory and proxy configuration before deployment; revert application and restore pre-migration data when required. Applied additive migrations are forward-fixed unless restoring the complete pre-migration backup.

## Batch 1 checkpoint — identity and Session foundation

Implemented:

- separated API-key and human-role permission namespaces;
- Migration 5 for users, Sessions, password-reset tickets and audit query fields;
- Argon2id password policy and high-entropy secret hashing;
- Session absolute/idle expiry, bounded devices, `auth_version` invalidation and revocation;
- CSRF plus trusted-Origin validation for Cookie writes;
- request assurance classes and Cookie/Bearer ambiguity rejection;
- no-default-password initial CEO command and transactional last-active-CEO guard;
- direct migration, permission, security, Session and assurance tests.

Verification status: implementation and tests are committed; repository Ruff, Pyright, classified Pytest and CI remain unrun.

## Batch 2 checkpoint — browser and personal account

Implemented:

- public member/employee registration with pending lifecycle;
- login failure counting, temporary lock, login audit and opaque Session Cookie;
- `/auth/me` hydration with CSRF rotation, logout and recent reauthentication;
- self profile, optimistic versioning, password change and Session/device management;
- avatar byte/decode/pixel validation, WebP re-encoding and data-directory storage;
- one-time reset-ticket consumption and public reset page;
- bounded application-level rate limiting for public auth endpoints;
- frontend Cookie Session state, in-memory CSRF, login/register/reset and personal-account pages;
- direct browser-flow, reset, logout, rate-limit and avatar tests.

Verification status: implementation and tests are committed; frontend lint/type/build and backend suites remain unrun.

## Batch 3 checkpoint — administration and audit

Implemented:

- server-side paginated search, role/status filtering and deterministic sorting;
- CEO complete DTOs, technical-lead target-scoped DTOs and employee server-side masked DTOs;
- user detail, create, edit, approve, reject, role, status, reset-ticket and Session-revoke APIs;
- target-role policy, self-mutation rejection, recent reauthentication and last-CEO transaction guard;
- one-time reset ticket returned once; random bootstrap password is never shown or known;
- sensitive writes and audit records share one database transaction;
- employee/member role-profile requirements are rechecked before approval and role changes;
- direct tests for creation/reset, employee masking, protected target fields and writes, role-profile requirements, row-version conflicts, last-CEO concurrency and audit rollback;
- frontend user table, filters, pagination, create flow, detail drawer, dangerous confirmations, reset-ticket one-time display and audit view;
- user-management route restored for internal roles and tagged with `user.read` permission metadata.

Verification status: implementation and tests are committed; backend and frontend executable checks remain unrun.

## Batch 4 checkpoint — member holdings and fund NAV

Implemented:

- additive Migration 6 with nullable `funds.fund_code`, member holdings and unit-NAV snapshots;
- exact Decimal parsing, canonical strings and derived market value/return calculations;
- explicit available, stale and unavailable NAV semantics; missing NAV never becomes zero;
- member self endpoint derives identity from Principal and accepts no user ID;
- CEO-only all-member holding read/update and fund NAV maintenance;
- technical lead and API-key wildcard cannot access customer holding administration;
- optimistic holding versioning, recent reauthentication and same-transaction audit;
- browser write DTOs accept only `manual_admin`; database source enum remains future-compatible;
- personal holding cards and CEO holding/NAV editor use shared string-only Decimal display;
- direct migration, Decimal, assurance, scope, architecture, audit-rollback and source-contract tests.

Verification status: implementation and tests are committed; backend and frontend executable checks remain unrun.

## Batch 5 checkpoint — navigation and ownership convergence

Implemented:

- canonical user pages use same-origin `/api/v1` Cookie Session clients and no longer depend on legacy `/api/auth` JWT state;
- dynamic route construction is centralized in the permission guard;
- menu trees and direct URL navigation both apply `meta.permissions` through one exact-match policy;
- API-key-style `*` is not recognized as a browser route permission;
- CEO receives an explicit business permission set rather than browser wildcard authority;
- canonical personal-account route is tagged with `profile.read_self`;
- Cookie-valid/CSRF-memory-missing state attempts `/auth/me` rehydration;
- CSRF rotation synchronizes across same-origin tabs with memory-only `BroadcastChannel`;
- avatar multipart upload preserves the browser-generated boundary;
- profile PATCH preserves omitted fields and supports explicit clear semantics;
- static ownership tests prevent legacy auth imports, browser token persistence and floating-point holding calculations;
- ownership, database, holding and design documents are synchronized.

Verification status: implementation and tests are committed; frontend executable checks remain unrun.

## Batch 6 checkpoint — authentication contract and verification preparation

Implemented:

- Browser Session errors carry explicit stable codes instead of message-derived semantics;
- authentication middleware returns structured `detail.code/detail.message` plus `requestId`;
- permission dependencies use the same structured error shape;
- authentication denial audit records the stable error code without raw credentials;
- Live-safety assurance tests assert error codes, messages, status and Request ID correlation;
- dedicated authentication error-contract documentation is authoritative for client handling;
- dependency-free Node 20 user-access tests replace unavailable Vitest files;
- `tsconfig.user-system.json` covers user Store, routes, account, administration and holdings pages;
- Platform CI runs focused user-system tests, ESLint, type checking and build.

Verification status: code, tests and CI definitions are committed; Ruff, Pyright, classified Pytest, frozen pnpm checks, documentation checks, Secret Scan and PR CI remain unrun.

## Remaining before an integration checkpoint

- run documentation consistency, repository structure and version checks;
- run Ruff, Pyright and all classified backend tests;
- run frozen pnpm install, user-system access tests, focused ESLint, both frontend type checks and build;
- run Secret Scan against the full tracked tree;
- resolve executable findings without weakening protected semantics;
- perform manual browser acceptance for registration, login, profile clear, avatar upload, multi-tab CSRF, role navigation and holdings/NAV;
- confirm legacy-user migration, same-origin production routing and initial holding-source evidence before deployment cutover;
- refresh `main` divergence and requested PR/CI state;
- only after the user requests integration review, open one linked Critical PR.

## Progress

- Done in code: design baseline; Batches 1–6 identity, personal account, administration, holdings, navigation and authentication-contract implementation.
- Current: executable-verification preparation and targeted static review. Branch work remains isolated; no Pull Request exists by design.
- Next: obtain a real checkout or requested PR CI, run the complete matrix and fix only evidence-backed findings.
- Blocked by: connector-only environment cannot execute the repository dependency and test matrix. No product/design blocker is currently known.
