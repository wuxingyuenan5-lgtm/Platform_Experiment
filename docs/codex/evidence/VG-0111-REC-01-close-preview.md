# VG-0111-REC-01 One-Time Close Preview

Authority: `eb950c4c`

Outcome: `NO-GO`. No endpoint was called and no order was attempted. Automatic retry and bypass are forbidden.

## Mandatory Gate Matrix

| Gate | Evidence | Result |
|---|---|---|
| Recovered Git ancestry | `2f3b291` is an ancestor of `eb950c4c`; isolated branch was clean before evidence writes | proven |
| Shared-root protection | Start status/path manifest recorded without file contents | proven, closure recheck pending |
| Running process source | Python executable/source paths unavailable; OS fallback denied | failed |
| Masked Bybit account identity | unavailable; no account read performed | failed |
| Masked MT5 account identity | unavailable; no account read performed | failed |
| Venue symbols | authorized target is Bybit `XAUTUSDT` and MT5 `XAUUSD.s`, but actual running symbols are unavailable | failed |
| Opposite position directions | unavailable | failed |
| Exact closable quantities and unit conversion | unavailable | failed |
| Position and external-order identities | unavailable | failed |
| No pending/open orders | unavailable | failed |
| No `result_unknown` state | unavailable | failed |
| Exit-plan and execution-batch claims | unavailable; running Platform database was not read | failed |
| Duplicate/occupied intent | unavailable | failed |
| Authenticated CEO authority | owner authorization is persisted, but no trusted authenticated Platform principal/token was available | failed |
| Formal active LiveTradingSession | unavailable; no authenticated read or mutation was attempted | failed |
| Runtime route identity | unavailable because running source/composition was not proven | failed |
| Bybit reduce-only close admission | repository rule proven locally; running route and actual position unavailable | failed |
| MT5 specified-position close admission | repository rule proven locally; actual Position Ticket and running route unavailable | failed |
| Operable Kill Switch | not proven; persisted owner observation says global Kill Switch disabled while `liveTradingEnabled=true` | failed/inconsistent |
| Independent Platform/Runtime Live Write gates and forced reset | repository contract only; running gates/readback unavailable | failed |

Any one failed or unavailable row is sufficient for `NO-GO`; multiple independent failures exist.

## Locally Provable Contract

- One close uses one existing active exit plan, one execution batch and the stable key `cross-spread-exit:<plan_id>`. The key must not be generated or used until the unique unoccupied plan identity is proven. Replay may return the same batch; it must never create a second business intent.
- Platform constructs the Bybit leg first and the MT5 leg second. Execution is serial: MT5 is not submitted until the Bybit command has a proven `filled` state. An accepted, processing, acknowledged or `result_unknown` first leg does not release the second leg.
- Both close intents must be `reduce_only=true`. Bybit must match exactly one opposite-side position and use its matching `positionIdx`; quantity cannot exceed that position. MT5 must bind the exact external Position Ticket, use the opposite closing side and not exceed ticket volume.
- The close target is all and only the externally proven matched exposure. Repository mapping is `MT5 lots = matched ounces / current MT5 contract_size`; minimum, step and maximum constraints must pass exactly. No repository default may substitute for a live contract specification.
- Repository leg order and sizing use `XAUTUSDT` then `XAUUSD.s`. However, `execution-runtime/tests/test_cross_spread_market_close.py` still exercises `XAUUSD+`; this inconsistency prevents inference about the running MT5 route.
- Entry spread is stored as `Bybit average fill price - MT5 average fill price` in USD per troy ounce. Executable long spread is `Bybit ask - MT5 bid`; executable short spread is `Bybit bid - MT5 ask`. Prices must be contemporaneous, symbol-matched and normalized to the same USD-per-troy-ounce unit.

## Diagnostic `-14.64`

The owner-expected value is diagnostic only and is not proven. Possible sources of a discrepancy include using entry averages instead of executable bid/ask sides, reversed subtraction/sign, non-contemporaneous quotes, stale quote timestamps, mark/last price substituted for bid/ask, MT5 symbol-suffix or contract mapping mismatch, inconsistent USD-per-ounce normalization, precision/rounding, or mixing fees/funding/swap with raw spread. None may change quantity, identity, reduce-only behavior or leg sequence.

## Narrow Future Read Interfaces

These interfaces are the minimum candidates for a separately proven formal window. They were not called in this task.

- Platform read-only: `GET /api/v1/live-trading/sessions`, `GET /api/v1/risk/kill-switches/{scope_type}/{scope_id}`, `GET /api/v1/trading/cross-spread/exit-plans`, `GET /api/v1/trading/execution-batches`, `GET /api/v1/trading/orders`, and `GET /api/v1/trading/fills`.
- Runtime read-only through the Platform-owned route only: `GET /status`, `GET /venue/instruments/{symbol}`, `GET /venue/positions`, `GET /venue/orders`, `GET /venue/order-history`, and `GET /venue/fill-history`, scoped to the two masked accounts and target symbols.
- Intended side-effect boundary: HTTP `GET` only; no order submission, cancellation, reconciliation mutation, auth-mode change, Live Write change or Kill Switch change. Source identity and authenticated CEO principal must be proven before use.

## Stop Record

The gate stopped before external reads because process provenance, trusted authentication, formal LiveSession, actual positions/orders/claims and Kill Switch operability were unavailable or inconsistent. No bypass, retry, direct SDK/script call, or order path was attempted.

## Offline Validation Record

- Task-card validator: passed after the `attention` summary named the accountable next action.
- `live-readiness` context pack: resolved within its selected required budget.
- Version consistency: passed.
- Repository structure and architecture: passed.
- Documentation consistency: this task's absolute user-profile path was corrected; the check remains failed only for the pre-existing unrelated missing `docs/codex/AI_DEVELOPMENT_STAGE_RETROSPECTIVE.md` reference in `VG-GOV-20260813-bounded-multi-agent.md`.
- Global context-budget check: failed on six unrelated over-budget packs (`identity-permission`, `member-contract`, `release-acceptance`, `research-field`, `research-provider`, `user-e2e`); `live-readiness` itself is within budget.
- Focused pytest suites: unavailable. The Codex-provided configured Python runtime has no `pytest` module and neither module has a project-local `.venv`; no dependency was installed or substituted.
- Repository pre-commit hook: unavailable because `platform-web/.husky/pre-commit` references missing `platform-web/.husky/_/husky.sh`; direct task-card, context, version, structure and diff checks were used instead.
