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


class AShareLiveSectorFundFlow(ResearchApiModel):
    sector_code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    return_pct: Decimal | None = None
    net_inflow_yuan: Decimal
    inflow_yuan: Decimal = Field(ge=0)
    outflow_yuan: Decimal = Field(ge=0)
    firm_count: int | None = Field(default=None, ge=0)


class AShareLiveSectorFundFlowResponse(ResearchApiModel):
    fetched_at: datetime
    source: str = Field(min_length=1, max_length=128)
    status: ResearchDataStatus = "ready"
    is_stale: bool = False
    message: str | None = None
    rows: list[AShareLiveSectorFundFlow]


class AShareMarketTurnoverRow(ResearchApiModel):
    security_code: str = Field(pattern=r"^\d{6}$")
    security_name: str = Field(min_length=1, max_length=128)
    price: Decimal | None = None
    return_pct: Decimal | None = None
    turnover_yuan: Decimal = Field(ge=0)
    market_cap_yuan: Decimal | None = Field(default=None, ge=0)
    industry: str | None = Field(default=None, max_length=128)


class AShareMarketTurnoverResponse(ResearchApiModel):
    fetched_at: datetime
    source: str = Field(min_length=1, max_length=128)
    status: ResearchDataStatus = "ready"
    is_stale: bool = False
    message: str | None = None
    daily_observed_at: str | None = None
    high_turnover_count: int | None = Field(default=None, ge=0)
    high_turnover_rows: list[AShareMarketTurnoverRow] = Field(default_factory=list)
    history_dates: list[str] = Field(default_factory=list)
    history_counts: list[int] = Field(default_factory=list)
    history_industries: list[dict[str, Any]] = Field(default_factory=list)
    historical_rows: list[dict[str, Any]] = Field(default_factory=list)
    rows: list[AShareMarketTurnoverRow]


class AShareTurnoverStock(ResearchApiModel):
    currency: Literal["CNY", "HKD"] = "CNY"
    # The A-share core universe is six digits; the user-maintained research
    # pool also contains five-digit HK listings, which share the same read-only
    # quote/history workflow.
    security_code: str = Field(pattern=r"^\d{5,6}$")
    security_name: str = Field(min_length=1, max_length=128)
    turnover_yuan: Decimal = Field(ge=0)
    return_pct: Decimal | None = None
    net_inflow_yuan: Decimal | None = None
    observed_at: datetime | None = None
    price: Decimal | None = Field(default=None, ge=0)
    turnover_pct: Decimal | None = None
    market_cap_yuan: Decimal | None = Field(default=None, ge=0)
    pe_ttm: Decimal | None = None
    pb: Decimal | None = None


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
    sw2_all: list[ShenwanLevel2Aggregate]
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
    history: list[AShareIndexHistoryPoint] = Field(default_factory=list)


class AShareIndexHistoryPoint(ResearchApiModel):
    observed_at: date
    close: Decimal = Field(gt=0)
    turnover_yuan: Decimal | None = Field(default=None, ge=0)


class AShareBreadthSnapshot(ResearchApiModel):
    total_amount_yuan: Decimal | None = Field(default=None, ge=0)
    up: int = Field(ge=0)
    down: int = Field(ge=0)
    flat: int = Field(ge=0)
    limit_up: int | None = Field(default=None, ge=0)
    real_limit_up: int | None = Field(default=None, ge=0)
    limit_down: int | None = Field(default=None, ge=0)
    real_limit_down: int | None = Field(default=None, ge=0)
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


class AShareMarketHistoryRow(ResearchApiModel):
    observed_at: date
    source: str | None = None
    up: int | None = Field(default=None, ge=0)
    down: int | None = Field(default=None, ge=0)
    flat: int | None = Field(default=None, ge=0)
    limit_up: int | None = Field(default=None, ge=0)
    limit_down: int | None = Field(default=None, ge=0)
    total_amount_yuan: Decimal | None = Field(default=None, ge=0)
    amount_change_pct: Decimal | None = None
    market_breadth_pct: Decimal | None = None


class AShareDashboardResponse(ResearchApiModel):
    generated_at: datetime
    market_detail: ResearchModuleResult
    breadth: ResearchModuleResult
    shenwan: ResearchModuleResult
    emotion: ResearchModuleResult
    crowding: ResearchModuleResult | None = None
    market_history: list[AShareMarketHistoryRow] = Field(default_factory=list)


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
