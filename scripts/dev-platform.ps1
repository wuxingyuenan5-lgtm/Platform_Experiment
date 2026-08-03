[CmdletBinding()]
param(
  [switch]$SkipInstall,
  [switch]$ForceInstall,
  [switch]$SkipFrontend,
  [int]$HealthTimeoutSeconds = 90
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$RuntimePath = Join-Path $RepoRoot 'execution-runtime'
$BackendPath = Join-Path $RepoRoot 'platform-api'
$FrontendPath = Join-Path $RepoRoot 'platform-web'
$FrontendPort = 4373

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

function Initialize-PythonProject {
  param(
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [string]$Extras = 'dev'
  )

  $VenvPath = Join-Path $ProjectPath '.venv'
  $PythonPath = Join-Path $VenvPath 'Scripts\python.exe'
  $InstallMarker = Join-Path $VenvPath '.platform-installed'
  $Created = $false

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
    $Created = $true
  }

  $NeedsInstall = -not $SkipInstall -and ($ForceInstall -or $Created -or -not (Test-Path $InstallMarker))
  if ($NeedsInstall) {
    Write-Host "Installing Python dependencies: $ProjectPath" -ForegroundColor Cyan
    Push-Location $ProjectPath
    try {
      Invoke-CheckedNative -FilePath $PythonPath -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip')
      Invoke-CheckedNative -FilePath $PythonPath -Arguments @('-m', 'pip', 'install', '-e', ".[${Extras}]")
      New-Item -ItemType File -Path $InstallMarker -Force | Out-Null
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

function Wait-ForHttp {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][int]$TimeoutSeconds
  )

  $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    try {
      $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
      if ($Response.StatusCode -ge 200 -and $Response.StatusCode -lt 500) {
        Write-Host "$Name ready: $Url" -ForegroundColor Green
        return
      }
    }
    catch {
      Start-Sleep -Seconds 1
    }
  } while ((Get-Date) -lt $Deadline)

  throw "$Name did not become ready within $TimeoutSeconds seconds: $Url"
}

$RuntimePython = Initialize-PythonProject -ProjectPath $RuntimePath -Extras 'dev,crypto'
$BackendPython = Initialize-PythonProject -ProjectPath $BackendPath -Extras 'dev'

$BackendEnv = Join-Path $BackendPath '.env'
$BackendEnvExample = Join-Path $BackendPath '.env.example'
if (-not (Test-Path $BackendEnv) -and (Test-Path $BackendEnvExample)) {
  Copy-Item $BackendEnvExample $BackendEnv
  Write-Host 'Created platform-api/.env from .env.example.' -ForegroundColor DarkGray
}

Start-ServiceWindow `
  -Title 'Platform Execution Runtime :8100' `
  -WorkingDirectory $RuntimePath `
  -Command "& '$RuntimePython' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8100"

Start-ServiceWindow `
  -Title 'Platform API :8000' `
  -WorkingDirectory $BackendPath `
  -Command "& '$BackendPython' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

if (-not $SkipFrontend) {
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw 'Node.js was not found. Install Node.js 20 or later first.'
  }
  if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    throw 'npx was not found. Use a Node.js installation that includes npm/npx.'
  }

  $Package = Get-Content (Join-Path $FrontendPath 'package.json') -Raw | ConvertFrom-Json
  $PnpmVersion = ($Package.packageManager -split '@')[-1]
  $PnpmPackage = "pnpm@$PnpmVersion"

  $FrontendEnv = Join-Path $FrontendPath '.env.local'
  $FrontendEnvExample = Join-Path $FrontendPath '.env.platform.example'
  if (-not (Test-Path $FrontendEnv) -and (Test-Path $FrontendEnvExample)) {
    Copy-Item $FrontendEnvExample $FrontendEnv
    Write-Host 'Created platform-web/.env.local from .env.platform.example.' -ForegroundColor DarkGray
  }

  $NodeModules = Join-Path $FrontendPath 'node_modules'
  if (-not $SkipInstall -and ($ForceInstall -or -not (Test-Path $NodeModules))) {
    Push-Location $FrontendPath
    try {
      Invoke-CheckedNative -FilePath 'npx' -Arguments @($PnpmPackage, 'install', '--frozen-lockfile')
    }
    finally {
      Pop-Location
    }
  }

  $VitePath = Join-Path $FrontendPath 'node_modules\.bin\vite.cmd'
  if (-not (Test-Path $VitePath)) {
    throw "Vite executable was not found: $VitePath. Run without -SkipInstall first."
  }

  Start-ServiceWindow `
    -Title "Platform Web :$FrontendPort" `
    -WorkingDirectory $FrontendPath `
    -Command "& '$VitePath' --host 127.0.0.1 --port $FrontendPort"
}

Wait-ForHttp -Name 'Platform Execution Runtime' -Url 'http://127.0.0.1:8100/health' -TimeoutSeconds $HealthTimeoutSeconds
Wait-ForHttp -Name 'Platform API' -Url 'http://127.0.0.1:8000/health' -TimeoutSeconds $HealthTimeoutSeconds
if (-not $SkipFrontend) {
  Wait-ForHttp -Name 'Platform Web' -Url "http://127.0.0.1:$FrontendPort/index.html" -TimeoutSeconds $HealthTimeoutSeconds
}

Write-Host ''
Write-Host 'Platform local services are ready.' -ForegroundColor Green
Write-Host 'Platform Execution Runtime: http://127.0.0.1:8100/health'
Write-Host 'Platform API:               http://127.0.0.1:8000/health'
if (-not $SkipFrontend) {
  Write-Host "Platform Web:               http://127.0.0.1:$FrontendPort/index.html"
}
Write-Host 'Safety defaults remain Simulation + Fake Gateway + Live Write disabled.' -ForegroundColor Yellow
