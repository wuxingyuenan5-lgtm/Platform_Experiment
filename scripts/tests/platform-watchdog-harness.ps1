$ErrorActionPreference = 'Stop'

class WatchdogHarnessStop : Exception {
  WatchdogHarnessStop() : base('harness cycle limit reached') {}
}

$script:HarnessNow = [DateTimeOffset]::Parse('2026-01-01T00:00:00Z')
$script:HarnessCycle = 0
$script:HarnessMaxCycles = 1
$script:HarnessSleepAdvanceSeconds = 0
$global:HarnessHealthFailures = @()
$script:HarnessModeMatches = $true
$script:HarnessOwnershipMatches = $true
$script:HarnessStopCalls = @()
$script:HarnessStartCalls = @()
$script:HarnessStatuses = @()
$script:HarnessState = $null
$RepoRoot = 'watchdog-harness'
$StateDir = Join-Path $PSScriptRoot 'watchdog-harness-state'
$EnableLiveWrite = $true
$Services = @(
  [pscustomobject]@{ Key = 'web'; Port = 4373; WorkingDirectory = 'web' }
  [pscustomobject]@{ Key = 'api'; Port = 8000; WorkingDirectory = 'api' }
  [pscustomobject]@{ Key = 'runtime'; Port = 8100; WorkingDirectory = 'runtime' }
)

function Get-HarnessNow { return $script:HarnessNow }
function Assert-Dependencies($service) {}
function New-LifecycleLock { return $null }
function Read-State { return $script:HarnessState }
function Write-State($records) {
  $script:HarnessState = [pscustomobject]@{
    repoRoot = $script:HarnessState.repoRoot
    services = @($records)
  }
}
function Write-WatchdogStatus($status, $reason, $recoveries) {
  $script:HarnessStatuses += [pscustomobject]@{ status = $status; reason = $reason; recoveries = $recoveries }
}
function Get-JsonFieldValue($data, $field) {
  if ($field -eq 'capabilities.liveWriteEnabled') { return [bool]$data.capabilities.liveWriteEnabled }
  if ($field -eq 'liveTradingEnabled') { return [bool]$data.liveTradingEnabled }
  throw "unexpected probe field: $field"
}
function Invoke-RestMethod($Uri, $TimeoutSec) {
  if ($Uri -like '*8100/status') {
    return [pscustomobject]@{ capabilities = [pscustomobject]@{ liveWriteEnabled = $script:HarnessModeMatches } }
  }
  if ($Uri -like '*trading-safety') {
    return [pscustomobject]@{ liveTradingEnabled = $script:HarnessModeMatches }
  }
  if ($Uri -like '*health/monitors') {
    $status = if ($global:HarnessHealthFailures -contains 'reads') { 'stalled' } else { 'healthy' }
    return [pscustomobject]@{
      accountSync = [pscustomobject]@{ status = $status }
      crossExit = [pscustomobject]@{ status = 'healthy' }
    }
  }
  throw "unexpected URL: $Uri"
}
function Get-PortListener($Port) {
  $service = @($Services | Where-Object { $_.Port -eq $Port })[0]
  if ($script:HarnessOwnershipMatches) {
    return [pscustomobject]@{ OwningProcess = (@($script:HarnessState.services | Where-Object { $_.key -eq $service.Key })[0].pid) }
  }
  return [pscustomobject]@{ OwningProcess = 99999 }
}
function Test-ServiceSignature($service, $processId) { return $script:HarnessOwnershipMatches }
function Get-Process($Id, $ErrorAction) {
  $record = @($script:HarnessState.services | Where-Object { [int]$_.pid -eq [int]$Id })[0]
  return [pscustomobject]@{ StartTime = [datetime]::Parse($record.processStartedAt).ToUniversalTime() }
}
function Test-Health($service) { return -not ($global:HarnessHealthFailures -contains $service.Key) }
function Stop-ManagedPid($ProcessId, $WorkingDirectory, $Service) {
  $script:HarnessStopCalls += $Service.Key
}
function Start-ServiceManaged($service) {
  $script:HarnessStartCalls += $service.Key
  return [pscustomobject]@{
    key = $service.Key
    'pid' = (@($script:HarnessState.services | Where-Object { $_.key -eq $service.Key })[0].pid)
    processStartedAt = (@($script:HarnessState.services | Where-Object { $_.key -eq $service.Key })[0].processStartedAt)
  }
}
function Start-Sleep($Seconds) {
  $script:HarnessCycle++
  $script:HarnessNow = $script:HarnessNow.AddSeconds($script:HarnessSleepAdvanceSeconds)
  if ($script:HarnessCycle -ge $script:HarnessMaxCycles) { throw [WatchdogHarnessStop]::new() }
}

$watchdogSource = Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\platform-watchdog.ps1') -Raw
$watchdogSource = $watchdogSource.Replace('[DateTimeOffset]::UtcNow', 'Get-HarnessNow')
Invoke-Expression $watchdogSource

