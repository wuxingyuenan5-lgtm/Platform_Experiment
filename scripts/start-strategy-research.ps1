[CmdletBinding()]
param([ValidateSet('check','start')][string]$Action='check')
$ErrorActionPreference='Stop'
$ResearchRoot=Split-Path -Parent $PSScriptRoot
$ApiRoot=Join-Path $ResearchRoot 'platform-api'
$RuntimeRoot=Join-Path $ResearchRoot 'execution-runtime'
$ApiPython=Join-Path $ApiRoot '.venv\Scripts\python.exe'
$RuntimePython=Join-Path $RuntimeRoot '.venv\Scripts\python.exe'
$env:PYTHONUTF8='1'
if (-not (Test-Path -LiteralPath $ApiPython) -or -not (Test-Path -LiteralPath $RuntimePython)) {
  throw 'Use the project Python environments before research startup.'
}
Push-Location $ApiRoot
try {
  & $ApiPython (Join-Path $ApiRoot 'scripts\strategy_research_ops.py') check
  if ($LASTEXITCODE -ne 0) { throw 'Database preflight failed.' }
  & $ApiPython -c "import pyarrow; print('PyArrow', pyarrow.__version__)"
  if ($LASTEXITCODE -ne 0) { throw 'Parquet dependency unavailable.' }
} finally { Pop-Location }
Push-Location $RuntimeRoot
try {
  & $RuntimePython -c 'from app.config import get_settings; s=get_settings(); print("owner", s.gateway_name, "capture", s.research_capture_enabled, "fixed_account", s.mt5_primary_account_id); assert not s.live_write_enabled, "Live Write active"; assert s.gateway_name=="bybit_mt5", "Real gateway required"; assert s.mt5_primary_account_id in s.mt5_accounts, "Fixed Worker account required"; assert s.research_bybit_account_id in s.bybit_accounts, "Select the configured Bybit request owner"'
  if ($LASTEXITCODE -ne 0) { throw 'Runtime owner preflight failed.' }
} finally { Pop-Location }
if ($Action -eq 'start') {
  # Never retake another checkout's ports or restart a live account owner.
  foreach ($ResearchPort in @(8000,8100,4373)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $ResearchPort -ErrorAction SilentlyContinue) {
      throw "Port $ResearchPort already has an owner. Use its controlled maintenance procedure."
    }
  }
  Push-Location $ApiRoot
  try {
    $ResearchBackup=Join-Path $ApiRoot ('data\backups\research-'+(Get-Date -Format 'yyyyMMddTHHmmss'))
    & $ApiPython (Join-Path $ApiRoot 'scripts\strategy_research_ops.py') backup --destination $ResearchBackup
    if ($LASTEXITCODE -ne 0) { throw 'Backup failed.' }
    & $ApiPython (Join-Path $ApiRoot 'scripts\strategy_research_ops.py') verify-backup --destination $ResearchBackup
    if ($LASTEXITCODE -ne 0) { throw 'Backup verification failed.' }
  } finally { Pop-Location }
  $env:VG_RUNTIME_RESEARCH_CAPTURE_ENABLED='true'
  $env:VG_STRATEGY_RESEARCH_ENABLED='true'
  $env:VG_STRATEGY_RESEARCH_WORKER_ENABLED='true'
  $env:VG_STRATEGY_RESEARCH_PROJECTION_ENABLED='true'
  Push-Location $ApiRoot
  try {
    & $ApiPython -c 'from app.database import initialize_database; initialize_database()'
    if ($LASTEXITCODE -ne 0) { throw 'Migration failed; backup retained.' }
  } finally { Pop-Location }
  # The existing launcher owns all three processes and preserves its identity checks.
  & (Join-Path $PSScriptRoot 'dev-platform.ps1') -Action start
}

