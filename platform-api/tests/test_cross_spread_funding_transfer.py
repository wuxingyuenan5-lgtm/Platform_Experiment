from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app

QUOTE_URL = "/api/v1/trading/cross-spread/funding-transfer/quote"
CREATE_URL = "/api/v1/trading/cross-spread/funding-transfer"


def _readiness(
    source_account_id: str,
    destination_account_id: str,
    *,
    bybit: str = "260.000000000000000001",
    mt5: str = "100",
    ready: bool = True,
    simulation: bool = True,
) -> dict[str, object]:
    source_is_mt5 = "mt5" in source_account_id.lower()
    return {
        "ready": ready,
        "sourceAccountId": source_account_id,
        "destinationAccountId": destination_account_id,
        "currency": "USDT",
        "transferableBalance": (mt5 if source_is_mt5 else bybit) if ready else None,
        "fromAccountType": (
            "simulation" if simulation else ("TradFi" if source_is_mt5 else "UNIFIED")
        ),
        "toAccountType": "simulation" if simulation else ("UNIFIED" if source_is_mt5 else "TradFi"),
        "reason": None if ready else "BYBIT_WALLET_ACCOUNT_TRANSFER_PERMISSION_REQUIRED",
        "checkedAt": "2026-08-22T00:00:00+00:00",
    }


def _payload(
    *,
    key: str = "funding-transfer-001",
    direction: str = "bybit_to_mt5",
    amount: object = "80.0000000000000000005",
) -> dict[str, object]:
    return {"idempotencyKey": key, "direction": direction, "amount": amount}


def _configure_quote(monkeypatch, callback=_readiness) -> None:
    monkeypatch.setattr(
        "app.strategies.capital_transfer._runtime_transfer_readiness",
        callback,
    )


def test_quote_uses_decimal_half_difference_and_never_turns_failure_into_zero(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "funding-transfer-quote.db")
    _configure_quote(monkeypatch)
    with TestClient(app) as client:
        quote = client.get(QUOTE_URL)
    assert quote.status_code == 200, quote.text
    assert quote.json()["suggestedDirection"] == "bybit_to_mt5"
    assert quote.json()["suggestedAmount"] == "80.0000000000000000005"

    def one_side_unavailable(
        source_account_id: str,
        destination_account_id: str,
    ) -> dict[str, object]:
        return _readiness(
            source_account_id,
            destination_account_id,
            ready="bybit" not in source_account_id.lower(),
        )

    _configure_quote(monkeypatch, one_side_unavailable)
    with TestClient(app) as client:
        unavailable = client.get(QUOTE_URL)
    assert unavailable.status_code == 200
    assert unavailable.json()["bybitTransferable"]["amount"] is None
    assert unavailable.json()["bybitTransferable"]["dataQualityState"] == "unavailable"
    assert unavailable.json()["suggestedAmount"] is None
    assert unavailable.json()["mode"] == "unavailable"

    with TestClient(app) as client:
        blocked = client.post(CREATE_URL, json=_payload(key="permission-blocked", amount="10"))
    assert blocked.status_code == 423
    assert "ACCOUNT_TRANSFER_PERMISSION_REQUIRED" in blocked.json()["detail"]


@pytest.mark.parametrize(
    ("direction", "expected_path"),
    [
        (
            "bybit_to_mt5",
            [
                ("bybit-live-main", "fake:bybit-funding"),
                ("fake:bybit-funding", "mt5-live-main"),
            ],
        ),
        (
            "mt5_to_bybit",
            [
                ("mt5-live-main", "fake:bybit-funding"),
                ("fake:bybit-funding", "bybit-live-main"),
            ],
        ),
    ],
)
def test_fake_transfer_executes_two_internal_steps_without_trading_objects(
    monkeypatch,
    tmp_path: Path,
    direction: str,
    expected_path: list[tuple[str, str]],
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / f"funding-transfer-{direction}.db")
    _configure_quote(
        monkeypatch,
        lambda source, destination: _readiness(
            source,
            destination,
            bybit="300",
            mt5="300",
        ),
    )
    calls: list[tuple[str, str, Decimal]] = []

    def transfer_step(**kwargs) -> dict[str, object]:
        calls.append(
            (
                kwargs["source_account_id"],
                kwargs["destination_account_id"],
                kwargs["amount"],
            )
        )
        return {
            "status": "completed",
            "externalTransferId": f"fake-step-{len(calls)}",
        }

    monkeypatch.setattr(
        "app.strategies.capital_transfer._runtime_transfer_step",
        transfer_step,
    )
    with TestClient(app) as client:
        response = client.post(
            CREATE_URL,
            json=_payload(key=f"two-step-{direction}", direction=direction, amount="10.25"),
        )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"
    assert [(source, destination) for source, destination, _ in calls] == expected_path
    assert all(amount == Decimal("10.25") for _, _, amount in calls)
    assert response.json()["requestedBy"] == settings.development_user_id
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM strategy_runs").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM execution_batches").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM trade_commands").fetchone()[0] == 0


