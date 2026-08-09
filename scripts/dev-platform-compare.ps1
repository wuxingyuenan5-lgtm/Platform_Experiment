[CmdletBinding()]
param(
  [switch]$SkipInstall,
  [switch]$ForceInstall,
  [string]$LegacyFrontendPath = $env:VG_LEGACY_FRONTEND_PATH,
  [int]$HealthTimeoutSeconds = 90
)

$ErrorActionPreference = 'Stop'
$ScriptPath = Join-Path $PSScriptRoot 'dev-platform.ps1'
& $ScriptPath `
  -SkipInstall:$SkipInstall `
  -ForceInstall:$ForceInstall `
  -WithLegacyFrontend `
  -LegacyFrontendPath $LegacyFrontendPath `
  -HealthTimeoutSeconds $HealthTimeoutSeconds
