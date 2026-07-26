# Task: Complete user system

Issue: #117
Status: active
Branch: `feature/issue-117-user-system`
Base commit: `71603bcc6807284ef3a6da26ad3f43c541bc99c2`

## Objective

Deliver one maintainable user-system boundary for browser registration/login, server-side sessions, business-role permissions, personal accounts, member fund holdings, backend user administration and auditable sensitive operations, without weakening the existing API-key, LiveTradingSession or execution-safety controls.

## Protected semantics

- Market, FOK, PostOnly and TP/SL execution semantics remain unchanged.
- Cross-venue spread pricing, quantity, lifecycle, compensation and reconciliation behavior remain unchanged.
- Platform Live Write and Runtime Live Write remain disabled by default and are not enabled by this work.
- Existing API-key authentication remains available for automation and Live operations.
- Live trading continues to require the existing production authentication, LiveTradingSession, Kill Switch, reconciliation and absolute-limit gates.
- Unknown external results remain unknown and never authorize blind retry.
- No real password, token, phone number, email address or customer holding data may be committed.

## Scope

Included outcomes:

- `platform-backend` becomes the authoritative owner of browser users, password authentication, server-side sessions, business roles, permission resolution, member holdings and user-system audit records.
- Existing API-key principals and the new browser-session principals resolve through one authenticated Principal boundary.
- Fixed phase-one business roles: CEO, technical lead, employee and member.
- Permission points control menus, routes, pages, fields, operations, APIs and data scope.
- Public registration supports member and employee applications only.
- Personal-account profile, avatar, password and session management.
- Backend user search, detail, approval, creation, update, role, status, password-reset and forced-session-revocation workflows.
- Member fund holding and fund NAV models with exact Decimal calculations.
- Additive schema migrations, initial CEO bootstrap, compatibility and rollback plans.
- Frontend navigation and page integration using existing layout and components.
- Direct backend, frontend, migration, security and repository verification.

Explicit non-goals for phase one:

- Social login, SMS login, email-code login or password recovery by email/SMS.
- Multi-tenant IAM, SSO or enterprise identity-provider integration.
- Visual role/permission editor or arbitrary per-user permission overrides.
- Fund subscription, redemption, payment, clearing or settlement.
- Independent object-storage service.
- Unrelated refactoring of trading, execution, Runtime, risk or data-service modules.
- Removal of legacy Go services in the same change unless a later approved implementation step proves removal is required and safe.

## Context

Read in addition to the standard startup context:

- `docs/technical/AUTH_RBAC_LIVE_SESSIONS.md`
- `docs/database/README.md`
- `docs/architecture/OWNERSHIP.md`
- `platform-backend/app/auth.py`
- `platform-backend/app/schema_migrations.py`
- `platform-backend/app/database_bootstrap.py`
- `platform-backend/app/database_seeds.py`
- `platform-backend/tests/test_auth_rbac.py`
- `admin-risk/src/api/sys/user.ts`
- `admin-risk/src/store/modules/user.ts`
- `admin-risk/src/store/modules/permission.ts`
- `admin-risk/src/router/routes/modules/risk.ts`
- `admin-risk/src/views/sys/login/`
- `admin-risk/src/views/sys/register/index.vue`
- `admin-risk/src/views/users/index.vue`
- `admin-risk/src/views/risk/profile/index.vue`

## Design decisions

- Browser users use server-side HttpOnly sessions; long-lived browser authentication tokens are not persisted in frontend storage.
- Public registration offers only member and employee applications. CEO and technical-lead accounts require an existing CEO.
- Technical leads cannot modify CEOs or other technical leads, cannot grant themselves greater authority, cannot view all member holdings by default and cannot execute real trades or modify core risk parameters by default.
- The existing API-key role set remains compatible and distinct from the four browser business roles.
- Authorization separates permission-point checks from target/data-scope checks.
- Member self-holding APIs derive the member identity from Principal and do not accept a user identifier.
- Financial values use Decimal in backend boundaries and canonical decimal strings in persistence/API contracts.
- Role, password and account-status changes invalidate existing sessions through an authorization-version boundary.

## Verification

Documentation phase:

```powershell
python scripts/check-documentation-consistency.py
python scripts/check-repository-structure.py
python scripts/check-version-consistency.py
```

Implementation phase backend:

```powershell
cd platform-backend
python -m ruff check app tests
python -m pyright
python -m pytest -m "architecture or unit or integration or live_safety"
```

Implementation phase frontend:

```powershell
cd admin-risk
pnpm exec eslint --max-warnings 0 <changed-files>
pnpm type:check
pnpm build
```

Final PR requirements:

- Repository Safety.
- Full Backend, Runtime and Frontend matrix because auth, migrations and shared authorization are Critical.
- Secret Scan.
- Version Consistency.
- No Live Write or execution-semantics regression.

## Stop conditions

- Stop if the proposed browser-session model would weaken existing API-key or Live authentication requirements.
- Stop if any implementation exposes passwords, raw session tokens, API keys or complete customer-sensitive fields in logs or responses.
- Stop if member data isolation depends only on frontend hiding or client-provided user identifiers.
- Stop if the migration requires editing an already-applied migration.
- Stop if user-system work requires changing Venue adapters, execution ordering, cross-spread calculations or Runtime write behavior.
- Stop if the last-active-CEO rule cannot be enforced transactionally.
- Stop if the initial CEO requires a committed default password.

## Acceptance criteria

- [ ] One authoritative identity, session and RBAC boundary is implemented in `platform-backend`.
- [ ] Browser-session and API-key principals coexist without weakening Live controls.
- [ ] CEO, technical lead, employee and member permission/data-scope matrices are enforced by backend tests.
- [ ] Public registration cannot create or request CEO/technical-lead authority.
- [ ] Users can manage allowed personal fields, avatar, password and sessions.
- [ ] Authorized administrators can search, inspect and manage users with protected-role rules.
- [ ] Last active CEO cannot be disabled or downgraded.
- [ ] Role, status and password changes invalidate old sessions.
- [ ] Members can read only their own fund holdings.
- [ ] Holding calculations use exact Decimal values and explicit unavailable/stale NAV semantics.
- [ ] Sensitive operations produce audit evidence without recording secret or customer-sensitive payloads.
- [ ] Additive migrations pass fresh, upgrade, repeat-startup and checksum-drift tests.
- [ ] Frontend menu, route, page, field and operation visibility derives from permission configuration.
- [ ] Full CI, Secret Scan and Version Consistency pass before squash merge.

## Risk and rollback

Risk: high

- Primary risks: authentication lockout, privilege escalation, horizontal member-data access, stale-session authority, last-CEO removal, migration failure and accidental weakening of Live safety.
- Detection: direct permission/data-scope tests, migration tests, session invalidation tests, protected-role transaction tests, frontend route tests and the existing live-safety suite.
- Rollback: before deployment, back up the Platform SQLite database and avatar data directory; revert the application release and restore the pre-migration database if rollback is required. Additive migrations should otherwise be forward-fixed rather than edited.

## Progress

- Done: Issue #117 created; latest `main` verified at `71603bcc6807284ef3a6da26ad3f43c541bc99c2`; no open PR found; confirmed design decisions recorded; Critical branch created.
- Current: complete the durable architecture, security, data, API, frontend, migration, testing and phased implementation plan.
- Next: review and approve the design documents, then begin implementation only after explicit approval.
- Blocked by: none.
