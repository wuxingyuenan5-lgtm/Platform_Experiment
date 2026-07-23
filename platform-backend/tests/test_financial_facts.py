from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


def fact_payload(
    *,
    key: str,
    fact_type: str,
    external_id: str,
    occurred_at: str,
    **extra,
) -> dict[str, object]:
    return {
        "idempotencyKey": key,
        "factType": fact_type,
        "source": "golden-test",
        "externalId": external_id,
        "strategyInstanceId": STRATEGY_ID,
        "accountId": ACCOUNT_ID,
        "instrumentId": INSTRUMENT_ID,
        "occurredAt": occurred_at,
        **extra,
    }


def test_financial_facts_are_idempotent_rebuildable_and_componentized(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "financial-facts.db")
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

        buy = fact_payload(
            key="fill-buy-1",
            fact_type="trade_fill",
            external_id="fill-buy-1",
            occurred_at="2026-07-23T01:00:00+00:00",
            side="buy",
            quantity="2",
            price="100",
        )
        sell = fact_payload(
            key="fill-sell-1",
            fact_type="trade_fill",
            external_id="fill-sell-1",
            occurred_at="2026-07-23T02:00:00+00:00",
            side="sell",
            quantity="1",
            price="110",
        )
        assert client.post("/api/v1/financial-facts", json=buy).status_code == 200
        assert client.post("/api/v1/financial-facts", json=sell).status_code == 200

        duplicate = client.post("/api/v1/financial-facts", json=sell)
        assert duplicate.status_code == 200
        conflict = client.post(
            "/api/v1/financial-facts",
            json={**sell, "price": "111"},
        )
        assert conflict.status_code == 409

        for key, fact_type, amount, hour in [
            ("funding-1", "funding", "5", 3),
            ("swap-1", "swap", "2", 4),
            ("fee-1", "fee", "-1", 5),
            ("fx-1", "fx", "3", 6),
        ]:
            response = client.post(
                "/api/v1/financial-facts",
                json=fact_payload(
                    key=key,
                    fact_type=fact_type,
                    external_id=key,
                    occurred_at=f"2026-07-23T0{hour}:00:00+00:00",
                    amount=amount,
                    currency="USDT",
                ),
            )
            assert response.status_code == 200

        pnl_response = client.get(
            f"/api/v1/strategies/instances/{STRATEGY_ID}/formal-pnl"
        )
        assert pnl_response.status_code == 200
        pnl = pnl_response.json()[0]
        assert pnl["tradingPnl"] == "100"
        assert pnl["fundingPnl"] == "5"
        assert pnl["swapPnl"] == "2"
        assert pnl["feePnl"] == "-1"
        assert pnl["fxPnl"] == "3"
        assert pnl["totalPnl"] == "109"
        assert pnl["factCount"] == 6
        assert pnl["dataQualityState"] == "complete"

        position_response = client.get(
            f"/api/v1/strategies/instances/{STRATEGY_ID}/formal-positions"
        )
        assert position_response.status_code == 200
        position = position_response.json()[0]
        assert position["netQuantity"] == "1"
        assert position["averagePrice"] == "100"
        assert position["quantityUnit"] == "BTC"

        with connection() as db:
            db.execute(
                "DELETE FROM formal_positions WHERE strategy_instance_id = ?",
                (STRATEGY_ID,),
            )
            db.execute(
                "DELETE FROM formal_pnl_results WHERE strategy_instance_id = ?",
                (STRATEGY_ID,),
            )
        rebuild = client.post(
            f"/api/v1/strategies/instances/{STRATEGY_ID}/financials/rebuild"
        )
        assert rebuild.status_code == 200
        assert rebuild.json()["rebuiltPairCount"] == 1
        rebuilt_pnl = client.get(
            f"/api/v1/strategies/instances/{STRATEGY_ID}/formal-pnl"
        ).json()[0]
        assert rebuilt_pnl["totalPnl"] == "109"

        facts = client.get(
            "/api/v1/financial-facts",
            params={"strategyInstanceId": STRATEGY_ID},
        )
        assert facts.status_code == 200
        assert len(facts.json()) == 6


