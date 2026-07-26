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
- `docs/planning/USER_SYSTEM_EXECUTION_PLAN.md`
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

- Browser users use same-origin server-side HttpOnly sessions; long-lived browser authentication tokens are not persisted.
- Public registration offers member and employee applications only. CEO and technical-lead accounts require an existing CEO.
- Customer identity APIs reject API-key principals even when the API-key role has wildcard permission.
- Current Live write routes remain API-key-only; browser Live authentication is a separate future Critical decision.
- Technical leads cannot modify CEOs or other technical leads, cannot grant themselves greater authority, cannot view all member holdings by default and cannot execute real trades or modify core risk parameters by default.
- Authorization separates authentication assurance, permission points, target-role policy, field policy and data scope.
- Member self-holding APIs derive identity from Principal and accept no user identifier.
- Financial values use Decimal and canonical decimal strings.
- Role, password and lifecycle-state changes invalidate existing sessions through `auth_version`.
- Temporary login lock uses `locked_until`, not a lifecycle `locked` status.
- Administrator password reset uses a one-time short-lived reset ticket; administrators do not set or view temporary passwords.
- Backend returns permissions, not a menu tree; frontend menus and routes derive from one local permission registry.
- Critical mutable rows use optimistic `row_version` checks.
- Member holdings are a customer-reporting read model, not formal accounting or subscription/redemption truth.
- Phase one provides no user DELETE workflow.

## Decision gates before implementation

- Legacy user migration: use the safe branch default of no import while building the new isolated database boundary. Stop before login cutover if evidence shows real users must migrate.
- Initial holding source: use the safe branch default `manual_admin`; stop before production data import if another source is required.
- Deployment origin: develop and test for same-origin `/api/v1`; stop before production deployment if cross-origin is required.

Do not silently assume a conflicting answer. Stop the affected batch if evidence differs from the safe default.

## Verification

Documentation phase:

```powershell
python scripts/check-documentation-consistency.py
python scripts/check-repository-structure.py
python scripts/check-version-consistency.py
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
pnpm exec eslint --max-warnings 0 <changed-files>
pnpm type:check
pnpm build
```

Final PR:

- Repository Safety.
- Full Backend, Runtime and Frontend matrix.
- Secret Scan.
- Version Consistency.
- No Live Write or execution-semantics regression.

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
- [ ] User-system local run no longer depends on legacy auth port 8080.
- [ ] Full CI, Secret Scan and Version Consistency pass before squash merge.

## Risk and rollback

Risk: high

- Primary risks: authentication lockout, privilege escalation, API-key/human-domain confusion, horizontal member-data access, stale-session authority, last-CEO removal, reset-ticket leakage, migration failure and accidental Live-safety weakening.
- Detection: assurance-class tests, target/data-scope tests, migration tests, session invalidation tests, reset-ticket tests, protected-role concurrency tests, frontend route tests and existing live-safety suite.
- Rollback: back up Platform SQLite, avatar directory and proxy configuration before deployment; revert application and restore pre-migration data when required. Applied additive migrations are forward-fixed unless restoring the complete pre-migration backup.

## Progress

- Done: Issue #117 and Critical branch created; requirements, architecture and execution plan self-reviewed; user role permissions moved to one resolver; existing API-Key roles preserved; Principal permission checks use the shared resolver; Migration 5 adds users, sessions, reset tickets and queryable audit fields; direct permission and migration tests added.
- Current: Batch 1 identity/session foundation. Business routes and frontend are not connected yet.
- Next: implement the user/session repository, Argon2id password boundary, Session/CSRF authentication assurance and initial CEO bootstrap; then run the direct Backend checks in an environment with repository execution access.
- Blocked by: this connector environment cannot resolve `github.com` for a local clone, and branch-only pushes do not trigger the repository's PR validation workflows. No design blocker is known.
