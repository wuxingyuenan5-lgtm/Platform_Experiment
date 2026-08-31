from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.database import connection, initialize_database
from app.execution_batches import (
    _claim_batch_execution_resources,
    _release_batch_claims_and_reservations_if_safe,
)
from app.schema_migrations import apply_platform_migrations
from app.strategies.domain import StrategyInstructionAction
from app.strategies.instruction_service import (
    CreateStrategyInstructionRequest,
    create_instruction,
    execute_instruction,
)

CROSS_INSTANCE = "strategy_cross_venue_spread_instance_default"
FUNDING_INSTANCE = "strategy_funding_arbitrage_instance_default"


class _FilledResponse:
    def __init__(self, command: dict[str, object]) -> None:
        self.command = command

    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[dict[str, object]]:
        command = self.command
        return [
            {
                "event_id": str(uuid4()),
                "command_id": command["command_id"],
                "platform_order_id": command["platform_order_id"],
                "event_type": "order_filled",
                "external_order_id": f"fake-{command['platform_order_id']}",
                "fill_price": "100",
                "fill_quantity": command["quantity"],
                "occurred_at": "2026-08-31T00:00:00+00:00",
                "reason": None,
            }
        ]


def _prepare_database(tmp_path, name: str) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / name)
    settings.environment = "development"
    settings.auth_mode = "development"
    settings.development_roles = "admin"
    settings.live_trading_enabled = True
    settings.default_trading_environment = "simulation"
    initialize_database()
    apply_platform_migrations()
    timestamp = datetime(2026, 8, 31, tzinfo=UTC).isoformat()
    with connection() as db:
        db.execute(
            "UPDATE strategy_instances SET status = 'active', trading_mode = 'simulation' "
            "WHERE id IN (?, ?)",
            (CROSS_INSTANCE, FUNDING_INSTANCE),
        )
        db.execute(
            "UPDATE accounts SET status = 'active' WHERE id IN (?, ?, ?)",
            ("bybit-live-main", "mt5-live-main", "account_sim_usdt"),
        )
        for account_id, currency in (
            ("bybit-live-main", "USDT"),
            ("mt5-live-main", "USD"),
            ("account_sim_usdt", "USDT"),
        ):
            db.execute(
                """
                INSERT OR REPLACE INTO balance_snapshots (
                    id, account_id, currency, equity, available_balance, source,
                    data_quality_state, as_of, created_at
                ) VALUES (?, ?, ?, '1000000', '1000000', 'test', 'complete', ?, ?)
                """,
                (f"balance-{account_id}-{currency}", account_id, currency, timestamp, timestamp),
            )


def _cross_instruction(key: str) -> dict[str, object]:
    return create_instruction(
        CROSS_INSTANCE,
        CreateStrategyInstructionRequest(
            idempotencyKey=key,
            action=StrategyInstructionAction.OPEN,
            parameters={"action": "OPEN_LONG", "quantityOz": Decimal("1")},
            reason="resource admission regression",
        ),
        requested_by="test",
    )


def _counts(batch_id: str) -> tuple[int, int, int, str]:
    with connection() as db:
        claims = db.execute(
            "SELECT COUNT(*) AS count FROM execution_resource_claims "
            "WHERE owner_type = 'batch' AND owner_id = ?",
            (batch_id,),
        ).fetchone()["count"]
        reservations = db.execute(
            "SELECT COUNT(*) AS count FROM execution_balance_reservations "
            "WHERE owner_type = 'batch' AND owner_id = ?",
            (batch_id,),
        ).fetchone()["count"]
        commands = db.execute("SELECT COUNT(*) AS count FROM trade_commands").fetchone()["count"]
        status = db.execute(
            "SELECT status FROM execution_batches WHERE id = ?", (batch_id,)
        ).fetchone()["status"]
    return int(claims), int(reservations), int(commands), str(status)


