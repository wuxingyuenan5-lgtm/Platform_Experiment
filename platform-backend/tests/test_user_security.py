from __future__ import annotations

import pytest

from app.user_security import (
    PasswordPolicyError,
    generate_secret_token,
    hash_password,
    hash_secret_token,
    validate_password,
    verify_password,
)


@pytest.mark.unit
def test_argon2id_password_round_trip() -> None:
    encoded = hash_password("correct horse battery staple")
    assert encoded.startswith("$argon2id$")
    assert verify_password(encoded, "correct horse battery staple").valid
    assert not verify_password(encoded, "wrong password").valid


@pytest.mark.unit
def test_password_policy_rejects_weak_or_identity_derived_values() -> None:
    with pytest.raises(PasswordPolicyError):
        validate_password("short")
    with pytest.raises(PasswordPolicyError):
        validate_password("password1234")
    with pytest.raises(PasswordPolicyError):
        validate_password(
            "example@example.com-strong",
            email="example@example.com",
        )
    with pytest.raises(PasswordPolicyError):
        validate_password(
            "secure-prefix-8613800138000",
            phone="+86 138 0013 8000",
        )


@pytest.mark.unit
def test_secret_tokens_have_entropy_and_stable_hashes() -> None:
    first = generate_secret_token()
    second = generate_secret_token()
    assert first != second
    assert len(hash_secret_token(first)) == 64
    with pytest.raises(ValueError):
        generate_secret_token(16)
