from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.version import PLATFORM_VERSION


def test_runtime_persists_events_and_replays_duplicate_command(tmp_path: Path) -> None:
    get_settings().journal_path = str(tmp_path / "runtime_journal.db")

    payload = {
        "command_id": "command-001",
        "platform_order_id": "order-001",
        "account_id": "account_sim_usdt",
        "instrument_id": "instrument_btc_usdt",
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "limit",
        "quantity": "1",
        "price": "100",
    }

    with TestClient(app) as client:
        first = client.post("/commands/orders", json=payload)
        second = client.post("/commands/orders", json=payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json() == first.json()
        assert [event["event_type"] for event in first.json()] == [
            "order_acknowledged",
            "order_filled",
        ]

        events = client.get("/commands/command-001/events")
        assert events.status_code == 200
        assert events.json() == first.json()

        status = client.get("/status")
        assert status.status_code == 200
        assert status.json()["version"] == PLATFORM_VERSION
        journal = status.json()["journal"]
        assert journal["status"] == "available"
        assert journal["commandCount"] == 1
        assert journal["eventCount"] == 2

        openapi = client.get("/openapi.json")
        assert openapi.status_code == 200
        properties = openapi.json()["components"]["schemas"]["RuntimeStatusResponse"]["properties"]
        assert properties["version"]["type"] == "string"
