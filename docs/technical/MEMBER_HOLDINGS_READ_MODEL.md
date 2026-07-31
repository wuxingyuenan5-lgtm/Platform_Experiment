# Member Holdings and Fund Unit NAV Read Model

Status: implementation checkpoint on `feature/issue-117-user-system`
Issue: #117
Owner: `platform-api` user system
Requirements: `USR-HOLD-*`, `USR-AUD-*`

## 1. Purpose and authority

This module provides a customer-reporting view of a member's fund units and the latest available fund unit NAV.

It is not:

- a trading-account balance;
- a subscription, redemption, payment, clearing or settlement ledger;
- a formal accounting source;
- a replacement for `financial_facts`, formal Position/PnL/NAV projections or Strategy NAV;
- an input to Venue execution, Runtime routing, LiveTradingSession or risk limits.

The first implementation source is `manual_admin`. Future migration or external-import sources require their own evidence and validation; the schema permits them but no importer is enabled by this change.

## 2. Ownership boundaries

| Boundary | Authoritative owner | Responsibility | Must not own |
|---|---|---|---|
| Decimal policy | `platform-api/app/member_holding_decimal.py` | Strict plain-decimal parsing, canonical output and exact derived calculations | SQL, HTTP or float conversion |
| Persistence | `platform-api/app/member_holding_repository.py` | Fund lookup, holding optimistic upsert, latest available NAV and NAV supersession | Permission, audit policy or presentation |
| Service | `platform-api/app/member_holding_service.py` | Member target checks, exact calculation, stale/unavailable semantics, recent reauthentication and transactional audit | Formal accounting or Venue data |
| Public DTOs | `platform-api/app/member_holding_schemas.py` | Holding, fund and NAV request/response contracts | Calculation or persistence |
| Routes | `platform-api/app/member_holding_routes.py` | Session-only routing and permission dependencies | Identity supplied by the client for self reads |
| Frontend API | `platform-web/src/api/platform/memberHoldings.ts` | Cookie Session transport and in-memory CSRF propagation | Financial calculation |
| Decimal display | `platform-web/src/utils/decimalDisplay.ts` | Pure string grouping, signed display and ratio-to-percent shift | JavaScript `number` financial authority |

## 3. Migration 6

Migration 6 is named:

```text
member-fund-holdings-and-unit-nav
```

It is additive and does not edit migrations 1–5.

### 3.1 `funds.fund_code`

```sql
fund_code TEXT NULL
```

A partial unique index applies only when a code is present. Existing fund rows remain valid with `NULL` code and existing Seed identifiers are unchanged.

### 3.2 `member_fund_holdings`

One row represents one member/fund customer-reporting holding.

Key fields:

- `member_user_id` — approved human user whose business role is `member`;
- `fund_id` — existing Platform fund master identifier;
- `share_quantity` — canonical non-negative Decimal string;
- `cumulative_invested` — canonical non-negative Decimal string in the fund base currency;
- `confirmed_at` — optional share-confirmation time;
- `as_of` — mandatory source data time;
- `source` — `manual_admin`, `migration` or `external_import`;
- `status` — `active` or `closed`;
- `row_version` — optimistic concurrency version;
- `updated_by` — authenticated human administrator.

`UNIQUE(member_user_id, fund_id)` prevents parallel rows for the same member and fund.

### 3.3 `fund_nav_snapshots`

One row is one unit-NAV observation.

Key fields:

- `fund_id`;
- `valuation_time`;
- `unit_nav` as canonical non-negative Decimal string;
- `currency`, which must equal the fund base currency at service admission;
- `source`;
- `status` — `available`, `superseded` or `invalid`.

A new successful NAV update changes prior `available` rows for that fund to `superseded` and inserts one new `available` row in the same transaction. Historical rows remain queryable evidence.

## 4. Decimal contract

Financial values must be plain decimal strings:

```text
0
1250
1250.50
0.00000001
```

Rejected examples include:

```text
-1
+1
.5
1.
00.5
1e-8
NaN
Infinity
1,000
```

The current boundary allows at most 24 integer digits and 18 fractional digits. All calculations use Python `Decimal` with an explicit high-precision local context.

For one holding:

```text
marketValue      = shareQuantity × latestUnitNav
cumulativeReturn = marketValue − cumulativeInvested
returnRate       = cumulativeReturn ÷ cumulativeInvested
```

When `cumulativeInvested = 0`, `returnRate` is `null`, not infinity and not zero.

The API returns canonical strings and never returns JSON floating-point numbers for these fields. The frontend may add grouping separators for display but must not convert the values to JavaScript `number` to derive business output.

## 5. NAV availability semantics

### Available

An `available` NAV exists and its valuation time is no older than the configured freshness threshold.

### Stale

