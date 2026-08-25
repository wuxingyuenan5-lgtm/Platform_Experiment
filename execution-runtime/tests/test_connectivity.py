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


def test_gateway_connectivity_classifies_secondary_mt5_account_reference(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "journal_path", str(tmp_path / "runtime_journal.db"))
    monkeypatch.setattr(
        settings, "mt5_credential_ref", "secret://environment/mt5-primary"
    )
    monkeypatch.setattr(
        settings,
        "mt5_account_credential_refs",
        "mt5-live-main=secret://environment/mt5-primary,"
        "account-mt5-short-a=secret://environment/mt5-secondary",
    )
    monkeypatch.setattr(
        settings,
        "credential_refs",
        "secret://environment/mt5-primary,secret://environment/mt5-secondary",
    )
    for prefix in ("VG_SECRET_MT5_PRIMARY", "VG_SECRET_MT5_SECONDARY"):
        monkeypatch.setenv(f"{prefix}_LOGIN", "10001")
        monkeypatch.setenv(f"{prefix}_PASSWORD", "password")
        monkeypatch.setenv(f"{prefix}_SERVER", "Broker")

    with TestClient(app) as client:
        response = client.get("/gateway/connectivity")

    assert response.status_code == 200
    body = response.json()
    assert body["credentialCount"] == 2
    assert body["configuredCredentialCount"] == 2
    assert body["credentials"][1]["configured"] is True
    assert body["credentials"][1]["missingFields"] == []
