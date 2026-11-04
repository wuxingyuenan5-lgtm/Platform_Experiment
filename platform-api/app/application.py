import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import live_venue_snapshot_sync, runtime_transport
from app.auth import AuthenticationMiddleware
from app.catalog_routes import create_catalog_router
from app.config import get_settings
from app.credential_security import router as credential_security_router
from app.cross_spread_exit_routes import router as cross_spread_exit_router
from app.cross_spread_observability_routes import router as cross_spread_observability_router
from app.data_audit import lifespan as data_audit_lifespan
from app.data_audit import router as data_audit_router
from app.database import initialize_database
from app.disaster_recovery import router as disaster_recovery_router
from app.eod_reconciliation_routes import router as eod_reconciliation_router
from app.execution_risk import configure_trade_command_port
from app.execution_risk import router as execution_risk_router
from app.financial_ai_routes import router as financial_ai_router
from app.financial_facts import router as financial_facts_router
from app.live_trading_sessions import router as live_trading_sessions_router
from app.live_venue_accounting import router as live_venue_accounting_router
from app.live_venue_snapshot_sync import router as live_venue_snapshot_sync_router
from app.member_holding_routes import router as member_holding_router
from app.operational_metrics import router as operational_metrics_router
from app.production_monitoring import router as production_monitoring_router
from app.research_a_share_refresh import lifespan as research_lifespan
from app.research_hk_share_refresh import lifespan as research_hk_lifespan
from app.research_overseas_refresh import lifespan as research_overseas_lifespan
from app.research_routes import router as research_router
from app.research_watchlist_routes import router as research_watchlist_router
from app.schema_governance import router as schema_governance_router
from app.security_ops_routes import create_security_ops_router
from app.strategies import funding_runner
from app.strategy_research_ingest import lifespan as strategy_research_lifespan
from app.strategy_research_routes import router as strategy_research_router
from app.system_routes import create_system_router
from app.trade_commands import create_trade_command
from app.trading_routes import create_trading_router
from app.user_admin_note_routes import router as user_admin_note_router
from app.user_admin_routes import router as user_admin_router
from app.user_avatar_routes import router as user_avatar_router
from app.user_cache_control import UserNoStoreMiddleware
from app.user_routes import router as user_router
from app.personal_workspace import router as personal_workspace_router
from app.venue_reconciliation_routes import router as venue_reconciliation_router

PLATFORM_VERSION = "0.11.4"

configure_trade_command_port(create_trade_command)


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app.account_history_sync import run_history_sync_monitor
    from app.strategies.funding_exit_service import run_funding_exit_monitor

    initialize_database()
    stop = asyncio.Event()
    runner = asyncio.create_task(funding_runner.run_funding_instruction_monitor(stop))
    funding_exit_monitor = asyncio.create_task(run_funding_exit_monitor(stop))
    snapshot_monitor = asyncio.create_task(live_venue_snapshot_sync.run_snapshot_sync_monitor())
    history_monitor = asyncio.create_task(run_history_sync_monitor())
    from app.strategy_management_projection import run_management_projection_monitor

    management_monitor = asyncio.create_task(run_management_projection_monitor())
    try:
        async with (
            research_lifespan(_),
            research_hk_lifespan(_),
            research_overseas_lifespan(_),
            strategy_research_lifespan(_),
            data_audit_lifespan(_),
        ):
            yield
    finally:
        stop.set()
        snapshot_monitor.cancel()
        history_monitor.cancel()
        management_monitor.cancel()
        try:
            await management_monitor
        except asyncio.CancelledError:
            pass
        try:
            await runner
        finally:
            await funding_exit_monitor
            try:
                await snapshot_monitor
            except asyncio.CancelledError:
                pass
            try:
                await history_monitor
            except asyncio.CancelledError:
                pass
            runtime_transport.close()


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

    for router in (
        financial_facts_router, financial_ai_router, execution_risk_router,
        venue_reconciliation_router, live_venue_accounting_router,
        live_venue_snapshot_sync_router, eod_reconciliation_router,
        live_trading_sessions_router, credential_security_router,
        production_monitoring_router, operational_metrics_router,
        disaster_recovery_router, schema_governance_router, cross_spread_exit_router,
        cross_spread_observability_router, research_router, data_audit_router,
        strategy_research_router, research_watchlist_router, user_router,
        personal_workspace_router, user_avatar_router, user_admin_router,
        user_admin_note_router, member_holding_router,
    ):
        application.include_router(router)

    application.add_middleware(AuthenticationMiddleware)
    application.add_middleware(UserNoStoreMiddleware)
    return application


app = create_application()

# Version-consistency tooling verifies both OpenAPI and system-info ownership here.
SYSTEM_INFO_VERSION = {"version": PLATFORM_VERSION}
