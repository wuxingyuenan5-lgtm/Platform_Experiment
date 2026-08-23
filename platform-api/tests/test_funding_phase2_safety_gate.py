from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.strategies.funding_orchestration import get_funding_controlled_live_readiness


def test_funding_controlled_live_is_rejected_until_phase_2_capability_exists(
    tmp_path: Path,
) -> None:
    """Removing the Phase 2 gate would turn the legacy two-market-leg path live."""
    settings = get_settings()
    settings.database_path = str(tmp_path / "funding-phase-2-gate.db")
    settings.live_trading_enabled = True
    settings.default_trading_environment = "live"

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


def test_funding_controlled_live_readiness_reports_closed_by_default(
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "funding-phase-2-readiness.db")
    settings.live_trading_enabled = False

    readiness = get_funding_controlled_live_readiness(
        strategy_instance_id="strategy_funding_arbitrage_instance_default",
        account_id="account_bybit_funding",
    )

    assert readiness["liveTradingEnabled"] is False
    assert readiness["sharedClaims"] is True
    assert readiness["balanceReservations"] is True
    assert readiness["ready"] is False
