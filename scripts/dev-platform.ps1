[CmdletBinding()]
param(
[ValidateSet('start', 'status', 'stop', 'restart', 'restart-web', 'restart-api', 'watch', 'supervisor')][string]$Action = 'start',
  [ValidateRange(1, 180)][int]$HealthTimeoutSeconds = 90,
  [switch]$EnableLiveWrite
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$StateDir = Join-Path $RepoRoot '.codex\dev-platform'
$StatePath = Join-Path $StateDir 'platform-dev-state.json'
$LogDir = Join-Path $StateDir 'logs'
$WebReleaseMarker = Join-Path $RepoRoot '.codex\releases\web\current.json'
$WebReleaseRoot = Join-Path $RepoRoot '.codex\releases\web'
$CaddyPath = Join-Path $RepoRoot '.codex\tools\caddy\caddy.exe'
$ContractVersion = '2026-08-25.dev-platform.v3'
$DemoUsername = 'demo_ceo'
$Services = @(
  @{
    Key = 'runtime'; Name = 'Execution Runtime'; Port = 8100; HealthUrl = 'http://127.0.0.1:8100/health';
    WorkingDirectory = (Join-Path $RepoRoot 'execution-runtime'); Python = $true;
    ContractChecks = @(
      @{ Url = 'http://127.0.0.1:8100/status'; JsonField = 'status'; Expected = 'available' },
      @{ Url = 'http://127.0.0.1:8100/status'; JsonField = 'capabilities.liveWriteEnabled'; Expected = [bool]$EnableLiveWrite }
    )
  },
  @{
    Key = 'api'; Name = 'Platform API'; Port = 8000; HealthUrl = 'http://127.0.0.1:8000/health';
    WorkingDirectory = (Join-Path $RepoRoot 'platform-api'); Python = $true;
    ContractChecks = @(
      @{ Url = 'http://127.0.0.1:8000/api/v1/auth/login'; AcceptStatus = @(200, 401, 405, 422) },
      @{ Url = 'http://127.0.0.1:8000/api/v1/strategies/management-overview'; AcceptStatus = @(200) },
      @{ Url = 'http://127.0.0.1:8000/api/v1/ops/venue-snapshots/status'; AcceptStatus = @(200) }
      @{ Url = 'http://127.0.0.1:8000/api/v1/security/trading-safety'; JsonField = 'liveTradingEnabled'; Expected = [bool]$EnableLiveWrite }
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
    processStartedAt = (Get-Process -Id $ProcessId).StartTime.ToUniversalTime().ToString('o')
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
  if ($commandLine.Contains('caddy') -and $commandLine.Contains('run') -and $commandLine.Contains($WebReleaseRoot.ToLowerInvariant())) { return $true }
  return $commandLine.Contains('vite') -and $commandLine.Contains("--port $($Service.Port)")
}

function Get-WebRelease {
  if (-not (Test-Path -LiteralPath $WebReleaseMarker)) { return $null }
  try {
    $release = Get-Content -LiteralPath $WebReleaseMarker -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace($release.release) -or [string]::IsNullOrWhiteSpace($release.caddyConfig)) { throw 'Incomplete local Web release marker.' }
    $releaseBoundary = [IO.Path]::GetFullPath($WebReleaseRoot).TrimEnd('\') + '\'
    foreach ($releasePath in @($release.release, $release.caddyConfig)) {
      if (-not [IO.Path]::GetFullPath($releasePath).StartsWith($releaseBoundary, [StringComparison]::OrdinalIgnoreCase)) { throw 'Local Web release path is outside the release directory.' }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $release.release 'index.html')) -or
        -not (Test-Path -LiteralPath $release.caddyConfig)) { throw 'Published local Web files are missing.' }
    return $release
  } catch { throw "Cannot load published local Web: $($_.Exception.Message)" }
}

function Test-ExpectedRuntime {
  param([hashtable]$Service, [int]$ProcessId)
  if (-not $Service.Python) {
    if ($Service.WebMode -eq 'published') {
      return (Get-ProcessCommandLine $ProcessId).ToLowerInvariant().Contains($Service.CaddyConfig.ToLowerInvariant())
    }
    return $true
  }
  if (-not $Service.PythonPath) { return $false }
  try {
    $health = (Invoke-ServiceRequest $Service.HealthUrl).Content | ConvertFrom-Json
    return [bool]$health.pythonVirtualEnvironment
  } catch {
    return $false
  }
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
    $release = Get-WebRelease
    if ($null -ne $release) {
      if (-not (Test-Path -LiteralPath $CaddyPath)) { throw "Caddy executable is missing: $CaddyPath" }
      $Service.CaddyPath = $CaddyPath
      $Service.CaddyConfig = [string]$release.caddyConfig
      $Service.WebMode = 'published'
    } else {
      $vite = Join-Path $Service.WorkingDirectory 'node_modules\.bin\vite.cmd'
      if (-not (Test-Path $vite)) { throw "Platform Web dependencies are missing: $vite" }
      $Service.VitePath = $vite
      $Service.WebMode = 'development'
    }
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
    $bootstrapPassword = $env:PLATFORM_DEMO_PASSWORD
    if ([string]::IsNullOrWhiteSpace($bootstrapPassword)) {
      $bootstrapPassword = [Environment]::GetEnvironmentVariable('PLATFORM_DEMO_PASSWORD', 'User')
    }
    $generatedPassword = [string]::IsNullOrWhiteSpace($bootstrapPassword)
    if ($generatedPassword) {
      $bootstrapPassword = "Local-$([guid]::NewGuid().ToString('N'))!9aA"
    }
    $env:VG_LIVE_TRADING_ENABLED = 'false'
    $env:USER_SYSTEM_DEMO_SEED = '1'
    $env:USER_SYSTEM_DEMO_PASSWORD = $bootstrapPassword
    $env:USER_SYSTEM_DEMO_REFRESH = '0'
    $seedOutput = @(& $platformApi.PythonPath $seedScript)
    if ($LASTEXITCODE -ne 0) {
      throw 'Reusable demo account seeding failed.'
    }
    $created = @($seedOutput | Where-Object { $_ -match '\screated$' }).Count -gt 0
    if ($created -and $generatedPassword) {
      Write-Host 'A temporary local demo password was generated for newly created accounts.' -ForegroundColor Yellow
      Write-Host "Temporary password (shown once): $bootstrapPassword" -ForegroundColor Yellow
    }
    return [pscustomobject]@{
      Created = $created
      Username = $DemoUsername
      Password = if ($created) { $bootstrapPassword } else { $null }
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

function Get-ExistingLiveWrite {
  # Preserve an already running mode; never infer permission from a saved file.
  $backends = @($Services | Where-Object { $_.Key -in @('runtime', 'api') })
  $running = @()
  foreach ($service in $backends) {
    $listener = Get-PortListener $service.Port
    if ($listener) {
      if (-not (Test-ProjectProcess ([int]$listener.OwningProcess) $service.WorkingDirectory)) {
        # Relative uvicorn commands omit the repository path. Verify their
        # listener against this repository's managed process record instead.
        $state = Read-State
        $record = @($state.services | Where-Object {
          $_.key -eq $service.Key -and $_.pid -eq $listener.OwningProcess -and
          $_.workingDirectory -eq $service.WorkingDirectory
        })
        if ($null -eq $state -or $state.repoRoot -ne $RepoRoot -or $record.Count -ne 1 -or
            -not (Test-ServiceSignature $service ([int]$listener.OwningProcess))) {
          throw 'Cannot preserve trading mode from a non-project backend.'
        }
      }
      $running += $service
    }
  }
  if ($running.Count -eq 0) { return $false }
  if ($running.Count -ne 2) {
    throw 'Backend state is incomplete. Specify -EnableLiveWrite:$true or :$false explicitly before restarting.'
  }
  $runtime = Invoke-RestMethod -Uri 'http://127.0.0.1:8100/status' -TimeoutSec 5
  $platform = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/security/trading-safety' -TimeoutSec 5
  $runtimeFlag = $runtime.capabilities.liveWriteEnabled
  $platformFlag = $platform.liveTradingEnabled
  if ($runtimeFlag -isnot [bool] -or $platformFlag -isnot [bool] -or $runtimeFlag -ne $platformFlag) {
    throw 'Backend trading modes are unavailable or inconsistent. Resolve before restarting.'
  }
  return $platformFlag
}

function Read-State {
  if (-not (Test-Path $StatePath)) { return $null }
  try { return Get-Content -LiteralPath $StatePath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { throw "Cannot read Platform service state: $($_.Exception.Message)" }
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
  $children = @{}
  $allProcesses = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)
  $pending = @($ProcessId)
  while ($pending.Count -gt 0) {
    $parentId = [int]$pending[0]
    $pending = @($pending | Select-Object -Skip 1)
    foreach ($child in @($allProcesses | Where-Object { [int]$_.ParentProcessId -eq $parentId })) {
      if (-not $children.ContainsKey([int]$child.ProcessId)) {
        $children[[int]$child.ProcessId] = $true
        $pending += [int]$child.ProcessId
      }
    }
  }
  foreach ($childId in @($children.Keys | Sort-Object -Descending)) {
    Stop-Process -Id ([int]$childId) -Force -ErrorAction SilentlyContinue
  }
  Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
  if ($null -ne $Service) {
    $stopDeadline = [DateTime]::UtcNow.AddSeconds(10)
    do {
      $remainingListener = Get-PortListener $Service.Port
      if (-not $remainingListener -or [int]$remainingListener.OwningProcess -ne $ProcessId) { return }
      Start-Sleep -Milliseconds 200
    } while ([DateTime]::UtcNow -lt $stopDeadline)
    throw "Stopped process $ProcessId has not released port $($Service.Port)."
  }
}

function Stop-ManagedServices {
  $state = Read-State
  if ($null -eq $state) { return }
  if ($state.repoRoot -ne $RepoRoot) { throw 'Platform service state belongs to another repository.' }
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
  param($SeedResult)
  $headers = @{ Origin = 'http://127.0.0.1:4373' }
  if ($SeedResult.Created) {
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $body = @{ username = $SeedResult.Username; password = $SeedResult.Password } | ConvertTo-Json
    $login = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/auth/login' -Method Post `
      -Headers $headers -WebSession $session -ContentType 'application/json' -Body $body -UseBasicParsing
    if ($login.StatusCode -ne 200) {
      throw 'Platform API newly seeded account login smoke check failed.'
    }
    $me = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/auth/me' -Headers $headers -WebSession $session -UseBasicParsing
    if ($me.StatusCode -ne 200) {
      throw 'Platform API auth/me smoke check failed.'
    }
  } else {
    $invalidBody = @{
      username = "startup_probe_$([guid]::NewGuid().ToString('N'))"
      password = "Invalid-$([guid]::NewGuid().ToString('N'))!9aA"
    } | ConvertTo-Json
    try {
      Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/auth/login' -Method Post `
        -Headers $headers -ContentType 'application/json' -Body $invalidBody -UseBasicParsing | Out-Null
      throw 'Platform API auth route accepted an invalid startup probe.'
    } catch {
      $statusCode = [int]($_.Exception.Response.StatusCode.value__ 2>$null)
      if ($statusCode -ne 401) { throw }
    }
  }
  $overview = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/strategies/management-overview' `
    -Headers $headers -UseBasicParsing
  if ($overview.StatusCode -ne 200) {
    throw 'Platform API management overview smoke check failed.'
  }
}

function Invoke-PlatformSupervisor {
  $supervisorLog = Join-Path $StateDir 'supervisor.log'
  New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
  function Write-SupervisorLog { param([string]$Message) Add-Content -LiteralPath $supervisorLog -Value ((Get-Date).ToString('o') + ' ' + $Message) -Encoding UTF8 }
  function Ensure-SupervisorWatchdog {
    # A removed state file is an intentional operator stop. The watchdog alone
    # owns service recovery; the supervisor only keeps that watchdog alive.
    if (-not (Test-Path -LiteralPath $StatePath)) { return }
    $watchPath = Join-Path $StateDir 'watchdog.json'
    $record = $null
    if (Test-Path -LiteralPath $watchPath) {
      try { $record = Get-Content -LiteralPath $watchPath -Raw | ConvertFrom-Json } catch {}
    }
    $watchProcess = if ($record) { Get-Process -Id ([int]$record.pid) -ErrorAction SilentlyContinue } else { $null }
    $watchCommand = if ($watchProcess) { Get-ProcessCommandLine ([int]$watchProcess.Id) } else { '' }
    $fresh = $false
    if ($record -and $watchProcess -and $watchCommand.Contains((Join-Path $PSScriptRoot 'dev-platform.ps1')) -and $watchCommand.Contains('-Action watch')) {
      try { $fresh = (([DateTimeOffset]::UtcNow - [DateTimeOffset]::Parse($record.observedAt)).TotalSeconds -lt 180) } catch {}
    }
    # The launcher exits after handing durable log handles to the child, so
    # ParentProcessId is not a stable ownership signal for this process.
    if ($fresh -and [bool]$record.liveWrite -eq [bool]$EnableLiveWrite) { return }
    if ($watchProcess -and $watchCommand.Contains((Join-Path $PSScriptRoot 'dev-platform.ps1')) -and $watchCommand.Contains('-Action watch')) {
      Stop-Process -Id $watchProcess.Id -Force -ErrorAction SilentlyContinue
    }
    $args = @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $PSScriptRoot 'dev-platform.ps1'),'-Action','watch')
    if ($EnableLiveWrite) { $args += '-EnableLiveWrite' }
    Start-PlatformChildProcess -FilePath (Get-Process -Id $PID).Path -ArgumentList $args `
      -WorkingDirectory $RepoRoot -StandardOutput (Join-Path $LogDir 'supervised-watchdog.out.log') `
      -StandardError (Join-Path $LogDir 'supervised-watchdog.err.log') | Out-Null
    Write-SupervisorLog 'watchdog launched and assigned to supervisor'
  }
  Write-SupervisorLog ("started pid=$PID liveWrite=$([bool]$EnableLiveWrite)")
  while ($true) {
    try {
      if ((Get-PortListener 8100) -and (Get-PortListener 8000)) {
        # Adopt only a verified, matching mode from both running backends.
        $EnableLiveWrite = Get-ExistingLiveWrite
      }
      Ensure-SupervisorWatchdog
    } catch { Write-SupervisorLog ("supervisor error: {0}" -f $_.Exception.Message) }
    Start-Sleep -Seconds 15
  }
}

function Start-PlatformChildProcess {
  param(
    [Parameter(Mandatory)][string]$FilePath,
    [Parameter(Mandatory)][string[]]$ArgumentList,
    [Parameter(Mandatory)][string]$WorkingDirectory,
    [Parameter(Mandatory)][string]$StandardOutput,
    [Parameter(Mandatory)][string]$StandardError
  )
  $launcher = Join-Path $PSScriptRoot 'launch-platform-child.py'
  $python = Join-Path $RepoRoot 'execution-runtime\.venv\Scripts\python.exe'
  if (-not (Test-Path -LiteralPath $python)) { throw "Platform launcher Python is missing: $python" }
  $launchOutput = @(& $python $launcher $FilePath $WorkingDirectory $StandardOutput $StandardError @ArgumentList)
  if ($LASTEXITCODE -ne 0 -or $launchOutput.Count -ne 1 -or [string]$launchOutput[0] -notmatch '^\d+$') {
    throw "Managed process launch failed: $FilePath"
  }
  $childProcess = Get-Process -Id ([int]$launchOutput[0]) -ErrorAction Stop
  return $childProcess
}

function Start-ServiceManaged {
  param([hashtable]$Service)
  $safeName = $Service.Name.ToLowerInvariant().Replace(' ', '-')
  $logStamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
  $stdout = Join-Path $LogDir "$safeName.$logStamp.out.log"
  $stderr = Join-Path $LogDir "$safeName.$logStamp.err.log"
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
    $previousPlatformLiveWrite = $env:VG_LIVE_TRADING_ENABLED
    $previousFounderDemo = $env:VG_FOUNDER_DEMO_LIVE_ACCEPTANCE_ENABLED
    $previousResearchCapture = $env:VG_RUNTIME_RESEARCH_CAPTURE_ENABLED
    $previousStrategyResearch = $env:VG_STRATEGY_RESEARCH_ENABLED
    $previousStrategyWorker = $env:VG_STRATEGY_RESEARCH_WORKER_ENABLED
    $previousStrategyProjection = $env:VG_STRATEGY_RESEARCH_PROJECTION_ENABLED
    try {
      $liveWriteValue = if ($EnableLiveWrite) { 'true' } else { 'false' }
      if ($Service.Key -eq 'runtime') {
        $env:VG_RUNTIME_LIVE_WRITE_ENABLED = $liveWriteValue
      }
      if ($Service.Key -in @('runtime', 'api')) {
        $env:VG_LIVE_TRADING_ENABLED = $liveWriteValue
        $env:VG_FOUNDER_DEMO_LIVE_ACCEPTANCE_ENABLED = 'false'
      }
      if ($Service.Key -eq 'runtime') {
        # Research capture is the shared high-resolution source for the
        # strategy and hedge-board producers; ordinary local starts must not
        # silently launch the venue process without it.
        $env:VG_RUNTIME_RESEARCH_CAPTURE_ENABLED = 'true'
      }
      if ($Service.Key -eq 'api') {
        $env:VG_STRATEGY_RESEARCH_ENABLED = 'true'
        $env:VG_STRATEGY_RESEARCH_WORKER_ENABLED = 'true'
        $env:VG_STRATEGY_RESEARCH_PROJECTION_ENABLED = 'true'
      }
      Start-PlatformChildProcess -FilePath $Service.PythonPath `
        -ArgumentList @('-u', '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$($Service.Port)") `
        -WorkingDirectory $Service.WorkingDirectory -StandardOutput $stdout -StandardError $stderr | Out-Null
    } finally {
      if ($null -eq $previousLiveWrite) {
        Remove-Item Env:VG_RUNTIME_LIVE_WRITE_ENABLED -ErrorAction SilentlyContinue
      } else {
        $env:VG_RUNTIME_LIVE_WRITE_ENABLED = $previousLiveWrite
      }
      if ($null -eq $previousPlatformLiveWrite) {
        Remove-Item Env:VG_LIVE_TRADING_ENABLED -ErrorAction SilentlyContinue
      } else {
        $env:VG_LIVE_TRADING_ENABLED = $previousPlatformLiveWrite
      }
      if ($null -eq $previousFounderDemo) {
        Remove-Item Env:VG_FOUNDER_DEMO_LIVE_ACCEPTANCE_ENABLED -ErrorAction SilentlyContinue
      } else {
        $env:VG_FOUNDER_DEMO_LIVE_ACCEPTANCE_ENABLED = $previousFounderDemo
      }
      if ($null -eq $previousResearchCapture) {
        Remove-Item Env:VG_RUNTIME_RESEARCH_CAPTURE_ENABLED -ErrorAction SilentlyContinue
      } else {
        $env:VG_RUNTIME_RESEARCH_CAPTURE_ENABLED = $previousResearchCapture
      }
      if ($null -eq $previousStrategyResearch) {
        Remove-Item Env:VG_STRATEGY_RESEARCH_ENABLED -ErrorAction SilentlyContinue
      } else {
        $env:VG_STRATEGY_RESEARCH_ENABLED = $previousStrategyResearch
      }
      if ($null -eq $previousStrategyWorker) {
        Remove-Item Env:VG_STRATEGY_RESEARCH_WORKER_ENABLED -ErrorAction SilentlyContinue
      } else {
        $env:VG_STRATEGY_RESEARCH_WORKER_ENABLED = $previousStrategyWorker
      }
      if ($null -eq $previousStrategyProjection) {
        Remove-Item Env:VG_STRATEGY_RESEARCH_PROJECTION_ENABLED -ErrorAction SilentlyContinue
      } else {
        $env:VG_STRATEGY_RESEARCH_PROJECTION_ENABLED = $previousStrategyProjection
      }
    }
  } elseif ($Service.WebMode -eq 'published') {
    Start-PlatformChildProcess -FilePath $Service.CaddyPath `
      -ArgumentList @('run', '--config', $Service.CaddyConfig, '--adapter', 'caddyfile') `
      -WorkingDirectory $RepoRoot -StandardOutput $stdout -StandardError $stderr | Out-Null
  } else {
    Start-PlatformChildProcess -FilePath $Service.VitePath `
      -ArgumentList @('--host', '127.0.0.1', '--port', "$($Service.Port)") `
      -WorkingDirectory $Service.WorkingDirectory -StandardOutput $stdout -StandardError $stderr | Out-Null
  }
  $servicePid = Wait-ForHealth $Service
  return (New-ServiceRecord -Service $Service -Ownership 'started' -ProcessId $servicePid)
}

