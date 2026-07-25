from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

import app.cross_spread_exit_service as exit_service
from app.config import get_settings
from app.cross_spread_live_read_client import LivePosition
from app.database import connection
from app.execution_schemas import ExecutionBatchResponse
from app.main import app
from app.schemas import TradeCommandResponse

NOW = "2026-07-25T00:00:00+00:00"


def configure_platform(tmp_path: Path) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "cross-spread-rollback.db")
    settings.live_trading_enabled = True
    settings.cross_spread_acceptance_max_quantity_oz = Decimal("1")
    settings.cross_spread_definitive_failure_rollback_enabled = True
    settings.cross_spread_position_verification_required = True


def insert_definitive_failure_batch(batch_id: str) -> None:
    with connection() as db:
        db.execute(
            """
            INSERT INTO execution_batches (
                id, idempotency_key, strategy_instance_id, account_id, strategy_key,
                direction, status, requires_manual_intervention, failure_reason,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'OPEN_LONG', 'manual_intervention', 1, ?, ?, ?)
            """,
            (
                batch_id,
                f"key:{batch_id}",
                "strategy_cross_venue_spread_instance_default",
                "account_crypto_test",
                "cross_venue_spread",
                "MT5 hedge definitively failed",
                NOW,
                NOW,
            ),
        )
        db.execute(
            """
            INSERT INTO orders (
                id, command_id, account_id, instrument_id, symbol, side,
                order_type, quantity, price, status, external_order_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'buy', 'market', '1', NULL, 'filled', ?, ?, ?)
            """,
            (
                "bybit-order-id",
                "bybit-command-id",
                "account_crypto_test",
                "instrument_xau_usdt_perp",
                "XAUTUSDT",
                "BYBIT-ORDER-1",
                NOW,
                NOW,
            ),
        )
        db.execute(
            """
            INSERT INTO execution_batch_legs (
                id, batch_id, sequence, role, account_id, instrument_id,
                symbol, side, order_type, quantity, price, order_id, status,
                failure_reason, created_at, updated_at
            ) VALUES (?, ?, 1, 'bybit_leg', ?, ?, ?, 'buy', 'market', '1', NULL,
                      'bybit-order-id', 'filled', NULL, ?, ?)
            """,
            (
                "bybit-leg-id",
                batch_id,
                "account_crypto_test",
                "instrument_xau_usdt_perp",
                "XAUTUSDT",
                NOW,
                NOW,
            ),
        )
        db.execute(
            """
            INSERT INTO execution_batch_legs (
                id, batch_id, sequence, role, account_id, instrument_id,
                symbol, side, order_type, quantity, price, order_id, status,
                failure_reason, created_at, updated_at
            ) VALUES (?, ?, 2, 'mt5_leg', ?, ?, ?, 'sell', 'market', '0.01', NULL,
                      NULL, 'failed', 'MT5 rejected order', ?, ?)
            """,
            (
                "mt5-leg-id",
                batch_id,
                "account_mt5_demo",
                "instrument_xau_usd",
                "XAUUSD+",
                NOW,
                NOW,
            ),
        )
        db.execute(
            """
            INSERT INTO fills (
                id, order_id, account_id, instrument_id, side,
                quantity, price, occurred_at
            ) VALUES (?, ?, ?, ?, 'buy', '1', '2500', ?)
            """,
            (
                "bybit-fill-id",
                "bybit-order-id",
                "account_crypto_test",
                "instrument_xau_usdt_perp",
                NOW,
            ),
        )


def failed_batch(batch_id: str) -> ExecutionBatchResponse:
    return ExecutionBatchResponse.model_validate(
        {
            "batchId": batch_id,
            "idempotencyKey": f"key:{batch_id}",
            "strategyInstanceId": "strategy_cross_venue_spread_instance_default",
            "accountId": "account_crypto_test",
            "strategyKey": "cross_venue_spread",
            "direction": "OPEN_LONG",
            "status": "manual_intervention",
            "requiresManualIntervention": True,
            "failureReason": "MT5 hedge definitively failed",
            "legs": [
                {
                    "role": "bybit_leg",
                    "accountId": "account_crypto_test",
                    "orderId": "bybit-order-id",
                    "status": "filled",
                    "failureReason": None,
                },
                {
                    "role": "mt5_leg",
                    "accountId": "account_mt5_demo",
                    "orderId": None,
                    "status": "failed",
                    "failureReason": "MT5 rejected order",
                },
            ],
            "createdAt": NOW,
            "updatedAt": NOW,
        }
    )


