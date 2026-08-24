from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from sqlite3 import OperationalError
from threading import Barrier, Lock, local
from typing import Any, cast
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection, initialize_database
from app.execution_batches import (
    _batch_terminal_release_is_safe,
    _claim_batch_execution_resources,
    _reservation_requirement_for_leg,
    create_execution_batch,
)
from app.main import app
from app.schemas import CreateExecutionBatchRequest, TradeCommandResponse

STRATEGY_INSTANCE_ID = "strategy_funding_arbitrage_instance_default"


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
                    "occurred_at": "2026-07-19T10:00:00+00:00",
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
                    "occurred_at": "2026-07-19T10:00:01+00:00",
                    "reason": None,
                },
            ]

    return FakeResponse()


def batch_payload(
    account_id: str,
    spot_id: str,
    perp_id: str,
    *,
    idempotency_key: str,
) -> dict[str, object]:
    return {
        "idempotencyKey": idempotency_key,
        "strategyInstanceId": STRATEGY_INSTANCE_ID,
        "accountId": account_id,
        "strategyKey": "funding_arbitrage",
        "direction": "collect",
        "legs": [
            {
                "role": "spot",
                "instrumentId": spot_id,
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "1",
                "price": "100",
            },
            {
                "role": "perp",
                "instrumentId": perp_id,
                "symbol": "BTCUSDT-PERP",
                "side": "sell",
                "orderType": "limit",
                "quantity": "1",
                "price": "100",
            },
        ],
    }


def cross_strategy_payload(*, idempotency_key: str) -> dict[str, object]:
    payload = batch_payload(
        "account_sim_usdt",
        "instrument_btc_usdt",
        "instrument_btc_usdt_perp",
        idempotency_key=idempotency_key,
    )
    payload.update(
        {
            "strategyInstanceId": "strategy_cross_venue_spread_instance_default",
            "strategyKey": "cross_venue_spread",
            "direction": "close_short_spread",
        }
    )
    return payload


def insert_persisted_batch(
    *,
    payload: dict[str, object],
    status: str,
    leg_status: str = "pending",
) -> str:
    batch_id = str(uuid4())
    timestamp = "2026-08-13T00:00:00+00:00"
    legs = payload["legs"]
    assert isinstance(legs, list)
    with connection() as db:
        db.execute(
            """
            INSERT INTO execution_batches (
                id, idempotency_key, strategy_instance_id, account_id,
                strategy_key, direction, status, requires_manual_intervention,
                failure_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_id,
                payload["idempotencyKey"],
                payload["strategyInstanceId"],
                payload["accountId"],
                payload["strategyKey"],
                payload["direction"],
                status,
                int(status == "manual_intervention"),
                "persisted unresolved disposition" if status == "manual_intervention" else None,
                timestamp,
                timestamp,
            ),
        )
        for sequence, leg in enumerate(legs, start=1):
            assert isinstance(leg, dict)
            db.execute(
                """
                INSERT INTO execution_batch_legs (
                    id, batch_id, sequence, role, account_id, instrument_id, symbol,
                    side, order_type, quantity, price, order_id, status,
                    failure_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    batch_id,
                    sequence,
                    leg["role"],
                    leg.get("accountId") or payload["accountId"],
                    leg["instrumentId"],
                    leg["symbol"],
                    leg["side"],
                    leg["orderType"],
                    leg["quantity"],
                    leg.get("price"),
                    None,
                    leg_status if sequence == 1 else "pending",
                    None,
                    timestamp,
                    timestamp,
                ),
            )
    return batch_id


