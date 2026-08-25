[CmdletBinding()]
param(
  [ValidateSet('start', 'status', 'stop', 'restart')][string]$Action = 'start',
  [ValidateRange(1, 180)][int]$HealthTimeoutSeconds = 90
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$StateDir = Join-Path $RepoRoot '.codex\dev-platform'
$StatePath = Join-Path $StateDir 'platform-dev-state.json'
$LogDir = Join-Path $StateDir 'logs'
$ContractVersion = '2026-08-25.dev-platform.v2'
$DemoUsername = 'demo_ceo'
$DemoPassword = 'Demo-Accounts!2026'
$Services = @(
  @{
    Key = 'runtime'; Name = 'Execution Runtime'; Port = 8100; HealthUrl = 'http://127.0.0.1:8100/health';
    WorkingDirectory = (Join-Path $RepoRoot 'execution-runtime'); Python = $true;
    ContractChecks = @(
      @{ Url = 'http://127.0.0.1:8100/status'; JsonField = 'status'; Expected = 'available' },
      @{ Url = 'http://127.0.0.1:8100/status'; JsonField = 'capabilities.liveWriteEnabled'; Expected = $false },
      @{ Url = 'http://127.0.0.1:8100/venue/account-snapshot?accountId=bybit-live-main'; AcceptStatus = @(200, 503) }
    )
  },
  @{
    Key = 'api'; Name = 'Platform API'; Port = 8000; HealthUrl = 'http://127.0.0.1:8000/health';
    WorkingDirectory = (Join-Path $RepoRoot 'platform-api'); Python = $true;
    ContractChecks = @(
      @{ Url = 'http://127.0.0.1:8000/api/v1/auth/login'; AcceptStatus = @(200, 401, 405, 422) },
      @{ Url = 'http://127.0.0.1:8000/api/v1/strategies/management-overview'; AcceptStatus = @(200) },
      @{ Url = 'http://127.0.0.1:8000/api/v1/ops/venue-snapshots/status'; AcceptStatus = @(200) }
    )
  },
  @{
    Key = 'web'; Name = 'Platform Web'; Port = 4373; HealthUrl = 'http://127.0.0.1:4373/index.html';
    WorkingDirectory = (Join-Path $RepoRoot 'platform-web'); Python = $false;
    ContractChecks = @(
      @{ Url = 'http://127.0.0.1:4373/index.html'; ContentPattern = 'id="htmlRoot"|/src/main|assets/' }
    )
  }
)

function New-ServiceRecord {
  param([hashtable]$Service, [string]$Ownership, [int]$ProcessId)
  return [ordered]@{
    key = $Service.Key
    name = $Service.Name
    port = $Service.Port
    healthUrl = $Service.HealthUrl
    workingDirectory = $Service.WorkingDirectory
    ownership = $Ownership
    pid = $ProcessId
    startedAt = (Get-Date).ToString('o')
    contractVersion = $ContractVersion
  }
}

function Get-PortListener { param([int]$Port) Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 }

function Get-JsonFieldValue {
  param($Payload, [string]$Path)
  $current = $Payload
  foreach ($segment in ($Path -split '\.')) {
    if ($null -eq $current) { return $null }
    $current = $current.$segment
  }
  return $current
}

function Test-ProjectProcess {
  param([int]$ProcessId, [string]$WorkingDirectory)
  $process = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
  if ($null -eq $process) { return $false }
  return ([string]$process.CommandLine).ToLowerInvariant().Contains($WorkingDirectory.ToLowerInvariant())
}

function Get-ProcessCommandLine {
  param([int]$ProcessId)
  $process = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
  if ($null -eq $process) { return '' }
  return [string]$process.CommandLine
}

function Test-ServiceSignature {
  param([hashtable]$Service, [int]$ProcessId)
  $commandLine = (Get-ProcessCommandLine $ProcessId).ToLowerInvariant()
  if ([string]::IsNullOrWhiteSpace($commandLine)) { return $false }
  if ($Service.Python) {
    return $commandLine.Contains('uvicorn app.main:app') -and $commandLine.Contains("--port $($Service.Port)")
  }
  return $commandLine.Contains('vite') -and $commandLine.Contains("--port $($Service.Port)")
}

function Test-ExpectedRuntime {
  param([hashtable]$Service, [int]$ProcessId)
  if (-not $Service.Python) { return $true }
  $process = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
  if ($null -eq $process) { return $false }
  $executablePath = ([string]$process.ExecutablePath).ToLowerInvariant()
  if ($Service.PythonPath -and $executablePath -eq $Service.PythonPath.ToLowerInvariant()) {
    return $true
  }
  return (Test-ServiceSignature $Service $ProcessId)
}

function Invoke-ServiceRequest {
  param([string]$Url)
  return Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
}

function Test-Health {
  param([hashtable]$Service)
  try {
    $response = Invoke-ServiceRequest $Service.HealthUrl
    if ($response.StatusCode -ne 200) { return $false }
    if ($Service.Python) { return (($response.Content | ConvertFrom-Json).status -eq 'ok') }
    return $response.Content -match 'id="htmlRoot"|vite|/src/main|assets/'
  } catch { return $false }
}

function Test-Contracts {
  param([hashtable]$Service)
  foreach ($check in @($Service.ContractChecks)) {
    try {
      $response = Invoke-ServiceRequest $check.Url
      if ($check.AcceptStatus -and (@($check.AcceptStatus) -notcontains [int]$response.StatusCode)) { return $false }
      if ($check.JsonField) {
        $payload = $response.Content | ConvertFrom-Json
        if ((Get-JsonFieldValue $payload $check.JsonField) -ne $check.Expected) { return $false }
      }
      if ($check.ContentPattern -and ($response.Content -notmatch $check.ContentPattern)) { return $false }
    } catch {
      $statusCode = [int]($_.Exception.Response.StatusCode.value__ 2>$null)
      if (-not $check.AcceptStatus -or (@($check.AcceptStatus) -notcontains $statusCode)) { return $false }
    }
  }
  return $true
}

function Assert-Dependencies {
  param([hashtable]$Service)
  if ($Service.Python) {
    $python = Join-Path $Service.WorkingDirectory '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) { throw "$($Service.Name) Python environment is missing: $python" }
    & $python -c 'import fastapi, uvicorn'
    if ($LASTEXITCODE -ne 0) { throw "$($Service.Name) Python dependencies are missing in $python" }
    $Service.PythonPath = $python
  } else {
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js is required for Platform Web' }
    $pnpm = Get-Command corepack -ErrorAction SilentlyContinue
    if ($null -eq $pnpm) { throw 'corepack is required for Platform Web' }
    $vite = Join-Path $Service.WorkingDirectory 'node_modules\.bin\vite.cmd'
    if (-not (Test-Path $vite)) { throw "Platform Web dependencies are missing: $vite" }
    $Service.VitePath = $vite
  }
}

function Invoke-DemoUserSeed {
  $seedScript = Join-Path $RepoRoot 'platform-api\scripts\seed_user_system_demo.py'
  if (-not (Test-Path $seedScript)) { return }
  $platformApi = @($Services | Where-Object { $_.Key -eq 'api' })[0]
  if ($null -eq $platformApi) { return }
  Assert-Dependencies $platformApi
  $previous = @{
    VG_LIVE_TRADING_ENABLED = $env:VG_LIVE_TRADING_ENABLED
    USER_SYSTEM_DEMO_SEED = $env:USER_SYSTEM_DEMO_SEED
    USER_SYSTEM_DEMO_PASSWORD = $env:USER_SYSTEM_DEMO_PASSWORD
    USER_SYSTEM_DEMO_REFRESH = $env:USER_SYSTEM_DEMO_REFRESH
  }
  try {
    $env:VG_LIVE_TRADING_ENABLED = 'false'
    $env:USER_SYSTEM_DEMO_SEED = '1'
    $env:USER_SYSTEM_DEMO_PASSWORD = $DemoPassword
    $env:USER_SYSTEM_DEMO_REFRESH = '1'
    & $platformApi.PythonPath $seedScript | Out-Null
    if ($LASTEXITCODE -ne 0) {
      throw 'Reusable demo account seeding failed.'
    }
  } finally {
    foreach ($entry in $previous.GetEnumerator()) {
      if ($null -eq $entry.Value) {
        Remove-Item "Env:$($entry.Key)" -ErrorAction SilentlyContinue
      } else {
        Set-Item "Env:$($entry.Key)" $entry.Value
      }
    }
  }
}

function Wait-ForHealth {
  param([hashtable]$Service)
  $deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    $listener = Get-PortListener $Service.Port
    if ($listener -and (Test-Health $Service) -and (Test-Contracts $Service)) {
      return [int]$listener.OwningProcess
    }
    Start-Sleep -Seconds 1
  }
  throw "$($Service.Name) failed startup contract checks on port $($Service.Port)"
}

