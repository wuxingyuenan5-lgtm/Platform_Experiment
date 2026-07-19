[CmdletBinding()]
param(
  [string]$BackendBaseUrl = 'http://127.0.0.1:8000',
  [string]$RuntimeBaseUrl = 'http://127.0.0.1:8100'
)

$ErrorActionPreference = 'Stop'

function Wait-ForHealth {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Url
  )

  for ($Attempt = 1; $Attempt -le 20; $Attempt++) {
    try {
      $Health = Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 2
      if ($Health.status -eq 'ok') {
        Write-Host "$Name is healthy." -ForegroundColor Green
        return
      }
    }
    catch {
      if ($Attempt -eq 20) {
        throw "$Name did not become healthy at $Url. $($_.Exception.Message)"
      }
    }
    Start-Sleep -Seconds 1
  }
}

function Submit-Order {
  param(
    [Parameter(Mandatory = $true)][string]$AccountId,
    [Parameter(Mandatory = $true)][string]$InstrumentId,
    [Parameter(Mandatory = $true)][ValidateSet('buy', 'sell')][string]$Side,
    [Parameter(Mandatory = $true)][string]$Quantity,
    [Parameter(Mandatory = $true)][string]$Price
  )

  $Body = @{
    accountId = $AccountId
    instrumentId = $InstrumentId
    symbol = 'SMOKEUSDT'
    side = $Side
    orderType = 'limit'
    quantity = $Quantity
    price = $Price
  } | ConvertTo-Json

  $Order = Invoke-RestMethod `
    -Method Post `
    -Uri "$BackendBaseUrl/api/v1/trading/orders" `
    -ContentType 'application/json' `
    -Body $Body `
    -TimeoutSec 10

  if ($Order.status -ne 'filled') {
    throw "Expected a filled order, received status: $($Order.status)"
  }

  return $Order
}

function Get-Position {
  param(
    [Parameter(Mandatory = $true)][string]$AccountId,
    [Parameter(Mandatory = $true)][string]$InstrumentId
  )

  return Invoke-RestMethod `
    -Method Get `
    -Uri "$BackendBaseUrl/api/v1/accounts/$AccountId/positions/$InstrumentId" `
    -TimeoutSec 5
}

function Get-Pnl {
  param(
    [Parameter(Mandatory = $true)][string]$AccountId,
    [Parameter(Mandatory = $true)][string]$InstrumentId
  )

  return Invoke-RestMethod `
    -Method Get `
    -Uri "$BackendBaseUrl/api/v1/accounts/$AccountId/pnl/$InstrumentId" `
    -TimeoutSec 5
}

Wait-ForHealth -Name 'Execution Runtime' -Url "$RuntimeBaseUrl/health"
Wait-ForHealth -Name 'Platform Backend' -Url "$BackendBaseUrl/health"

$AccountId = [guid]::NewGuid().ToString()
$InstrumentId = [guid]::NewGuid().ToString()

Write-Host 'Submitting opening buy order...' -ForegroundColor Cyan
$OpeningOrder = Submit-Order `
  -AccountId $AccountId `
  -InstrumentId $InstrumentId `
  -Side 'buy' `
  -Quantity '2' `
  -Price '100'

$Position = Get-Position -AccountId $AccountId -InstrumentId $InstrumentId
$Pnl = Get-Pnl -AccountId $AccountId -InstrumentId $InstrumentId

if ([decimal]$Position.netQuantity -ne [decimal]2) {
  throw "Expected net quantity 2, received $($Position.netQuantity)"
}
if ([decimal]$Position.averagePrice -ne [decimal]100) {
  throw "Expected average price 100, received $($Position.averagePrice)"
}
if ([decimal]$Pnl.realizedPnl -ne [decimal]0) {
  throw "Expected realized PnL 0, received $($Pnl.realizedPnl)"
}

Write-Host 'Submitting partial closing sell order...' -ForegroundColor Cyan
$ClosingOrder = Submit-Order `
  -AccountId $AccountId `
  -InstrumentId $InstrumentId `
  -Side 'sell' `
  -Quantity '1' `
  -Price '110'

$Position = Get-Position -AccountId $AccountId -InstrumentId $InstrumentId
$Pnl = Get-Pnl -AccountId $AccountId -InstrumentId $InstrumentId

if ([decimal]$Position.netQuantity -ne [decimal]1) {
  throw "Expected net quantity 1, received $($Position.netQuantity)"
}
if ([decimal]$Position.averagePrice -ne [decimal]100) {
  throw "Expected remaining average price 100, received $($Position.averagePrice)"
}
if ([decimal]$Pnl.realizedPnl -ne [decimal]10) {
  throw "Expected realized PnL 10, received $($Pnl.realizedPnl)"
}

Write-Host 'Submitting two-leg execution batch...' -ForegroundColor Cyan
$BatchAccountId = [guid]::NewGuid().ToString()
$SpotInstrumentId = [guid]::NewGuid().ToString()
$PerpInstrumentId = [guid]::NewGuid().ToString()
$BatchBody = @{
  accountId = $BatchAccountId
  strategyKey = 'funding_carry'
  direction = 'collect'
  legs = @(
    @{
      role = 'spot'
      instrumentId = $SpotInstrumentId
      symbol = 'BTCUSDT'
      side = 'buy'
      orderType = 'limit'
      quantity = '1'
      price = '100'
    },
    @{
      role = 'perp'
      instrumentId = $PerpInstrumentId
      symbol = 'BTCUSDT-PERP'
      side = 'sell'
      orderType = 'limit'
      quantity = '1'
      price = '100'
    }
  )
} | ConvertTo-Json -Depth 5

$Batch = Invoke-RestMethod `
  -Method Post `
  -Uri "$BackendBaseUrl/api/v1/trading/execution-batches" `
  -ContentType 'application/json' `
  -Body $BatchBody `
  -TimeoutSec 15

if ($Batch.status -ne 'hedged') {
  throw "Expected hedged batch, received status: $($Batch.status)"
}
if ($Batch.requiresManualIntervention) {
  throw 'Hedged smoke batch unexpectedly requires manual intervention.'
}
if ($Batch.legs.Count -ne 2) {
  throw "Expected two batch legs, received $($Batch.legs.Count)"
}

$SpotPosition = Get-Position `
  -AccountId $BatchAccountId `
  -InstrumentId $SpotInstrumentId
$PerpPosition = Get-Position `
  -AccountId $BatchAccountId `
  -InstrumentId $PerpInstrumentId

if ([decimal]$SpotPosition.netQuantity -ne [decimal]1) {
  throw "Expected spot quantity 1, received $($SpotPosition.netQuantity)"
}
if ([decimal]$PerpPosition.netQuantity -ne [decimal]-1) {
  throw "Expected perpetual quantity -1, received $($PerpPosition.netQuantity)"
}

Write-Host ''
Write-Host 'Platform smoke test passed.' -ForegroundColor Green
Write-Host "Opening order: $($OpeningOrder.orderId)"
Write-Host "Closing order: $($ClosingOrder.orderId)"
Write-Host "Execution batch: $($Batch.batchId)"
