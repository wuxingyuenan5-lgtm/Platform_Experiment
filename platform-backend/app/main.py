from app.application import app
from app.auth import AuthenticationMiddleware
from app.credential_security import router as credential_security_router
from app.cross_spread_exit_routes import router as cross_spread_exit_router
from app.cross_spread_observability_routes import router as cross_spread_observability_router
from app.disaster_recovery import router as disaster_recovery_router
from app.eod_reconciliation import router as eod_reconciliation_router
from app.execution_risk import router as execution_risk_router
from app.financial_facts import router as financial_facts_router
from app.live_trading_sessions import router as live_trading_sessions_router
from app.live_venue_accounting import router as live_venue_accounting_router
from app.member_holding_routes import router as member_holding_router
from app.production_monitoring import router as production_monitoring_router
from app.schema_governance import router as schema_governance_router
from app.user_admin_routes import router as user_admin_router
from app.user_avatar_routes import router as user_avatar_router
from app.user_cache_control import UserNoStoreMiddleware
from app.user_routes import router as user_router
from app.venue_reconciliation import router as venue_reconciliation_router

app.include_router(financial_facts_router)
app.include_router(execution_risk_router)
app.include_router(venue_reconciliation_router)
app.include_router(live_venue_accounting_router)
app.include_router(eod_reconciliation_router)
app.include_router(live_trading_sessions_router)
app.include_router(credential_security_router)
app.include_router(production_monitoring_router)
app.include_router(disaster_recovery_router)
app.include_router(schema_governance_router)
app.include_router(cross_spread_exit_router)
app.include_router(cross_spread_observability_router)
app.include_router(user_router)
app.include_router(user_avatar_router)
app.include_router(user_admin_router)
app.include_router(member_holding_router)

# Authentication is added at the composition root so every legacy and modular
# route passes through one default-deny production authorization boundary.
app.add_middleware(AuthenticationMiddleware)
# Added after AuthenticationMiddleware so it wraps authentication failures as
# well as successful identity/customer responses.
app.add_middleware(UserNoStoreMiddleware)

__all__ = ["app"]
