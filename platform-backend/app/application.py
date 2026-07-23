from contextlib import asynccontextmanager
from decimal import Decimal

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.catalog import (
    get_account,
    get_instrument,
    get_latest_balance,
    get_order,
    get_strategy_instance,
    get_strategy_pnl,
    list_accounts,
    list_fills,
    list_instruments,
    list_nav_snapshots,
    list_orders,
    list_positions,
    list_strategy_account_bindings,
    list_strategy_definitions,
    list_strategy_instances,
    run_nav_snapshot,
)
from app.config import get_settings
from app.cross_spread import (
    get_cross_spread_history,
    get_cross_spread_snapshot,
    submit_cross_spread_market_command,
)
from app.database import connection, initialize_database
from app.ops import get_reconciliation_summary, list_audit_events
from app.phase4_risk import create_execution_batch, get_execution_batch, list_execution_batches
from app.schemas import (
    AccountResponse,
    AuditEventResponse,
    BalanceSnapshotResponse,
    CreateExecutionBatchRequest,
    CreateOrderRequest,
    CreateStrategyRunRequest,
    CreateTradeCommandRequest,
    CredentialReferenceResponse,
    CrossSpreadHistoryPointResponse,
    CrossSpreadMarketCommandRequest,
    CrossSpreadSnapshotResponse,
    ExchangeConnectivityResponse,
    ExchangeVenueReadinessResponse,
    ExecutionBatchResponse,
    FillResponse,
    InstrumentResponse,
    OrderDetailResponse,
    OrderResponse,
    PnlResponse,
    PositionResponse,
    ReconciliationSummaryResponse,
    RuntimeReadinessResponse,
    StrategyAccountBindingResponse,
    StrategyDefinitionResponse,
    StrategyInstanceResponse,
    StrategyNavSnapshotResponse,
    StrategyPnlResponse,
    StrategyRunResponse,
    StrategyV1ReadinessResponse,
    TradeCommandResponse,
    TradingSafetyResponse,
)
from app.security import (
    get_exchange_connectivity,
    get_exchange_venue_readiness,
    get_trading_safety,
    list_credential_references,
)
from app.strategy_runs import create_strategy_run, list_strategy_runs
from app.trade_commands import create_trade_command, get_trade_command
from app.trading import reconcile_order, submit_order
from app.v1_readiness import get_strategy_v1_readiness

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title=settings.app_name, version="0.6.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "platform-backend",
        "environment": settings.environment,
    }


@app.get(f"{settings.api_prefix}/system/info", tags=["system"])
def system_info() -> dict[str, str]:
    return {
        "service": "platform-backend",
        "version": "0.6.0",
        "apiVersion": "v1",
    }


@app.get(
    f"{settings.api_prefix}/system/runtime-readiness",
    response_model=RuntimeReadinessResponse,
    tags=["system"],
)
def runtime_readiness() -> RuntimeReadinessResponse:
    with connection() as db:
        db.execute("SELECT 1").fetchone()
    runtime_status = "not_connected"
    try:
        response = httpx.get(
            f"{settings.runtime_base_url}/status",
            timeout=settings.runtime_timeout_seconds,
        )
        response.raise_for_status()
        runtime_status = response.json().get("status", "unknown")
    except httpx.HTTPError:
        runtime_status = "not_connected"
    return RuntimeReadinessResponse(
        backendStatus="available",
        databaseStatus="available",
        runtimeStatus=runtime_status,
        defaultTradingMode="simulation",
    )


@app.get(
    f"{settings.api_prefix}/security/trading-safety",
    response_model=TradingSafetyResponse,
    tags=["security"],
)
def trading_safety() -> TradingSafetyResponse:
    return get_trading_safety()


@app.get(
    f"{settings.api_prefix}/security/credential-references",
    response_model=list[CredentialReferenceResponse],
    tags=["security"],
)
def credential_references() -> list[CredentialReferenceResponse]:
    return list_credential_references()


@app.get(
    f"{settings.api_prefix}/security/exchange-connectivity",
    response_model=ExchangeConnectivityResponse,
    tags=["security"],
)
def exchange_connectivity() -> ExchangeConnectivityResponse:
    return get_exchange_connectivity()


@app.get(
    f"{settings.api_prefix}/security/exchange-venue-readiness",
    response_model=ExchangeVenueReadinessResponse,
    tags=["security"],
)
def exchange_venue_readiness() -> ExchangeVenueReadinessResponse:
    return get_exchange_venue_readiness()


@app.get(
    f"{settings.api_prefix}/ops/reconciliation-summary",
    response_model=ReconciliationSummaryResponse,
    tags=["ops"],
)
def reconciliation_summary() -> ReconciliationSummaryResponse:
    return get_reconciliation_summary()


