from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Barrier, Lock, Thread

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database_bootstrap import bootstrap_database
from app.main import app
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_admin_schemas import ChangeUserStatusRequest
from app.user_admin_service import (
    AdminRequestContext,
    UserAdminServiceError,
    change_user_status,
    get_user_detail,
)
from app.user_service import create_initial_ceo

ORIGIN = "https://testserver"
OWNER_PASSWORD = "correct horse battery staple"
SECOND_PASSWORD = "second correct horse battery staple"


def prepare_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    path = tmp_path / "last-ceo-concurrency.db"
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(path))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(settings, "auth_credentials_json", "[]")
    monkeypatch.setattr(settings, "cors_origins", ORIGIN)
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        bootstrap_database(db)
        apply_migrations(db, PLATFORM_MIGRATIONS)
        db.commit()
    return path


def login(client: TestClient, username: str, password: str):
    return client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"username": username, "password": password},
    )


@pytest.mark.integration
def test_concurrent_ceo_disables_cannot_remove_all_active_ceos(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = prepare_database(monkeypatch, tmp_path)
    first = create_initial_ceo(
        username="ceo-one",
        password=OWNER_PASSWORD,
        real_name="CEO One",
        email="ceo-one@example.test",
    )

    with TestClient(app, base_url=ORIGIN) as first_client:
        first_login = login(first_client, "ceo-one", OWNER_PASSWORD)
        first_auth = first_login.json()
        created = first_client.post(
            "/api/v1/users",
            headers={
                "Origin": ORIGIN,
                "X-CSRF-Token": first_auth["csrfToken"],
            },
            json={
                "username": "ceo-two",
                "realName": "CEO Two",
                "email": "ceo-two@example.test",
                "role": "ceo",
            },
        )
        assert created.status_code == 201
        second_user = created.json()["user"]
        reset_ticket = created.json()["resetTicket"]

    with TestClient(app, base_url=ORIGIN) as reset_client:
        reset = reset_client.post(
            "/api/v1/auth/reset-password",
            headers={"Origin": ORIGIN},
            json={
                "username": "ceo-two",
                "resetTicket": reset_ticket,
                "newPassword": SECOND_PASSWORD,
                "newPasswordConfirmation": SECOND_PASSWORD,
            },
        )
        assert reset.status_code == 200

    with TestClient(app, base_url=ORIGIN) as first_client, TestClient(
        app, base_url=ORIGIN
    ) as second_client:
        first_auth = login(first_client, "ceo-one", OWNER_PASSWORD).json()
        second_auth = login(second_client, "ceo-two", SECOND_PASSWORD).json()

        first_context = AdminRequestContext(
            actor_user_id=first.id,
            actor_role="ceo",
            session_id=first_auth["session"]["sessionId"],
            request_id="disable-second",
            ip_address="127.0.0.1",
        )
        second_context = AdminRequestContext(
            actor_user_id=second_user["userId"],
            actor_role="ceo",
            session_id=second_auth["session"]["sessionId"],
            request_id="disable-first",
            ip_address="127.0.0.1",
        )
        first_version = get_user_detail(user_id=first.id, sensitive=True).row_version
        second_version = get_user_detail(
            user_id=second_user["userId"], sensitive=True
        ).row_version

        barrier = Barrier(2)
        result_lock = Lock()
        outcomes: list[str] = []

        def disable_target(
            target_user_id: str,
            expected_version: int,
            context: AdminRequestContext,
        ) -> None:
            barrier.wait()
            try:
                change_user_status(
                    target_user_id,
                    ChangeUserStatusRequest(
                        status="disabled",
                        reason="concurrency test",
                        expectedVersion=expected_version,
                    ),
                    context=context,
                )
            except UserAdminServiceError as exc:
                outcome = f"error:{exc.code}"
            else:
                outcome = "success"
            with result_lock:
                outcomes.append(outcome)

        threads = [
            Thread(
                target=disable_target,
                args=(second_user["userId"], second_version, first_context),
            ),
            Thread(
                target=disable_target,
                args=(first.id, first_version, second_context),
            ),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            assert not thread.is_alive()

    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            """
            SELECT COUNT(*) AS count FROM users
            WHERE role_code = 'ceo' AND lifecycle_status = 'active'
            """
        ).fetchone()
    assert outcomes.count("success") == 1
    assert int(row["count"]) == 1
