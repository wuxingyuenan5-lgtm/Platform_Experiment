[CmdletBinding()]
param(
  [switch]$SkipInstall,
  [switch]$SkipFrontend
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$RuntimePath = Join-Path $RepoRoot 'execution-runtime'
$BackendPath = Join-Path $RepoRoot 'platform-backend'
$FrontendPath = Join-Path $RepoRoot 'admin-risk'

function Get-ProjectPython {
  param([Parameter(Mandatory = $true)][string]$ProjectPath)

  $VenvPath = Join-Path $ProjectPath '.venv'
  $PythonPath = Join-Path $VenvPath 'Scripts\python.exe'

  if (-not (Test-Path $PythonPath)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
      & py -3.12 -m venv $VenvPath
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
      & python -m venv $VenvPath
    }
    else {
      throw 'Python was not found. Install Python 3.12 first.'
    }
  }

  if (-not $SkipInstall) {
    Push-Location $ProjectPath
    try {
      & $PythonPath -m pip install --upgrade pip
      & $PythonPath -m pip install -e '.[dev]'
    }
    finally {
      Pop-Location
    }
  }

  return $PythonPath
}

function Test-PythonProject {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$ProjectPath
  )

  Write-Host "`n[$Name]" -ForegroundColor Cyan
  $PythonPath = Get-ProjectPython -ProjectPath $ProjectPath
  Push-Location $ProjectPath
  try {
    & $PythonPath -m ruff check app tests
    & $PythonPath -m pytest
  }
  finally {
    Pop-Location
  }
}

Test-PythonProject -Name 'Execution Runtime' -ProjectPath $RuntimePath
Test-PythonProject -Name 'Platform Backend' -ProjectPath $BackendPath

if (-not $SkipFrontend) {
  Write-Host "`n[Frontend Type Check]" -ForegroundColor Cyan
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw 'Node.js was not found. Install Node.js 20 or later first.'
  }
  if (-not (Get-Command corepack -ErrorAction SilentlyContinue)) {
    throw 'Corepack was not found.'
  }

  Push-Location $FrontendPath
  try {
    & corepack enable
    & corepack prepare pnpm@8.1.0 --activate
    if (-not $SkipInstall) {
      & pnpm install --frozen-lockfile
    }
    & pnpm type:check
  }
  finally {
    Pop-Location
  }
}

Write-Host "`nAll requested checks passed." -ForegroundColor Green
