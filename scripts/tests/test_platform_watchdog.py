"""Execute the watchdog with fake processes/network; never stop a real service."""

import base64
import json
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "live,foreign,expected", [(False, False, 1), (True, False, 0), (False, True, 0)]
)
def test_watchdog_recovery_is_bounded_and_respects_mode(
    tmp_path, live, foreign, expected
):
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell unavailable")
    source = Path(__file__).resolve().parents[1] / "platform-watchdog.ps1"
    script = (
        """
$ErrorActionPreference='Stop'
$RepoRoot='watchdog-isolated-test'
$StateDir='TEMP'
$EnableLiveWrite=LIVE
$Services=@(@{Key='runtime';Port=8100;WorkingDirectory='test'})
. 'SOURCE'
$script:count=0; $script:stops=0; $script:status=''
function Assert-Dependencies {}
function Read-State { return @{repoRoot=$RepoRoot;services=@(@{key='runtime';pid=100;workingDirectory='test'})} }
function Get-PortListener { return @{OwningProcess=LISTENER} }
function Test-ServiceSignature { return $true }
function Test-Health { return $false }
function Get-JsonFieldValue { return $EnableLiveWrite }
function Invoke-RestMethod { return @{accountSync=@{status='healthy'};crossExit=@{status='disabled'}} }
function Get-Process { return $null }
function Stop-ManagedPid { $script:stops++ }
function Start-ServiceManaged { return @{key='runtime';pid=100} }
function Write-State {}
function Write-WatchdogStatus { param($Status,$Reason,$Recoveries); $script:status=$Status }
function Start-Sleep { $script:count++; if ($script:count -ge 5) { throw 'finished' } }
try { Invoke-PlatformWatchdog } catch { if ($_.Exception.Message -ne 'finished') { throw } }
@{stops=$script:stops;status=$script:status} | ConvertTo-Json -Compress
""".replace("TEMP", str(tmp_path).replace("'", "''"))
        .replace("SOURCE", str(source).replace("'", "''"))
        .replace("LIVE", "$true" if live else "$false")
        .replace("LISTENER", "101" if foreign else "100")
    )
    result = subprocess.run(
        [
            executable,
            "-NoProfile",
            "-EncodedCommand",
            base64.b64encode(script.encode("utf-16-le")).decode(),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    data = json.loads(result.stdout)
    assert data["stops"] == expected
    assert data["status"] == ("blocked" if live or foreign else "degraded")
