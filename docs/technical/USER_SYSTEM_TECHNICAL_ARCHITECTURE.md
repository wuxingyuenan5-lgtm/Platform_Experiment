# User System Technical Architecture

> Version: 0.9.0  
> Issue: #117  
> Workstream: Critical  
> Status: implementation baseline; executable verification pending

## 1. Purpose

This document defines the authoritative implementation architecture for the browser user system. Product behavior and acceptance criteria are owned by `docs/planning/USER_SYSTEM_REQUIREMENTS.md`; sequencing and validation are owned by `docs/planning/USER_SYSTEM_EXECUTION_PLAN.md`.

The design introduces human browser identities without weakening the existing API-key, LiveTradingSession, Kill Switch, reconciliation, Runtime or Venue safety boundaries.

## 2. Architectural outcome

```text
Browser
  ├─ public registration/login/reset-ticket consumption
  └─ same-origin HttpOnly Cookie Session
          ↓
Platform Backend /api/v1
  ├─ authentication assurance classifier
  ├─ unified Principal
  ├─ explicit human permission registry
  ├─ target/field/data-scope policy
  ├─ user/session repositories
  ├─ user administration service
  ├─ member holding customer-reporting read model
  └─ transactional audit

Automation / operations
  └─ Bearer API Key
          ↓
Platform Backend existing platform/live routes
          ↓
LiveTradingSession + Kill Switch + reconciliation + limits
          ↓
Execution Runtime
          ↓
Venue
```

Browser Sessions and API Keys share a Principal shape, but they do not share credential semantics or automatic authority. Authentication assurance is evaluated before permission points.

## 3. Authority boundaries

### 3.1 Platform Backend

The Platform Backend owns:

- browser users and lifecycle;
- password hashes and password policy;
- opaque browser Sessions and CSRF state;
- fixed business roles and explicit permission resolution;
- self-profile, avatar, password and device workflows;
- user administration and target-role policy;
- member fund holding customer-reporting records;
- fund unit-NAV reporting snapshots;
- user-system audit records and mutation transactions.

It must not own:

- raw browser passwords beyond request verification;
- raw Session, CSRF or reset tokens at rest;
- API-key secret values;
- formal fund accounting, subscription/redemption or settlement;
- Venue SDKs or external order execution;
- browser authorization of Live Write in phase one.

### 3.2 Frontend

The frontend owns:

- login, registration, reset-ticket, personal-account and user-management interaction;
- one local permission-aware route/menu registry;
- in-memory CSRF state;
- exact string-based Decimal presentation;
- field/action visibility for usability.

Frontend visibility is never authoritative authorization. Every protected action is independently enforced by the backend.

### 3.3 Member holdings

Member holdings are a customer-reporting read model. They are not:

- a formal ledger;
- subscription/redemption truth;
- payment or settlement truth;
- a strategy NAV replacement;
- a trading-account balance;
- a Position, PnL or FinancialFact projection;
- a risk-limit or execution input.

## 4. Authentication assurance classes

Every route is assigned one assurance class:

| Class | Allowed authentication | Examples |
|---|---|---|
| `public` | none | health, registration, login, reset-ticket consumption |
| `human_session` | browser Session only | `/auth/me`, `/auth/logout`, `/auth/reauth`, `/me/**`, `/users/**` |
| `platform_read` | browser Session or API Key; explicit Development Identity in non-live | ordinary platform reads |
| `simulation_write` | browser Session or API Key; explicit Development Identity in non-live | non-live simulation writes subject to permission and domain checks |
| `live_write` | API Key only | real trading, core risk and LiveTradingSession writes |

Rules:

1. assurance is evaluated before permission resolution;
2. Cookie plus Bearer in one request is rejected as ambiguous;
3. API-key wildcard cannot enter `human_session` routes;
4. Browser Session cannot enter `live_write` routes;
5. unknown or unclassified routes fail closed;
6. existing Live safety gates remain mandatory after authentication.

## 5. Principal

```python
Principal(
    user_id: str,
    roles: tuple[str, ...],
    auth_method: Literal["session", "api_key", "development"],
    session_id: str | None,
    credential_id: str | None,
)
```

Constraints:

