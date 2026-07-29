from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.member_holding_schemas import (
    UpsertFundNavRequest,
    UpsertMemberHoldingRequest,
)


@pytest.mark.unit
@pytest.mark.parametrize("source", ["migration", "external_import"])
def test_browser_holding_request_cannot_claim_import_source(source: str) -> None:
    with pytest.raises(ValidationError):
        UpsertMemberHoldingRequest(
            shareQuantity="10",
            cumulativeInvested="100",
            asOf=datetime.now(UTC),
            source=source,
            status="active",
        )


@pytest.mark.unit
@pytest.mark.parametrize("source", ["migration", "external_import"])
def test_browser_nav_request_cannot_claim_import_source(source: str) -> None:
    with pytest.raises(ValidationError):
        UpsertFundNavRequest(
            unitNav="1.25",
            valuationTime=datetime.now(UTC),
            currency="USDT",
            source=source,
        )


@pytest.mark.unit
def test_manual_admin_remains_the_only_browser_write_source() -> None:
    holding = UpsertMemberHoldingRequest(
        shareQuantity="10",
        cumulativeInvested="100",
        asOf=datetime.now(UTC),
        source="manual_admin",
        status="active",
    )
    nav = UpsertFundNavRequest(
        unitNav="1.25",
        valuationTime=datetime.now(UTC),
        currency="USDT",
        source="manual_admin",
    )
    assert holding.source == "manual_admin"
    assert nav.source == "manual_admin"
