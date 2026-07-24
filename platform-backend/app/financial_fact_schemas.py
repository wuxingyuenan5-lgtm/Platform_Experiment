from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

FinancialFactType = Literal[
    "external_order",
    "trade_fill",
    "deal",
    "funding",
    "swap",
    "fee",
    "balance",
    "position",
    "fx",
]
TRADE_FACT_TYPES = {"trade_fill", "deal"}


class CreateFinancialFactRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    fact_type: FinancialFactType = Field(alias="factType")
    source: str = Field(min_length=1, max_length=64)
    external_id: str = Field(alias="externalId", min_length=1, max_length=128)
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str | None = Field(default=None, alias="accountId")
    instrument_id: str | None = Field(default=None, alias="instrumentId")
    side: Literal["buy", "sell"] | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    amount: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=16)
    available_balance: Decimal | None = Field(default=None, alias="availableBalance")
    fx_rate_to_base: Decimal | None = Field(default=None, alias="fxRateToBase", gt=0)
    occurred_at: datetime = Field(alias="occurredAt")
    payload: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_fact_shape(self) -> "CreateFinancialFactRequest":
        if self.fact_type in TRADE_FACT_TYPES:
            if (
                self.account_id is None
                or self.instrument_id is None
                or self.side is None
                or self.quantity is None
                or self.price is None
            ):
                raise ValueError(
                    "Trade facts require account, instrument, side, quantity and price"
                )
        elif self.fact_type in {"funding", "swap", "fee", "fx"}:
            if self.account_id is None or self.instrument_id is None:
                raise ValueError("PnL component facts require account and instrument")
            if self.amount is None or self.currency is None:
                raise ValueError("PnL component facts require amount and currency")
        elif self.fact_type == "balance":
            if self.account_id is None or self.amount is None or self.currency is None:
                raise ValueError("Balance facts require account, amount and currency")
        elif self.fact_type in {"external_order", "position"}:
            if self.account_id is None or self.instrument_id is None:
                raise ValueError("Order and position facts require account and instrument")
        return self


class FinancialFactResponse(BaseModel):
    fact_id: str = Field(alias="factId")
    idempotency_key: str = Field(alias="idempotencyKey")
    fact_type: FinancialFactType = Field(alias="factType")
    source: str
    external_id: str = Field(alias="externalId")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str | None = Field(default=None, alias="accountId")
    instrument_id: str | None = Field(default=None, alias="instrumentId")
    side: str | None = None
    quantity: Decimal | None = None
    quantity_unit: str | None = Field(default=None, alias="quantityUnit")
    price: Decimal | None = None
    contract_multiplier: Decimal | None = Field(default=None, alias="contractMultiplier")
    amount: Decimal | None = None
    currency: str | None = None
    base_currency: str = Field(alias="baseCurrency")
    fx_rate_to_base: Decimal | None = Field(default=None, alias="fxRateToBase")
    converted_amount: Decimal | None = Field(default=None, alias="convertedAmount")
    available_balance: Decimal | None = Field(default=None, alias="availableBalance")
    occurred_at: datetime = Field(alias="occurredAt")
    data_quality_state: str = Field(alias="dataQualityState")
    created_at: datetime = Field(alias="createdAt")


class FormalPositionResponse(BaseModel):
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    net_quantity: Decimal = Field(alias="netQuantity")
    average_price: Decimal | None = Field(default=None, alias="averagePrice")
    quantity_unit: str = Field(alias="quantityUnit")
    data_quality_state: str = Field(alias="dataQualityState")
    updated_at: datetime = Field(alias="updatedAt")


class FormalPnlResponse(BaseModel):
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    currency: str
    trading_pnl: Decimal = Field(alias="tradingPnl")
    funding_pnl: Decimal = Field(alias="fundingPnl")
    swap_pnl: Decimal = Field(alias="swapPnl")
    fee_pnl: Decimal = Field(alias="feePnl")
    fx_pnl: Decimal = Field(alias="fxPnl")
    total_pnl: Decimal = Field(alias="totalPnl")
    fact_count: int = Field(alias="factCount")
    data_quality_state: str = Field(alias="dataQualityState")
    updated_at: datetime = Field(alias="updatedAt")


class FormalNavSnapshotResponse(BaseModel):
    snapshot_id: str = Field(alias="snapshotId")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    valuation_time: datetime = Field(alias="valuationTime")
    equity: Decimal | None = None
    capital_base: Decimal = Field(alias="capitalBase")
    nav: Decimal | None = None
    currency: str
    data_quality_state: str = Field(alias="dataQualityState")
    required_account_count: int = Field(alias="requiredAccountCount")
    included_account_count: int = Field(alias="includedAccountCount")
    missing_account_ids: list[str] = Field(alias="missingAccountIds")
    created_at: datetime = Field(alias="createdAt")


class FinancialProjectionRebuildResponse(BaseModel):
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    rebuilt_pair_count: int = Field(alias="rebuiltPairCount")
    fact_count: int = Field(alias="factCount")
    completed_at: datetime = Field(alias="completedAt")


__all__ = [
    "CreateFinancialFactRequest",
    "FinancialFactResponse",
    "FinancialFactType",
    "FinancialProjectionRebuildResponse",
    "FormalNavSnapshotResponse",
    "FormalPnlResponse",
    "FormalPositionResponse",
    "TRADE_FACT_TYPES",
]
