from __future__ import annotations

import io
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import get_settings
from app.database_bootstrap import bootstrap_database
from app.main import app
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_service import create_initial_ceo

ORIGIN = "https://testserver"


def prepare(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = get_settings()
    database_path = tmp_path / "avatar.db"
    monkeypatch.setattr(settings, "database_path", str(database_path))
    monkeypatch.setattr(settings, "avatar_data_directory", str(tmp_path / "avatars"))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(settings, "auth_credentials_json", "[]")
    monkeypatch.setattr(settings, "cors_origins", ORIGIN)
    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        bootstrap_database(db)
        apply_migrations(db, PLATFORM_MIGRATIONS)
        db.commit()
    create_initial_ceo(
        username="owner",
        password="correct horse battery staple",
        email="owner@example.test",
    )


def png_bytes(width: int = 900, height: int = 600) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), (128, 140, 150)).save(output, format="PNG")
    return output.getvalue()


@pytest.mark.integration
def test_avatar_is_reencoded_served_and_deleted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare(monkeypatch, tmp_path)
    with TestClient(app, base_url=ORIGIN) as client:
        login = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"username": "owner", "password": "correct horse battery staple"},
        )
        assert login.status_code == 200
        csrf = login.json()["csrfToken"]
        version = login.json()["user"]["rowVersion"]

        uploaded = client.post(
            "/api/v1/me/avatar",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            data={"expectedVersion": str(version)},
            files={"file": ("avatar.png", png_bytes(), "image/png")},
        )
        assert uploaded.status_code == 200
        assert uploaded.json()["avatarKey"]
        assert uploaded.json()["rowVersion"] == version + 1

        served = client.get("/api/v1/me/avatar")
        assert served.status_code == 200
        assert served.headers["content-type"].startswith("image/webp")
        with Image.open(io.BytesIO(served.content)) as image:
            assert image.format == "WEBP"
            assert image.size == (512, 512)

        deleted = client.delete(
            f"/api/v1/me/avatar?expectedVersion={version + 1}",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        )
        assert deleted.status_code == 200
        assert deleted.json()["avatarKey"] is None
        assert client.get("/api/v1/me/avatar").status_code == 404


@pytest.mark.integration
def test_avatar_rejects_invalid_and_oversized_input(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare(monkeypatch, tmp_path)
    with TestClient(app, base_url=ORIGIN) as client:
        login = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"username": "owner", "password": "correct horse battery staple"},
        )
        csrf = login.json()["csrfToken"]
        version = login.json()["user"]["rowVersion"]

        invalid = client.post(
            "/api/v1/me/avatar",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            data={"expectedVersion": str(version)},
            files={"file": ("avatar.png", b"not-an-image", "image/png")},
        )
        assert invalid.status_code == 422
        assert invalid.json()["detail"]["code"] == "avatar_decode_failed"

        oversized = client.post(
            "/api/v1/me/avatar",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            data={"expectedVersion": str(version)},
            files={
                "file": (
                    "avatar.png",
                    b"x" * (get_settings().avatar_max_bytes + 1),
                    "image/png",
                )
            },
        )
        assert oversized.status_code == 413