def test_cross_instruction_claims_resources_once_and_dispatches_once(
    monkeypatch, tmp_path
) -> None:
    _prepare_database(tmp_path, "instruction-resource-once.db")
    monkeypatch.setattr(
        "app.execution_batches._reservation_reference_price", lambda **_kwargs: Decimal("100")
    )
    def fake_post(*_args, **kwargs):
        return _FilledResponse(kwargs["json"])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", fake_post)
    instruction = _cross_instruction("cross-resource-once")
    instruction_id = str(instruction["instructionId"])
    batch_id = str(instruction["executionBatchId"])

    assert _counts(batch_id) == (0, 0, 0, "pending")
    execute_instruction(instruction_id)
    first_counts = _counts(batch_id)
    execute_instruction(instruction_id)

    assert first_counts[:2] == (2, 2)
    assert first_counts[2] > 0
    assert _counts(batch_id)[:3] == first_counts[:3]


def test_concurrent_cross_execute_has_one_dispatch(monkeypatch, tmp_path) -> None:
    _prepare_database(tmp_path, "instruction-resource-concurrent.db")
    monkeypatch.setattr(
        "app.execution_batches._reservation_reference_price", lambda **_kwargs: Decimal("100")
    )
    first_dispatch_started = Event()
    release_first_dispatch = Event()
    calls = 0
    from app import execution_batches

    original_create_trade_command = execution_batches.create_trade_command

    def controlled_create_trade_command(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            first_dispatch_started.set()
            assert release_first_dispatch.wait(timeout=5)
        return original_create_trade_command(request)

    monkeypatch.setattr(execution_batches, "create_trade_command", controlled_create_trade_command)
    instruction = _cross_instruction("cross-resource-concurrent")
    instruction_id = str(instruction["instructionId"])
    batch_id = str(instruction["executionBatchId"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(execute_instruction, instruction_id)
        if not first_dispatch_started.wait(timeout=5):
            first.result(timeout=1)
            raise AssertionError("first execution did not reach TradeCommand dispatch")
        replay = pool.submit(execute_instruction, instruction_id)
        replay.result(timeout=5)
        release_first_dispatch.set()
        first.result(timeout=10)

    counts = _counts(batch_id)
    assert calls == counts[2] == 1
    assert counts[:2] == (2, 2)


def _leg(*, instrument_id: str, symbol: str, quantity: str = "1") -> SimpleNamespace:
    return SimpleNamespace(
        account_id="account_sim_usdt",
        instrument_id=instrument_id,
        symbol=symbol,
        side="buy",
        price=Decimal("100"),
        quantity=Decimal(quantity),
    )


def test_shared_uta_same_symbol_conflicts_but_different_symbol_can_run(tmp_path) -> None:
    _prepare_database(tmp_path, "instruction-shared-uta.db")
    timestamp = datetime(2026, 8, 31, tzinfo=UTC).isoformat()
    with connection() as db:
        db.execute(
            """
            INSERT INTO instruments (
                id, instrument_code, name, instrument_type, base_currency,
                quote_currency, settle_currency, quantity_unit,
                data_quality_state, created_at
            ) VALUES ('instrument_eth_perp_claim_test', 'ETH-PERP-CLAIM', 'ETH claim test',
                      'crypto_perp', 'ETH', 'USDT', 'USDT', 'contract', 'complete', ?)
            """,
            (timestamp,),
        )
        _claim_batch_execution_resources(
            db,
            batch_id="cross-owner",
            strategy_instance_id=CROSS_INSTANCE,
            legs=[_leg(instrument_id="instrument_btc_usdt_perp", symbol="BTCUSDT")],
            default_account_id="account_sim_usdt",
        )
        _claim_batch_execution_resources(
            db,
            batch_id="cross-owner",
            strategy_instance_id=CROSS_INSTANCE,
            legs=[_leg(instrument_id="instrument_btc_usdt_perp", symbol="BTCUSDT")],
            default_account_id="account_sim_usdt",
        )
        assert db.execute(
            "SELECT COUNT(*) AS count FROM execution_resource_claims WHERE owner_id = 'cross-owner'"
        ).fetchone()["count"] == 1
        assert db.execute(
            "SELECT COUNT(*) AS count FROM execution_balance_reservations "
            "WHERE owner_id = 'cross-owner'"
        ).fetchone()["count"] == 1

    with pytest.raises(HTTPException, match="Active execution resource claim"):
        with connection() as db:
            db.execute("BEGIN IMMEDIATE")
            _claim_batch_execution_resources(
                db,
                batch_id="funding-owner-conflict",
                strategy_instance_id=FUNDING_INSTANCE,
                legs=[_leg(instrument_id="instrument_btc_usdt_perp", symbol="BTCUSDT")],
                default_account_id="account_sim_usdt",
            )

    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        _claim_batch_execution_resources(
            db,
            batch_id="funding-owner-parallel",
            strategy_instance_id=FUNDING_INSTANCE,
            legs=[_leg(instrument_id="instrument_eth_perp_claim_test", symbol="ETHUSDT")],
            default_account_id="account_sim_usdt",
        )
        assert db.execute(
            "SELECT COUNT(*) AS count FROM execution_resource_claims WHERE status = 'active'"
        ).fetchone()["count"] == 2


def test_insufficient_balance_and_account_claim_fail_before_dispatch(monkeypatch, tmp_path) -> None:
    _prepare_database(tmp_path, "instruction-resource-fail-closed.db")
    monkeypatch.setattr(
        "app.execution_batches._reservation_reference_price", lambda **_kwargs: Decimal("100")
    )
    first = _cross_instruction("cross-insufficient")
    first_batch = str(first["executionBatchId"])
    with connection() as db:
        db.execute(
            "UPDATE balance_snapshots SET available_balance = '1' "
            "WHERE account_id = 'bybit-live-main' AND currency = 'USDT'"
        )

    with pytest.raises(HTTPException, match="balance reservation is insufficient"):
        execute_instruction(str(first["instructionId"]))
    failed_counts = _counts(first_batch)
    assert failed_counts[:3] == (0, 0, 0)
    assert failed_counts[3] != "executing"

    second = _cross_instruction("cross-account-wide")
    second_batch = str(second["executionBatchId"])
    with connection() as db:
        db.execute(
            "UPDATE balance_snapshots SET available_balance = '1000000' "
            "WHERE account_id = 'bybit-live-main' AND currency = 'USDT'"
        )
        timestamp = datetime(2026, 8, 31, tzinfo=UTC).isoformat()
        db.execute(
            """
            INSERT INTO execution_resource_claims (
                id, resource_key, owner_type, owner_id, account_id, venue_id,
                resource_category, symbol, status, created_at, updated_at
            ) VALUES (?, ?, 'transfer', 'transfer-test', 'bybit-live-main', 'venue_bybit',
                      'account', '*', 'active', ?, ?)
            """,
            (str(uuid4()), "bybit-live-main|venue_bybit|account|*", timestamp, timestamp),
        )

    with pytest.raises(HTTPException, match="Active execution resource claim"):
        execute_instruction(str(second["instructionId"]))
    blocked_counts = _counts(second_batch)
    assert blocked_counts[:3] == (0, 0, 0)
    assert blocked_counts[3] != "executing"


@pytest.mark.parametrize("batch_status", ["result_unknown", "manual_intervention", "reconciling"])
def test_uncertain_and_manual_batches_keep_resources(tmp_path, batch_status: str) -> None:
    _prepare_database(tmp_path, f"instruction-resource-retain-{batch_status}.db")
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        _claim_batch_execution_resources(
            db,
            batch_id="retained-owner",
            strategy_instance_id=FUNDING_INSTANCE,
            legs=[_leg(instrument_id="instrument_btc_usdt_perp", symbol="BTCUSDT")],
            default_account_id="account_sim_usdt",
        )

    _release_batch_claims_and_reservations_if_safe("retained-owner", batch_status)
    with connection() as db:
        assert db.execute(
            "SELECT COUNT(*) AS count FROM execution_resource_claims "
            "WHERE owner_id = 'retained-owner' AND status = 'active'"
        ).fetchone()["count"] == 1
        assert db.execute(
            "SELECT COUNT(*) AS count FROM execution_balance_reservations "
            "WHERE owner_id = 'retained-owner' AND status = 'active'"
        ).fetchone()["count"] == 1
