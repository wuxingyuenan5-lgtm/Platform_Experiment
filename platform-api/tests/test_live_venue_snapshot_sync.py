from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection, initialize_database
from app.live_venue_snapshot_sync import (
    _persist_fills,
    discover_live_accounts,
    sync_venue_snapshots,
)
from app.main import app


class StubResponse:
    def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            request = httpx.Request("GET", "http://runtime.test/venue/account-snapshot")
            response = httpx.Response(self.status_code, request=request, json=self._payload)
            raise httpx.HTTPStatusError("runtime error", request=request, response=response)


def base_snapshot(account_id: str) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "source": "runtime-test",
        "accountId": account_id,
        "venue": "bybit" if "bybit" in account_id else "mt5",
        "identity": {"accountId": account_id},
        "balances": [
            {
                "source": "runtime-test",
                "externalBalanceId": f"{account_id}:USDT:1",
                "accountId": account_id,
                "equity": "1000",
                "availableBalance": "900",
                "currency": "USDT" if "bybit" in account_id else "USD",
                "asOf": now,
                "dataQualityState": "complete",
            }
        ],
        "positions": [],
        "orders": [],
        "fills": [],
        "accountRisk": {
            "source": "runtime-test",
            "accountId": account_id,
            "currency": "USDT" if "bybit" in account_id else "USD",
            "equity": "1000",
            "availableBalance": "900",
            "initialMargin": "10",
            "marginLevel": "100",
            "asOf": now,
            "dataQualityState": "complete",
        },
        "asOf": now,
        "dataQualityState": "complete",
    }


def bootstrap(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "live-venue-sync.db")
    initialize_database()


def activate_legacy_monitor_fixture() -> None:
    """Opt a test into the retired WW monitor binding for sync-isolation tests."""
    with connection() as db:
        db.execute(
            """
            UPDATE strategy_account_bindings
            SET status = 'active'
            WHERE strategy_instance_id = 'strategy_short_term_l_instance_default'
              AND account_id = 'account_mt5_short_term_a'
            """
        )


def test_discover_live_accounts_deduplicates_shared_uta_and_includes_ww_mt5(
    tmp_path: Path,
) -> None:
    bootstrap(tmp_path)

    assert discover_live_accounts() == [
        "account_bybit_bottom_fishing",
        "account_mt5_short_term_a",
        "bybit-live-main",
        "mt5-live-main",
    ]


def test_snapshot_sync_does_not_double_count_component_fills_after_terminal_aggregate(
    tmp_path: Path,
) -> None:
    bootstrap(tmp_path)
    timestamp = "2026-09-04T00:00:00+00:00"
    with connection() as db:
        db.execute(
            """
            INSERT INTO trade_commands (
                id, idempotency_key, strategy_instance_id, account_id, instrument_id,
                command_type, side, order_type, quantity, price, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'submit_order', 'buy', 'market', '1', NULL,
                      'filled', ?, ?)
            """,
            (
                "command-terminal-aggregate",
                "command-terminal-aggregate-key",
                "strategy_cross_venue_spread_instance_default",
                "bybit-live-main",
                "instrument_xau_usdt_perp",
                timestamp,
                timestamp,
            ),
        )
        db.execute(
            """
            INSERT INTO orders (
                id, command_id, account_id, instrument_id, symbol, side, order_type,
                quantity, price, status, external_order_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'XAUTUSDT', 'buy', 'market', '1', NULL, 'filled',
                      'external-order-1', ?, ?)
            """,
            (
                "platform-order-1",
                "command-terminal-aggregate",
                "bybit-live-main",
                "instrument_xau_usdt_perp",
                timestamp,
                timestamp,
            ),
        )
        db.execute(
            """
            INSERT INTO fills (
                id, order_id, account_id, instrument_id, side, quantity, price, occurred_at
            ) VALUES ('aggregate-fill', 'platform-order-1', 'bybit-live-main',
                      'instrument_xau_usdt_perp', 'buy', '1', '4462', ?)
            """,
            (timestamp,),
        )
        written, _realized, _fees = _persist_fills(
            db,
            "bybit-live-main",
            [
                {
                    "externalFillId": "component-fill-1",
                    "externalOrderId": "external-order-1",
                    "platformOrderId": "platform-order-1",
                    "instrumentId": "instrument_xau_usdt_perp",
                    "symbol": "XAUTUSDT",
                    "side": "buy",
                    "quantity": "0.5",
                    "price": "4462",
                    "fee": "0.1",
                    "occurredAt": timestamp,
                }
            ],
        )
        count = db.execute(
            "SELECT COUNT(*) AS count FROM fills WHERE order_id = 'platform-order-1'"
        ).fetchone()["count"]

    assert written == 0
    assert count == 1


