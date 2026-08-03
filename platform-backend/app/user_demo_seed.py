from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid5

from app.database import connection
from app.member_holding_repository import (
    get_latest_available_nav,
    get_member_holding,
    insert_fund_nav,
    update_fund_code,
    upsert_member_holding,
)
from app.user_repository import insert_audit_event, revoke_all_user_sessions
from app.user_security import (
    hash_password,
    normalize_email,
    normalize_username,
    validate_password,
)

_DEMO_NAMESPACE = UUID("7264d6b8-b487-4f77-929f-b9e49ed91b91")
_DEMO_FUND_ID = "fund_default"
_DEMO_NAV = "100"


@dataclass(frozen=True, slots=True)
class DemoAccountSpec:
    slot: str
    username_suffix: str
    display_name: str
    role: str
    department: str | None = None
    member_type: str | None = None
    share_quantity: str | None = None
    cumulative_invested: str | None = None


@dataclass(frozen=True, slots=True)
class SeededDemoAccount:
    slot: str
    user_id: str
    username: str
    role: str
    created: bool
    refreshed: bool


_DEMO_ACCOUNTS: tuple[DemoAccountSpec, ...] = (
    DemoAccountSpec("ceo", "ceo", "演示 CEO", "ceo"),
    DemoAccountSpec("tech_lead", "tech", "演示技术负责人", "tech_lead"),
    DemoAccountSpec("employee_1", "employee_1", "演示员工一", "employee", "运营中心"),
    DemoAccountSpec("employee_2", "employee_2", "演示员工二", "employee", "行研中心"),
    DemoAccountSpec("employee_3", "employee_3", "演示员工三", "employee", "量化中心"),
    DemoAccountSpec(
        "vip_1",
        "vip_1",
        "演示 VIP 一",
        "member",
        member_type="vip",
        share_quantity="1000",
        cumulative_invested="90000",
    ),
    DemoAccountSpec(
        "vip_2",
        "vip_2",
        "演示 VIP 二",
        "member",
        member_type="vip",
        share_quantity="650",
        cumulative_invested="70000",
    ),
    DemoAccountSpec(
        "vip_3",
        "vip_3",
        "演示 VIP 三",
        "member",
        member_type="vip",
        share_quantity="2000",
        cumulative_invested="180000",
    ),
)


def _demo_user_id(slot: str) -> str:
    return str(uuid5(_DEMO_NAMESPACE, slot))


def _username(prefix: str, suffix: str) -> str:
    value = f"{prefix.strip()}_{suffix}"
    normalized = normalize_username(value)
    if len(value) > 64:
        raise ValueError("Demo account username exceeds 64 characters")
    if not normalized.replace("_", "").isalnum():
        raise ValueError("Demo account prefix may contain only letters, numbers and underscores")
    return value


def _email(slot: str) -> str:
    return f"user-system-demo-{slot}@example.invalid"


def _load_user(db: sqlite3.Connection, user_id: str) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def _username_owner(db: sqlite3.Connection, username: str) -> str | None:
    row = db.execute(
        "SELECT id FROM users WHERE username_normalized = ?",
        (normalize_username(username),),
    ).fetchone()
    return str(row["id"]) if row is not None else None


