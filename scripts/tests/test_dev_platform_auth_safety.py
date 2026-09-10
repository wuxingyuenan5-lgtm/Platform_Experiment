from __future__ import annotations

import base64
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
STARTUP_SCRIPT = REPO_ROOT / "scripts" / "dev-platform.ps1"


def test_windows_powershell_reads_utf8_state_without_bom(tmp_path) -> None:
    executable = shutil.which("powershell")
    if executable is None:
        pytest.skip("Windows PowerShell is unavailable")
    state_path = tmp_path / "state.json"
    expected = {"repoRoot": "C:/workspace/全球变量平台", "services": []}
    state_path.write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")
    source = STARTUP_SCRIPT.read_text(encoding="utf-8")
    reader = source[
        source.index("function Read-State {") : source.index("function Write-State {")
    ]
    script = (
        "[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)\n"
        + "$StatePath = '"
        + str(state_path).replace("'", "''")
        + "'\n"
        + reader
        + "\nRead-State | ConvertTo-Json -Compress\n"
    )
    result = subprocess.run(
        [
            executable,
            "-NoProfile",
            "-EncodedCommand",
            base64.b64encode(script.encode("utf-16-le")).decode("ascii"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert json.loads(result.stdout.lstrip("\ufeff")) == expected


def test_local_startup_never_refreshes_existing_demo_credentials() -> None:
    source = STARTUP_SCRIPT.read_text(encoding="utf-8")

    assert "$env:USER_SYSTEM_DEMO_REFRESH = '0'" in source
    assert "$env:USER_SYSTEM_DEMO_REFRESH = '1'" not in source
    assert "$DemoPassword" not in source
    assert "PLATFORM_DEMO_PASSWORD" in source


def test_existing_account_smoke_does_not_depend_on_owner_password() -> None:
    source = STARTUP_SCRIPT.read_text(encoding="utf-8")

    assert "if ($SeedResult.Created)" in source
    assert "startup_probe_" in source
    assert "auth route accepted an invalid startup probe" in source


def test_core_startup_does_not_depend_on_external_account_snapshot() -> None:
    source = STARTUP_SCRIPT.read_text(encoding="utf-8")

    assert "/venue/account-snapshot?accountId=" not in source


@pytest.mark.parametrize(
    "running,platform_flag,runtime_flag,foreign,managed,expected",
    [
        (2, True, True, False, False, "True"),
        (2, False, False, False, False, "False"),
        (0, None, None, False, False, "False"),
        (1, True, True, False, False, "ERROR"),
        (2, True, False, False, False, "ERROR"),
        (2, None, True, False, False, "ERROR"),
        (2, True, True, True, False, "ERROR"),
        (2, True, True, True, True, "True"),
    ],
)
def test_restart_preserves_only_verified_running_mode(
    running, platform_flag, runtime_flag, foreign, managed, expected
):
    executable = shutil.which("powershell")
    if executable is None:
        pytest.skip("Windows PowerShell is unavailable")
    source = STARTUP_SCRIPT.read_text(encoding="utf-8")
    function = source[source.index("function Get-ExistingLiveWrite {"):source.index("function Read-State {")]
    def literal(value):
        return "$null" if value is None else "$true" if value else "$false"
    # Exercise the real resolver with fake listeners and HTTP responses. No
    # lifecycle entry point, real backend connection or process operation runs.
    script = f"""
$ErrorActionPreference = 'Stop'
$RepoRoot = 'test-root'
$Services = @(@{{Key='runtime';Port=8100;WorkingDirectory='test'}},@{{Key='api';Port=8000;WorkingDirectory='test'}})
function Get-PortListener($port) {{
  if ({running} -eq 2 -or ({running} -eq 1 -and $port -eq 8100)) {{ return @{{OwningProcess=1}} }}
}}
function Test-ProjectProcess {{ return {literal(not foreign)} }}
function Read-State {{
 if ({literal(managed)}) {{ return @{{repoRoot='test-root';services=@(@{{key='runtime';pid=1;workingDirectory='test'}},@{{key='api';pid=1;workingDirectory='test'}})}} }}
 return $null
}}
function Test-ServiceSignature {{ return {literal(managed)} }}
function Invoke-RestMethod {{
 param($Uri,$TimeoutSec)
 if ($Uri -like '*8100*') {{ return @{{capabilities=@{{liveWriteEnabled={literal(runtime_flag)}}}}} }}
 return @{{liveTradingEnabled={literal(platform_flag)}}}
}}
{function}
try {{ Write-Output (Get-ExistingLiveWrite) }} catch {{ Write-Output 'ERROR' }}
"""
    result = subprocess.run(
        [executable, "-NoProfile", "-EncodedCommand",
         base64.b64encode(script.encode("utf-16-le")).decode("ascii")],
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip() == expected


@pytest.mark.parametrize("action", ["status", "stop"])
def test_shortcut_delegates_to_canonical_lifecycle(tmp_path, action) -> None:
    executable = shutil.which("powershell")
    if executable is None:
        pytest.skip("Windows PowerShell is unavailable")
    wrapper = tmp_path / f"{action}-platform.ps1"
    shutil.copyfile(REPO_ROOT / "scripts" / wrapper.name, wrapper)
    # Replace only the test directory's canonical entry point. The stop shortcut
    # must dispatch the right action without touching any real process or state.
    (tmp_path / "dev-platform.ps1").write_text(
        "param([string]$Action)\n"
        "[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)\n"
        "@{action=$Action; extraArguments=@($args)} | ConvertTo-Json -Compress\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [executable, "-NoProfile", "-File", str(wrapper)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert json.loads(result.stdout.lstrip("\ufeff")) == {
        "action": action,
        "extraArguments": [],
    }
