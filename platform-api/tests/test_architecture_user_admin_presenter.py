from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.architecture
def test_user_admin_presenter_boundary() -> None:
    service = (ROOT / "app" / "user_admin_service.py").read_text(encoding="utf-8")
    presenter = (ROOT / "app" / "user_admin_presenter.py").read_text(encoding="utf-8")

    assert "from app.user_admin_presenter import admin_audit_response as _audit_response" in service
    assert "from app.user_admin_presenter import admin_user_detail as _detail" in service
    assert "from app.user_admin_presenter import admin_user_summary as _summary" in service

    for removed_definition in (
        "def _mask_email",
        "def _mask_phone",
        "def _mask_real_name",
        "def _summary",
        "def _detail",
        "def _audit_response",
    ):
        assert removed_definition not in service

    for retained_call in (
        "assert_active_ceo_remains",
        "assert_recent_reauthentication",
        "revoke_all_user_sessions",
        "assert_can_manage_target",
        "assert_can_assign_role",
    ):
        assert retained_call in service

    for presenter_contract in (
        "def admin_user_summary",
        "def admin_user_detail",
        "def admin_audit_response",
        "permissions_for_roles",
        "contactMasked=not sensitive",
        "applicationNote=record.application_note if sensitive else None",
        "rejectionReason=record.rejection_reason if sensitive else None",
        "base.model_dump(by_alias=True)",
    ):
        assert presenter_contract in presenter
