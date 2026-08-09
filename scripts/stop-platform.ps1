[CmdletBinding()]
param(
  [switch]$IncludeLegacyFrontend
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$StatePath = Join-Path $RepoRoot '.codex\dev-platform\platform-dev-state.json'
$ManagedNames = @('Platform Execution Runtime', 'Platform API', 'Platform Web')
if ($IncludeLegacyFrontend) {
  $ManagedNames += 'Legacy Reference Web'
}

function Get-PortListener {
  param([Parameter(Mandatory = $true)][int]$Port)

  $Connection = Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if (-not $Connection) {
    $Connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
      Select-Object -First 1
  }
  return $Connection
}

function Get-ProcessIdentity {
  param([Parameter(Mandatory = $true)][int]$ProcessId)

  $Cim = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
  if ($Cim) {
    return [pscustomobject]@{
      pid = [int]$Cim.ProcessId
      name = [string]$Cim.Name
      executablePath = [string]$Cim.ExecutablePath
      commandLine = [string]$Cim.CommandLine
    }
  }

  $Proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
  if ($Proc) {
    return [pscustomobject]@{
      pid = [int]$Proc.Id
      name = [string]$Proc.ProcessName
      executablePath = [string]$Proc.Path
      commandLine = ''
    }
  }

  return $null
}

function Test-ProcessMatchesProject {
  param(
    [Parameter(Mandatory = $true)][int]$ProcessId,
    [Parameter(Mandatory = $true)][string]$ExpectedPath
  )

  if ($ProcessId -le 0) {
    return $false
  }
  $Identity = Get-ProcessIdentity -ProcessId $Pid
  if (-not $Identity) {
    return $false
  }

  $Expected = ([string]$ExpectedPath).ToLowerInvariant()
  $Repo = $RepoRoot.ToLowerInvariant()
  $Executable = ([string]$Identity.executablePath).ToLowerInvariant()
  $CommandLine = ([string]$Identity.commandLine).ToLowerInvariant()
  return ($Executable.Contains($Expected) -or $CommandLine.Contains($Expected) -or $Executable.Contains($Repo) -or $CommandLine.Contains($Repo))
}

function Test-JsonHealth {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][string]$ServiceName
  )

  try {
    $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    if ([int]$Response.StatusCode -ne 200) {
      return $false
    }
    $Body = $Response.Content | ConvertFrom-Json
    return ([string]$Body.service -eq $ServiceName -and [string]$Body.status -eq 'ok')
  }
  catch {
    return $false
  }
}

function Test-FrontendHealth {
  param([Parameter(Mandatory = $true)][string]$Url)

  try {
    $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    if ([int]$Response.StatusCode -ne 200) {
      return $false
    }
    $Content = [string]$Response.Content
    return ($Content.Contains('id="htmlRoot"') -or $Content.Contains('/src/main') -or $Content.Contains('vite'))
  }
  catch {
    return $false
  }
}

function Test-ServiceHealth {
  param(
    [Parameter(Mandatory = $true)][object]$Service
  )

  if ($Service.kind -eq 'runtime') {
    return Test-JsonHealth -Url $Service.healthUrl -ServiceName 'execution-runtime'
  }
  if ($Service.kind -eq 'api') {
    return Test-JsonHealth -Url $Service.healthUrl -ServiceName 'platform-api'
  }
  return Test-FrontendHealth -Url $Service.healthUrl
}

if (-not (Test-Path $StatePath)) {
  Write-Host "No platform dev state file found: $StatePath" -ForegroundColor Yellow
  return
}

$State = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
if ($State.repoRoot -ne $RepoRoot) {
  throw "State file repoRoot does not match this project. Refusing to stop processes. State: $($State.repoRoot)"
}

$Remaining = @()
$Failures = @()
foreach ($Service in @($State.services | Where-Object { $null -ne $_ })) {
  if ($ManagedNames -notcontains $Service.name) {
    $Remaining += $Service
    continue
  }

  if ($Service.ownership -ne 'managed') {
    Write-Host "$($Service.name) is $($Service.ownership); leaving it running." -ForegroundColor DarkGray
    $Remaining += $Service
    continue
  }

  $Port = [int]$Service.port
  $ListenerPid = [int]$Service.listenerPid
  $LauncherPid = [int]$Service.launcherPid
  $PortOwner = Get-PortListener -Port $Port
  if (-not $PortOwner) {
    Write-Host "$($Service.name) port $Port is already free." -ForegroundColor DarkGray
    continue
  }

  if ([int]$PortOwner.OwningProcess -ne $ListenerPid) {
    $Failures += "$($Service.name) port $Port is now owned by PID $($PortOwner.OwningProcess), recorded listener PID is $ListenerPid. Refusing to stop."
    $Remaining += $Service
    continue
  }

  if (-not (Test-ServiceHealth -Service $Service)) {
    $Failures += "$($Service.name) on port $Port did not pass identity health checks. Refusing to stop."
    $Remaining += $Service
    continue
  }

  if (-not (Test-ProcessMatchesProject -ProcessId $ListenerPid -ExpectedPath $Service.workingDirectory)) {
    $Failures += "$($Service.name) listener PID $ListenerPid identity could not be verified. Refusing to stop."
    $Remaining += $Service
    continue
  }

  $TargetPids = @($ListenerPid)
  if ($LauncherPid -gt 0) {
    $TargetPids += $LauncherPid
  }
  $TargetPids = @($TargetPids | Where-Object { $_ -gt 0 } | Select-Object -Unique)
  foreach ($TargetPid in $TargetPids) {
    $TargetProc = Get-Process -Id $TargetPid -ErrorAction SilentlyContinue
    if (-not $TargetProc) {
      continue
    }
    if (-not (Test-ProcessMatchesProject -ProcessId $TargetPid -ExpectedPath $Service.workingDirectory)) {
      $Failures += "$($Service.name) PID $TargetPid identity could not be verified. Refusing to stop this PID."
      continue
    }
    Write-Host "Stopping $($Service.name) PID $TargetPid." -ForegroundColor Cyan
    try {
      Stop-Process -Id $TargetPid -Force -ErrorAction Stop
    }
    catch [Microsoft.PowerShell.Commands.ProcessCommandException] {
      if ($_.FullyQualifiedErrorId -like 'NoProcessFoundForGivenId*') {
        continue
      }
      throw
    }
  }

  Start-Sleep -Milliseconds 700
  $StillListening = Get-PortListener -Port $Port
  if ($StillListening) {
    $Failures += "$($Service.name) port $Port is still owned by PID $($StillListening.OwningProcess) after stop."
    $Remaining += $Service
  }
}

@{
  repoRoot = $RepoRoot
  updatedAt = (Get-Date).ToString('o')
  services = @($Remaining | Where-Object { $null -ne $_ })
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $StatePath -Encoding UTF8

if ($Failures.Count -gt 0) {
  $Failures | ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
  throw "Platform stop completed with $($Failures.Count) refusal(s). See messages above."
}

Write-Host 'Platform stop completed.' -ForegroundColor Green
if (-not $IncludeLegacyFrontend) {
  Write-Host 'Legacy Reference Web was left running by default.' -ForegroundColor DarkGray
}