def test_transfer_replay_conflict_and_public_payload_boundary(monkeypatch, tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "funding-transfer-idempotency.db")
    _configure_quote(
        monkeypatch,
        lambda source, destination: _readiness(
            source,
            destination,
            bybit="300",
            mt5="100",
        ),
    )
    calls = 0

    def transfer_step(**kwargs) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"status": "completed", "externalTransferId": f"step-{calls}"}

    monkeypatch.setattr(
        "app.strategies.capital_transfer._runtime_transfer_step",
        transfer_step,
    )
    with TestClient(app) as client:
        first = client.post(CREATE_URL, json=_payload(amount="10.125"))
        replay = client.post(CREATE_URL, json=_payload(amount="10.125"))
        conflict = client.post(CREATE_URL, json=_payload(amount="10.126"))
        spoofed = client.post(
            CREATE_URL,
            json={**_payload(key="spoofed"), "accountId": "forged", "uid": "forged"},
        )
        numeric = client.post(CREATE_URL, json=_payload(key="numeric", amount=10.125))
    assert first.status_code == replay.status_code == 200
    assert replay.json() == first.json()
    assert calls == 2
    assert conflict.status_code == 409
    assert spoofed.status_code == 422
    assert numeric.status_code == 422


def test_second_step_failure_leaves_funds_in_funding_and_unknown_is_not_retried(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "funding-transfer-partial.db")
    _configure_quote(
        monkeypatch,
        lambda source, destination: _readiness(
            source,
            destination,
            bybit="300",
            mt5="100",
        ),
    )
    calls = 0

    def partial_step(**kwargs) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 2:
            request = httpx.Request("POST", "http://runtime/transfer")
            response = httpx.Response(409, request=request)
            raise httpx.HTTPStatusError("rejected", request=request, response=response)
        return {"status": "completed", "externalTransferId": "step-one"}

    monkeypatch.setattr(
        "app.strategies.capital_transfer._runtime_transfer_step",
        partial_step,
    )
    with TestClient(app) as client:
        failed = client.post(CREATE_URL, json=_payload(key="partial", amount="10"))
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    assert failed.json()["currentLocation"] == "funding"
    assert failed.json()["externalTransferId"] == "step-one"

    calls = 0

    def unknown_step(**kwargs) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"status": "result_unknown", "externalTransferId": "unknown-one"}

    monkeypatch.setattr(
        "app.strategies.capital_transfer._runtime_transfer_step",
        unknown_step,
    )
    with TestClient(app) as client:
        unknown = client.post(CREATE_URL, json=_payload(key="unknown", amount="10"))
        replay = client.post(CREATE_URL, json=_payload(key="unknown", amount="10"))
    assert unknown.json()["status"] == "result_unknown"
    assert replay.json() == unknown.json()
    assert calls == 1

    monkeypatch.setattr(
        "app.strategies.capital_transfer._runtime_transfer_status",
        lambda row: {
            "status": "completed",
            "externalTransferId": row["external_transfer_id"],
        },
    )
    with TestClient(app) as client:
        reconciled = client.get(
            f"/api/v1/trading/cross-spread/funding-transfers/{unknown.json()['transferId']}"
        )
    assert reconciled.status_code == 200
    assert reconciled.json()["status"] == "completed"
    with connection() as db:
        assert (
            db.execute(
                """
                SELECT COUNT(*) FROM execution_resource_claims
                WHERE owner_id = ? AND status = 'active'
                """,
                (unknown.json()["transferId"],),
            ).fetchone()[0]
            == 0
        )


def test_live_transfer_uses_one_official_runtime_step_and_releases_claims(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "funding-transfer-live.db")
    _configure_quote(
        monkeypatch,
        lambda source, destination: _readiness(
            source,
            destination,
            bybit="300",
            mt5="100",
            simulation=False,
        ),
    )
    calls: list[dict[str, object]] = []

    def transfer_step(**kwargs) -> dict[str, object]:
        calls.append(kwargs)
        return {"status": "completed", "externalTransferId": "official-transfer-1"}

    monkeypatch.setattr(
        "app.strategies.capital_transfer._runtime_transfer_step",
        transfer_step,
    )
    with TestClient(app) as client:
        created = client.post(CREATE_URL, json=_payload(key="live-direct", amount="25"))
    assert created.status_code == 200, created.text
    assert created.json()["status"] == "completed"
    assert created.json()["mode"] == "automated"
    assert created.json()["externalTransferId"] == "official-transfer-1"
    assert len(calls) == 1
    assert calls[0]["source_account_id"] == "bybit-live-main"
    assert calls[0]["destination_account_id"] == "mt5-live-main"
    assert calls[0]["source_currency"] == "USDT"
    assert calls[0]["destination_currency"] == "USDT"
    assert calls[0]["amount"] == Decimal("25")
    with connection() as db:
        assert (
            db.execute(
                """
                SELECT COUNT(*) FROM execution_resource_claims
                WHERE owner_id = ? AND status = 'active'
                """,
                (created.json()["transferId"],),
            ).fetchone()[0]
            == 0
        )
        assert (
            db.execute(
                """
                SELECT COUNT(*) FROM execution_balance_reservations
                WHERE owner_id = ? AND status = 'active'
                """,
                (created.json()["transferId"],),
            ).fetchone()[0]
            == 0
        )
