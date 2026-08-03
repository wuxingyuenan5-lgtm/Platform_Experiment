from __future__ import annotations

from datetime import datetime

from app.user_repository import SessionSummaryRecord
from app.user_schemas import UserSessionListResponse, UserSessionSummaryResponse


def mask_ip(value: str | None) -> str | None:
    if value is None:
        return None
    if "." in value:
        parts = value.split(".")
        if len(parts) == 4:
            return ".".join((*parts[:3], "*"))
    if ":" in value:
        parts = [part for part in value.split(":") if part]
        return ":".join(parts[:4]) + "::*"
    return "***"


def summarize_user_agent(value: str | None) -> str | None:
    if value is None:
        return None
    compact = " ".join(value.split())
    return compact[:160]


def session_list_response(
    sessions: list[SessionSummaryRecord],
    *,
    current_session_id: str,
) -> UserSessionListResponse:
    return UserSessionListResponse(
        items=[
            UserSessionSummaryResponse(
                sessionId=session.id,
                current=session.id == current_session_id,
                createdAt=datetime.fromisoformat(session.created_at),
                expiresAt=datetime.fromisoformat(session.expires_at),
                idleExpiresAt=datetime.fromisoformat(session.idle_expires_at),
                lastSeenAt=datetime.fromisoformat(session.last_seen_at),
                lastReauthenticatedAt=(
                    datetime.fromisoformat(session.last_reauthenticated_at)
                    if session.last_reauthenticated_at is not None
                    else None
                ),
                ipSummary=mask_ip(session.ip_address),
                userAgentSummary=summarize_user_agent(session.user_agent),
            )
            for session in sessions
        ]
    )
