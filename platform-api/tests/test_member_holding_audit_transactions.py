from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.member_holding_service as holding_service
from app.config import get_settings
from app.database_bootstrap import bootstrap_database
from app.database_seeds import seed_reference_data
from app.main import app
from app.member_holding_schemas import UpsertMemberHoldingRequest
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_admin_service import AdminRequestContext
from app.user_rate_limit import get_public_auth_rate_limiter
from app.user_service import create_initial_ceo

ORIGIN = "https://testserver"
PASSWORD = "correct horse battery staple"


def prepare_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    path = tmp_path / "holding-audit-transaction.db"
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(path))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(settings, "auth_credentials_json", "[]")
    monkeypatch.setattr(settings, "cors_origins", ORIGIN)
    monkeypatch.setattr(settings, "public_login_rate_limit", 1000)
    get_public_auth_rate_limiter(settings.public_rate_limit_max_keys).clear()
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        bootstrap_database(db)
        apply_migrations(db, PLATFORM_MIGRATIONS)
        seed_reference_data(db)
        db.commit()
    return path


@pytest.mark.integration
def test_holding_write_rolls_back_when_audit_insert_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = prepare_database(monkeypatch, tmp_path)
    owner = create_initial_ceo(
        username="holding-audit-owner",
        password=PASSWORD,
        real_name="Holding Audit Owner",
        email="holding-audit-owner@example.test",
    )

    with TestClient(app, base_url=ORIGIN) as client:
        signed_in = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"username": "holding-audit-owner", "password": PASSWORD},
        )
        assert signed_in.status_code == 200
        csrf = signed_in.json()["csrfToken"]
        session_id = signed_in.json()["session"]["sessionId"]
        created = client.post(
            "/api/v1/users",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "username": "holding-audit-member",
                "realName": "Fictional Holding Member",
                "email": "holding-audit-member@example.test",
                "role": "member",
                "memberType": "individual",
            },
        )
        assert created.status_code == 201
        member_id = created.json()["user"]["userId"]

    context = AdminRequestContext(
        actor_user_id=owner.id,
        actor_role="ceo",
        session_id=session_id,
        request_id="holding-audit-failure",
        ip_address="127.0.0.1",
    )

    def fail_audit(*args, **kwargs) -> None:
        raise sqlite3.OperationalError("audit storage unavailable")

    monkeypatch.setattr(holding_service, "insert_audit_event", fail_audit)
    with pytest.raises(holding_service.MemberHoldingServiceError) as captured:
        holding_service.put_member_holding(
            member_user_id=member_id,
            fund_id="fund_default",
            request=UpsertMemberHoldingRequest(
                shareQuantity="10",
                cumulativeInvested="100",
                asOf=datetime.now(UTC),
                source="manual_admin",
                status="active",
            ),
            context=context,
        )
    assert captured.value.code == "holding_operation_failed"

    with sqlite3.connect(database_path) as db:
        row = db.execute(
            """
            SELECT id FROM member_fund_holdings
            WHERE member_user_id = ? AND fund_id = 'fund_default'
            """,
            (member_id,),
        ).fetchone()
    assert row is None
