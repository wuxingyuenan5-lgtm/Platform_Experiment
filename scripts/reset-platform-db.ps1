[CmdletBinding()]
param([switch]$Force)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$DatabaseBasePath = Join-Path $RepoRoot 'platform-backend\data\platform.db'
$DatabaseFiles = @(
  $DatabaseBasePath,
  "$DatabaseBasePath-wal",
  "$DatabaseBasePath-shm"
)
$ExistingFiles = $DatabaseFiles | Where-Object { Test-Path $_ }

if (-not $ExistingFiles) {
  Write-Host 'No platform database files were found.' -ForegroundColor Yellow
  exit 0
}

if (-not $Force) {
  $Answer = Read-Host 'Delete the local platform database and all simulated orders, fills, positions and PnL? (y/N)'
  if ($Answer -notin @('y', 'Y', 'yes', 'YES')) {
    Write-Host 'Database reset cancelled.' -ForegroundColor Yellow
    exit 0
  }
}

foreach ($File in $ExistingFiles) {
  try {
    Remove-Item $File -Force
    Write-Host "Deleted: $File" -ForegroundColor DarkGray
  }
  catch {
    throw "Could not delete $File. Stop platform-backend before resetting the database. $($_.Exception.Message)"
  }
}

Write-Host 'Platform database reset complete. It will be recreated when platform-backend starts.' -ForegroundColor Green
