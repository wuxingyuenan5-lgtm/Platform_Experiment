"""Typed projections of existing financial reads; native event fields remain intact."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class NativeFinancialRead(BaseModel):
    model_config = ConfigDict(
        extra="allow", allow_inf_nan=False, json_schema_serialization_defaults_required=True
    )


class FinancialAmountsResponse(NativeFinancialRead):
    currency: str
    accountId: str = ""
    realizedPnl: Decimal | None
    tradingPnl: Decimal | None
    fees: Decimal | None
    fundingPnl: Decimal | None = None
    swapPnl: Decimal | None = None
    netPnl: Decimal | None = None


class FinancialTimelinePointResponse(NativeFinancialRead):
    asOf: str
    accountId: str
    currency: str
    realizedPnl: Decimal


class FinancialCoverageResponse(NativeFinancialRead):
    accountId: str
    historyStart: str | None = None
    historyEnd: str | None = None
    asOf: str


class EconomicEventResponse(NativeFinancialRead):
    externalEventId: str
    eventType: str
    symbol: str | None = None
    amount: Decimal
    currency: str
    occurredAt: str
    accountId: str | None = None
    source: str | None = None
    orderId: str | None = None
    externalOrderId: str | None = None
    instructionId: str | None = None
    batchId: str | None = None


class CoinBalanceResponse(NativeFinancialRead):
    currency: str
    equity: Decimal
    walletBalance: Decimal | None = None
    availableBalance: Decimal | None = None
    usdValue: Decimal | None = None


class AssetCategoryResponse(NativeFinancialRead):
    category: str
    equity: Decimal | None = None


class AssetBreakdownResponse(NativeFinancialRead):
    accountType: str
    valuationCurrency: str | None = None
    totalEquity: Decimal | None = None
    categories: list[AssetCategoryResponse] = []
