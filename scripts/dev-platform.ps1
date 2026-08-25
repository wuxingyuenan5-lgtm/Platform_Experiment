[CmdletBinding()]
param([ValidateRange(1, 180)][int]$HealthTimeoutSeconds = 90)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$StateDir = Join-Path $RepoRoot '.codex\dev-platform'
$StatePath = Join-Path $StateDir 'platform-dev-state.json'
$LogDir = Join-Path $StateDir 'logs'
$Services = @(
  @{ Name = 'Execution Runtime'; Port = 8100; HealthUrl = 'http://127.0.0.1:8100/health'; WorkingDirectory = (Join-Path $RepoRoot 'execution-runtime'); Python = $true; ContractChecks = @(
      @{ Url = 'http://127.0.0.1:8100/status'; JsonField = 'status'; Expected = 'available' },
      @{ Url = 'http://127.0.0.1:8100/status'; JsonField = 'capabilities.liveWriteEnabled'; Expected = $false },
      @{ Url = 'http://127.0.0.1:8100/venue/account-snapshot?accountId=bybit-live-main'; AcceptStatus = @(200, 503) }
    ) },
  @{ Name = 'Platform API'; Port = 8000; HealthUrl = 'http://127.0.0.1:8000/health'; WorkingDirectory = (Join-Path $RepoRoot 'platform-api'); Python = $true; ContractChecks = @(
      @{ Url = 'http://127.0.0.1:8000/api/v1/strategies/management-overview'; AcceptStatus = @(200) },
      @{ Url = 'http://127.0.0.1:8000/api/v1/ops/venue-snapshots/status'; AcceptStatus = @(200) }
    ) },
  @{ Name = 'Platform Web'; Port = 4373; HealthUrl = 'http://127.0.0.1:4373/index.html'; WorkingDirectory = (Join-Path $RepoRoot 'platform-web'); Python = $false }
)

