import pytest

from app.secret_resolver import (
    EnvironmentSecretProvider,
    WindowsCredentialManagerProvider,
    inspect_credential_reference,
    parse_secret_reference,
    reset_secret_providers,
    resolve_secret_reference,
)


def test_explicit_environment_reference_reports_metadata_without_values(monkeypatch) -> None:
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_API_KEY", "provider-api-value")
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_SECRET", "provider-secret-value")
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_PASSPHRASE", "provider-passphrase-value")
    monkeypatch.setenv("VG_SECRET_CRYPTO_TEST_001_VERSION", "2026-07-23.1")

    result = inspect_credential_reference("secret://environment/crypto-test-001")

    assert result.credential_ref == "secret://environment/crypto-test-001"
    assert result.provider == "environment"
    assert result.secret_name == "crypto-test-001"
    assert result.version == "2026-07-23.1"
    assert result.env_prefix == "VG_SECRET_CRYPTO_TEST_001"
    assert result.configured is True
    assert result.available_fields == ["API_KEY", "PASSPHRASE", "SECRET"]
    assert result.missing_fields == []
    assert result.legacy_reference is False
    serialized = result.model_dump_json()
    assert "provider-api-value" not in serialized
    assert "provider-secret-value" not in serialized
    assert "provider-passphrase-value" not in serialized

    resolved = resolve_secret_reference("secret://environment/crypto-test-001")
    assert resolved == {
        "API_KEY": "provider-api-value",
        "SECRET": "provider-secret-value",
        "PASSPHRASE": "provider-passphrase-value",
    }


def test_legacy_reference_remains_environment_compatible(monkeypatch) -> None:
    monkeypatch.setenv("VG_SECRET_LEGACY_001_API_KEY", "legacy-api-value")
    monkeypatch.setenv("VG_SECRET_LEGACY_001_SECRET", "legacy-secret-value")

    result = inspect_credential_reference("secret://legacy-001")

    assert result.provider == "environment"
    assert result.secret_name == "legacy-001"
    assert result.legacy_reference is True
    assert result.configured is True


def test_missing_required_fields_are_reported_without_values(monkeypatch) -> None:
    monkeypatch.delenv("VG_SECRET_MT5_LIVE_001_LOGIN", raising=False)
    monkeypatch.delenv("VG_SECRET_MT5_LIVE_001_PASSWORD", raising=False)
    monkeypatch.delenv("VG_SECRET_MT5_LIVE_001_SERVER", raising=False)

    result = inspect_credential_reference(
        "secret://environment/mt5-live-001",
        required_fields=("LOGIN", "PASSWORD", "SERVER"),
    )

    assert result.configured is False
    assert result.provider == "environment"
    assert result.missing_fields == ["LOGIN", "PASSWORD", "SERVER"]
    with pytest.raises(ValueError, match="missing fields"):
        resolve_secret_reference(
            "secret://environment/mt5-live-001",
            required_fields=("LOGIN", "PASSWORD", "SERVER"),
        )


def test_unknown_provider_and_invalid_reference_fail_closed() -> None:
    with pytest.raises(ValueError, match="Unknown secret provider"):
        inspect_credential_reference("secret://unknown-provider/account-001")
    with pytest.raises(ValueError, match="must start"):
        parse_secret_reference("environment/account-001")
    with pytest.raises(ValueError, match="invalid"):
        parse_secret_reference("secret://environment/../escape")


def test_windows_provider_uses_field_targets_and_never_returns_values_in_inspection() -> None:
    values = {
        "VariableGlobal/bybit-live-001/API_KEY": "windows-api-value",
        "VariableGlobal/bybit-live-001/SECRET": "windows-secret-value",
        "VariableGlobal/bybit-live-001/VERSION": "rotation-7",
    }
    provider = WindowsCredentialManagerProvider(reader=values.get, platform="win32")
    reset_secret_providers(
        {
            "environment": EnvironmentSecretProvider(),
            "windows-credential-manager": provider,
        }
    )
    try:
        inspection = inspect_credential_reference(
            "secret://windows-credential-manager/bybit-live-001"
        )
        assert inspection.provider == "windows-credential-manager"
        assert inspection.secret_name == "bybit-live-001"
        assert inspection.version == "rotation-7"
        assert inspection.env_prefix is None
        assert inspection.configured is True
        assert "windows-api-value" not in inspection.model_dump_json()
        assert "windows-secret-value" not in inspection.model_dump_json()

        resolved = resolve_secret_reference(
            "secret://windows-credential-manager/bybit-live-001"
        )
        assert resolved["API_KEY"] == "windows-api-value"
        assert resolved["SECRET"] == "windows-secret-value"
    finally:
        reset_secret_providers()


def test_windows_provider_fails_closed_outside_windows() -> None:
    provider = WindowsCredentialManagerProvider(platform="linux")
    reset_secret_providers(
        {
            "environment": EnvironmentSecretProvider(),
            "windows-credential-manager": provider,
        }
    )
    try:
        with pytest.raises(ValueError, match="requires Windows"):
            inspect_credential_reference(
                "secret://windows-credential-manager/bybit-live-001"
            )
    finally:
        reset_secret_providers()
