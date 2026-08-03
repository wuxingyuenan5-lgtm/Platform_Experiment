from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import main as runtime_main
from app.config import get_settings
from app.gateway_errors import GatewayResultUnknownError
from app.gateway_factory import create_gateway


def test_unknown_gateway_result_is_not_resubmitted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    get_settings().journal_path = str(tmp_path / "unknown-result-journal.db")
    calls = 0

    def result_unknown(_command):
        nonlocal calls
        calls += 1
        raise GatewayResultUnknownError("venue outcome is unknown")

    gateway = create_gateway(get_settings().gateway_name)
    monkeypatch.setattr(gateway, "submit_order", result_unknown)
    payload = {
        "contract_name": "runtime-command",
        "contract_version": "1.0",
        "payload_version": "1.0",
        "command_id": "unknown-command-001",
        "platform_order_id": "unknown-order-001",
        "strategy_instance_id": "strategy-001",
        "account_id": "account_sim_usdt",
        "instrument_id": "instrument_btc_usdt",
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "limit",
        "quantity": "1",
        "price": "100",
    }

    with TestClient(runtime_main.create_app(gateway)) as client:
        first = client.post("/commands/orders", json=payload)
        second = client.post("/commands/orders", json=payload)
        events = client.get("/commands/unknown-command-001/events")

    assert first.status_code == 502
    assert second.status_code == 409
    assert events.status_code == 404
    assert calls == 1
