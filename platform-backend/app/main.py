from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.database import connection, initialize_database
from app.schemas import CreateOrderRequest, OrderResponse, PnlResponse, PositionResponse
from app.trading import submit_order

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)


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
        "version": "0.2.0",
        "apiVersion": "v1",
    }


@app.post(
    f"{settings.api_prefix}/trading/orders",
    response_model=OrderResponse,
    tags=["trading"],
)
def create_order(request: CreateOrderRequest) -> OrderResponse:
    return submit_order(request)


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
