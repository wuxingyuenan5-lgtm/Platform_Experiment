from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app

QUOTE_URL = "/api/v1/trading/cross-spread/funding-transfer/quote"
CREATE_URL = "/api/v1/trading/cross-spread/funding-transfer"


def _risk(
    account_id: str,
    *,
    bybit: str = "260.000000000000000001",
    mt5: str = "100",
    source: str = "fake",
) -> dict[str, object]:
    return {
        "source": source,
        "accountId": account_id,
        "currency": "USDT",
        "availableBalance": bybit if account_id == "account_crypto_test" else mt5,
        "dataQualityState": "complete",
        "asOf": "2026-08-22T00:00:00+00:00",
    }


def _payload(
    *,
    key: str = "funding-transfer-001",
    direction: str = "bybit_to_mt5",
    amount: object = "80.0000000000000000005",
) -> dict[str, object]:
    return {"idempotencyKey": key, "direction": direction, "amount": amount}


def _configure_quote(monkeypatch, callback: Callable[[str], dict[str, object]]) -> None:
    monkeypatch.setattr(
        "app.strategies.capital_transfer._runtime_account_risk",
        callback,
    )


def test_quote_uses_decimal_half_difference_and_never_turns_failure_into_zero(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "funding-transfer-quote.db")
    _configure_quote(monkeypatch, _risk)
    with TestClient(app) as client:
        quote = client.get(QUOTE_URL)
    assert quote.status_code == 200, quote.text
    assert quote.json()["suggestedDirection"] == "bybit_to_mt5"
    assert quote.json()["suggestedAmount"] == "80.0000000000000000005"

    def one_side_unavailable(account_id: str) -> dict[str, object]:
        if account_id == "account_crypto_test":
            raise httpx.ConnectError("Bybit read unavailable")
        return _risk(account_id)

    _configure_quote(monkeypatch, one_side_unavailable)
    with TestClient(app) as client:
        unavailable = client.get(QUOTE_URL)
    assert unavailable.status_code == 200
    assert unavailable.json()["bybitTransferable"]["amount"] is None
    assert unavailable.json()["bybitTransferable"]["dataQualityState"] == "unavailable"
    assert unavailable.json()["suggestedAmount"] is None


@pytest.mark.parametrize(
    ("direction", "expected_path"),
    [
        (
            "bybit_to_mt5",
            [
                ("account_crypto_test", "fake:bybit-funding"),
                ("fake:bybit-funding", "account_mt5_demo"),
            ],
        ),
        (
            "mt5_to_bybit",
            [
                ("account_mt5_demo", "fake:bybit-funding"),
                ("fake:bybit-funding", "account_crypto_test"),
            ],
        ),
    ],
)
def test_fake_transfer_executes_two_internal_steps_without_trading_objects(
    monkeypatch,
    tmp_path: Path,
    direction: str,
    expected_path: list[tuple[str, str]],
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / f"funding-transfer-{direction}.db")
    _configure_quote(
        monkeypatch,
        lambda account_id: _risk(account_id, bybit="300", mt5="300"),
    )
    calls: list[tuple[str, str, Decimal]] = []

    def transfer_step(**kwargs) -> dict[str, object]:
        calls.append(
            (
                kwargs["source_account_id"],
                kwargs["destination_account_id"],
                kwargs["amount"],
            )
        )
        return {
            "status": "completed",
            "externalTransferId": f"fake-step-{len(calls)}",
        }

    monkeypatch.setattr(
        "app.strategies.capital_transfer._runtime_transfer_step",
        transfer_step,
    )
    with TestClient(app) as client:
        response = client.post(
            CREATE_URL,
            json=_payload(key=f"two-step-{direction}", direction=direction, amount="10.25"),
        )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"
    assert [(source, destination) for source, destination, _ in calls] == expected_path
    assert all(amount == Decimal("10.25") for _, _, amount in calls)
    assert response.json()["requestedBy"] == settings.development_user_id
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM strategy_runs").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM execution_batches").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM trade_commands").fetchone()[0] == 0


def test_transfer_replay_conflict_and_public_payload_boundary(monkeypatch, tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "funding-transfer-idempotency.db")
    _configure_quote(monkeypatch, lambda account_id: _risk(account_id, bybit="300", mt5="100"))
    calls = 0

    def transfer_step(**kwargs) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"status": "completed", "externalTransferId": f"step-{calls}"}

    monkeypatch.setattr(
        "app.strategies.capital_transfer._runtime_transfer_step",
        transfer_step,
    )
    with TestClient(app) as client:
        first = client.post(CREATE_URL, json=_payload(amount="10.125"))
        replay = client.post(CREATE_URL, json=_payload(amount="10.125"))
        conflict = client.post(CREATE_URL, json=_payload(amount="10.126"))
        spoofed = client.post(
            CREATE_URL,
            json={**_payload(key="spoofed"), "accountId": "forged", "uid": "forged"},
        )
        numeric = client.post(CREATE_URL, json=_payload(key="numeric", amount=10.125))
    assert first.status_code == replay.status_code == 200
    assert replay.json() == first.json()
    assert calls == 2
    assert conflict.status_code == 409
    assert spoofed.status_code == 422
    assert numeric.status_code == 422


def test_second_step_failure_leaves_funds_in_funding_and_unknown_is_not_retried(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "funding-transfer-partial.db")
    _configure_quote(monkeypatch, lambda account_id: _risk(account_id, bybit="300", mt5="100"))
    calls = 0

    def partial_step(**kwargs) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 2:
            request = httpx.Request("POST", "http://runtime/transfer")
            response = httpx.Response(409, request=request)
            raise httpx.HTTPStatusError("rejected", request=request, response=response)
        return {"status": "completed", "externalTransferId": "step-one"}

    monkeypatch.setattr(
        "app.strategies.capital_transfer._runtime_transfer_step",
        partial_step,
    )
    with TestClient(app) as client:
        failed = client.post(CREATE_URL, json=_payload(key="partial", amount="10"))
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    assert failed.json()["currentLocation"] == "funding"
    assert failed.json()["externalTransferId"] == "step-one"

    calls = 0

    def unknown_step(**kwargs) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"status": "result_unknown", "externalTransferId": "unknown-one"}

    monkeypatch.setattr(
        "app.strategies.capital_transfer._runtime_transfer_step",
        unknown_step,
    )
    with TestClient(app) as client:
        unknown = client.post(CREATE_URL, json=_payload(key="unknown", amount="10"))
        replay = client.post(CREATE_URL, json=_payload(key="unknown", amount="10"))
    assert unknown.json()["status"] == "result_unknown"
    assert replay.json() == unknown.json()
    assert calls == 1


def test_assisted_mode_stays_pending_and_can_be_queried(monkeypatch, tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "funding-transfer-assisted.db")
    _configure_quote(
        monkeypatch,
        lambda account_id: _risk(account_id, bybit="300", mt5="100", source="bybit_mt5"),
    )
    with TestClient(app) as client:
        created = client.post(CREATE_URL, json=_payload(key="assisted", amount="25"))
        fetched = client.get(
            f"/api/v1/trading/cross-spread/funding-transfers/{created.json()['transferId']}"
        )
    assert created.status_code == fetched.status_code == 200
    assert created.json()["status"] == "pending"
    assert created.json()["mode"] == "assisted"
    assert fetched.json() == created.json()
    assert created.json()["officialFundingUrl"].startswith("https://www.bybit.com/")