@app.get(
    f"{settings.api_prefix}/ops/audit-events",
    response_model=list[AuditEventResponse],
    tags=["ops"],
)
def audit_events(
    subject_type: str | None = Query(default=None, alias="subjectType"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AuditEventResponse]:
    return list_audit_events(subject_type=subject_type, limit=limit)


@app.get(
    f"{settings.api_prefix}/strategies/definitions",
    response_model=list[StrategyDefinitionResponse],
    tags=["strategies"],
)
def strategies_definitions() -> list[StrategyDefinitionResponse]:
    return list_strategy_definitions()


@app.get(
    f"{settings.api_prefix}/strategies/instances",
    response_model=list[StrategyInstanceResponse],
    tags=["strategies"],
)
def strategies_instances() -> list[StrategyInstanceResponse]:
    return list_strategy_instances()


@app.get(
    f"{settings.api_prefix}/strategies/instances/{{strategy_instance_id}}",
    response_model=StrategyInstanceResponse,
    tags=["strategies"],
)
def strategy_instance(strategy_instance_id: str) -> StrategyInstanceResponse:
    return get_strategy_instance(strategy_instance_id)


@app.get(
    f"{settings.api_prefix}/strategies/instances/{{strategy_instance_id}}/accounts",
    response_model=list[StrategyAccountBindingResponse],
    tags=["strategies"],
)
def strategy_accounts(strategy_instance_id: str) -> list[StrategyAccountBindingResponse]:
    return list_strategy_account_bindings(strategy_instance_id)


@app.post(
    f"{settings.api_prefix}/strategies/instances/{{strategy_instance_id}}/runs",
    response_model=StrategyRunResponse,
    tags=["strategies"],
)
def create_run(
    strategy_instance_id: str,
    request: CreateStrategyRunRequest,
) -> StrategyRunResponse:
    return create_strategy_run(strategy_instance_id, request)


@app.get(
    f"{settings.api_prefix}/strategies/instances/{{strategy_instance_id}}/runs",
    response_model=list[StrategyRunResponse],
    tags=["strategies"],
)
def strategy_runs(strategy_instance_id: str) -> list[StrategyRunResponse]:
    return list_strategy_runs(strategy_instance_id)


@app.get(
    f"{settings.api_prefix}/strategies/instances/{{strategy_instance_id}}/v1-readiness",
    response_model=StrategyV1ReadinessResponse,
    tags=["strategies"],
)
def strategy_v1_readiness(strategy_instance_id: str) -> StrategyV1ReadinessResponse:
    return get_strategy_v1_readiness(strategy_instance_id)


@app.get(
    f"{settings.api_prefix}/accounts",
    response_model=list[AccountResponse],
    tags=["accounts"],
)
def accounts() -> list[AccountResponse]:
    return list_accounts()


@app.get(
    f"{settings.api_prefix}/accounts/{{account_id}}",
    response_model=AccountResponse,
    tags=["accounts"],
)
def account(account_id: str) -> AccountResponse:
    return get_account(account_id)


@app.get(
    f"{settings.api_prefix}/accounts/{{account_id}}/balances/latest",
    response_model=BalanceSnapshotResponse,
    tags=["accounts"],
)
def latest_balance(account_id: str) -> BalanceSnapshotResponse:
    return get_latest_balance(account_id)


@app.get(
    f"{settings.api_prefix}/accounts/{{account_id}}/positions",
    response_model=list[PositionResponse],
    tags=["accounts"],
)
def account_positions(account_id: str) -> list[PositionResponse]:
    rows = list_positions(account_id)
    return [
        PositionResponse(
            accountId=row["account_id"],
            instrumentId=row["instrument_id"],
            netQuantity=Decimal(row["net_quantity"]),
            averagePrice=(Decimal(row["average_price"]) if row["average_price"] else None),
        )
        for row in rows
    ]


@app.get(
    f"{settings.api_prefix}/instruments",
    response_model=list[InstrumentResponse],
    tags=["instruments"],
)
def instruments() -> list[InstrumentResponse]:
    return list_instruments()


@app.get(
    f"{settings.api_prefix}/instruments/{{instrument_id}}",
    response_model=InstrumentResponse,
    tags=["instruments"],
)
def instrument(instrument_id: str) -> InstrumentResponse:
    return get_instrument(instrument_id)


@app.post(
    f"{settings.api_prefix}/trading/orders",
    response_model=OrderResponse,
    tags=["trading"],
    deprecated=True,
    summary="Compatibility order endpoint; use TradeCommand or ExecutionBatch",
)
def create_order(request: CreateOrderRequest) -> OrderResponse:
    return submit_order(request)


@app.post(
    f"{settings.api_prefix}/trading/orders/{{order_id}}/reconcile",
    response_model=OrderResponse,
    tags=["trading"],
    summary="Recover an uncertain order from Runtime Journal",
)
def reconcile_trading_order(order_id: str) -> OrderResponse:
    return reconcile_order(order_id)


@app.post(
    f"{settings.api_prefix}/trading/execution-batches",
    response_model=ExecutionBatchResponse,
    tags=["trading"],
)
def create_batch(request: CreateExecutionBatchRequest) -> ExecutionBatchResponse:
    return create_execution_batch(request)


@app.get(
    f"{settings.api_prefix}/trading/cross-spread/snapshot",
    response_model=CrossSpreadSnapshotResponse,
    tags=["trading"],
)
def cross_spread_snapshot() -> CrossSpreadSnapshotResponse:
    return get_cross_spread_snapshot()


@app.get(
    f"{settings.api_prefix}/trading/cross-spread/history",
    response_model=list[CrossSpreadHistoryPointResponse],
    tags=["trading"],
)
def cross_spread_history(
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[CrossSpreadHistoryPointResponse]:
    return get_cross_spread_history(limit)


@app.post(
    f"{settings.api_prefix}/trading/cross-spread/market-command",
    response_model=ExecutionBatchResponse,
    tags=["trading"],
)
def cross_spread_market_command(
    request: CrossSpreadMarketCommandRequest,
) -> ExecutionBatchResponse:
    return submit_cross_spread_market_command(request)


@app.post(
    f"{settings.api_prefix}/trading/commands",
    response_model=TradeCommandResponse,
    tags=["trading"],
)
def create_command(request: CreateTradeCommandRequest) -> TradeCommandResponse:
    return create_trade_command(request)


@app.get(
    f"{settings.api_prefix}/trading/commands/{{trade_command_id}}",
    response_model=TradeCommandResponse,
    tags=["trading"],
)
def trade_command(trade_command_id: str) -> TradeCommandResponse:
    return get_trade_command(trade_command_id)


@app.get(
    f"{settings.api_prefix}/trading/orders",
    response_model=list[OrderDetailResponse],
    tags=["trading"],
)
def orders() -> list[OrderDetailResponse]:
    return list_orders()


@app.get(
    f"{settings.api_prefix}/trading/orders/{{order_id}}",
    response_model=OrderDetailResponse,
    tags=["trading"],
)
def order(order_id: str) -> OrderDetailResponse:
    return get_order(order_id)


@app.get(
    f"{settings.api_prefix}/trading/fills",
    response_model=list[FillResponse],
    tags=["trading"],
)
def fills() -> list[FillResponse]:
    return list_fills()


@app.get(
    f"{settings.api_prefix}/trading/execution-batches",
    response_model=list[ExecutionBatchResponse],
    tags=["trading"],
)
def execution_batches(
    strategy_instance_id: str | None = Query(default=None, alias="strategyInstanceId"),
) -> list[ExecutionBatchResponse]:
    return list_execution_batches(strategy_instance_id)


@app.get(
    f"{settings.api_prefix}/trading/execution-batches/{{batch_id}}",
    response_model=ExecutionBatchResponse,
    tags=["trading"],
)
def get_batch(batch_id: str) -> ExecutionBatchResponse:
    return get_execution_batch(batch_id)


@app.get(
    f"{settings.api_prefix}/accounts/{{account_id}}/positions/{{instrument_id}}",
    response_model=PositionResponse,
    tags=["accounts"],
)
def get_position(account_id: str, instrument_id: str) -> PositionResponse:
    with connection() as db:
        row = db.execute(
            """
            SELECT account_id, instrument_id, net_quantity, average_price
            FROM positions
            WHERE account_id = ? AND instrument_id = ?
            """,
            (account_id, instrument_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Position not found")
    return PositionResponse(
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        netQuantity=Decimal(row["net_quantity"]),
        averagePrice=(Decimal(row["average_price"]) if row["average_price"] else None),
    )


@app.get(
    f"{settings.api_prefix}/accounts/{{account_id}}/pnl/{{instrument_id}}",
    response_model=PnlResponse,
    tags=["pnl"],
)
def get_pnl(account_id: str, instrument_id: str) -> PnlResponse:
    with connection() as db:
        row = db.execute(
            """
            SELECT account_id, instrument_id, realized_pnl, trading_pnl, fees
            FROM pnl_results
            WHERE account_id = ? AND instrument_id = ?
            """,
            (account_id, instrument_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="PnL result not found")
    return PnlResponse(
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        realizedPnl=Decimal(row["realized_pnl"]),
        tradingPnl=Decimal(row["trading_pnl"]),
        fees=Decimal(row["fees"]),
    )


@app.get(
    f"{settings.api_prefix}/strategies/instances/{{strategy_instance_id}}/pnl",
    response_model=StrategyPnlResponse,
    tags=["pnl"],
)
def strategy_pnl(strategy_instance_id: str) -> StrategyPnlResponse:
    return get_strategy_pnl(strategy_instance_id)


@app.get(
    f"{settings.api_prefix}/strategies/instances/{{strategy_instance_id}}/nav-snapshots",
    response_model=list[StrategyNavSnapshotResponse],
    tags=["pnl"],
)
def strategy_nav_snapshots(strategy_instance_id: str) -> list[StrategyNavSnapshotResponse]:
    return list_nav_snapshots(strategy_instance_id)


@app.post(
    f"{settings.api_prefix}/strategies/instances/{{strategy_instance_id}}/nav-snapshots/run",
    response_model=StrategyNavSnapshotResponse,
    tags=["pnl"],
)
def run_strategy_nav_snapshot(strategy_instance_id: str) -> StrategyNavSnapshotResponse:
    return run_nav_snapshot(strategy_instance_id)
