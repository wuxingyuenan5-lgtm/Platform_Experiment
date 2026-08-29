import sys

from fastapi import APIRouter

from app.config import Settings
from app.schemas import RuntimeReadinessResponse
from app.system_service import get_runtime_readiness


def create_system_router(settings: Settings, platform_version: str) -> APIRouter:
    router = APIRouter()

    @router.get("/health", tags=["system"])
    def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "service": "platform-api",
            "environment": settings.environment,
            "pythonVirtualEnvironment": sys.prefix != sys.base_prefix,
        }

    @router.get(f"{settings.api_prefix}/system/info", tags=["system"])
    def system_info() -> dict[str, str]:
        return {
            "service": "platform-api",
            "version": platform_version,
            "apiVersion": "v1",
        }

    @router.get(
        f"{settings.api_prefix}/system/runtime-readiness",
        response_model=RuntimeReadinessResponse,
        tags=["system"],
    )
    def runtime_readiness() -> RuntimeReadinessResponse:
        return get_runtime_readiness(settings)

    return router
