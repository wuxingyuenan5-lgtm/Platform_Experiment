from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app import financial_projection_service as service

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


@pytest.mark.parametrize(
    ("old_quantity", "old_average", "signed_fill", "fill_price", "expected"),
    [
        (
            Decimal("0"),
            None,
            Decimal("2"),
            Decimal("100"),
            (Decimal("2"), Decimal("100"), Decimal("0")),
        ),
        (
            Decimal("2"),
            Decimal("100"),
            Decimal("1"),
            Decimal("130"),
            (Decimal("3"), Decimal("110"), Decimal("0")),
        ),
        (
            Decimal("2"),
            Decimal("100"),
            Decimal("-1"),
            Decimal("110"),
            (Decimal("1"), Decimal("100"), Decimal("10")),
        ),
        (
            Decimal("2"),
            Decimal("100"),
            Decimal("-3"),
            Decimal("90"),
            (Decimal("-1"), Decimal("90"), Decimal("-20")),
        ),
        (
            Decimal("-2"),
            Decimal("100"),
            Decimal("1"),
            Decimal("90"),
            (Decimal("-1"), Decimal("100"), Decimal("10")),
        ),
        (
            Decimal("-2"),
            Decimal("100"),
            Decimal("2"),
            Decimal("110"),
            (Decimal("0"), None, Decimal("-20")),
        ),
    ],
)
def test_calculate_position_update_golden_vectors(
    old_quantity: Decimal,
    old_average: Decimal | None,
    signed_fill: Decimal,
    fill_price: Decimal,
    expected: tuple[Decimal, Decimal | None, Decimal],
) -> None:
    assert service.calculate_position_update(
        old_quantity=old_quantity,
        old_average=old_average,
        signed_fill=signed_fill,
        fill_price=fill_price,
    ) == expected


def test_projection_rebuild_preserves_component_attribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facts = [
        {
            "fact_type": "trade_fill",
            "base_currency": "USDT",
            "quantity_unit": "BTC",
            "quantity": "2",
            "side": "buy",
            "price": "100",
            "contract_multiplier": "10",
            "currency": "USDT",
            "fx_rate_to_base": None,
            "converted_amount": None,
            "occurred_at": "2026-07-23T01:00:00+00:00",
        },
        {
            "fact_type": "trade_fill",
            "base_currency": "USDT",
            "quantity_unit": "BTC",
            "quantity": "1",
            "side": "sell",
            "price": "110",
            "contract_multiplier": "10",
            "currency": "USDT",
            "fx_rate_to_base": None,
            "converted_amount": None,
            "occurred_at": "2026-07-23T02:00:00+00:00",
        },
        {
            "fact_type": "funding",
            "base_currency": "USDT",
            "quantity_unit": None,
            "converted_amount": "5",
            "occurred_at": "2026-07-23T03:00:00+00:00",
        },
        {
            "fact_type": "swap",
            "base_currency": "USDT",
            "quantity_unit": None,
            "converted_amount": "2",
            "occurred_at": "2026-07-23T04:00:00+00:00",
        },
        {
            "fact_type": "fee",
            "base_currency": "USDT",
            "quantity_unit": None,
            "converted_amount": "-1",
            "occurred_at": "2026-07-23T05:00:00+00:00",
        },
        {
            "fact_type": "fx",
            "base_currency": "USDT",
            "quantity_unit": None,
            "converted_amount": "3",
            "occurred_at": "2026-07-23T06:00:00+00:00",
        },
    ]
    captured: dict[str, object] = {}
    monkeypatch.setattr(service.repository, "ensure_schema", lambda: None)
    monkeypatch.setattr(service.repository, "list_projection_fact_rows", lambda *_: facts)
    monkeypatch.setattr(
        service.repository,
        "save_formal_projection",
        lambda **kwargs: captured.update(kwargs),
    )

    service.rebuild_account_instrument_projection(STRATEGY_ID, ACCOUNT_ID, INSTRUMENT_ID)

    assert captured == {
        "strategy_instance_id": STRATEGY_ID,
        "account_id": ACCOUNT_ID,
        "instrument_id": INSTRUMENT_ID,
        "has_trade": True,
        "net_quantity": "1",
        "average_price": "100",
        "quantity_unit": "BTC",
        "currency": "USDT",
        "trading_pnl": "100",
        "funding_pnl": "5",
        "swap_pnl": "2",
        "fee_pnl": "-1",
        "fx_pnl": "3",
        "total_pnl": "109",
        "fact_count": 6,
        "data_quality_state": "complete",
        "updated_at": "2026-07-23T06:00:00+00:00",
    }


def test_projection_rebuild_propagates_incomplete_quality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facts = [
        {
            "fact_type": "trade_fill",
            "base_currency": "USDT",
            "quantity_unit": "BTC",
            "quantity": "1",
            "side": "buy",
            "price": "100",
            "contract_multiplier": "1",
            "currency": "USD",
            "fx_rate_to_base": None,
            "converted_amount": None,
            "occurred_at": "2026-07-23T01:00:00+00:00",
        },
        {
            "fact_type": "trade_fill",
            "base_currency": "USDT",
            "quantity_unit": "BTC",
            "quantity": "1",
            "side": "sell",
            "price": "110",
            "contract_multiplier": "1",
            "currency": "USD",
            "fx_rate_to_base": None,
            "converted_amount": None,
            "occurred_at": "2026-07-23T02:00:00+00:00",
        },
        {
            "fact_type": "funding",
            "base_currency": "USDT",
            "quantity_unit": None,
            "converted_amount": None,
            "occurred_at": "2026-07-23T03:00:00+00:00",
        },
    ]
    captured: dict[str, object] = {}
    monkeypatch.setattr(service.repository, "ensure_schema", lambda: None)
    monkeypatch.setattr(service.repository, "list_projection_fact_rows", lambda *_: facts)
    monkeypatch.setattr(
        service.repository,
        "save_formal_projection",
        lambda **kwargs: captured.update(kwargs),
    )

    service.rebuild_account_instrument_projection(STRATEGY_ID, ACCOUNT_ID, INSTRUMENT_ID)

    assert captured["trading_pnl"] == "0"
    assert captured["funding_pnl"] == "0"
    assert captured["total_pnl"] == "0"
    assert captured["data_quality_state"] == "incomplete"


