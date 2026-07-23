from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def order_payload(*, account_id: str, instrument_id: str, quantity: str = "0.01") -> dict[str, str]:
    return {
        "accountId": account_id,
        "instrumentId": instrument_id,
        "symbol": "BTCUSDT",
        "side": "buy",
        "orderType": "limit",
        "quantity": quantity,
        "price": "65000",
    }


def test_unknown_account_is_rejected_before_runtime_call(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "unknown-account.db")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/orders",
            json=order_payload(
                account_id="missing-account",
                instrument_id="instrument_btc_usdt",
            ),
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Account not found"


def test_unknown_instrument_is_rejected_before_runtime_call(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "unknown-instrument.db")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/orders",
            json=order_payload(
                account_id="account_sim_usdt",
                instrument_id="missing-instrument",
            ),
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Instrument not found"


def test_quantity_must_follow_contract_specification(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "quantity-step.db")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/orders",
            json=order_payload(
                account_id="account_sim_usdt",
                instrument_id="instrument_btc_usdt",
                quantity="0.0005",
            ),
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Order quantity is below minimum"
