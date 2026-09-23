"""A slow session store must not stall unrelated requests on the ASGI loop."""

import asyncio
import sqlite3
from contextlib import contextmanager
from threading import Event

import httpx
import pytest
from fastapi import FastAPI

from app import auth


@pytest.mark.parametrize("denied", [False, True])
def test_auth_store_wait_does_not_block_health(monkeypatch, denied):
    entered = Event()
    released = Event()
    finished_before_release = []

    def wait_for_health():
        entered.set()
        finished_before_release.append(not released.wait(timeout=2))

    def authenticate(_request, _settings):
        if denied:
            raise auth.AuthenticationError(401, "invalid_session", "Session invalid")
        wait_for_health()
        _request.state.browser_session = auth.AuthenticatedBrowserSession(
            session_id="test-session",
            user_id="owner",
            role_code="ceo",
            csrf_token_hash="test",
            last_reauthenticated_at=None,
        )
        return auth.Principal(
            user_id="owner", roles=("ceo",), auth_method="session", session_id="test-session"
        )

    def audit(**_kwargs):
        wait_for_health()

    monkeypatch.setattr(auth, "authenticate_request", authenticate)
    monkeypatch.setattr(auth, "audit_auth_event", audit)
    app = FastAPI()
    app.add_middleware(auth.AuthenticationMiddleware)

    @app.get("/health")
    async def health():
        released.set()
        return {"status": "ok"}

    @app.get("/api/v1/auth/me")
    async def me():
        return {"status": "ok"}

    async def exercise():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            pending = asyncio.create_task(client.get("/api/v1/auth/me"))
            assert await asyncio.to_thread(entered.wait, 3)
            try:
                assert (await client.get("/health")).status_code == 200
            finally:
                released.set()
            assert (await pending).status_code == (401 if denied else 200)

    asyncio.run(exercise())
    assert finished_before_release == [False]


@pytest.mark.parametrize(
    "table,path",
    [
        ("execution_batches", "/api/v1/trading/execution-batches/test/risk-actions"),
        ("strategy_runs", "/api/v1/strategy-instructions/test/execute"),
    ],
)
def test_trade_authority_sqlite_lock_does_not_block_health(monkeypatch, tmp_path, table, path):
    database = tmp_path / "locked.db"
    lock = sqlite3.connect(database)
    lock.execute("CREATE TABLE strategy_instances (id TEXT, strategy_definition_id TEXT)")
    lock.execute("CREATE TABLE strategy_definitions (id TEXT, strategy_key TEXT)")
    lock.execute(f"CREATE TABLE {table} (id TEXT, strategy_instance_id TEXT)")
    lock.execute(f"INSERT INTO {table} VALUES (?,?)", ("test", "not-a-ceo-strategy"))
    lock.commit()
    lock.execute("BEGIN EXCLUSIVE")
    entered = Event()

    @contextmanager
    def locked_connection():
        db = sqlite3.connect(database, timeout=2)
        db.row_factory = sqlite3.Row
        entered.set()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(auth, "connection", locked_connection)
    app = FastAPI()

    @app.get("/health")
    async def health():
        lock.rollback()
        return {"status": "ok"}

    @app.post(path)
    async def trade_authority(request: auth.Request):
        return {"required": await auth.requires_ceo_trade_authority(request)}

    async def exercise():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            pending = asyncio.create_task(client.post(path))
            assert await asyncio.to_thread(entered.wait, 3)
            assert (await client.get("/health")).status_code == 200
            result = await pending
            assert result.json() == {"required": False}

    try:
        asyncio.run(exercise())
    finally:
        lock.close()
