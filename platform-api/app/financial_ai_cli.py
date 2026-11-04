"""Restricted machine-account CLI invocation and subprocess lifetime ownership."""
from __future__ import annotations

import asyncio
import codecs
import os
import shutil
import signal
import subprocess
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import anyio

CLI_COMMANDS: dict[str, tuple[str, ...] | None] = {
    "codex": (
        "exec", "--skip-git-repo-check", "--sandbox", "read-only",
        "--ignore-user-config", "--ignore-rules", "--ephemeral", "-",
    ),
    "claude": (
        "-p", "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        "--setting-sources", "", "--settings", '{"disableAllHooks":true}',
        "--disable-slash-commands", "--no-session-persistence", "--no-chrome",
        "--permission-mode", "dontAsk",
    ),
    # No verified unattended, restricted invocation is available for these adapters.
    "qwen": None,
    "deepseek": None,
}
CLI_TIMEOUT_SECONDS = 300
STDERR_LIMIT = 8192


def cli_executable(cli: str) -> str | None:
    if CLI_COMMANDS.get(cli) is None:
        return None
    # Do not execute npm .cmd/.ps1 shims through a shell with user-supplied input.
    return shutil.which(f"{cli}.exe" if os.name == "nt" else cli)


def cli_environment() -> dict[str, str]:
    # Keep OS, subscription login location and deployment proxy/TLS policy only.
    allowed = {
        "PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP",
        "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "LANG", "LC_ALL",
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "SSL_CERT_FILE",
        "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "NODE_EXTRA_CA_CERTS",
    }
    return {key: value for key, value in os.environ.items() if key.upper() in allowed}


async def _drain_stderr(stream: asyncio.StreamReader) -> bytes:
    tail = bytearray()
    while chunk := await stream.read(4096):
        tail.extend(chunk)
        del tail[:-STDERR_LIMIT]
    return bytes(tail)


async def _stop_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is None:
        if os.name == "nt":
            # taskkill targets this invocation's process tree, including CLI helpers.
            killer = await asyncio.create_subprocess_exec(
                str(Path(os.environ["SYSTEMROOT"]) / "System32" / "taskkill.exe"),
                "/PID", str(process.pid), "/T", "/F",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            try:
                await asyncio.wait_for(killer.wait(), 5)
            except TimeoutError:
                killer.kill()
                await killer.wait()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
    await process.wait()


async def cli_stream(cli: str, prompt: str) -> AsyncIterator[dict[str, str]]:
    arguments = CLI_COMMANDS.get(cli)
    if arguments is None:
        yield {"type": "error", "message": "该 CLI 尚不支持受限分析调用，请使用 API 接入。"}
        return
    executable = cli_executable(cli)
    if not executable:
        yield {"type": "error", "message": f"未检测到 {cli} 原生 CLI，请先安装并登录。"}
        return
    workspace = tempfile.mkdtemp(prefix="vg-financial-ai-")
    process: asyncio.subprocess.Process | None = None
    stderr_task: asyncio.Task[bytes] | None = None
    failure: str | None = None
    try:
        async with asyncio.timeout(CLI_TIMEOUT_SECONDS):
            process = await asyncio.create_subprocess_exec(
                executable, *arguments, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                cwd=workspace, env=cli_environment(),
                **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt"
                   else {"start_new_session": True}),
            )
            assert process.stdin and process.stdout and process.stderr
            stderr_task = asyncio.create_task(_drain_stderr(process.stderr))
            process.stdin.write(prompt.encode("utf-8"))
            await process.stdin.drain()
            process.stdin.close()
            decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
            while chunk := await process.stdout.read(1024):
                text = decoder.decode(chunk)
                if text:
                    yield {"type": "delta", "text": text}
            if text := decoder.decode(b"", final=True):
                yield {"type": "delta", "text": text}
            return_code = await process.wait()
            await stderr_task
            # stderr can contain local paths or authentication details; do not expose it.
            yield ({"type": "error", "message": f"CLI 退出码 {return_code}"}
                   if return_code else {"type": "done"})
    except TimeoutError:
        failure = f"CLI 运行超过 {CLI_TIMEOUT_SECONDS} 秒，已停止。"
    except (OSError, BrokenPipeError):
        failure = "CLI 启动或通信失败，请检查本机安装与登录状态。"
    finally:
        # Starlette cancellation uses an AnyIO cancel scope. Cleanup must survive it.
        with anyio.CancelScope(shield=True):
            if process is not None:
                await _stop_process(process)
            if stderr_task is not None:
                stderr_task.cancel()
                await asyncio.gather(stderr_task, return_exceptions=True)
        try:
            os.rmdir(workspace)  # Only remove an empty invocation directory.
        except OSError:
            pass
    if failure:
        yield {"type": "error", "message": failure}
