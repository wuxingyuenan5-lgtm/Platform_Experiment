[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$pythonw = Join-Path $RepoRoot 'execution-runtime\.venv\Scripts\pythonw.exe'
$launcher = Join-Path $PSScriptRoot 'launch-platform-child.py'
$shellPath = (Get-Process -Id $PID).Path
$logDir = Join-Path $RepoRoot '.codex\dev-platform\logs'
foreach ($path in @($pythonw, $launcher)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing launcher: $path" }
}
# Require both existing tasks before changing either. Preserve their triggers,
# principals, restart policy and limits; do not stop services or running tasks.
$tasks = @(
    @{ Name = 'Global Variable Platform Supervisor'; Script = 'dev-platform.ps1'; Suffix = ' -Action supervisor'; Log = 'scheduled-supervisor' },
    @{ Name = 'Global Variable Platform Supervisor Pulse'; Script = 'platform-supervisor-pulse.ps1'; Suffix = ''; Log = 'scheduled-pulse' }
)
foreach ($entry in $tasks) { Get-ScheduledTask -TaskName $entry.Name -ErrorAction Stop | Out-Null }
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
foreach ($entry in $tasks) {
    $scriptPath = Join-Path $PSScriptRoot $entry.Script
    $stdout = Join-Path $logDir ($entry.Log + '.out.log')
    $stderr = Join-Path $logDir ($entry.Log + '.err.log')
    $arguments = '"{0}" --wait "{1}" "{2}" "{3}" "{4}" -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "{5}"{6}' -f $launcher, $shellPath, $RepoRoot, $stdout, $stderr, $scriptPath, $entry.Suffix
    $action = New-ScheduledTaskAction -Execute $pythonw -Argument $arguments -WorkingDirectory $RepoRoot
    Set-ScheduledTask -TaskName $entry.Name -Action $action | Select-Object TaskName, State
}
