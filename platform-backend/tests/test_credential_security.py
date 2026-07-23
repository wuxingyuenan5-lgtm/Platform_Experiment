import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app
from app.redaction import REDACTED, redact_sensitive, redact_text


def credential(user_id: str, token: str, roles: list[str]) -> dict[str, object]:
    return {
        "credentialId": f"credential-{user_id}",
        "userId": user_id,
        "tokenSha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        "roles": roles,
        "status": "active",
    }


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def configure_live(monkeypatch, tmp_path: Path) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "credential-security.db"))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(
        settings,
        "auth_credentials_json",
        json.dumps(
            [
                credential("viewer-1", "viewer-token", ["viewer"]),
                credential("risk-1", "risk-token", ["risk_officer"]),
                credential("admin-1", "admin-token", ["admin"]),
            ]
        ),
    )


def rotation_payload() -> dict[str, str]:
    return {
        "idempotencyKey": "rotate-bybit-20260723-01",
        "credentialRef": "secret://windows-credential-manager/bybit-live-001",
        "provider": "windows-credential-manager",
        "version": "2026-07-23.1",
        "rotatedAt": "2026-07-23T16:00:00+00:00",
        "reason": "scheduled credential rotation",
    }


def test_rotation_records_metadata_only_and_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    configure_live(monkeypatch, tmp_path)
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/security/credential-rotations",
            headers=headers("admin-token"),
            json=rotation_payload(),
        )
        assert created.status_code == 200
        body = created.json()
        assert body["rotatedBy"] == "admin-1"
        assert body["version"] == "2026-07-23.1"
        serialized = json.dumps(body)
        assert "apiKey" not in serialized
        assert "password" not in serialized.lower()

        replay = client.post(
            "/api/v1/security/credential-rotations",
            headers=headers("admin-token"),
            json=rotation_payload(),
        )
        assert replay.status_code == 200
        assert replay.json()["rotationId"] == body["rotationId"]

        conflict = client.post(
            "/api/v1/security/credential-rotations",
            headers=headers("admin-token"),
            json={**rotation_payload(), "reason": "different payload"},
        )
        assert conflict.status_code == 409

        listed = client.get(
            "/api/v1/security/credential-rotations",
            headers=headers("risk-token"),
        )
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        viewer = client.get(
            "/api/v1/security/credential-rotations",
            headers=headers("viewer-token"),
        )
        assert viewer.status_code == 403

        with connection() as db:
            row = db.execute("SELECT * FROM credential_rotation_records").fetchone()
            assert set(row.keys()) == {
                "id",
                "idempotency_key",
                "payload_hash",
                "credential_ref",
                "provider",
                "version",
                "rotated_at",
                "rotated_by",
                "reason",
                "created_at",
            }
            audit = db.execute(
                "SELECT details_json FROM audit_events WHERE event_type = 'credential_rotation_recorded'"
            ).fetchone()
        assert audit is not None
        assert "admin-1" in audit["details_json"]


def test_rotation_rejects_provider_mismatch_and_non_admin_write(monkeypatch, tmp_path: Path) -> None:
    configure_live(monkeypatch, tmp_path)
    with TestClient(app) as client:
        mismatch = client.post(
            "/api/v1/security/credential-rotations",
            headers=headers("admin-token"),
            json={**rotation_payload(), "provider": "environment"},
        )
        assert mismatch.status_code == 422

        risk_write = client.post(
            "/api/v1/security/credential-rotations",
            headers=headers("risk-token"),
            json=rotation_payload(),
        )
        assert risk_write.status_code == 403


def test_backend_redactor_hides_nested_bearer_url_and_exception_values() -> None:
    result = redact_sensitive(
        {
            "safe": "visible",
            "authorization": "Bearer backend-token-value",
            "nested": {
                "apiSecret": "backend-secret-value",
                "error": RuntimeError("password=terminal-password-value-123456789"),
            },
        }
    )
    assert result["safe"] == "visible"
    assert result["authorization"] == REDACTED
    assert result["nested"]["apiSecret"] == REDACTED
    assert "terminal-password" not in result["nested"]["error"]

    message = redact_text(
        "Bearer bearer-value-123 postgresql://operator:database-password@localhost/vg"
    )
    assert "bearer-value" not in message
    assert "database-password" not in message
