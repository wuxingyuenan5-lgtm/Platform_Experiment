import json
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

from app import bybit_connection
from app.bybit_connection import BybitConnections
from app.bybit_live_adapter import BybitLiveAdapter
from app.config import Settings


def connections(monkeypatch):
    monkeypatch.setattr(
        bybit_connection,
        "resolve_secret_reference",
        lambda *_args, **_kwargs: {"API_KEY": "offline-key", "SECRET": "offline-secret"},
    )
    # Isolate time evidence as well as the HTTP transport. No server connection.
    monkeypatch.setattr(BybitConnections, "_sync_clock", lambda *args: None)
    return BybitConnections(Settings(_env_file=None, bybit_account_ids="first,second"))


def test_concurrent_users_share_one_sdk_per_account(monkeypatch):
    manager = connections(monkeypatch)
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            clients = list(pool.map(lambda _: manager.client("first"), range(24)))
        assert len({id(client) for client in clients}) == 1
        assert manager.client("second") is not clients[0]
        assert clients[0].force_retry is False
        assert clients[0].max_retries == 1
    finally:
        manager.close()


def test_sdk_write_timeout_is_not_replayed_and_preserves_client_id(monkeypatch):
    manager = connections(monkeypatch)
    attempts = []

    class LostResponse(requests.adapters.BaseAdapter):
        def send(self, request, **kwargs):
            attempts.append(request)
            raise requests.ReadTimeout("accepted remotely, response lost")

        def close(self):
            pass

    try:
        client = manager.client("first")
        client.client.mount("https://", LostResponse())
        with pytest.raises(requests.ReadTimeout):
            client.place_order(
                category="linear",
                symbol="XAUTUSDT",
                side="Buy",
                orderType="Market",
                qty="0.1234567891",
                orderLinkId="the-original-intent",
            )
        assert len(attempts) == 1
        payload = json.loads(attempts[0].body)
        assert payload["orderLinkId"] == "the-original-intent"
        assert payload["qty"] == "0.1234567891"
    finally:
        manager.close()


def test_read_retries_only_transport_errors_on_the_same_client():
    client = object()
    adapter = BybitLiveAdapter(Settings(_env_file=None, bybit_account_ids="first"), client)
    attempts = []

    def flaky(value):
        attempts.append(value)
        if len(attempts) == 1:
            raise requests.ConnectionError("read connection dropped")
        return {"confirmed": True}

    assert adapter._read_with_retry("first", flaky) == {"confirmed": True}
    assert attempts == [client, client]
    attempts.clear()

    def invalid(value):
        attempts.append(value)
        raise ValueError("malformed receipt")

    with pytest.raises(ValueError):
        adapter._read_with_retry("first", invalid)
    assert attempts == [client]


def test_clock_calibration_uses_post_response_sample_for_asymmetric_paths():
    samples = iter([1_000_000])

    class PublicClient:
        @staticmethod
        def get_server_time():
            return {"retCode": 0, "time": 999_950}

    offset = BybitConnections._measure_clock_offset(lambda: next(samples), PublicClient())

    # The latest local sample keeps signed requests behind the venue when the
    # response path is slower in one direction.
    assert offset == -50
