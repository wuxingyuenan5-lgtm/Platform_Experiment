from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_exchange_connectivity_proxies_runtime_without_secret_material(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "exchange-connectivity.db")
    settings.runtime_base_url = "http://runtime.local"

    def fake_get(url: str, timeout: float) -> httpx.Response:
        assert url == "http://runtime.local/gateway/connectivity"
        assert timeout == settings.runtime_timeout_seconds
        return httpx.Response(
            200,
            json={
                "gateway": "bybit_mt5",
                "credentialCount": 2,
                "configuredCredentialCount": 1,
                "credentials": [
                    {
                        "credentialRef": "secret://crypto-test-001",
                        "envPrefix": "VG_SECRET_CRYPTO_TEST_001",
                        "configured": True,
                        "availableFields": ["API_KEY", "SECRET"],
                        "missingFields": [],
                    },
                    {
                        "credentialRef": "secret://mt5-demo-001",
                        "envPrefix": "VG_SECRET_MT5_DEMO_001",
                        "configured": False,
                        "availableFields": [],
                        "missingFields": ["API_KEY", "SECRET"],
                    },
                ],
            },
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    with TestClient(app) as client:
        response = client.get("/api/v1/security/exchange-connectivity")

    assert response.status_code == 200
    body = response.json()
    assert body["gateway"] == "bybit_mt5"
    assert body["configuredCredentialCount"] == 1
    assert body["credentials"][0]["credentialRef"] == "secret://crypto-test-001"
    serialized = str(body).lower()
    assert "real-api-key" not in serialized
    assert "real-secret" not in serialized


def test_exchange_connectivity_reports_runtime_unavailable(monkeypatch, tmp_path: Path) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "exchange-connectivity-down.db")
    settings.runtime_base_url = "http://runtime.local"

    def fake_get(url: str, timeout: float) -> httpx.Response:
        raise httpx.ConnectError("runtime down")

    monkeypatch.setattr(httpx, "get", fake_get)

    with TestClient(app) as client:
        response = client.get("/api/v1/security/exchange-connectivity")

    assert response.status_code == 200
    assert response.json()["status"] == "not_connected"


def test_exchange_venue_readiness_proxies_bybit_and_mt5_symbols(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "venue-readiness.db")
    settings.runtime_base_url = "http://runtime.local"

    def fake_get(url: str, timeout: float) -> httpx.Response:
        assert url == "http://runtime.local/gateway/venue-readiness"
        assert timeout == 20.0
        return httpx.Response(
            200,
            json={
                "status": "available",
                "venues": [
                    {
                        "venue": "bybit",
                        "status": "available",
                        "credentialRef": "secret://crypto-test-001",
                        "symbol": "XAUTUSDT",
                        "marketType": "linear",
                        "checks": ["ticker", "wallet"],
                        "reason": None,
                    },
                    {
                        "venue": "mt5",
                        "status": "available",
                        "credentialRef": "secret://mt5-demo-001",
                        "symbol": "XAUUSD+",
                        "marketType": None,
                        "checks": ["login", "symbol"],
                        "reason": None,
                    },
                ],
            },
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    with TestClient(app) as client:
        response = client.get("/api/v1/security/exchange-venue-readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "available"
    assert body["venues"][0]["symbol"] == "XAUTUSDT"
    assert body["venues"][0]["marketType"] == "linear"
    assert body["venues"][1]["symbol"] == "XAUUSD+"
