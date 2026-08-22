from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

EXPECTED_READ_ONLY_INSTANCES = {
    "strategy_bottom_fishing_instance_default",
    "strategy_short_term_l_instance_default",
    "strategy_short_term_w_instance_default",
}


def test_existing_management_strategies_have_bybit_account_bindings_with_read_only_capability(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "strategy-account-registry.db")

    with TestClient(app) as client:
        definitions = client.get("/api/v1/strategies/definitions")
        assert definitions.status_code == 200
        definitions_by_key = {item["strategyKey"]: item for item in definitions.json()}
        assert definitions_by_key["funding_arbitrage"]["status"] == "active"
        for strategy_key in ("bottom_fishing", "short_term_l", "short_term_w"):
            assert definitions_by_key[strategy_key]["status"] == "active"
            assert definitions_by_key[strategy_key]["v1Scope"] == "read_only"

        funding = client.get(
            "/api/v1/strategies/instances/"
            "strategy_funding_arbitrage_instance_default/accounts"
        )
        assert funding.status_code == 200
        funding_bindings = funding.json()
        assert {
            (item["accountId"], item["role"], item["capability"])
            for item in funding_bindings
        } == {
            ("account_bybit_funding", "primary", "trade_and_read"),
            ("account_sim_usdt", "local_test", "trade_and_read"),
        }

        for instance_id in EXPECTED_READ_ONLY_INSTANCES:
            response = client.get(f"/api/v1/strategies/instances/{instance_id}/accounts")
            assert response.status_code == 200
            bindings = response.json()
            assert len(bindings) == 1
            assert bindings[0]["capability"] == "read_only"
            assert bindings[0]["accountCode"].startswith("BYBIT-")
            assert bindings[0]["status"] == "active"
