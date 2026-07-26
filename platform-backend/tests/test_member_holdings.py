from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database_bootstrap import bootstrap_database
from app.database_seeds import seed_reference_data
from app.main import app
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_rate_limit import get_public_auth_rate_limiter
from app.user_service import create_initial_ceo

ORIGIN = "https://testserver"
OWNER_PASSWORD = "correct horse battery staple"
MEMBER_PASSWORD = "member correct horse battery staple"


def prepare_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    name: str,
) -> Path:
    path = tmp_path / name
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(path))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(settings, "auth_credentials_json", "[]")
    monkeypatch.setattr(settings, "cors_origins", ORIGIN)
    monkeypatch.setattr(settings, "fund_nav_stale_after_hours", 36)
    monkeypatch.setattr(settings, "public_login_rate_limit", 1000)
    monkeypatch.setattr(settings, "public_password_reset_rate_limit", 1000)
    get_public_auth_rate_limiter(settings.public_rate_limit_max_keys).clear()
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        bootstrap_database(db)
        apply_migrations(db, PLATFORM_MIGRATIONS)
        seed_reference_data(db)
        db.commit()
    return path


def login(client: TestClient, username: str, password: str):
    return client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"username": username, "password": password},
    )


def create_member(owner_client: TestClient, csrf: str, username: str) -> tuple[str, str]:
    created = owner_client.post(
        "/api/v1/users",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json={
            "username": username,
            "realName": "虚构会员",
            "email": f"{username}@example.test",
            "role": "member",
            "memberType": "individual",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    return payload["user"]["userId"], payload["resetTicket"]


def activate_member(client: TestClient, username: str, ticket: str) -> None:
    reset = client.post(
        "/api/v1/auth/reset-password",
        headers={"Origin": ORIGIN},
        json={
            "username": username,
            "resetTicket": ticket,
            "newPassword": MEMBER_PASSWORD,
            "newPasswordConfirmation": MEMBER_PASSWORD,
        },
    )
    assert reset.status_code == 200


def put_holding(
    owner_client: TestClient,
    csrf: str,
    member_id: str,
    fund_id: str,
    *,
    shares: str,
    invested: str,
    expected_version: int | None = None,
):
    now = datetime.now(UTC)
    body: dict[str, object] = {
        "shareQuantity": shares,
        "cumulativeInvested": invested,
        "confirmedAt": (now - timedelta(days=2)).isoformat(),
        "asOf": now.isoformat(),
        "source": "manual_admin",
        "status": "active",
    }
    if expected_version is not None:
        body["expectedVersion"] = expected_version
    return owner_client.put(
        f"/api/v1/users/{member_id}/holdings/{fund_id}",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json=body,
    )


@pytest.mark.integration
def test_member_reads_exact_self_holding_without_identity_parameter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = prepare_database(monkeypatch, tmp_path, "member-holdings.db")
    create_initial_ceo(
        username="holding-owner",
        password=OWNER_PASSWORD,
        real_name="Holding Owner",
        email="holding-owner@example.test",
    )

    with TestClient(app, base_url=ORIGIN) as owner_client:
        owner_login = login(owner_client, "holding-owner", OWNER_PASSWORD)
        assert owner_login.status_code == 200
        csrf = owner_login.json()["csrfToken"]
        member_id, ticket = create_member(owner_client, csrf, "holding-member")

        nav = owner_client.put(
            "/api/v1/users/holdings/funds/fund_default/nav",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "unitNav": "0.2",
                "valuationTime": datetime.now(UTC).isoformat(),
                "currency": "USDT",
                "source": "manual_admin",
                "fundCode": "VG-DEMO-001",
            },
        )
        assert nav.status_code == 200
        assert nav.json()["fund"]["fundCode"] == "VG-DEMO-001"

        holding = put_holding(
            owner_client,
            csrf,
            member_id,
            "fund_default",
            shares="0.1",
            invested="0.01",
        )
        assert holding.status_code == 200
        assert holding.json()["marketValue"] == "0.02"
        assert holding.json()["cumulativeReturn"] == "0.01"
        assert holding.json()["returnRate"] == "1"

    with TestClient(app, base_url=ORIGIN) as member_client:
        activate_member(member_client, "holding-member", ticket)
        signed_in = login(member_client, "holding-member", MEMBER_PASSWORD)
        assert signed_in.status_code == 200
        response = member_client.get("/api/v1/me/holdings")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["memberUserId"] == member_id
        assert items[0]["fundCode"] == "VG-DEMO-001"
        assert items[0]["shareQuantity"] == "0.1"
        assert items[0]["latestUnitNav"] == "0.2"
        assert items[0]["marketValue"] == "0.02"
        assert items[0]["navStatus"] == "available"

        ignored_identity = member_client.get(
            "/api/v1/me/holdings",
            params={"user_id": "another-user"},
        )
        assert ignored_identity.status_code == 200
        assert ignored_identity.json()["items"][0]["memberUserId"] == member_id

    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        events = {
            str(row["event_type"])
            for row in db.execute(
                "SELECT event_type FROM audit_events WHERE subject_id = ?",
                (member_id,),
            ).fetchall()
        }
    assert "member.holding_updated" in events


@pytest.mark.integration
def test_unavailable_and_stale_nav_are_explicit_not_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = prepare_database(monkeypatch, tmp_path, "holding-nav-state.db")
    create_initial_ceo(
        username="nav-owner",
        password=OWNER_PASSWORD,
        real_name="NAV Owner",
        email="nav-owner@example.test",
    )
    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        db.execute(
            """
            INSERT INTO funds (
                id, legal_entity_id, name, base_currency, fund_code, created_at
            ) VALUES (
                'fund_without_nav', 'le_default', 'Fund Without NAV', 'USDT',
                'VG-DEMO-002', '2026-07-01T00:00:00+00:00'
            )
            """
        )
        db.execute(
            """
            INSERT INTO funds (
                id, legal_entity_id, name, base_currency, fund_code, created_at
            ) VALUES (
                'fund_stale_nav', 'le_default', 'Fund Stale NAV', 'USDT',
                'VG-DEMO-003', '2026-07-01T00:00:00+00:00'
            )
            """
        )
        db.commit()

    with TestClient(app, base_url=ORIGIN) as owner_client:
        owner_login = login(owner_client, "nav-owner", OWNER_PASSWORD)
        csrf = owner_login.json()["csrfToken"]
        member_id, ticket = create_member(owner_client, csrf, "nav-member")

        missing = put_holding(
            owner_client,
            csrf,
            member_id,
            "fund_without_nav",
            shares="10",
            invested="100",
        )
        assert missing.status_code == 200
        assert missing.json()["navStatus"] == "unavailable"
        assert missing.json()["latestUnitNav"] is None
        assert missing.json()["marketValue"] is None
        assert missing.json()["cumulativeReturn"] is None
        assert missing.json()["returnRate"] is None

        stale_nav = owner_client.put(
            "/api/v1/users/holdings/funds/fund_stale_nav/nav",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "unitNav": "1.25",
                "valuationTime": (datetime.now(UTC) - timedelta(hours=48)).isoformat(),
                "currency": "USDT",
                "source": "manual_admin",
            },
        )
        assert stale_nav.status_code == 200
        stale = put_holding(
            owner_client,
            csrf,
            member_id,
            "fund_stale_nav",
            shares="10",
            invested="0",
        )
        assert stale.status_code == 200
        assert stale.json()["navStatus"] == "stale"
        assert stale.json()["marketValue"] == "12.5"
        assert stale.json()["cumulativeReturn"] == "12.5"
        assert stale.json()["returnRate"] is None

    with TestClient(app, base_url=ORIGIN) as member_client:
        activate_member(member_client, "nav-member", ticket)
        assert login(member_client, "nav-member", MEMBER_PASSWORD).status_code == 200
        response = member_client.get("/api/v1/me/holdings")
        assert response.status_code == 200
        by_fund = {item["fundId"]: item for item in response.json()["items"]}
        assert by_fund["fund_without_nav"]["navStatus"] == "unavailable"
        assert by_fund["fund_stale_nav"]["navStatus"] == "stale"


