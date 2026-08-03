from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.financial_fact_normalization import (
    FinancialFactNormalizationContext,
    normalize_financial_fact,
    normalized_content_hash,
)
from app.financial_fact_schemas import CreateFinancialFactRequest


def test_trade_normalization_and_content_hash_match_exact_golden() -> None:
    request = CreateFinancialFactRequest(
        idempotencyKey="trade-normalization-1",
        factType="trade_fill",
        source="golden-normalization",
        externalId="trade-1",
        strategyInstanceId="strategy-1",
        accountId="account-1",
        instrumentId="instrument-1",
        side="buy",
        quantity="2.500",
        price="100.2500",
        currency="usdt",
        fxRateToBase="7.2500",
        occurredAt="2026-07-24T08:30:00+08:00",
        payload={"z": 1, "a": "first"},
    )
    context = FinancialFactNormalizationContext(
        base_currency="USD",
        settle_currency="USDT",
        quantity_unit="BTC",
        contract_multiplier=Decimal("10"),
    )

    normalized = normalize_financial_fact(request, context)

    assert normalized == {
        "fact_type": "trade_fill",
        "source": "golden-normalization",
        "external_id": "trade-1",
        "strategy_instance_id": "strategy-1",
        "account_id": "account-1",
        "instrument_id": "instrument-1",
        "side": "buy",
        "quantity": "2.500",
        "quantity_unit": "BTC",
        "price": "100.2500",
        "contract_multiplier": "10",
        "amount": None,
        "currency": "USDT",
        "base_currency": "USD",
        "fx_rate_to_base": "7.2500",
        "converted_amount": None,
        "available_balance": None,
        "occurred_at": "2026-07-24T00:30:00+00:00",
        "payload_json": '{"a": "first", "z": 1}',
        "data_quality_state": "complete",
    }
    assert (
        normalized_content_hash(normalized)
        == "1f85b80c60bfccb013edb582ca6e11ffaeaa803879cb022aab581aa764f6b4e4"
    )


def test_same_currency_monetary_fact_forces_fx_one_and_preserves_decimal_text() -> None:
    request = CreateFinancialFactRequest(
        idempotencyKey="funding-normalization-1",
        factType="funding",
        source="golden-normalization",
        externalId="funding-1",
        strategyInstanceId="strategy-1",
        accountId="account-1",
        instrumentId="instrument-1",
        amount="5.00",
        currency="usdt",
        fxRateToBase="9.5",
        occurredAt="2026-07-24T01:02:03",
    )

    normalized = normalize_financial_fact(
        request,
        FinancialFactNormalizationContext(base_currency="USDT"),
    )

    assert normalized["currency"] == "USDT"
    assert normalized["amount"] == "5.00"
    assert normalized["fx_rate_to_base"] == "1"
    assert normalized["converted_amount"] == "5.00"
    assert normalized["occurred_at"] == "2026-07-24T01:02:03+00:00"
    assert normalized["data_quality_state"] == "complete"


def test_cross_currency_monetary_fact_without_fx_is_explicitly_incomplete() -> None:
    request = CreateFinancialFactRequest(
        idempotencyKey="funding-normalization-2",
        factType="funding",
        source="golden-normalization",
        externalId="funding-2",
        strategyInstanceId="strategy-1",
        accountId="account-1",
        instrumentId="instrument-1",
        amount="10",
        currency="usd",
        occurredAt="2026-07-24T00:00:00Z",
    )

    normalized = normalize_financial_fact(
        request,
        FinancialFactNormalizationContext(base_currency="USDT"),
    )

    assert normalized["currency"] == "USD"
    assert normalized["fx_rate_to_base"] is None
    assert normalized["converted_amount"] is None
    assert normalized["data_quality_state"] == "incomplete"


def test_trade_currency_mismatch_preserves_http_error_contract() -> None:
    request = CreateFinancialFactRequest(
        idempotencyKey="trade-normalization-mismatch",
        factType="trade_fill",
        source="golden-normalization",
        externalId="trade-mismatch",
        strategyInstanceId="strategy-1",
        accountId="account-1",
        instrumentId="instrument-1",
        side="buy",
        quantity="1",
        price="100",
        currency="USD",
        occurredAt="2026-07-24T00:00:00Z",
    )

    with pytest.raises(HTTPException) as exc_info:
        normalize_financial_fact(
            request,
            FinancialFactNormalizationContext(
                base_currency="USDT",
                settle_currency="USDT",
                quantity_unit="BTC",
                contract_multiplier=Decimal("1"),
            ),
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == (
        "Trade fact currency must match instrument settlement currency"
    )
