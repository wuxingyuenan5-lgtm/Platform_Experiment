from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

FUNDING_INSTANCE = "strategy_funding_arbitrage_instance_default"


def _payload(*, key: str, quantity: str = "1") -> dict[str, object]:
    return {
        "idempotencyKey": key,
        "action": "open",
        "parameters": {
            "perpetualSymbol": "BTCUSDT",
            "perpetualQuantity": quantity,
            "spotSymbol": "BTCUSDT",
            "spotQuantity": quantity,
        },
        "reason": "CEO manual instruction",
    }


def test_instruction_replay_returns_the_original_frozen_plan_and_one_batch(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "instruction-replay.db")
    url = f"/api/v1/strategies/{FUNDING_INSTANCE}/instructions"

    with TestClient(app) as client:
        first = client.post(url, json=_payload(key="instruction-001"))
        second = client.post(url, json=_payload(key="instruction-001"))

        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        assert second.json() == first.json()
        assert first.json()["status"] == "accepted"
        assert first.json()["executionPlan"]["schemaVersion"] == "1"
        assert first.json()["executionPlan"]["legs"][0]["executionPolicy"] == "post_only_chase"
        assert first.json()["executionBatchId"]
        assert first.json()["requestedBy"] == get_settings().development_user_id

        fetched = client.get(f"/api/v1/strategy-instructions/{first.json()['instructionId']}")
        assert fetched.status_code == 200
        assert fetched.json() == first.json()


def test_instruction_rejects_idempotency_key_reused_for_different_parameters(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "instruction-conflict.db")
    url = f"/api/v1/strategies/{FUNDING_INSTANCE}/instructions"

    with TestClient(app) as client:
        assert client.post(url, json=_payload(key="instruction-002")).status_code == 200
        conflict = client.post(url, json=_payload(key="instruction-002", quantity="2"))

    assert conflict.status_code == 409
    assert conflict.json()["detail"] == (
        "Idempotency key is already used by a different strategy instruction payload"
    )


def test_instruction_idempotency_includes_business_reason_and_position_group(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "instruction-business-fingerprint.db")
    url = f"/api/v1/strategies/{FUNDING_INSTANCE}/instructions"
    with TestClient(app) as client:
        assert (
            client.post(url, json=_payload(key="instruction-business-fingerprint")).status_code
            == 200
        )
        changed_reason = client.post(
            url,
            json={
                **_payload(key="instruction-business-fingerprint"),
                "reason": "different CEO reason",
            },
        )

    assert changed_reason.status_code == 409


def test_instruction_idempotency_normalizes_decimal_parameters(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "instruction-normalized-fingerprint.db")
    url = f"/api/v1/strategies/{FUNDING_INSTANCE}/instructions"
    first_payload = _payload(key="instruction-normalized-fingerprint", quantity="1")
    first_payload["parameters"]["perpetualQuantity"] = 1
    first_payload["parameters"]["spotQuantity"] = 1
    with TestClient(app) as client:
        first = client.post(url, json=first_payload)
        replay = client.post(url, json=_payload(key="instruction-normalized-fingerprint"))

    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    assert replay.json()["instructionId"] == first.json()["instructionId"]


def test_close_instruction_fails_closed_without_position_group(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "instruction-close.db")
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/strategies/{FUNDING_INSTANCE}/instructions",
            json={
                "idempotencyKey": "close-without-position-group",
                "action": "close",
                "parameters": {
                    "perpetualSymbol": "BTCUSDT",
                    "perpetualQuantity": "1",
                    "spotSymbol": "BTCUSDT",
                    "spotQuantity": "1",
                },
            },
        )
    assert response.status_code == 423
    assert response.json()["detail"] == "Position Group close planning is unavailable"


def test_instruction_rejects_unknown_parameters_and_unmapped_symbols(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "instruction-validation.db")
    url = f"/api/v1/strategies/{FUNDING_INSTANCE}/instructions"
    with TestClient(app) as client:
        unknown = client.post(
            url,
            json={
                **_payload(key="instruction-extra"),
                "parameters": {**_payload(key="x")["parameters"], "accountId": "spoofed"},
            },
        )
        unmapped = client.post(
            url,
            json={
                **_payload(key="instruction-eth"),
                "parameters": {**_payload(key="x")["parameters"], "perpetualSymbol": "ETHUSDT"},
            },
        )

    assert unknown.status_code == 422
    assert unknown.json()["detail"] == "Invalid strategy instruction parameters"
    assert unmapped.status_code == 422
    assert "Authoritative crypto_perp" in unmapped.json()["detail"]


def test_instruction_preserves_account_ids_in_capability_snapshot(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "instruction-account-id.db")
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/strategies/{FUNDING_INSTANCE}/instructions",
            json=_payload(key="instruction-account-id"),
        )

    assert response.status_code == 200, response.text
    snapshot = response.json()["executionPlan"]["accountCapabilitySnapshot"]
    assert snapshot == {"account_sim_usdt": "trade_and_read"}
