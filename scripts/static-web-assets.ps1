function Copy-VersionedWebAsset {
  param(
    [Parameter(Mandatory)][string]$SourceRoot,
    [Parameter(Mandatory)][string]$AssetRoot,
    [Parameter(Mandatory)][string]$RelativePath,
    [switch]$TrustExisting
  )
  $relative = $RelativePath.Replace('\', '/')
  if ($relative.Split('/') -contains '..') { throw "Invalid Web asset path: $RelativePath" }
  if ($relative -notmatch '^assets/.+-[a-f0-9]{8}(-[0-9]+)?\.[^/]+$') { return }
  $sourceBase = [IO.Path]::GetFullPath($SourceRoot)
  $assetBase = [IO.Path]::GetFullPath($AssetRoot)
  $source = [IO.Path]::GetFullPath((Join-Path $sourceBase $relative))
  $destination = [IO.Path]::GetFullPath((Join-Path $assetBase $relative))
  if (-not $source.StartsWith($sourceBase + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or
      -not $destination.StartsWith($assetBase + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Versioned Web asset path is outside its root: $RelativePath"
  }
  if (Test-Path -LiteralPath $destination -PathType Leaf) {
    if ($TrustExisting) { return }
    if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne
        (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash) {
      throw "Immutable Web asset name has conflicting content: $RelativePath"
    }
    return
  }
  New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
  $temporary = "$destination.$([guid]::NewGuid().ToString('N')).tmp"
  Copy-Item -LiteralPath $source -Destination $temporary
  Move-Item -LiteralPath $temporary -Destination $destination -Force
}

function Initialize-RetainedWebAssets {
  param(
    [Parameter(Mandatory)][string]$ReleaseRoot,
    [Parameter(Mandatory)][string]$AssetRoot
  )
  $seedMarker = Join-Path $AssetRoot '.retained-assets-seeded'
  if (Test-Path -LiteralPath $seedMarker -PathType Leaf) { return }
  $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
  # Existing immutable names are already shared; never duplicate each release tree.
  $releases = Get-ChildItem -LiteralPath $ReleaseRoot -Directory |
    Where-Object { $_.Name -match '^\d{8}T\d{9}Z$' } | Sort-Object Name -Descending
  foreach ($release in $releases) {
    $assets = Join-Path $release.FullName 'assets'
    if (-not (Test-Path -LiteralPath $assets -PathType Container)) { continue }
    foreach ($file in Get-ChildItem -LiteralPath $assets -File -Recurse) {
      $relative = $file.FullName.Substring($release.FullName.Length + 1)
      if (-not $seen.Add($relative)) { continue }
      Copy-VersionedWebAsset -SourceRoot $release.FullName -AssetRoot $AssetRoot -RelativePath $relative -TrustExisting
    }
  }
  New-Item -ItemType Directory -Path $AssetRoot -Force | Out-Null
  [IO.File]::WriteAllText($seedMarker, [DateTimeOffset]::UtcNow.ToString('o'))
}
