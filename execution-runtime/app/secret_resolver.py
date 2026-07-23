from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol

from app.models import CredentialInspection

DEFAULT_REQUIRED_SECRET_FIELDS = ("API_KEY", "SECRET")
OPTIONAL_SECRET_FIELDS = ("PASSPHRASE", "LOGIN", "PASSWORD", "SERVER")
SECRET_REF_PREFIX = "secret://"
ENVIRONMENT_PROVIDER = "environment"
WINDOWS_PROVIDER = "windows-credential-manager"


@dataclass(frozen=True)
class ParsedSecretReference:
    original_ref: str
    provider: str
    secret_name: str
    legacy_reference: bool


class SecretProvider(Protocol):
    name: str

    def inspect(
        self,
        reference: ParsedSecretReference,
        required_fields: tuple[str, ...],
        known_fields: tuple[str, ...],
    ) -> CredentialInspection: ...

    def resolve(
        self,
        reference: ParsedSecretReference,
        required_fields: tuple[str, ...],
        known_fields: tuple[str, ...],
    ) -> dict[str, str]: ...


class EnvironmentSecretProvider:
    name = ENVIRONMENT_PROVIDER

    def inspect(
        self,
        reference: ParsedSecretReference,
        required_fields: tuple[str, ...],
        known_fields: tuple[str, ...],
    ) -> CredentialInspection:
        env_prefix = env_prefix_for_secret_name(reference.secret_name)
        available_fields = [
            field for field in known_fields if os.getenv(f"{env_prefix}_{field}")
        ]
        missing_fields = [field for field in required_fields if field not in available_fields]
        version = os.getenv(f"{env_prefix}_VERSION", "unversioned")
        return CredentialInspection(
            credentialRef=reference.original_ref,
            provider=self.name,
            secretName=reference.secret_name,
            version=version,
            envPrefix=env_prefix,
            configured=not missing_fields,
            availableFields=sorted(available_fields),
            missingFields=missing_fields,
            legacyReference=reference.legacy_reference,
        )

    def resolve(
        self,
        reference: ParsedSecretReference,
        required_fields: tuple[str, ...],
        known_fields: tuple[str, ...],
    ) -> dict[str, str]:
        env_prefix = env_prefix_for_secret_name(reference.secret_name)
        values = {field: os.getenv(f"{env_prefix}_{field}") for field in known_fields}
        missing_fields = [field for field in required_fields if not values.get(field)]
        if missing_fields:
            raise ValueError(
                f"Credential reference is missing fields: {', '.join(missing_fields)}"
            )
        return {field: value for field, value in values.items() if value}


class WindowsCredentialManagerProvider:
    name = WINDOWS_PROVIDER

    def __init__(
        self,
        reader: Callable[[str], str | None] | None = None,
        platform: str | None = None,
    ) -> None:
        self._reader = reader
        self._platform = platform or sys.platform

    def inspect(
        self,
        reference: ParsedSecretReference,
        required_fields: tuple[str, ...],
        known_fields: tuple[str, ...],
    ) -> CredentialInspection:
        reader = self._credential_reader()
        values = {field: reader(self._target(reference.secret_name, field)) for field in known_fields}
        available_fields = [field for field, value in values.items() if value]
        missing_fields = [field for field in required_fields if field not in available_fields]
        version = reader(self._target(reference.secret_name, "VERSION")) or "unversioned"
        return CredentialInspection(
            credentialRef=reference.original_ref,
            provider=self.name,
            secretName=reference.secret_name,
            version=version,
            envPrefix=None,
            configured=not missing_fields,
            availableFields=sorted(available_fields),
            missingFields=missing_fields,
            legacyReference=reference.legacy_reference,
        )

    def resolve(
        self,
        reference: ParsedSecretReference,
        required_fields: tuple[str, ...],
        known_fields: tuple[str, ...],
    ) -> dict[str, str]:
        reader = self._credential_reader()
        values = {field: reader(self._target(reference.secret_name, field)) for field in known_fields}
        missing_fields = [field for field in required_fields if not values.get(field)]
        if missing_fields:
            raise ValueError(
                f"Credential reference is missing fields: {', '.join(missing_fields)}"
            )
        return {field: value for field, value in values.items() if value}

    def _credential_reader(self) -> Callable[[str], str | None]:
        if self._reader is not None:
            return self._reader
        if self._platform != "win32":
            raise ValueError("Windows Credential Manager provider requires Windows")
        try:
            import win32cred  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValueError(
                "Windows Credential Manager provider requires the optional pywin32 dependency"
            ) from exc

        def read(target: str) -> str | None:
            try:
                credential = win32cred.CredRead(target, win32cred.CRED_TYPE_GENERIC, 0)
            except Exception:
                return None
            blob = credential.get("CredentialBlob")
            if blob is None:
                return None
            if isinstance(blob, bytes):
                return blob.decode("utf-16-le").rstrip("\x00")
            return str(blob)

        return read

    @staticmethod
    def _target(secret_name: str, field: str) -> str:
        return f"VariableGlobal/{secret_name}/{field}"


