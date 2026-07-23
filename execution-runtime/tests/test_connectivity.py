from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_gateway_connectivity_exposes_only_credential_metadata(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.journal_path = str(tmp_path / "runtime_journal.db")
    settings.credential_refs = "secret://crypto-test-001,secret://mt5-demo-001"
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_API_KEY", "real-api-key")
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_SECRET", "real-secret")

    with TestClient(app) as client:
        response = client.get("/gateway/connectivity")

    assert response.status_code == 200
    body = response.json()
    assert body["gateway"] == "fake"
    assert body["credentialCount"] == 2
    assert body["configuredCredentialCount"] == 1
    assert body["credentials"][0]["credentialRef"] == "secret://crypto-test-001"
    assert body["credentials"][0]["configured"] is True
    assert body["credentials"][1]["credentialRef"] == "secret://mt5-demo-001"
    assert body["credentials"][1]["configured"] is False
    serialized = str(body).lower()
    assert "real-api-key" not in serialized
    assert "real-secret" not in serialized