def test_strategy_rebuild_preserves_pair_order_counts_and_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pairs = [
        {"account_id": "account-b", "instrument_id": "instrument-2"},
        {"account_id": "account-a", "instrument_id": "instrument-1"},
    ]
    rebuilt: list[tuple[str, str, str]] = []
    audit: dict[str, object] = {}
    monkeypatch.setattr(service.repository, "ensure_schema", lambda: None)
    monkeypatch.setattr(
        service.repository,
        "prepare_strategy_rebuild",
        lambda *_: (7, pairs),
    )
    monkeypatch.setattr(
        service,
        "rebuild_account_instrument_projection",
        lambda strategy_id, account_id, instrument_id: rebuilt.append(
            (strategy_id, account_id, instrument_id)
        ),
    )
    monkeypatch.setattr(service, "now_iso", lambda: "2026-07-24T00:00:00+00:00")
    monkeypatch.setattr(service, "uuid4", lambda: "audit-rebuild-1")
    monkeypatch.setattr(
        service.repository,
        "record_projection_rebuild_audit",
        lambda **kwargs: audit.update(kwargs),
    )

    response = service.rebuild_strategy_financials(STRATEGY_ID)

    assert rebuilt == [
        (STRATEGY_ID, "account-b", "instrument-2"),
        (STRATEGY_ID, "account-a", "instrument-1"),
    ]
    assert response.model_dump(by_alias=True, mode="json") == {
        "strategyInstanceId": STRATEGY_ID,
        "rebuiltPairCount": 2,
        "factCount": 7,
        "completedAt": "2026-07-24T00:00:00Z",
    }
    assert audit == {
        "audit_event_id": "audit-rebuild-1",
        "strategy_instance_id": STRATEGY_ID,
        "details_json": '{"factCount": 7, "rebuiltPairCount": 2}',
        "created_at": "2026-07-24T00:00:00+00:00",
    }


def test_nav_calculation_preserves_coverage_and_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    sentinel = object()
    monkeypatch.setattr(service.repository, "ensure_schema", lambda: None)
    monkeypatch.setattr(
        service.repository,
        "list_active_account_rows",
        lambda *_: [{"account_id": "account-a"}, {"account_id": "account-b"}],
    )
    monkeypatch.setattr(
        service.repository,
        "load_latest_balance_rows",
        lambda *_: {
            "account-a": {"converted_amount": "100000"},
            "account-b": None,
        },
    )
    monkeypatch.setattr(service, "now_iso", lambda: "2026-07-24T00:00:00+00:00")
    ids = iter(["snapshot-1", "audit-nav-1"])
    monkeypatch.setattr(service, "uuid4", lambda: next(ids))
    monkeypatch.setattr(
        service.repository,
        "store_formal_nav_snapshot",
        lambda **kwargs: captured.update(kwargs) or sentinel,
    )

    response = service.run_formal_nav_snapshot(
        STRATEGY_ID,
        capital_base=Decimal("100000"),
        base_currency="USDT",
        valuation_time=datetime(2026, 7, 23, 9, tzinfo=UTC),
    )

    assert response is sentinel
    assert captured == {
        "snapshot_id": "snapshot-1",
        "audit_event_id": "audit-nav-1",
        "strategy_instance_id": STRATEGY_ID,
        "valuation_time": "2026-07-23T09:00:00+00:00",
        "equity": "100000",
        "capital_base": "100000",
        "nav": "1",
        "currency": "USDT",
        "data_quality_state": "partial",
        "required_account_count": 2,
        "included_account_count": 1,
        "missing_account_ids_json": '["account-b"]',
        "audit_details_json": (
            '{"dataQualityState": "partial", "includedAccountCount": 1, '
            '"missingAccountIds": ["account-b"], "requiredAccountCount": 2, '
            '"valuationTime": "2026-07-23T09:00:00+00:00"}'
        ),
        "created_at": "2026-07-24T00:00:00+00:00",
    }


def test_nav_rejects_invalid_capital_and_missing_accounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service.repository, "ensure_schema", lambda: None)
    with pytest.raises(service.InvalidCapitalBaseError, match="no valid capital base"):
        service.run_formal_nav_snapshot(
            STRATEGY_ID,
            capital_base=None,
            base_currency="USDT",
        )

    monkeypatch.setattr(service.repository, "list_active_account_rows", lambda *_: [])
    with pytest.raises(
        service.NoActiveAccountBindingsError,
        match="no active account bindings",
    ):
        service.run_formal_nav_snapshot(
            STRATEGY_ID,
            capital_base=Decimal("100000"),
            base_currency="USDT",
        )
