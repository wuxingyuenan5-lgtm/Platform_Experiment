from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, model_validator

ReportStatus = Literal[
    "complete",
    "completed_with_differences",
    "partial",
    "failed",
]
ScaleGateStatus = Literal[
    "blocked",
    "eligible_for_review",
    "approved_same_limits",
    "needs_remediation",
    "rejected",
]
ReviewDecision = Literal["approved_same_limits", "needs_remediation", "rejected"]


class EodReconciliationReportRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    business_date: date = Field(alias="businessDate")
    timezone: str = Field(min_length=1, max_length=128)
    valuation_time: datetime = Field(alias="valuationTime")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    actor: str = Field(min_length=1, max_length=128)
    owner: str = Field(min_length=1, max_length=128)
    due_at: datetime = Field(alias="dueAt")

    @model_validator(mode="after")
    def validate_time_contract(self) -> "EodReconciliationReportRequest":
        if self.valuation_time.tzinfo is None or self.due_at.tzinfo is None:
            raise ValueError("valuationTime and dueAt must include a timezone")
        try:
            timezone = ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone must be a valid IANA timezone") from exc
        local_business_date = self.valuation_time.astimezone(timezone).date()
        if local_business_date != self.business_date:
            raise ValueError("businessDate must match valuationTime in the configured timezone")
        return self


class EodReconciliationReviewRequest(BaseModel):
    decision: ReviewDecision
    reviewer: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)


class EodReconciliationReportResponse(BaseModel):
    report_id: str = Field(alias="reportId")
    idempotency_key: str = Field(alias="idempotencyKey")
    attempt: int
    business_date: date = Field(alias="businessDate")
    timezone: str
    valuation_time: datetime = Field(alias="valuationTime")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    actor: str
    owner: str
    due_at: datetime = Field(alias="dueAt")
    status: ReportStatus
    sla_status: str = Field(alias="slaStatus")
    scale_gate_status: ScaleGateStatus = Field(alias="scaleGateStatus")
    order_reconciliation_count: int = Field(alias="orderReconciliationCount")
    account_reconciliation_run_id: str | None = Field(
        default=None,
        alias="accountReconciliationRunId",
    )
    economic_event_import_id: str | None = Field(
        default=None,
        alias="economicEventImportId",
    )
    nav_snapshot_id: str | None = Field(default=None, alias="navSnapshotId")
    formal_pnl_count: int = Field(alias="formalPnlCount")
    formal_pnl_incomplete_count: int = Field(alias="formalPnlIncompleteCount")
    open_difference_count: int = Field(alias="openDifferenceCount")
    resolved_difference_count: int = Field(alias="resolvedDifferenceCount")
    accepted_difference_count: int = Field(alias="acceptedDifferenceCount")
    skipped_external_ids: list[str] = Field(alias="skippedExternalIds")
    missing_account_ids: list[str] = Field(alias="missingAccountIds")
    errors: list[str]
    reviewer: str | None = None
    review_decision: ReviewDecision | None = Field(default=None, alias="reviewDecision")
    review_reason: str | None = Field(default=None, alias="reviewReason")
    reviewed_at: datetime | None = Field(default=None, alias="reviewedAt")
    created_at: datetime = Field(alias="createdAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")
