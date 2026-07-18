from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class CreateOrderRequest(BaseModel):
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    symbol: str
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"] = Field(alias="orderType")
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = Field(default=None, gt=0)


class OrderResponse(BaseModel):
    order_id: str = Field(alias="orderId")
    command_id: str = Field(alias="commandId")
    status: str
    external_order_id: str | None = Field(default=None, alias="externalOrderId")


class PositionResponse(BaseModel):
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    net_quantity: Decimal = Field(alias="netQuantity")
    average_price: Decimal | None = Field(alias="averagePrice")


class PnlResponse(BaseModel):
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    realized_pnl: Decimal = Field(alias="realizedPnl")
    trading_pnl: Decimal = Field(alias="tradingPnl")
    fees: Decimal
