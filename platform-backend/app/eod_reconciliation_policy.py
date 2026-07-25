from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from app.eod_reconciliation_schemas import ReportStatus, ReviewDecision, ScaleGateStatus


class EodReviewConflictError(RuntimeError):
    pass


class EodReviewNotEligibleError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReportDisposition:
    status: ReportStatus
    scale_gate_status: ScaleGateStatus


@dataclass(frozen=True)
class ReviewDisposition:
    changed: bool
    scale_gate_status: ScaleGateStatus
