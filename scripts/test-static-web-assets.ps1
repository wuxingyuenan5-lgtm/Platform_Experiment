$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'static-web-assets.ps1')
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('web-assets-' + [guid]::NewGuid().ToString('N'))
$old = Join-Path $fixture '20261020T100000000Z'
$new = Join-Path $fixture '20261020T110000000Z'
$shared = Join-Path $fixture 'shared'
New-Item -ItemType Directory -Path "$old/assets", "$new/assets" -Force | Out-Null
[IO.File]::WriteAllText("$old/assets/chart-12345678.js", 'old chart')
[IO.File]::WriteAllText("$new/assets/chart-87654321.js", 'new chart')
[IO.File]::WriteAllText("$new/assets/config.js", 'mutable')
Initialize-RetainedWebAssets -ReleaseRoot $fixture -AssetRoot $shared
Initialize-RetainedWebAssets -ReleaseRoot $fixture -AssetRoot $shared
foreach ($name in 'chart-12345678.js', 'chart-87654321.js') {
  if (-not (Test-Path -LiteralPath "$shared/assets/$name")) { throw "Missing retained asset: $name" }
}
if (Test-Path -LiteralPath "$shared/assets/config.js") { throw 'Mutable asset archived' }
Copy-VersionedWebAsset -SourceRoot $new -AssetRoot $shared -RelativePath 'assets/chart-87654321.js'
[IO.File]::WriteAllText("$new/assets/chart-87654321.js", 'conflict')
$rejected = $false
try { Copy-VersionedWebAsset -SourceRoot $new -AssetRoot $shared -RelativePath 'assets/chart-87654321.js' } catch { $rejected = $true }
if (-not $rejected -or [IO.File]::ReadAllText("$shared/assets/chart-87654321.js") -ne 'new chart') { throw 'Immutable conflict not protected' }
$rejected = $false
try { Copy-VersionedWebAsset -SourceRoot $new -AssetRoot $shared -RelativePath 'assets/../../escape-12345678.js' } catch { $rejected = $true }
if (-not $rejected) { throw 'Path escape accepted' }
'PASS: retained releases, repeat initialization, mutable exclusion, immutable conflict, path escape'