def test_sync_persists_risk_and_deduplicates_fill_fingerprint(monkeypatch, tmp_path: Path) -> None:
    bootstrap(tmp_path)
    snapshot = base_snapshot("bybit-live-main")
    snapshot["fills"] = [
        {
            "platformOrderId": "external:bybit:1",
            "externalOrderId": "OID-1",
            "instrumentId": "instrument_btc_usdt",
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": "1",
            "price": "100",
            "occurredAt": "2026-08-24T00:00:01+00:00",
        }
    ]
    snapshot["orders"] = [
        {
            "platformOrderId": "external:bybit:1",
            "commandId": "external:bybit:1",
            "externalOrderId": "OID-1",
            "accountId": "bybit-live-main",
            "instrumentId": "instrument_btc_usdt",
            "symbol": "BTCUSDT",
            "side": "buy",
            "orderType": "limit",
            "quantity": "1",
            "price": "100",
            "status": "filled",
            "occurredAt": "2026-08-24T00:00:00+00:00",
            "asOf": "2026-08-24T00:00:01+00:00",
        }
    ]

    monkeypatch.setattr(
        "app.live_venue_snapshot_sync.runtime_get",
        lambda path, params=None: StubResponse(snapshot),
    )

    first = sync_venue_snapshots("bybit-live-main")
    second = sync_venue_snapshots("bybit-live-main")

    assert first.overall_status == "synced"
    assert first.fill_rows == 1
    assert second.overall_status == "synced"
    assert second.fill_rows == 0
    with connection() as db:
        fill_count = db.execute(
            "SELECT COUNT(*) AS c FROM fills WHERE account_id = ?",
            ("bybit-live-main",),
        ).fetchone()["c"]
        risk = db.execute(
            """
            SELECT equity, free_margin, margin_level
            FROM account_risk_snapshots
            WHERE account_id = ?
            """,
            ("bybit-live-main",),
        ).fetchone()
    assert fill_count == 1
    assert dict(risk) == {"equity": "1000", "free_margin": "900", "margin_level": "100"}


def test_missing_section_or_foreign_account_does_not_clear_positions(monkeypatch, tmp_path):
    bootstrap(tmp_path)
    account = "bybit-live-main"
    snapshot = base_snapshot(account)
    snapshot["positions"] = [
        {
            "accountId": account,
            "instrumentId": "instrument_btc_usdt",
            "netQuantity": "1",
            "averagePrice": "100",
        }
    ]
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync.runtime_get", lambda path, params=None: StubResponse(snapshot)
    )
    assert sync_venue_snapshots(account).overall_status == "synced"
    del snapshot["positions"]
    assert sync_venue_snapshots(account).overall_status == "failed"
    snapshot["positions"] = []
    snapshot["accountId"] = "account_bybit_bottom_fishing"
    assert sync_venue_snapshots(account).overall_status == "failed"
    with connection() as db:
        assert (
            db.execute(
                "SELECT net_quantity FROM positions WHERE account_id=?", (account,)
            ).fetchone()[0]
            == "1"
        )


def test_monitor_keeps_last_snapshot_during_sync_and_marks_stale(monkeypatch, tmp_path):
    from app.catalog import get_strategy_account_snapshot

    bootstrap(tmp_path)
    account = "account_mt5_short_term_a"
    snapshot = base_snapshot(account)
    snapshot["accountRisk"]["availableBalance"] = None
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync.runtime_get", lambda path, params=None: StubResponse(snapshot)
    )
    sync_venue_snapshots(account)
    with connection() as db:
        db.execute("UPDATE account_sync_status SET status='syncing' WHERE account_id=?", (account,))
    result = get_strategy_account_snapshot("strategy_short_term_l_instance_default")
    assert result.balance.equity == 1000
    assert result.balance.available_balance is None
    assert result.is_stale is False
    old = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    with connection() as db:
        db.execute("UPDATE account_venue_snapshots SET as_of=? WHERE account_id=?", (old, account))
    result = get_strategy_account_snapshot("strategy_short_term_l_instance_default")
    assert result.balance.equity == 1000
    assert result.is_stale is True
    assert result.data_quality_state == "stale"


