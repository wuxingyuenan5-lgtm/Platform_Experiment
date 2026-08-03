from __future__ import annotations

from fastapi import APIRouter

from app.config import Settings
from app.gateway import ExecutionGateway
from app.journal import journal_status
from app.models import RuntimeStatusResponse
from app.version import PLATFORM_VERSION


def create_system_router(
    *,
    settings: Settings,
    gateway: ExecutionGateway,
) -> APIRouter:
    router = APIRouter()

    @router.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "execution-runtime",
            "gateway": gateway.name,
        }

    @router.get("/status", response_model=RuntimeStatusResponse, tags=["system"])
    def status() -> RuntimeStatusResponse:
        return RuntimeStatusResponse(
            status="available",
            service="execution-runtime",
            version=PLATFORM_VERSION,
            environment=settings.environment,
            gateway=gateway.name,
            journal=journal_status(),
        )

    return router
