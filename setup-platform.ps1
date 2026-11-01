[CmdletBinding()]
param(
  # Reinstall dependencies even when the environment already looks complete.
  [switch]$Force,
  # Skip the frontend pnpm install.
  [switch]$SkipWeb,
  # Skip both Python virtual environments.
  [switch]$SkipPython
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# The Windows console defaults to the legacy ANSI code page (936 on this host),
# which turns any non-ASCII path printed here into mojibake. Switch this process
# to UTF-8 so repository paths and file names survive the round trip.
try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding = $utf8
  $OutputEncoding = $utf8
} catch { }

function Write-Step { param([string]$Message) Write-Host ""; Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Message) Write-Host "    OK  $Message" -ForegroundColor Green }
function Write-Skip { param([string]$Message) Write-Host "    --  $Message" -ForegroundColor DarkGray }
function Write-Warn { param([string]$Message) Write-Host "    !!  $Message" -ForegroundColor Yellow }
function Write-Dim  { param([string]$Message) Write-Host "        $Message" -ForegroundColor DarkGray }

function Wait-ForKey {
  Write-Host ""
  Write-Host "Press any key to continue . . ."
  try { $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown') } catch { }
}

function Fail {
  param([string]$Message, [string[]]$Hints)
  Write-Host ""
  Write-Host "SETUP FAILED: $Message" -ForegroundColor Red
  foreach ($hint in @($Hints)) { if ($hint) { Write-Host "  Hint: $hint" -ForegroundColor Yellow } }
  Wait-ForKey
  exit 1
}

# Returns a hashtable describing a Python 3.12+ interpreter, or $null.
function Get-PythonLauncher {
  $candidates = @()

  # 1) The Windows py launcher is authoritative when present.
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    $listed = @(& py -0p 2>$null)
    foreach ($line in $listed) {
      if ($line -match '^\s*-V:(3\.\d+)\s+\*?\s*(.+?)\s*$') {
        $tag = $Matches[1]
        if ([version]$tag -ge [version]'3.12') {
          $candidates += @{ Exe = $py.Source; Args = @("-$tag"); Label = "py -$tag" }
        }
      }
    }
  }

  # 2) Whatever `python` resolves to, if it is new enough.
  $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
  if ($pythonCmd) {
    $candidates += @{ Exe = $pythonCmd.Source; Args = @(); Label = $pythonCmd.Source }
  }

  # 3) Common per-user and machine-wide install locations.
  foreach ($root in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, "$env:LOCALAPPDATA\Programs\Python")) {
    if (-not $root) { continue }
    foreach ($ver in @('313', '312', '314', '315')) {
      $exe = Join-Path $root "Python$ver\python.exe"
      if (Test-Path -LiteralPath $exe) { $candidates += @{ Exe = $exe; Args = @(); Label = $exe } }
    }
  }

  foreach ($candidate in $candidates) {
    if (-not (Test-Path -LiteralPath $candidate.Exe)) { continue }
    try {
      $versionText = (& $candidate.Exe @($candidate.Args) -c "import sys;print('%d.%d.%d' % sys.version_info[:3])" 2>$null | Select-Object -Last 1)
      if ($LASTEXITCODE -ne 0 -or -not $versionText) { continue }
      $versionText = "$versionText".Trim()
      if ($versionText -match '^3\.(\d+)\.' -and [version]$versionText -ge [version]'3.12.0') {
        return [pscustomobject]@{ Exe = $candidate.Exe; Args = $candidate.Args; Version = $versionText; Label = $candidate.Label }
      }
    } catch { }
  }

  return $null
}

function Invoke-Python {
  param([hashtable]$Launcher, [string]$Directory, [string[]]$Arguments)
  Push-Location $Directory
  try {
    & $Launcher.Exe @($Launcher.Args) @($Arguments)
    return $LASTEXITCODE
  } finally { Pop-Location }
}