_PROVIDER_REGISTRY: dict[str, SecretProvider] = {
    ENVIRONMENT_PROVIDER: EnvironmentSecretProvider(),
    WINDOWS_PROVIDER: WindowsCredentialManagerProvider(),
}


def register_secret_provider(provider: SecretProvider) -> None:
    if not provider.name or "/" in provider.name:
        raise ValueError("Secret provider name is invalid")
    _PROVIDER_REGISTRY[provider.name] = provider


def reset_secret_providers(providers: Mapping[str, SecretProvider] | None = None) -> None:
    _PROVIDER_REGISTRY.clear()
    if providers is None:
        _PROVIDER_REGISTRY.update(
            {
                ENVIRONMENT_PROVIDER: EnvironmentSecretProvider(),
                WINDOWS_PROVIDER: WindowsCredentialManagerProvider(),
            }
        )
    else:
        _PROVIDER_REGISTRY.update(providers)


def inspect_credential_reference(
    credential_ref: str,
    required_fields: Iterable[str] = DEFAULT_REQUIRED_SECRET_FIELDS,
) -> CredentialInspection:
    required, known = normalized_fields(required_fields)
    reference = parse_secret_reference(credential_ref)
    return provider_for(reference.provider).inspect(reference, required, known)


def resolve_secret_reference(
    credential_ref: str,
    required_fields: Iterable[str] = DEFAULT_REQUIRED_SECRET_FIELDS,
) -> dict[str, str]:
    required, known = normalized_fields(required_fields)
    reference = parse_secret_reference(credential_ref)
    return provider_for(reference.provider).resolve(reference, required, known)


def parse_secret_reference(credential_ref: str) -> ParsedSecretReference:
    if not credential_ref.startswith(SECRET_REF_PREFIX):
        raise ValueError("Credential reference must start with secret://")
    body = credential_ref.removeprefix(SECRET_REF_PREFIX).strip("/")
    if not body:
        raise ValueError("Credential reference is empty")
    provider, separator, secret_name = body.partition("/")
    if not separator:
        # Migration compatibility for the existing V6 references. New production
        # references must use secret://environment/<name> or another explicit provider.
        provider = ENVIRONMENT_PROVIDER
        secret_name = body
        legacy_reference = True
    else:
        legacy_reference = False
    if not provider or not secret_name or ".." in secret_name.split("/"):
        raise ValueError("Credential reference provider or secret name is invalid")
    return ParsedSecretReference(
        original_ref=credential_ref,
        provider=provider.lower(),
        secret_name=secret_name,
        legacy_reference=legacy_reference,
    )


def provider_for(provider_name: str) -> SecretProvider:
    provider = _PROVIDER_REGISTRY.get(provider_name)
    if provider is None:
        raise ValueError(f"Unknown secret provider: {provider_name}")
    return provider


def normalized_fields(required_fields: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    required = tuple(dict.fromkeys(str(field).strip().upper() for field in required_fields))
    if not required or any(not field for field in required):
        raise ValueError("Required secret fields are invalid")
    known = tuple(dict.fromkeys((*required, *OPTIONAL_SECRET_FIELDS)))
    return required, known


def env_prefix_for_secret_ref(credential_ref: str) -> str:
    reference = parse_secret_reference(credential_ref)
    if reference.provider != ENVIRONMENT_PROVIDER:
        raise ValueError("Credential reference does not use the environment provider")
    return env_prefix_for_secret_name(reference.secret_name)


def env_prefix_for_secret_name(secret_name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", secret_name).strip("_").upper()
    if not normalized:
        raise ValueError("Credential reference name is empty")
    return f"VG_SECRET_{normalized}"
