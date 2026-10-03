import json
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.catalog import _funding_current_positions
from app.config import get_settings
from app.database import connection, initialize_database
from app.main import app


@pytest.fixture(autouse=True)
def isolated_lifespan(monkeypatch):
    # These tests verify the persisted account projection, with its worker driven
    # explicitly after seeding. Do not launch unrelated production monitors.
    @asynccontextmanager
    async def lifespan(_):
        initialize_database()
        yield

    monkeypatch.setattr(app.router, "lifespan_context", lifespan)


def projected_get(client, path):
    from app.strategy_management_projection import refresh_one

    response = client.get(path)
    assert response.status_code == 503
    assert refresh_one(force=True)
    return client.get(path)


def test_unconfigured_bybit_strategy_account_is_explicitly_unavailable(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "strategy-account-snapshot.db")

    with TestClient(app) as client:
        response = projected_get(client, 
            "/api/v1/strategies/instances/strategy_bottom_fishing_instance_default/account-snapshot"
        )

    assert response.status_code == 200
    expected = {
        "strategyInstanceId": "strategy_bottom_fishing_instance_default",
        "accountId": "account_bybit_bottom_fishing",
        "accountCode": "BYBIT-BOTTOM-FISHING",
        "capability": "read_only",
        "dataQualityState": "waiting_initial_sync",
        "asOf": None,
        "balance": None,
        "equityHistory": [],
        "accountRisk": None,
        "positions": [],
        "orders": [],
        "fills": [],
        "pnl": None,
        "syncStatus": "waiting_initial_sync",
        "syncErrorCode": None,
    }
    assert {key: response.json()[key] for key in expected} == expected
    assert response.json()["isStale"] is True


def test_unbound_strategy_account_snapshot_returns_explicit_unbound_state(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "strategy-account-unbound.db")

    with TestClient(app) as client:
        response = projected_get(client, 
            "/api/v1/strategies/instances/strategy_short_term_w_instance_default/account-snapshot"
        )

    assert response.status_code == 200
    expected = {
        "strategyInstanceId": "strategy_short_term_w_instance_default",
        "accountId": None,
        "accountCode": None,
        "capability": None,
        "dataQualityState": "unbound",
        "asOf": None,
        "balance": None,
        "equityHistory": [],
        "accountRisk": None,
        "positions": [],
        "orders": [],
        "fills": [],
        "pnl": None,
        "syncStatus": "unbound",
        "syncErrorCode": "account_unbound",
    }
    assert {key: response.json()[key] for key in expected} == expected
    assert response.json()["finance"] is None


