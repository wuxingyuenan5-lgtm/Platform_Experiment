from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.execution_risk import check_leg_deadline
from app.main import app

STRATEGY_INSTANCE_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
SPOT_ID = "instrument_btc_usdt"
PERP_ID = "instrument_btc_usdt_perp"


def filled_runtime_response(command: dict[str, object]) -> object:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return [
                {
                    "event_id": str(uuid4()),
                    "command_id": command["command_id"],
                    "platform_order_id": command["platform_order_id"],
                    "event_type": "order_acknowledged",
                    "external_order_id": f"fake-{command['platform_order_id']}",
                    "fill_price": None,
                    "fill_quantity": None,
                    "occurred_at": "2026-07-23T10:00:00+00:00",
                    "reason": None,
                },
                {
                    "event_id": str(uuid4()),
                    "command_id": command["command_id"],
                    "platform_order_id": command["platform_order_id"],
                    "event_type": "order_filled",
                    "external_order_id": f"fake-{command['platform_order_id']}",
                    "fill_price": command["price"] or "100",
                    "fill_quantity": command["quantity"],
                    "occurred_at": "2026-07-23T10:00:01+00:00",
                    "reason": None,
                },
            ]

    return FakeResponse()


def batch_payload(idempotency_key: str) -> dict[str, object]:
    return {
        "idempotencyKey": idempotency_key,
        "strategyInstanceId": STRATEGY_INSTANCE_ID,
        "accountId": ACCOUNT_ID,
        "strategyKey": "funding_arbitrage",
        "direction": "collect",
        "legs": [
            {
                "role": "spot",
                "instrumentId": SPOT_ID,
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "1",
                "price": "100",
            },
            {
                "role": "perp",
                "instrumentId": PERP_ID,
                "symbol": "BTCUSDT-PERP",
                "side": "sell",
                "orderType": "limit",
                "quantity": "1",
                "price": "100",
            },
        ],
    }


def set_policy(
    client: TestClient,
    *,
    key: str,
    max_delay: int = 10,
    max_residual: str = "100000",
    failure_action: str = "hold_and_escalate",
) -> None:
    response = client.put(
        f"/api/v1/strategies/instances/{STRATEGY_INSTANCE_ID}/execution-risk-policy",
        json={
            "idempotencyKey": key,
            "maxLegDelaySeconds": max_delay,
            "maxResidualNotional": max_residual,
            "failureAction": failure_action,
            "actor": "risk-test",
        },
    )
    assert response.status_code == 200


def test_global_kill_switch_blocks_before_batch_claim(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "kill-switch.db")
    with TestClient(app) as client:
        switch_payload = {
            "idempotencyKey": "kill-global-on-001",
            "enabled": True,
            "reason": "incident drill",
            "actor": "risk-officer",
        }
        first = client.put("/api/v1/risk/kill-switches/global/*", json=switch_payload)
        second = client.put("/api/v1/risk/kill-switches/global/*", json=switch_payload)
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json() == first.json()
        assert first.json()["enabled"] is True
        assert first.json()["version"] == 1

        blocked = client.post(
            "/api/v1/trading/execution-batches",
            json=batch_payload("kill-switch-blocked-batch"),
        )
        assert blocked.status_code == 423
        assert "global kill switch" in blocked.json()["detail"]

        with connection() as db:
            batch_count = db.execute("SELECT COUNT(*) AS count FROM execution_batches").fetchone()[
                "count"
            ]
            command_count = db.execute("SELECT COUNT(*) AS count FROM trade_commands").fetchone()[
                "count"
            ]
        assert batch_count == 0
        assert command_count == 0

        conflict = client.put(
            "/api/v1/risk/kill-switches/global/*",
            json={**switch_payload, "enabled": False},
        )
        assert conflict.status_code == 409


