[CmdletBinding()]
param(
  [string]$StatePath,
  [object[]]$ServiceDefinitions
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not $StatePath) { $StatePath = Join-Path $RepoRoot '.codex\dev-platform\platform-dev-state.json' }
$services = if ($ServiceDefinitions) { @($ServiceDefinitions) } else { @(
  @{ Name = 'Execution Runtime'; Port = 8100; Url = 'http://127.0.0.1:8100/health'; Python = $true },
  @{ Name = 'Platform API'; Port = 8000; Url = 'http://127.0.0.1:8000/health'; Python = $true },
  @{ Name = 'Platform Web'; Port = 4373; Url = 'http://127.0.0.1:4373/index.html'; Python = $false }
) }
$state = if (Test-Path $StatePath) { Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json } else { $null }
foreach ($service in $services) {
  $listener = Get-NetTCPConnection -LocalPort $service.Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
  $healthy = $false
  if ($listener) {
    try {
      $response = Invoke-WebRequest -Uri $service.Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
      $healthy = $response.StatusCode -eq 200
      if ($healthy -and $service.Python) { $healthy = (($response.Content | ConvertFrom-Json).status -eq 'ok') }
      if ($healthy -and -not $service.Python) { $healthy = $response.Content -match 'id="htmlRoot"|vite|/src/main' }
    } catch { $healthy = $false }
  }
  $record = if ($state) { @($state.services | Where-Object { $_.port -eq $service.Port })[0] } else { $null }
  $staleRecord = $record -and ([int]$record.listenerPid -ne [int]$listener.OwningProcess)
  if ($listener -and $healthy) {
    $message = "$($service.Name): running (port $($service.Port), PID $($listener.OwningProcess))"
    if ($staleRecord) { $message += '; service running, but state record is stale' }
    Write-Output $message
  } else {
    Write-Output "$($service.Name): stopped (port $($service.Port) is not healthy)"
    if ($record) { Write-Output '  state: record is stale or the service is no longer listening' }
  }
}
