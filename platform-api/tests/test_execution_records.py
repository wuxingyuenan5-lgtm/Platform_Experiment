"""Durable execution records: projection, idempotency and detail aggregation."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.config import get_settings
from app.database import initialize_database
from app.execution_records import (
    capture_account_state,
    get_execution_record_detail,
    list_execution_records,
    sync_execution_record,
)

BATCH_ID = "batch-records-1"
INSTRUCTION_ID = "run-records-1"


def _seed(monkeypatch) -> None:
    initialize_database()
    path = get_settings().database_path
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = OFF")
    db.execute(
        "INSERT INTO strategy_runs (id, idempotency_key, strategy_instance_id, strategy_key,"
        " direction, status, execution_batch_id, created_at, updated_at, action,"
        " requested_parameters_json, execution_plan_json, requested_by)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            INSTRUCTION_ID,
            "idem-records-1",
            "strategy_funding_arbitrage_instance_default",
            "funding_arbitrage",
            "long",
            "completed",
            BATCH_ID,
            "2026-11-01T10:00:00+00:00",
            "2026-11-01T10:00:20+00:00",
            "open",
            '{"perpetualQuantity":"0.001"}',
            "{}",
            "demo_ceo",
        ),
    )
    db.execute(
        "INSERT INTO execution_batches (id, idempotency_key, strategy_instance_id, account_id,"
        " strategy_key, direction, status, requires_manual_intervention, created_at, updated_at,"
        " strategy_instruction_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            BATCH_ID,
            "idem-records-1",
            "strategy_funding_arbitrage_instance_default",
            "bybit-live-main",
            "funding_arbitrage",
            "long",
            "completed",
            0,
            "2026-11-01T10:00:00+00:00",
            "2026-11-01T10:00:20+00:00",
            INSTRUCTION_ID,
        ),
    )
    legs = (
        (1, "spot_leg", "BTCUSDT", "buy", "0.001001", "order-spot"),
        (2, "perpetual_leg", "BTCUSDT", "sell", "0.001", "order-perp"),
    )
    for sequence, role, symbol, side, quantity, order_id in legs:
        db.execute(
            "INSERT INTO execution_batch_legs (id, batch_id, sequence, role, account_id,"
            " instrument_id, symbol, side, order_type, quantity, price, order_id, status,"
            " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                f"leg-{sequence}",
                BATCH_ID,
                sequence,
                role,
                "bybit-live-main",
                f"instrument-{sequence}",
                symbol,
                side,
                "market",
                quantity,
                None,
                order_id,
                "filled",
                "2026-11-01T10:00:00+00:00",
                "2026-11-01T10:00:10+00:00",
            ),
        )
        db.execute(
            "INSERT INTO orders (id, command_id, account_id, instrument_id, symbol, side,"
            " order_type, quantity, price, status, external_order_id, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                order_id,
                f"command-{sequence}",
                "bybit-live-main",
                f"instrument-{sequence}",
                symbol,
                side,
                "market",
                quantity,
                None,
                "filled",
                f"external-{order_id}",
                "2026-11-01T10:00:01+00:00",
                "2026-11-01T10:00:10+00:00",
            ),
        )
        fee = "0.0780" if sequence == 1 else "0.0429"
        price = "77948.75" if sequence == 1 else "77950"
        db.execute(
            "INSERT INTO fills (id, order_id, account_id, instrument_id, side, quantity, price,"
            " occurred_at, origin, source, external_fill_id, fee, fee_currency, fee_quality)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                f"fill-{sequence}",
                order_id,
                "bybit-live-main",
                f"instrument-{sequence}",
                side,
                quantity,
                price,
                "2026-11-01T10:00:05+00:00",
                "venue_execution",
                "runtime",
                f"native-{sequence}",
                fee,
                "USDT",
                "exact",
            ),
        )
    db.commit()
    db.close()


def test_projection_is_idempotent_and_carries_totals(monkeypatch) -> None:
    _seed(monkeypatch)

    first = sync_execution_record(BATCH_ID, trace_id="trace-records")
    second = sync_execution_record(BATCH_ID)

    assert first is not None and second is not None
    assert first["id"] == second["id"]
    assert first["action"] == "open"
    assert first["status"] == "completed"
    assert first["primarySymbol"] == "BTCUSDT"
    assert first["primaryQuantity"] == "0.001"
    assert first["primaryAveragePrice"] == "77950"
    assert first["totalFees"] == "0.1209"
    assert first["feeCurrency"] == "USDT"
    assert first["legCount"] == 2
    assert first["filledLegCount"] == 2
    assert first["durationMs"] == 20000
    # Idempotent replay keeps the trace of the original submission.
    assert second["traceId"] == "trace-records"

    page = list_execution_records(strategy_key="funding_arbitrage")
    assert page["total"] == 1
    assert len(page["items"]) == 1
    assert page["items"][0]["batchId"] == BATCH_ID


def test_list_filters_by_action_and_symbol(monkeypatch) -> None:
    _seed(monkeypatch)
    sync_execution_record(BATCH_ID)

    assert list_execution_records(action="close")["total"] == 0
    assert list_execution_records(action="open")["total"] == 1
    assert list_execution_records(symbol="btc")["total"] == 1
    assert list_execution_records(symbol="ETH")["total"] == 0
    assert list_execution_records(status="failed")["total"] == 0


def test_detail_aggregates_full_chain(monkeypatch) -> None:
    _seed(monkeypatch)
    record = sync_execution_record(BATCH_ID, trace_id="trace-records")
    assert record is not None

    detail = get_execution_record_detail(record["id"])
    assert detail is not None
    assert detail["record"]["batchId"] == BATCH_ID
    assert detail["batch"] is not None and detail["batch"]["status"] == "completed"
    assert detail["instruction"]["requestedBy"] == "demo_ceo"
    assert detail["instruction"]["requestedParameters"]["perpetualQuantity"] == "0.001"
    assert len(detail["legs"]) == 2
    assert len(detail["orders"]) == 2
    assert len(detail["fills"]) == 2
    assert {fill["fee"] for fill in detail["fills"]} == {"0.0780", "0.0429"}
    assert "summary" in detail["timeline"]


def test_detail_accepts_batch_id_as_identifier(monkeypatch) -> None:
    _seed(monkeypatch)
    record = sync_execution_record(BATCH_ID)
    assert record is not None

    detail = get_execution_record_detail(BATCH_ID)
    assert detail is not None
    assert detail["record"]["id"] == record["id"]


def test_account_snapshot_records_each_phase(monkeypatch) -> None:
    _seed(monkeypatch)
    record = sync_execution_record(BATCH_ID)
    assert record is not None

    capture_account_state(
        account_id="bybit-live-main",
        phase="pre_submit",
        batch_id=BATCH_ID,
        trace_id="trace-records",
    )
    capture_account_state(
        account_id="bybit-live-main",
        phase="final",
        batch_id=BATCH_ID,
        trace_id="trace-records",
    )

    detail = get_execution_record_detail(record["id"])
    assert detail is not None
    phases: dict[str, Any] = {
        snapshot["phase"]: snapshot for snapshot in detail["accountSnapshots"]
    }
    assert set(phases) == {"pre_submit", "final"}
    assert phases["final"]["qualityState"] in {"unavailable", "complete", "partial"}
    assert isinstance(phases["pre_submit"]["positions"], list)


def test_fill_fee_backfills_from_venue_receipts(monkeypatch) -> None:
    """Runtime confirmations have no fee; the venue receipt must fill it in."""

    _seed(monkeypatch)
    path = get_settings().database_path
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = OFF")
    db.execute("UPDATE fills SET fee = NULL, fee_currency = NULL, fee_quality = NULL")
    for order_id, external_id, occurred_at, fee in (
        ("order-perp", "native-perp-exec", "2026-11-01T10:00:05.100+00:00", "0.0428879"),
        ("order-spot", "native-spot-exec", "2026-11-01T10:00:05.400+00:00", "0.000001001"),
    ):
        db.execute(
            "INSERT INTO venue_account_events (account_id, source, event_type, external_id,"
            " instrument_id, platform_order_id, occurred_at, amount, currency, payload_json)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                "bybit-live-main",
                "bybit_live",
                "trade_fill",
                external_id,
                "instrument-1",
                order_id,
                occurred_at,
                None,
                "USDT",
                '{"fee":"%s","currency":"USDT"}' % fee,
            ),
        )
    db.commit()
    db.close()

    record = sync_execution_record(BATCH_ID)
    assert record is not None
    # Both receipts are quoted in USDT, so the single total carries both legs.
    assert record["totalFees"] == "0.042888901"
    assert record["feeCurrency"] == "USDT"
    legs = {leg["role"]: leg for leg in record["legDetails"]}
    assert legs["perpetual_leg"]["fees"] == "0.0428879"
    assert legs["spot_leg"]["fees"] == "0.000001001"
    assert legs["spot_leg"]["feeCurrency"] == "USDT"
    # Each receipt must land on its own order, not be duplicated onto both.
    assert legs["perpetual_leg"]["orderId"] == "order-perp"
    assert legs["spot_leg"]["orderId"] == "order-spot"

    detail = get_execution_record_detail(record["id"])
    assert detail is not None
    assert {fill["fee"] for fill in detail["fills"]} == {"0.0428879", "0.000001001"}
    assert {fill["fee_quality"] for fill in detail["fills"]} == {"reported"}


def test_snapshots_fall_back_to_balance_series(monkeypatch) -> None:
    """A batch without hook snapshots still shows the account on both sides."""

    _seed(monkeypatch)
    path = get_settings().database_path
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = OFF")
    for suffix, as_of, available in (
        ("pre", "2026-11-01T09:59:30+00:00", "556.63"),
        ("post", "2026-11-01T10:00:40+00:00", "476.90"),
    ):
        db.execute(
            "INSERT INTO balance_snapshots (id, account_id, currency, equity,"
            " available_balance, source, data_quality_state, as_of, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (
                f"balance-{suffix}",
                "bybit-live-main",
                "USDT",
                available,
                available,
                "runtime",
                "complete",
                as_of,
                as_of,
            ),
        )
    db.commit()
    db.close()

    record = sync_execution_record(BATCH_ID)
    assert record is not None
    detail = get_execution_record_detail(record["id"])
    assert detail is not None
    snapshots = {item["phase"]: item for item in detail["accountSnapshots"]}
    assert set(snapshots) == {"pre_submit", "final"}
    assert snapshots["pre_submit"]["available"] == "556.63"
    assert snapshots["final"]["available"] == "476.90"
    assert snapshots["final"]["derivedFrom"] == "balance_snapshots"
    assert snapshots["final"]["positionCount"] is None
