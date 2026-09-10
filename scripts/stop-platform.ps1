[CmdletBinding()]
param()

# The desktop shortcut uses the same verified PID ownership as restart.
& (Join-Path $PSScriptRoot 'dev-platform.ps1') -Action stop
