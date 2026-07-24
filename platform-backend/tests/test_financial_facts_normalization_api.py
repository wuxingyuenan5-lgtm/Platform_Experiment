from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


def test_api_persists_exact_normalized_values_and_content_hash(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "normalization-api.db")
    with TestClient(app) as client:
        with connection() as db:
            db.execute(
                """
                UPDATE contract_specifications
                SET contract_multiplier = '10'
                WHERE instrument_id = ?
                """,
                (INSTRUMENT_ID,),
            )

        trade = client.post(
            "/api/v1/financial-facts",
            json={
                "idempotencyKey": "api-trade-1",
                "factType": "trade_fill",
                "source": "normalization-api",
                "externalId": "api-trade-1",
                "strategyInstanceId": STRATEGY_ID,
                "accountId": ACCOUNT_ID,
                "instrumentId": INSTRUMENT_ID,
                "side": "buy",
                "quantity": "2.500",
                "price": "100.2500",
                "currency": "usdt",
                "occurredAt": "2026-07-24T08:30:00+08:00",
                "payload": {"z": 1, "a": "first"},
            },
        )
        assert trade.status_code == 200
        assert trade.json()["currency"] == "USDT"
        assert trade.json()["baseCurrency"] == "USDT"
        assert trade.json()["quantityUnit"] == "BTC"
        assert trade.json()["contractMultiplier"] == "10"
        assert trade.json()["fxRateToBase"] is None
        assert trade.json()["dataQualityState"] == "complete"

        with connection() as db:
            row = db.execute(
                "SELECT * FROM financial_facts WHERE idempotency_key = ?",
                ("api-trade-1",),
            ).fetchone()
        assert row is not None
        assert row["quantity"] == "2.500"
        assert row["price"] == "100.2500"
        assert row["currency"] == "USDT"
        assert row["base_currency"] == "USDT"
        assert row["quantity_unit"] == "BTC"
        assert row["contract_multiplier"] == "10"
        assert row["occurred_at"] == "2026-07-24T00:30:00+00:00"
        assert row["payload_json"] == '{"a": "first", "z": 1}'
        assert row["content_hash"] == (
            "15b3ed2f558dc728491664013383dba2a4d0081e0c1a2e4e11e486210e5f66ec"
        )

        same_currency = client.post(
            "/api/v1/financial-facts",
            json={
                "idempotencyKey": "api-funding-same-currency",
                "factType": "funding",
                "source": "normalization-api",
                "externalId": "api-funding-same-currency",
                "strategyInstanceId": STRATEGY_ID,
                "accountId": ACCOUNT_ID,
                "instrumentId": INSTRUMENT_ID,
                "amount": "5.00",
                "currency": "usdt",
                "fxRateToBase": "9.5",
                "occurredAt": "2026-07-24T01:00:00Z",
            },
        )
        assert same_currency.status_code == 200
        assert same_currency.json()["currency"] == "USDT"
        assert same_currency.json()["fxRateToBase"] == "1"
        assert same_currency.json()["convertedAmount"] == "5.00"
        assert same_currency.json()["dataQualityState"] == "complete"

        cross_currency = client.post(
            "/api/v1/financial-facts",
            json={
                "idempotencyKey": "api-funding-cross-currency",
                "factType": "funding",
                "source": "normalization-api",
                "externalId": "api-funding-cross-currency",
                "strategyInstanceId": STRATEGY_ID,
                "accountId": ACCOUNT_ID,
                "instrumentId": INSTRUMENT_ID,
                "amount": "10",
                "currency": "usd",
                "occurredAt": "2026-07-24T02:00:00Z",
            },
        )
        assert cross_currency.status_code == 200
        assert cross_currency.json()["currency"] == "USD"
        assert cross_currency.json()["fxRateToBase"] is None
        assert cross_currency.json()["convertedAmount"] is None
        assert cross_currency.json()["dataQualityState"] == "incomplete"


def test_api_validation_status_and_detail_contracts_are_unchanged(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "normalization-errors.db")
    with TestClient(app) as client:
        missing_strategy = client.post(
            "/api/v1/financial-facts",
            json={
                "idempotencyKey": "missing-strategy",
                "factType": "balance",
                "source": "normalization-api",
                "externalId": "missing-strategy",
                "strategyInstanceId": "missing-strategy",
                "accountId": ACCOUNT_ID,
                "amount": "1",
                "currency": "USDT",
                "occurredAt": "2026-07-24T00:00:00Z",
            },
        )
        assert missing_strategy.status_code == 404
        assert missing_strategy.json()["detail"] == "Strategy instance not found"

        unbound_account = client.post(
            "/api/v1/financial-facts",
            json={
                "idempotencyKey": "unbound-account",
                "factType": "balance",
                "source": "normalization-api",
                "externalId": "unbound-account",
                "strategyInstanceId": STRATEGY_ID,
                "accountId": "missing-account",
                "amount": "1",
                "currency": "USDT",
                "occurredAt": "2026-07-24T00:00:00Z",
            },
        )
        assert unbound_account.status_code == 403
        assert unbound_account.json()["detail"] == (
            "Account is not actively bound to strategy"
        )

        missing_instrument = client.post(
            "/api/v1/financial-facts",
            json={
                "idempotencyKey": "missing-instrument",
                "factType": "trade_fill",
                "source": "normalization-api",
                "externalId": "missing-instrument",
                "strategyInstanceId": STRATEGY_ID,
                "accountId": ACCOUNT_ID,
                "instrumentId": "missing-instrument",
                "side": "buy",
                "quantity": "1",
                "price": "100",
                "currency": "USDT",
                "occurredAt": "2026-07-24T00:00:00Z",
            },
        )
        assert missing_instrument.status_code == 422
        assert missing_instrument.json()["detail"] == (
            "Instrument or contract specification is unavailable"
        )

        currency_mismatch = client.post(
            "/api/v1/financial-facts",
            json={
                "idempotencyKey": "currency-mismatch",
                "factType": "trade_fill",
                "source": "normalization-api",
                "externalId": "currency-mismatch",
                "strategyInstanceId": STRATEGY_ID,
                "accountId": ACCOUNT_ID,
                "instrumentId": INSTRUMENT_ID,
                "side": "buy",
                "quantity": "1",
                "price": "100",
                "currency": "USD",
                "occurredAt": "2026-07-24T00:00:00Z",
            },
        )
        assert currency_mismatch.status_code == 422
        assert currency_mismatch.json()["detail"] == (
            "Trade fact currency must match instrument settlement currency"
        )
