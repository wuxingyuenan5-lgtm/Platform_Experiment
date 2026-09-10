[CmdletBinding()]
param()

# One owner for process identity, persisted state and lifecycle behavior.
& (Join-Path $PSScriptRoot 'dev-platform.ps1') -Action status
