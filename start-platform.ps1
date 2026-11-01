[CmdletBinding()]
param(
  [ValidateRange(1, 180)][int]$HealthTimeoutSeconds = 90,
  [switch]$EnableLiveWrite
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$devPlatform = Join-Path $RepoRoot 'scripts\dev-platform.ps1'
if ($EnableLiveWrite) {
  & $devPlatform -HealthTimeoutSeconds $HealthTimeoutSeconds -EnableLiveWrite
} else {
  & $devPlatform -HealthTimeoutSeconds $HealthTimeoutSeconds
}
