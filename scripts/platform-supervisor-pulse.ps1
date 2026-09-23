[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$StateDir = Join-Path $RepoRoot '.codex\dev-platform'
$LogPath = Join-Path $StateDir 'supervisor-pulse.log'
$ScriptPath = Join-Path $PSScriptRoot 'dev-platform.ps1'
New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
$running = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
  $_.CommandLine -and
  $_.CommandLine.Contains($ScriptPath) -and
  $_.CommandLine -match '-Action\s+supervisor'
})
if ($running.Count -gt 0) { exit 0 }

$stamp = (Get-Date).ToString('o')
Add-Content -LiteralPath $LogPath -Value "$stamp supervisor missing; launching" -Encoding UTF8
Start-ScheduledTask -TaskName 'Global Variable Platform Supervisor'
