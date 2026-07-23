from app import execution_risk
from app.application import app
from app.execution_exposure import calculate_residual_exposure
from app.execution_risk import router as execution_risk_router
from app.financial_facts import router as financial_facts_router
from app.venue_reconciliation import router as venue_reconciliation_router

# The composition root selects the Phase 4A contract-delta exposure model while
# the broader execution-risk module is split incrementally in later Phase 4 work.
execution_risk.calculate_residual_exposure = calculate_residual_exposure

app.include_router(financial_facts_router)
app.include_router(execution_risk_router)
app.include_router(venue_reconciliation_router)

__all__ = ["app"]
