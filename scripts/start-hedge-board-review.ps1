[CmdletBinding()]
param([ValidateRange(1, 180)][int]$HealthTimeoutSeconds = 90)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ApiRoot = Join-Path $RepoRoot 'platform-api'
$WebRoot = Join-Path $RepoRoot 'platform-web'
$StateDir = Join-Path $RepoRoot '.codex\hedge-board-review'
$StatePath = Join-Path $StateDir 'state.json'
$CredentialPath = Join-Path $StateDir 'login.txt'
$LogDir = Join-Path $StateDir 'logs'
$ApiPort = 18000
$WebPort = 14373
$ApiUrl = "http://127.0.0.1:$ApiPort"
$WebUrl = "http://127.0.0.1:$WebPort/#/hedge-board/macro"
$Python = Join-Path $ApiRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
  $Python = (Get-Command python -ErrorAction SilentlyContinue).Source
}
$Vite = Join-Path $WebRoot 'node_modules\.bin\vite.cmd'
$DatabasePath = Join-Path $RepoRoot '.e2e\hedge-board\review-platform.db'
$AvatarPath = Join-Path $RepoRoot '.e2e\hedge-board\review-avatars'
$DataRoot = 'D:\自营数据库\hedge-board'

function Get-PortListener {
  param([int]$Port)
  Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
}

function Test-ProjectProcess {
  param([int]$ProcessId, [string]$WorkingDirectory, [int]$Port = 0)
  $process = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
  if ($null -eq $process) { return $false }
  $commandLine = ([string]$process.CommandLine).ToLowerInvariant()
  return $commandLine.Contains($WorkingDirectory.ToLowerInvariant()) -or ($Port -gt 0 -and $commandLine.Contains('--port') -and $commandLine.Contains("$Port"))
}

function Wait-ForUrl {
  param([string]$Url, [int]$Port)
  $deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
      if ($response.StatusCode -eq 200 -and (Get-PortListener $Port)) { return }
    } catch { }
    Start-Sleep -Seconds 1
  }
  throw "Hedge Board review service failed to start: $Url. See $LogDir"
}

if (-not $Python -or -not (Test-Path -LiteralPath $Python)) { throw 'A Python runtime for Platform API is missing.' }
if (-not (Test-Path -LiteralPath $Vite)) { throw "Platform Web dependencies are missing: $Vite" }
if (-not (Test-Path -LiteralPath $DataRoot)) { throw "Local Hedge Board data is missing: $DataRoot" }
if (Get-PortListener $ApiPort) { throw "Review API port $ApiPort is already in use." }
if (Get-PortListener $WebPort) { throw "Review Web port $WebPort is already in use." }

New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $DatabasePath) -Force | Out-Null

$password = "Review!$([guid]::NewGuid().ToString('N').Substring(0, 16))Aa1"
$previousEnvironment = @{}
$reviewEnvironment = @{
  VG_DATABASE_PATH = $DatabasePath
  VG_AVATAR_DATA_DIRECTORY = $AvatarPath
  VG_CORS_ORIGINS = "http://127.0.0.1:$WebPort"
  VG_LIVE_TRADING_ENABLED = 'false'
  HEDGE_BOARD_DATA_ROOT = $DataRoot
  E2E_CEO_PASSWORD = $password
  VITE_PLATFORM_BACKEND_TARGET = $ApiUrl
  VITE_PLATFORM_API_BASE_URL = "$ApiUrl/api/v1"
}
foreach ($name in $reviewEnvironment.Keys) {
  $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
  [Environment]::SetEnvironmentVariable($name, $reviewEnvironment[$name], 'Process')
}

$started = @()
try {
  Push-Location $ApiRoot
  try { & $Python 'scripts\seed_hedge_board_e2e.py' } finally { Pop-Location }
  if ($LASTEXITCODE -ne 0) { throw 'Review account bootstrap failed.' }

  $apiOut = Join-Path $LogDir 'api.out.log'
  $apiErr = Join-Path $LogDir 'api.err.log'
  $apiProcess = Start-Process $Python -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$ApiPort") -WorkingDirectory $ApiRoot -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr -WindowStyle Hidden -PassThru
  $started += @{ Name = 'Review API'; LauncherPid = [int]$apiProcess.Id; Port = $ApiPort; WorkingDirectory = $ApiRoot }
  Wait-ForUrl "$ApiUrl/health" $ApiPort
  $started[-1].ListenerPid = [int](Get-PortListener $ApiPort).OwningProcess

  $webOut = Join-Path $LogDir 'web.out.log'
  $webErr = Join-Path $LogDir 'web.err.log'
  $webProcess = Start-Process $Vite -ArgumentList @('--host', '127.0.0.1', '--port', "$WebPort", '--strictPort') -WorkingDirectory $WebRoot -RedirectStandardOutput $webOut -RedirectStandardError $webErr -WindowStyle Hidden -PassThru
  $started += @{ Name = 'Review Web'; LauncherPid = [int]$webProcess.Id; Port = $WebPort; WorkingDirectory = $WebRoot }
  Wait-ForUrl "http://127.0.0.1:$WebPort/index.html" $WebPort
  $started[-1].ListenerPid = [int](Get-PortListener $WebPort).OwningProcess

  @{ repoRoot = $RepoRoot; updatedAt = (Get-Date).ToString('o'); services = @($started) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StatePath -Encoding UTF8
  @("Hedge Board 本地验收站", "网址：$WebUrl", '用户名：e2e_ceo', "密码：$password") | Set-Content -LiteralPath $CredentialPath -Encoding UTF8
} catch {
  foreach ($service in @($started)) {
    $listener = Get-PortListener ([int]$service.Port)
    if ($listener -and (Test-ProjectProcess ([int]$listener.OwningProcess) $service.WorkingDirectory ([int]$service.Port))) { Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue }
    if ($service.LauncherPid -and (Test-ProjectProcess ([int]$service.LauncherPid) $service.WorkingDirectory ([int]$service.Port))) { Stop-Process -Id $service.LauncherPid -Force -ErrorAction SilentlyContinue }
  }
  throw
} finally {
  foreach ($name in $reviewEnvironment.Keys) { [Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process') }
}

Write-Host 'Hedge Board 本地验收站已启动。' -ForegroundColor Green
Write-Host "网址：$WebUrl"
Write-Host '用户名：e2e_ceo'
Write-Host "密码：$password"
Write-Host "登录信息已保存：$CredentialPath"
Start-Process notepad.exe -ArgumentList @($CredentialPath)
Start-Process $WebUrl
