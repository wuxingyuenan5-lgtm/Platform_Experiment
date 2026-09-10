from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import httpx
import pytest

from app import runtime_transport


@pytest.fixture(autouse=True)
def isolated_pool():
    runtime_transport.close()
    yield
    runtime_transport.close()


def test_reads_and_writes_reuse_one_tcp_connection():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b""
            requests.append((self.client_address, self.command, body))
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

        do_POST = do_GET

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/runtime"
        runtime_transport.get(url)
        runtime_transport.post(url, json={"quantity": "0.123456789012345678"})
        runtime_transport.get(url)
        assert len(requests) == 3
        assert len({address for address, _, _ in requests}) == 1
        assert requests[1][1:] == ("POST", b'{"quantity":"0.123456789012345678"}')
    finally:
        runtime_transport.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize(
    "error", [httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError]
)
def test_uncertain_write_is_attempted_once_and_preserves_identity(monkeypatch, error):
    attempts = []

    def send(request):
        attempts.append(request)
        raise error("response lost", request=request)

    client = httpx.Client(transport=httpx.MockTransport(send))
    monkeypatch.setattr(runtime_transport, "_client", client)
    with pytest.raises(error):
        runtime_transport.post("http://runtime/commands/orders", json={"commandId": "original"})
    assert len(attempts) == 1
    assert attempts[0].content == b'{"commandId":"original"}'


def test_pool_construction_is_shared_and_shutdown_releases_it(monkeypatch):
    real_client = httpx.Client
    clients = []

    def create(**kwargs):
        assert kwargs["trust_env"] is False
        assert kwargs["follow_redirects"] is False
        assert kwargs["verify"] is runtime_transport.RUNTIME_SSL_CONTEXT
        client = real_client(transport=httpx.MockTransport(lambda _: httpx.Response(200)))
        clients.append(client)
        return client

    monkeypatch.setattr(runtime_transport.httpx, "Client", create)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: runtime_transport.get("http://runtime/status"), range(24)))
    assert len(clients) == 1
    runtime_transport.close()
    assert clients[0].is_closed
    runtime_transport.get("http://runtime/status")
    assert len(clients) == 2


def test_request_timeout_is_not_mutated_on_the_shared_client(monkeypatch):
    observed = []

    def send(request):
        observed.append(request.extensions["timeout"])
        return httpx.Response(200)

    monkeypatch.setattr(
        runtime_transport, "_client", httpx.Client(transport=httpx.MockTransport(send))
    )
    runtime_transport.get("http://runtime/status", timeout=1.5)
    runtime_transport.post("http://runtime/commands/orders", timeout=9.0)
    assert observed[0]["read"] == 1.5
    assert observed[1]["read"] == 9.0
