from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.command_routes import create_command_router
from app.config import get_settings
from app.gateway import ExecutionGateway
from app.gateway_factory import create_gateway
from app.gateway_routes import create_gateway_router
from app.journal import initialize_journal
from app.live_route_store import ensure_live_store
from app.system_routes import create_system_router
from app.venue_query_routes import create_venue_query_router
from app.venue_store import ensure_store
from app.version import PLATFORM_VERSION

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_journal()
    ensure_store()
    ensure_live_store()
    yield


def create_app(gateway: ExecutionGateway | None = None) -> FastAPI:
    runtime_gateway = gateway or create_gateway(settings.gateway_name)
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
    application.include_router(create_venue_query_router(gateway=runtime_gateway))
    return application


app = create_app()
