from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app


def test_seeded_strategy_account_and_instrument_catalog(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "catalog.db")

    with TestClient(app) as client:
        strategies = client.get("/api/v1/strategies/definitions")
        assert strategies.status_code == 200
        body = strategies.json()
        assert len(body) == 6
        closed_loop = {item["strategyKey"] for item in body if item["v1Scope"] == "closed_loop"}
        assert closed_loop == {"funding_arbitrage", "cross_venue_spread"}

        instances = client.get("/api/v1/strategies/instances")
        assert instances.status_code == 200
        assert len(instances.json()) == 6

        overview = client.get("/api/v1/strategies/management-overview")
        assert overview.status_code == 200
        overview_body = overview.json()
        assert [item["deskKey"] for item in overview_body] == [
            "funding",
            "crossSpread",
            "domesticOverseas",
            "dip",
            "shortLineTraderL",
            "shortLineTraderW",
        ]
        assert {item["strategyKey"] for item in overview_body} == {
            "funding_arbitrage",
            "cross_venue_spread",
            "home_abroad_spread",
            "bottom_fishing",
            "short_term_l",
            "short_term_w",
        }
        by_desk = {item["deskKey"]: item for item in overview_body}
        assert by_desk["funding"]["activeCapability"] == "trade_and_read"
        assert by_desk["crossSpread"]["activeCapability"] == "trade_and_read"
        assert by_desk["domesticOverseas"]["operatingStatus"] == "paused"
        assert by_desk["dip"]["operatingStatus"] == "active"
        assert by_desk["shortLineTraderL"]["operatingStatus"] == "active"
        assert by_desk["shortLineTraderW"]["operatingStatus"] == "active"
        assert by_desk["dip"]["executionReadiness"] is None
        assert by_desk["shortLineTraderL"]["executionReadiness"] is None
        assert by_desk["shortLineTraderW"]["executionReadiness"] is None
        assert by_desk["dip"]["primaryAccountDataQualityState"] == "unavailable"
        assert by_desk["dip"]["operatingStatus"] == "active"
        assert by_desk["dip"]["latestRunStatus"] is None
        assert by_desk["dip"]["latestRunAt"] is None
        assert all("credentialRef" not in item for item in overview_body)

        accounts = client.get("/api/v1/accounts")
        assert accounts.status_code == 200
        assert {item["accountId"] for item in accounts.json()} >= {
            "account_sim_usdt",
            "account_crypto_test",
            "account_mt5_demo",
        }

        instruments = client.get("/api/v1/instruments")
        assert instruments.status_code == 200
        assert {item["instrumentId"] for item in instruments.json()} >= {
            "instrument_btc_usdt",
            "instrument_btc_usdt_perp",
            "instrument_xau_usd",
        }


def test_trade_command_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "commands.db")

    def runtime_unavailable(*args, **kwargs):
        raise httpx.ConnectError("runtime unavailable")

    monkeypatch.setattr("app.trade_command_execution.httpx.post", runtime_unavailable)

    payload = {
        "idempotencyKey": "idem-001",
        "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
        "accountId": "account_sim_usdt",
        "instrumentId": "instrument_btc_usdt",
        "symbol": "BTCUSDT",
        "side": "buy",
        "orderType": "limit",
        "quantity": "1",
        "price": "100",
    }

    with TestClient(app) as client:
        first = client.post("/api/v1/trading/commands", json=payload)
        second = client.post("/api/v1/trading/commands", json=payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["tradeCommandId"] == second.json()["tradeCommandId"]
        assert first.json()["platformOrderId"] == second.json()["platformOrderId"]

        orders = client.get("/api/v1/trading/orders")
        assert orders.status_code == 200
        assert len(orders.json()) == 1
        assert orders.json()[0]["status"] == "result_unknown"


def test_strategy_nav_snapshot_uses_seed_balance_and_capital_base(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "nav.db")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/strategies/instances/"
            "strategy_funding_arbitrage_instance_default/nav-snapshots/run"
        )
        assert response.status_code == 200
        snapshot = response.json()
        assert snapshot["equity"] == "100000"
        assert snapshot["capitalBase"] == "100000"
        assert snapshot["nav"] == "1"
        assert snapshot["dataQualityState"] == "complete"

        snapshots = client.get(
            "/api/v1/strategies/instances/"
            "strategy_funding_arbitrage_instance_default/nav-snapshots"
        )
        assert snapshots.status_code == 200
        assert len(snapshots.json()) == 1


def test_management_overview_exposes_latest_run_freshness_for_closed_loop_and_read_only(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "management-overview-runs.db")

    with TestClient(app) as client:
        with connection() as db:
            db.execute(
                """
                INSERT INTO strategy_runs (
                    id, idempotency_key, strategy_instance_id, strategy_key, direction,
                    status, execution_batch_id, reason, failure_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "run-funding-latest",
                    "idem-funding-latest",
                    "strategy_funding_arbitrage_instance_default",
                    "funding_arbitrage",
                    "collect",
                    "completed",
                    None,
                    None,
                    None,
                    "2026-08-24T01:00:00+00:00",
                    "2026-08-24T01:00:00+00:00",
                    "run-bottom-fishing-latest",
                    "idem-bottom-fishing-latest",
                    "strategy_bottom_fishing_instance_default",
                    "bottom_fishing",
                    "read_only_refresh",
                    "executing",
                    None,
                    None,
                    None,
                    "2026-08-24T02:00:00+00:00",
                    "2026-08-24T02:00:00+00:00",
                ),
            )

        response = client.get("/api/v1/strategies/management-overview")

    assert response.status_code == 200
    overview_by_desk = {item["deskKey"]: item for item in response.json()}
    assert overview_by_desk["funding"]["latestRunStatus"] == "completed"
    assert overview_by_desk["funding"]["latestRunAt"] == "2026-08-24T01:00:00Z"
    assert overview_by_desk["dip"]["latestRunStatus"] == "executing"
    assert overview_by_desk["dip"]["latestRunAt"] == "2026-08-24T02:00:00Z"
    assert overview_by_desk["shortLineTraderL"]["latestRunStatus"] is None
    assert overview_by_desk["shortLineTraderL"]["latestRunAt"] is None
    assert overview_by_desk["shortLineTraderL"]["operatingStatus"] == "active"