def test_formal_nav_uses_one_valuation_time_and_reports_missing_accounts(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "formal-nav.db")
    with TestClient(app) as client:
        second_account = "account_sim_usdt_secondary"
        with connection() as db:
            venue_id = db.execute(
                "SELECT venue_id FROM accounts WHERE id = ?",
                (ACCOUNT_ID,),
            ).fetchone()["venue_id"]
            db.execute(
                """
                INSERT INTO accounts (
                    id, venue_id, account_code, name, account_type, environment,
                    base_currency, credential_ref, status, data_quality_state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    second_account,
                    venue_id,
                    "SIM-USDT-SECONDARY",
                    "Secondary Simulation",
                    "simulation",
                    "simulation",
                    "USDT",
                    None,
                    "active",
                    "complete",
                    "2026-07-23T00:00:00+00:00",
                ),
            )
            db.execute(
                """
                INSERT INTO strategy_account_bindings (
                    id, strategy_instance_id, account_id, role, max_notional, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "binding_funding_secondary",
                    STRATEGY_ID,
                    second_account,
                    "secondary",
                    None,
                    "active",
                    "2026-07-23T00:00:00+00:00",
                ),
            )

        first_balance = {
            "idempotencyKey": "balance-primary-1",
            "factType": "balance",
            "source": "golden-test",
            "externalId": "balance-primary-1",
            "strategyInstanceId": STRATEGY_ID,
            "accountId": ACCOUNT_ID,
            "amount": "100000",
            "availableBalance": "90000",
            "currency": "USDT",
            "occurredAt": "2026-07-23T08:00:00+00:00",
        }
        assert client.post("/api/v1/financial-facts", json=first_balance).status_code == 200

        partial = client.post(
            f"/api/v1/strategies/instances/{STRATEGY_ID}/formal-nav-snapshots/run",
            params={"valuationTime": "2026-07-23T09:00:00+00:00"},
        )
        assert partial.status_code == 200
        assert partial.json()["dataQualityState"] == "partial"
        assert partial.json()["requiredAccountCount"] == 2
        assert partial.json()["includedAccountCount"] == 1
        assert partial.json()["missingAccountIds"] == [second_account]
        assert partial.json()["equity"] == "100000"
        assert partial.json()["nav"] == "1"

        second_balance = {
            "idempotencyKey": "balance-secondary-1",
            "factType": "balance",
            "source": "golden-test",
            "externalId": "balance-secondary-1",
            "strategyInstanceId": STRATEGY_ID,
            "accountId": second_account,
            "amount": "50000",
            "availableBalance": "45000",
            "currency": "USDT",
            "occurredAt": "2026-07-23T08:30:00+00:00",
        }
        assert client.post("/api/v1/financial-facts", json=second_balance).status_code == 200

        complete = client.post(
            f"/api/v1/strategies/instances/{STRATEGY_ID}/formal-nav-snapshots/run",
            params={"valuationTime": "2026-07-23T09:00:00+00:00"},
        )
        assert complete.status_code == 200
        assert complete.json()["dataQualityState"] == "complete"
        assert complete.json()["includedAccountCount"] == 2
        assert complete.json()["missingAccountIds"] == []
        assert complete.json()["equity"] == "150000"
        assert complete.json()["nav"] == "1.5"


def test_cross_currency_fact_without_fx_is_explicitly_incomplete(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "financial-quality.db")
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/financial-facts",
            json=fact_payload(
                key="funding-usd-no-fx",
                fact_type="funding",
                external_id="funding-usd-no-fx",
                occurred_at="2026-07-23T10:00:00+00:00",
                amount="10",
                currency="USD",
            ),
        )
        assert response.status_code == 200
        assert response.json()["dataQualityState"] == "incomplete"
        assert response.json()["convertedAmount"] is None

        pnl = client.get(
            f"/api/v1/strategies/instances/{STRATEGY_ID}/formal-pnl"
        ).json()[0]
        assert pnl["fundingPnl"] == "0"
        assert pnl["totalPnl"] == "0"
        assert pnl["dataQualityState"] == "incomplete"
