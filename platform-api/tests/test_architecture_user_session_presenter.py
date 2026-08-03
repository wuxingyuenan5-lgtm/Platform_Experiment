from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.architecture
def test_user_session_presenter_boundary() -> None:
    service = (ROOT / "app" / "user_service.py").read_text(encoding="utf-8")
    presenter = (ROOT / "app" / "user_session_presenter.py").read_text(encoding="utf-8")

    assert "session_list_response as _session_list_response" in service
    assert "summarize_user_agent as _summarize_user_agent" in service
    assert "def _mask_ip" not in service
    assert "def _summarize_user_agent" not in service
    assert "return _session_list_response(" in service
    assert "user_agent=_summarize_user_agent(user_agent)" in service

    for retained_call in (
        "get_session_owner",
        "revoke_session",
        "revoke_other_user_sessions",
        "insert_audit_event",
        "rotate_session_csrf",
        "hash_secret_token",
    ):
        assert retained_call in service

    for presenter_contract in (
        "def mask_ip",
        "def summarize_user_agent",
        "def session_list_response",
        "current=session.id == current_session_id",
        "datetime.fromisoformat(session.created_at)",
        "ipSummary=mask_ip(session.ip_address)",
        "userAgentSummary=summarize_user_agent(session.user_agent)",
    ):
        assert presenter_contract in presenter
