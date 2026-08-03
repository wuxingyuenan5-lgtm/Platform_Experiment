import httpx
import pytest
from fastapi import HTTPException

from app import venue_reconciliation
from app import venue_reconciliation_runtime_client as runtime_client
from app.config import get_settings


def test_runtime_get_uses_configured_url_params_and_timeout(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "runtime_base_url", "http://runtime.test")
    monkeypatch.setattr(settings, "runtime_timeout_seconds", 7.5)
    captured: dict[str, object] = {}
    expected = httpx.Response(200, request=httpx.Request("GET", "http://runtime.test/venue/positions"))

    def fake_get(
        url: str,
        *,
        params: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        captured.update(url=url, params=params, timeout=timeout)
        return expected

    monkeypatch.setattr(runtime_client.httpx, "get", fake_get)

    result = runtime_client.get("/venue/positions", params={"accountId": "account-1"})

    assert result is expected
    assert captured == {
        "url": "http://runtime.test/venue/positions",
        "params": {"accountId": "account-1"},
        "timeout": 7.5,
    }


def test_runtime_get_wraps_http_transport_errors(monkeypatch) -> None:
    def fail(*args, **kwargs):
        raise httpx.ConnectError("runtime unavailable")

    monkeypatch.setattr(runtime_client.httpx, "get", fail)

    with pytest.raises(runtime_client.RuntimeQueryError) as exc_info:
        runtime_client.get("/venue/balances")

    assert str(exc_info.value) == "Platform Execution Runtime query failed"
    assert isinstance(exc_info.value.__cause__, httpx.ConnectError)


def test_compatibility_runtime_get_preserves_platform_503_mapping(monkeypatch) -> None:
    def fail(path: str, params: dict[str, str] | None = None) -> httpx.Response:
        raise runtime_client.RuntimeQueryError("Platform Execution Runtime query failed")

    monkeypatch.setattr(runtime_client, "get", fail)

    with pytest.raises(HTTPException) as exc_info:
        venue_reconciliation.runtime_get("/venue/orders/by-platform/order-1")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Platform Execution Runtime query failed"
    assert isinstance(exc_info.value.__cause__, runtime_client.RuntimeQueryError)
