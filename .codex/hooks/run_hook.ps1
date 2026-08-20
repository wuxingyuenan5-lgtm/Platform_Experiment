param(
  [Parameter(Mandatory = $true)]
  [string]$ScriptPath
)

$ErrorActionPreference = "Stop"

function Resolve-Python {
  if ($env:CODEX_PYTHON) {
    if (Test-Path -LiteralPath $env:CODEX_PYTHON -PathType Leaf) {
      return $env:CODEX_PYTHON
    }
  }

  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python -and (Test-Path -LiteralPath $python.Source -PathType Leaf)) {
    return $python.Source
  }

  $candidates = @(
    (Join-Path $HOME ".codex\python\python.exe"),
    (Join-Path $HOME ".codex\plugins\cache\openai-primary-runtime\python\python.exe"),
    (Join-Path $HOME ".codex\plugins\cache\openai-primary-runtime\python312\python.exe"),
    (Join-Path $HOME ".codex\plugins\cache\openai-bundled\python\python.exe")
  )

  foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
      return $candidate
    }
  }

  return $null
}

if (-not (Test-Path -LiteralPath $ScriptPath -PathType Leaf)) {
  Write-Error "Hook script not found."
  exit 1
}

$resolvedScriptPath = (Resolve-Path -LiteralPath $ScriptPath).Path
$pythonPath = Resolve-Python
if (-not $pythonPath) {
  Write-Error "No supported Python interpreter found for Codex hooks."
  exit 1
}

$stdinText = [Console]::In.ReadToEnd()
if ([string]::IsNullOrEmpty($stdinText)) {
  & $pythonPath $resolvedScriptPath
}
else {
  $stdinText | & $pythonPath $resolvedScriptPath
}

exit $LASTEXITCODE
