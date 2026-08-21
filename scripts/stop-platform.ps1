[CmdletBinding()]
param([string]$StatePath)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$DefaultStatePath = Join-Path $RepoRoot '.codex\dev-platform\platform-dev-state.json'
if (-not $StatePath) { $StatePath = $DefaultStatePath }
$ExpectedServices = @{
  8100 = (Join-Path $RepoRoot 'execution-runtime')
  8000 = (Join-Path $RepoRoot 'platform-api')
  4373 = (Join-Path $RepoRoot 'platform-web')
}
function Get-PortListener { param([int]$Port) Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 }
function Test-ProjectProcess {
  param([int]$ProcessId, [string]$WorkingDirectory)
  $process = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
  return $null -ne $process -and ([string]$process.CommandLine).ToLowerInvariant().Contains($WorkingDirectory.ToLowerInvariant())
}
if (-not (Test-Path $StatePath)) { Write-Host 'No recorded platform processes to stop.'; return }
$state = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
if ($state.repoRoot -ne $RepoRoot) { throw "State file belongs to another repository: $($state.repoRoot)" }
$remaining = @()
foreach ($service in @($state.services)) {
  $port = [int]$service.Port
  if (-not $ExpectedServices.ContainsKey($port) -or $service.WorkingDirectory -ne $ExpectedServices[$port] -or $service.ownership -ne 'managed') {
    Write-Warning "$($service.Name) is not a managed service record for this platform; leaving it untouched."
    $remaining += $service
    continue
  }
  $listener = Get-PortListener $port
  if (-not $listener) { Write-Host "$($service.Name) is already stopped; clearing its stale record."; continue }
  if ([int]$listener.OwningProcess -ne [int]$service.ListenerPid) { Write-Warning "$($service.Name) port $($service.Port) is not owned by its recorded process; leaving it untouched."; continue }
  if (-not (Test-ProjectProcess $service.ListenerPid $service.WorkingDirectory)) { Write-Warning "$($service.Name) listener identity could not be verified; leaving it untouched."; $remaining += $service; continue }
  foreach ($targetPid in @([int]$service.ListenerPid, [int]$service.LauncherPid | Select-Object -Unique)) {
    if ($targetPid -gt 0 -and (Test-ProjectProcess $targetPid $service.WorkingDirectory)) { Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue }
  }
  Start-Sleep -Milliseconds 300
  if (Get-PortListener $port) { Write-Warning "$($service.Name) did not release port $($service.Port)."; $remaining += $service } else { Write-Host "Stopped $($service.Name)." }
}
if ($remaining.Count -eq 0) { Remove-Item -LiteralPath $StatePath -Force -ErrorAction SilentlyContinue } else { @{ repoRoot = $RepoRoot; updatedAt = (Get-Date).ToString('o'); services = @($remaining) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StatePath -Encoding UTF8 }
Write-Host 'Platform stop completed.' -ForegroundColor Green
