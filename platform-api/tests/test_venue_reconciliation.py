from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app
from app.venue_reconciliation_repository import update_order_from_external

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


def command_payload(key: str) -> dict[str, str]:
    return {
        "idempotencyKey": key,
        "strategyInstanceId": STRATEGY_ID,
        "accountId": ACCOUNT_ID,
        "instrumentId": INSTRUMENT_ID,
        "symbol": "BTCUSDT",
        "side": "buy",
        "orderType": "limit",
        "quantity": "1",
        "price": "100",
    }


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "http://runtime.test")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("runtime error", request=request, response=response)

    def json(self):
        return self.payload


def test_result_unknown_recovers_from_venue_and_imports_facts_once(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "venue-order-recovery.db")
    monkeypatch.setattr(
        "app.trade_command_execution.httpx.post",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("timeout")),
    )

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/trading/commands",
            json=command_payload("venue-recovery-command-001"),
        )
        assert created.status_code == 200
        command = created.json()
        order_id = command["platformOrderId"]
        command_id = command["tradeCommandId"]
        assert command["status"] == "result_unknown"

        external_order = {
            "source": "fake",
            "externalOrderId": f"FAKE-{order_id}",
            "platformOrderId": order_id,
            "commandId": command_id,
            "accountId": ACCOUNT_ID,
            "instrumentId": INSTRUMENT_ID,
            "symbol": "BTCUSDT",
            "side": "buy",
            "orderType": "limit",
            "quantity": "1",
            "price": "100",
            "status": "filled",
            "filledQuantity": "1",
            "averageFillPrice": "100",
            "occurredAt": "2026-07-23T12:00:00+00:00",
            "asOf": "2026-07-23T12:00:01+00:00",
            "dataQualityState": "complete",
        }
        external_fill = {
            "source": "fake",
            "externalFillId": f"FAKE-FILL-{order_id}",
            "externalOrderId": f"FAKE-{order_id}",
            "platformOrderId": order_id,
            "commandId": command_id,
            "accountId": ACCOUNT_ID,
            "instrumentId": INSTRUMENT_ID,
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": "1",
            "price": "100",
            "fee": "0",
            "currency": "USDT",
            "occurredAt": "2026-07-23T12:00:00+00:00",
            "dataQualityState": "complete",
        }

        def runtime_get(url, *args, **kwargs):
            if "/commands/" in url and url.endswith("/events"):
                return FakeResponse({}, 404)
            if url.endswith(f"/venue/orders/by-platform/{order_id}"):
                return FakeResponse(external_order)
            if url.endswith("/venue/fills"):
                return FakeResponse([external_fill])
            raise AssertionError(f"unexpected runtime url: {url}")

        monkeypatch.setattr("app.venue_reconciliation_runtime_client.httpx.get", runtime_get)
        first = client.post(f"/api/v1/trading/orders/{order_id}/venue-reconcile")
        second = client.post(f"/api/v1/trading/orders/{order_id}/venue-reconcile")

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["statusBefore"] == "result_unknown"
        assert first.json()["statusAfter"] == "filled"
        assert first.json()["recovered"] is True
        assert first.json()["differenceIds"] == []
        assert len(first.json()["importedFactIds"]) == 2
        assert second.json()["statusAfter"] == "filled"

        with connection() as db:
            fill_count = db.execute("SELECT COUNT(*) AS count FROM fills").fetchone()["count"]
            fact_count = db.execute(
                """
                SELECT COUNT(*) AS count FROM financial_facts
                WHERE strategy_instance_id = ?
                """,
                (STRATEGY_ID,),
            ).fetchone()["count"]
        assert fill_count == 1
        assert fact_count == 2

        position = client.get(
            f"/api/v1/strategies/instances/{STRATEGY_ID}/formal-positions"
        ).json()[0]
        assert position["netQuantity"] == "1"


def test_owner_can_close_absent_standalone_result_unknown_order(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "venue-order-absent.db")
    monkeypatch.setattr(
        "app.trade_command_execution.httpx.post",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("timeout")),
    )

    def runtime_get(url, *args, **kwargs):
        if "/commands/" in url and url.endswith("/events"):
            return FakeResponse({}, 404)
        if "/venue/orders/by-platform/" in url:
            return FakeResponse({}, 404)
        raise AssertionError(f"unexpected runtime URL: {url}")

    monkeypatch.setattr("app.venue_reconciliation_runtime_client.httpx.get", runtime_get)

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/trading/commands",
            json=command_payload("venue-absent-command-001"),
        )
        assert created.status_code == 200
        order_id = created.json()["platformOrderId"]

        reconciled = client.post(f"/api/v1/trading/orders/{order_id}/venue-reconcile")
        assert reconciled.status_code == 200
        difference_id = reconciled.json()["differenceIds"][0]
        accepted = client.post(
            f"/api/v1/ops/venue-reconciliation/differences/{difference_id}/resolve",
            json={
                "status": "accepted",
                "actor": "risk-officer",
                "reason": "Runtime exact order lookup returned 404",
            },
        )
        assert accepted.status_code == 200

        closed = client.post(
            f"/api/v1/trading/orders/{order_id}/resolve-missing-external"
        )
        assert closed.status_code == 200
        assert closed.json()["statusAfter"] == "rejected"

        summary = client.get("/api/v1/ops/reconciliation-summary")
        assert summary.status_code == 200
        assert summary.json()["resultUnknownOrderCount"] == 0


