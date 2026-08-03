from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.user_repository import SessionSummaryRecord
from app.user_session_presenter import mask_ip, session_list_response, summarize_user_agent


@pytest.mark.unit
def test_session_formatting_preserves_original_masking_and_summary_rules() -> None:
    assert mask_ip(None) is None
    assert mask_ip("192.168.10.24") == "192.168.10.*"
    assert mask_ip("2001:db8:85a3:0:0:8a2e:370:7334") == "2001:db8:85a3:0::*"
    assert mask_ip("local") == "***"
    assert summarize_user_agent(None) is None
    assert summarize_user_agent(" Browser   Agent\nVersion ") == "Browser Agent Version"
    assert summarize_user_agent("x" * 180) == "x" * 160


@pytest.mark.unit
def test_session_list_response_preserves_aliases_current_marker_and_timestamps() -> None:
    session = SessionSummaryRecord(
        id="session-1",
        created_at="2026-01-01T01:02:03+00:00",
        expires_at="2026-01-02T01:02:03+00:00",
        idle_expires_at="2026-01-01T02:02:03+00:00",
        last_seen_at="2026-01-01T01:32:03+00:00",
        last_reauthenticated_at="2026-01-01T01:22:03+00:00",
        ip_address="10.20.30.40",
        user_agent=" Browser   Agent ",
    )

    response = session_list_response([session], current_session_id="session-1")
    item = response.items[0]

    assert item.current is True
    assert item.created_at == datetime(2026, 1, 1, 1, 2, 3, tzinfo=UTC)
    assert item.last_reauthenticated_at == datetime(2026, 1, 1, 1, 22, 3, tzinfo=UTC)
    assert item.ip_summary == "10.20.30.*"
    assert item.user_agent_summary == "Browser Agent"
    payload = response.model_dump(by_alias=True)
    assert payload["items"][0]["sessionId"] == "session-1"
    assert payload["items"][0]["idleExpiresAt"] == datetime(2026, 1, 1, 2, 2, 3, tzinfo=UTC)
    assert payload["items"][0]["ipSummary"] == "10.20.30.*"
