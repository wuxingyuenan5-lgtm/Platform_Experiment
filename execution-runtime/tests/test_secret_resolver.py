from app.secret_resolver import inspect_credential_reference


def test_secret_reference_maps_to_local_env_names_without_exposing_values(monkeypatch) -> None:
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_API_KEY", "real-api-key")
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_SECRET", "real-secret")
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_PASSPHRASE", "real-passphrase")

    result = inspect_credential_reference("secret://crypto-test-001")

    assert result.credential_ref == "secret://crypto-test-001"
    assert result.env_prefix == "VG_SECRET_CRYPTO_TEST_001"
    assert result.configured is True
    assert result.available_fields == ["API_KEY", "PASSPHRASE", "SECRET"]
    assert result.missing_fields == []
    assert "real-api-key" not in result.model_dump_json()
    assert "real-secret" not in result.model_dump_json()
    assert "real-passphrase" not in result.model_dump_json()


def test_secret_reference_reports_missing_required_fields(monkeypatch) -> None:
    monkeypatch.delenv("VG_SECRET_MT5_DEMO_001_API_KEY", raising=False)
    monkeypatch.delenv("VG_SECRET_MT5_DEMO_001_SECRET", raising=False)
    monkeypatch.delenv("VG_SECRET_MT5_DEMO_001_PASSPHRASE", raising=False)

    result = inspect_credential_reference("secret://mt5-demo-001")

    assert result.configured is False
    assert result.env_prefix == "VG_SECRET_MT5_DEMO_001"
    assert result.missing_fields == ["API_KEY", "SECRET"]
