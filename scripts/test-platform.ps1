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

function Invoke-CheckedNative {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string[]]$Arguments
  )

  & $FilePath @Arguments | Out-Host
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code $LASTEXITCODE: $FilePath $($Arguments -join ' ')"
  }
}

function Get-ProjectPython {
  param([Parameter(Mandatory = $true)][string]$ProjectPath)

  $VenvPath = Join-Path $ProjectPath '.venv'
  $PythonPath = Join-Path $VenvPath 'Scripts\python.exe'

  if (-not (Test-Path $PythonPath)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
      Invoke-CheckedNative -FilePath 'py' -Arguments @('-3.12', '-m', 'venv', $VenvPath)
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
      Invoke-CheckedNative -FilePath 'python' -Arguments @('-m', 'venv', $VenvPath)
    }
    else {
      throw 'Python was not found. Install Python 3.12 first.'
    }
  }

  if (-not $SkipInstall) {
    Push-Location $ProjectPath
    try {
      Invoke-CheckedNative -FilePath $PythonPath -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip')
      Invoke-CheckedNative -FilePath $PythonPath -Arguments @('-m', 'pip', 'install', '-e', '.[dev]')
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
    Invoke-CheckedNative -FilePath $PythonPath -Arguments @('-m', 'ruff', 'check', 'app', 'tests')
    Invoke-CheckedNative -FilePath $PythonPath -Arguments @('-m', 'pytest')
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
    Invoke-CheckedNative -FilePath 'corepack' -Arguments @('enable')
    Invoke-CheckedNative -FilePath 'corepack' -Arguments @('prepare', 'pnpm@8.1.0', '--activate')
    if (-not $SkipInstall) {
      Invoke-CheckedNative -FilePath 'pnpm' -Arguments @('install', '--frozen-lockfile')
    }
    Invoke-CheckedNative -FilePath 'pnpm' -Arguments @('type:check')
  }
  finally {
    Pop-Location
  }
}

Write-Host "`nAll requested checks passed." -ForegroundColor Green