def test_execution_batch_becomes_hedged_and_creates_two_commands(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "hedged.db")
    runtime_calls = 0

    def runtime_post(*args, **kwargs):
        nonlocal runtime_calls
        runtime_calls += 1
        return filled_runtime_response(kwargs["json"])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", runtime_post)

    account_id = "account_sim_usdt"
    spot_id = "instrument_btc_usdt"
    perp_id = "instrument_btc_usdt_perp"
    payload = batch_payload(
        account_id,
        spot_id,
        perp_id,
        idempotency_key="funding-batch-hedged-001",
    )

    with TestClient(app) as client:
        first = client.post("/api/v1/trading/execution-batches", json=payload)
        second = client.post("/api/v1/trading/execution-batches", json=payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json() == first.json()
        batch = first.json()
        assert batch["status"] == "hedged"
        assert batch["requiresManualIntervention"] is False
        assert [leg["status"] for leg in batch["legs"]] == ["filled", "filled"]
        assert runtime_calls == 2

        with connection() as db:
            command_rows = db.execute(
                """
                SELECT idempotency_key
                FROM trade_commands
                WHERE strategy_instance_id = ?
                ORDER BY idempotency_key
                """,
                (STRATEGY_INSTANCE_ID,),
            ).fetchall()
        assert [row["idempotency_key"] for row in command_rows] == [
            "funding-batch-hedged-001:perp",
            "funding-batch-hedged-001:spot",
        ]

        spot = client.get(f"/api/v1/accounts/{account_id}/positions/{spot_id}")
        perp = client.get(f"/api/v1/accounts/{account_id}/positions/{perp_id}")
        assert spot.json()["netQuantity"] == "1"
        assert perp.json()["netQuantity"] == "-1"

        stored = client.get(f"/api/v1/trading/execution-batches/{batch['batchId']}")
        assert stored.status_code == 200
        assert stored.json()["status"] == "hedged"


def test_second_leg_unknown_requires_manual_intervention(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "manual.db")
    call_count = 0

    def runtime_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return filled_runtime_response(kwargs["json"])
        raise httpx.ConnectError("runtime unavailable")

    monkeypatch.setattr("app.trade_command_execution.httpx.post", runtime_post)

    account_id = "account_sim_usdt"
    spot_id = "instrument_btc_usdt"
    perp_id = "instrument_btc_usdt_perp"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/execution-batches",
            json=batch_payload(
                account_id,
                spot_id,
                perp_id,
                idempotency_key="funding-batch-manual-001",
            ),
        )

        assert response.status_code == 200
        batch = response.json()
        assert batch["status"] == "manual_intervention"
        assert batch["requiresManualIntervention"] is True
        assert batch["legs"][0]["status"] == "filled"
        assert batch["legs"][1]["status"] == "result_unknown"
        assert batch["legs"][1]["orderId"] is not None

        spot = client.get(f"/api/v1/accounts/{account_id}/positions/{spot_id}")
        perp = client.get(f"/api/v1/accounts/{account_id}/positions/{perp_id}")
        assert spot.status_code == 200
        assert spot.json()["netQuantity"] == "1"
        assert perp.status_code == 404


def test_global_claim_allows_only_one_concurrent_strategy_batch_before_commands(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "global-claim-race.db")
    initialize_database()

    from app import execution_batches

    real_assert_execution_allowed = execution_batches.assert_execution_allowed
    admission_barrier = Barrier(2)
    admission_state = local()

    def synchronized_execution_admission(strategy_instance_id: str, account_ids: list[str]):
        real_assert_execution_allowed(strategy_instance_id, account_ids)
        if not getattr(admission_state, "synchronized", False):
            admission_state.synchronized = True
            admission_barrier.wait(timeout=5)

    command_keys: list[str] = []
    command_lock = Lock()

    def result_unknown_command(request) -> TradeCommandResponse:
        with command_lock:
            command_keys.append(request.idempotency_key)
        timestamp = datetime.now(UTC)
        return TradeCommandResponse(
            tradeCommandId=str(uuid4()),
            idempotencyKey=request.idempotency_key,
            strategyInstanceId=request.strategy_instance_id,
            accountId=request.account_id,
            instrumentId=request.instrument_id,
            platformOrderId=None,
            status="result_unknown",
            createdAt=timestamp,
            updatedAt=timestamp,
        )

    monkeypatch.setattr(
        execution_batches, "assert_execution_allowed", synchronized_execution_admission
    )
    monkeypatch.setattr(execution_batches, "create_trade_command", result_unknown_command)

    requests = [
        CreateExecutionBatchRequest.model_validate(
            batch_payload(
                "account_sim_usdt",
                "instrument_btc_usdt",
                "instrument_btc_usdt_perp",
                idempotency_key="funding-global-race-001",
            )
        ),
        CreateExecutionBatchRequest.model_validate(
            cross_strategy_payload(idempotency_key="cross-global-race-001")
        ),
    ]

    def attempt(request: CreateExecutionBatchRequest):
        try:
            return create_execution_batch(request)
        except HTTPException as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, requests))

    successes = [result for result in results if not isinstance(result, HTTPException)]
    conflicts = [result for result in results if isinstance(result, HTTPException)]
    assert len(successes) == 1
    assert len(conflicts) == 1
    assert conflicts[0].status_code == 409
    assert "active execution batch" in str(conflicts[0].detail).lower()
    assert len(command_keys) == 1

    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM execution_batches").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM execution_batch_legs").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM trade_commands").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


