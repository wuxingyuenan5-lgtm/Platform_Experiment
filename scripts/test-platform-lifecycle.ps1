[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$StatusScript = Join-Path $PSScriptRoot 'status-platform.ps1'
$DevScript = Join-Path $PSScriptRoot 'dev-platform.ps1'
$StopScript = Join-Path $PSScriptRoot 'stop-platform.ps1'
$StatePath = Join-Path $RepoRoot '.codex\dev-platform\lifecycle-stale-test.json'

function Assert-True {
  param([Parameter(Mandatory = $true)][bool]$Condition, [Parameter(Mandatory = $true)][string]$Message)

  if (-not $Condition) {
    throw $Message
  }
}

try {
  Assert-True (Test-Path $StatusScript) 'status-platform.ps1 must exist.'
  Assert-True (Test-Path $StopScript) 'stop-platform.ps1 must exist.'

  $DevSource = Get-Content -LiteralPath $DevScript -Raw
  Assert-True ($DevSource -match 'Port = 8100' -and $DevSource -match 'Port = 8000' -and $DevSource -match 'Port = 4373') 'Startup must define the three fixed service ports.'
  Assert-True ($DevSource -notmatch '5273|5173|8001|8002|8003') 'Normal startup must not include alternate ports.'
  Assert-True ($DevSource -notmatch 'seed_user_system_demo') 'Normal startup must not seed demo accounts.'
  Assert-True ($DevSource -notmatch 'Start-Process[^\r\n]*(pnpm|npx|pip)[^\r\n]*install|&\s+(pnpm|npx|pip)\s+install') 'Normal startup must not install dependencies.'
  Assert-True ($DevSource -match 'Stop-StartedService' -and $DevSource -match 'services started by this attempt were stopped') 'Startup failures must clean up services started by this attempt.'
  Assert-True ($DevSource -match 'function Remove-StaleStateFile' -and $DevSource -match 'Remove-StaleStateFile') 'Startup must clear an old state file when it has no verifiable managed listener.'

  New-Item -ItemType Directory -Path (Split-Path -Parent $StatePath) -Force | Out-Null
  @{
    repoRoot = $RepoRoot
    services = @(
      @{ name = 'No Listener'; port = 18081; healthUrl = 'http://127.0.0.1:18081/health'; listenerPid = 999999; launcherPid = 999999; workingDirectory = $RepoRoot; ownership = 'managed' }
    )
  } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StatePath -Encoding UTF8

  $NoListener = @(@{ Name = 'No Listener'; Port = 18081; Url = 'http://127.0.0.1:18081/health'; Python = $true })
  $StatusOutput = & $StatusScript -StatePath $StatePath -ServiceDefinitions $NoListener 2>&1 | Out-String
  Assert-True ($StatusOutput -match 'No Listener: stopped') 'A stale record without a listener must not report running.'

  $HealthyListener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($HealthyListener) {
    @{ repoRoot = $RepoRoot; services = @(@{ name = 'Platform API'; port = 8000; listenerPid = 999999; launcherPid = 999999; workingDirectory = (Join-Path $RepoRoot 'platform-api'); ownership = 'managed' }) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StatePath -Encoding UTF8
    $HealthyOutput = & $StatusScript -StatePath $StatePath 2>&1 | Out-String
    Assert-True ($HealthyOutput -match 'Platform API: running.*state record is stale') 'A healthy service with an expired record must be reported as running with stale state.'
    & $StopScript -StatePath $StatePath 2>&1 | Out-Null
    $AfterStopAttempt = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    Assert-True ($null -ne $AfterStopAttempt) 'Stop must not terminate a listener that is not the recorded project process.'
  }

  Write-Host 'Platform lifecycle checks passed.' -ForegroundColor Green
}
finally {
  if (Test-Path $StatePath) {
    Remove-Item -LiteralPath $StatePath -Force
  }
}
