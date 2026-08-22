from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_funding_controlled_live_is_rejected_until_phase_2_capability_exists(
    tmp_path: Path,
) -> None:
    """Removing the Phase 2 gate would turn the legacy two-market-leg path live."""
    settings = get_settings()
    settings.database_path = str(tmp_path / "funding-phase-2-gate.db")
    settings.live_trading_enabled = True

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/funding/market-command",
            json={
                "action": "OPEN_SHORT_PERP_LONG_SPOT",
                "perpetualSymbol": "BTCUSDT",
                "spotSymbol": "BTC",
                "quantity": "1",
            },
        )

    assert response.status_code == 423
    assert response.json()["detail"] == (
        "Funding controlled-live execution requires Phase 2 post-only "
        "chase and authoritative incremental release"
    )