def test_same_key_replay_precedes_global_lease_and_mismatched_payload_still_conflicts(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "global-claim-replay.db")
    initialize_database()
    payload = batch_payload(
        "account_sim_usdt",
        "instrument_btc_usdt",
        "instrument_btc_usdt_perp",
        idempotency_key="global-replay-001",
    )
    batch_id = insert_persisted_batch(payload=payload, status="executing")

    replay = create_execution_batch(CreateExecutionBatchRequest.model_validate(payload))
    assert replay.batch_id == batch_id
    assert replay.status == "executing"

    changed_payload = dict(payload)
    changed_payload["direction"] = "close"
    with pytest.raises(HTTPException) as conflict:
        create_execution_batch(CreateExecutionBatchRequest.model_validate(changed_payload))
    assert conflict.value.status_code == 409
    assert "different execution batch payload" in str(conflict.value.detail)


def test_same_key_swapped_legs_conflict_without_new_effects(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "global-claim-swapped-legs.db")
    runtime_calls = 0

    def runtime_post(*args, **kwargs):
        nonlocal runtime_calls
        runtime_calls += 1
        return filled_runtime_response(kwargs["json"])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", runtime_post)
    payload = batch_payload(
        "account_sim_usdt",
        "instrument_btc_usdt",
        "instrument_btc_usdt_perp",
        idempotency_key="global-replay-swapped-legs-001",
    )

    with TestClient(app) as client:
        insert_persisted_batch(payload=payload, status="executing")
        swapped_payload = dict(payload)
        legs = payload["legs"]
        assert isinstance(legs, list)
        swapped_payload["legs"] = list(reversed(legs))

        response = client.post(
            "/api/v1/trading/execution-batches",
            json=swapped_payload,
        )

    assert response.status_code == 409
    assert "different execution batch payload" in response.json()["detail"]
    assert runtime_calls == 0
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM execution_batches").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM execution_batch_legs").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM trade_commands").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


@pytest.mark.parametrize(
    ("status", "leg_status"),
    [
        ("pending", "pending"),
        ("executing", "submitting"),
        ("partially_executed", "filled"),
        ("manual_intervention", "result_unknown"),
    ],
)
def test_persisted_unresolved_batch_blocks_new_instruction_after_restart(
    monkeypatch,
    tmp_path: Path,
    status: str,
    leg_status: str,
) -> None:
    get_settings().database_path = str(tmp_path / f"restart-{status}.db")
    blocking_payload = batch_payload(
        "account_sim_usdt",
        "instrument_btc_usdt",
        "instrument_btc_usdt_perp",
        idempotency_key=f"persisted-{status}-001",
    )
    with TestClient(app):
        insert_persisted_batch(payload=blocking_payload, status=status, leg_status=leg_status)

    runtime_calls = 0

    def runtime_post(*args, **kwargs):
        nonlocal runtime_calls
        runtime_calls += 1
        return filled_runtime_response(kwargs["json"])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", runtime_post)
    with TestClient(app) as restarted_client:
        response = restarted_client.post(
            "/api/v1/trading/execution-batches",
            json=cross_strategy_payload(idempotency_key=f"after-restart-{status}-001"),
        )

    assert response.status_code == 409
    assert "active execution batch" in response.json()["detail"].lower()
    assert runtime_calls == 0
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM execution_batches").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM trade_commands").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


