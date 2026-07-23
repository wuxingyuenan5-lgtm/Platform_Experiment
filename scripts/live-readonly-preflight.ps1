param(
    [string]$RuntimeBaseUrl = "http://127.0.0.1:8100",
    [switch]$AllowWriteGate
)

$ErrorActionPreference = "Stop"

function Invoke-RuntimeJson {
    param([Parameter(Mandatory = $true)][string]$Path)

    $uri = "$($RuntimeBaseUrl.TrimEnd('/'))$Path"
    try {
        return Invoke-RestMethod -Method Get -Uri $uri -TimeoutSec 15
    }
    catch {
        throw "Runtime request failed: $uri`n$($_.Exception.Message)"
    }
}

function Assert-True {
    param(
        [Parameter(Mandatory = $true)][bool]$Condition,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

Write-Host "[1/5] Runtime health"
$health = Invoke-RuntimeJson -Path "/health"
Assert-True ($health.status -eq "ok") "Runtime health is not ok."

Write-Host "[2/5] Runtime status"
$status = Invoke-RuntimeJson -Path "/status"
Assert-True ($status.environment -eq "live") "Runtime environment must be live for real-account verification."
Assert-True ($status.gateway -eq "bybit_mt5") "Runtime gateway must be bybit_mt5."

Write-Host "[3/5] Gateway capabilities"
$capabilities = Invoke-RuntimeJson -Path "/gateway/capabilities"
Assert-True ($capabilities.environment -eq "live") "Gateway capability environment is not live."
if (-not $AllowWriteGate) {
    Assert-True (-not [bool]$capabilities.liveWriteEnabled) (
        "liveWriteEnabled must remain false during read-only and shadow verification."
    )
}

$configuredAdapters = @($capabilities.adapters | Where-Object { $_.configured })
Assert-True ($configuredAdapters.Count -gt 0) "No live adapter is configured."

Write-Host "[4/5] Credential references"
$connectivity = Invoke-RuntimeJson -Path "/gateway/connectivity"
Assert-True ($connectivity.credentialCount -gt 0) "No credential reference is configured."
Assert-True (
    $connectivity.configuredCredentialCount -eq $connectivity.credentialCount
) "One or more credential references are incomplete."

Write-Host "[5/5] Venue readiness"
$readiness = Invoke-RuntimeJson -Path "/gateway/venue-readiness"
$failedVenues = @($readiness.venues | Where-Object { $_.status -ne "ready" })
if ($failedVenues.Count -gt 0) {
    $details = $failedVenues | ForEach-Object {
        "$($_.venue): $($_.status) - $($_.reason)"
    }
    throw "Venue readiness failed:`n$($details -join "`n")"
}

Write-Host ""
Write-Host "Read-only live preflight passed." -ForegroundColor Green
Write-Host "No order was submitted and no live position was changed."
Write-Host "Next stage: query balances, positions, orders, fills, and economic events, then reconcile them with Platform facts."
