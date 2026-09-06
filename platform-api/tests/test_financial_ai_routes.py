from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import HttpUrl, TypeAdapter, ValidationError

import app.financial_ai_routes as financial_ai_routes
from app.auth import permission_for_request
from app.financial_ai_routes import (
    AiConnection,
    _completion_url,
    _read_local_connection,
    _require_gateway_key,
    _write_local_connection,
    settings,
)
from app.main import app
from app.user_permissions import has_permission


def test_browser_connection_only_selects_api_or_known_subscription_cli() -> None:
    assert AiConnection(mode="api").mode == "api"
    with pytest.raises(ValidationError):
        AiConnection(mode="deployment")


def test_subscription_connection_only_accepts_known_cli() -> None:
    assert AiConnection(mode="subscription", cli="codex").cli == "codex"
    with pytest.raises(ValidationError):
        AiConnection(mode="subscription", cli="arbitrary-command")


def test_optional_gateway_compares_sha256_digest() -> None:
    previous = settings.financial_ai_access_key_sha256
    try:
        settings.financial_ai_access_key_sha256 = hashlib.sha256(b"browser-secret").hexdigest()
        _require_gateway_key("browser-secret")
        with pytest.raises(HTTPException) as error:
            _require_gateway_key("wrong")
        assert error.value.status_code == 401
    finally:
        settings.financial_ai_access_key_sha256 = previous


def test_connection_is_saved_on_backend_and_read_without_browser_storage(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "financial_ai_connection.json"
    monkeypatch.setattr(financial_ai_routes, "_CONNECTION_PATH", target)
    payload = {
        "provider": "deepseek",
        "baseUrl": "https://api.deepseek.com",
        "apiKey": "server-only-secret",
        "model": "deepseek-v4-flash",
    }
    _write_local_connection(payload)
    assert _read_local_connection() == payload
    assert target.exists()


def test_connection_api_persists_key_but_never_returns_it(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "financial_ai_connection.json"
    monkeypatch.setattr(financial_ai_routes, "_CONNECTION_PATH", target)
    with TestClient(app) as client:
        response = client.put(
            "/api/v1/financial-ai/connection",
            json={
                "provider": "deepseek",
                "base_url": "https://api.deepseek.com",
                "api_key": "server-only-secret",
                "model": "deepseek-v4-flash",
            },
        )
        status = client.get("/api/v1/financial-ai/connection")
    assert response.status_code == 200
    assert status.status_code == 200
    assert response.json()["hasApiKey"] is True
    assert "apiKey" not in response.json()
    assert "server-only-secret" not in response.text
    assert "server-only-secret" not in status.text
    assert json.loads(target.read_text(encoding="utf-8"))["apiKey"] == "server-only-secret"


def test_connection_api_can_clear_the_backend_file(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "financial_ai_connection.json"
    monkeypatch.setattr(financial_ai_routes, "_CONNECTION_PATH", target)
    _write_local_connection(
        {
            "provider": "deepseek",
            "baseUrl": "https://api.deepseek.com",
            "apiKey": "server-only-secret",
            "model": "deepseek-v4-flash",
        }
    )
    with TestClient(app) as client:
        response = client.delete("/api/v1/financial-ai/connection")
    assert response.status_code == 200
    assert response.json()["configured"] is False
    assert response.json()["hasApiKey"] is False
    assert not target.exists()


def test_financial_ai_analysis_posts_only_require_platform_read() -> None:
    assert permission_for_request("POST", "/api/v1/financial-ai/chat") == "platform:read"
    assert permission_for_request("POST", "/api/v1/financial-ai/test-connection") == "platform:read"
    assert permission_for_request("GET", "/api/v1/financial-ai/connection") == "platform:read"


def test_financial_ai_shared_connection_changes_require_management_write() -> None:
    path = "/api/v1/financial-ai/connection"
    assert permission_for_request("PUT", path) == "settings.write"
    assert permission_for_request("DELETE", path) == "settings.write"
    assert has_permission(["ceo"], "settings.write")
    assert has_permission(["tech_lead"], "settings.write")
    assert has_permission(["admin"], "settings.write")
    assert not has_permission(["employee"], "settings.write")
    assert not has_permission(["member"], "settings.write")
    assert not has_permission(["viewer"], "settings.write")


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("https://api.deepseek.com", "https://api.deepseek.com/v1/chat/completions"),
        ("https://api.openai.com/v1", "https://api.openai.com/v1/chat/completions"),
        ("https://example.com/v3", "https://example.com/v3/chat/completions"),
        (
            "https://example.com/api/v3",
            "https://example.com/api/v3/chat/completions",
        ),
    ],
)
def test_completion_url_matches_reference_compatible_endpoint_logic(
    base_url: str, expected: str
) -> None:
    parsed = TypeAdapter(HttpUrl).validate_python(base_url)
    assert _completion_url(parsed) == expected