def test_auto_flatten_resolves_first_leg_exposure_idempotently(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "auto-flatten.db")
    call_count = 0

    def runtime_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise httpx.ConnectError("runtime unavailable")
        return filled_runtime_response(kwargs["json"])

    monkeypatch.setattr("app.trading.httpx.post", runtime_post)

    with TestClient(app) as client:
        set_policy(
            client,
            key="policy-auto-flatten-001",
            failure_action="auto_flatten",
        )
        response = client.post(
            "/api/v1/trading/execution-batches",
            json=batch_payload("auto-flatten-batch-001"),
        )
        assert response.status_code == 200
        batch = response.json()
        assert batch["status"] == "failed"
        assert batch["requiresManualIntervention"] is False
        assert call_count == 3

        risk = client.get(
            f"/api/v1/trading/execution-batches/{batch['batchId']}/risk"
        ).json()
        assert risk["riskStatus"] == "resolved"
        assert risk["residualExposureNotional"] == "0"

        actions = client.get(
            f"/api/v1/trading/execution-batches/{batch['batchId']}/risk-actions"
        ).json()
        assert len(actions) == 1
        assert actions[0]["action"] == "flatten_filled_legs"
        assert actions[0]["status"] == "completed"
        assert len(actions[0]["generatedOrderIds"]) == 1

        replay = client.post(
            f"/api/v1/trading/execution-batches/{batch['batchId']}/risk-actions",
            json={
                "idempotencyKey": f"auto-flatten:{batch['batchId']}",
                "action": "flatten_filled_legs",
                "actor": "system-risk-engine",
                "reason": actions[0]["reason"],
            },
        )
        assert replay.status_code == 200
        assert replay.json()["riskActionId"] == actions[0]["riskActionId"]
        assert call_count == 3

        position = client.get(f"/api/v1/accounts/{ACCOUNT_ID}/positions/{SPOT_ID}")
        assert position.status_code == 200
        assert position.json()["netQuantity"] == "0"


def test_residual_limit_stops_second_leg_and_manual_action_is_idempotent(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "residual-limit.db")
    call_count = 0

    def runtime_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return filled_runtime_response(kwargs["json"])

    monkeypatch.setattr("app.trading.httpx.post", runtime_post)

    with TestClient(app) as client:
        set_policy(
            client,
            key="policy-residual-limit-001",
            max_residual="50",
        )
        response = client.post(
            "/api/v1/trading/execution-batches",
            json=batch_payload("residual-limit-batch-001"),
        )
        assert response.status_code == 200
        batch = response.json()
        assert batch["status"] == "manual_intervention"
        assert batch["requiresManualIntervention"] is True
        assert call_count == 1

        risk = client.get(
            f"/api/v1/trading/execution-batches/{batch['batchId']}/risk"
        ).json()
        assert risk["riskStatus"] == "escalated"
        assert risk["residualExposureNotional"] == "100"
        assert risk["residualCurrency"] == "USDT"

        action_payload = {
            "idempotencyKey": "manual-hold-action-001",
            "action": "hold_and_escalate",
            "actor": "risk-officer",
            "reason": "retain exposure for controlled drill",
        }
        first = client.post(
            f"/api/v1/trading/execution-batches/{batch['batchId']}/risk-actions",
            json=action_payload,
        )
        second = client.post(
            f"/api/v1/trading/execution-batches/{batch['batchId']}/risk-actions",
            json=action_payload,
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["riskActionId"] == first.json()["riskActionId"]
        assert first.json()["status"] == "completed"

        conflict = client.post(
            f"/api/v1/trading/execution-batches/{batch['batchId']}/risk-actions",
            json={**action_payload, "reason": "different reason"},
        )
        assert conflict.status_code == 409


def test_leg_deadline_uses_first_fill_timestamp(monkeypatch, tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "leg-deadline.db")
    call_count = 0

    def runtime_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise httpx.ConnectError("runtime unavailable")
        return filled_runtime_response(kwargs["json"])

    monkeypatch.setattr("app.trading.httpx.post", runtime_post)

    with TestClient(app) as client:
        set_policy(
            client,
            key="policy-leg-delay-001",
            max_delay=1,
        )
        batch = client.post(
            "/api/v1/trading/execution-batches",
            json=batch_payload("leg-delay-batch-001"),
        ).json()
        risk = client.get(
            f"/api/v1/trading/execution-batches/{batch['batchId']}/risk"
        ).json()
        first_fill_at = datetime.fromisoformat(risk["firstFillAt"])
        allowed, reason = check_leg_deadline(
            batch["batchId"],
            at=first_fill_at.astimezone(UTC) + timedelta(seconds=2),
        )
        assert allowed is False
        assert reason is not None
        assert "exceeded policy limit" in reason
