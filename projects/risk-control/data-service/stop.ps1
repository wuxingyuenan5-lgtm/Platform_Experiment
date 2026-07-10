$processes = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "data-service.exe" -or $_.CommandLine -match "data-service"
}

foreach ($process in $processes) {
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}