def _insert_user(
    db: sqlite3.Connection,
    *,
    user_id: str,
    username: str,
    password_hash: str,
    spec: DemoAccountSpec,
    ceo_user_id: str,
    now: str,
) -> None:
    email = _email(spec.slot)
    creator = None if spec.role == "ceo" else ceo_user_id
    db.execute(
        """
        INSERT INTO users (
            id, username, username_normalized, password_hash,
            display_name, real_name, email, email_normalized,
            role_code, requested_role_code, department, member_type,
            lifecycle_status, registered_at, approved_at, approved_by,
            password_changed_at, created_by, created_at, updated_at, admin_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            username,
            normalize_username(username),
            password_hash,
            spec.display_name,
            spec.display_name,
            email,
            normalize_email(email),
            spec.role,
            spec.department,
            spec.member_type,
            now,
            now,
            creator,
            now,
            creator,
            now,
            now,
            f"可复用演示账号：{spec.display_name}",
        ),
    )


def _refresh_user(
    db: sqlite3.Connection,
    *,
    user_id: str,
    username: str,
    password_hash: str,
    spec: DemoAccountSpec,
    ceo_user_id: str,
    now: str,
) -> None:
    email = _email(spec.slot)
    approver = None if spec.role == "ceo" else ceo_user_id
    db.execute(
        """
        UPDATE users
        SET username = ?, username_normalized = ?, password_hash = ?,
            display_name = ?, real_name = ?,
            email = ?, email_normalized = ?,
            role_code = ?, requested_role_code = NULL,
            department = ?, member_type = ?,
            lifecycle_status = 'active', failed_login_count = 0, locked_until = NULL,
            auth_version = auth_version + 1, row_version = row_version + 1,
            approved_at = COALESCE(approved_at, ?), approved_by = COALESCE(approved_by, ?),
            password_changed_at = ?, updated_at = ?,
            admin_note = ?
        WHERE id = ?
        """,
        (
            username,
            normalize_username(username),
            password_hash,
            spec.display_name,
            spec.display_name,
            email,
            normalize_email(email),
            spec.role,
            spec.department,
            spec.member_type,
            now,
            approver,
            now,
            now,
            f"可复用演示账号：{spec.display_name}",
            user_id,
        ),
    )
    revoke_all_user_sessions(
        db,
        user_id=user_id,
        revoked_at=now,
        reason="demo_account_refreshed",
    )


def _seed_holding(
    db: sqlite3.Connection,
    *,
    user_id: str,
    spec: DemoAccountSpec,
    ceo_user_id: str,
    now: str,
) -> None:
    if spec.share_quantity is None or spec.cumulative_invested is None:
        return
    existing = get_member_holding(
        db,
        member_user_id=user_id,
        fund_id=_DEMO_FUND_ID,
    )
    if (
        existing is not None
        and existing.share_quantity == spec.share_quantity
        and existing.cumulative_invested == spec.cumulative_invested
        and existing.status == "active"
    ):
        return
    upsert_member_holding(
        db,
        member_user_id=user_id,
        fund_id=_DEMO_FUND_ID,
        share_quantity=spec.share_quantity,
        cumulative_invested=spec.cumulative_invested,
        confirmed_at=now,
        as_of=now,
        source="manual_admin",
        status="active",
        expected_version=existing.row_version if existing is not None else None,
        updated_by=ceo_user_id,
        now=now,
    )


def seed_demo_users(
    *,
    password: str,
    prefix: str = "demo",
    refresh_existing: bool = False,
    now: datetime | None = None,
) -> list[SeededDemoAccount]:
    timestamp = (now or datetime.now(UTC)).astimezone(UTC).isoformat()
    usernames = {spec.slot: _username(prefix, spec.username_suffix) for spec in _DEMO_ACCOUNTS}
    for spec in _DEMO_ACCOUNTS:
        validate_password(password, username=usernames[spec.slot], email=_email(spec.slot))

    ceo_user_id = _demo_user_id("ceo")
    seeded: list[SeededDemoAccount] = []
    with connection() as db:
        if not db.in_transaction:
            db.execute("BEGIN IMMEDIATE")
        update_fund_code(db, fund_id=_DEMO_FUND_ID, fund_code="DEMO-USDT")
        latest_nav = get_latest_available_nav(db, _DEMO_FUND_ID)
        if latest_nav is None or latest_nav.unit_nav != _DEMO_NAV:
            insert_fund_nav(
                db,
                fund_id=_DEMO_FUND_ID,
                valuation_time=timestamp,
                unit_nav=_DEMO_NAV,
                currency="USDT",
                source="manual_admin",
                now=timestamp,
            )

        for spec in _DEMO_ACCOUNTS:
            user_id = _demo_user_id(spec.slot)
            username = usernames[spec.slot]
            row = _load_user(db, user_id)
            if row is None:
                owner = _username_owner(db, username)
                if owner is not None:
                    user_id = owner
                    row = _load_user(db, user_id)
            created = row is None
            refreshed = False
            if created:
                _insert_user(
                    db,
                    user_id=user_id,
                    username=username,
                    password_hash=hash_password(password),
                    spec=spec,
                    ceo_user_id=ceo_user_id,
                    now=timestamp,
                )
            elif refresh_existing:
                conflict_owner = _username_owner(db, username)
                if conflict_owner is not None and conflict_owner != user_id:
                    raise ValueError(f"Username {username!r} is already used by another account")
                _refresh_user(
                    db,
                    user_id=user_id,
                    username=username,
                    password_hash=hash_password(password),
                    spec=spec,
                    ceo_user_id=ceo_user_id,
                    now=timestamp,
                )
                refreshed = True

            _seed_holding(
                db,
                user_id=user_id,
                spec=spec,
                ceo_user_id=ceo_user_id,
                now=timestamp,
            )
            if created or refreshed:
                insert_audit_event(
                    db,
                    event_type="user.demo_account_seeded",
                    subject_type="user",
                    subject_id=user_id,
                    actor_user_id=ceo_user_id,
                    auth_method="bootstrap",
                    result="succeeded",
                    details={"slot": spec.slot, "role": spec.role, "refreshed": refreshed},
                    request_id=None,
                    ip_address=None,
                    now=timestamp,
                )
            current = _load_user(db, user_id)
            if current is None:
                raise RuntimeError(f"Demo account {spec.slot} was not persisted")
            seeded.append(
                SeededDemoAccount(
                    slot=spec.slot,
                    user_id=user_id,
                    username=str(current["username"]),
                    role=str(current["role_code"]),
                    created=created,
                    refreshed=refreshed,
                )
            )
    return seeded
