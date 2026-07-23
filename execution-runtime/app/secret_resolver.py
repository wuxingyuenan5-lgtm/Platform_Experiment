from __future__ import annotations

import os
import re

from app.models import CredentialInspection

REQUIRED_SECRET_FIELDS = ("API_KEY", "SECRET")
OPTIONAL_SECRET_FIELDS = ("PASSPHRASE",)
SECRET_REF_PREFIX = "secret://"


def inspect_credential_reference(credential_ref: str) -> CredentialInspection:
    env_prefix = env_prefix_for_secret_ref(credential_ref)
    available_fields = [
        field
        for field in (*REQUIRED_SECRET_FIELDS, *OPTIONAL_SECRET_FIELDS)
        if os.getenv(f"{env_prefix}_{field}")
    ]
    missing_fields = [
        field for field in REQUIRED_SECRET_FIELDS if field not in available_fields
    ]
    return CredentialInspection(
        credentialRef=credential_ref,
        envPrefix=env_prefix,
        configured=not missing_fields,
        availableFields=sorted(available_fields),
        missingFields=missing_fields,
    )


def resolve_secret_reference(credential_ref: str) -> dict[str, str]:
    env_prefix = env_prefix_for_secret_ref(credential_ref)
    values = {
        field: os.getenv(f"{env_prefix}_{field}")
        for field in (*REQUIRED_SECRET_FIELDS, *OPTIONAL_SECRET_FIELDS)
    }
    missing_fields = [
        field for field in REQUIRED_SECRET_FIELDS if not values.get(field)
    ]
    if missing_fields:
        raise ValueError(f"Credential reference is missing fields: {', '.join(missing_fields)}")
    return {field: value for field, value in values.items() if value}


def env_prefix_for_secret_ref(credential_ref: str) -> str:
    if not credential_ref.startswith(SECRET_REF_PREFIX):
        raise ValueError("Credential reference must start with secret://")
    secret_name = credential_ref.removeprefix(SECRET_REF_PREFIX).strip()
    if not secret_name:
        raise ValueError("Credential reference name is empty")
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", secret_name).strip("_").upper()
    return f"VG_SECRET_{normalized}"
