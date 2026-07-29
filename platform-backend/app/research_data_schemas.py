from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ResearchDataStatus = Literal["loading", "ready", "partial", "no_data", "stale", "error"]
StrictThresholdOperator = Literal[">"]


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail)


class ResearchApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class ResearchSourceMeta(ResearchApiModel):
    source: str = Field(min_length=1, max_length=128)
    source_timestamp: datetime | None = None
    fetched_at: datetime
    status: ResearchDataStatus
    is_stale: bool = False
    error_code: str | None = Field(default=None, max_length=128)
    message: str | None = Field(default=None, max_length=512)

    @field_validator("source_timestamp", "fetched_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("research timestamps must include a timezone")
        return value


class ResearchModuleResult(ResearchApiModel):
    meta: ResearchSourceMeta
    data: Any = None


class AShareTurnoverStock(ResearchApiModel):
    security_code: str = Field(pattern=r"^\d{6}$")
    security_name: str = Field(min_length=1, max_length=128)
    turnover_yuan: Decimal = Field(ge=0)
    return_pct: Decimal | None = None
    net_inflow_yuan: Decimal | None = None


class ShenwanMembership(ResearchApiModel):
    security_code: str = Field(pattern=r"^\d{6}$")
    sw_l1_code: str = Field(min_length=1, max_length=32)
    sw_l1_name: str = Field(min_length=1, max_length=128)
    sw_l2_code: str = Field(min_length=1, max_length=32)
    sw_l2_name: str = Field(min_length=1, max_length=128)
    classification_version: str = Field(min_length=1, max_length=64)
    effective_from: date
    effective_to: date | None = None


class ShenwanLevel2Aggregate(ResearchApiModel):
    rank: int = Field(ge=1)
    sw_l1_code: str
    sw_l1_name: str
    sw_l2_code: str
    sw_l2_name: str
    return_pct: Decimal | None = None
    turnover_yuan: Decimal = Field(ge=0)
    market_share_pct: Decimal = Field(ge=0)
    net_inflow_yuan: Decimal | None = None


class TurnoverThresholdIndustryCount(ResearchApiModel):
    sw_l1_code: str
    sw_l1_name: str
    sw_l2_code: str
    sw_l2_name: str
    stock_count: int = Field(ge=1)


class TurnoverThresholdStock(ResearchApiModel):
    security_code: str
    security_name: str
    sw_l1_code: str
    sw_l1_name: str
    sw_l2_code: str
    sw_l2_name: str
    turnover_yuan: Decimal = Field(ge=0)
    return_pct: Decimal | None = None


class TurnoverThresholdResult(ResearchApiModel):
    threshold_yuan: Decimal = Field(gt=0)
    operator: StrictThresholdOperator = ">"
    industries: list[TurnoverThresholdIndustryCount]
    stocks: list[TurnoverThresholdStock]
    unmatched_security_codes: list[str]


class AShareResearchAggregation(ResearchApiModel):
    sw2_top: list[ShenwanLevel2Aggregate]
    threshold: TurnoverThresholdResult
    unmatched_security_codes: list[str]


class AShareIndexSnapshot(ResearchApiModel):
    code: str
    name: str
    source_symbol: str
    close: Decimal | None = None
    turnover_yuan: Decimal | None = None
    volatility_20_pct: Decimal | None = None
    return_1d_pct: Decimal | None = None
    return_ytd_pct: Decimal | None = None
    return_qtd_pct: Decimal | None = None
    return_1w_pct: Decimal | None = None
    return_1m_pct: Decimal | None = None
    return_1y_pct: Decimal | None = None
    distance_52w_high_pct: Decimal | None = None
    signal_1h: str | None = None
    signal_daily: str | None = None
    signal_3d: str | None = None
    signal_weekly: str | None = None
    spark: list[Decimal] = Field(default_factory=list)


class AShareBreadthSnapshot(ResearchApiModel):
    up: int = Field(ge=0)
    down: int = Field(ge=0)
    flat: int = Field(ge=0)
    limit_up: int = Field(ge=0)
    real_limit_up: int = Field(ge=0)
    limit_down: int = Field(ge=0)
    real_limit_down: int = Field(ge=0)
    activity_pct: Decimal | None = None
    breadth_state: str
    speculation_state: str
    trade_date: date | None = None


class EmotionLadderRow(ResearchApiModel):
    board_count: str
    stock_count: int = Field(ge=0)


class EmotionStockRow(ResearchApiModel):
    security_code: str
    security_name: str
    board_count: int = Field(ge=1)
    turnover_yuan: Decimal | None = None


class ShortTermEmotionSnapshot(ResearchApiModel):
    limit_up_count: int = Field(ge=0)
    broken_board_count: int = Field(ge=0)
    limit_down_count: int = Field(ge=0)
    highest_board_count: int = Field(ge=0)
    consecutive_board_count: int = Field(ge=0)
    seal_rate_pct: Decimal | None = None
    break_rate_pct: Decimal | None = None
    promotion_rate_pct: Decimal | None = None
    ladder: list[EmotionLadderRow]
    leaders: list[EmotionStockRow]
    trade_date: date | None = None


class AShareDashboardResponse(ResearchApiModel):
    generated_at: datetime
    market_detail: ResearchModuleResult
    breadth: ResearchModuleResult
    shenwan: ResearchModuleResult
    emotion: ResearchModuleResult


class StockSnapshotResponse(ResearchApiModel):
    security_code: str
    security_name: str | None = None
    generated_at: datetime
    completeness_pct: Decimal = Field(ge=0, le=100)
    modules: dict[str, ResearchModuleResult]


class MacroProbabilityPoint(ResearchApiModel):
    observed_at: datetime
    probability_pct: Decimal = Field(ge=0, le=100)


class MacroExpectationEvent(ResearchApiModel):
    event_id: str
    category: Literal["monetary_policy", "macro", "geopolitics", "election"]
    title: str
    outcome: str
    current_probability_pct: Decimal = Field(ge=0, le=100)
    change_1d_pct_points: Decimal | None = None
    change_7d_pct_points: Decimal | None = None
    liquidity_label: str | None = None
    expiry_at: datetime | None = None
    source_url: str | None = None
    history: list[MacroProbabilityPoint] = Field(default_factory=list)


class MacroExpectationResponse(ResearchApiModel):
    generated_at: datetime
    events: ResearchModuleResult
