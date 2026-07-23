from app.redaction import REDACTED, redact_sensitive, redact_text


def test_recursive_redaction_hides_sensitive_fields_and_nested_values() -> None:
    payload = {
        "accountId": "account-live-1",
        "authorization": "Bearer runtime-token-value",
        "nested": {
            "apiSecret": "adapter-secret-value",
            "safe": "visible",
            "items": [
                {"password": "terminal-password-value"},
                "token=inline-token-value-1234567890",
            ],
        },
    }

    result = redact_sensitive(payload)

    assert result["accountId"] == "account-live-1"
    assert result["authorization"] == REDACTED
    assert result["nested"]["apiSecret"] == REDACTED
    assert result["nested"]["safe"] == "visible"
    assert result["nested"]["items"][0]["password"] == REDACTED
    assert "inline-token-value" not in result["nested"]["items"][1]


def test_text_redaction_hides_bearer_private_key_and_url_password() -> None:
    begin = "-----BEGIN " + "PRIVATE KEY-----"
    end = "-----END " + "PRIVATE KEY-----"
    text = (
        "Authorization: Bearer sample-runtime-token-12345 "
        "postgresql://operator:database-password@127.0.0.1:5432/vg "
        f"{begin}\nmaterial\n{end}"
    )

    result = redact_text(text)

    assert "sample-runtime-token" not in result
    assert "database-password" not in result
    assert "material" not in result
    assert result.count(REDACTED) >= 3


def test_exception_message_is_redacted() -> None:
    error = RuntimeError("api_secret=secret-material-1234567890")
    result = redact_sensitive(error)
    assert "secret-material" not in result
    assert REDACTED in result
