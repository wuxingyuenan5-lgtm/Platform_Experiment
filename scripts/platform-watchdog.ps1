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
  $pwshCommand = Get-Command pwsh -ErrorAction SilentlyContinue
  $hostExecutable = if ($pwshCommand) { $pwshCommand.Source } else { (Get-Process -Id $PID).Path }
  $arguments = @(
    '-NoProfile',
    '-File',
    (Join-Path $PSScriptRoot 'dev-platform.ps1'),
    '-Action',
    'watch'
  )
  if ($EnableLiveWrite) { $arguments += '-EnableLiveWrite' }
  if (Get-Command Start-PlatformChildProcess -ErrorAction SilentlyContinue) {
    Start-PlatformChildProcess -FilePath $hostExecutable -ArgumentList $arguments `
      -WorkingDirectory $RepoRoot -StandardOutput (Join-Path $LogDir 'watchdog.out.log') `
      -StandardError (Join-Path $LogDir 'watchdog.err.log') | Out-Null
  } else {
    Start-Process $hostExecutable -ArgumentList $arguments -WindowStyle Hidden | Out-Null
  }
}

function Write-WatchdogStatus {
  param([string]$Status, [string]$Reason, [int]$Recoveries)
  $temporary = "$WatchPath.tmp"
  @{pid=$PID; status=$Status; reason=$Reason; recoveries=$Recoveries;
    observedAt=[DateTimeOffset]::UtcNow.ToString('o'); liveWrite=[bool]$EnableLiveWrite} |
    ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding UTF8
  Move-Item -LiteralPath $temporary -Destination $WatchPath -Force
}

function Test-ExecutionInFlight {
  # A live-write backend may only be interrupted when its durable journal has
  # no unresolved command.  If the journal cannot be read, fail closed.
  $runtime = @($Services | Where-Object { $_.Key -eq 'runtime' })[0]
  if ($null -eq $runtime -or [string]::IsNullOrWhiteSpace($runtime.PythonPath)) { return $true }
  $journal = Join-Path $runtime.WorkingDirectory 'data\runtime_journal.db'
  if (-not (Test-Path -LiteralPath $journal)) { return $false }
  try {
    $dbPath = [IO.Path]::GetFullPath($journal).Replace('\', '/').Replace("'", "''")
    $code = "import sqlite3; db=sqlite3.connect(r'$dbPath'); print(db.execute(`"select count(*) from runtime_commands where status in ('processing','result_unknown')`").fetchone()[0])"
    $count = [int]((& $runtime.PythonPath -c $code 2>$null | Select-Object -Last 1))
    return $count -gt 0
  } catch { return $true }
}

function Reconcile-ManagedServiceRecord {
  param(
    [Parameter(Mandatory)]$State,
    [Parameter(Mandatory)]$Service,
    [Parameter(Mandatory)]$Listener
  )
  $processId = [int]$Listener.OwningProcess
  if ($processId -le 0 -or -not (Test-ServiceSignature $Service $processId)) { return $null }
  try {
    $record = New-ServiceRecord -Service $Service -Ownership 'reconciled' -ProcessId $processId
    $records = @($State.services | Where-Object { $_.key -ne $Service.Key }) + @($record)
    Write-State $records
    return @($records | Where-Object { $_.key -eq $Service.Key })[0]
  } catch { return $null }
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
        if ($record.Count -ne 1) {
          if ($listener) {
            $record = @(Reconcile-ManagedServiceRecord -State $state -Service $service -Listener $listener)
          }
          if ($record.Count -ne 1) {
            if ($listener) { $blocked=$true; $reason='Service ownership changed' }
            else { $targets += $service; $reason='Managed service missing from state' }
            continue
          }
        }
        if ($listener -and [int]$record[0].pid -ne [int]$listener.OwningProcess) {
          $reconciled = Reconcile-ManagedServiceRecord -State $state -Service $service -Listener $listener
          if ($null -ne $reconciled) { $record = @($reconciled) }
          else { $blocked=$true; $reason='Service ownership changed'; continue }
        }
        if ($listener -and -not (Test-ServiceSignature $service ([int]$listener.OwningProcess))) {
          $blocked=$true; $reason='Service ownership changed'; continue
        }
        if (Test-Health $service) { $failures[$service.Key]=0 }
        else { $failures[$service.Key]=1+[int]$failures[$service.Key] }
        if ($failures[$service.Key] -ge 3) { $targets += $service; $reason='Repeated local health failure' }
      }
      # Account and venue read failures are reported by monitor-health. They
      # must not recycle healthy API/Runtime processes or hide their cause.
      # Live Write protects the trading backends, while a static web process
      # is safe to recycle independently. Preserve any earlier mode or
      # ownership block: it must still prevent all recovery.
      $backendTargets = @($targets | Where-Object { $_.Key -in @('runtime', 'api') })
      $webTargets = @($targets | Where-Object { $_.Key -eq 'web' })
      $allowWebRecovery = $EnableLiveWrite -and $webTargets.Count -gt 0 -and -not $blocked
      if ($EnableLiveWrite -and $backendTargets.Count -and (Test-ExecutionInFlight)) {
        $blocked=$true; $reason='Live execution may be in flight; automatic backend interruption withheld'
      }
      $recoveryTargets = @(if ($EnableLiveWrite) { $webTargets } else { $targets })
      $recoveryTimes = @($recoveryTimes | Where-Object { ($now - $_).TotalHours -lt 1 })
      if ($recoveryTargets.Count -and (-not $blocked -or $allowWebRecovery)) {
        if ($recoveryTimes.Count -ge 3) { $blocked=$true; $reason='Recovery limit reached; operator attention required' }
        elseif (($now - $lastRecovery).TotalSeconds -ge 300) {
          $lastRecovery=$now; $recoveryTimes += $now
          Write-WatchdogStatus 'recovering' $reason $recoveryTimes.Count
          try {
            foreach ($service in $recoveryTargets) {
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
            foreach ($service in $recoveryTargets) {
              $newRecord = Start-ServiceManaged $service
              $records = @($records | Where-Object { $_.key -ne $service.Key }) + @($newRecord)
              Write-State $records
            }
          } catch { $blocked=$true; $reason='Recovery failed; inspect local service logs' }
        }
      }
      $status = if ($blocked) { 'blocked' } elseif ($targets.Count) { 'degraded' } else { 'healthy' }
      Write-WatchdogStatus $status $reason $recoveryTimes.Count
      } catch {
        # Keep the watchdog alive across transient file/network/process errors;
        # a single uncaught probe exception previously killed the only recovery
        # process and left all three services down together.
        try { Write-WatchdogStatus 'degraded' 'Watchdog probe failed; retrying' $recoveryTimes.Count } catch {}
      } finally { $cycleLock.ReleaseMutex(); $cycleLock.Dispose() }
      Start-Sleep -Seconds 15
    }
  } finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
}