function New-PythonEnvironment {
  param([string]$Name, [string]$Directory, [hashtable]$Launcher)

  $venvDir = Join-Path $Directory '.venv'
  $venvPython = Join-Path $venvDir 'Scripts\python.exe'
  Write-Step "$Name Python environment"

  if ((Test-Path -LiteralPath $venvPython) -and -not $Force) {
    Write-Skip 'existing .venv reused (pass -Force to rebuild)'
  } else {
    if (Test-Path -LiteralPath $venvDir) {
      Write-Dim 'removing previous .venv'
      Remove-Item -LiteralPath $venvDir -Recurse -Force
    }
    Write-Dim "creating .venv with Python $($Launcher.Version)"
    $code = Invoke-Python -Launcher $Launcher -Directory $Directory -Arguments @('-m', 'venv', '.venv')
    if ($code -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) {
      Fail "$Name virtual environment could not be created" @(
        "Verify $($Launcher.Exe) can run 'python -m venv .venv' manually.",
        'An Antivirus or Controlled Folder Access policy can block venv creation.'
      )
    }
    Write-Ok ".venv created ($($Launcher.Version))"
  }

  Write-Dim 'installing dependencies: pip install -e ".[dev]"'
  & $venvPython -m pip install --upgrade pip --quiet --disable-pip-version-check
  $code = 0
  Push-Location $Directory
  try {
    & $venvPython -m pip install -e ".[dev]" --disable-pip-version-check
    $code = $LASTEXITCODE
  } finally { Pop-Location }
  if ($code -ne 0) {
    Fail "$Name dependency installation failed" @(
      'Check network access to PyPI, or configure a proxy / mirror (e.g. -i https://pypi.tuna.tsinghua.edu.cn/simple).',
      'MetaTrader5 and ccxt are part of the [dev] extra and need a working network.'
    )
  }
  Write-Ok 'dependencies installed'
  return $venvPython
}

function Test-PythonImports {
  param([string]$VenvPython, [string]$ImportExpression)
  & $VenvPython -c $ImportExpression 2>$null
  return ($LASTEXITCODE -eq 0)
}

# ==================================================================== preamble
Write-Host ""
Write-Host "Variable Global Platform - local environment setup" -ForegroundColor White
Write-Host "Repository: $RepoRoot" -ForegroundColor DarkGray
Write-Host "PowerShell: $($PSVersionTable.PSVersion)" -ForegroundColor DarkGray

if ($PSVersionTable.PSVersion.Major -lt 7) {
  Write-Warn "You are running Windows PowerShell $($PSVersionTable.PSVersion)."
  Write-Warn 'The platform lifecycle scripts are validated on PowerShell 7.'
  Write-Warn 'If startup later fails, install PowerShell 7 and re-run there.'
}

# ================================================================ prerequisites
Write-Step 'Toolchain prerequisites'

$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($null -eq $nodeCmd) {
  Fail 'Node.js was not found on PATH' @(
    'Install Node.js 22.x from https://nodejs.org/ (LTS installer).',
    'Then close this window, reopen it, and run the setup .bat again.'
  )
}
Write-Ok "node $(& node --version)"

$corepackCmd = Get-Command corepack -ErrorAction SilentlyContinue
if ($null -eq $corepackCmd) {
  Fail 'corepack was not found on PATH' @(
    'corepack ships with Node.js; reinstall Node.js 22.x from https://nodejs.org/.'
  )
}

$pythonLauncher = $null
if (-not $SkipPython) {
  $pythonLauncher = Get-PythonLauncher
  if ($null -eq $pythonLauncher) {
    Write-Warn 'No Python 3.12 or newer interpreter was found.'
    if ($PSVersionTable.PSVersion.Major) { }
    $found = Get-Command python -ErrorAction SilentlyContinue
    if ($found) {
      $actual = (& $found.Source -c "import sys;print('%d.%d.%d' % sys.version_info[:3])" 2>$null | Select-Object -Last 1)
      Write-Warn "The 'python' on PATH is $actual at $($found.Source)."
      Write-Warn 'Both services declare requires-python >= 3.12, so that interpreter cannot be used.'
    }
    Fail 'No usable Python 3.12+ interpreter' @(
      'Install Python 3.12 or newer from https://www.python.org/downloads/windows/',
      'During install, tick "Add python.exe to PATH" and include the py launcher.',
      'Then close this window, reopen it, and run the setup .bat again.'
    )
  }
  Write-Ok "python $($pythonLauncher.Version)  ($($pythonLauncher.Label))"
}

# ==================================================================== env files
Write-Step 'Environment variable files'
$envPlan = @(
  @{ Target = (Join-Path $RepoRoot '.env');                   Source = (Join-Path $RepoRoot '.env.example');                    Label = '.env' },
  @{ Target = (Join-Path $RepoRoot 'platform-api\.env');      Source = (Join-Path $RepoRoot 'platform-api\.env.example');        Label = 'platform-api\.env' },
  @{ Target = (Join-Path $RepoRoot 'execution-runtime\.env'); Source = (Join-Path $RepoRoot 'execution-runtime\.env.live.example'); Label = 'execution-runtime\.env' }
)
foreach ($entry in $envPlan) {
  if (Test-Path -LiteralPath $entry.Target) {
    Write-Skip "$($entry.Label) already exists, left untouched"
  } elseif (Test-Path -LiteralPath $entry.Source) {
    Copy-Item -LiteralPath $entry.Source -Destination $entry.Target
    Write-Ok "created $($entry.Label)"
  } else {
    Write-Warn "template missing, skipped: $($entry.Source)"
  }
}
Write-Dim 'Review the generated .env files before enabling any live setting.'

