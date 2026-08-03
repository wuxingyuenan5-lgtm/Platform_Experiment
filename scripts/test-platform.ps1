[CmdletBinding()]
param(
  [switch]$SkipInstall,
  [switch]$SkipFrontend
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$RuntimePath = Join-Path $RepoRoot 'execution-runtime'
$BackendPath = Join-Path $RepoRoot 'platform-api'
$FrontendPath = Join-Path $RepoRoot 'platform-web'

function Invoke-CheckedNative {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string[]]$Arguments
  )

  & $FilePath @Arguments | Out-Host
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
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

Test-PythonProject -Name 'Platform Execution Runtime' -ProjectPath $RuntimePath
Test-PythonProject -Name 'Platform API' -ProjectPath $BackendPath

if (-not $SkipFrontend) {
  Write-Host "`n[Frontend Type Check]" -ForegroundColor Cyan
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw 'Node.js was not found. Install Node.js 20 or later first.'
  }
  if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    throw 'npx was not found. Use a Node.js installation that includes npm/npx.'
  }

  Push-Location $FrontendPath
  try {
    $Package = Get-Content (Join-Path $FrontendPath 'package.json') -Raw | ConvertFrom-Json
    $PnpmPackage = $Package.packageManager
    if (-not $SkipInstall) {
      Invoke-CheckedNative -FilePath 'npx' -Arguments @($PnpmPackage, 'install', '--frozen-lockfile')
    }
    Invoke-CheckedNative -FilePath 'npx' -Arguments @($PnpmPackage, 'type:check')
  }
  finally {
    Pop-Location
  }
}

Write-Host "`nAll requested checks passed." -ForegroundColor Green
