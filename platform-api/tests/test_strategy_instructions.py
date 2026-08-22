from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app
from app.strategies.instruction_service import execute_instruction

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
        assert first.json()["executionPlan"]["legs"][0]["executionPolicy"] == "market"
        assert (
            first.json()["executionPlan"]["simulationCompatibilityPolicy"]
            == "fake_gateway_market"
        )
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


def test_pending_instruction_batch_is_claimed_once_and_replay_does_not_duplicate_commands(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "instruction-dispatch-claim.db")
    settings.live_trading_enabled = True
    settings.default_trading_environment = "simulation"
    first_submit_started = Event()
    release_first_submit = Event()

    class FilledResponse:
        def __init__(self, command: dict[str, object]) -> None:
            self.command = command

        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            command = self.command
            return [
                {
                    "event_id": str(uuid4()),
                    "command_id": command["command_id"],
                    "platform_order_id": command["platform_order_id"],
                    "event_type": "order_filled",
                    "external_order_id": f"fake-{command['platform_order_id']}",
                    "fill_price": "100",
                    "fill_quantity": command["quantity"],
                    "occurred_at": "2026-08-22T00:00:00+00:00",
                    "reason": None,
                }
            ]

    call_count = 0

    def fake_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            first_submit_started.set()
            assert release_first_submit.wait(timeout=5)
        return FilledResponse(kwargs["json"])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", fake_post)

    with TestClient(app) as client:
        created = client.post(
            f"/api/v1/strategies/{FUNDING_INSTANCE}/instructions",
            json=_payload(key="instruction-dispatch-claim"),
        )
        assert created.status_code == 200, created.text
        instruction_id = created.json()["instructionId"]

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(execute_instruction, instruction_id)
            assert first_submit_started.wait(timeout=5)
            replay = pool.submit(execute_instruction, instruction_id)
            replay.result(timeout=5)
            release_first_submit.set()
            result = first.result(timeout=10)

    assert result.status == "hedged"
    assert call_count == 2
    with connection() as db:
        command_count = db.execute("SELECT COUNT(*) AS count FROM trade_commands").fetchone()
        instruction = db.execute(
            "SELECT status FROM strategy_runs WHERE id = ?", (instruction_id,)
        ).fetchone()
    assert command_count["count"] == 2
    assert instruction["status"] == "completed"
