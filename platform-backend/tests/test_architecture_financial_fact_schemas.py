from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from app import financial_fact_schemas, financial_facts

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_NAMES = (
    "CreateFinancialFactRequest",
    "FinancialFactResponse",
    "FormalPositionResponse",
    "FormalPnlResponse",
    "FormalNavSnapshotResponse",
    "FinancialProjectionRebuildResponse",
)
EXPECTED_SCHEMAS = {
    "CreateFinancialFactRequest": {
        "properties": {
            "idempotencyKey",
            "factType",
            "source",
            "externalId",
            "strategyInstanceId",
            "accountId",
            "instrumentId",
            "side",
            "quantity",
            "price",
            "amount",
            "currency",
            "availableBalance",
            "fxRateToBase",
            "occurredAt",
            "payload",
        },
        "required": {
            "idempotencyKey",
            "factType",
            "source",
            "externalId",
            "strategyInstanceId",
            "occurredAt",
        },
    },
    "FinancialFactResponse": {
        "properties": {
            "factId",
            "idempotencyKey",
            "factType",
            "source",
            "externalId",
            "strategyInstanceId",
            "accountId",
            "instrumentId",
            "side",
            "quantity",
            "quantityUnit",
            "price",
            "contractMultiplier",
            "amount",
            "currency",
            "baseCurrency",
            "fxRateToBase",
            "convertedAmount",
            "availableBalance",
            "occurredAt",
            "dataQualityState",
            "createdAt",
        },
        "required": {
            "factId",
            "idempotencyKey",
            "factType",
            "source",
            "externalId",
            "strategyInstanceId",
            "baseCurrency",
            "occurredAt",
            "dataQualityState",
            "createdAt",
        },
    },
    "FormalPositionResponse": {
        "properties": {
            "strategyInstanceId",
            "accountId",
            "instrumentId",
            "netQuantity",
            "averagePrice",
            "quantityUnit",
            "dataQualityState",
            "updatedAt",
        },
        "required": {
            "strategyInstanceId",
            "accountId",
            "instrumentId",
            "netQuantity",
            "quantityUnit",
            "dataQualityState",
            "updatedAt",
        },
    },
    "FormalPnlResponse": {
        "properties": {
            "strategyInstanceId",
            "accountId",
            "instrumentId",
            "currency",
            "tradingPnl",
            "fundingPnl",
            "swapPnl",
            "feePnl",
            "fxPnl",
            "totalPnl",
            "factCount",
            "dataQualityState",
            "updatedAt",
        },
        "required": {
            "strategyInstanceId",
            "accountId",
            "instrumentId",
            "currency",
            "tradingPnl",
            "fundingPnl",
            "swapPnl",
            "feePnl",
            "fxPnl",
            "totalPnl",
            "factCount",
            "dataQualityState",
            "updatedAt",
        },
    },
    "FormalNavSnapshotResponse": {
        "properties": {
            "snapshotId",
            "strategyInstanceId",
            "valuationTime",
            "equity",
            "capitalBase",
            "nav",
            "currency",
            "dataQualityState",
            "requiredAccountCount",
            "includedAccountCount",
            "missingAccountIds",
            "createdAt",
        },
        "required": {
            "snapshotId",
            "strategyInstanceId",
            "valuationTime",
            "capitalBase",
            "currency",
            "dataQualityState",
            "requiredAccountCount",
            "includedAccountCount",
            "missingAccountIds",
            "createdAt",
        },
    },
    "FinancialProjectionRebuildResponse": {
        "properties": {
            "strategyInstanceId",
            "rebuiltPairCount",
            "factCount",
            "completedAt",
        },
        "required": {
            "strategyInstanceId",
            "rebuiltPairCount",
            "factCount",
            "completedAt",
        },
    },
}


def test_financial_fact_schemas_have_one_authoritative_owner() -> None:
    source = (BACKEND_ROOT / "app/financial_facts.py").read_text(encoding="utf-8")
    class_names = {
        node.name
        for node in ast.parse(source).body
        if isinstance(node, ast.ClassDef)
    }

    assert class_names.isdisjoint(SCHEMA_NAMES)
    for name in SCHEMA_NAMES:
        canonical = getattr(financial_fact_schemas, name)
        compatibility = getattr(financial_facts, name)
        assert compatibility is canonical
        assert canonical.__module__ == "app.financial_fact_schemas"


def test_financial_fact_public_json_schemas_are_stable() -> None:
    for name, expected in EXPECTED_SCHEMAS.items():
        model = getattr(financial_fact_schemas, name)
        schema = model.model_json_schema(by_alias=True)
        assert set(schema["properties"]) == expected["properties"]
        assert set(schema.get("required", [])) == expected["required"]


def test_financial_fact_request_validation_is_preserved() -> None:
    common = {
        "idempotencyKey": "schema-golden-1",
        "factType": "trade_fill",
        "source": "schema-golden",
        "externalId": "external-schema-golden-1",
        "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
        "occurredAt": "2026-07-24T00:00:00+00:00",
    }

    with pytest.raises(ValidationError, match="Trade facts require"):
        financial_fact_schemas.CreateFinancialFactRequest.model_validate(common)

    request = financial_fact_schemas.CreateFinancialFactRequest.model_validate(
        {
            **common,
            "accountId": "account_sim_usdt",
            "instrumentId": "instrument_btc_usdt",
            "side": "buy",
            "quantity": "1",
            "price": "100",
        }
    )
    assert request.model_dump(by_alias=True, mode="json") == {
        **common,
        "accountId": "account_sim_usdt",
        "instrumentId": "instrument_btc_usdt",
        "side": "buy",
        "quantity": "1",
        "price": "100",
        "amount": None,
        "currency": None,
        "availableBalance": None,
        "fxRateToBase": None,
        "payload": {},
    }