def test_account_risk_currency_does_not_inherit_base_currency(monkeypatch, tmp_path):
    from app.catalog import get_strategy_account_snapshot

    bootstrap(tmp_path)
    snapshot = base_snapshot("bybit-live-main")
    snapshot["accountRisk"].update(
        currency="USD",
        assetScope="unified_trading",
        totalAssets="5000",
        walletBalance="990",
        assetOverviewQuality="complete",
    )
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync.runtime_get", lambda path, params=None: StubResponse(snapshot)
    )
    sync_venue_snapshots("bybit-live-main")
    result = get_strategy_account_snapshot("strategy_funding_arbitrage_instance_default")
    assert result.balance.currency == "USD"
    assert result.account_risk.total_assets == 5000
    assert result.account_risk.equity == 1000
    assert result.account_risk.wallet_balance == 990


def test_venue_fee_records_accumulate_and_conflicting_identity_rolls_back(monkeypatch, tmp_path):
    bootstrap(tmp_path)
    account = "account_mt5_short_term_a"
    snapshot = base_snapshot(account)
    snapshot["economicEvents"] = [
        {
            "source": "mt5",
            "accountId": account,
            "eventType": "fee",
            "externalEventId": "fee:1",
            "amount": "-0.1",
            "currency": "USD",
            "occurredAt": "2026-09-07T16:00:00Z",
        }
    ]
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync.runtime_get", lambda path, params=None: StubResponse(snapshot)
    )
    assert sync_venue_snapshots(account).overall_status == "synced"
    first = deepcopy(snapshot["economicEvents"][0])
    snapshot["economicEvents"][0].update(externalEventId="fee:2", amount="0.02")
    assert sync_venue_snapshots(account).overall_status == "synced"
    assert sync_venue_snapshots(account).overall_status == "synced"
    first["amount"] = "-9"
    snapshot["economicEvents"] = [first]
    snapshot["accountRisk"]["equity"] = "0"
    assert sync_venue_snapshots(account).overall_status == "failed"
    with connection() as db:
        assert (
            db.execute(
                "SELECT COUNT(*) FROM venue_account_events WHERE account_id=?", (account,)
            ).fetchone()[0]
            == 2
        )
        assert (
            db.execute(
                "SELECT equity FROM account_risk_snapshots WHERE account_id=?", (account,)
            ).fetchone()[0]
            == "1000"
        )


def test_sync_failure_isolated_and_does_not_commit_partial_rows(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bootstrap(tmp_path)
    activate_legacy_monitor_fixture()

    def fake_runtime_get(path, params=None):
        account_id = params["accountId"]
        if account_id == "account_mt5_short_term_a":
            return StubResponse({"detail": "MT5 primary account restore failed"}, status_code=503)
        snapshot = base_snapshot(account_id)
        snapshot["fills"] = [
            {
                "platformOrderId": "external:test:1",
                "externalOrderId": "",
                "instrumentId": "instrument_xau_usd",
                "symbol": "XAUUSD+",
                "side": "buy",
                "quantity": "0.01",
                "price": "2400",
                # intentionally missing occurredAt for deterministic identity failure
            }
        ]
        return StubResponse(snapshot)

    monkeypatch.setattr("app.live_venue_snapshot_sync.runtime_get", fake_runtime_get)

    result = sync_venue_snapshots("account_mt5_short_term_a")

    assert result.overall_status == "failed"
    assert result.synced_accounts == []
    assert [(item.account_id, item.status, item.error_code) for item in result.failed_accounts] == [
        ("account_mt5_short_term_a", "restore_failed", "restore_failed")
    ]
    with connection() as db:
        status = db.execute(
            "SELECT status, error_code FROM account_sync_status WHERE account_id = ?",
            ("account_mt5_short_term_a",),
        ).fetchone()
        baseline_balances = db.execute(
            "SELECT COUNT(*) AS c FROM balance_snapshots WHERE account_id = ?",
            ("account_mt5_short_term_a",),
        ).fetchone()["c"]
    assert status is not None
    assert dict(status) == {"status": "restore_failed", "error_code": "restore_failed"}

    invalid_snapshot = base_snapshot("account_mt5_short_term_a")
    invalid_snapshot["fills"] = [
        {
            "platformOrderId": "external:test:1",
            "externalOrderId": "",
            "instrumentId": "instrument_xau_usd",
            "symbol": "XAUUSD+",
            "side": "buy",
            "quantity": "0.01",
            "price": "2400",
        }
    ]
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync.runtime_get",
        lambda path, params=None: StubResponse(invalid_snapshot),
    )
    with pytest.raises(ValueError, match="authoritative identity"):
        from app.live_venue_snapshot_sync import _sync_one_account

        _sync_one_account("account_mt5_short_term_a")
    with connection() as db:
        balances = db.execute(
            "SELECT COUNT(*) AS c FROM balance_snapshots WHERE account_id = ?",
            ("account_mt5_short_term_a",),
        ).fetchone()["c"]
    assert balances == baseline_balances