# =================================================================== python envs
$venvState = @{ runtime = 'not requested'; api = 'not requested' }
if (-not $SkipPython) {
  $runtimeVenv = New-PythonEnvironment -Name 'Execution Runtime' `
    -Directory (Join-Path $RepoRoot 'execution-runtime') -Launcher $pythonLauncher
  $apiVenv = New-PythonEnvironment -Name 'Platform API' `
    -Directory (Join-Path $RepoRoot 'platform-api') -Launcher $pythonLauncher

  Write-Step 'Python import verification'
  if (Test-PythonImports -VenvPython $runtimeVenv -ImportExpression 'import fastapi, uvicorn') {
    Write-Ok 'Execution Runtime: fastapi, uvicorn'
    $venvState.runtime = 'ready'
  } else {
    Write-Warn 'Execution Runtime import check failed'
    $venvState.runtime = 'IMPORT FAILED'
  }
  if (Test-PythonImports -VenvPython $apiVenv -ImportExpression 'import fastapi, uvicorn') {
    Write-Ok 'Platform API: fastapi, uvicorn'
    $venvState.api = 'ready'
  } else {
    Write-Warn 'Platform API import check failed'
    $venvState.api = 'IMPORT FAILED'
  }
}

# ===================================================================== frontend
$webState = 'not requested'
if (-not $SkipWeb) {
  Write-Step 'Platform Web dependencies (pnpm)'
  $webDir = Join-Path $RepoRoot 'platform-web'
  $viteCmd = Join-Path $webDir 'node_modules\.bin\vite.cmd'

  if ((Test-Path -LiteralPath $viteCmd) -and -not $Force) {
    Write-Skip 'existing node_modules reused (pass -Force to reinstall)'
    Write-Ok 'vite present'
    $webState = 'ready'
  } else {
    Push-Location $webDir
    try {
      Write-Dim 'corepack pnpm install - this can take several minutes'
      & corepack pnpm install
      $code = $LASTEXITCODE
    } finally { Pop-Location }
    if ($code -ne 0) {
      Fail 'pnpm install failed' @(
        'platform-web/package.json enforces pnpm via "only-allow pnpm"; do not use npm.',
        'Check network access to the npm registry, or configure a registry mirror.',
        'If corepack cannot download pnpm 9.15.9, run "corepack prepare pnpm@9.15.9 --activate" first.'
      )
    }
    if (-not (Test-Path -LiteralPath $viteCmd)) {
      Fail 'pnpm install finished but node_modules\.bin\vite.cmd is still missing' @(
        'Inspect the pnpm output above for skipped or partially installed packages.'
      )
    }
    Write-Ok 'frontend dependencies installed'
    $webState = 'ready'
  }
}

# ====================================================================== summary
Write-Host ""
Write-Host "Local environment setup complete." -ForegroundColor Green
Write-Host ""
Write-Host 'Environment status:'
Write-Host ("  {0,-18} {1}" -f 'execution-runtime', $venvState.runtime)
Write-Host ("  {0,-18} {1}" -f 'platform-api', $venvState.api)
Write-Host ("  {0,-18} {1}" -f 'platform-web', $webState)
Write-Host ""
Write-Host 'Next step: run the platform start script (see README "Local startup").' -ForegroundColor Cyan
Write-Host 'From this repository root:' -ForegroundColor DarkGray
Write-Host '  Double-click the start .bat next to this setup script, or run:' -ForegroundColor DarkGray
Write-Host '  scripts\dev-platform.ps1' -ForegroundColor DarkGray
Write-Host 'Endpoints once started:' -ForegroundColor DarkGray
Write-Host '  Platform Web:        http://127.0.0.1:4373/index.html' -ForegroundColor DarkGray
Write-Host '  Platform API:        http://127.0.0.1:8000/health' -ForegroundColor DarkGray
Write-Host '  Execution Runtime:   http://127.0.0.1:8100/health' -ForegroundColor DarkGray

Wait-ForKey
exit 0
