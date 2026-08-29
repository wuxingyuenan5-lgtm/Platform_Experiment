from __future__ import annotations

import sys
from datetime import UTC, datetime

from fastapi import APIRouter

from app.config import Settings
from app.gateway import ExecutionGateway
from app.journal import journal_status
from app.models import RuntimeStatusResponse
from app.version import PLATFORM_VERSION

PROCESS_STARTED_AT = datetime.now(UTC)


def create_system_router(
    *,
    settings: Settings,
    gateway: ExecutionGateway,
) -> APIRouter:
    router = APIRouter()

    @router.get("/health", tags=["system"])
    def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "service": "execution-runtime",
            "gateway": gateway.name,
            "pythonVirtualEnvironment": sys.prefix != sys.base_prefix,
        }

    @router.get("/status", response_model=RuntimeStatusResponse, tags=["system"])
    def status() -> RuntimeStatusResponse:
        return RuntimeStatusResponse(
            status="available",
            service="execution-runtime",
            version=PLATFORM_VERSION,
            environment=settings.environment,
            gateway=gateway.name,
            processStartedAt=PROCESS_STARTED_AT,
            journal=journal_status(),
            capabilities=gateway.capabilities(),
        )

    return router