# The sourced file defines its own status writer; replace it after loading so
# the harness never writes watchdog state to disk.
function Write-WatchdogStatus($status, $reason, $recoveries) {
  $script:HarnessStatuses += [pscustomobject]@{ status = $status; reason = $reason; recoveries = $recoveries }
}

function Reset-Harness {
  $script:HarnessNow = [DateTimeOffset]::Parse('2026-01-01T00:00:00Z')
  $script:HarnessCycle = 0
  $script:HarnessMaxCycles = 4
  $script:HarnessSleepAdvanceSeconds = 0
  $global:HarnessHealthFailures = @()
  $script:HarnessModeMatches = $true
  $script:HarnessOwnershipMatches = $true
  $script:HarnessStopCalls = @()
  $script:HarnessStartCalls = @()
  $script:HarnessStatuses = @()
  $script:HarnessState = [pscustomobject]@{
    repoRoot = $global:RepoRoot
    services = @(
      [pscustomobject]@{ key = 'web'; 'pid' = 101; processStartedAt = '2026-01-01T00:00:00.0000000Z' }
      [pscustomobject]@{ key = 'api'; 'pid' = 102; processStartedAt = '2026-01-01T00:00:00.0000000Z' }
      [pscustomobject]@{ key = 'runtime'; 'pid' = 103; processStartedAt = '2026-01-01T00:00:00.0000000Z' }
    )
  }
}

function Assert-Equal($actual, $expected, $label) {
  $a = (@($actual) -join ',')
  $e = (@($expected) -join ',')
  if ($a -ne $e) { throw "$label expected [$e], got [$a]; statuses=$($script:HarnessStatuses | ConvertTo-Json -Compress)" }
}
function Assert-Contains($actual, $expected, $label) {
  if (@($actual) -notcontains $expected) { throw "$label expected to contain [$expected], got [$( @($actual) -join ',' )]" }
}
function Assert-NotContains($actual, $expected, $label) {
  if (@($actual) -contains $expected) { throw "$label unexpectedly contained [$expected]" }
}
function Invoke-HarnessCase($name, $configure, $expectedStops, $expectedStarts, $expectedStatus, $expectedRecoveryCount) {
  Reset-Harness
  . $configure
  try { Invoke-PlatformWatchdog } catch [WatchdogHarnessStop] {}
  Assert-Equal $script:HarnessStopCalls $expectedStops "$name stop calls"
  Assert-Equal $script:HarnessStartCalls $expectedStarts "$name start calls"
  $last = @($script:HarnessStatuses)[-1]
  Assert-Equal $last.status $expectedStatus "$name status"
  Assert-Equal $last.recoveries $expectedRecoveryCount "$name recovery count"
  Write-Output "PASS $name"
}

$global:RepoRoot = $RepoRoot
$global:StateDir = Join-Path $PSScriptRoot 'watchdog-harness-state'
$global:EnableLiveWrite = $true
$global:Services = @(
  [pscustomobject]@{ Key = 'web'; Port = 4373; WorkingDirectory = 'web' }
  [pscustomobject]@{ Key = 'api'; Port = 8000; WorkingDirectory = 'api' }
  [pscustomobject]@{ Key = 'runtime'; Port = 8100; WorkingDirectory = 'runtime' }
)

Invoke-HarnessCase 'live Web-only recovers' { $global:HarnessHealthFailures = @('web') } @('web') @('web') 'degraded' 1
Invoke-HarnessCase 'live API/runtime only blocked' { $global:HarnessHealthFailures = @('api', 'runtime') } @() @() 'blocked' 0
Invoke-HarnessCase 'mixed recovers only Web preserving blocked' { $global:HarnessHealthFailures = @('web', 'api', 'runtime') } @('web') @('web') 'blocked' 1
Invoke-HarnessCase 'read failure does not block Web recovery' { $global:HarnessHealthFailures = @('web', 'reads') } @('web') @('web') 'degraded' 1
Invoke-HarnessCase 'read failure does not restart healthy Web' { $global:HarnessHealthFailures = @('api', 'reads') } @() @() 'blocked' 0
Invoke-HarnessCase 'read failure alone does not restart services' { $global:HarnessHealthFailures = @('reads') } @() @() 'healthy' 0
Invoke-HarnessCase 'mode changed blocks recovery' { $script:HarnessModeMatches = $false; $global:HarnessHealthFailures = @('web') } @() @() 'blocked' 0
Invoke-HarnessCase 'ownership changed blocks recovery' { $script:HarnessOwnershipMatches = $false; $global:HarnessHealthFailures = @('web') } @() @() 'blocked' 0

Invoke-HarnessCase 'cooldown prevents immediate second recovery' {
  $global:HarnessHealthFailures = @('web')
  $script:HarnessMaxCycles = 4
} @('web') @('web') 'degraded' 1

Invoke-HarnessCase 'recovery limit blocks fourth recovery' {
  $global:HarnessHealthFailures = @('web')
  $script:HarnessMaxCycles = 12
  $script:HarnessSleepAdvanceSeconds = 301
} @('web', 'web', 'web') @('web', 'web', 'web') 'blocked' 3
