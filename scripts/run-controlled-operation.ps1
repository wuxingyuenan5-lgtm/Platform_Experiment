param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("health_scan", "backup", "eod")]
    [string]$TaskType,

    [string]$PlatformBaseUrl = "http://127.0.0.1:8000/api/v1",
    [string]$IdempotencyKey,
    [string]$ScheduledFor,
    [string]$Owner = "operations",
    [string]$BackupLabel = "scheduled",
    [string]$EodPayloadPath,
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($env:VG_PLATFORM_BEARER_TOKEN)) {
    throw "VG_PLATFORM_BEARER_TOKEN is required on the controlled host. The token is never printed."
}

if ([string]::IsNullOrWhiteSpace($ScheduledFor)) {
    $ScheduledFor = [DateTimeOffset]::UtcNow.ToString("o")
}

if ([string]::IsNullOrWhiteSpace($IdempotencyKey)) {
    $dateKey = [DateTimeOffset]::Parse($ScheduledFor).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
    $IdempotencyKey = "scheduled-$TaskType-$dateKey"
}

$taskPayload = @{}
switch ($TaskType) {
    "health_scan" {
        $taskPayload = @{ owner = $Owner }
    }
    "backup" {
        $taskPayload = @{ label = $BackupLabel }
    }
    "eod" {
        if ([string]::IsNullOrWhiteSpace($EodPayloadPath)) {
            throw "EodPayloadPath is required for the eod task."
        }
        $resolvedPayload = Resolve-Path -LiteralPath $EodPayloadPath
        $taskPayload = Get-Content -LiteralPath $resolvedPayload -Raw | ConvertFrom-Json -AsHashtable
    }
}

$body = @{
    idempotencyKey = $IdempotencyKey
    taskType = $TaskType
    scheduledFor = $ScheduledFor
    payload = $taskPayload
} | ConvertTo-Json -Depth 20

$headers = @{
    Authorization = "Bearer $($env:VG_PLATFORM_BEARER_TOKEN)"
    "X-Request-ID" = "scheduler-$IdempotencyKey"
}

$response = Invoke-RestMethod `
    -Method Post `
    -Uri "$PlatformBaseUrl/ops/controlled-operations" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $body

$json = $response | ConvertTo-Json -Depth 20
if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
    $parent = Split-Path -Parent $OutputPath
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
}

$json
