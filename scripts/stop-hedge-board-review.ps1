[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$StatePath = Join-Path $RepoRoot '.codex\hedge-board-review\state.json'
$ExpectedServices = @{
  18000 = (Join-Path $RepoRoot 'platform-api')
  14373 = (Join-Path $RepoRoot 'platform-web')
}

function Get-PortListener {
  param([int]$Port)
  Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
}

function Test-ProjectProcess {
  param([int]$ProcessId, [string]$WorkingDirectory, [int]$Port = 0)
  $process = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
  if ($null -eq $process) { return $false }
  $commandLine = ([string]$process.CommandLine).ToLowerInvariant()
  return $commandLine.Contains($WorkingDirectory.ToLowerInvariant()) -or ($Port -gt 0 -and $commandLine.Contains('--port') -and $commandLine.Contains("$Port"))
}

if (-not (Test-Path -LiteralPath $StatePath)) { Write-Host 'Hedge Board 验收站未运行。'; return }
$state = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
if ($state.repoRoot -ne $RepoRoot) { throw "State file belongs to another repository: $($state.repoRoot)" }
$remaining = @()
foreach ($service in @($state.services)) {
  $port = [int]$service.Port
  if (-not $ExpectedServices.ContainsKey($port) -or $service.WorkingDirectory -ne $ExpectedServices[$port]) {
    Write-Warning "$($service.Name) is not a recognized review service; leaving it untouched."
    $remaining += $service
    continue
  }
  $listener = Get-PortListener $port
  if (-not $listener) { continue }
  if ([int]$listener.OwningProcess -ne [int]$service.ListenerPid -or -not (Test-ProjectProcess ([int]$service.ListenerPid) $service.WorkingDirectory $port)) {
    Write-Warning "$($service.Name) ownership could not be verified; leaving it untouched."
    $remaining += $service
    continue
  }
  foreach ($targetPid in @([int]$service.ListenerPid, [int]$service.LauncherPid | Select-Object -Unique)) {
    if ($targetPid -gt 0 -and (Test-ProjectProcess $targetPid $service.WorkingDirectory $port)) { Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue }
  }
  Write-Host "Stopped $($service.Name)."
}
if ($remaining.Count -eq 0) {
  Remove-Item -LiteralPath $StatePath -Force
} else {
  @{ repoRoot = $RepoRoot; updatedAt = (Get-Date).ToString('o'); services = @($remaining) } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StatePath -Encoding UTF8
}
Write-Host 'Hedge Board 本地验收站已关闭。' -ForegroundColor Green
