$processes = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "auth-service.exe" })

foreach ($process in $processes) {
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped auth-service process PID:$($process.ProcessId)"
}

if (-not $processes) {
    Write-Host "No running auth-service process found"
}