- Session Principals contain exactly one fixed human role;
- API-Key/Development Principals use the existing API-key role namespace;
- a Session Principal has `session_id` and no `credential_id`;
- an API-Key Principal has `credential_id` and no browser Session authority;
- actor identity is derived from Principal, not trusted from request bodies.

## 6. Role namespaces and permission resolution

### 6.1 API-key roles

```text
viewer
researcher
trader
risk_officer
operations
admin
```

Existing semantics remain compatible. API-key `admin` retains `*` wildcard compatibility for API-key permission resolution.

### 6.2 Human roles

```text
ceo
tech_lead
employee
member
```

Human roles are stored in `users.role_code` and are invalid in API-key configuration.

The CEO is the highest business role, but is not a wildcard identity. The server returns an explicit CEO permission set covering business reads, user administration, self account management and all-member holding administration. It does not include `trade:submit`, `risk:manage`, LiveTradingSession applicant/approver permissions or any other API-key-only Live Write authority.

Technical-lead defaults:

- may manage employee/member users;
- may not manage CEO or peer technical leads;
- may not grant CEO/technical-lead authority;
- may not view all member holdings by default;
- may not update member holdings or NAV;
- may not submit real trades or change core risk controls.

Employee defaults:

- internal platform/risk/trade reads where explicitly routed;
- masked user directory read;
- self-profile/session management;
- no user mutations;
- no all-member holdings.

Member defaults:

- self-profile/session management;
- own holdings only;
- no internal platform or user-directory access.

### 6.3 Permission naming

Existing automation/platform permissions retain colon names, for example:

```text
platform:read
trade:submit
risk:manage
```

Human user-domain permissions use explicit dot names, for example:

```text
profile.read_self
profile.update_self
session.read_self
user.read
user.update
user.assign_role
member.holding.read_self
member.holding.read_all
member.holding.update
```

The frontend performs exact permission matching. It never interprets `*` as browser authority.

## 7. Authorization pipeline

```text
authentication assurance
→ permission point
→ target-role policy
→ field policy
→ data scope
→ recent reauthentication
→ domain invariant
```

### 7.1 Target-role policy

- CEO may manage other users subject to last-CEO and self-mutation rules;
- technical lead may manage employee/member targets only;
- technical lead cannot operate on CEO or technical-lead targets;
- self administrator mutation is rejected; personal changes use `/me/**`;
- role assignment is checked separately from target management.

### 7.2 Role-profile invariants

- employee approval or role assignment requires non-empty `department`;
- member approval or role assignment requires non-empty `member_type`;
- permission and target policy execute before these field errors are exposed;
- `expectedVersion` ensures a concurrent profile change causes 409 rather than applying a role against stale data.

### 7.3 Data scope

- `/me/**` derives the current user from Principal and accepts no target user ID;
- `/me/holdings` derives the member identity from Principal;
- all-member holding routes require `member.holding.read_all` or `member.holding.update`;
- technical lead has neither permission by default;
- API-key wildcard is rejected by the `human_session` assurance boundary.

## 8. Browser Session design

### 8.1 Token and Cookie

- generate at least 256 bits of cryptographic entropy;
- send the raw token only in the `vg_session` Cookie;
- store SHA-256 of the token in SQLite;
- Cookie is HttpOnly, SameSite=Lax, Path=/ and Secure in production;
- use host-only Cookie scope;
- require same-origin `/api/v1` deployment.

### 8.2 Defaults

```text
absolute TTL          12 hours
idle TTL              30 minutes
recent reauth         10 minutes
max active sessions   5
last-seen DB throttle  5 minutes
```

### 8.3 Validation

Each request validates:

1. token hash exists;
2. Session is not revoked;
3. user is active;
4. temporary login lock is not active;
5. Session `auth_version` equals user `auth_version`;
6. absolute expiry has not passed;
7. idle expiry has not passed.

Role, password and lifecycle changes increment `auth_version` and/or explicitly revoke Sessions.

### 8.4 CSRF and Origin

Unsafe Session-authenticated requests require:

```text
X-CSRF-Token + trusted Origin
```

The database stores only the CSRF hash. Login and `/auth/me` return the raw CSRF value to browser memory. It is not persisted in localStorage, sessionStorage or persisted Pinia state. Frontend user/holding clients clear the in-memory value on logout, reset and 401 Session expiry.

