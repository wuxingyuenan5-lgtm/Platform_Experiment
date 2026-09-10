from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.capital_flows import bybit_capital_flows
from app.gateway_errors import GatewayConfigurationError


def adapter(uta, pages):
    client = SimpleNamespace(
        endpoint="https://example.invalid", _submit_request=lambda **kwargs: pages.pop(0)
    )
    return SimpleNamespace(
        _snapshot_pages=lambda *args: uta,
        _read_with_retry=lambda account, fn: fn(client),
        _require_success=lambda response, message: None,
    )


def test_funding_transfer_internal_and_withdraw_external():
    start = datetime(2026, 9, 1, tzinfo=UTC)
    uta = [
        {
            "id": "u1",
            "transactionTime": str(int(start.timestamp() * 1000)),
            "currency": "USDT",
            "type": "TRANSFER_OUT",
            "change": "-100",
        }
    ]
    funding = [
        {
            "currcCursor": "f1",
            "createTime": str(int(start.timestamp())),
            "currency": "USDT",
            "txnAmt": "100",
            "ioDirection": "I",
            "showBusiType": "fundingAccountRecordTransferIn",
            "descriptionEn": "Transfer from Unified Trading Account",
        },
        {
            "currcCursor": "f2",
            "createTime": str(int(start.timestamp())),
            "currency": "USDT",
            "txnAmt": "100",
            "ioDirection": "O",
            "showBusiType": "fundingAccountRecordTypeWithdraw",
            "descriptionEn": "Withdrawal",
        },
    ]
    result = bybit_capital_flows(
        adapter(uta, [{"result": {"list": funding}}]), "a", start, start + timedelta(hours=1)
    )
    assert [(e["assetScope"], e["amount"]) for e in result["events"]] == [
        ("unified_trading", "-100"),
        ("full_account", "0"),
        ("full_account", "0"),
        ("full_account", "-100"),
    ]


def test_repeated_cursor_rejected():
    page = {"result": {"list": [], "nextPageCursor": "same"}}
    with pytest.raises(GatewayConfigurationError, match="advance"):
        bybit_capital_flows(adapter([], [page, page]), "a", datetime.now(UTC), datetime.now(UTC))
