import asyncio
import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

from app import financial_ai_cli as cli
from app import financial_ai_routes as routes
from app.auth import Principal, require_principal
from app.main import app


@pytest.mark.parametrize("role", ["guest", "viewer", "member", "employee"])
def test_readers_cannot_invoke_machine_cli_but_can_use_api(monkeypatch, role):
    calls = []

    async def stream(request):
        calls.append(request.connection.mode)
        yield b'{"type":"done"}\n'

    monkeypatch.setattr(routes, "_chat_stream", stream)
    app.dependency_overrides[require_principal] = lambda: Principal("reader", (role,), "session")
    try:
        client = TestClient(app)
        payload = {"connection": {"mode": "subscription", "cli": "codex"},
                   "prompt": "hello", "context": "facts"}
        assert client.post("/api/v1/financial-ai/chat", json=payload).status_code == 403
        assert client.post("/api/v1/financial-ai/test-connection",
                           json=payload["connection"]).status_code == 403
        assert not calls
        payload["connection"] = {"mode": "api"}
        assert client.post("/api/v1/financial-ai/chat", json=payload).status_code == 200
        assert calls == ["api"]
    finally:
        app.dependency_overrides.pop(require_principal, None)


def test_manager_can_use_restricted_subscription_and_unsupported_cli_is_closed(monkeypatch):
    calls = []

    async def stream(request):
        calls.append(request.connection.cli)
        yield b'{"type":"done"}\n'

    monkeypatch.setattr(routes, "_chat_stream", stream)
    app.dependency_overrides[require_principal] = lambda: Principal("admin", ("admin",), "session")
    try:
        client = TestClient(app)
        assert client.post("/api/v1/financial-ai/chat", json={
            "connection": {"mode": "subscription", "cli": "codex"},
            "prompt": "hello", "context": "facts",
        }).status_code == 200
        assert calls == ["codex"]
        assert client.post("/api/v1/financial-ai/test-connection", json={
            "mode": "subscription", "cli": "qwen",
        }).json()["ok"] is False
    finally:
        app.dependency_overrides.pop(require_principal, None)


def test_fixed_restricted_flags_and_environment(monkeypatch):
    monkeypatch.setenv("VG_RUNTIME_TOKEN", "private")
    monkeypatch.setenv("OPENAI_API_KEY", "private")
    monkeypatch.setenv("NODE_OPTIONS", "--require evil.js")
    monkeypatch.setenv("HTTPS_PROXY", "http://deployment-proxy")
    environment = cli.cli_environment()
    assert not {"VG_RUNTIME_TOKEN", "OPENAI_API_KEY", "NODE_OPTIONS"} & environment.keys()
    assert environment["HTTPS_PROXY"] == "http://deployment-proxy"
    codex = cli.CLI_COMMANDS["codex"]
    assert codex[codex.index("--sandbox") + 1] == "read-only"
    assert "--ignore-user-config" in codex
    claude = cli.CLI_COMMANDS["claude"]
    assert claude[claude.index("--tools") + 1] == ""
    assert "--strict-mcp-config" in claude
    assert cli.CLI_COMMANDS["qwen"] is cli.CLI_COMMANDS["deepseek"] is None


def fake_cli(monkeypatch, script):
    processes = []
    original = asyncio.create_subprocess_exec

    async def spawn(*args, **kwargs):
        process = await original(*args, **kwargs)
        if args[0] == sys.executable:
            processes.append((process, kwargs))
        return process

    monkeypatch.setattr(cli, "cli_executable", lambda _: sys.executable)
    monkeypatch.setitem(cli.CLI_COMMANDS, "codex", ("-u", "-c", script))
    monkeypatch.setattr(cli.asyncio, "create_subprocess_exec", spawn)
    return processes


def request():
    return routes.AiChatRequest(connection={"mode": "subscription", "cli": "codex"},
                                prompt="hello", context="facts")


def test_real_process_drains_large_stderr_and_uses_empty_working_directory(monkeypatch):
    processes = fake_cli(monkeypatch,
        "import sys; sys.stdin.read(); sys.stderr.write('secret'*200000); print('success')")

    async def run():
        return [json.loads(event) async for event in routes._chat_stream(request())]

    events = asyncio.run(run())
    assert events[-1] == {"type": "done"}
    assert "success" in "".join(event.get("text", "") for event in events)
    assert "secret" not in str(events)
    process, options = processes[0]
    assert process.returncode == 0
    assert options["cwd"] != os.getcwd()
    assert not os.path.exists(options["cwd"])


@pytest.mark.parametrize("stop", ["close", "cancel", "timeout"])
def test_real_process_is_reaped_when_stream_stops(monkeypatch, stop):
    processes = fake_cli(monkeypatch,
        "import sys,time; sys.stdin.read(); print('ready',flush=True); time.sleep(60)")
    monkeypatch.setattr(cli, "CLI_TIMEOUT_SECONDS", 0.4 if stop == "timeout" else 10)

    async def run():
        stream = routes._chat_stream(request())
        assert json.loads(await anext(stream))["text"].strip() == "ready"
        if stop == "close":
            await stream.aclose()
        elif stop == "cancel":
            pending = asyncio.create_task(anext(stream))
            await asyncio.sleep(0.05)
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
        else:
            error = json.loads(await anext(stream))
            assert error["type"] == "error"
            assert processes[0][0].returncode is not None
            await stream.aclose()
        assert processes[0][0].returncode is not None
        assert not os.path.exists(processes[0][1]["cwd"])

    asyncio.run(run())


def test_nonzero_exit_does_not_expose_stderr_credentials(monkeypatch):
    fake_cli(monkeypatch, "import sys; sys.stdin.read(); sys.stderr.write('secret-key'); sys.exit(2)")

    async def run():
        return [event async for event in cli.cli_stream("codex", "facts")]

    assert asyncio.run(run()) == [{"type": "error", "message": "CLI 退出码 2"}]
