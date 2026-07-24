# Failure Injection and Production Acceptance

Offline tests prove fail-closed software behavior. They do not authorize Live Write or replace controlled real-account acceptance.

## Automated failure matrix

| Scenario | Required result | Automated evidence |
|---|---|---|
| Runtime request times out | Platform Order and TradeCommand become `result_unknown`; no automatic resubmit | order recovery and failure-injection tests |
| Runtime returns unsupported contract version | payload is rejected as incompatible; Platform keeps outcome unknown | contract compatibility and live-safety tests |
| Fill arrives before ACK | Fill remains authoritative; later ACK cannot downgrade `filled` | out-of-order event test |
| Duplicate Fill arrives | immutable Fill identity prevents duplicate Position/PnL projection | replay and failure-injection tests |
| Runtime Gateway result becomes unknown | command claim remains; repeating the HTTP request does not call Gateway again | Runtime unknown-result injection test |
| Runtime journal has no events yet | replay returns conflict/unknown, not a second external action | Runtime unknown-result injection test |
| Command/Event identity mismatches | Platform rejects the event and does not project it | execution-event validation tests |
| Kill Switch activates during execution | further legs/actions fail closed according to the risk policy | live-safety and execution-risk tests |
| Reconciliation or EOD source is unavailable | status remains partial/failed; cannot appear clean | reconciliation/EOD/monitoring tests |
| Backup or restore evidence is invalid | operation fails and Live Write remains disabled | disaster-recovery tests |

## Controlled production acceptance order

1. Run full CI and Secret Scan on the exact release commit.
2. Deploy to a controlled host with separate Platform DB, Runtime Journal and backup root.
3. Keep both Live Write gates disabled.
4. Resolve credential references using the approved provider; never copy values into logs or task documents.
5. Run read-only connectivity and venue-readiness checks.
6. Run shadow Order/Fill/Position/Balance reconciliation.
7. Exercise Global, Strategy and Account Kill Switches without sending an order.
8. Approve one bounded LiveTradingSession using two different identities.
9. Submit the venue/broker minimum permitted order size with pre-defined stop conditions.
10. Verify external Order/Fill/Deal identity, Platform Order, Runtime Journal, FinancialFact and EOD evidence.
11. Complete multiple clean EOD cycles before considering any increase in limits.

## Mandatory stop conditions

Stop new submissions and enable the Global Kill Switch when any of these occurs:

- external result cannot be recovered from query/history;
- Platform and venue position differ;
- duplicate or missing Fill/Deal identity is observed;
- formal financial fact cannot be reconciled;
- Runtime restarts without deterministic recovery;
- credential/redaction boundary is violated;
- backup, restore or EOD evidence is incomplete;
- session scope, notional or daily limit is uncertain.

## Evidence record

A production acceptance record must identify:

- release commit and CI runs;
- controlled host/environment;
- StrategyInstance, Account and symbols without credential values;
- session approver identities;
- minimum-size order and external IDs;
- timestamps and reconciliation result;
- Kill Switch drill result;
- EOD report and backup/restore evidence;
- final decision: remain at current limits, remediate or reject.

Passing offline or controlled acceptance never changes Live Write defaults in source control. Any future limit increase is a separate risk/operations decision.
