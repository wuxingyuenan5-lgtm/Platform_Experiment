#Requires -RunAsAdministrator
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
# Use Windows' already configured time source; do not invent a broker timezone
# or manually set a trading host's clock from an application timestamp.
Set-Service -Name W32Time -StartupType Automatic
Start-Service -Name W32Time
& w32tm.exe /resync
if ($LASTEXITCODE -ne 0) { throw 'Windows Time resync failed; inspect its configured time source.' }
& w32tm.exe /query /status
if ($LASTEXITCODE -ne 0) { throw 'Windows Time status could not be verified.' }
