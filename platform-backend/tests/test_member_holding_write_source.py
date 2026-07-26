from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.member_holding_schemas import UpsertFundNavRequest, UpsertMemberHoldingRequest


@pytest.mark.unit
def test_holding_write_request_only_accepts_manual_admin_source() -> None:
    accepted = UpsertMemberHoldingRequest.model_validate(
        {
            "shareQuantity": "1250.50",
            "cumulativeInvested": "100000",
            "asOf": datetime(2026, 7, 26, tzinfo=UTC),
            "source": "manual_admin",
        }
    )
    assert accepted.source == "manual_admin"

    for forbidden in ("migration", "external_import"):
        with pytest.raises(ValidationError):
            UpsertMemberHoldingRequest.model_validate(
                {
                    "shareQuantity": "1250.50",
                    "cumulativeInvested": "100000",
                    "asOf": datetime(2026, 7, 26, tzinfo=UTC),
                    "source": forbidden,
                }
            )


@pytest.mark.unit
def test_nav_write_request_only_accepts_manual_admin_source() -> None:
    accepted = UpsertFundNavRequest.model_validate(
        {
            "unitNav": "1.0235",
            "valuationTime": datetime(2026, 7, 26, tzinfo=UTC),
            "currency": "cny",
            "source": "manual_admin",
        }
    )
    assert accepted.source == "manual_admin"
    assert accepted.currency == "CNY"

    for forbidden in ("migration", "external_import"):
        with pytest.raises(ValidationError):
            UpsertFundNavRequest.model_validate(
                {
                    "unitNav": "1.0235",
                    "valuationTime": datetime(2026, 7, 26, tzinfo=UTC),
                    "currency": "CNY",
                    "source": forbidden,
                }
            )
