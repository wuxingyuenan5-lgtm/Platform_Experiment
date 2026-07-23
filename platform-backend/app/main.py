from app.application import app
from app.financial_facts import router as financial_facts_router

app.include_router(financial_facts_router)

__all__ = ["app"]
