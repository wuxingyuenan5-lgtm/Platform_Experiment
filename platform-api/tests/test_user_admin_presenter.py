from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.user_admin_presenter import admin_audit_response, admin_user_detail, admin_user_summary
from app.user_admin_repository import AdminAuditRecord, AdminUserRecord
from app.user_permissions import permissions_for_roles


def record() -> AdminUserRecord:
    return AdminUserRecord(
        id="user-1",
        username="member-one",
        display_name="Member One",
        real_name="完整姓名",
        avatar_key="avatar-1",
        phone="+86 138 0013 8000",
        email="member-one@example.test",
        role_code="member",
        requested_role_code=None,
        department=None,
        member_type="individual",
        application_note="application note",
        rejection_reason="rejection reason",
        lifecycle_status="active",
        registered_at="2026-01-02T03:04:05+00:00",
        last_login_at="2026-02-03T04:05:06+00:00",
        row_version=7,
        active_session_count=2,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-02-04T00:00:00+00:00",
    )


@pytest.mark.unit
def test_admin_summary_masks_contacts_and_preserves_fields() -> None:
    response = admin_user_summary(record(), sensitive=False)

    assert response.user_id == "user-1"
    assert response.role == "member"
    assert response.status == "active"
    assert response.real_name == "完***"
    assert response.email == "m***@example.test"
    assert response.phone == "***8000"
    assert response.contact_masked is True
    assert response.registered_at == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    assert response.last_login_at == datetime(2026, 2, 3, 4, 5, 6, tzinfo=UTC)
    assert response.active_session_count == 2
    assert response.row_version == 7


@pytest.mark.unit
def test_admin_detail_preserves_sensitive_alias_and_permission_contract() -> None:
    source = record()
    response = admin_user_detail(source, sensitive=True)

    assert response.contact_masked is False
    assert response.real_name == source.real_name
    assert response.email == source.email
    assert response.phone == source.phone
    assert response.application_note == source.application_note
    assert response.rejection_reason == source.rejection_reason
    assert response.permissions == sorted(permissions_for_roles(("member",)))
    payload = response.model_dump(by_alias=True)
    assert payload["userId"] == source.id
    assert payload["displayName"] == source.display_name
    assert payload["activeSessionCount"] == source.active_session_count
    assert payload["rowVersion"] == source.row_version
    assert payload["applicationNote"] == source.application_note
    assert payload["rejectionReason"] == source.rejection_reason


@pytest.mark.unit
def test_admin_audit_response_preserves_details_and_timestamp() -> None:
    source = AdminAuditRecord(
        id="audit-1",
        event_type="user.updated",
        actor_user_id="actor-1",
        result="succeeded",
        auth_method="session",
        request_id="request-1",
        details={"changedFields": ["email"]},
        created_at="2026-03-04T05:06:07+00:00",
    )

    response = admin_audit_response(source)

    assert response.event_id == source.id
    assert response.event_type == source.event_type
    assert response.actor_user_id == source.actor_user_id
    assert response.details == source.details
    assert response.created_at == datetime(2026, 3, 4, 5, 6, 7, tzinfo=UTC)
