param(
    [Parameter(Mandatory = $true)][string]$StrategyInstanceId,
    [Parameter(Mandatory = $true)][string]$AccountId,
    [Parameter(Mandatory = $true)][string]$BusinessDate,
    [Parameter(Mandatory = $true)][string]$TimeZone,
    [Parameter(Mandatory = $true)][string]$ValuationTime,
    [Parameter(Mandatory = $true)][string]$DueAt,
    [Parameter(Mandatory = $true)][string]$Actor,
    [Parameter(Mandatory = $true)][string]$Owner,
    [string]$PlatformBaseUrl = "http://127.0.0.1:8000/api/v1",
    [string]$RuntimeBaseUrl = "http://127.0.0.1:8100",
    [string]$OutputDirectory = "outputs/eod-reconciliation",
    [switch]$SkipRuntimePreflight
)

$ErrorActionPreference = "Stop"

function Assert-IsoDateTime {
    param(
        [Parameter(Mandatory = $true)][string]$Value,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $parsed = [DateTimeOffset]::MinValue
    if (-not [DateTimeOffset]::TryParse($Value, [ref]$parsed)) {
        throw "$Name must be an ISO 8601 datetime with an explicit UTC offset."
    }
}

Assert-IsoDateTime -Value $ValuationTime -Name "ValuationTime"
Assert-IsoDateTime -Value $DueAt -Name "DueAt"

$businessDateValue = [DateTime]::MinValue
if (-not [DateTime]::TryParseExact(
    $BusinessDate,
    "yyyy-MM-dd",
    [System.Globalization.CultureInfo]::InvariantCulture,
    [System.Globalization.DateTimeStyles]::None,
    [ref]$businessDateValue
)) {
    throw "BusinessDate must use yyyy-MM-dd."
}

if (-not $SkipRuntimePreflight) {
    & "$PSScriptRoot/live-readonly-preflight.ps1" -RuntimeBaseUrl $RuntimeBaseUrl
}

$naturalIdentity = "$BusinessDate|$StrategyInstanceId|$AccountId"
$sha256 = [System.Security.Cryptography.SHA256]::Create()
try {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($naturalIdentity)
    $hash = [System.BitConverter]::ToString($sha256.ComputeHash($bytes)).Replace("-", "").ToLowerInvariant()
}
finally {
    $sha256.Dispose()
}
$idempotencyKey = "eod-$BusinessDate-$($hash.Substring(0, 24))"

$body = @{
    idempotencyKey = $idempotencyKey
    businessDate = $BusinessDate
    timezone = $TimeZone
    valuationTime = $ValuationTime
    strategyInstanceId = $StrategyInstanceId
    accountId = $AccountId
    actor = $Actor
    owner = $Owner
    dueAt = $DueAt
} | ConvertTo-Json -Depth 8

$uri = "$($PlatformBaseUrl.TrimEnd('/'))/ops/eod-reconciliation/reports"
Write-Host "Running EOD reconciliation for $BusinessDate / $AccountId"
Write-Host "Idempotency key: $idempotencyKey"

try {
    $report = Invoke-RestMethod \
        -Method Post \
        -Uri $uri \
        -ContentType "application/json" \
        -Body $body \
        -TimeoutSec 120
}
catch {
    throw "EOD reconciliation request failed: $uri`n$($_.Exception.Message)"
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$outputPath = Join-Path $OutputDirectory "$BusinessDate-$AccountId.json"
$report | ConvertTo-Json -Depth 12 | Set-Content -Path $outputPath -Encoding UTF8

Write-Host ""
Write-Host "Report status: $($report.status)"
Write-Host "SLA status: $($report.slaStatus)"
Write-Host "Scale gate: $($report.scaleGateStatus)"
Write-Host "Open differences: $($report.openDifferenceCount)"
Write-Host "Skipped external events: $(@($report.skippedExternalIds).Count)"
Write-Host "Missing accounts: $(@($report.missingAccountIds).Count)"
Write-Host "Errors: $(@($report.errors).Count)"
Write-Host "Saved: $outputPath"

if ($report.status -ne "complete") {
    Write-Warning "The EOD report is not clean. Do not increase live limits, capital, symbols, or automation frequency."
    exit 2
}

Write-Host "EOD report is clean and eligible for human review at the existing limits." -ForegroundColor Green
Write-Host "This does not automatically increase any live limit or enable order writes."
