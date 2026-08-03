from decimal import Decimal

from fastapi import HTTPException

from app.account_read_repository import get_pnl_row, get_position_row
from app.schemas import PnlResponse, PositionResponse


def get_position(account_id: str, instrument_id: str) -> PositionResponse:
    row = get_position_row(account_id, instrument_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Position not found")
    return PositionResponse(
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        netQuantity=Decimal(row["net_quantity"]),
        averagePrice=Decimal(row["average_price"]) if row["average_price"] else None,
    )


def get_pnl(account_id: str, instrument_id: str) -> PnlResponse:
    row = get_pnl_row(account_id, instrument_id)
    if row is None:
        raise HTTPException(status_code=404, detail="PnL result not found")
    return PnlResponse(
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        realizedPnl=Decimal(row["realized_pnl"]),
        tradingPnl=Decimal(row["trading_pnl"]),
        fees=Decimal(row["fees"]),
    )
