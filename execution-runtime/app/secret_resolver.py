from __future__ import annotations

import os
import re
from collections.abc import Iterable

from app.models import CredentialInspection

DEFAULT_REQUIRED_SECRET_FIELDS = ("API_KEY", "SECRET")
OPTIONAL_SECRET_FIELDS = ("PASSPHRASE", "LOGIN", "PASSWORD", "SERVER")
SECRET_REF_PREFIX = "secret://"


def inspect_credential_reference(
    credential_ref: str,
    required_fields: Iterable[str] = DEFAULT_REQUIRED_SECRET_FIELDS,
) -> CredentialInspection:
    required = tuple(required_fields)
    env_prefix = env_prefix_for_secret_ref(credential_ref)
    known_fields = tuple(dict.fromkeys((*required, *OPTIONAL_SECRET_FIELDS)))
    available_fields = [
        field for field in known_fields if os.getenv(f"{env_prefix}_{field}")
    ]
    missing_fields = [field for field in required if field not in available_fields]
    return CredentialInspection(
        credentialRef=credential_ref,
        envPrefix=env_prefix,
        configured=not missing_fields,
        availableFields=sorted(available_fields),
        missingFields=missing_fields,
    )


def resolve_secret_reference(
    credential_ref: str,
    required_fields: Iterable[str] = DEFAULT_REQUIRED_SECRET_FIELDS,
) -> dict[str, str]:
    required = tuple(required_fields)
    env_prefix = env_prefix_for_secret_ref(credential_ref)
    known_fields = tuple(dict.fromkeys((*required, *OPTIONAL_SECRET_FIELDS)))
    values = {field: os.getenv(f"{env_prefix}_{field}") for field in known_fields}
    missing_fields = [field for field in required if not values.get(field)]
    if missing_fields:
        raise ValueError(
            f"Credential reference is missing fields: {', '.join(missing_fields)}"
        )
    return {field: value for field, value in values.items() if value}


def env_prefix_for_secret_ref(credential_ref: str) -> str:
    if not credential_ref.startswith(SECRET_REF_PREFIX):
        raise ValueError("Credential reference must start with secret://")
    secret_name = credential_ref.removeprefix(SECRET_REF_PREFIX).strip()
    if not secret_name:
        raise ValueError("Credential reference name is empty")
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", secret_name).strip("_").upper()
    return f"VG_SECRET_{normalized}"
