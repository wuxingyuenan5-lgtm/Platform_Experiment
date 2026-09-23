"""Named wire models shared by generated browser types and response validation."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OpenModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class SourceState(OpenModel):
    status: str | None = None
    reason: str | None = None
    clock: str | None = None
    lastReceivedAt: str | None = None
    lastReadAt: str | None = None
    rttNs: str | None = None


class CaptureState(OpenModel):
    status: str | None = None
    error: str | None = None
    runtime: "CaptureState | None" = None
    sources: dict[str, SourceState] = Field(default_factory=dict)
    lastDurableAt: str | None = None
    lastReceivedAt: str | None = None


class OHLC(BaseModel):
    open: str
    high: str
    low: str
    close: str


class FundingPayload(OpenModel):
    symbol: str | None = None
    fundingRate: str | None = None
    markPrice: str | None = None
    nextFundingTime: str | None = None
    fundingRateTimestamp: str | None = None


class HistoricalCandle(OpenModel):
    symbol: str
    category: str
    priceType: str
    sourceTimeMs: str
    closeTimeMs: str
    intervalMs: str
    close: str
    receivedAt: str


class ResearchRow(OpenModel):
    timeMs: str = ""
    receivedAt: str | None = None
    stream: str | None = None
    payload: FundingPayload = Field(default_factory=FundingPayload)
    validDurationMs: int = 0
    ohlc: dict[str, OHLC] = Field(default_factory=dict)


class EventOutcome(OpenModel):
    id: str
    entryAt: str | None = None
    exitReason: str
    netPnl: str | None = None
    priceMAE: str | None = None
    priceMFE: str | None = None


class OutcomeSummary(OpenModel):
    independentEvents: int
    netSampleCount: int
    netP50: str | None = None
    unknownRatio: str | None = None


class MatrixCell(OpenModel):
    entry: str
    target: str
    summary: OutcomeSummary
    events: list[EventOutcome]


class HoldingPoint(OpenModel):
    seconds: int
    entryCohortCount: int
    sampleCount: int
    unknownCount: int
    p10: str | None = None
    p50: str | None = None
    p90: str | None = None


class ScenarioSummary(OpenModel):
    latencyMs: int | None = None
    quantity: str | None = None
    summary: OutcomeSummary


class ExperimentResult(OpenModel):
    summary: OutcomeSummary
    events: list[EventOutcome]
    matrix: list[MatrixCell]
    holdingCurve: list[HoldingPoint]
    latencyScenarios: list[ScenarioSummary]
    quantityScenarios: list[ScenarioSummary]
    sampleOutOfTraining: OutcomeSummary


class ResearchData(OpenModel):
    board: dict[str, Any] | None = None
    fundingChart: dict[str, Any] | None = None
    borrowObservations: list[dict[str, str]] = Field(default_factory=list)
    chartSeries: list[dict[str, Any]] = Field(default_factory=list)
    emptyReason: str | None = None
    projection: dict[str, Any] | None = None
    sourcePriceCount: int | None = None
    displayIntervalMs: str | None = None
    brokerHistory: list[ResearchRow] = Field(default_factory=list)
    prices: list[HistoricalCandle] = Field(default_factory=list)
    settlements: list[ResearchRow] = Field(default_factory=list)
    quality: list[str] = Field(default_factory=list)
    consumer: CaptureState | None = None
    runtime: CaptureState | None = None
    bytes: str | None = None
    parts: int | None = None
    backup: str | None = None
    calendarCoverage: str | None = None
    rows: list[ResearchRow] = Field(default_factory=list)
    history: list[ResearchRow] = Field(default_factory=list)
    distribution: dict[str, Any] | None = None
    netPnl: str | None = None
    breakEvenExitSpread: str | None = None
    pricePnl: str | None = None
    fundingCash: str | None = None
    borrowCash: str | None = None
    swapCash: str | None = None
    run_id: str | None = None
    id: str | None = None
    result: ExperimentResult | None = None
    parameters: dict[str, Any] | None = None
    projectedBytesPerDay: str | None = None
    diskFreeBytes: str | None = None


class ResearchResponse(BaseModel):
    source: str
    observedAt: str | None = None
    receivedAt: str | None = None
    publishedThrough: str | None = None
    status: str
    stale: bool
    coverage: dict[str, Any]
    clockBasis: str
    methodVersion: str
    parameterHash: str | None = None
    dataVersion: str | None = None
    warnings: list[str]
    data: ResearchData | None = None