An `available` NAV exists but is older than `VG_FUND_NAV_STALE_AFTER_HOURS`, default 36 hours.

The last NAV and derived values are returned together with:

```json
{"navStatus":"stale"}
```

The UI must display a warning.

### Unavailable

No `available` NAV exists.

The response keeps these fields `null`:

```json
{
  "latestUnitNav": null,
  "marketValue": null,
  "cumulativeReturn": null,
  "returnRate": null,
  "navStatus": "unavailable"
}
```

Missing data is never represented as zero.

A stored NAV whose currency conflicts with fund base currency, whose Decimal is invalid or whose valuation time is unexpectedly in the future is treated as a server-side integrity failure and fails closed.

## 6. Authentication, permissions and scope

All routes are under the existing human-session assurance boundary. API-key `admin`, including wildcard permission, is rejected before the user-system route executes.

| Operation | Permission | Additional controls |
|---|---|---|
| Read own holdings | `member.holding.read_self` | User ID comes only from Session Principal |
| Read a member's holdings | `member.holding.read_all` | CEO policy; target must be approved member; successful read audited |
| Create/update holding | `member.holding.update` | CEO policy; recent reauthentication; target member; optimistic version; audit in same transaction |
| List fund catalog for holding administration | `member.holding.read_all` | Human Session only |
| Update fund unit NAV/code | `member.holding.update` | CEO policy; recent reauthentication; currency match; audit in same transaction |

The self endpoint is:

```http
GET /api/v1/me/holdings
```

It accepts no member user identifier. Unknown query parameters cannot change the Principal-derived user.

Administrative endpoints are:

```http
GET /api/v1/users/{userId}/holdings
PUT /api/v1/users/{userId}/holdings/{fundId}
GET /api/v1/users/holdings/funds
PUT /api/v1/users/holdings/funds/{fundId}/nav
```

Fund management routes intentionally remain under `/api/v1/users/...` so the existing assurance classifier treats them as human-session routes in every environment. They do not broaden the authentication rules for existing `/api/v1/funds`, trading or operational APIs.

## 7. Audit and transaction semantics

Successful sensitive operations create audit events without raw passwords, Session/CSRF tokens, reset tickets or full holding payload copies.

Current events:

- `member.holdings_viewed_by_admin`;
- `member.holding_updated`;
- `fund.nav_updated`.

Holding/NAV mutation and its audit row use the same SQLite transaction. If audit insertion fails, the holding/NAV write rolls back. The service does not return success without audit evidence.

## 8. Optimistic concurrency

Creating a new holding requires `expectedVersion` to be omitted.

Updating an existing holding requires the current `rowVersion`:

```json
{
  "shareQuantity": "1250.5",
  "cumulativeInvested": "100000",
  "asOf": "2026-07-26T08:00:00+00:00",
  "source": "manual_admin",
  "status": "active",
  "expectedVersion": 3
}
```

A stale version returns HTTP 409 with `row_version_conflict`. The server never silently overwrites a concurrent change.

## 9. Frontend behavior

### Member personal account

The canonical personal route remains `/account/index`. Members default to the fund-holdings tab after profile hydration.

The page displays:

- fund name/code and currency;
- units, latest unit NAV, market value and cumulative invested;
- cumulative return and return rate;
- NAV state and valuation time;
- holding source/status and data timestamps.

Stale and unavailable NAV states are visually explicit. Non-member roles receive an explicit not-applicable empty state.

### Administrator user detail

The holding tab is rendered only when:

- the target role is `member`; and
- the current authentication state contains `member.holding.read_all`.

Mutation controls additionally require `member.holding.update`. Frontend visibility is usability only; backend permission, target and reauthentication checks remain authoritative.

## 10. Verification evidence to execute

Direct tests committed in this branch include:

- `test_member_holding_migrations.py`;
- `test_member_holding_decimal.py`;
- `test_member_holdings.py`;
- `test_member_holding_scope.py`;
- `test_member_holding_audit_transactions.py`;
- frontend `decimalDisplay.test.ts`.

They cover additive upgrade/repeat startup, exact Decimal vectors, missing/stale NAV, self isolation, employee/technical-lead/API-key denial, recent reauthentication, optimistic conflicts and audit rollback.

These tests are written but have not been executed in the connector-only environment. Ruff, Pyright, classified Pytest, frontend lint/type/build and full CI remain required before acceptance.

## 11. Rollback and forward fix

Before deployment, back up the Platform SQLite database.

Migration 6 is additive. An applied migration is not edited or selectively reversed. Recovery is either:

1. restore the complete pre-migration database backup together with the prior application version; or
2. deploy a new forward-fix migration and compatible application version.

Application rollback without database restore is allowed only when the older application tolerates the added nullable column and tables; this must be verified in deployment rehearsal.
