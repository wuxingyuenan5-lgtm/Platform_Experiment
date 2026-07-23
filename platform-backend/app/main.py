from app import auth, eod_reconciliation, execution_risk
from app.application import app
from app.auth import AuthenticationMiddleware
from app.credential_security import router as credential_security_router
from app.disaster_recovery import router as disaster_recovery_router
from app.eod_policy import apply_outstanding_difference_gate, list_strategy_orders_for_eod
from app.eod_reconciliation import router as eod_reconciliation_router
from app.execution_exposure import calculate_residual_exposure
from app.execution_risk import router as execution_risk_router
from app.financial_facts import router as financial_facts_router
from app.live_trading_sessions import router as live_trading_sessions_router
from app.live_venue_accounting import router as live_venue_accounting_router
from app.production_monitoring import router as production_monitoring_router
from app.venue_reconciliation import router as venue_reconciliation_router

# The composition root selects the Phase 4A contract-delta exposure model while
# the broader execution-risk module is split incrementally in later Phase 4 work.
execution_risk.calculate_residual_exposure = calculate_residual_exposure

# Phase 4D keeps the report orchestration module stable while applying the final
# operational policies at the composition boundary: reconcile the business-day
# window plus unresolved historical orders, and block scale review for any
# historical open or accepted difference.
eod_reconciliation.list_strategy_orders = list_strategy_orders_for_eod
_original_create_eod_report = eod_reconciliation.create_eod_report


def _create_eod_report_with_policy(request):
    report = _original_create_eod_report(request)
    apply_outstanding_difference_gate(
        report.report_id,
        report.strategy_instance_id,
        report.account_id,
    )
    return eod_reconciliation.get_eod_report(report.report_id)


eod_reconciliation.create_eod_report = _create_eod_report_with_policy

# Security metadata and Production Operations are intentionally narrower than
# ordinary platform reads and admin writes. Existing role permissions are reused:
# audit:read for status/history, operations:run for scans/backup/restore/scheduler,
# and reconciliation:review for alert acknowledgement/closure by Risk or Ops.
_original_permission_for_request = auth.permission_for_request


def _permission_for_request(method: str, path: str) -> str:
    normalized_method = method.upper()
    if normalized_method in {"GET", "HEAD"} and path.endswith(
        "/security/credential-rotations"
    ):
        return "audit:read"
    production_read_paths = (
        "/ops/production-status",
        "/ops/alerts",
        "/ops/backups",
        "/ops/restore-drills",
        "/ops/controlled-operations",
    )
    if normalized_method in {"GET", "HEAD"} and any(
        path.endswith(fragment) for fragment in production_read_paths
    ):
        return "audit:read"
    if "/ops/alerts/" in path and (
        path.endswith("/acknowledge") or path.endswith("/close")
    ):
        return "reconciliation:review"
    production_write_paths = (
        "/ops/alerts/scan",
        "/ops/backups",
        "/ops/restore-drills",
        "/ops/controlled-operations",
    )
    if normalized_method == "POST" and any(
        path.endswith(fragment) for fragment in production_write_paths
    ):
        return "operations:run"
    return _original_permission_for_request(method, path)


auth.permission_for_request = _permission_for_request

app.include_router(financial_facts_router)
app.include_router(execution_risk_router)
app.include_router(venue_reconciliation_router)
app.include_router(live_venue_accounting_router)
app.include_router(eod_reconciliation_router)
app.include_router(live_trading_sessions_router)
app.include_router(credential_security_router)
app.include_router(production_monitoring_router)
app.include_router(disaster_recovery_router)

# Authentication is added at the composition root so every legacy and modular
# route passes through one default-deny production authorization boundary.
app.add_middleware(AuthenticationMiddleware)

__all__ = ["app"]