def test_unrelated_account_residue_does_not_block_new_instruction(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "restart-unrelated-account.db")
    blocking_payload = batch_payload(
        "account_crypto_test",
        "instrument_btc_usdt",
        "instrument_btc_usdt_perp",
        idempotency_key="persisted-unrelated-account-001",
    )
    with TestClient(app):
        insert_persisted_batch(
            payload=blocking_payload,
            status="hedged",
            leg_status="acknowledged",
        )

    runtime_calls = 0

    def runtime_post(*args, **kwargs):
        nonlocal runtime_calls
        runtime_calls += 1
        return filled_runtime_response(kwargs["json"])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", runtime_post)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/execution-batches",
            json=cross_strategy_payload(idempotency_key="after-unrelated-account-001"),
        )

    assert response.status_code == 200, response.text
    assert "active execution batch" not in response.text.lower()
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM execution_batches").fetchone()[0] == 2


def test_terminal_hedged_batch_with_uncertain_leg_releases_same_account_admission(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "hedged-uncertain-same-account.db")
    initialize_database()
    blocking_payload = batch_payload(
        "account_sim_usdt",
        "instrument_btc_usdt",
        "instrument_btc_usdt_perp",
        idempotency_key="persisted-hedged-ack-001",
    )
    insert_persisted_batch(
        payload=blocking_payload,
        status="hedged",
        leg_status="acknowledged",
    )

    runtime_calls = 0

    def runtime_post(*args, **kwargs):
        nonlocal runtime_calls
        runtime_calls += 1
        return filled_runtime_response(kwargs["json"])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", runtime_post)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/execution-batches",
            json=batch_payload(
                "account_sim_usdt",
                "instrument_btc_usdt",
                "instrument_btc_usdt_perp",
                idempotency_key="after-hedged-ack-001",
            ),
        )

    assert response.status_code == 200, response.text
    assert "active execution batch" not in response.text.lower()


def test_result_unknown_disposition_retains_lease_after_failed_batch_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "failed-result-unknown.db")
    initialize_database()
    blocking_payload = batch_payload(
        "account_sim_usdt",
        "instrument_btc_usdt",
        "instrument_btc_usdt_perp",
        idempotency_key="failed-result-unknown-001",
    )
    insert_persisted_batch(
        payload=blocking_payload,
        status="failed",
        leg_status="result_unknown",
    )

    runtime_calls = 0

    def runtime_post(*args, **kwargs):
        nonlocal runtime_calls
        runtime_calls += 1
        return filled_runtime_response(kwargs["json"])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", runtime_post)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/execution-batches",
            json=cross_strategy_payload(idempotency_key="after-unknown-001"),
        )

    assert response.status_code == 409
    assert runtime_calls == 0
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM execution_batches").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM trade_commands").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


@pytest.mark.parametrize("terminal_status", ["hedged", "failed"])
def test_proven_terminal_batch_releases_global_admission(
    monkeypatch,
    tmp_path: Path,
    terminal_status: str,
) -> None:
    get_settings().database_path = str(tmp_path / f"terminal-{terminal_status}.db")
    initialize_database()
    historical_payload = batch_payload(
        "account_sim_usdt",
        "instrument_btc_usdt",
        "instrument_btc_usdt_perp",
        idempotency_key=f"historical-{terminal_status}-001",
    )
    historical_batch_id = insert_persisted_batch(
        payload=historical_payload,
        status=terminal_status,
        leg_status="filled" if terminal_status == "hedged" else "failed",
    )
    monkeypatch.setattr(
        "app.trade_command_execution.httpx.post",
        lambda *args, **kwargs: filled_runtime_response(kwargs["json"]),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/execution-batches",
            json=cross_strategy_payload(idempotency_key=f"after-terminal-{terminal_status}-001"),
        )

    assert response.status_code == 200
    assert response.json()["status"] == "hedged"
    with connection() as db:
        historical = db.execute(
            "SELECT status FROM execution_batches WHERE id = ?",
            (historical_batch_id,),
        ).fetchone()
        assert historical["status"] == terminal_status


