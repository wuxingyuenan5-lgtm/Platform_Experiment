$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$DevPlatformScript = Join-Path $RepoRoot 'scripts\dev-platform.ps1'

if (-not (Test-Path $DevPlatformScript)) {
  Write-Error "Platform start script not found: $DevPlatformScript"
  exit 1
}

try {
  Set-Location $RepoRoot
  & $DevPlatformScript @args
  if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
  Start-Process 'http://127.0.0.1:4373/index.html#/login'
  exit 0
}
catch {
  Write-Error $_
  exit 1
}
