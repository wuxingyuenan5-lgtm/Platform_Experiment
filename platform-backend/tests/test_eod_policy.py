from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.financial_facts import ensure_schema as ensure_financial_schema
from app.main import app
from app.venue_reconciliation import ensure_schema as ensure_reconciliation_schema

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


def insert_order(
    *,
    suffix: str,
    status: str,
    created_at: str,
) -> str:
    command_id = f"command-eod-policy-{suffix}"
    order_id = f"order-eod-policy-{suffix}"
    with connection() as db:
        db.execute(
            """
            INSERT INTO trade_commands (
                id, idempotency_key, strategy_instance_id, account_id,
                instrument_id, command_type, side, order_type, quantity,
                price, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                command_id,
                f"idempotency-eod-policy-{suffix}",
                STRATEGY_ID,
                ACCOUNT_ID,
                INSTRUMENT_ID,
                "submit_order",
                "buy",
                "limit",
                "1",
                "100",
                status,
                created_at,
                created_at,
            ),
        )
        db.execute(
            """
            INSERT INTO orders (
                id, command_id, account_id, instrument_id, symbol, side,
                order_type, quantity, price, status, external_order_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                command_id,
                ACCOUNT_ID,
                INSTRUMENT_ID,
                "BTCUSDT",
                "buy",
                "limit",
                "1",
                "100",
                status,
                None,
                created_at,
                created_at,
            ),
        )
    return order_id


def test_order_window_includes_business_day_and_older_nonterminal_orders(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "eod-order-window.db")
    with TestClient(app):
        same_day_terminal = insert_order(
            suffix="same-day-terminal",
            status="filled",
            created_at="2026-07-23T02:00:00+00:00",
        )
        prior_nonterminal = insert_order(
            suffix="prior-nonterminal",
            status="result_unknown",
            created_at="2026-07-22T02:00:00+00:00",
        )
        insert_order(
            suffix="prior-terminal",
            status="filled",
            created_at="2026-07-22T03:00:00+00:00",
        )
        insert_order(
            suffix="after-valuation",
            status="acknowledged",
            created_at="2026-07-23T16:30:00+00:00",
        )

        from app.eod_reconciliation import list_strategy_orders

        selected = list_strategy_orders(
            STRATEGY_ID,
            ACCOUNT_ID,
            __import__("datetime").datetime.fromisoformat("2026-07-23T23:59:00+08:00"),
        )
        assert selected == [prior_nonterminal, same_day_terminal]


def report_payload() -> dict[str, str]:
    return {
        "idempotencyKey": "eod-historical-accepted-001",
        "businessDate": "2026-07-23",
        "timezone": "Asia/Shanghai",
        "valuationTime": "2026-07-23T23:59:00+08:00",
        "strategyInstanceId": STRATEGY_ID,
        "accountId": ACCOUNT_ID,
        "actor": "eod-runner",
        "owner": "operations-owner",
        "dueAt": "2026-07-24T23:59:00+08:00",
    }


def test_historical_accepted_difference_blocks_scale_review(monkeypatch, tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "eod-historical-accepted.db")
    with TestClient(app) as client:
        ensure_financial_schema()
        ensure_reconciliation_schema()
        with connection() as db:
            db.execute(
                """
                INSERT INTO formal_pnl_results (
                    strategy_instance_id, account_id, instrument_id, currency,
                    trading_pnl, funding_pnl, swap_pnl, fee_pnl, fx_pnl,
                    total_pnl, fact_count, data_quality_state, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    STRATEGY_ID,
                    ACCOUNT_ID,
                    INSTRUMENT_ID,
                    "USDT",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    0,
                    "complete",
                    "2026-07-23T15:59:00+00:00",
                ),
            )
            db.execute(
                """
                INSERT INTO venue_reconciliation_runs (
                    id, idempotency_key, payload_hash, strategy_instance_id,
                    account_id, run_type, source, status, order_count,
                    fill_count, position_count, balance_count, fact_count,
                    difference_count, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "historical-run-accepted",
                    "historical-run-accepted",
                    "historical-hash",
                    STRATEGY_ID,
                    ACCOUNT_ID,
                    "account_snapshot",
                    "live",
                    "completed_with_differences",
                    0,
                    0,
                    1,
                    1,
                    2,
                    1,
                    "2026-07-22T16:00:00+00:00",
                    "2026-07-22T16:01:00+00:00",
                ),
            )
            db.execute(
                """
                INSERT INTO reconciliation_differences (
                    id, run_id, difference_key, difference_type, entity_type,
                    local_reference, external_reference, local_value_json,
                    external_value_json, status, resolution_actor,
                    resolution_reason, resolved_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "historical-accepted-difference",
                    "historical-run-accepted",
                    "historical-position-accepted",
                    "quantity_mismatch",
                    "position",
                    "local",
                    "external",
                    '{"netQuantity":"1"}',
                    '{"netQuantity":"2"}',
                    "accepted",
                    "risk-officer",
                    "temporarily accepted for investigation",
                    "2026-07-22T16:02:00+00:00",
                    "2026-07-22T16:01:00+00:00",
                ),
            )

        monkeypatch.setattr(
            "app.eod_reconciliation.list_strategy_orders",
            lambda *args, **kwargs: [],
        )
        monkeypatch.setattr(
            "app.eod_reconciliation.run_account_reconciliation",
            lambda request: SimpleNamespace(run_id="clean-current-run"),
        )
        monkeypatch.setattr(
            "app.eod_reconciliation.import_live_economic_events",
            lambda request: SimpleNamespace(
                import_id="clean-current-economic-import",
                skipped_external_ids=[],
            ),
        )
        monkeypatch.setattr(
            "app.eod_reconciliation.rebuild_strategy_financials",
            lambda strategy_instance_id: None,
        )
        monkeypatch.setattr(
            "app.eod_reconciliation.run_formal_nav_snapshot",
            lambda strategy_instance_id, valuation_time: SimpleNamespace(
                snapshot_id="clean-current-nav",
                missing_account_ids=[],
            ),
        )

        response = client.post(
            "/api/v1/ops/eod-reconciliation/reports",
            json=report_payload(),
        )
        assert response.status_code == 200
        report = response.json()
        assert report["status"] == "completed_with_differences"
        assert report["scaleGateStatus"] == "blocked"
        assert report["acceptedDifferenceCount"] == 1
        assert report["openDifferenceCount"] == 0

        approval = client.post(
            f"/api/v1/ops/eod-reconciliation/reports/{report['reportId']}/review",
            json={
                "decision": "approved_same_limits",
                "reviewer": "risk-reviewer",
                "reason": "accepted differences must still block scale review",
            },
        )
        assert approval.status_code == 422