def test_strategy_account_snapshot_returns_ready_sync_status_and_account_risk(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bootstrap(tmp_path)
    with TestClient(app) as client:
        activate_legacy_monitor_fixture()
        monkeypatch.setattr(
            "app.live_venue_snapshot_sync.runtime_get",
            lambda path, params=None: StubResponse(base_snapshot("account_mt5_short_term_a")),
        )
        sync_venue_snapshots("account_mt5_short_term_a")
        response = client.get(
            "/api/v1/strategies/instances/strategy_short_term_l_instance_default/account-snapshot"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["syncStatus"] == "ready"
    assert body["accountRisk"]["marginLevel"] == "100"
    assert body["accountCode"] == "MT5-SHORT-TERM-A"

    with TestClient(app) as client:
        activate_legacy_monitor_fixture()
        overview = client.get("/api/v1/strategies/management-overview")

    assert overview.status_code == 200
    by_desk = {item["deskKey"]: item for item in overview.json()}
    assert by_desk["shortLineTraderL"]["primaryAccountDataQualityState"] == "complete"


def test_sync_without_position_keeps_realized_and_fees_but_clears_unrealized(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bootstrap(tmp_path)
    with connection() as db:
        db.execute(
            """
            INSERT INTO pnl_results (
                account_id, instrument_id, realized_pnl, trading_pnl, fees, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "bybit-live-main",
                "instrument_btc_usdt",
                "12.5",
                "3.4",
                "0.6",
                "2026-08-24T00:00:00+00:00",
            ),
        )
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync.runtime_get",
        lambda path, params=None: StubResponse(base_snapshot("bybit-live-main")),
    )

    sync_venue_snapshots("bybit-live-main")

    with connection() as db:
        row = db.execute(
            """
            SELECT realized_pnl, trading_pnl, fees
            FROM pnl_results
            WHERE account_id = ? AND instrument_id = ?
            """,
            ("bybit-live-main", "instrument_btc_usdt"),
        ).fetchone()
    assert dict(row) == {"realized_pnl": "12.5", "trading_pnl": "0", "fees": "0.6"}


def test_sync_resets_unrealized_pnl_when_authoritative_position_is_flat(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bootstrap(tmp_path)
    with connection() as db:
        db.execute(
            """
            INSERT INTO positions (
                account_id, instrument_id, net_quantity, average_price, updated_at
            ) VALUES ('bybit-live-main', 'instrument_xau_usdt_perp', '1', '2000', ?)
            """,
            ("2026-08-24T00:00:00+00:00",),
        )
        db.execute(
            """
            INSERT INTO pnl_results (
                account_id, instrument_id, realized_pnl, trading_pnl, fees, updated_at
            ) VALUES ('bybit-live-main', 'instrument_xau_usdt_perp', '2', '9', '0.5', ?)
            """,
            ("2026-08-24T00:00:00+00:00",),
        )
    snapshot = base_snapshot("bybit-live-main")
    snapshot["positions"] = []
    snapshot["fills"] = []
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync.runtime_get",
        lambda path, params=None: StubResponse(snapshot),
    )

    sync_venue_snapshots("bybit-live-main")

    with connection() as db:
        row = db.execute(
            """
            SELECT realized_pnl, trading_pnl, fees
            FROM pnl_results
            WHERE account_id = 'bybit-live-main'
              AND instrument_id = 'instrument_xau_usdt_perp'
            """
        ).fetchone()
    assert dict(row) == {"realized_pnl": "2", "trading_pnl": "0", "fees": "0.5"}


def test_sync_persists_unmapped_mt5_monitoring_identity_without_duplicates(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bootstrap(tmp_path)
    snapshot = base_snapshot("account_mt5_short_term_a")
    snapshot["venue"] = "mt5"
    snapshot["dataQualityState"] = "external_unmapped"
    balances = cast(list[dict[str, Any]], snapshot["balances"])
    balances[0]["currency"] = "USD"
    account_risk = cast(dict[str, Any], snapshot["accountRisk"])
    account_risk["currency"] = "USD"
    snapshot["positions"] = [
        {
            "source": "runtime-test",
            "externalPositionId": "1",
            "accountId": "account_mt5_short_term_a",
            "instrumentId": "monitor:mt5:account_mt5_short_term_a:abc123",
            "symbol": "XAUUSD+",
            "netQuantity": "0.01",
            "averagePrice": "2400",
            "currentPrice": "2401",
            "unrealizedPnl": "1.2",
            "currency": "USD",
            "asOf": "2026-08-24T00:00:00+00:00",
            "dataQualityState": "external_unmapped",
        }
    ]
    snapshot["orders"] = [
        {
            "source": "runtime-test",
            "externalOrderId": "2",
            "platformOrderId": "external:mt5_live:2",
            "commandId": "external:mt5_live:2",
            "accountId": "account_mt5_short_term_a",
            "instrumentId": "monitor:mt5:account_mt5_short_term_a:abc123",
            "symbol": "XAUUSD+",
            "side": "buy",
            "orderType": "limit",
            "quantity": "0.01",
            "price": "2400",
            "status": "accepted",
            "filledQuantity": "0",
            "remainingQuantity": "0.01",
            "occurredAt": "2026-08-24T00:00:00+00:00",
            "asOf": "2026-08-24T00:00:00+00:00",
            "dataQualityState": "external_unmapped",
        }
    ]
    snapshot["fills"] = [
        {
            "source": "runtime-test",
            "externalFillId": "3",
            "externalOrderId": "2",
            "platformOrderId": "external:mt5_live:2",
            "commandId": "external:mt5_live:2",
            "accountId": "account_mt5_short_term_a",
            "instrumentId": "monitor:mt5:account_mt5_short_term_a:abc123",
            "symbol": "XAUUSD+",
            "side": "buy",
            "quantity": "0.01",
            "price": "2400.5",
            "fee": "0.1",
            "currency": "USD",
            "occurredAt": "2026-08-24T00:00:01+00:00",
            "dataQualityState": "external_unmapped",
        }
    ]
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync.runtime_get",
        lambda path, params=None: StubResponse(snapshot),
    )

    activate_legacy_monitor_fixture()
    first = sync_venue_snapshots("account_mt5_short_term_a")
    second = sync_venue_snapshots("account_mt5_short_term_a")

    assert first.overall_status == "synced"
    assert first.fill_rows == 1
    assert second.overall_status == "synced"
    assert second.fill_rows == 0
    with connection() as db:
        position = db.execute(
            "SELECT instrument_id, net_quantity FROM positions WHERE account_id = ?",
            ("account_mt5_short_term_a",),
        ).fetchone()
        fill_count = db.execute(
            "SELECT COUNT(*) AS c FROM fills WHERE account_id = ? AND instrument_id = ?",
            ("account_mt5_short_term_a", "monitor:mt5:account_mt5_short_term_a:abc123"),
        ).fetchone()["c"]
    assert dict(position) == {
        "instrument_id": "monitor:mt5:account_mt5_short_term_a:abc123",
        "net_quantity": "0.01",
    }
    assert fill_count == 1


def test_current_only_sync_skips_history_persistence_and_keeps_existing_history(
    monkeypatch, tmp_path: Path
) -> None:
    bootstrap(tmp_path)
    account = "bybit-live-main"
    historical = base_snapshot(account)
    historical["orders"] = [
        {
            "platformOrderId": "history-order-1",
            "externalOrderId": "history-external-1",
            "accountId": account,
            "instrumentId": "instrument_btc_usdt",
            "symbol": "BTCUSDT",
            "side": "buy",
            "orderType": "limit",
            "quantity": "1",
            "price": "100",
            "status": "filled",
            "occurredAt": historical["asOf"],
            "asOf": historical["asOf"],
        }
    ]
    historical["fills"] = [
        {
            "externalFillId": "history-fill-1",
            "externalOrderId": "history-external-1",
            "platformOrderId": "history-order-1",
            "instrumentId": "instrument_btc_usdt",
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": "1",
            "price": "100",
            "occurredAt": historical["asOf"],
        }
    ]
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync.runtime_get",
        lambda path, params=None: StubResponse(historical),
    )
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync._sync_account_finance", lambda account_id: None
    )
    sync_venue_snapshots(account)

    current = base_snapshot(account)
    current["asOf"] = "2026-09-15T00:00:00+00:00"
    current["balances"][0]["asOf"] = current["asOf"]
    current["balances"][0]["equity"] = "1200"
    current["accountRisk"]["asOf"] = current["asOf"]
    current["accountRisk"]["equity"] = "1200"
    current["orders"] = [{**historical["orders"][0], "externalOrderId": "new-order"}]
    current["fills"] = [{**historical["fills"][0], "externalFillId": "new-fill"}]
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync.runtime_get",
        lambda path, params=None: StubResponse(current),
    )
    result = sync_venue_snapshots(account, include_history=False)

    assert result.order_rows == 0
    assert result.fill_rows == 0
    with connection() as db:
        counts = db.execute(
            "SELECT (SELECT COUNT(*) FROM orders WHERE account_id=?) AS orders, "
            "(SELECT COUNT(*) FROM fills WHERE account_id=?) AS fills",
            (account, account),
        ).fetchone()
        payload = db.execute(
            "SELECT payload_json FROM account_venue_snapshots WHERE account_id=?", (account,)
        ).fetchone()[0]
    assert dict(counts) == {"orders": 1, "fills": 1}
    assert json.loads(payload)["orders"][0]["externalOrderId"] == "history-external-1"


def test_history_refresh_preserves_newer_current_balance_positions_and_as_of(
    monkeypatch, tmp_path: Path
) -> None:
    bootstrap(tmp_path)
    account = "bybit-live-main"
    current = base_snapshot(account)
    current["asOf"] = "2026-09-15T00:00:00+00:00"
    current["balances"][0]["asOf"] = current["asOf"]
    current["balances"][0]["equity"] = "1500"
    current["accountRisk"]["asOf"] = current["asOf"]
    current["accountRisk"]["equity"] = "1500"
    current["positions"] = [
        {
            "accountId": account,
            "instrumentId": "instrument_btc_usdt",
            "netQuantity": "2",
            "averagePrice": "100",
            "asOf": current["asOf"],
        }
    ]
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync.runtime_get",
        lambda path, params=None: StubResponse(current),
    )
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync._sync_account_finance", lambda account_id: None
    )
    sync_venue_snapshots(account)

    historical = base_snapshot(account)
    historical["asOf"] = "2026-09-14T00:00:00+00:00"
    historical["orders"] = []
    historical["fills"] = []
    monkeypatch.setattr(
        "app.account_history_sync.runtime_get",
        lambda path, params=None: StubResponse(historical),
    )
    monkeypatch.setattr("app.account_history_sync._sync_account_finance", lambda account_id: None)
    from app.account_history_sync import sync_account_history

    sync_account_history(account)

    with connection() as db:
        snapshot = db.execute(
            "SELECT as_of, payload_json FROM account_venue_snapshots WHERE account_id=?",
            (account,),
        ).fetchone()
        position = db.execute(
            "SELECT net_quantity FROM positions WHERE account_id=? AND instrument_id=?",
            (account, "instrument_btc_usdt"),
        ).fetchone()
    payload = json.loads(snapshot["payload_json"])
    assert snapshot["as_of"] == current["asOf"]
    assert payload["balances"][0]["equity"] == "1500"
    assert payload["positions"][0]["netQuantity"] == "2"
    assert position["net_quantity"] == "2"