## 9. Password and recovery

- Argon2id hashes are authoritative;
- password policy is enforced server-side;
- login failures increment bounded lock state;
- lifecycle status and temporary lock are separate;
- administrators never set or see a temporary password;
- reset tickets are cryptographically random, hash-only at rest, short-lived and single-use;
- ticket issuance revokes previous active tickets, invalidates Sessions and increments authority version as designed;
- initial CEO is created via an interactive CLI using `getpass`;
- no default CEO password is committed.

## 10. User lifecycle

```text
pending → active ↔ disabled
   └────→ rejected
```

Temporary security lock is represented by:

```text
failed_login_count
locked_until
```

There is no lifecycle `locked` state and no phase-one hard-delete endpoint.

## 11. Persistence and migrations

### Migration 5

Additive identity/security migration:

- `users`;
- `user_sessions`;
- `password_reset_tickets`;
- nullable audit query fields and indexes.

### Migration 6

Additive customer-reporting migration:

- nullable `funds.fund_code` plus partial unique index;
- `member_fund_holdings`;
- `fund_nav_snapshots`;
- holding and NAV lookup indexes.

Migrations 1–6 are immutable after application. No Migration 7 is required for role-profile fields: existing service authorization order plus optimistic `row_version` provides the phase-one invariant without editing the database ledger.

## 12. Member holding Decimal contract

- database and API financial boundaries use canonical plain Decimal strings;
- exponent notation, NaN, Infinity, separators and invalid signs are rejected;
- backend uses Decimal for calculations;
- frontend formats strings without converting business truth to JavaScript `number`;
- missing NAV produces nullable derived values, never zero;
- stale NAV is explicit;
- NAV currency must match the fund base currency;
- browser writes may declare only `manual_admin`;
- `migration` and `external_import` remain database-compatible sources for future dedicated importers.

## 13. Audit and transaction rules

Sensitive successful mutations and their AuditEvent are committed in the same transaction. Audit failure rolls back the mutation.

Audited examples:

- account creation/approval/rejection;
- role and status changes;
- reset-ticket issuance;
- Session revocation;
- member holding update;
- fund NAV update;
- viewing another member's holdings.

Audit details must not contain passwords, raw tokens, full contact data, avatar bytes or complete holding payloads.

## 14. Frontend integration

Authoritative clients:

```text
admin-risk/src/api/platform/userSystem.ts
admin-risk/src/api/platform/memberHoldings.ts
```

Access policy:

```text
admin-risk/src/access/userAccess.ts
admin-risk/src/access/routeAccess.ts
```

Rules:

- same-origin `/api/v1`;
- Cookie managed by browser;
- CSRF kept in module memory;
- one permission-aware route/menu registry;
- dynamic route construction centralized in the route guard;
- menus and direct URL navigation use the same exact permission checks;
- canonical personal account is `/account/index`;
- legacy `/risk/profile` is a hidden redirect;
- canonical user pages do not import the legacy `/api/auth` JWT client;
- no long-lived authentication token is written to browser storage.

## 15. Live safety preservation

Browser identity work does not alter:

- Market, FOK, PostOnly or TP/SL semantics;
- TradeCommand or ExecutionBatch submission;
- LiveTradingSession application, approval or claim;
- Kill Switch or absolute limits;
- reconciliation/EOD gates;
- Runtime gateway behavior;
- Venue adapters;
- unknown-result handling.

A Browser Session CEO cannot act as the API-Key Live applicant, approver or submitter.

## 16. Implementation status

Implemented on `feature/issue-117-user-system`:

- Batches 1–5 identity, Session, account, administration, holding and frontend convergence code;
- Migration 5 and 6;
- direct backend/frontend tests for security, scope, Decimal, audit and route policy;
- synchronized task packet and supporting technical/database/ownership documents.

Verification still pending:

- Ruff and Pyright;
- architecture, unit, integration and live-safety Pytest groups;
- frontend ESLint, type check, unit tests and build;
- documentation consistency, repository structure and version consistency;
- Secret Scan and full PR CI;
- production same-origin proxy, Secure Cookie, backup/restore and deployment acceptance.

No executable check is considered passed until it has run successfully in a real checkout or requested PR CI. No code completion or CI result enables Platform or Runtime Live Write.
