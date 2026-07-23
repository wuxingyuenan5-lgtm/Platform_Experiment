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

function Submit-TradeCommand {
  param(
    [Parameter(Mandatory = $true)][string]$IdempotencyKey,
    [Parameter(Mandatory = $true)][string]$StrategyInstanceId,
    [Parameter(Mandatory = $true)][string]$AccountId,
    [Parameter(Mandatory = $true)][string]$InstrumentId,
    [Parameter(Mandatory = $true)][ValidateSet('buy', 'sell')][string]$Side,
    [Parameter(Mandatory = $true)][string]$Quantity,
    [Parameter(Mandatory = $true)][string]$Price
  )

  $Body = @{
    idempotencyKey = $IdempotencyKey
    strategyInstanceId = $StrategyInstanceId
    accountId = $AccountId
    instrumentId = $InstrumentId
    symbol = 'BTCUSDT'
    side = $Side
    orderType = 'limit'
    quantity = $Quantity
    price = $Price
  } | ConvertTo-Json

  $Command = Invoke-RestMethod `
    -Method Post `
    -Uri "$BackendBaseUrl/api/v1/trading/commands" `
    -ContentType 'application/json' `
    -Body $Body `
    -TimeoutSec 10

  if ($Command.status -ne 'filled') {
    throw "Expected a filled trade command, received status: $($Command.status)"
  }

  return $Command
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

$StrategyInstanceId = 'strategy_funding_arbitrage_instance_default'
$AccountId = 'account_sim_usdt'
$SpotInstrumentId = 'instrument_btc_usdt'
$PerpInstrumentId = 'instrument_btc_usdt_perp'
$RunId = [guid]::NewGuid().ToString()

Write-Host 'Submitting opening buy TradeCommand...' -ForegroundColor Cyan
$OpeningCommand = Submit-TradeCommand `
  -IdempotencyKey "smoke:$RunId:open" `
  -StrategyInstanceId $StrategyInstanceId `
  -AccountId $AccountId `
  -InstrumentId $SpotInstrumentId `
  -Side 'buy' `
  -Quantity '2' `
  -Price '100'

$Position = Get-Position -AccountId $AccountId -InstrumentId $SpotInstrumentId
$Pnl = Get-Pnl -AccountId $AccountId -InstrumentId $SpotInstrumentId

if ([decimal]$Position.netQuantity -ne [decimal]2) {
  throw "Expected net quantity 2, received $($Position.netQuantity)"
}
if ([decimal]$Position.averagePrice -ne [decimal]100) {
  throw "Expected average price 100, received $($Position.averagePrice)"
}
if ([decimal]$Pnl.realizedPnl -ne [decimal]0) {
  throw "Expected realized PnL 0, received $($Pnl.realizedPnl)"
}

Write-Host 'Submitting partial closing sell TradeCommand...' -ForegroundColor Cyan
$ClosingCommand = Submit-TradeCommand `
  -IdempotencyKey "smoke:$RunId:close" `
  -StrategyInstanceId $StrategyInstanceId `
  -AccountId $AccountId `
  -InstrumentId $SpotInstrumentId `
  -Side 'sell' `
  -Quantity '1' `
  -Price '110'

$Position = Get-Position -AccountId $AccountId -InstrumentId $SpotInstrumentId
$Pnl = Get-Pnl -AccountId $AccountId -InstrumentId $SpotInstrumentId

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
$BatchBody = @{
  idempotencyKey = "smoke:$RunId:batch"
  strategyInstanceId = $StrategyInstanceId
  accountId = $AccountId
  strategyKey = 'funding_arbitrage'
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

Write-Host ''
Write-Host 'Platform smoke test passed.' -ForegroundColor Green
Write-Host "Opening command: $($OpeningCommand.tradeCommandId)"
Write-Host "Closing command: $($ClosingCommand.tradeCommandId)"
Write-Host "Execution batch: $($Batch.batchId)"
