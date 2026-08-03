from __future__ import annotations

import pytest

from app.auth import AuthenticationAssurance, assurance_for_request
from app.config import Settings


@pytest.mark.unit
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/me/holdings"),
        ("GET", "/api/v1/users/member-id/holdings"),
        ("PUT", "/api/v1/users/member-id/holdings/fund-id"),
        ("GET", "/api/v1/users/holdings/funds"),
        ("PUT", "/api/v1/users/holdings/funds/fund-id/nav"),
    ],
)
def test_holding_routes_are_human_session_assurance_in_live(
    method: str,
    path: str,
) -> None:
    settings = Settings(environment="live", auth_mode="api_key")
    assert (
        assurance_for_request(method, path, settings)
        == AuthenticationAssurance.HUMAN_SESSION
    )