def test_account_snapshot_import_is_idempotent_and_difference_is_auditable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "venue-account-run.db")
    position = {
        "source": "fake",
        "externalPositionId": "FAKE-POS-ACCOUNT-BTC",
        "accountId": ACCOUNT_ID,
        "instrumentId": INSTRUMENT_ID,
        "symbol": "BTCUSDT",
        "netQuantity": "2",
        "averagePrice": "100",
        "currency": "USDT",
        "asOf": "2026-07-23T13:00:00+00:00",
        "dataQualityState": "complete",
    }
    balance = {
        "source": "fake",
        "externalBalanceId": "FAKE-BAL-ACCOUNT-USDT-1300",
        "accountId": ACCOUNT_ID,
        "equity": "100000",
        "availableBalance": "100000",
        "currency": "USDT",
        "asOf": "2026-07-23T13:00:00+00:00",
        "dataQualityState": "complete",
    }

    def venue_get(url, *args, **kwargs):
        if url.endswith("/venue/positions"):
            return FakeResponse([position])
        if url.endswith("/venue/balances"):
            return FakeResponse([balance])
        raise AssertionError(f"unexpected runtime url: {url}")

    monkeypatch.setattr("app.venue_reconciliation_runtime_client.httpx.get", venue_get)

    with TestClient(app) as client:
        payload = {
            "idempotencyKey": "venue-account-run-001",
            "strategyInstanceId": STRATEGY_ID,
            "accountId": ACCOUNT_ID,
            "actor": "reconciliation-test",
        }
        first = client.post("/api/v1/ops/venue-reconciliation/runs", json=payload)
        second = client.post("/api/v1/ops/venue-reconciliation/runs", json=payload)
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json() == first.json()
        run = first.json()
        assert run["positionCount"] == 1
        assert run["balanceCount"] == 1
        assert run["factCount"] == 2
        assert run["differenceCount"] >= 1
        assert run["status"] == "completed_with_differences"

        differences = client.get(
            f"/api/v1/ops/venue-reconciliation/runs/{run['runId']}/differences"
        )
        assert differences.status_code == 200
        types = {item["differenceType"] for item in differences.json()}
        assert "missing_local" in types

        difference_id = differences.json()[0]["differenceId"]
        resolved = client.post(
            f"/api/v1/ops/venue-reconciliation/differences/{difference_id}/resolve",
            json={
                "status": "accepted",
                "actor": "risk-officer",
                "reason": "expected fake venue bootstrap difference",
            },
        )
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "accepted"

        replay = client.post(
            f"/api/v1/ops/venue-reconciliation/differences/{difference_id}/resolve",
            json={
                "status": "resolved",
                "actor": "other-actor",
                "reason": "must not overwrite prior resolution",
            },
        )
        assert replay.status_code == 200
        assert replay.json()["status"] == "accepted"

        with connection() as db:
            fact_count = db.execute(
                "SELECT COUNT(*) AS count FROM financial_facts WHERE source = 'fake'"
            ).fetchone()["count"]
            audit_count = db.execute(
                """
                SELECT COUNT(*) AS count FROM audit_events
                WHERE event_type IN (
                    'venue_reconciliation_completed',
                    'reconciliation_difference_resolved'
                )
                """
            ).fetchone()["count"]
        assert fact_count == 2
        assert audit_count == 2


def test_reconciliation_idempotency_payload_conflict_returns_409(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "venue-conflict.db")
    monkeypatch.setattr(
        "app.venue_reconciliation_runtime_client.httpx.get",
        lambda url, *args, **kwargs: FakeResponse([]),
    )
    with TestClient(app) as client:
        payload = {
            "idempotencyKey": "venue-run-conflict-001",
            "strategyInstanceId": STRATEGY_ID,
            "accountId": ACCOUNT_ID,
            "actor": "first-actor",
        }
        assert client.post("/api/v1/ops/venue-reconciliation/runs", json=payload).status_code == 200
        conflict = client.post(
            "/api/v1/ops/venue-reconciliation/runs",
            json={**payload, "actor": "different-actor"},
        )
        assert conflict.status_code == 409


