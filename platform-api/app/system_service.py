from app.config import Settings
from app.runtime_status_client import read_runtime_status
from app.schemas import RuntimeReadinessResponse
from app.system_repository import check_database_ready


def get_runtime_readiness(settings: Settings) -> RuntimeReadinessResponse:
    check_database_ready()
    return RuntimeReadinessResponse(
        backendStatus="available",
        databaseStatus="available",
        runtimeStatus=read_runtime_status(
            settings.runtime_base_url,
            settings.runtime_timeout_seconds,
        ),
        defaultTradingMode="simulation",
    )
