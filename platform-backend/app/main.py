from app.application import app
from app.financial_facts import router as financial_facts_router
from app.phase4_risk import router as phase4_risk_router

app.include_router(financial_facts_router)
app.include_router(phase4_risk_router)

__all__ = ["app"]
