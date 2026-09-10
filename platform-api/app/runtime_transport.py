"""One process-owned HTTPX connection pool for the execution Runtime.

Every call makes one HTTP attempt. In particular POST timeout/connection errors
must reach the business owner, which persists unknown results and reconciles by
the original identity. Neither transport retries nor redirects may replay writes.
"""

import ssl
from contextlib import contextmanager
from threading import Lock
from time import perf_counter

import httpx
from prometheus_client import Histogram

from app.config import get_settings

# Loading the Windows trust store for every state-machine read adds seconds
# to each instruction. Reuse the verified context; never disable TLS checks.
RUNTIME_SSL_CONTEXT = ssl.create_default_context()

_lock = Lock()
_client: httpx.Client | None = None
REQUEST_SECONDS = Histogram(
    "vg_platform_runtime_request_seconds", "Single Runtime HTTP attempt, including failures",
    ("method", "outcome"), buckets=(0.01, 0.05, 0.1, 0.5, 1, 2, 5, 15, 60),
)


@contextmanager
def _observe(method: str):
    started = perf_counter()
    result: list[httpx.Response] = []
    outcome = "error"
    try:
        yield result
        status = result[0].status_code
        outcome = "rate_limited" if status == 429 else f"http_{status // 100}xx"
    except httpx.TimeoutException:
        outcome = "timeout"
        raise
    except httpx.TransportError:
        outcome = "transport_error"
        raise
    finally:
        REQUEST_SECONDS.labels(method, outcome).observe(perf_counter() - started)


def _get_client() -> httpx.Client:
    global _client
    with _lock:
        if _client is None:
            _client = httpx.Client(
                verify=RUNTIME_SSL_CONTEXT,
                trust_env=False,
                follow_redirects=False,
            )
        return _client


def close() -> None:
    """Release the pool after API requests and background runners have drained."""
    global _client
    with _lock:
        client, _client = _client, None
    if client is not None:
        client.close()


def get(
    url: str,
    *,
    params: dict[str, str] | None = None,
    timeout: float | None = None,
) -> httpx.Response:
    with _observe("GET") as result:
        response = _get_client().get(
            url,
            params=params,
            timeout=get_settings().runtime_timeout_seconds if timeout is None else timeout,
        )
        result.append(response)
        return response


def post(
    url: str,
    *,
    json: object = None,
    timeout: float | None = None,
) -> httpx.Response:
    with _observe("POST") as result:
        response = _get_client().post(
            url,
            json=json,
            timeout=get_settings().runtime_timeout_seconds if timeout is None else timeout,
        )
        result.append(response)
        return response