function Start-ManagedServices {
  New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
  New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
  foreach ($service in $Services) { Assert-Dependencies $service }
  $seedResult = Invoke-DemoUserSeed
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
  Invoke-LoginSmoke -SeedResult $seedResult
  Write-Host 'Platform local services are ready.' -ForegroundColor Green
  Write-Host 'Execution Runtime: http://127.0.0.1:8100/health'
  Write-Host 'Platform API:      http://127.0.0.1:8000/health'
  Write-Host 'Platform Web:      http://127.0.0.1:4373/index.html'
  Write-Host 'Platform Web API:  http://127.0.0.1:8000/api/v1'
  Write-Host "Live Write:        $(if ($EnableLiveWrite) { 'enabled (explicit or preserved running mode)' } else { 'disabled' })"
}

. (Join-Path $PSScriptRoot 'platform-watchdog.ps1')

$lifecycleLock = $null
if ($Action -in @('start','stop','restart','restart-web','restart-api')) {
  $lifecycleLock = New-LifecycleLock
  try { $acquired = $lifecycleLock.WaitOne(180000) } catch [Threading.AbandonedMutexException] { $acquired = $true }
  if (-not $acquired) { throw 'Lifecycle operation already running' }
}
try {
if ($Action -in @('start', 'restart', 'restart-web', 'restart-api', 'status') -and -not $PSBoundParameters.ContainsKey('EnableLiveWrite')) {
  $EnableLiveWrite = Get-ExistingLiveWrite
}
foreach ($service in $Services) {
  foreach ($check in $service.ContractChecks) {
    if ($check.JsonField -in @('capabilities.liveWriteEnabled', 'liveTradingEnabled')) {
      $check.Expected = [bool]$EnableLiveWrite
    }
  }
}

switch ($Action) {
  'supervisor' {
    Invoke-PlatformSupervisor
    break
  }
  'watch' {
    Invoke-PlatformWatchdog
    break
  }
  'status' {
    Show-Status
    break
  }
  'stop' {
    Stop-PlatformWatchdog
    Stop-ManagedServices
    Write-Host 'Managed Platform services stopped.' -ForegroundColor Yellow
    break
  }
  { $_ -in @('restart-web', 'restart-api') } {
    $serviceKey = if ($Action -eq 'restart-web') { 'web' } else { 'api' }
    $restartDefinition = @($Services | Where-Object { $_.Key -eq $serviceKey })[0]
    Assert-Dependencies $restartDefinition
    $existingState = Read-State
    Stop-PlatformWatchdog
    try {
      $restartListener = Get-PortListener $restartDefinition.Port
      if ($restartListener) {
        Stop-ManagedPid -ProcessId ([int]$restartListener.OwningProcess) -WorkingDirectory $restartDefinition.WorkingDirectory -Service $restartDefinition
      }
      $newRecord = Start-ServiceManaged $restartDefinition
      $otherRecords = @($existingState.services | Where-Object { $_.key -ne $serviceKey })
      Write-State ($otherRecords + @($newRecord))
    } finally { Start-PlatformWatchdog }
    break
  }
  'restart' {
    Stop-PlatformWatchdog
    Stop-ManagedServices
    Start-ManagedServices
    Start-PlatformWatchdog
    break
  }
  default {
    Start-ManagedServices
    Start-PlatformWatchdog
    break
  }
}

} finally {
  if ($null -ne $lifecycleLock) { $lifecycleLock.ReleaseMutex(); $lifecycleLock.Dispose() }
}
