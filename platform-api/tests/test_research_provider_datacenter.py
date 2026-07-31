from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app import research_provider_datacenter as datacenter
from app.research_provider_datacenter import EastmoneyDataCenterClient

pytestmark = pytest.mark.unit


class _Response:
    def __init__(self, payload: Any, error: Exception | None = None) -> None:
        self._payload = payload
        self._error = error

    def raise_for_status(self) -> None:
        if self._error is not None:
            raise self._error

    def json(self) -> Any:
        return self._payload


class _Client:
    init_kwargs: dict[str, Any] | None = None
    request: dict[str, Any] | None = None
    payload: Any = None
    error: Exception | None = None

    def __init__(self, **kwargs: Any) -> None:
        type(self).init_kwargs = kwargs

    async def __aenter__(self) -> _Client:
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def get(self, url: str, **kwargs: Any) -> _Response:
        type(self).request = {"url": url, **kwargs}
        return _Response(type(self).payload, type(self).error)


def _client(monkeypatch: pytest.MonkeyPatch) -> EastmoneyDataCenterClient:
    _Client.init_kwargs = None
    _Client.request = None
    _Client.payload = None
    _Client.error = None
    monkeypatch.setattr(datacenter.httpx, "AsyncClient", _Client)
    return EastmoneyDataCenterClient(timeout_seconds=8.5, user_agent="research-test")


def test_datacenter_client_preserves_http_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    _Client.payload = {"result": {"data": [{"SECURITY_CODE": "600000"}]}}

    rows = asyncio.run(
        client.rows(
            report_name="RPTA_WEB_RZRQ_GGMX",
            filter_value='(SCODE="600000")',
            page_size=12,
            sort_columns="DATE",
            sort_types="1",
        )
    )

    assert rows == [{"SECURITY_CODE": "600000"}]
    assert _Client.init_kwargs == {"timeout": 8.5, "trust_env": False}
    assert _Client.request == {
        "url": "https://datacenter-web.eastmoney.com/api/data/v1/get",
        "params": {
            "reportName": "RPTA_WEB_RZRQ_GGMX",
            "columns": "ALL",
            "filter": '(SCODE="600000")',
            "pageNumber": "1",
            "pageSize": "12",
            "sortColumns": "DATE",
            "sortTypes": "1",
            "source": "WEB",
            "client": "WEB",
        },
        "headers": {"User-Agent": "research-test"},
    }


def test_datacenter_client_preserves_empty_result_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    _Client.payload = {"result": None}

    assert asyncio.run(client.rows(report_name="RPT_TEST", filter_value="")) == []


def test_datacenter_client_does_not_swallow_http_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    _Client.payload = {"result": {"data": []}}
    _Client.error = RuntimeError("upstream failed")

    with pytest.raises(RuntimeError, match="upstream failed"):
        asyncio.run(client.rows(report_name="RPT_TEST", filter_value=""))


def test_datacenter_client_preserves_malformed_payload_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    _Client.payload = []

    with pytest.raises(AttributeError):
        asyncio.run(client.rows(report_name="RPT_TEST", filter_value=""))
