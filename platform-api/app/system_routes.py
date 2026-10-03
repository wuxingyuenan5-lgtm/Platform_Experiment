import sys

from fastapi import APIRouter

from app import monitor_health
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

    @router.get(f"{settings.api_prefix}/system/monitor-health", tags=["system"])
    @router.get("/health/monitors", tags=["system"])
    async def monitors() -> dict:
        # Async route remains responsive when blocking venue calls occupy workers.
        return {
            "watchdog": monitor_health.watchdog_snapshot(),
            "dataAudit": monitor_health.snapshot("data_audit", enabled=True, deadline=900),
            "accountSync": monitor_health.snapshot("account_sync", enabled=True, deadline=180),
            "accountHistory": monitor_health.snapshot(
                "account_history", enabled=True, deadline=600
            ),
            "managementProjection": monitor_health.snapshot(
                "management_projection", enabled=True, deadline=120
            ),
            "fundingRunner": monitor_health.snapshot("funding_runner", enabled=True, deadline=60),
            "fundingExit": monitor_health.snapshot("funding_exit", enabled=True, deadline=60),
            "crossExit": monitor_health.snapshot(
                "cross_exit",
                enabled=settings.cross_spread_exit_monitor_enabled,
                deadline=60,
            ),
            "crossExitExecutionEnabled": (
                settings.cross_spread_exit_monitor_enabled and settings.live_trading_enabled
            ),
            "liveTradingEnabled": settings.live_trading_enabled,
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
