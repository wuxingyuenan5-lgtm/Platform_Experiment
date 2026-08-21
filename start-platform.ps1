[CmdletBinding()]
param([ValidateRange(1, 180)][int]$HealthTimeoutSeconds = 90)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $RepoRoot 'scripts\dev-platform.ps1') -HealthTimeoutSeconds $HealthTimeoutSeconds