function Get-PortListener { param([int]$Port) Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 }
function Test-Health {
  param([hashtable]$Service)
  try {
    $response = Invoke-WebRequest -Uri $Service.HealthUrl -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    if ($response.StatusCode -ne 200) { return $false }
    if ($Service.Python) { return (($response.Content | ConvertFrom-Json).status -eq 'ok') }
    return $response.Content -match 'id="htmlRoot"|vite|/src/main'
  } catch { return $false }
}
function Test-Contracts {
  param([hashtable]$Service)
  foreach ($check in @($Service.ContractChecks)) {
    try {
      $response = Invoke-WebRequest -Uri $check.Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
      if ($check.AcceptStatus -and (@($check.AcceptStatus) -notcontains [int]$response.StatusCode)) { return $false }
      if ($check.JsonField) {
        $payload = $response.Content | ConvertFrom-Json
        $current = $payload
        foreach ($segment in ($check.JsonField -split '\.')) {
          if ($null -eq $current) { return $false }
          $current = $current.$segment
        }
        if ($current -ne $check.Expected) { return $false }
      }
    } catch {
      $statusCode = [int]($_.Exception.Response.StatusCode.value__ 2>$null)
      if (-not $check.AcceptStatus -or (@($check.AcceptStatus) -notcontains $statusCode)) { return $false }
    }
  }
  return $true
}
function Wait-ForHealth {
  param([hashtable]$Service)
  $deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    if ((Get-PortListener $Service.Port) -and (Test-Health $Service) -and (Test-Contracts $Service)) { return }
    Start-Sleep -Seconds 1
  }
  throw "$($Service.Name) failed startup contract checks on port $($Service.Port). Logs: $($Service.Stdout); $($Service.Stderr)"
}
function Assert-Dependencies {
  param([hashtable]$Service)
  if ($Service.Python) {
    $python = Join-Path $Service.WorkingDirectory '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) { throw "$($Service.Name) Python environment is missing: $python. Create it and install this project's dependencies before running start-platform.ps1." }
    & $python -c 'import fastapi, uvicorn'
    if ($LASTEXITCODE -ne 0) { throw "$($Service.Name) Python dependencies are missing in $python. Install this project's dependencies before running start-platform.ps1." }
    $Service.PythonPath = $python
  } else {
    if (-not (Get-Command node -ErrorAction SilentlyContinue) -or -not (Get-Command pnpm -ErrorAction SilentlyContinue)) { throw 'Platform Web requires Node.js and pnpm. Install the versions declared in platform-web/package.json before running start-platform.ps1.' }
    $vite = Join-Path $Service.WorkingDirectory 'node_modules\.bin\vite.cmd'
    if (-not (Test-Path $vite)) { throw "Platform Web dependencies are missing: $vite. Run pnpm install in platform-web before running start-platform.ps1." }
    $Service.VitePath = $vite
  }
}
function Start-Service {
  param([hashtable]$Service)
  $safeName = $Service.Name.ToLowerInvariant().Replace(' ', '-')
  $Service.Stdout = Join-Path $LogDir "$safeName.out.log"
  $Service.Stderr = Join-Path $LogDir "$safeName.err.log"
  $existing = Get-PortListener $Service.Port
  if ($existing) {
    if ((Test-Health $Service) -and (Test-Contracts $Service)) {
      throw "$($Service.Name) cannot start: port $($Service.Port) is already in use by an already-healthy process (PID $($existing.OwningProcess))."
    }
    throw "$($Service.Name) cannot start: port $($Service.Port) is occupied by PID $($existing.OwningProcess), but the current process fails health or contract checks. Stop the stale process first. Logs: $($Service.Stdout); $($Service.Stderr)"
  }
  if ($Service.Python) {
    $process = Start-Process $Service.PythonPath -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$($Service.Port)") -WorkingDirectory $Service.WorkingDirectory -RedirectStandardOutput $Service.Stdout -RedirectStandardError $Service.Stderr -WindowStyle Hidden -PassThru
  } else {
    $process = Start-Process $Service.VitePath -ArgumentList @('--host', '127.0.0.1', '--port', "$($Service.Port)") -WorkingDirectory $Service.WorkingDirectory -RedirectStandardOutput $Service.Stdout -RedirectStandardError $Service.Stderr -WindowStyle Hidden -PassThru
  }
  $Service.LauncherPid = [int]$process.Id
  Wait-ForHealth $Service
  $Service.ListenerPid = [int](Get-PortListener $Service.Port).OwningProcess
}
function Test-ProjectProcess {
  param([int]$ProcessId, [string]$WorkingDirectory)
  $process = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
  return $null -ne $process -and ([string]$process.CommandLine).ToLowerInvariant().Contains($WorkingDirectory.ToLowerInvariant())
}
function Remove-StaleStateFile {
  if (-not (Test-Path $StatePath)) { return }
  try {
    $state = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
    if ($state.repoRoot -ne $RepoRoot) { return }
    foreach ($record in @($state.services)) {
      $definition = @($Services | Where-Object { [int]$_.Port -eq [int]$record.port -and $_.WorkingDirectory -eq $record.workingDirectory })[0]
      $listener = if ($definition) { Get-PortListener ([int]$record.port) } else { $null }
      if ($definition -and $record.ownership -eq 'managed' -and $listener -and [int]$listener.OwningProcess -eq [int]$record.listenerPid -and (Test-ProjectProcess $record.listenerPid $definition.WorkingDirectory)) {
        return
      }
    }
  } catch {
    Write-Warning "Removing unreadable platform state file: $StatePath"
  }
  Remove-Item -LiteralPath $StatePath -Force
  Write-Host 'Removed stale platform state file with no verifiable managed listener.' -ForegroundColor DarkYellow
}
function Stop-StartedService {
  param([hashtable]$Service)
  $listener = Get-PortListener $Service.Port
  if ($listener -and [int]$listener.OwningProcess -eq [int]$Service.ListenerPid -and (Test-ProjectProcess $Service.ListenerPid $Service.WorkingDirectory)) {
    Stop-Process -Id $Service.ListenerPid -Force -ErrorAction SilentlyContinue
  }
  if ($Service.LauncherPid -gt 0 -and $Service.LauncherPid -ne $Service.ListenerPid -and (Test-ProjectProcess $Service.LauncherPid $Service.WorkingDirectory)) {
    Stop-Process -Id $Service.LauncherPid -Force -ErrorAction SilentlyContinue
  }
}

New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
Remove-StaleStateFile
foreach ($service in $Services) { Assert-Dependencies $service }
$started = @()
$wroteState = $false
$currentService = $null
try {
  foreach ($service in $Services) {
    $currentService = $service
    Start-Service $service
    $started += $service
  }
  foreach ($service in $started) { $service.ownership = 'managed' }
  @{ repoRoot = $RepoRoot; updatedAt = (Get-Date).ToString('o'); services = @($started) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StatePath -Encoding UTF8
  $wroteState = $true
} catch {
  $webFailed = $null -ne $currentService -and $currentService.Name -eq 'Platform Web'
  if ($webFailed -and $started.Count -gt 0) {
    foreach ($service in $started) { $service.ownership = 'managed' }
    @{ repoRoot = $RepoRoot; updatedAt = (Get-Date).ToString('o'); services = @($started) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StatePath -Encoding UTF8
    throw "Startup partially succeeded: Platform Web failed, but healthy services were kept running. Healthy: $((@($started | ForEach-Object Name)) -join ', '). Failure: $($_.Exception.Message)"
  }
  foreach ($service in @($started | Sort-Object { $_.Port })) { Stop-StartedService $service }
  if ($wroteState -and (Test-Path $StatePath)) { Remove-Item -LiteralPath $StatePath -Force }
  Remove-StaleStateFile
  throw "Startup failed; services started by this attempt were stopped. $($_.Exception.Message)"
}

Write-Host 'Platform local services are ready.' -ForegroundColor Green
Write-Host 'Execution Runtime: http://127.0.0.1:8100/health'
Write-Host 'Platform API:      http://127.0.0.1:8000/health'
Write-Host 'Platform Web:      http://127.0.0.1:4373/index.html'
Write-Host 'Platform Web API:  http://127.0.0.1:8000/api/v1'
