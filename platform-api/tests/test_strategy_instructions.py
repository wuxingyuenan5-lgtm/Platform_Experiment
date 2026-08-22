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
            "spotSymbol": "BTC",
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
