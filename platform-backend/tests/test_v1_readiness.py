from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_v1_readiness_marks_closed_loop_strategy_runnable(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "readiness-runnable.db")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/strategies/instances/"
            "strategy_funding_arbitrage_instance_default/v1-readiness"
        )

        assert response.status_code == 200
        body = response.json()
        assert body["runnable"] is True
        assert body["strategyKey"] == "funding_arbitrage"
        assert body["blockers"] == []
        assert body["manualInterventionCount"] == 0
        assert body["resultUnknownOrderCount"] == 0


def test_v1_readiness_blocks_reserved_strategy(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "readiness-blocked.db")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/strategies/instances/"
            "strategy_home_abroad_spread_instance_default/v1-readiness"
        )

        assert response.status_code == 200
        body = response.json()
        assert body["runnable"] is False
        assert "Strategy is not in V1 closed-loop scope" in body["blockers"]