@pytest.mark.integration
def test_holding_update_uses_optimistic_version_and_plain_decimal_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare_database(monkeypatch, tmp_path, "holding-version.db")
    create_initial_ceo(
        username="version-owner",
        password=OWNER_PASSWORD,
        real_name="Version Owner",
        email="version-owner@example.test",
    )

    with TestClient(app, base_url=ORIGIN) as owner_client:
        owner_login = login(owner_client, "version-owner", OWNER_PASSWORD)
        csrf = owner_login.json()["csrfToken"]
        member_id, _ = create_member(owner_client, csrf, "version-member")

        invalid = put_holding(
            owner_client,
            csrf,
            member_id,
            "fund_default",
            shares="1e-3",
            invested="10",
        )
        assert invalid.status_code == 422
        assert invalid.json()["detail"]["code"] == "decimal_invalid"

        created = put_holding(
            owner_client,
            csrf,
            member_id,
            "fund_default",
            shares="2",
            invested="10",
        )
        assert created.status_code == 200
        version = created.json()["rowVersion"]

        updated = put_holding(
            owner_client,
            csrf,
            member_id,
            "fund_default",
            shares="3",
            invested="10",
            expected_version=version,
        )
        assert updated.status_code == 200
        assert updated.json()["rowVersion"] == version + 1

        stale = put_holding(
            owner_client,
            csrf,
            member_id,
            "fund_default",
            shares="4",
            invested="10",
            expected_version=version,
        )
        assert stale.status_code == 409
        assert stale.json()["detail"]["code"] == "row_version_conflict"

        wrong_currency = owner_client.put(
            "/api/v1/users/holdings/funds/fund_default/nav",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "unitNav": "1",
                "valuationTime": datetime.now(UTC).isoformat(),
                "currency": "CNY",
                "source": "manual_admin",
            },
        )
        assert wrong_currency.status_code == 422
        assert wrong_currency.json()["detail"]["code"] == "fund_nav_currency_mismatch"