def unknown_batch() -> ExecutionBatchResponse:
    return ExecutionBatchResponse.model_validate(
        {
            "batchId": "unknown-batch",
            "idempotencyKey": "key:unknown-batch",
            "strategyInstanceId": "strategy_cross_venue_spread_instance_default",
            "accountId": "account_crypto_test",
            "strategyKey": "cross_venue_spread",
            "direction": "OPEN_LONG",
            "status": "manual_intervention",
            "requiresManualIntervention": True,
            "failureReason": "MT5 result is unknown",
            "legs": [
                {
                    "role": "bybit_leg",
                    "accountId": "account_crypto_test",
                    "orderId": "bybit-order-id",
                    "status": "filled",
                    "failureReason": None,
                },
                {
                    "role": "mt5_leg",
                    "accountId": "account_mt5_demo",
                    "orderId": "mt5-order-id",
                    "status": "result_unknown",
                    "failureReason": "Runtime returned an unknown result",
                },
            ],
            "createdAt": NOW,
            "updatedAt": NOW,
        }
    )


def live_bybit_position() -> LivePosition:
    return LivePosition(
        source="bybit_live",
        external_position_id="bybit-position-1",
        account_id="account_crypto_test",
        instrument_id="instrument_xau_usdt_perp",
        symbol="XAUTUSDT",
        net_quantity=Decimal("1"),
    )


def test_definitive_mt5_failure_submits_one_reduce_only_bybit_rollback(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configure_platform(tmp_path)
    calls: list[dict[str, object]] = []
    position_reads = iter([([live_bybit_position()], []), ([], [])])
    with TestClient(app):
        insert_definitive_failure_batch("failed-open-batch")

        def fake_rollback(**kwargs) -> TradeCommandResponse:
            calls.append(kwargs)
            return TradeCommandResponse(
                tradeCommandId="rollback-command-id",
                idempotencyKey="cross-spread-rollback:failed-open-batch:bybit",
                strategyInstanceId="strategy_cross_venue_spread_instance_default",
                accountId="account_crypto_test",
                instrumentId="instrument_xau_usdt_perp",
                platformOrderId="rollback-platform-order-id",
                status="filled",
                createdAt=NOW,
                updatedAt=NOW,
            )

        monkeypatch.setattr(
            exit_service,
            "submit_bybit_definitive_failure_rollback",
            fake_rollback,
        )
        monkeypatch.setattr(
            exit_service,
            "_load_live_positions",
            lambda: next(position_reads),
        )

        result = exit_service._handle_definitive_open_failure(
            failed_batch("failed-open-batch")
        )

    assert calls == [
        {
            "open_batch_id": "failed-open-batch",
            "open_action": "OPEN_LONG",
            "quantity_oz": Decimal("1"),
        }
    ]
    assert result.status == "failed"
    assert result.requires_manual_intervention is False
    assert "rollback-platform-order-id" in str(result.failure_reason)


def test_already_flat_external_positions_do_not_submit_duplicate_rollback(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configure_platform(tmp_path)
    called = False
    with TestClient(app):
        insert_definitive_failure_batch("already-flat-batch")

        def forbidden_rollback(**kwargs):
            nonlocal called
            called = True
            raise AssertionError("already-flat exposure must not be rolled back again")

        monkeypatch.setattr(
            exit_service,
            "submit_bybit_definitive_failure_rollback",
            forbidden_rollback,
        )
        monkeypatch.setattr(
            exit_service,
            "_load_live_positions",
            lambda: ([], []),
        )

        result = exit_service._handle_definitive_open_failure(
            failed_batch("already-flat-batch")
        )

    assert called is False
    assert result.status == "failed"
    assert result.requires_manual_intervention is False
    assert "already flat" in str(result.failure_reason)


def test_mt5_result_unknown_never_triggers_automatic_rollback(monkeypatch) -> None:
    called = False

    def forbidden_rollback(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("unknown MT5 outcome must not trigger rollback")

    monkeypatch.setattr(
        exit_service,
        "submit_bybit_definitive_failure_rollback",
        forbidden_rollback,
    )
    batch = unknown_batch()

    result = exit_service._handle_definitive_open_failure(batch)

    assert result is batch
    assert called is False