def test_update_batch_status_hedged_normalizes_uncertain_legs(
    tmp_path: Path,
) -> None:
    from app.execution_batches import update_batch_status

    get_settings().database_path = str(tmp_path / "normalize-hedged-legs.db")
    initialize_database()
    payload = cross_strategy_payload(idempotency_key="normalize-hedged-legs-001")
    batch_id = insert_persisted_batch(
        payload=payload,
        status="executing",
        leg_status="acknowledged",
    )

    with connection() as db:
        db.execute(
            """
            INSERT INTO orders (
                id, command_id, account_id, instrument_id, symbol, side,
                order_type, quantity, price, status, external_order_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "external-order-001",
                "command-normalize-001",
                "account_sim_usdt",
                "instrument_btc_usdt",
                "BTCUSDT",
                "buy",
                "limit",
                "1",
                "100",
                "acknowledged",
                "venue-order-001",
                "2026-08-21T00:00:00+00:00",
                "2026-08-21T00:00:00+00:00",
            ),
        )
        db.execute(
            """
            UPDATE execution_batch_legs
            SET order_id = ?, status = 'acknowledged'
            WHERE batch_id = ? AND sequence = 1
            """,
            ("external-order-001", batch_id),
        )

    update_batch_status(batch_id, "hedged")

    with connection() as db:
        legs = db.execute(
            """
            SELECT status, failure_reason
            FROM execution_batch_legs
            WHERE batch_id = ?
            ORDER BY sequence
            """,
            (batch_id,),
        ).fetchall()

    assert legs[0]["status"] == "filled"
    assert legs[0]["failure_reason"] is None


class _FakeCursor:
    def __init__(self, row) -> None:
        self._row = row

    def fetchone(self):
        return self._row


class _LegacyReleaseCompatibilityDb:
    def __init__(
        self,
        row,
        *,
        error_message: str = "no such column: batch.strategy_instruction_id",
    ):
        self._row = row
        self._error_message = error_message

    def execute(self, sql: str, params: tuple[str, ...]):
        assert params
        if "strategy_instruction_id" in sql:
            raise OperationalError(self._error_message)
        return _FakeCursor(self._row)


def test_legacy_release_keeps_funding_hedged_fail_closed() -> None:
    assert (
        _batch_terminal_release_is_safe(
            cast(
                Any,
                _LegacyReleaseCompatibilityDb(
                    {"strategy_key": "funding_arbitrage", "status": "hedged"}
                ),
            ),
            batch_id="legacy-funding-hedged",
            status="hedged",
        )
        is False
    )


def test_legacy_release_allows_funding_completed() -> None:
    assert (
        _batch_terminal_release_is_safe(
            cast(
                Any,
                _LegacyReleaseCompatibilityDb(
                    {"strategy_key": "funding_arbitrage", "status": "completed"}
                ),
            ),
            batch_id="legacy-funding-completed",
            status="completed",
        )
        is True
    )


def test_legacy_release_keeps_non_funding_hedged_compatible() -> None:
    assert (
        _batch_terminal_release_is_safe(
            cast(
                Any,
                _LegacyReleaseCompatibilityDb(
                    {"strategy_key": "cross_venue_spread", "status": "hedged"}
                ),
            ),
            batch_id="legacy-cross-hedged",
            status="hedged",
        )
        is True
    )


def test_release_compatibility_only_handles_missing_column_error() -> None:
    with pytest.raises(OperationalError, match="database disk image is malformed"):
        _batch_terminal_release_is_safe(
            cast(
                Any,
                _LegacyReleaseCompatibilityDb(
                    {"strategy_key": "funding_arbitrage", "status": "completed"},
                    error_message="database disk image is malformed",
                ),
            ),
            batch_id="legacy-error",
            status="completed",
        )


def test_reservation_rules_use_authoritative_crypto_instrument_types() -> None:
    class Leg:
        def __init__(self, *, side: str, quantity: str, price: str | None = None) -> None:
            self.side = side
            self.quantity = Decimal(quantity)
            self.price = Decimal(price) if price is not None else None
            self.symbol = "BTCUSDT"

    spot_buy_key, spot_buy_amount = _reservation_requirement_for_leg(
        Leg(side="buy", quantity="2", price="101.25"),
        account_id="account_crypto_test",
        instrument_type="crypto_spot",
        base_currency="BTC",
        quote_currency="USDT",
        contract_multiplier=None,
    )
    spot_sell_key, spot_sell_amount = _reservation_requirement_for_leg(
        Leg(side="sell", quantity="2.5"),
        account_id="account_crypto_test",
        instrument_type="crypto_spot",
        base_currency="BTC",
        quote_currency="USDT",
        contract_multiplier=None,
    )
    perp_key, perp_amount = _reservation_requirement_for_leg(
        Leg(side="sell", quantity="3", price="99.5"),
        account_id="account_crypto_test",
        instrument_type="crypto_perp",
        base_currency="BTC",
        quote_currency="USDT",
        contract_multiplier=Decimal("0.1"),
    )

    assert spot_buy_key == ("account_crypto_test", "USDT")
    assert spot_buy_amount == Decimal("202.50")
    assert spot_sell_key == ("account_crypto_test", "BTC")
    assert spot_sell_amount == Decimal("2.5")
    assert perp_key == ("account_crypto_test", "USDT")
    assert perp_amount == Decimal("29.85")


def test_shared_account_claims_allow_different_symbols_and_block_same_resource(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "shared-account-resource-identity.db")
    initialize_database()
    timestamp = "2026-08-23T00:00:00+00:00"
    with connection() as db:
        db.execute(
            """
            INSERT INTO instruments (
                id, instrument_code, name, instrument_type, base_currency,
                quote_currency, settle_currency, quantity_unit,
                data_quality_state, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'complete', ?)
            """,
            (
                "instrument_eth_usdt_perp_test",
                "ETH-USDT-PERP-TEST",
                "ETH USDT Perpetual Test",
                "crypto_perp",
                "ETH",
                "USDT",
                "USDT",
                "contract",
                timestamp,
            ),
        )
    for batch_id, instrument_id, symbol in (
        ("batch-btc", "instrument_btc_usdt_perp", "BTCUSDT"),
        ("batch-eth", "instrument_eth_usdt_perp_test", "ETHUSDT"),
    ):
        with connection() as db:
            db.execute("BEGIN IMMEDIATE")
            _claim_batch_execution_resources(
                db,
                batch_id=batch_id,
                strategy_instance_id=STRATEGY_INSTANCE_ID,
                legs=[
                    SimpleNamespace(
                        account_id="account_sim_usdt",
                        instrument_id=instrument_id,
                        symbol=symbol,
                        side="buy",
                        price=Decimal("100"),
                        quantity=Decimal("1"),
                    )
                ],
                default_account_id="account_sim_usdt",
            )

    with pytest.raises(HTTPException, match="Active execution resource claim"):
        with connection() as db:
            db.execute("BEGIN IMMEDIATE")
            _claim_batch_execution_resources(
                db,
                batch_id="batch-btc-conflict",
                strategy_instance_id="strategy_cross_venue_spread_instance_default",
                legs=[
                    SimpleNamespace(
                        account_id="account_sim_usdt",
                        instrument_id="instrument_btc_usdt_perp",
                        symbol="BTCUSDT",
                        side="sell",
                        price=Decimal("100"),
                        quantity=Decimal("1"),
                    )
                ],
                default_account_id="account_sim_usdt",
            )

    with pytest.raises(HTTPException, match="balance reservation is insufficient"):
        with connection() as db:
            db.execute("BEGIN IMMEDIATE")
            _claim_batch_execution_resources(
                db,
                batch_id="batch-insufficient",
                strategy_instance_id=STRATEGY_INSTANCE_ID,
                legs=[
                    SimpleNamespace(
                        account_id="account_sim_usdt",
                        instrument_id="instrument_eth_usdt_perp_test",
                        symbol="ETHUSDT-LARGE",
                        side="buy",
                        price=Decimal("100"),
                        quantity=Decimal("2000"),
                    )
                ],
                default_account_id="account_sim_usdt",
            )

    with connection() as db:
        active = db.execute(
            """
            SELECT resource_key FROM execution_resource_claims
            WHERE status = 'active' ORDER BY resource_key
            """
        ).fetchall()
    assert len(active) == 2
    assert {str(row["resource_key"]).split("|")[-1] for row in active} == {
        "BTCUSDT",
        "ETHUSDT",
    }