function Read-State {
  if (-not (Test-Path $StatePath)) { return $null }
  try { return Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json } catch { return $null }
}

function Write-State {
  param([array]$ServiceRecords)
  New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
  New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
  @{
    repoRoot = $RepoRoot
    contractVersion = $ContractVersion
    updatedAt = (Get-Date).ToString('o')
    services = $ServiceRecords
  } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $StatePath -Encoding UTF8
}

function Stop-ManagedPid {
  param([int]$ProcessId, [string]$WorkingDirectory, [hashtable]$Service = $null)
  if ($ProcessId -le 0) { return }
  $replaceable = (Test-ProjectProcess $ProcessId $WorkingDirectory)
  if (-not $replaceable -and $null -ne $Service) {
    $replaceable = Test-ServiceSignature $Service $ProcessId
  }
  if (-not $replaceable) { return }
  Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Stop-ManagedServices {
  $state = Read-State
  if ($null -eq $state -or $state.repoRoot -ne $RepoRoot) { return }
  foreach ($record in @($state.services)) {
    $definition = @($Services | Where-Object { $_.Key -eq $record.key })[0]
    if ($null -eq $definition) { continue }
    Stop-ManagedPid -ProcessId ([int]$record.pid) -WorkingDirectory $definition.WorkingDirectory -Service $definition
  }
  if (Test-Path $StatePath) { Remove-Item -LiteralPath $StatePath -Force }
}

function Get-ServiceStatusRecord {
  param([hashtable]$Service, $ExistingState)
  $listener = Get-PortListener $Service.Port
  $servicePid = if ($listener) { [int]$listener.OwningProcess } else { 0 }
  $belongs = $servicePid -gt 0 -and (
    (Test-ProjectProcess $servicePid $Service.WorkingDirectory) -or
    (Test-ServiceSignature $Service $servicePid)
  )
  $healthy = $listener -and (Test-Health $Service)
  $contract = $listener -and (Test-Contracts $Service)
  $stateRecord = $null
  if ($ExistingState -and $ExistingState.services) {
    $stateRecord = @($ExistingState.services | Where-Object { $_.key -eq $Service.Key })[0]
  }
  [ordered]@{
    key = $Service.Key
    name = $Service.Name
    port = $Service.Port
    pid = $servicePid
    belongsToRepo = $belongs
    healthy = [bool]$healthy
    contractMatched = [bool]$contract
    managed = ($null -ne $stateRecord -and [int]$stateRecord.pid -eq $servicePid)
    expectedRuntime = ($servicePid -gt 0 -and (Test-ExpectedRuntime $Service $servicePid))
    stateStartedAt = if ($stateRecord) { $stateRecord.startedAt } else { $null }
    contractVersion = if ($stateRecord) { $stateRecord.contractVersion } else { $null }
  }
}

function Show-Status {
  foreach ($service in $Services) {
    try { Assert-Dependencies $service } catch {}
  }
  $state = Read-State
  $records = @()
  foreach ($service in $Services) {
    $records += Get-ServiceStatusRecord -Service $service -ExistingState $state
  }
  $records | ConvertTo-Json -Depth 5
}

function Invoke-LoginSmoke {
  $headers = @{ Origin = 'http://127.0.0.1:4373' }
  $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
  $body = @{ username = $DemoUsername; password = $DemoPassword } | ConvertTo-Json
  $login = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/auth/login' -Method Post `
    -Headers $headers -WebSession $session -ContentType 'application/json' -Body $body -UseBasicParsing
  if ($login.StatusCode -ne 200) {
    throw 'Platform API login smoke check failed.'
  }
  $me = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/auth/me' -Headers $headers -WebSession $session -UseBasicParsing
  if ($me.StatusCode -ne 200) {
    throw 'Platform API auth/me smoke check failed.'
  }
  $overview = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/strategies/management-overview' `
    -Headers $headers -WebSession $session -UseBasicParsing
  if ($overview.StatusCode -ne 200) {
    throw 'Platform API management overview smoke check failed.'
  }
}

function Start-ServiceManaged {
  param([hashtable]$Service)
  $safeName = $Service.Name.ToLowerInvariant().Replace(' ', '-')
  $stdout = Join-Path $LogDir "$safeName.out.log"
  $stderr = Join-Path $LogDir "$safeName.err.log"
  $listener = Get-PortListener $Service.Port
  if ($listener) {
    $servicePid = [int]$listener.OwningProcess
    $repoService = (Test-ProjectProcess $servicePid $Service.WorkingDirectory) -or (Test-ServiceSignature $Service $servicePid)
    if (-not $repoService) {
      throw "$($Service.Name) port $($Service.Port) is occupied by a non-project process (PID $servicePid)"
    }
    $expectedRuntime = Test-ExpectedRuntime $Service $servicePid
    if ((Test-Health $Service) -and (Test-Contracts $Service) -and $expectedRuntime) {
      return (New-ServiceRecord -Service $Service -Ownership 'reused' -ProcessId $servicePid)
    }
    Stop-ManagedPid -ProcessId $servicePid -WorkingDirectory $Service.WorkingDirectory -Service $Service
  }
  if ($Service.Python) {
    $previousLiveWrite = $env:VG_RUNTIME_LIVE_WRITE_ENABLED
    try {
      if ($Service.Key -eq 'runtime') {
        $env:VG_RUNTIME_LIVE_WRITE_ENABLED = 'false'
      }
      Start-Process $Service.PythonPath -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$($Service.Port)") `
        -WorkingDirectory $Service.WorkingDirectory -RedirectStandardOutput $stdout -RedirectStandardError $stderr `
        -WindowStyle Hidden | Out-Null
    } finally {
      if ($null -eq $previousLiveWrite) {
        Remove-Item Env:VG_RUNTIME_LIVE_WRITE_ENABLED -ErrorAction SilentlyContinue
      } else {
        $env:VG_RUNTIME_LIVE_WRITE_ENABLED = $previousLiveWrite
      }
    }
  } else {
    Start-Process $Service.VitePath -ArgumentList @('--host', '127.0.0.1', '--port', "$($Service.Port)") `
      -WorkingDirectory $Service.WorkingDirectory -RedirectStandardOutput $stdout -RedirectStandardError $stderr `
      -WindowStyle Hidden | Out-Null
  }
  $servicePid = Wait-ForHealth $Service
  return (New-ServiceRecord -Service $Service -Ownership 'started' -ProcessId $servicePid)
}

function Start-ManagedServices {
  New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
  New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
  foreach ($service in $Services) { Assert-Dependencies $service }
  Invoke-DemoUserSeed
  $records = @()
  $startedNow = @()
  try {
    foreach ($service in $Services) {
      $record = Start-ServiceManaged -Service $service
      $records += $record
      if ($record.ownership -eq 'started') { $startedNow += $record }
      Write-State $records
    }
  } catch {
    foreach ($record in $startedNow) {
      $definition = @($Services | Where-Object { $_.Key -eq $record.key })[0]
      if ($null -ne $definition) {
        Stop-ManagedPid -ProcessId ([int]$record.pid) -WorkingDirectory $definition.WorkingDirectory -Service $definition
      }
    }
    if (Test-Path $StatePath) { Remove-Item -LiteralPath $StatePath -Force }
    throw
  }
  Write-State $records
  Invoke-LoginSmoke
  Write-Host 'Platform local services are ready.' -ForegroundColor Green
  Write-Host 'Execution Runtime: http://127.0.0.1:8100/health'
  Write-Host 'Platform API:      http://127.0.0.1:8000/health'
  Write-Host 'Platform Web:      http://127.0.0.1:4373/index.html'
  Write-Host 'Platform Web API:  http://127.0.0.1:8000/api/v1'
}

switch ($Action) {
  'status' {
    Show-Status
    break
  }
  'stop' {
    Stop-ManagedServices
    Write-Host 'Managed Platform services stopped.' -ForegroundColor Yellow
    break
  }
  'restart' {
    Stop-ManagedServices
    Start-ManagedServices
    break
  }
  default {
    Start-ManagedServices
    break
  }
}
