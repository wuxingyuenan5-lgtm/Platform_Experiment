# Uses the existing managed-service lifecycle; never submits trading commands.
$WatchPath = Join-Path $StateDir 'watchdog.json'

function New-LifecycleLock {
  $suffix = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($RepoRoot)).Replace('/', '_')
  return [Threading.Mutex]::new($false, ('Local\VGLifecycle-' + $suffix))
}

function Stop-PlatformWatchdog {
  if (-not (Test-Path $WatchPath)) { return }
  $record = Get-Content -LiteralPath $WatchPath -Raw | ConvertFrom-Json
  $command = Get-ProcessCommandLine ([int]$record.pid)
  if ($record.pid -ne $PID -and $command.Contains((Join-Path $PSScriptRoot 'dev-platform.ps1')) -and $command.Contains('-Action watch')) {
    Stop-Process -Id ([int]$record.pid) -Force -ErrorAction SilentlyContinue
  }
  Remove-Item -LiteralPath $WatchPath -Force
}

function Start-PlatformWatchdog {
  if (Test-Path $WatchPath) {
    $record = Get-Content -LiteralPath $WatchPath -Raw | ConvertFrom-Json
    $command = Get-ProcessCommandLine ([int]$record.pid)
    if ($command.Contains((Join-Path $PSScriptRoot 'dev-platform.ps1')) -and $command.Contains('-Action watch')) { return }
  }
  $hostExecutable = (Get-Process -Id $PID).Path
  $arguments = @(
    '-NoProfile',
    '-File',
    ('"' + (Join-Path $PSScriptRoot 'dev-platform.ps1') + '"'),
    '-Action',
    'watch'
  )
  if ($EnableLiveWrite) { $arguments += '-EnableLiveWrite' }
  Start-Process $hostExecutable -ArgumentList $arguments -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDir 'watchdog.out.log') `
    -RedirectStandardError (Join-Path $LogDir 'watchdog.err.log') | Out-Null
}

function Write-WatchdogStatus {
  param([string]$Status, [string]$Reason, [int]$Recoveries)
  $temporary = "$WatchPath.tmp"
  @{pid=$PID; status=$Status; reason=$Reason; recoveries=$Recoveries;
    observedAt=[DateTimeOffset]::UtcNow.ToString('o'); liveWrite=[bool]$EnableLiveWrite} |
    ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding UTF8
  Move-Item -LiteralPath $temporary -Destination $WatchPath -Force
}

function Invoke-PlatformWatchdog {
  # Startup captures a verified mode in this process, never from a saved flag.
  $name = 'Local\VGWatch-' + [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($RepoRoot)).Replace('/', '_')
  $mutex = [Threading.Mutex]::new($false, $name)
  try { $owned = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $owned = $true }
  if (-not $owned) { $mutex.Dispose(); return }
  $failures = @{}; $recoveryTimes = @(); $lastRecovery = [DateTimeOffset]::MinValue
  try {
    foreach ($service in $Services) { Assert-Dependencies $service }
    while ($true) {
      $cycleLock = New-LifecycleLock
      try { $acquired = $cycleLock.WaitOne(0) } catch [Threading.AbandonedMutexException] { $acquired = $true }
      if (-not $acquired) { $cycleLock.Dispose(); Start-Sleep -Seconds 5; continue }
      try {
      $state = Read-State
      if ($null -eq $state -or $state.repoRoot -ne $RepoRoot) { return }
      $now = [DateTimeOffset]::UtcNow
      $targets = @(); $reason = ''; $blocked = $false
      foreach ($probe in @(@{url='http://127.0.0.1:8100/status';field='capabilities.liveWriteEnabled'},
          @{url='http://127.0.0.1:8000/api/v1/security/trading-safety';field='liveTradingEnabled'})) {
        try {
          $data = Invoke-RestMethod -Uri $probe.url -TimeoutSec 3
          $flag = Get-JsonFieldValue $data $probe.field
          if ($flag -isnot [bool] -or $flag -ne [bool]$EnableLiveWrite) {
            $blocked=$true; $reason='Trading mode changed; restart watchdog through lifecycle command'
          }
        } catch { }
      }
      foreach ($service in $Services) {
        $listener = Get-PortListener $service.Port
        $record = @($state.services | Where-Object { $_.key -eq $service.Key })
        if ($record.Count -ne 1) { $blocked=$true; $reason='Missing managed service identity'; continue }
        if ($listener -and ([int]$record[0].pid -ne [int]$listener.OwningProcess -or
            -not (Test-ServiceSignature $service ([int]$listener.OwningProcess)))) {
          $blocked=$true; $reason='Service ownership changed'; continue
        }
        if (Test-Health $service) { $failures[$service.Key]=0 }
        else { $failures[$service.Key]=1+[int]$failures[$service.Key] }
        if ($failures[$service.Key] -ge 3) { $targets += $service; $reason='Repeated local health failure' }
      }
      try {
        $monitors = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health/monitors' -TimeoutSec 3
        $stalled = $monitors.accountSync.status -eq 'stalled' -or $monitors.crossExit.status -eq 'stalled'
        $failures['reads'] = if ($monitors.accountSync.status -eq 'degraded') { 1+[int]$failures['reads'] } else { 0 }
        if ($stalled -or $failures['reads'] -ge 6) {
          $reason='Background reads stalled or repeatedly failed'
          $targets = @($Services | Where-Object { $_.Key -in @('runtime','api') })
        }
      } catch { }
      if ($EnableLiveWrite -and $targets.Count) {
        $blocked=$true; $reason='Live execution may be in flight; automatic interruption withheld'
      }
      $recoveryTimes = @($recoveryTimes | Where-Object { ($now - $_).TotalHours -lt 1 })
      if ($targets.Count -and -not $blocked) {
        if ($recoveryTimes.Count -ge 3) { $blocked=$true; $reason='Recovery limit reached; operator attention required' }
        elseif (($now - $lastRecovery).TotalSeconds -ge 300) {
          $lastRecovery=$now; $recoveryTimes += $now
          Write-WatchdogStatus 'recovering' $reason $recoveryTimes.Count
          try {
            foreach ($service in $targets) {
              $record = @($state.services | Where-Object { $_.key -eq $service.Key })[0]
              $listener = Get-PortListener $service.Port
              if ($listener -and [int]$listener.OwningProcess -ne [int]$record.pid) { throw 'Ownership changed during recovery' }
              $process = Get-Process -Id ([int]$record.pid) -ErrorAction SilentlyContinue
              if ($process -and $process.StartTime.ToUniversalTime().ToString('o') -ne $record.processStartedAt) {
                throw 'Managed process identity is no longer current'
              }
              Stop-ManagedPid -ProcessId ([int]$record.pid) -WorkingDirectory $service.WorkingDirectory -Service $service
            }
            $records = @($state.services)
            foreach ($service in $targets) {
              $newRecord = Start-ServiceManaged $service
              $records = @($records | Where-Object { $_.key -ne $service.Key }) + @($newRecord)
              Write-State $records
            }
          } catch { $blocked=$true; $reason='Recovery failed; inspect local service logs' }
        }
      }
      $status = if ($blocked) { 'blocked' } elseif ($targets.Count) { 'degraded' } else { 'healthy' }
      Write-WatchdogStatus $status $reason $recoveryTimes.Count
      } finally { $cycleLock.ReleaseMutex(); $cycleLock.Dispose() }
      Start-Sleep -Seconds 15
    }
  } finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
}
