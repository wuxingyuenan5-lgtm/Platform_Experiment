import hashlib
import json

import pytest
from pydantic import ValidationError

from app import eod_reconciliation as compatibility
from app import eod_reconciliation_schemas as schemas

SCHEMA_SHA256 = "3a4f1a3d7d96930b53065b579ca67a584d7c8c8a6df5fc4ba846ae68bfce7beb"


def canonical_schema_hash() -> str:
    payload = {
        model.__name__: model.model_json_schema(by_alias=True)
        for model in (
            schemas.EodReconciliationReportRequest,
            schemas.EodReconciliationReviewRequest,
            schemas.EodReconciliationReportResponse,
        )
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def valid_report_payload() -> dict[str, str]:
    return {
        "idempotencyKey": "eod-schema-001",
        "businessDate": "2026-07-23",
        "timezone": "Asia/Shanghai",
        "valuationTime": "2026-07-23T23:59:00+08:00",
        "strategyInstanceId": "strategy-1",
        "accountId": "account-1",
        "actor": "eod-runner",
        "owner": "operations-owner",
        "dueAt": "2026-07-24T23:59:00+08:00",
    }


def test_compatibility_exports_are_identical_schema_objects() -> None:
    assert compatibility.ReportStatus is schemas.ReportStatus
    assert compatibility.ScaleGateStatus is schemas.ScaleGateStatus
    assert compatibility.ReviewDecision is schemas.ReviewDecision
    assert compatibility.EodReconciliationReportRequest is schemas.EodReconciliationReportRequest
    assert compatibility.EodReconciliationReviewRequest is schemas.EodReconciliationReviewRequest
    assert compatibility.EodReconciliationReportResponse is schemas.EodReconciliationReportResponse


def test_public_schema_snapshot_is_exact() -> None:
    assert canonical_schema_hash() == SCHEMA_SHA256


def test_report_request_preserves_timezone_validation_messages() -> None:
    schemas.EodReconciliationReportRequest.model_validate(valid_report_payload())

    with pytest.raises(ValidationError, match="valuationTime and dueAt must include a timezone"):
        schemas.EodReconciliationReportRequest.model_validate(
            {
                **valid_report_payload(),
                "valuationTime": "2026-07-23T23:59:00",
            }
        )

    with pytest.raises(ValidationError, match="timezone must be a valid IANA timezone"):
        schemas.EodReconciliationReportRequest.model_validate(
            {**valid_report_payload(), "timezone": "Invalid/Timezone"}
        )

    with pytest.raises(
        ValidationError,
        match="businessDate must match valuationTime in the configured timezone",
    ):
        schemas.EodReconciliationReportRequest.model_validate(
            {**valid_report_payload(), "businessDate": "2026-07-22"}
        )


def test_review_decision_values_remain_exact() -> None:
    accepted = schemas.EodReconciliationReviewRequest(
        decision="approved_same_limits",
        reviewer="risk-reviewer",
        reason="clean report",
    )
    assert accepted.decision == "approved_same_limits"

    with pytest.raises(ValidationError):
        schemas.EodReconciliationReviewRequest(
            decision="raise_limits",
            reviewer="risk-reviewer",
            reason="not an allowed decision",
        )
