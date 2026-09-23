from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator


def exact(value):
    if isinstance(value, float):
        raise ValueError("financial values must be decimal strings")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("finite decimal required")
    exponent = result.as_tuple().exponent
    assert isinstance(exponent, int)
    if len(result.as_tuple().digits) > 38 or result.adjusted() >= 20 or exponent < -18:
        raise ValueError("decimal domain is precision 38 / scale 18; no implicit rounding")
    return result


Money = Annotated[Decimal, BeforeValidator(exact)]


class ResearchModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class FundingEvent(ResearchModel):
    at: datetime
    rate: Money
    mark: Money | None = Field(default=None, gt=0)
    kind: Literal["settled", "indicated", "scenario"]
    observedAt: datetime
    markQuality: Literal["exact", "prior_estimate", "missing"] = "missing"
    currency: str = "USDT"


class BorrowProfile(ResearchModel):
    product: Literal["self_funded", "uta_flexible"] = "self_funded"
    liabilityType: Literal["spot", "derivatives"] = "spot"
    currency: str = "USDT"
    vipLevel: str = "scenario"
    principal: Money = Field(default=Decimal("0"), ge=0)
    hourlyRate: Money | None = Field(default=None, ge=0)
    observedAt: datetime | None = None
    effectiveFrom: datetime | None = None
    billingRuleVersion: Literal["bybit-uta-2026-09-03"] = "bybit-uta-2026-09-03"


class SwapEvent(ResearchModel):
    at: datetime
    mode: Literal["points", "currency_profit", "unsupported"]
    longRate: Money | None = None
    shortRate: Money | None = None
    point: Money | None = Field(default=None, gt=0)
    contractSize: Money = Field(gt=0)
    rolloverMultiplier: int = Field(ge=0, le=3)
    currency: str
    effectiveFrom: datetime
    observedAt: datetime


class Scenario(ResearchModel):
    pairId: Literal["cross-gold", "funding-btc"]
    direction: Literal["buy_spread", "sell_spread"]
    quantity: Money = Field(gt=0, le=1000000)
    entrySpread: Money
    exitSpread: Money
    openedAt: datetime
    closedAt: datetime
    currency: Literal["USD", "USDT"] = "USDT"
    fxAssumption: Literal["explicit_1_to_1", "same_currency"] = "same_currency"
    tradingFees: Money | None = Field(default=None, ge=0)
    additionalExecutionCost: Money | None = Field(default=None, ge=0)
    costProfileId: str = Field(min_length=1, max_length=120)
    funding: list[FundingEvent] = Field(default_factory=list, max_length=1000)
    fundingCoverage: Literal["complete", "scenario", "unknown"] = "unknown"
    borrow: BorrowProfile = Field(default_factory=BorrowProfile)
    swap: list[SwapEvent] = Field(default_factory=list, max_length=1000)
    swapCoverage: Literal["not_applicable", "complete", "scenario", "unknown"] = "unknown"
    ownCapital: Money | None = Field(default=None, gt=0)

    @field_validator("openedAt", "closedAt")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("timezone required")
        return value

    @model_validator(mode="after")
    def valid_window(self):
        if self.closedAt < self.openedAt or (self.closedAt - self.openedAt).days > 366:
            raise ValueError("invalid holding window")
        if self.pairId == "cross-gold" and self.fxAssumption != "explicit_1_to_1":
            raise ValueError(
                "cross USD/USDT requires explicit 1:1 scenario; no observed FX supplied"
            )
        for event in [*self.funding, *self.swap]:
            if event.at.tzinfo is None or event.observedAt.tzinfo is None:
                raise ValueError("event timezone required")
        currencies = [e.currency for e in self.funding] + [e.currency for e in self.swap]
        if self.borrow.product != "self_funded":
            currencies.append(self.borrow.currency)
        for currency in currencies:
            if currency != self.currency and not (
                self.fxAssumption == "explicit_1_to_1"
                and {currency, self.currency} <= {"USD", "USDT"}
            ):
                raise ValueError("cashflow currency requires an explicit conversion")
        for stamp in [
            self.borrow.observedAt,
            self.borrow.effectiveFrom,
            *[e.effectiveFrom for e in self.swap],
        ]:
            if stamp is not None and stamp.tzinfo is None:
                raise ValueError("effective and observed times require timezone")
        return self


class Experiment(ResearchModel):
    pairId: Literal["cross-gold", "funding-btc"]
    direction: Literal["buy_spread", "sell_spread"]
    quantity: Money = Field(gt=0, le=1000000)
    entryThreshold: Money
    exitTarget: Money
    riskPnl: Money | None = Field(default=None, lt=0)
    maxHoldingSeconds: int = Field(ge=1, le=604800)
    from_: datetime = Field(alias="from")
    to: datetime
    cutoff: datetime
    validationFrom: datetime
    clockBasis: Literal["observed"] = "observed"
    qualityProfileId: Literal["research-quality.v2"] = "research-quality.v2"
    costProfile: Scenario
    entryThresholds: list[Money] = Field(default_factory=list, max_length=5)
    exitTargets: list[Money] = Field(default_factory=list, max_length=5)
    latencyMs: list[int] = Field(default=[0, 100, 250, 500, 1000], max_length=5)
    quantities: list[Money] = Field(default_factory=list, max_length=5)
    holdingSeconds: list[int] = Field(default=[300, 900, 3600, 14400], max_length=8)
    maxQuoteAgeMs: int = Field(default=2000, ge=1, le=60000)
    mt5SlippagePerUnit: Money | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def limits(self):
        stamps = (self.from_, self.to, self.cutoff, self.validationFrom)
        if any(t.tzinfo is None for t in stamps):
            raise ValueError("timezone required")
        if not self.from_ < self.validationFrom < self.to <= self.cutoff:
            raise ValueError("require from < validationFrom < to <= cutoff")
        if (self.cutoff - self.from_).days > 31:
            raise ValueError("maximum research window is 31 days")
        if any(x < 0 or x > 60000 for x in self.latencyMs):
            raise ValueError("latency budget")
        if any(x <= 0 or x > 1000000 for x in self.quantities):
            raise ValueError("quantity budget")
        if any(x <= 0 or x > 604800 for x in self.holdingSeconds):
            raise ValueError("holding budget")
        if self.costProfile.pairId != self.pairId or self.costProfile.direction != self.direction:
            raise ValueError("cost profile context mismatch")
        return self


class DraftRequest(ResearchModel):
    pairId: Literal["cross-gold", "funding-btc"]
    direction: Literal["buy_spread", "sell_spread"]
    quantity: Money = Field(gt=0)
    entryThreshold: Money
    exitTarget: Money
    methodVersion: Literal["experiment.v1"]
    costProfileId: str = Field(min_length=1, max_length=120)
