from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit, urlunsplit

REDACTED = "[REDACTED]"
SENSITIVE_KEY_PARTS = {
    "authorization",
    "token",
    "api_key",
    "apikey",
    "api_secret",
    "apisecret",
    "secret",
    "password",
    "passphrase",
    "private_key",
    "privatekey",
    "credential_value",
    "credentialvalue",
}
BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?"
    r"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    re.DOTALL,
)
ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|api[_-]?secret|token|secret|password|passphrase)"
    r"\s*([:=])\s*([^\s,;]+)"
)


def is_sensitive_key(key: object) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")
    return normalized in SENSITIVE_KEY_PARTS or any(
        normalized.endswith(f"_{part}") for part in SENSITIVE_KEY_PARTS
    )


def redact_text(value: str) -> str:
    result = PRIVATE_KEY_PATTERN.sub(REDACTED, value)
    result = BEARER_PATTERN.sub(f"Bearer {REDACTED}", result)
    result = ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{REDACTED}",
        result,
    )
    return redact_url_passwords(result)


def redact_url_passwords(value: str) -> str:
    output: list[str] = []
    for token in value.split():
        candidate = token.strip("'\"(),[]{}")
        if "://" not in candidate:
            output.append(token)
            continue
        try:
            parts = urlsplit(candidate)
        except ValueError:
            output.append(token)
            continue
        if parts.password is None or parts.hostname is None:
            output.append(token)
            continue
        username = parts.username or ""
        host = parts.hostname
        if parts.port is not None:
            host = f"{host}:{parts.port}"
        netloc = f"{username}:{REDACTED}@{host}" if username else f":{REDACTED}@{host}"
        safe = urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
        output.append(token.replace(candidate, safe))
    return " ".join(output)


def redact_sensitive(value: Any, *, parent_key: object | None = None) -> Any:
    if parent_key is not None and is_sensitive_key(parent_key):
        return REDACTED
    if isinstance(value, Mapping):
        return {
            key: (REDACTED if is_sensitive_key(key) else redact_sensitive(item, parent_key=key))
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, set):
        return {redact_sensitive(item) for item in value}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, BaseException):
        return redact_text(str(value))
    if isinstance(value, str):
        return redact_text(value)
    return value
