from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.command_routes import create_command_router
from app.config import get_settings
from app.gateway import VenueGateway
from app.gateway_factory import create_gateway
from app.gateway_routes import create_gateway_router
from app.journal import initialize_journal
from app.live_route_store import ensure_live_store
from app.operational_metrics import router as operational_metrics_router
from app.recovery_routes import create_recovery_router
from app.research_market_capture import ResearchCapture, create_research_market_router
from app.system_routes import create_system_router
from app.venue_query_routes import create_venue_query_router
from app.venue_store import ensure_store
from app.version import PLATFORM_VERSION

settings = get_settings()


def create_app(gateway: VenueGateway | None = None) -> FastAPI:
    runtime_gateway = gateway or create_gateway(
        settings.gateway_name,
        live_write_enabled=settings.live_write_enabled,
    )

    capture = ResearchCapture(settings, runtime_gateway)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        initialize_journal()
        ensure_store()
        ensure_live_store()
        if settings.live_write_enabled:
            warm = getattr(runtime_gateway, "warm_live_execution", None)
            if warm is not None:
                warm()
        capture.start()
        try:
            yield
        finally:
            capture.close()
            close = getattr(runtime_gateway, "close", None)
            if close is not None:
                close()

    application = FastAPI(
        title=settings.app_name,
        version=PLATFORM_VERSION,
        lifespan=lifespan,
    )
    application.include_router(
        create_system_router(
            settings=settings,
            gateway=runtime_gateway,
        )
    )
    application.include_router(
        create_gateway_router(settings=settings, gateway=runtime_gateway)
    )
    application.include_router(create_command_router(gateway=runtime_gateway))
    application.include_router(create_recovery_router(gateway=runtime_gateway))
    application.include_router(create_venue_query_router(gateway=runtime_gateway))
    application.include_router(operational_metrics_router)
    application.include_router(create_research_market_router(capture))
    return application


app = create_app()
