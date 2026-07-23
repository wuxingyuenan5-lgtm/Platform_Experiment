from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class SubmitOrderCommand(BaseModel):
    command_id: str
    platform_order_id: str
    account_id: str
    instrument_id: str
    symbol: str = Field(min_length=1)
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"] = "market"
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExecutionEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    command_id: str
    platform_order_id: str
    event_type: Literal["order_acknowledged", "order_filled", "order_rejected"]
    external_order_id: str | None = None
    fill_price: Decimal | None = None
    fill_quantity: Decimal | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reason: str | None = None


class RuntimeStatusResponse(BaseModel):
    status: str
    service: str
    environment: str
    gateway: str
    journal: dict[str, object]


class CredentialInspection(BaseModel):
    credential_ref: str = Field(alias="credentialRef")
    env_prefix: str = Field(alias="envPrefix")
    configured: bool
    available_fields: list[str] = Field(alias="availableFields")
    missing_fields: list[str] = Field(alias="missingFields")


class GatewayConnectivityResponse(BaseModel):
    gateway: str
    credential_count: int = Field(alias="credentialCount")
    configured_credential_count: int = Field(alias="configuredCredentialCount")
    credentials: list[CredentialInspection]


class VenueReadinessResult(BaseModel):
    venue: str
    status: str
    credential_ref: str = Field(alias="credentialRef")
    symbol: str
    market_type: str | None = Field(default=None, alias="marketType")
    checks: list[str] = []
    reason: str | None = None


class VenueReadinessResponse(BaseModel):
    status: str
    venues: list[VenueReadinessResult]


class MarketQuote(BaseModel):
    bid: Decimal
    ask: Decimal
    mid: Decimal
    last: Decimal | None = None
    currency: str


class VenuePosition(BaseModel):
    symbol: str
    side: str
    quantity: Decimal
    average_price: Decimal | None = Field(default=None, alias="averagePrice")
    unrealized_pnl: Decimal | None = Field(default=None, alias="unrealizedPnl")
    external_id: str | None = Field(default=None, alias="externalId")


class CrossSpreadVenueSnapshot(BaseModel):
    venue: str
    symbol: str
    status: str
    quote: MarketQuote | None = None
    positions: list[VenuePosition] = []
    reason: str | None = None


class CrossSpreadMetrics(BaseModel):
    funding_rate: Decimal | None = Field(default=None, alias="fundingRate")
    usdt_usd: Decimal | None = Field(default=None, alias="usdtUsd")
    buyer_inventory_fee: Decimal | None = Field(default=None, alias="buyerInventoryFee")
    seller_inventory_fee: Decimal | None = Field(default=None, alias="sellerInventoryFee")


class CrossSpreadHistoryPoint(BaseModel):
    as_of: datetime = Field(alias="asOf")
    long_spread: Decimal | None = Field(default=None, alias="longSpread")
    short_spread: Decimal | None = Field(default=None, alias="shortSpread")
    bybit_mid: Decimal | None = Field(default=None, alias="bybitMid")
    mt5_mid: Decimal | None = Field(default=None, alias="mt5Mid")


class CrossSpreadSnapshotResponse(BaseModel):
    status: str
    bybit: CrossSpreadVenueSnapshot
    mt5: CrossSpreadVenueSnapshot
    long_spread: Decimal | None = Field(default=None, alias="longSpread")
    short_spread: Decimal | None = Field(default=None, alias="shortSpread")
    metrics: CrossSpreadMetrics = Field(default_factory=CrossSpreadMetrics)
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="asOf")
