from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


class FakeResponse:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return [
            {
                "source": "bybit_live",
                "externalEventId": "funding-live-1",
                "eventType": "funding",
                "accountId": ACCOUNT_ID,
                "instrumentId": INSTRUMENT_ID,
                "symbol": "BTCUSDT",
                "amount": "5",
                "currency": "USDT",
                "occurredAt": "2026-07-23T12:00:00+00:00",
                "dataQualityState": "complete",
                "payload": {},
            },
            {
                "source": "mt5_live",
                "externalEventId": "swap-unmapped-1",
                "eventType": "swap",
                "accountId": ACCOUNT_ID,
                "instrumentId": None,
                "symbol": "UNKNOWN",
                "amount": "-2",
                "currency": "USD",
                "occurredAt": "2026-07-23T12:00:00+00:00",
                "dataQualityState": "incomplete",
                "payload": {},
            },
        ]


def test_live_economic_events_import_idempotently(tmp_path: Path, monkeypatch) -> None:
    get_settings().database_path = str(tmp_path / "live-accounting.db")
    monkeypatch.setattr(
        "app.live_venue_accounting.runtime_get",
        lambda path, params=None: FakeResponse(),
    )
    payload = {
        "idempotencyKey": "live-economic-import-1",
        "strategyInstanceId": STRATEGY_ID,
        "accountId": ACCOUNT_ID,
        "actor": "test-operator",
    }

    with TestClient(app) as client:
        first = client.post("/api/v1/ops/live-economic-events/import", json=payload)
        second = client.post("/api/v1/ops/live-economic-events/import", json=payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["importId"] == second.json()["importId"]
        assert first.json()["status"] == "completed_with_skips"
        assert len(first.json()["importedFactIds"]) == 1
        assert first.json()["skippedExternalIds"] == ["swap-unmapped-1"]

        with connection() as db:
            fact_count = db.execute(
                """
                SELECT COUNT(*) AS count
                FROM financial_facts
                WHERE source = 'bybit_live' AND external_id = 'funding-live-1'
                """
            ).fetchone()["count"]
            audit_count = db.execute(
                """
                SELECT COUNT(*) AS count
                FROM audit_events
                WHERE event_type = 'live_economic_events_imported'
                """
            ).fetchone()["count"]
        assert fact_count == 1
        assert audit_count == 1
