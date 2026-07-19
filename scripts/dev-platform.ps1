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

function New-PythonEnvironment {
  param([Parameter(Mandatory = $true)][string]$ProjectPath)

  $VenvPath = Join-Path $ProjectPath '.venv'
  $PythonPath = Join-Path $VenvPath 'Scripts\python.exe'

  if (-not (Test-Path $PythonPath)) {
    Write-Host "Creating Python 3.12 environment: $ProjectPath" -ForegroundColor Cyan
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
    Write-Host "Installing dependencies: $ProjectPath" -ForegroundColor Cyan
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

function Start-ServiceWindow {
  param(
    [Parameter(Mandatory = $true)][string]$Title,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [Parameter(Mandatory = $true)][string]$Command
  )

  $WindowCommand = "`$Host.UI.RawUI.WindowTitle = '$Title'; Set-Location '$WorkingDirectory'; $Command"
  Start-Process -FilePath 'powershell.exe' -ArgumentList @(
    '-NoExit',
    '-ExecutionPolicy', 'Bypass',
    '-Command', $WindowCommand
  ) | Out-Null
}

$RuntimePython = New-PythonEnvironment -ProjectPath $RuntimePath
$BackendPython = New-PythonEnvironment -ProjectPath $BackendPath

$BackendEnv = Join-Path $BackendPath '.env'
$BackendEnvExample = Join-Path $BackendPath '.env.example'
if (-not (Test-Path $BackendEnv) -and (Test-Path $BackendEnvExample)) {
  Copy-Item $BackendEnvExample $BackendEnv
  Write-Host 'Created platform-backend/.env from .env.example.' -ForegroundColor DarkGray
}

Start-ServiceWindow `
  -Title 'Variable-Global Execution Runtime :8100' `
  -WorkingDirectory $RuntimePath `
  -Command "& '$RuntimePython' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8100"

Start-ServiceWindow `
  -Title 'Variable-Global Platform Backend :8000' `
  -WorkingDirectory $BackendPath `
  -Command "& '$BackendPython' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

if (-not $SkipFrontend) {
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw 'Node.js was not found. Install Node.js 20 or later first.'
  }
  if (-not (Get-Command corepack -ErrorAction SilentlyContinue)) {
    throw 'Corepack was not found. Use a Node.js installation that includes Corepack.'
  }

  $FrontendEnv = Join-Path $FrontendPath '.env.local'
  $FrontendEnvExample = Join-Path $FrontendPath '.env.platform.example'
  if (-not (Test-Path $FrontendEnv) -and (Test-Path $FrontendEnvExample)) {
    Copy-Item $FrontendEnvExample $FrontendEnv
    Write-Host 'Created admin-risk/.env.local from .env.platform.example.' -ForegroundColor DarkGray
  }

  if (-not $SkipInstall) {
    Push-Location $FrontendPath
    try {
      Invoke-CheckedNative -FilePath 'corepack' -Arguments @('enable')
      Invoke-CheckedNative -FilePath 'corepack' -Arguments @('prepare', 'pnpm@8.1.0', '--activate')
      Invoke-CheckedNative -FilePath 'pnpm' -Arguments @('install', '--frozen-lockfile')
    }
    finally {
      Pop-Location
    }
  }

  Start-ServiceWindow `
    -Title 'Variable-Global Frontend :5173' `
    -WorkingDirectory $FrontendPath `
    -Command 'corepack pnpm dev -- --host 127.0.0.1 --port 5173'
}

Write-Host ''
Write-Host 'Development services were opened in separate PowerShell windows.' -ForegroundColor Green
Write-Host 'Runtime:  http://127.0.0.1:8100/health'
Write-Host 'Backend:  http://127.0.0.1:8000/health'
if (-not $SkipFrontend) {
  Write-Host 'Frontend: http://127.0.0.1:5173'
}
