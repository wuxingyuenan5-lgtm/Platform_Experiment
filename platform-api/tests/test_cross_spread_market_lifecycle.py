from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

import app.cross_spread_exit_service as exit_service
from app.config import get_settings
from app.cross_spread_exit_repository import (
    claim_exit_plan,
    create_exit_plan,
    get_exit_plan,
)
from app.cross_spread_exit_schemas import CrossSpreadMarketOpenRequest
from app.cross_spread_live_read_client import LivePosition
from app.database import connection
from app.execution_schemas import ExecutionBatchResponse
from app.main import app
from app.schemas import CrossSpreadSnapshotResponse

NOW = "2026-07-25T00:00:00+00:00"


def credential(user_id: str, token: str, roles: list[str]) -> dict[str, object]:
    return {
        "credentialId": f"credential-{user_id}",
        "userId": user_id,
        "tokenSha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        "roles": roles,
        "status": "active",
    }


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def insert_batch_with_fills(batch_id: str, *, direction: str = "OPEN_LONG") -> None:
    with connection() as db:
        db.execute(
            """
            INSERT INTO execution_batches (
                id, idempotency_key, strategy_instance_id, account_id, strategy_key,
                direction, status, requires_manual_intervention, failure_reason,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'hedged', 0, NULL, ?, ?)
            """,
            (
                batch_id,
                f"key:{batch_id}",
                "strategy_cross_venue_spread_instance_default",
                "account_crypto_test",
                "cross_venue_spread",
                direction,
                NOW,
                NOW,
            ),
        )
        legs = (
            (
                "bybit-leg-id",
                1,
                "bybit_leg",
                "account_crypto_test",
                "instrument_xau_usdt_perp",
                "XAUTUSDT",
                "buy",
                "1",
                "bybit-order-id",
            ),
            (
                "mt5-leg-id",
                2,
                "mt5_leg",
                "account_mt5_demo",
                "instrument_xau_usd",
                "XAUUSD.s",
                "sell",
                "0.01",
                "mt5-order-id",
            ),
        )
        for leg_id, sequence, role, account_id, instrument_id, symbol, side, qty, order_id in legs:
            db.execute(
                """
                INSERT INTO orders (
                    id, command_id, account_id, instrument_id, symbol, side,
                    order_type, quantity, price, status, external_order_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'market', ?, NULL, 'filled', NULL, ?, ?)
                """,
                (
                    order_id,
                    f"command:{order_id}",
                    account_id,
                    instrument_id,
                    symbol,
                    side,
                    qty,
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'market', ?, NULL, ?, 'filled', NULL, ?, ?)
                """,
                (
                    leg_id,
                    batch_id,
                    sequence,
                    role,
                    account_id,
                    instrument_id,
                    symbol,
                    side,
                    qty,
                    order_id,
                    NOW,
                    NOW,
                ),
            )
        db.execute(
            """
            INSERT INTO fills (
                id, order_id, account_id, instrument_id, side,
                quantity, price, occurred_at
            )
            VALUES ('fill-bybit', 'bybit-order-id', 'account_crypto_test',
                    'instrument_xau_usdt_perp', 'buy', '1', '2499', ?)
            """,
            (NOW,),
        )
        db.execute(
            """
            INSERT INTO fills (
                id, order_id, account_id, instrument_id, side,
                quantity, price, occurred_at
            )
            VALUES ('fill-mt5', 'mt5-order-id', 'account_mt5_demo',
                    'instrument_xau_usd', 'sell', '0.01', '2501', ?)
            """,
            (NOW,),
        )


def batch_response(
    batch_id: str,
    *,
    direction: str,
    status: str = "hedged",
) -> ExecutionBatchResponse:
    return ExecutionBatchResponse(
        batchId=batch_id,
        idempotencyKey=f"key:{batch_id}",
        strategyInstanceId="strategy_cross_venue_spread_instance_default",
        accountId="account_crypto_test",
        strategyKey="cross_venue_spread",
        direction=direction,
        status=status,
        requiresManualIntervention=False,
        failureReason=None,
        legs=[],
        createdAt=NOW,
        updatedAt=NOW,
    )


def available_snapshot() -> CrossSpreadSnapshotResponse:
    return CrossSpreadSnapshotResponse.model_validate(
        {
            "status": "available",
            "bybit": {
                "venue": "bybit",
                "symbol": "XAUTUSDT",
                "status": "available",
                "quote": {
                    "bid": "2500",
                    "ask": "2500.2",
                    "mid": "2500.1",
                    "currency": "USDT",
                },
                "positions": [],
            },
            "mt5": {
                "venue": "mt5",
                "symbol": "XAUUSD.s",
                "status": "available",
                "quote": {
                    "bid": "2501",
                    "ask": "2501.2",
                    "mid": "2501.1",
                    "currency": "USD",
                },
                "positions": [
                    {
                        "symbol": "XAUUSD.s",
                        "side": "sell",
                        "quantity": "-0.01",
                        "averagePrice": "2501",
                        "externalId": "778899",
                    }
                ],
            },
            "longSpread": "-0.8",
            "shortSpread": "-1.2",
            "metrics": {},
            "asOf": NOW,
        }
    )


def live_open_positions() -> tuple[list[LivePosition], list[LivePosition]]:
    return (
        [
            LivePosition(
                source="bybit_live",
                external_position_id="bybit-position-1",
                account_id="account_crypto_test",
                instrument_id="instrument_xau_usdt_perp",
                symbol="XAUTUSDT",
                net_quantity=Decimal("1"),
            )
        ],
        [
            LivePosition(
                source="mt5_live",
                external_position_id="778899",
                account_id="account_mt5_demo",
                instrument_id="instrument_xau_usd",
                symbol="XAUUSD.s",
                net_quantity=Decimal("-0.01"),
            )
        ],
    )


def configure_platform(tmp_path: Path) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "cross-spread-lifecycle.db")
    settings.environment = "live"
    settings.auth_mode = "api_key"
    settings.auth_credentials_json = json.dumps([credential("admin-1", "admin-token", ["admin"])])
    settings.live_trading_enabled = True
    settings.cross_spread_exit_monitor_enabled = False
    settings.cross_spread_acceptance_max_quantity_oz = Decimal("1")
    settings.cross_spread_acceptance_max_active_plans = 1
    settings.cross_spread_position_verification_required = True


def created_plan_stub() -> exit_service.CrossSpreadExitPlanResponse:
    return exit_service.CrossSpreadExitPlanResponse(
        planId="plan-safe-open",
        strategyInstanceId="strategy_cross_venue_spread_instance_default",
        openBatchId="open-batch-safe",
        closeBatchId=None,
        direction="LONG_SPREAD",
        quantityOz="1",
        mt5PositionId="778899",
        entrySpread="-2",
        takeProfitSpread="0",
        stopLossSpread="-3",
        takeProfitExecutionMode="market",
        stopLossExecutionMode="market",
        takeProfitLimitStrategy="fok",
        stopLossLimitStrategy="fok",
        status="active",
        triggerReason=None,
        triggerSpread=None,
        createdAt=NOW,
        updatedAt=NOW,
        triggeredAt=None,
        closedAt=None,
    )


def test_hedged_market_open_creates_plan_from_actual_fills(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configure_platform(tmp_path)
    position_reads = iter([([], []), live_open_positions()])
    with TestClient(app):
        insert_batch_with_fills("open-batch-1")
        monkeypatch.setattr(
            exit_service,
            "submit_cross_spread_market_command",
            lambda request: batch_response("open-batch-1", direction=request.action),
        )
        monkeypatch.setattr(
            exit_service,
            "_load_live_positions",
            lambda: next(position_reads),
        )

        result = exit_service.open_cross_spread_market(
            CrossSpreadMarketOpenRequest(
                direction="LONG_SPREAD",
                quantityOz="1",
                takeProfitSpread="0",
                stopLossSpread="-3",
                executionMode="market",
            )
        )

    assert result.execution_batch.status == "hedged"
    assert result.exit_plan is not None
    assert result.exit_plan.quantity_oz == Decimal("1")
    assert result.exit_plan.entry_spread == Decimal("-2")
    assert result.exit_plan.mt5_position_id == "778899"


def test_open_ignores_unresolved_batches_from_other_accounts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configure_platform(tmp_path)
    with TestClient(app):
        with connection() as db:
          db.execute(
              """
              INSERT INTO execution_batches (
                  id, idempotency_key, strategy_instance_id, account_id, strategy_key,
                  direction, status, requires_manual_intervention, failure_reason,
                  created_at, updated_at
              ) VALUES (?, ?, ?, ?, ?, ?, 'manual_intervention', 1, 'legacy residue', ?, ?)
              """,
              (
                  "legacy-live-batch",
                  "legacy-live-key",
                  "strategy_cross_venue_spread_instance_default",
                  "account_crypto_test",
                  "cross_venue_spread",
                  "OPEN_LONG",
                  NOW,
                  NOW,
              ),
          )
        monkeypatch.setattr(
            exit_service,
            "_load_live_positions",
            lambda: ([], []),
        )
        monkeypatch.setattr(
            exit_service,
            "submit_cross_spread_market_command",
            lambda request: batch_response("open-batch-safe", direction=request.action),
        )
        monkeypatch.setattr(
            exit_service,
            "_create_exit_plan_for_open_batch",
            lambda *args, **kwargs: created_plan_stub(),
        )

        result = exit_service.open_cross_spread_market(
            CrossSpreadMarketOpenRequest(
                direction="LONG_SPREAD",
                quantityOz="1",
                takeProfitSpread="0",
                stopLossSpread="-3",
                executionMode="market",
            )
        )

    assert result.execution_batch.batch_id == "open-batch-safe"
    assert result.exit_plan is not None
    assert result.exit_plan.plan_id == "plan-safe-open"


def test_exit_plan_claim_is_atomic(tmp_path: Path) -> None:
    configure_platform(tmp_path)
    with TestClient(app):
        insert_batch_with_fills("open-batch-claim")
        plan = create_exit_plan(
            strategy_instance_id="strategy_cross_venue_spread_instance_default",
            open_batch_id="open-batch-claim",
            direction="LONG_SPREAD",
            quantity_oz=Decimal("1"),
            mt5_position_id="778899",
            entry_spread=Decimal("-2"),
            take_profit_spread=Decimal("0"),
            stop_loss_spread=Decimal("-3"),
        )
        first = claim_exit_plan(
            plan.plan_id,
            trigger_reason="take_profit",
            trigger_spread=Decimal("0.1"),
        )
        second = claim_exit_plan(
            plan.plan_id,
            trigger_reason="take_profit",
            trigger_spread=Decimal("0.2"),
        )

    assert first is not None
    assert second is None


def test_market_close_registers_reduce_only_and_mt5_ticket(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configure_platform(tmp_path)
    captured = {}
    with TestClient(app):
        insert_batch_with_fills("open-batch-close")
        plan = create_exit_plan(
            strategy_instance_id="strategy_cross_venue_spread_instance_default",
            open_batch_id="open-batch-close",
            direction="LONG_SPREAD",
            quantity_oz=Decimal("1"),
            mt5_position_id="778899",
            entry_spread=Decimal("-2"),
            take_profit_spread=Decimal("0"),
            stop_loss_spread=Decimal("-3"),
        )

        def fake_submit(request, **kwargs):
            captured["request"] = request
            captured["kwargs"] = kwargs
            close_batch_id = "close-batch-1"
            with connection() as db:
                db.execute(
                    """
                    INSERT INTO execution_batches (
                        id, idempotency_key, strategy_instance_id, account_id,
                        strategy_key, direction, status, requires_manual_intervention,
                        failure_reason, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'hedged', 0, NULL, ?, ?)
                    """,
                    (
                        close_batch_id,
                        kwargs["idempotency_key"],
                        "strategy_cross_venue_spread_instance_default",
                        "account_crypto_test",
                        "cross_venue_spread",
                        request.action,
                        NOW,
                        NOW,
                    ),
                )
            return batch_response(close_batch_id, direction=request.action)

        monkeypatch.setattr(
            exit_service,
            "submit_cross_spread_market_command",
            fake_submit,
        )
        monkeypatch.setattr(
            exit_service,
            "_load_live_positions",
            lambda: ([], []),
        )
        result = exit_service.close_cross_spread_market(
            plan.plan_id,
            execution_mode="market",
        )

    assert captured["request"].action == "CLOSE_LONG"
    assert captured["kwargs"]["bybit_reduce_only"] is True
    assert captured["kwargs"]["mt5_reduce_only"] is True
    assert captured["kwargs"]["mt5_position_id"] == "778899"
    assert captured["kwargs"]["idempotency_key"] == (
        f"cross-spread-exit:{plan.plan_id}"
    )
    assert result.exit_plan.status == "closed"
    assert get_exit_plan(plan.plan_id).status == "closed"


def test_limit_requires_spread_and_legacy_close_fails_closed(tmp_path: Path) -> None:
    configure_platform(tmp_path)
    exit_service.has_ceo_trade_authority = lambda principal, current: True
    import app.auth as auth_module

    auth_module.has_ceo_trade_authority = lambda principal, current: True
    with TestClient(app) as client:
        limit_response = client.post(
            "/api/v1/trading/cross-spread/lifecycle/open",
            headers=headers("admin-token"),
            json={
                "direction": "LONG_SPREAD",
                "quantityOz": "1",
                "takeProfitSpread": "0",
                "stopLossSpread": "-3",
                "executionMode": "limit",
            },
        )
        legacy_close = client.post(
            "/api/v1/trading/cross-spread/market-command",
            headers=headers("admin-token"),
            json={"action": "CLOSE_LONG", "quantityOz": "1"},
        )

    assert limit_response.status_code == 422
    details = limit_response.json()["detail"]
    assert any("limitSpread" in item["msg"] for item in details)
    assert legacy_close.status_code == 422
    assert "requires reduce-only" in legacy_close.json()["detail"]