def test_cross_close_reconciliation_completes_lifecycle_and_releases_resources(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "cross-close-reconciliation.db")
    timestamp = "2026-09-04T12:00:00+00:00"
    with TestClient(app):
        with connection() as db:
            for batch_id, direction, status in (
                ("open-batch", "open_long", "hedged"),
                ("close-batch", "close_long", "manual_intervention"),
            ):
                db.execute(
                    """
                    INSERT INTO execution_batches (
                        id, idempotency_key, strategy_instance_id, account_id,
                        strategy_key, direction, status, requires_manual_intervention,
                        created_at, updated_at, strategy_instruction_id
                    ) VALUES (?, ?, ?, ?, 'cross_venue_spread', ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        batch_id,
                        f"{batch_id}-key",
                        "strategy_cross_venue_spread_instance_default",
                        ACCOUNT_ID,
                        direction,
                        status,
                        int(status == "manual_intervention"),
                        timestamp,
                        timestamp,
                        "close-instruction" if batch_id == "close-batch" else None,
                    ),
                )
            db.execute(
                """
                INSERT INTO strategy_runs (
                    id, idempotency_key, strategy_instance_id, strategy_key,
                    direction, status, execution_batch_id, created_at, updated_at
                ) VALUES ('close-instruction', 'close-instruction-key', ?,
                          'cross_venue_spread', 'close_long', 'manual_intervention',
                          'close-batch', ?, ?)
                """,
                ("strategy_cross_venue_spread_instance_default", timestamp, timestamp),
            )
            for order_id, command_id, instrument_id, symbol, status in (
                ("bybit-close-order", "bybit-close-command", INSTRUMENT_ID, "BTCUSDT", "filled"),
                ("mt5-close-order", "mt5-close-command", "instrument_xau_usd", "XAUUSD.S", "acknowledged"),
            ):
                db.execute(
                    """
                    INSERT INTO orders (
                        id, command_id, account_id, instrument_id, symbol, side,
                        order_type, quantity, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'sell', 'market', '1', ?, ?, ?)
                    """,
                    (
                        order_id,
                        command_id,
                        ACCOUNT_ID,
                        instrument_id,
                        symbol,
                        status,
                        timestamp,
                        timestamp,
                    ),
                )
            for sequence, role, order_id, instrument_id, symbol, status in (
                (1, "primary", "bybit-close-order", INSTRUMENT_ID, "BTCUSDT", "filled"),
                (2, "hedge", "mt5-close-order", "instrument_xau_usd", "XAUUSD.S", "acknowledged"),
            ):
                db.execute(
                    """
                    INSERT INTO execution_batch_legs (
                        id, batch_id, sequence, role, account_id, instrument_id,
                        symbol, side, order_type, quantity, order_id, status,
                        created_at, updated_at
                    ) VALUES (?, 'close-batch', ?, ?, ?, ?, ?, 'sell', 'market',
                              '1', ?, ?, ?, ?)
                    """,
                    (
                        f"close-leg-{sequence}",
                        sequence,
                        role,
                        ACCOUNT_ID,
                        instrument_id,
                        symbol,
                        order_id,
                        status,
                        timestamp,
                        timestamp,
                    ),
                )
            db.execute(
                """
                INSERT INTO cross_spread_exit_plans (
                    id, strategy_instance_id, open_batch_id, close_batch_id,
                    direction, quantity_oz, mt5_position_id, entry_spread,
                    take_profit_spread, stop_loss_spread, status, created_at, updated_at
                ) VALUES ('exit-plan', ?, 'open-batch', 'close-batch', 'long', '1',
                          'position-1', '-1', '-2', '2', 'manual_intervention', ?, ?)
                """,
                ("strategy_cross_venue_spread_instance_default", timestamp, timestamp),
            )
            db.execute(
                """
                INSERT INTO execution_resource_claims (
                    id, resource_key, owner_type, owner_id, account_id, venue_id,
                    resource_category, symbol, status, created_at, updated_at
                ) VALUES ('claim-1', 'resource-1', 'batch', 'close-batch', ?,
                          'venue-1', 'instrument', 'BTCUSDT', 'active', ?, ?)
                """,
                (ACCOUNT_ID, timestamp, timestamp),
            )
            db.execute(
                """
                INSERT INTO execution_balance_reservations (
                    id, owner_type, owner_id, account_id, strategy_instance_id,
                    instruction_id, currency, reserved_amount, status, created_at, updated_at
                ) VALUES ('reservation-1', 'batch', 'close-batch', ?, ?,
                          'close-instruction', 'USDT', '100', 'active', ?, ?)
                """,
                (
                    ACCOUNT_ID,
                    "strategy_cross_venue_spread_instance_default",
                    timestamp,
                    timestamp,
                ),
            )

        update_order_from_external(
            "mt5-close-order", "filled", "external-mt5-order", timestamp
        )

        with connection() as db:
            batch = db.execute(
                "SELECT status, requires_manual_intervention FROM execution_batches WHERE id = 'close-batch'"
            ).fetchone()
            instruction = db.execute(
                "SELECT status FROM strategy_runs WHERE id = 'close-instruction'"
            ).fetchone()
            plan = db.execute(
                "SELECT status FROM cross_spread_exit_plans WHERE id = 'exit-plan'"
            ).fetchone()
            claim = db.execute(
                "SELECT status FROM execution_resource_claims WHERE id = 'claim-1'"
            ).fetchone()
            reservation = db.execute(
                "SELECT status FROM execution_balance_reservations WHERE id = 'reservation-1'"
            ).fetchone()

    assert dict(batch) == {"status": "hedged", "requires_manual_intervention": 0}
    assert instruction["status"] == "completed"
    assert plan["status"] == "closed"
    assert claim["status"] == "released"
    assert reservation["status"] == "released"
