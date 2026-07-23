from app.application import app
from app.execution_risk import router as execution_risk_router
from app.financial_facts import router as financial_facts_router

app.include_router(financial_facts_router)
app.include_router(execution_risk_router)

__all__ = ["app"]
