[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot 'platform-api/.venv/Scripts/python.exe'
& $Python -m pytest (Join-Path $PSScriptRoot 'tests/test_dev_platform_auth_safety.py') -q
if ($LASTEXITCODE -ne 0) { throw 'Platform lifecycle checks failed.' }
Write-Host 'Platform lifecycle checks passed.' -ForegroundColor Green
