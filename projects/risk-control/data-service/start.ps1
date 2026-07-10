$ErrorActionPreference = "Stop"

if (-not $env:TZ) {
    $env:TZ = "Asia/Shanghai"
}
if (-not $env:DB_DSN) {
    throw "Please set the DB_DSN environment variable."
}
if (-not $env:JWT_SECRET) {
    throw "Please set the JWT_SECRET environment variable."
}
if (-not $env:PORT) {
    $env:PORT = "8082"
}
if (-not $env:SYNC_INTERVAL) {
    $env:SYNC_INTERVAL = "5m"
}
if (-not $env:SYNC_ON_START) {
    $env:SYNC_ON_START = "true"
}
if (-not $env:SCHEDULER_ENABLED) {
    $env:SCHEDULER_ENABLED = "true"
}
if (-not $env:BYBIT_CREDENTIAL_FILE) {
    $env:BYBIT_CREDENTIAL_FILE = "bitget-data-service/bybitapi.txt"
}
if (-not $env:BYBIT_ACCOUNT_TYPE) {
    $env:BYBIT_ACCOUNT_TYPE = "UNIFIED"
}
if (-not $env:BYBIT_RECV_WINDOW) {
    $env:BYBIT_RECV_WINDOW = "10000"
}
if (-not $env:BYBIT_TIMESTAMP_OFFSET_MS) {
    $env:BYBIT_TIMESTAMP_OFFSET_MS = "0"
}
if (-not $env:BYBIT_ACCOUNT_ADDRESS) {
    $env:BYBIT_ACCOUNT_ADDRESS = "bybit-unified"
}
if (-not $env:BYBIT_ACCOUNT_NAME) {
    $env:BYBIT_ACCOUNT_NAME = "Bybit Unified Account"
}

New-Item -ItemType Directory -Force -Path "bin" | Out-Null

Write-Host "Building data-service..."
go build -o "bin\data-service.exe" .\cmd

Write-Host "Starting data-service on port $env:PORT ..."
.\bin\data-service.exe
