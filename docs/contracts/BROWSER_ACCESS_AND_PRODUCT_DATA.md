# Browser Access and Product Data Contract

This contract owns browser-role capabilities, route/menu consistency, personal-account access and restored product data states. It does not grant API-Key authority, LiveTradingSession authority or permission to bypass execution safety.

## Authority chain

1. `platform-api/app/user_permissions.py` owns human-role capability sets.
2. Authenticated browser Sessions receive the resolved permission set from the backend.
3. `platform-web/src/access/browserRouteCapabilities.ts` assigns one capability to each formal route family.
4. The effective `asyncRoutes` tree is the shared input for menu generation and direct-URL authorization.
5. Backend endpoints independently verify permission and resource scope. A hidden menu or button is never authorization.

## Browser roles

| Role | Product pages | Risk and account directory | Business writes | Personal account |
|---|---|---|---|---|
| CEO | All formal pages | Full internal visibility | Broad product and administration capability | Own profile, avatar, password, devices, sessions and holdings |
| Technical lead | All formal pages | Internal visibility and operational management | Broad operational writes, excluding CEO identity governance | Own profile, avatar, password, devices, sessions and holdings |
| Employee | All formal business pages, read-only | Risk management and account directory read-only | Denied | Own profile, avatar, password, devices, sessions and holdings |
| Member | All formal business pages, read-only | Hidden and denied | Denied | Own profile, avatar, password, devices, sessions and holdings |

CEO uses the backend wildcard capability. The wildcard affects authorization lookup only; it does not bypass last-CEO protection, two-person approval, Kill Switch, allowlists, risk checks, query-before-retry, EOD controls or either Live Write gate.

## Route capabilities

| Route family | Capability |
|---|---|
| `/home` | `dashboard.read` |
| `/hedge-board` | `research.read` |
| `/strategy` | `strategy.read` |
| `/finance` | `finance.read` |
| `/data` | `data.read` |
| `/monitor` | `monitor.read` |
| `/reports` | `reports.read` |
| `/news-calendar` | `news.read` |
| `/financial-ai` | `financial_ai.read` |
| `/settings` | `settings.read` |
| `/risk` | `risk.read` |
| `/users` | `user.read` |
| `/audit` | `audit:read` |
| `/account` | `profile.read_self` |

Legacy route `roles` fields are not part of the effective browser authorization tree. New route families must be registered in the central mapping and covered by tests.

## Product data states

Every restored product surface has one of four states:

- `live`: owned Provider or Platform fact with source and current timestamp semantics;
- `sample`: deliberately static or deterministic presentation data, visibly labeled, `actionable=false`;
- `unavailable`: required Provider or application owner is not configured;
- `error`: an owned live request failed; the UI must not silently replace it with a successful-looking value.

A `sample` envelope with `actionable=true` is invalid. Sample pages must not import production `mock`, `fixture` or `seed` directories. Buttons that imply writes are hidden for read-only roles and remain disabled when the underlying product state is non-actionable or Live Write is disabled.

## Restored surfaces

| Surface | Current data boundary |
|---|---|
| Dashboard | Disclosed sample structure; aggregate Owner unavailable |
| Strategy management | Disclosed sample strategy catalog; no lifecycle writes |
| Funding carry | Disclosed sample research; no order submission |
| Cross-venue spread research | Disclosed sample analysis; formal `CrossVenueExecutionWorkspace` retained for execution |
| Financial AI | Provider unavailable; no fabricated model answer |
| News calendar | TradingView economic calendar live; news and wealth sections use disclosed samples |
| Settings | Current Session and data-service health are live when available; settings writes unavailable; personal account remains real self-service |

## Acceptance criteria

- All eight reusable browser accounts can sign in.
- CEO and technical lead can see the relevant operation controls, while Live Write and non-actionable sample states remain enforced.
- Employees can reach all business pages and read risk/account-directory views, but backend mutation attempts return `403`.
- Members can reach business pages and their personal account, but `/risk` and user-directory API access are denied.
- Menu visibility, direct URL behavior and backend API responses agree for every role.
- Four viewport visual evidence covers Dashboard, strategy management, funding carry, spread research, Financial AI, news and settings.
- Product Data Owner audit is closed and Live Write remains `false` for every entry.
