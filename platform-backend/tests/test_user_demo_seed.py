from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import get_settings
from app.database import connection, initialize_database
from app.member_holding_service import get_self_holdings
from app.schema_migrations import apply_platform_migrations
from app.user_demo_seed import seed_demo_users
from app.user_product_migrations import apply_user_product_migrations
from app.user_service import UserServiceError, login_user

_INITIAL_PASSWORD = "Demo-Accounts!2026"
_REFRESHED_PASSWORD = "Demo-Accounts!2027"
_NOW = datetime(2026, 7, 28, 8, 0, tzinfo=UTC)


def _prepare_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VG_DATABASE_PATH", str(tmp_path / "demo-users.db"))
    monkeypatch.setenv("VG_ENVIRONMENT", "testing")
    monkeypatch.setenv("VG_LIVE_TRADING_ENABLED", "false")
    get_settings.cache_clear()
    initialize_database()
    apply_platform_migrations()
    apply_user_product_migrations()


def _login(username: str, password: str):
    return login_user(
        username=username,
        password=password,
        request_id=f"login-{username}",
        ip_address="127.0.0.1",
        user_agent="pytest",
        now=_NOW,
    )


@pytest.mark.integration
def test_demo_seed_creates_reusable_role_accounts_and_vip_holdings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _prepare_database(monkeypatch, tmp_path)

    accounts = seed_demo_users(password=_INITIAL_PASSWORD, now=_NOW)
    assert len(accounts) == 8
    assert [account.role for account in accounts] == [
        "ceo",
        "tech_lead",
        "employee",
        "employee",
        "employee",
        "member",
        "member",
        "member",
    ]
    assert all(account.created for account in accounts)

    for account in accounts:
        signed_in = _login(account.username, _INITIAL_PASSWORD)
        assert signed_in.response.user.role == account.role

    vip_accounts = [account for account in accounts if account.role == "member"]
    expected_values = ["100000", "65000", "200000"]
    for account, expected_value in zip(vip_accounts, expected_values, strict=True):
        holdings = get_self_holdings(user_id=account.user_id, now=_NOW)
        assert len(holdings.items) == 1
        assert holdings.items[0].market_value == expected_value
        assert holdings.items[0].nav_status == "available"

    with connection() as db:
        rows = db.execute(
            "SELECT username, admin_note FROM users ORDER BY username_normalized"
        ).fetchall()
    assert len(rows) == 8
    assert all(str(row["admin_note"]).startswith("可复用演示账号：") for row in rows)


@pytest.mark.integration
def test_demo_seed_refreshes_credentials_only_when_explicitly_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _prepare_database(monkeypatch, tmp_path)
    original = seed_demo_users(password=_INITIAL_PASSWORD, now=_NOW)

    kept = seed_demo_users(
        password=_REFRESHED_PASSWORD,
        prefix="pilot",
        refresh_existing=False,
        now=_NOW,
    )
    assert [account.username for account in kept] == [account.username for account in original]
    assert all(not account.created and not account.refreshed for account in kept)
    assert _login("demo_ceo", _INITIAL_PASSWORD).response.user.role == "ceo"

    refreshed = seed_demo_users(
        password=_REFRESHED_PASSWORD,
        prefix="pilot",
        refresh_existing=True,
        now=_NOW,
    )
    assert all(account.refreshed for account in refreshed)
    assert refreshed[0].username == "pilot_ceo"
    assert _login("pilot_ceo", _REFRESHED_PASSWORD).response.user.role == "ceo"
    with pytest.raises(UserServiceError) as exc_info:
        _login("pilot_ceo", _INITIAL_PASSWORD)
    assert exc_info.value.code == "invalid_credentials"