def test_cross_strategy_account_snapshot_uses_current_venue_positions(
    tmp_path: Path,
) -> None:
    """A closed strategy projection must not resurrect a venue-flat leg."""
    get_settings().database_path = str(tmp_path / "cross-strategy-current-position.db")

    with TestClient(app) as client:
        with connection() as db:
            payload = {
                "accountId": "bybit-live-main",
                "source": "bybit_live",
                "venue": "bybit",
                "asOf": "2026-08-21T00:00:00+00:00",
                "positions": [
                    {
                        "accountId": "bybit-live-main",
                        "instrumentId": "instrument_xau_usdt_perp",
                        "symbol": "XAUTUSDT",
                        "instrumentType": "crypto_perp",
                        "category": "linear",
                        "side": "Buy",
                        "netQuantity": "1",
                        "averagePrice": "2000",
                        "currentPrice": "2010",
                        "positionValue": "2010",
                        "currency": "USDT",
                    },
                    {
                        "accountId": "bybit-live-main",
                        "instrumentId": "instrument_btc_usdt_perp",
                        "symbol": "BTCUSDT",
                        "instrumentType": "crypto_perp",
                        "category": "linear",
                        "side": "Buy",
                        "netQuantity": "0.001",
                        "averagePrice": "100000",
                        "currentPrice": "100000",
                        "positionValue": "100",
                        "currency": "USDT",
                    },
                ],
            }
            db.execute(
                """
                INSERT INTO account_venue_snapshots (
                    account_id, source, venue, as_of, data_quality_state, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "bybit-live-main",
                    "bybit_live",
                    "bybit",
                    payload["asOf"],
                    "complete",
                    json.dumps(payload),
                ),
            )
        response = projected_get(client, 
            "/api/v1/strategies/instances/strategy_cross_venue_spread_instance_default/"
            "account-snapshot?accountId=bybit-live-main"
        )
        summary_response = projected_get(client, 
            "/api/v1/strategies/instances/strategy_cross_venue_spread_instance_default/"
            "account-snapshot?accountId=bybit-live-main&includeDetails=false"
        )

    assert response.status_code == 200
    positions = response.json()["positions"]
    assert [position["symbol"] for position in positions] == ["XAUTUSDT"]
    assert positions[0]["currentPrice"] == "2010"
    assert positions[0]["positionValue"] == "2010"
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["orders"] == []
    assert summary["fills"] == []
    assert summary["finance"] is None


def test_funding_current_positions_follow_active_order_groups_not_fill_history(
    tmp_path: Path, monkeypatch
) -> None:
    get_settings().database_path = str(tmp_path / "funding-current-position.db")
    initialize_database()
    with connection() as db:
        db.executemany(
            """
            INSERT INTO instruments (
                id,instrument_code,name,instrument_type,base_currency,quote_currency,
                settle_currency,quantity_unit,data_quality_state,created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            [
                (
                    "funding-spot",
                    "BTCUSDT-FUNDING-TEST-SPOT",
                    "BTC spot",
                    "crypto_spot",
                    "BTC",
                    "USDT",
                    "USDT",
                    "BTC",
                    "complete",
                    "2026-09-25T00:00:00+00:00",
                ),
                (
                    "funding-perp",
                    "BTCUSDT-FUNDING-TEST-PERP",
                    "BTC perpetual",
                    "crypto_perp",
                    "BTC",
                    "USDT",
                    "USDT",
                    "BTC",
                    "complete",
                    "2026-09-25T00:00:00+00:00",
                ),
            ],
        )

    group = {
        "openInstructionId": "open-1",
        "spotSide": "buy",
        "perpetualSide": "sell",
        "remainingSpotHolding": "0.0099",
        "remainingPerpetualQuantity": "0.01",
        "asOf": "2026-09-25T00:00:00+00:00",
    }
    plan = {
        "executionPlan": {
            "legs": [
                {
                    "role": "spot_leg",
                    "accountId": "bybit-live-main",
                    "instrumentId": "funding-spot",
                    "externalSymbol": "BTCUSDT",
                    "side": "buy",
                    "contractMultiplier": "1",
                },
                {
                    "role": "perpetual_leg",
                    "accountId": "bybit-live-main",
                    "instrumentId": "funding-perp",
                    "externalSymbol": "BTCUSDT",
                    "side": "sell",
                    "contractMultiplier": "1",
                },
            ]
        }
    }
    monkeypatch.setattr(
        "app.strategies.funding_workspace.list_funding_position_groups",
        lambda *, scope: [group] if scope == "active" else [],
    )
    monkeypatch.setattr("app.strategies.instruction_service.get_instruction", lambda _id: plan)

    marks = [
        {"instrumentId": "funding-spot", "currentPrice": "100"},
        {"instrumentId": "funding-perp", "currentPrice": "100"},
        # A lifetime-fill residual must not become a current position.
        {
            "instrumentId": "unrelated-fill-dust",
            "netQuantity": "0.000000759",
            "positionValue": "0.0000759",
        },
    ]
    positions, exposure = _funding_current_positions("bybit-live-main", marks)
    assert [(row.instrument_id, row.net_quantity) for row in positions] == [
        ("funding-spot", Decimal("0.0099")),
        ("funding-perp", Decimal("-0.01")),
    ]
    assert [row.instrument_type for row in positions] == ["crypto_spot", "crypto_perp"]
    assert Decimal(str(exposure["positionValue"])) == Decimal("1.99")
    assert Decimal(str(exposure["positionValueNet"])) == Decimal("0.01")

    monkeypatch.setattr(
        "app.strategies.funding_workspace.list_funding_position_groups",
        lambda *, scope: [],
    )
    closed, closed_exposure = _funding_current_positions("bybit-live-main", marks)
    assert closed == []
    assert closed_exposure == {
        "positionValue": None,
        "positionValueNet": None,
        "positionValueCurrency": None,
    }


def test_strategy_account_snapshot_aggregates_assets_in_account_currency(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "strategy-account-assets.db")

    with TestClient(app) as client:
        with connection() as db:
            db.execute(
                """
                INSERT INTO balance_snapshots (
                    id, account_id, currency, equity, available_balance, source,
                    data_quality_state, as_of, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "balance-bottom-usdt",
                    "account_bybit_bottom_fishing",
                    "USD",
                    "100",
                    "90",
                    "test",
                    "complete",
                    "2026-08-21T00:00:00+00:00",
                    "2026-08-21T00:00:00+00:00",
                    "balance-bottom-xpl",
                    "account_bybit_bottom_fishing",
                    "XPL",
                    "0.0136",
                    "0.0136",
                    "test",
                    "complete",
                    "2026-08-21T00:00:00+00:00",
                    "2026-08-21T00:00:00+00:00",
                ),
            )
        response = projected_get(client, 
            "/api/v1/strategies/instances/strategy_bottom_fishing_instance_default/account-snapshot"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["balance"]["currency"] == "USD"
    assert body["balance"]["equity"] == "100"
    assert body["equityHistory"] == [
        {
            "asOf": "2026-08-21T00:00:00Z",
            "equity": "100",
            "currency": "USD",
            "assetScope": "coin",
            "totalAssets": None,
            "equityDrawdown": None,
            "totalAssetsDrawdown": None,
            "equityDrawdownQuality": "baseline",
            "totalAssetsDrawdownQuality": "baseline",
        }
    ]


def test_strategy_account_snapshot_reports_single_asset_in_account_currency(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "strategy-account-single-asset.db")

    with TestClient(app) as client:
        with connection() as db:
            db.execute(
                """
                INSERT INTO balance_snapshots (
                    id, account_id, currency, equity, available_balance, source,
                    data_quality_state, as_of, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "balance-bottom-xpl",
                    "account_bybit_bottom_fishing",
                    "XPL",
                    "0.0136",
                    "0.0136",
                    "test",
                    "complete",
                    "2026-08-21T00:00:00+00:00",
                    "2026-08-21T00:00:00+00:00",
                    "balance-bottom-usd",
                    "account_bybit_bottom_fishing",
                    "USD",
                    "100",
                    "90",
                    "test",
                    "complete",
                    "2026-08-21T00:00:00+00:00",
                    "2026-08-21T00:00:00+00:00",
                ),
            )
        response = projected_get(client, 
            "/api/v1/strategies/instances/strategy_bottom_fishing_instance_default/account-snapshot"
        )

    assert response.json()["balance"]["currency"] == "USD"


def test_strategy_account_snapshot_uses_account_risk_for_live_account_funds(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "strategy-account-risk.db")

    with TestClient(app) as client:
        with connection() as db:
            db.execute(
                """
                INSERT INTO balance_snapshots (
                    id, account_id, currency, equity, available_balance, source,
                    data_quality_state, as_of, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "balance-bottom-xpl",
                    "account_bybit_bottom_fishing",
                    "XPL",
                    "0.0136",
                    "28944",
                    "bybit_live",
                    "complete",
                    "2026-08-21T00:00:00+00:00",
                    "2026-08-21T00:00:00+00:00",
                ),
            )
            db.execute(
                """
                INSERT INTO account_risk_snapshots (
                    account_id, as_of, currency, equity, margin, free_margin,
                    margin_level, data_quality_state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "account_bybit_bottom_fishing",
                    "2026-08-21T00:00:01+00:00",
                    "USDT",
                    "73436.92",
                    "1000",
                    "28944.58",
                    None,
                    "complete",
                    "2026-08-21T00:00:01+00:00",
                ),
            )
            db.execute(
                """
                INSERT INTO account_risk_snapshots (
                    account_id, as_of, currency, equity, margin, free_margin,
                    margin_level, data_quality_state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "account_bybit_bottom_fishing",
                    "2026-08-22T00:00:01+00:00",
                    "USD",
                    "100000",
                    "1000",
                    "60000",
                    None,
                    "complete",
                    "2026-08-22T00:00:01+00:00",
                ),
            )
        response = projected_get(client, 
            "/api/v1/strategies/instances/strategy_bottom_fishing_instance_default/account-snapshot"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["balance"]["source"] == "account_risk"
    assert body["balance"]["equity"] == "100000"
    assert body["balance"]["availableBalance"] == "60000"
    assert body["equityHistory"] == [
        {
            "asOf": "2026-08-22T00:00:01Z",
            "equity": "100000",
            "currency": "USD",
            "assetScope": "unspecified",
            "totalAssets": None,
            "equityDrawdown": None, "totalAssetsDrawdown": None,
            "equityDrawdownQuality": "baseline", "totalAssetsDrawdownQuality": "baseline",
        }
    ]


def test_strategy_account_snapshot_does_not_promote_legacy_account_pnl_to_strategy(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "strategy-account-pnl.db")

    with TestClient(app) as client:
        with connection() as db:
            db.execute(
                """
                INSERT INTO trade_commands (
                    id, idempotency_key, strategy_instance_id, account_id, instrument_id,
                    command_type, side, order_type, quantity, price, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "command-bottom-fishing-pnl",
                    "idempotency-bottom-fishing-pnl",
                    "strategy_bottom_fishing_instance_default",
                    "account_bybit_bottom_fishing",
                    "instrument_btc_usdt",
                    "create_order",
                    "buy",
                    "market",
                    "1",
                    None,
                    "accepted",
                    "2026-08-21T00:00:00+00:00",
                    "2026-08-21T00:00:00+00:00",
                ),
            )
            db.execute(
                """
                INSERT INTO pnl_results (
                    account_id, instrument_id, realized_pnl, trading_pnl, fees, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "account_bybit_bottom_fishing",
                    "instrument_btc_usdt",
                    "5.00",
                    "7.00",
                    "0.30",
                    "2026-08-21T00:00:00+00:00",
                ),
            )
        response = projected_get(client, 
            "/api/v1/strategies/instances/strategy_bottom_fishing_instance_default/account-snapshot"
        )

    assert response.status_code == 200
    assert response.json()["pnl"] is None
    assert response.json()["finance"]["realizedPnl"] is None
    assert "waiting_initial_sync" in response.json()["finance"]["issues"]
