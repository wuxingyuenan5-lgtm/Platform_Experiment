$ErrorActionPreference = "Stop"

if (-not $env:DB_DSN) {
    throw "Please set the DB_DSN environment variable."
}
if (-not $env:JWT_SECRET) {
    throw "Please set the JWT_SECRET environment variable."
}
if (-not $env:PORT) {
    $env:PORT = "8080"
}

New-Item -ItemType Directory -Force -Path "bin" | Out-Null

Write-Host "Building auth-service..."
go build -o "bin\auth-service.exe" .\cmd

Write-Host "Starting auth-service on port $env:PORT ..."
.\bin\auth-service.exe
