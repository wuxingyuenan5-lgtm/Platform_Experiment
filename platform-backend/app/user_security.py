from __future__ import annotations

import hashlib
import secrets
import unicodedata
from dataclasses import dataclass

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128
COMMON_PASSWORDS = frozenset(
    {
        "123456789012",
        "password1234",
        "qwerty123456",
        "admin123456",
        "letmein123456",
    }
)


class PasswordPolicyError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PasswordVerification:
    valid: bool
    needs_rehash: bool = False


_PASSWORD_HASHER = PasswordHasher(type=Type.ID)


def normalize_username(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    if not normalized:
        raise ValueError("Username is required")
    return normalized


def normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    return normalized or None


def normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = "".join(
        character for character in value if character.isdigit() or character == "+"
    )
    return normalized or None


def validate_password(
    password: str,
    *,
    username: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> None:
    if len(password) < PASSWORD_MIN_LENGTH or len(password) > PASSWORD_MAX_LENGTH:
        raise PasswordPolicyError(
            "Password length must be between "
            f"{PASSWORD_MIN_LENGTH} and {PASSWORD_MAX_LENGTH} characters"
        )
    normalized_password = unicodedata.normalize("NFKC", password).casefold()
    if normalized_password in COMMON_PASSWORDS:
        raise PasswordPolicyError("Password is too common")
    if username and normalized_password == normalize_username(username):
        raise PasswordPolicyError("Password must not match the username")
    normalized_email = normalize_email(email)
    if normalized_email and normalized_email in normalized_password:
        raise PasswordPolicyError("Password must not contain the full email address")
    normalized_phone = normalize_phone(phone)
    normalized_password_phone = normalize_phone(password) or ""
    if normalized_phone and normalized_phone in normalized_password_phone:
        raise PasswordPolicyError("Password must not contain the full phone number")


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password)


def verify_password(password_hash: str, password: str) -> PasswordVerification:
    try:
        valid = _PASSWORD_HASHER.verify(password_hash, password)
    except (InvalidHashError, VerificationError):
        return PasswordVerification(valid=False)
    return PasswordVerification(
        valid=bool(valid),
        needs_rehash=_PASSWORD_HASHER.check_needs_rehash(password_hash),
    )


def generate_secret_token(byte_length: int = 32) -> str:
    if byte_length < 32:
        raise ValueError("Secret tokens must contain at least 256 bits of entropy")
    return secrets.token_urlsafe(byte_length)


def hash_secret_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
