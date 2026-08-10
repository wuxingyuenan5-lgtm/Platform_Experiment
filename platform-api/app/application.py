from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import AuthenticationMiddleware
from app.catalog_routes import create_catalog_router
from app.config import get_settings
from app.credential_security import router as credential_security_router
from app.cross_spread_exit_routes import router as cross_spread_exit_router
from app.cross_spread_observability_routes import router as cross_spread_observability_router
from app.database import initialize_database
from app.disaster_recovery import router as disaster_recovery_router
from app.eod_reconciliation_routes import router as eod_reconciliation_router
from app.execution_risk import configure_trade_command_port
from app.execution_risk import router as execution_risk_router
from app.financial_facts import router as financial_facts_router
from app.live_trading_sessions import router as live_trading_sessions_router
from app.live_venue_accounting import router as live_venue_accounting_router
from app.member_holding_routes import router as member_holding_router
from app.production_monitoring import router as production_monitoring_router
from app.research_routes import router as research_router
from app.research_watchlist_routes import router as research_watchlist_router
from app.schema_governance import router as schema_governance_router
from app.security_ops_routes import create_security_ops_router
from app.system_routes import create_system_router
from app.trade_commands import create_trade_command
from app.trading_routes import create_trading_router
from app.user_admin_note_routes import router as user_admin_note_router
from app.user_admin_routes import router as user_admin_router
from app.user_avatar_routes import router as user_avatar_router
from app.user_cache_control import UserNoStoreMiddleware
from app.user_routes import router as user_router
from app.venue_reconciliation_routes import router as venue_reconciliation_router

PLATFORM_VERSION = "0.11.0"

configure_trade_command_port(create_trade_command)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


def create_application() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=PLATFORM_VERSION,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(create_system_router(settings, PLATFORM_VERSION))
    application.include_router(create_security_ops_router(settings.api_prefix))
    application.include_router(create_catalog_router(settings.api_prefix))
    application.include_router(create_trading_router(settings.api_prefix))

    application.include_router(financial_facts_router)
    application.include_router(execution_risk_router)
    application.include_router(venue_reconciliation_router)
    application.include_router(live_venue_accounting_router)
    application.include_router(eod_reconciliation_router)
    application.include_router(live_trading_sessions_router)
    application.include_router(credential_security_router)
    application.include_router(production_monitoring_router)
    application.include_router(disaster_recovery_router)
    application.include_router(schema_governance_router)
    application.include_router(cross_spread_exit_router)
    application.include_router(cross_spread_observability_router)
    application.include_router(research_router)
    application.include_router(research_watchlist_router)
    application.include_router(user_router)
    application.include_router(user_avatar_router)
    application.include_router(user_admin_router)
    application.include_router(user_admin_note_router)
    application.include_router(member_holding_router)

    application.add_middleware(AuthenticationMiddleware)
    application.add_middleware(UserNoStoreMiddleware)
    return application


app = create_application()

# Version-consistency tooling verifies both OpenAPI and system-info ownership here.
SYSTEM_INFO_VERSION = {"version": PLATFORM_VERSION}
