from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.live_venue_snapshot_sync import discover_live_accounts, sync_venue_snapshots
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
                "asOf": "2026-08-24T00:00:00+00:00",
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
            "asOf": "2026-08-24T00:00:00+00:00",
            "dataQualityState": "complete",
        },
        "asOf": "2026-08-24T00:00:00+00:00",
        "dataQualityState": "complete",
    }


def bootstrap(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "live-venue-sync.db")
    with TestClient(app):
        pass


def test_discover_live_accounts_deduplicates_shared_uta_and_excludes_short_b(
    tmp_path: Path,
) -> None:
    bootstrap(tmp_path)

    assert discover_live_accounts() == [
        "account_bybit_bottom_fishing",
        "account_mt5_short_term_a",
        "bybit-live-main",
        "mt5-live-main",
    ]


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


def test_sync_failure_isolated_and_does_not_commit_partial_rows(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bootstrap(tmp_path)

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
    monkeypatch.setattr(
        "app.live_venue_snapshot_sync.runtime_get",
        lambda path, params=None: StubResponse(base_snapshot("account_mt5_short_term_a")),
    )
    sync_venue_snapshots("account_mt5_short_term_a")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/strategies/instances/strategy_short_term_l_instance_default/account-snapshot"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["syncStatus"] == "ready"
    assert body["accountRisk"]["marginLevel"] == "100"
    assert body["accountCode"] == "MT5-SHORT-TERM-A"


def test_sync_without_current_window_keeps_existing_historical_pnl(
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
    assert dict(row) == {"realized_pnl": "12.5", "trading_pnl": "3.4", "fees": "0.6"}


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
