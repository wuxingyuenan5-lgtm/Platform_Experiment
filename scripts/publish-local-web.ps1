[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$WebRoot = Join-Path $RepoRoot 'platform-web'
$ReleaseRoot = Join-Path $RepoRoot '.codex\releases\web'
$Caddy = Join-Path $RepoRoot '.codex\tools\caddy\caddy.exe'
$Template = Join-Path $RepoRoot 'deploy\Caddyfile.windows'
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
$ReleaseDir = Join-Path $ReleaseRoot $stamp
$Marker = Join-Path $ReleaseRoot 'current.json'
$BuildDist = Join-Path $WebRoot 'dist'

function Assert-File([string]$Path, [string]$Description) {
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "$Description is missing: $Path" }
}

Assert-File $Caddy 'Caddy executable'
Assert-File $Template 'Local Caddyfile template'
Assert-File (Join-Path $WebRoot 'package.json') 'Platform Web package manifest'
New-Item -ItemType Directory -Path $ReleaseRoot -Force | Out-Null

Push-Location $WebRoot
try {
  & corepack pnpm run build
  if ($LASTEXITCODE -ne 0) { throw "Platform Web build failed with exit code $LASTEXITCODE" }
} finally { Pop-Location }

Assert-File (Join-Path $BuildDist 'index.html') 'Built Platform Web index'
if (-not (Test-Path -LiteralPath (Join-Path $BuildDist 'assets') -PathType Container)) {
  throw 'Built Platform Web assets directory is missing.'
}
Assert-File (Join-Path $BuildDist '_app.config.js') 'Generated formal brand configuration'

New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null
Get-ChildItem -LiteralPath $BuildDist -Force | Copy-Item -Destination $ReleaseDir -Recurse -Force
$caddyConfig = Join-Path $ReleaseRoot "$stamp.Caddyfile"
$releaseForCaddy = $ReleaseDir.Replace('\', '/')
$caddyText = (Get-Content -LiteralPath $Template -Raw).Replace('{$PLATFORM_WEB_RELEASE_DIR}', ('"' + $releaseForCaddy + '"'))
Set-Content -LiteralPath $caddyConfig -Value $caddyText -Encoding UTF8
& $Caddy validate --config $caddyConfig --adapter caddyfile
if ($LASTEXITCODE -ne 0) { throw 'Caddy rejected the candidate local release configuration.' }

$markerPayload = [ordered]@{
  release = $ReleaseDir
  caddyConfig = $caddyConfig
  publishedAt = [DateTime]::UtcNow.ToString('o')
  contract = 'local-web-release.v1'
}
$markerTemp = "$Marker.$([guid]::NewGuid().ToString('N')).tmp"
$markerPayload | ConvertTo-Json | Set-Content -LiteralPath $markerTemp -Encoding UTF8
if (Test-Path -LiteralPath $Marker) {
  Copy-Item -LiteralPath $Marker -Destination (Join-Path $ReleaseRoot 'previous.json') -Force
}
Move-Item -LiteralPath $markerTemp -Destination $Marker -Force
Write-Host "Published local web release: $ReleaseDir" -ForegroundColor Green
Write-Host 'Activate only the Web with: scripts/dev-platform.ps1 -Action restart-web'
